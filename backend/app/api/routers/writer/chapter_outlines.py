"""
章节大纲管理路由

处理章节大纲的生成、删除和重新生成操作。
"""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.state_machine import ProjectStatus
from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....exceptions import (
    InvalidParameterError,
    LLMServiceError,
    PromptTemplateNotFoundError,
    ResourceNotFoundError,
)
from ....schemas.novel import (
    DeleteLatestChapterOutlinesRequest,
    GenerateChapterOutlinesByCountRequest,
    RegenerateChapterOutlineRequest,
)
from ....schemas.user import UserInDB
from ....repositories.chapter_repository import ChapterOutlineRepository, ChapterRepository
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.prompt_service import PromptService
from ....utils.json_utils import remove_think_tags, parse_llm_json_or_fail
from ....utils.prompt_helpers import ensure_prompt

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/novels/{project_id}/chapter-outlines/generate-by-count", response_model=Dict[str, Any])
async def generate_chapter_outlines_by_count(
    project_id: str,
    request: GenerateChapterOutlinesByCountRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    生成指定数量的章节大纲（增量生成，串行批量模式）

    用于长篇小说的灵活大纲管理，支持根据需要逐步生成章节大纲，
    而不需要一次性生成全部。采用串行批量生成，每批5章，确保与前文连贯。

    Args:
        project_id: 项目ID
        request: 包含count（要生成的数量）和start_from（起始章节号，可选）

    Returns:
        包含生成结果的字典，包括生成的章节号列表和总章节数
    """
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 使用Repository获取当前最大章节号
    chapter_outline_repo = ChapterOutlineRepository(session)
    all_outlines = await chapter_outline_repo.list_by_project(project_id)

    # 确定起始章节号
    if request.start_from is not None:
        start_chapter = request.start_from
    else:
        if all_outlines:
            latest_chapter_number = max(outline.chapter_number for outline in all_outlines)
            start_chapter = latest_chapter_number + 1
        else:
            start_chapter = 1

    end_chapter = start_chapter + request.count - 1

    logger.info(
        "用户 %s 请求为项目 %s 增量串行生成章节大纲，起始章节 %s，数量 %s（第 %s-%s 章）",
        desktop_user.id,
        project_id,
        start_chapter,
        request.count,
        start_chapter,
        end_chapter,
    )

    # 获取大纲提示词
    outline_prompt = ensure_prompt(await prompt_service.get_prompt("outline"), "outline")

    # 获取项目蓝图
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()

    # 串行批量生成章节大纲
    CHAPTERS_PER_BATCH = 5
    all_generated_chapters = []
    current_chapter = start_chapter

    while current_chapter <= end_chapter:
        # 计算当前批次的章节范围
        batch_end = min(current_chapter + CHAPTERS_PER_BATCH - 1, end_chapter)
        batch_count = batch_end - current_chapter + 1

        logger.info(
            "开始生成第 %d-%d 章（共 %d 章，批次 %d/%d）",
            current_chapter, batch_end, batch_count,
            (current_chapter - start_chapter) // CHAPTERS_PER_BATCH + 1,
            (request.count + CHAPTERS_PER_BATCH - 1) // CHAPTERS_PER_BATCH
        )

        # 获取前面已生成的章节（包括本次生成前已存在的 + 本次已生成的）
        fresh_outlines = await chapter_outline_repo.list_by_project(project_id)
        previous_chapters = [
            {
                "chapter_number": outline.chapter_number,
                "title": outline.title,
                "summary": outline.summary,
            }
            for outline in fresh_outlines
            if outline.chapter_number < current_chapter
        ]
        previous_chapters.sort(key=lambda x: x["chapter_number"])

        # 准备LLM请求payload
        payload = {
            "novel_blueprint": blueprint_dict,
            "wait_to_generate": {
                "start_chapter": current_chapter,
                "num_chapters": batch_count,
            },
        }

        # 如果有前面的章节，加入上下文
        if previous_chapters:
            payload["previous_chapters"] = previous_chapters
            payload["context_note"] = f"前面已生成 {len(previous_chapters)} 章，请确保与前文保持连贯、设定一致、剧情承接自然。"

        # 调用LLM生成当前批次的大纲
        logger.info("调用LLM生成第 %d-%d 章的章节大纲", current_chapter, batch_end)
        response = await llm_service.get_llm_response(
            system_prompt=outline_prompt,
            conversation_history=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
            temperature=settings.llm_temp_outline,
            user_id=desktop_user.id,
            timeout=360.0,
        )

        # 解析LLM响应
        response_cleaned = remove_think_tags(response)
        data = parse_llm_json_or_fail(
            response_cleaned,
            f"项目{project_id}第{current_chapter}-{batch_end}章的章节大纲生成失败"
        )

        # 保存当前批次的章节大纲
        batch_chapters = data.get("chapters", [])
        if not batch_chapters:
            raise LLMServiceError("LLM未返回有效的章节大纲")

        for item in batch_chapters:
            chapter_number = item.get("chapter_number")
            if not chapter_number:
                continue

            await chapter_outline_repo.upsert_outline(
                project_id=project_id,
                chapter_number=chapter_number,
                title=item.get("title", ""),
                summary=item.get("summary", ""),
            )
            all_generated_chapters.append(chapter_number)

        logger.info(
            "成功生成第 %d-%d 章大纲（本批 %d 章）",
            current_chapter, batch_end, len(batch_chapters)
        )

        # 移动到下一批
        current_chapter = batch_end + 1

    # 提交所有章节
    await session.commit()
    logger.info("项目 %s 串行增量生成完成，共生成 %d 章大纲", project_id, len(all_generated_chapters))

    # 使用Repository获取当前总章节数
    total_chapters = await chapter_outline_repo.count_by_project(project_id)

    return {
        "message": f"成功生成{len(all_generated_chapters)}章大纲",
        "generated_chapters": all_generated_chapters,
        "total_chapters": total_chapters,
    }


@router.delete("/novels/{project_id}/chapter-outlines/delete-latest", response_model=Dict[str, Any])
async def delete_latest_chapter_outlines(
    project_id: str,
    request: DeleteLatestChapterOutlinesRequest,
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    删除最新的N章大纲

    用于灵活调整章节大纲，当用户对最新生成的章节大纲不满意时，
    可以删除后重新生成。

    Args:
        project_id: 项目ID
        request: 包含count（要删除的数量）

    Returns:
        包含删除结果的字典，包括删除的章节号列表
    """
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 使用Repository获取当前最大章节号
    chapter_outline_repo = ChapterOutlineRepository(session)
    all_outlines = await chapter_outline_repo.list_by_project(project_id)

    if not all_outlines:
        raise ResourceNotFoundError("章节大纲", project_id)

    max_chapter_number = max(outline.chapter_number for outline in all_outlines)

    # 验证删除数量
    if request.count > len(all_outlines):
        raise InvalidParameterError(
            f"删除数量({request.count})超过现有章节数({len(all_outlines)})"
        )

    # 计算要删除的章节范围
    start_delete = max_chapter_number - request.count + 1
    end_delete = max_chapter_number
    deleted_chapters = list(range(start_delete, end_delete + 1))

    logger.info(
        "用户 %s 请求删除项目 %s 的最新 %d 章大纲（第 %d-%d 章）",
        desktop_user.id,
        project_id,
        request.count,
        start_delete,
        end_delete,
    )

    # 批量检查这些章节是否已有生成的内容（优化：一次查询代替N次）
    chapter_repo = ChapterRepository(session)
    chapters = await chapter_repo.get_by_project_and_numbers(project_id, deleted_chapters)
    chapters_with_content = [
        chapter.chapter_number
        for chapter in chapters
        if chapter.selected_version
    ]

    if chapters_with_content:
        logger.warning(
            "项目 %s 章节 %s 已有生成内容，将执行级联删除（删除章节内容、向量库数据和大纲）",
            project_id,
            chapters_with_content,
        )

    # 级联删除：删除向量库数据
    from ....services.vector_store_service import VectorStoreService
    from ....services.chapter_ingest_service import ChapterIngestionService

    # 使用try-except包裹向量库初始化，避免在RAG禁用时失败
    vector_store = None
    try:
        vector_store = VectorStoreService()
    except RuntimeError as exc:
        logger.warning("向量库初始化失败，跳过向量数据删除: %s", exc)

    if vector_store:
        ingest_service = ChapterIngestionService(llm_service=llm_service, vector_store=vector_store)

        try:
            await ingest_service.delete_chapters(project_id, deleted_chapters)
            logger.info("项目 %s 成功删除章节向量库数据: %s", project_id, deleted_chapters)
        except Exception as exc:
            logger.warning("删除章节向量库数据失败，但继续执行: %s", exc)
    else:
        logger.info("向量库未启用，跳过向量数据删除")

    # 级联删除：删除Chapter记录（包括版本、评审等关联数据）和ChapterOutline
    # 使用NovelService的delete_chapters方法，它会处理所有级联删除
    await novel_service.delete_chapters(project_id, deleted_chapters)
    await session.commit()

    logger.info("项目 %s 成功级联删除 %d 章（包括大纲、章节内容和向量数据）", project_id, len(deleted_chapters))

    # 使用Repository获取剩余章节数
    remaining_chapters = await chapter_outline_repo.count_by_project(project_id)

    # 根据是否有章节内容，返回不同的消息
    if chapters_with_content:
        message = f"成功级联删除{len(deleted_chapters)}章（包括大纲、章节内容和向量数据）"
        warning = f"已删除章节 {chapters_with_content} 的所有数据（内容、向量、大纲）"
    else:
        message = f"成功删除{len(deleted_chapters)}章大纲"
        warning = None

    return {
        "message": message,
        "deleted_chapters": deleted_chapters,
        "remaining_chapters": remaining_chapters,
        "warning": warning,
    }


@router.post("/novels/{project_id}/chapter-outlines/{chapter_number}/regenerate", response_model=Dict[str, Any])
async def regenerate_chapter_outline(
    project_id: str,
    chapter_number: int,
    request: RegenerateChapterOutlineRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    重新生成指定章节的大纲（串行生成原则）

    支持使用可选的优化提示词来引导AI生成更符合预期的章节大纲。
    会自动包含前面章节的上下文，确保重新生成的大纲与前文保持连贯。

    串行生成原则：
    - 只能重新生成最后一章（因为它后面没有依赖它的章节）
    - 如果需要重新生成非最后一章，必须设置cascade_delete=True，
      这将级联删除该章及之后的所有章节大纲

    Args:
        project_id: 项目ID
        chapter_number: 要重新生成的章节号
        request: 包含prompt（优化提示词，可选）和cascade_delete（是否级联删除）

    Returns:
        包含重新生成的章节大纲，以及可能的级联删除信息
    """
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    logger.info(
        "用户 %s 请求重新生成项目 %s 第 %s 章大纲，提示词: %s，级联删除: %s",
        desktop_user.id,
        project_id,
        chapter_number,
        request.prompt or "无",
        request.cascade_delete,
    )

    # 使用Repository获取当前章节大纲
    chapter_outline_repo = ChapterOutlineRepository(session)
    existing_outline = await chapter_outline_repo.get_by_project_and_number(project_id, chapter_number)

    if not existing_outline:
        raise ResourceNotFoundError("章节大纲", f"项目 {project_id} 第 {chapter_number} 章")

    # 获取所有章节大纲
    all_outlines = await chapter_outline_repo.list_by_project(project_id)

    # 找到最大章节号
    max_chapter_number = max(outline.chapter_number for outline in all_outlines)

    # 串行生成原则检查
    cascade_deleted_count = 0
    if chapter_number < max_chapter_number:
        if not request.cascade_delete:
            # 不是最后一章且没有设置级联删除，返回错误
            raise InvalidParameterError(
                f"串行生成原则：只能重新生成最后一章（当前最后一章为第{max_chapter_number}章）。"
                f"如需重新生成第{chapter_number}章，请设置cascade_delete=True以级联删除第{chapter_number}章之后的所有章节大纲。"
            )
        else:
            # 级联删除：删除该章节之后的所有章节大纲
            logger.info(
                "串行生成原则：级联删除第 %d 章之后的所有章节大纲（第 %d-%d 章）",
                chapter_number, chapter_number + 1, max_chapter_number
            )
            cascade_deleted_count = await chapter_outline_repo.delete_from_chapter(
                project_id, chapter_number + 1
            )
            logger.info("已删除 %d 章大纲", cascade_deleted_count)

    # 获取前面已生成的章节（用于上下文）
    # 注意：如果刚进行了级联删除，需要重新获取
    all_outlines_fresh = await chapter_outline_repo.list_by_project(project_id)
    previous_chapters = [
        {
            "chapter_number": outline.chapter_number,
            "title": outline.title,
            "summary": outline.summary,
        }
        for outline in all_outlines_fresh
        if outline.chapter_number < chapter_number
    ]
    previous_chapters.sort(key=lambda x: x["chapter_number"])

    # 获取大纲提示词
    outline_prompt = ensure_prompt(await prompt_service.get_prompt("outline"), "outline")

    # 获取项目蓝图
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint_dict = project_schema.blueprint.model_dump()

    # 准备LLM请求payload
    payload = {
        "novel_blueprint": blueprint_dict,
        "wait_to_generate": {
            "start_chapter": chapter_number,
            "num_chapters": 1,
        },
        "current_outline": {
            "title": existing_outline.title,
            "summary": existing_outline.summary,
        },
    }

    # 如果有前面的章节，加入上下文
    if previous_chapters:
        payload["previous_chapters"] = previous_chapters
        payload["context_note"] = f"前面已生成 {len(previous_chapters)} 章，请确保重新生成的大纲与前文保持连贯、设定一致、剧情承接自然。"

    # 如果有优化提示词，添加到payload
    if request.prompt:
        payload["optimization_prompt"] = request.prompt

    # 调用LLM重新生成大纲
    response = await llm_service.get_llm_response(
        system_prompt=outline_prompt,
        conversation_history=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        temperature=settings.llm_temp_outline,
        user_id=desktop_user.id,
        timeout=180.0,
    )

    # 解析LLM响应
    response_cleaned = remove_think_tags(response)
    data = parse_llm_json_or_fail(
        response_cleaned,
        f"项目{project_id}第{chapter_number}章的章节大纲重新生成失败"
    )

    # 更新章节大纲
    chapters = data.get("chapters", [])
    if not chapters:
        raise LLMServiceError("LLM未返回章节大纲")

    new_outline_data = chapters[0]
    existing_outline.title = new_outline_data.get("title", existing_outline.title)
    existing_outline.summary = new_outline_data.get("summary", existing_outline.summary)

    await session.commit()
    logger.info("项目 %s 第 %s 章大纲已重新生成（包含前文上下文）", project_id, chapter_number)

    result = {
        "message": f"第{chapter_number}章大纲已重新生成",
        "chapter_outline": {
            "chapter_number": chapter_number,
            "title": existing_outline.title,
            "summary": existing_outline.summary,
        },
    }

    # 如果有级联删除，添加相关信息
    if cascade_deleted_count > 0:
        result["cascade_deleted"] = {
            "count": cascade_deleted_count,
            "from_chapter": chapter_number + 1,
            "to_chapter": max_chapter_number,
            "message": f"根据串行生成原则，已删除第{chapter_number + 1}-{max_chapter_number}章的大纲"
        }

    return result


