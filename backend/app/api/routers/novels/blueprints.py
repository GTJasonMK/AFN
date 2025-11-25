"""
蓝图管理路由

处理小说蓝图的生成、保存、优化和更新操作。
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.state_machine import ProjectStatus
from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_llm_service,
    get_prompt_service,
)
from ....core.config import settings
from ....db.session import get_session
from ....exceptions import (
    PromptTemplateNotFoundError,
    ConflictError,
    InvalidParameterError,
    JSONParseError,
    DatabaseError,
    BlueprintNotReadyError,
)
from ....models.part_outline import PartOutline
from ....models.novel import ChapterOutline
from ....schemas.novel import (
    Blueprint,
    BlueprintGenerationResponse,
    BlueprintPatch,
    BlueprintRefineRequest,
    NovelProject as NovelProjectSchema,
)
from ....schemas.user import UserInDB
from ....repositories.part_outline_repository import PartOutlineRepository
from ....repositories.chapter_repository import ChapterOutlineRepository
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.conversation_service import ConversationService
from ....services.blueprint_service import BlueprintService
from ....services.prompt_service import PromptService
from ....services.vector_store_service import VectorStoreService
from ....services.chapter_ingest_service import ChapterIngestionService
from ....utils.json_utils import (
    remove_think_tags,
    parse_llm_json_or_fail,
    parse_llm_json_safe,
)
from ....utils.prompt_helpers import ensure_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/blueprint/generate", response_model=BlueprintGenerationResponse)
async def generate_blueprint(
    project_id: str,
    force_regenerate: bool = False,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> BlueprintGenerationResponse:
    """根据完整对话生成可执行的小说蓝图。"""
    start_time = time.time()
    logger.info("=== 蓝图生成接口调用 CODE_VERSION=2025-10-27-v2 ===")

    # 初始化服务
    conversation_service = ConversationService(session)
    blueprint_service = BlueprintService(session)
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    logger.info(
        "项目 %s 开始生成蓝图 (force_regenerate=%s, user_id=%s)",
        project_id, force_regenerate, desktop_user.id
    )

    # 检查是否已有章节大纲，如果有且未强制重新生成，则返回警告
    if not force_regenerate:
        outline_count = await novel_service.count_chapter_outlines(project_id)
        if outline_count > 0:
            logger.warning("项目 %s 已有 %d 个章节大纲，需要用户确认是否删除", project_id, outline_count)
            raise ConflictError(
                f"项目已有 {outline_count} 个章节大纲，重新生成蓝图将删除所有章节大纲。请确认后重试。"
            )

    history_records = await conversation_service.list_conversations(project_id)
    if not history_records:
        raise InvalidParameterError("缺少对话历史，无法生成蓝图")

    # 使用ConversationService格式化对话历史
    formatted_history = conversation_service.format_conversation_history(history_records)

    system_prompt = ensure_prompt(await prompt_service.get_prompt("screenwriting"), "screenwriting")

    # 记录LLM调用准备信息
    logger.info(
        "项目 %s 准备调用LLM生成蓝图：对话轮次=%d, max_tokens=%d, timeout=%.1fs",
        project_id, len(formatted_history), 8192, 480.0
    )

    llm_start_time = time.time()

    # 对于大型小说，蓝图JSON可能很大，需要足够的输出长度
    # Gemini 2.5 Flash支持最多8192 output tokens
    blueprint_raw = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=formatted_history,
        temperature=settings.llm_temp_blueprint,
        user_id=desktop_user.id,
        timeout=480.0,
        max_tokens=8192,  # Gemini 2.5 Flash的最大输出限制
    )

    llm_elapsed = time.time() - llm_start_time
    logger.info(
        "项目 %s LLM响应获取成功，耗时 %.2f 秒，响应长度 %d 字符",
        project_id, llm_elapsed, len(blueprint_raw)
    )
    # 解析蓝图JSON
    blueprint_raw = remove_think_tags(blueprint_raw)
    blueprint_data = parse_llm_json_or_fail(
        blueprint_raw,
        f"项目{project_id}的蓝图生成失败"
    )

    logger.info("项目 %s 蓝图JSON解析成功，total_chapters=%s", project_id, blueprint_data.get('total_chapters'))

    try:
        blueprint = Blueprint(**blueprint_data)
    except Exception as exc:
        logger.error("项目 %s 蓝图Pydantic验证失败: %s\nblueprint_data keys: %s", project_id, str(exc), list(blueprint_data.keys()))
        raise JSONParseError(f"蓝图数据格式错误: {str(exc)}") from exc

    # 强制工作流分离：蓝图生成阶段不包含章节大纲
    # 即使LLM违反指令生成了章节大纲，也要强制清空
    # 但为了避免数据丢失，先备份到world_setting的特殊字段中
    if blueprint.chapter_outline:
        logger.warning(
            "项目 %s 蓝图生成时包含了 %d 个章节大纲，违反工作流设计，正在备份并清空",
            project_id,
            len(blueprint.chapter_outline),
        )

        # 初始化world_setting
        if not blueprint.world_setting:
            blueprint.world_setting = {}

        # 清理旧的违规备份（只保留最新一次，避免数据膨胀）
        if '_discarded_chapter_outlines' in blueprint.world_setting:
            old_count = blueprint.world_setting['_discarded_chapter_outlines'].get('count', 0)
            logger.info(
                "项目 %s 清理旧的违规章节大纲备份（共 %d 个）",
                project_id,
                old_count
            )

        # 备份当前被丢弃的数据（只保留元信息，不保留完整data，减少存储）
        blueprint.world_setting['_discarded_chapter_outlines'] = {
            'timestamp': datetime.now().isoformat(),
            'count': len(blueprint.chapter_outline),
            # 仅保留摘要信息，不保留完整数据（避免数据膨胀）
            'summary': f"检测到{len(blueprint.chapter_outline)}个违规章节大纲，已自动清理"
        }

        logger.info(
            "项目 %s 已记录违规章节大纲元信息（count=%d），完整数据已丢弃",
            project_id,
            len(blueprint.chapter_outline)
        )

        # 清空chapter_outline
        blueprint.chapter_outline = []

    # 数据校验与降级：total_chapters 必须大于0
    # 如果LLM返回的章节数无效，使用BlueprintService提取或推断
    total_chapters = blueprint_service.extract_total_chapters(
        blueprint_total=blueprint.total_chapters,
        history_records=history_records,
        formatted_history=formatted_history,
        project_id=project_id,
    )
    blueprint.total_chapters = total_chapters

    # 同时更新 needs_part_outlines 字段（根据章节数��断）
    if total_chapters > settings.part_outline_threshold:
        blueprint.needs_part_outlines = True
        logger.info(
            "项目 %s 章节数 %d 超过阈值 %d，自动设置 needs_part_outlines=True",
            project_id, total_chapters, settings.part_outline_threshold
        )
    else:
        blueprint.needs_part_outlines = False
        logger.info(
            "项目 %s 章节数 %d 未超过阈值 %d，设置 needs_part_outlines=False",
            project_id, total_chapters, settings.part_outline_threshold
        )

    needs_part_outlines = blueprint.needs_part_outlines

    logger.info(
        "项目 %s 蓝图生成完成，总章节数=%d，需要部分大纲=%s",
        project_id,
        total_chapters,
        needs_part_outlines,
    )

    # 根据章节数生成不同的提示消息
    if needs_part_outlines:
        ai_message = (
            f"太棒了！基础蓝图已生成完成。您的小说计划 {total_chapters} 章，"
            "接下来请在详情页点击「生成部分大纲」按钮来规划整体结构，"
            "然后再生成详细的章节大纲。"
        )
    else:
        ai_message = (
            f"太棒了！基础蓝图已生成完成。您的小说计划 {total_chapters} 章，"
            "接下来请在详情页点击「生成章节大纲」按钮来规划具体章节。"
        )

    # 重新生成蓝图时，清除所���已生成的章节内容、部分大纲和向量库数据
    await blueprint_service.cleanup_old_blueprint_data(project, llm_service)

    logger.info("项目 %s 准备保存蓝图到数据库", project_id)
    try:
        await blueprint_service.replace_blueprint(project_id, blueprint)

        # 更新项目标题
        if blueprint.title:
            project.title = blueprint.title
            logger.info("项目 %s 更新标题为 %s", project_id, blueprint.title)

        # 重置项目状态为 blueprint_ready (在数据清理之后,避免状态不一致)
        logger.info("重置项目状态: 当前状态=%s -> blueprint_ready", project.status)
        # 直接设置状态,不使用状态机转换(因为数据已清理,强制重置为初始状态)
        project.status = ProjectStatus.BLUEPRINT_READY.value

        # 统一提交所有更改（清理+保存+标题更新+状态重置）
        await session.commit()
        logger.info("项目 %s 蓝图保存成功，状态已重置为 blueprint_ready", project_id)
    except Exception as exc:
        await session.rollback()
        logger.error("项目 %s 保存蓝图失败: %s", project_id, str(exc), exc_info=True)
        raise DatabaseError(f"保存蓝图失败: {str(exc)}") from exc

    total_elapsed = time.time() - start_time
    logger.info(
        "项目 %s 蓝图生成流程全部完成，总耗时 %.2f 秒 (LLM: %.2f秒, 数据处理: %.2f秒)",
        project_id, total_elapsed, llm_elapsed, total_elapsed - llm_elapsed
    )

    return BlueprintGenerationResponse(blueprint=blueprint, ai_message=ai_message)


@router.post("/{project_id}/blueprint/save", response_model=NovelProjectSchema)
async def save_blueprint(
    project_id: str,
    blueprint_data: Blueprint | None = Body(None),
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
    """保存蓝图信息，可用于手动覆盖自动生成结果。"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    blueprint_service = BlueprintService(session)

    if blueprint_data:
        await blueprint_service.replace_blueprint(project_id, blueprint_data)
        if blueprint_data.title:
            project.title = blueprint_data.title
        await session.commit()
        logger.info("项目 %s 手动保存蓝图", project_id)
    else:
        raise InvalidParameterError("缺少蓝图数据")

    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/{project_id}/blueprint/refine", response_model=BlueprintGenerationResponse)
async def refine_blueprint(
    project_id: str,
    request: BlueprintRefineRequest,
    force: bool = Query(False),
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> BlueprintGenerationResponse:
    """基于用户的优化指令，迭代改进现有蓝图

    注意：优化蓝图会清除所有已生成的章节大纲、部分大纲、章节内容和向量库数据，
    以确保数据与新蓝图保持一致。
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    blueprint_service = BlueprintService(session)
    logger.info("项目 %s 开始优化蓝图 (force=%s)，优化指令：%s", project_id, force, request.refinement_instruction)

    # 检查是否已有章节大纲，如果有且未强制优化，则返回警告
    if not force:
        outline_count = await novel_service.count_chapter_outlines(project_id)
        if outline_count > 0:
            logger.warning("项目 %s 已有 %d 个章节大纲，需要用户确认是否删除", project_id, outline_count)
            raise ConflictError(
                f"项目已有 {outline_count} 个章节大纲，优化蓝图将删除所有章节大纲。请确认后重试。"
            )

    # 获取当前蓝图
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    if not project_schema.blueprint:
        raise BlueprintNotReadyError(project_id)

    # 将当前蓝图转为JSON字符串
    # 排除 part_outlines 字段，因为优化蓝图时不应该修改部分大纲结构
    current_blueprint_json = project_schema.blueprint.model_dump_json(
        indent=2,
        exclude_none=True,
        by_alias=False,
        exclude={'part_outlines'}
    )

    # 构造优化提示词
    system_prompt = ensure_prompt(
        await prompt_service.get_prompt("screenwriting"),
        "screenwriting"
    )

    # 添加优化任务说明
    system_prompt += """

## 蓝图优化任务

你正在进行的是蓝图**优化任务**，而非从零开始创建。

### 优化要求：
1. **保持现有设定的连贯性**：除非用户明确要求修改，否则保留现有的核心设定
2. **针对性改进**：重点优化用户指出的方面
3. **增量改进**：在现有基础上完善，而非推翻重来
4. **输出完整蓝图**：返回优化后的完整蓝图JSON，确保所有字段完整
5. **⚠️ 绝对不要生成章节大纲**：`chapter_outline` 必须保持为空数组 `[]`，章节大纲将在后续步骤单独生成
"""

    # 构建用户消息
    user_message = f"""请基于以下信息优化小说蓝图。

## 当前蓝图（JSON格式）：
```json
{current_blueprint_json}
```

## 用户的优化需求：
{request.refinement_instruction}

请生成优化后的完整蓝图JSON。"""

    # 调用LLM生成优化后的蓝图
    # 对于大型小说（如150章），蓝图JSON可能很大，不应限制输出长度
    blueprint_raw = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_message}],
        temperature=settings.llm_temp_blueprint,
        user_id=desktop_user.id,
        timeout=480.0,
        max_tokens=None,  # 移除限制，让模型输出完整蓝图
    )
    # 解析优化后的蓝图JSON
    blueprint_raw = remove_think_tags(blueprint_raw)
    blueprint_data = parse_llm_json_or_fail(
        blueprint_raw,
        f"项目{project_id}的蓝图优化失败"
    )

    # 验证并保存优化后的蓝图
    try:
        refined_blueprint = Blueprint(**blueprint_data)
    except Exception as exc:
        logger.exception("蓝图优化失败，Pydantic验证错误：project_id=%s, error=%s", project_id, str(exc))
        raise JSONParseError(f"蓝图优化失败：{str(exc)}") from exc

    # 强制工作流分离：蓝图优化阶段不应包含章节大纲
    if refined_blueprint.chapter_outline:
        logger.warning(
            "项目 %s 蓝图优化时包含了 %d 个章节大纲，违反工作流设计，已强制清空",
            project_id,
            len(refined_blueprint.chapter_outline),
        )
        refined_blueprint.chapter_outline = []

    # 优化蓝图时，清除所有已生成的章节内容、部分大纲、章节大纲和向量库数据
    # 以确保数据与新蓝图保持一致
    await blueprint_service.cleanup_old_blueprint_data(project, llm_service)
    logger.info("项目 %s 优化蓝图，已清理所有后续数据", project_id)

    await blueprint_service.replace_blueprint(project_id, refined_blueprint)

    # 更新项目标题（如果蓝图中有）
    if refined_blueprint.title:
        project.title = refined_blueprint.title

    # 重置项目状态为 blueprint_ready (在数据清理之后,避免状态不一致)
    logger.info("重置项目状态: 当前状态=%s -> blueprint_ready", project.status)
    # 直接设置状态,不使用状态机转换(因为数据已清理,强制重置为初始状态)
    project.status = ProjectStatus.BLUEPRINT_READY.value

    await session.commit()
    logger.info("项目 %s 优化完成，状态已重置为 blueprint_ready", project_id)

    ai_message = (
        f"已根据您的要求优化蓝图：「{request.refinement_instruction}」。"
        "请查看优化后的内容，如需继续调整可再次提出优化建议。"
    )

    return BlueprintGenerationResponse(blueprint=refined_blueprint, ai_message=ai_message)


@router.patch("/{project_id}/blueprint", response_model=NovelProjectSchema)
async def patch_blueprint(
    project_id: str,
    payload: BlueprintPatch,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
    """局部更新蓝图字段，对世界观或角色做微调。"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    blueprint_service = BlueprintService(session)

    update_data = payload.model_dump(exclude_unset=True)
    await blueprint_service.patch_blueprint(project_id, update_data)
    await session.commit()
    logger.info("项目 %s 局部更新蓝图字段：%s", project_id, list(update_data.keys()))
    return await novel_service.get_project_schema(project_id, desktop_user.id)
