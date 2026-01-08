"""
章节大纲生成路由

处理章节大纲的生成操作（短篇小说一次性生成全部章节大纲）。
支持小说项目和编程项目（功能设计大纲）。
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.constants import LLMConstants
from ....core.state_machine import ProjectStatus
from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....db.session import get_session
from ....exceptions import (
    PromptTemplateNotFoundError,
    BlueprintNotReadyError,
    InvalidParameterError,
    ConflictError,
    LLMServiceError,
)
from ....schemas.user import UserInDB
from ....repositories.chapter_repository import ChapterOutlineRepository
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.prompt_service import PromptService
from ....services.project_factory import ProjectTypeConfig, ProjectStage
from ....utils.json_utils import parse_llm_json_or_fail
from ....utils.prompt_helpers import ensure_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/chapter-outlines/generate")
async def generate_chapter_outlines(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
):
    """为短篇小说串行生成全部章节大纲

    改进：采用串行生成，每次生成一小批章节（默认5章），每次都能看到前面
    已生成章节的实际内容，确保设定连贯、剧情承接、角色发展一致。

    适用于章节数不超过part_outline_threshold配置的项目。
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    logger.info("项目 %s 开始串行生成章节大纲", project_id)

    # 检查蓝图是否存在
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint = project_schema.blueprint
    if not blueprint:
        raise BlueprintNotReadyError(project_id)

    total_items = blueprint.total_chapters or 0
    needs_phased = blueprint.needs_part_outlines
    existing_outlines = blueprint.chapter_outline

    # 检查是否为短篇流程（不需要分阶段）
    if needs_phased:
        raise InvalidParameterError("该项目需要分阶段设计，请先生成部分大纲")

    if total_items == 0:
        raise InvalidParameterError("蓝图未设置总章节数")

    # 检查是否已有大纲
    if existing_outlines and len(existing_outlines) > 0:
        logger.info("项目 %s 已有 %d 个章节大纲，跳过生成", project_id, len(existing_outlines))
        raise ConflictError(
            f"章节大纲已存在（共{len(existing_outlines)}个），如需重新生成请先删除现有大纲"
        )

    # 构建蓝图上下文
    blueprint_context = {
        "title": blueprint.title,
        "target_audience": blueprint.target_audience,
        "genre": blueprint.genre,
        "style": blueprint.style,
        "tone": blueprint.tone,
        "one_sentence_summary": blueprint.one_sentence_summary,
        "full_synopsis": blueprint.full_synopsis,
        "world_setting": blueprint.world_setting,
        "characters": blueprint.characters,
        "relationships": blueprint.relationships,
        "chapter_outline": [],  # 等待生成
    }

    # 获取系统提示词
    prompt_name = ProjectTypeConfig.get_prompt_name("novel", ProjectStage.CHAPTER_OUTLINE)
    system_prompt = ensure_prompt(await prompt_service.get_prompt(prompt_name), prompt_name)

    # 串行生成大纲（分批生成）
    ITEMS_PER_BATCH = 5
    all_items_data = []
    chapter_outline_repo = ChapterOutlineRepository(session)
    current_item = 1
    item_name = "章节"  # 用于日志和错误消息

    logger.info("项目 %s 将串行生成 %d 个章节大纲，每批 %d 个", project_id, total_items, ITEMS_PER_BATCH)

    while current_item <= total_items:
        # 计算当前批次的范围
        batch_end = min(current_item + ITEMS_PER_BATCH - 1, total_items)
        batch_count = batch_end - current_item + 1

        logger.info(
            "开始生成第 %d-%d 个章节（共 %d 个，批次 %d/%d）",
            current_item, batch_end, batch_count,
            (current_item - 1) // ITEMS_PER_BATCH + 1,
            (total_items + ITEMS_PER_BATCH - 1) // ITEMS_PER_BATCH
        )

        # 获取前面已生成的项目（用于上下文）
        previous_items = [
            {
                "chapter_number": ch["chapter_number"],
                "title": ch.get("title", ""),
                "summary": ch.get("summary", ""),
            }
            for ch in all_items_data
        ]

        # 构建用户输入
        payload = {
            "novel_blueprint": blueprint_context,
            "wait_to_generate": {
                "start_chapter": current_item,
                "num_chapters": batch_count
            },
        }
        if previous_items:
            payload["previous_chapters"] = previous_items
            payload["context_note"] = f"前面已生成 {len(previous_items)} 章，请确保与前文保持连贯、设定一致、剧情承接自然。"

        user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

        # 调用LLM生成当前批次的大纲
        logger.info("调用LLM生成第 %d-%d 个%s的大纲", current_item, batch_end, item_name)
        response = await llm_service.get_llm_response(
            system_prompt=system_prompt,
            conversation_history=[{"role": "user", "content": user_prompt}],
            temperature=settings.llm_temp_outline,
            user_id=desktop_user.id,
            timeout=LLMConstants.SUMMARY_GENERATION_TIMEOUT,
            max_tokens=settings.llm_max_tokens_outline,
        )

        # 解析大纲JSON
        result = parse_llm_json_or_fail(
            response,
            f"项目{project_id}的{item_name}大纲生成失败"
        )

        # 根据项目类型获取返回数据
        items_data = result.get("chapters", []) or result.get("features", [])
        if not items_data:
            raise LLMServiceError(f"LLM未返回有效的{item_name}大纲")

        # 保存当前批次的大纲到数据库
        for item_data in items_data:
            item_number = item_data.get("chapter_number") or item_data.get("feature_number")
            await chapter_outline_repo.upsert_outline(
                project_id=project_id,
                chapter_number=item_number,
                title=item_data.get("title") or item_data.get("feature_name", ""),
                summary=item_data.get("summary") or item_data.get("description", ""),
            )
            # 规范化保存的数据
            all_items_data.append({
                "chapter_number": item_number,
                "title": item_data.get("title") or item_data.get("feature_name", ""),
                "summary": item_data.get("summary") or item_data.get("description", ""),
            })

        logger.info(
            "成功生成第 %d-%d 个%s大纲（本批 %d 个）",
            current_item, batch_end, item_name, len(items_data)
        )

        # 移动到下一批
        current_item = batch_end + 1

    # 提交所有大纲
    await session.commit()

    # 更新项目状态为大纲完成
    await novel_service.transition_project_status(project, ProjectStatus.CHAPTER_OUTLINES_READY.value)

    # 自动入库：章节大纲数据
    from ....services.novel_rag import trigger_chapter_outline_ingestion
    await trigger_chapter_outline_ingestion(
        project_id, desktop_user.id, vector_store, llm_service
    )

    logger.info("项目 %s %s大纲串行生成完成，共 %d 个", project_id, item_name, len(all_items_data))

    return {
        "message": f"{item_name}大纲生成完成",
        "total_items": len(all_items_data),
        "status": ProjectStatus.CHAPTER_OUTLINES_READY.value,
    }


@router.post("/{project_id}/chapter-outlines/generate-stream")
async def generate_chapter_outlines_stream(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
):
    """为短篇小说串行生成全部章节大纲（SSE流式返回进度）

    与generate_chapter_outlines相同的逻辑，但通过SSE返回每批次的进度。

    事件类型：
    - progress: 批次进度 {"current_batch", "total_batches", "generated_count", "total_count", "current_range", "status"}
    - complete: 完成 {"message", "total_chapters"}
    - error: 错误 {"message"}
    """
    from fastapi.responses import StreamingResponse
    from ....utils.sse_helpers import sse_event, create_sse_response
    from ....utils.exception_helpers import get_safe_error_message
    import math

    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    logger.info("项目 %s 开始串行生成章节大纲（SSE模式）", project_id)

    # 检查蓝图是否存在
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    if not project_schema.blueprint:
        raise BlueprintNotReadyError(project_id)

    blueprint = project_schema.blueprint

    # 检查是否为短篇流程
    if blueprint.needs_part_outlines:
        raise InvalidParameterError(
            "该项目为长篇小说，请先生成部分大纲，再分批生成章节大纲"
        )

    total_chapters = blueprint.total_chapters or 0
    if total_chapters == 0:
        raise InvalidParameterError("蓝图未设置总章节数")

    # 检查是否已有章节大纲
    if blueprint.chapter_outline and len(blueprint.chapter_outline) > 0:
        raise ConflictError(
            f"章节大纲已存在（共{len(blueprint.chapter_outline)}章），如需重新生成请先删除现有大纲"
        )

    # 构建蓝图上下文
    blueprint_context = {
        "title": blueprint.title,
        "target_audience": blueprint.target_audience,
        "genre": blueprint.genre,
        "style": blueprint.style,
        "tone": blueprint.tone,
        "one_sentence_summary": blueprint.one_sentence_summary,
        "full_synopsis": blueprint.full_synopsis,
        "world_setting": blueprint.world_setting,
        "characters": blueprint.characters,
        "relationships": blueprint.relationships,
        "chapter_outline": [],
    }

    # 获取系统提示词
    system_prompt = ensure_prompt(await prompt_service.get_prompt("outline"), "outline")

    # 计算总批次数
    CHAPTERS_PER_BATCH = 5
    total_batches = math.ceil(total_chapters / CHAPTERS_PER_BATCH)

    async def event_generator():
        try:
            all_chapters_data = []
            chapter_outline_repo = ChapterOutlineRepository(session)
            current_chapter = 1
            current_batch = 0

            # 发送开始事件
            yield sse_event("progress", {
                "current_batch": 0,
                "total_batches": total_batches,
                "generated_count": 0,
                "total_count": total_chapters,
                "current_range": f"准备生成第1-{total_chapters}章",
                "status": "starting"
            })

            while current_chapter <= total_chapters:
                current_batch += 1
                batch_end = min(current_chapter + CHAPTERS_PER_BATCH - 1, total_chapters)
                batch_count = batch_end - current_chapter + 1

                logger.info(
                    "开始生成第 %d-%d 章（批次 %d/%d）",
                    current_chapter, batch_end, current_batch, total_batches
                )

                # 发送批次开始进度
                yield sse_event("progress", {
                    "current_batch": current_batch,
                    "total_batches": total_batches,
                    "generated_count": len(all_chapters_data),
                    "total_count": total_chapters,
                    "current_range": f"正在生成第{current_chapter}-{batch_end}章",
                    "status": "generating"
                })

                # 获取前面已生成的章节
                previous_chapters = [
                    {
                        "chapter_number": ch["chapter_number"],
                        "title": ch.get("title", ""),
                        "summary": ch.get("summary", "")[:200] + "..." if len(ch.get("summary", "") or "") > 200 else ch.get("summary", ""),
                    }
                    for ch in all_chapters_data
                ]

                # 上下文优化：最多保留最近15章的详细信息
                MAX_RECENT_CHAPTERS = 15
                if len(previous_chapters) > MAX_RECENT_CHAPTERS:
                    early_chapters = [
                        {"chapter_number": ch["chapter_number"], "title": ch["title"]}
                        for ch in previous_chapters[:-MAX_RECENT_CHAPTERS]
                    ]
                    recent_chapters = previous_chapters[-MAX_RECENT_CHAPTERS:]
                    context_previous = {
                        "early_chapters_titles": early_chapters,
                        "recent_chapters": recent_chapters,
                    }
                    context_note = f"前面已生成 {len(previous_chapters)} 章。最近{MAX_RECENT_CHAPTERS}章提供详细摘要。请确保与前文保持连贯、设定一致、剧情承接自然。"
                else:
                    context_previous = previous_chapters
                    context_note = f"前面已生成 {len(previous_chapters)} 章，请确保与前文保持连贯、设定一致、剧情承接自然。" if previous_chapters else None

                payload = {
                    "novel_blueprint": blueprint_context,
                    "wait_to_generate": {
                        "start_chapter": current_chapter,
                        "num_chapters": batch_count
                    },
                }

                if context_previous:
                    payload["previous_chapters"] = context_previous
                if context_note:
                    payload["context_note"] = context_note

                user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

                # 调用LLM
                response = await llm_service.get_llm_response(
                    system_prompt=system_prompt,
                    conversation_history=[{"role": "user", "content": user_prompt}],
                    temperature=settings.llm_temp_outline,
                    user_id=desktop_user.id,
                    timeout=LLMConstants.SUMMARY_GENERATION_TIMEOUT,
                    max_tokens=settings.llm_max_tokens_outline,
                )

                result = parse_llm_json_or_fail(
                    response,
                    f"项目{project_id}的章节大纲生成失败"
                )

                chapters_data = result.get("chapters", [])
                if not chapters_data:
                    raise LLMServiceError("LLM未返回有效的章节大纲")

                # 保存章节大纲
                for chapter_data in chapters_data:
                    await chapter_outline_repo.upsert_outline(
                        project_id=project_id,
                        chapter_number=chapter_data.get("chapter_number"),
                        title=chapter_data.get("title", ""),
                        summary=chapter_data.get("summary", ""),
                    )
                    all_chapters_data.append(chapter_data)

                logger.info(
                    "成功生成第 %d-%d 章大纲（本批 %d 章）",
                    current_chapter, batch_end, len(chapters_data)
                )

                # 增量提交
                await session.commit()

                # 发送批次完成进度
                yield sse_event("progress", {
                    "current_batch": current_batch,
                    "total_batches": total_batches,
                    "generated_count": len(all_chapters_data),
                    "total_count": total_chapters,
                    "current_range": f"已完成第{current_chapter}-{batch_end}章",
                    "status": "batch_done"
                })

                current_chapter = batch_end + 1

            # 更新项目状态
            updated_project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
            await novel_service.transition_project_status(updated_project, ProjectStatus.CHAPTER_OUTLINES_READY.value)

            # 自动入库：章节大纲数据（在SSE生成器内部触发）
            from ....services.novel_rag import trigger_chapter_outline_ingestion
            await trigger_chapter_outline_ingestion(
                project_id, desktop_user.id, vector_store, llm_service
            )

            logger.info("项目 %s 章节大纲串行生成完成（SSE模式），共 %d 章", project_id, len(all_chapters_data))

            # 发送完成事件
            yield sse_event("complete", {
                "message": f"成功生成{len(all_chapters_data)}章大纲",
                "total_chapters": len(all_chapters_data),
            })

        except Exception as exc:
            logger.exception("章节大纲生成失败: %s", exc)
            safe_message = get_safe_error_message(exc, "章节大纲生成失败，请稍后重试")
            yield sse_event("error", {
                "message": safe_message,
                "saved_count": len(all_chapters_data) if 'all_chapters_data' in locals() else 0,
            })

    return create_sse_response(event_generator())
