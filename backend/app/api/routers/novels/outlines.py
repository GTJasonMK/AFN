"""
章节大纲生成路由

处理章节大纲的生成操作（短篇小说一次性生成全部章节大纲）。
"""

import json
import logging

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
from ....utils.json_utils import (
    remove_think_tags,
    parse_llm_json_or_fail,
)
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
    if not project_schema.blueprint:
        raise BlueprintNotReadyError(project_id)

    blueprint = project_schema.blueprint

    # 检查是否为短篇流程（不需要部分大纲）
    if blueprint.needs_part_outlines:
        raise InvalidParameterError(
            "该项目为长篇小说，请先生成部分大纲，再分批生成章节大纲"
        )

    total_chapters = blueprint.total_chapters or 0
    if total_chapters == 0:
        raise InvalidParameterError("蓝图未设置总章节数")

    # 检查是否已有章节大纲
    if blueprint.chapter_outline and len(blueprint.chapter_outline) > 0:
        logger.info("项目 %s 已有 %d 个章节大纲，跳过生成", project_id, len(blueprint.chapter_outline))
        raise ConflictError(
            f"章节大纲已存在（共{len(blueprint.chapter_outline)}章），如需重新生成请先删除现有大纲"
        )

    # 构建蓝图JSON（用于LLM上下文）
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
        "chapter_outline": [],  # 当前为空，等待生成
    }

    # 获取系统提示词
    system_prompt = ensure_prompt(await prompt_service.get_prompt("outline"), "outline")

    # 串行生成章节大纲（分批生成）
    CHAPTERS_PER_BATCH = 5
    all_chapters_data = []
    chapter_outline_repo = ChapterOutlineRepository(session)
    current_chapter = 1

    logger.info("项目 %s 将串行生成 %d 章大纲，每批 %d 章", project_id, total_chapters, CHAPTERS_PER_BATCH)

    while current_chapter <= total_chapters:
        # 计算当前批次的章节范围
        batch_end = min(current_chapter + CHAPTERS_PER_BATCH - 1, total_chapters)
        batch_count = batch_end - current_chapter + 1

        logger.info(
            "开始生成第 %d-%d 章（共 %d 章，批次 %d/%d）",
            current_chapter, batch_end, batch_count,
            (current_chapter - 1) // CHAPTERS_PER_BATCH + 1,
            (total_chapters + CHAPTERS_PER_BATCH - 1) // CHAPTERS_PER_BATCH
        )

        # 获取前面已生成的章节（用于上下文）
        previous_chapters = [
            {
                "chapter_number": ch["chapter_number"],
                "title": ch.get("title", ""),
                "summary": ch.get("summary", ""),
            }
            for ch in all_chapters_data
        ]

        # 构建用户输入（包含前文章节）
        payload = {
            "novel_blueprint": blueprint_context,
            "wait_to_generate": {
                "start_chapter": current_chapter,
                "num_chapters": batch_count
            },
        }

        # 如果有前文章节，加入上下文
        if previous_chapters:
            payload["previous_chapters"] = previous_chapters
            payload["context_note"] = f"前面已生成 {len(previous_chapters)} 章，请确保与前文保持连贯、设定一致、剧情承接自然。"

        user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)

        # 调用LLM生成当前批次的章节大纲
        logger.info("调用LLM生成第 %d-%d 章的章节大纲", current_chapter, batch_end)
        response = await llm_service.get_llm_response(
            system_prompt=system_prompt,
            conversation_history=[{"role": "user", "content": user_prompt}],
            temperature=settings.llm_temp_outline,
            user_id=desktop_user.id,
            timeout=180.0,
            max_tokens=None,
        )

        # 解析章节大纲JSON
        response_cleaned = remove_think_tags(response)
        result = parse_llm_json_or_fail(
            response_cleaned,
            f"项目{project_id}的章节大纲生成失败"
        )

        chapters_data = result.get("chapters", [])
        if not chapters_data:
            raise LLMServiceError("LLM未返回有效的章节大纲")

        # 保存当前批次的章节大纲到数据库
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

        # 移动到下一批
        current_chapter = batch_end + 1

    # 提交所有章节
    await session.commit()

    # 更新项目状态为章节大纲完成
    await novel_service.transition_project_status(project, ProjectStatus.CHAPTER_OUTLINES_READY.value)

    logger.info("项目 %s 章节大纲串行生成完成，共 %d 章", project_id, len(all_chapters_data))

    return {
        "message": "章节大纲生成完成",
        "total_chapters": len(all_chapters_data),
        "status": ProjectStatus.CHAPTER_OUTLINES_READY.value,
    }
