"""
蓝图管理路由

处理小说蓝图的生成、保存、优化和更新操作。
"""

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.state_machine import ProjectStatus
from ....core.constants import LLMConstants
from ....core.state_validators import (
    validate_project_status,
    BLUEPRINT_EDIT_STATES,
)
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
from ....services.avatar_service import AvatarService
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

    # 状态校验：确保项目处于可编辑蓝图的状态
    validate_project_status(project.status, BLUEPRINT_EDIT_STATES, "生成蓝图")

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
        timeout=LLMConstants.BLUEPRINT_GENERATION_TIMEOUT,
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

    # 使用BlueprintService处理蓝图业务逻辑（验证、清理、章节数提取、消息生成）
    result = blueprint_service.process_generated_blueprint(
        blueprint=blueprint,
        history_records=history_records,
        formatted_history=formatted_history,
        project_id=project_id,
    )
    blueprint = result.blueprint
    ai_message = result.ai_message

    # 重新生成蓝图时，清除所有已生成的章节内容、部分大纲和向量库数据
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
        timeout=LLMConstants.BLUEPRINT_GENERATION_TIMEOUT,
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

    # 使用BlueprintService验证并清理蓝图（强制工作流分离）
    refined_blueprint = blueprint_service.validate_and_clean_blueprint(refined_blueprint, project_id)

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


@router.post("/{project_id}/avatar/generate")
async def generate_avatar(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """为小说生成SVG动物头像

    根据小说的类型、风格、氛围，使用LLM生成一个匹配的小动物SVG图标。

    Returns:
        dict: {
            "avatar_svg": "<svg>...</svg>",  # 完整SVG代码
            "animal": "fox",                  # 动物英文名
            "animal_cn": "狐狸"               # 动物中文名
        }
    """
    # 验证项目所有权
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 创建AvatarService并生成头像
    avatar_service = AvatarService(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    result = await avatar_service.generate_avatar(project_id, desktop_user.id)
    logger.info("项目 %s 头像生成成功: %s", project_id, result.get("animal"))

    return result


@router.delete("/{project_id}/avatar")
async def delete_avatar(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """删除小说的头像

    Returns:
        dict: {"success": True}
    """
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    avatar_service = AvatarService(session=session)
    success = await avatar_service.delete_avatar(project_id)
    await session.commit()

    logger.info("项目 %s 头像删除: success=%s", project_id, success)
    return {"success": success}
