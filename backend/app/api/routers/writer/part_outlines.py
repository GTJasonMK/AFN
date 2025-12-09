"""
部分大纲管理路由

处理长篇小说的部分大纲生成、批量生成和进度查询。
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_vector_store,
)
from ....core.state_machine import ProjectStatus
from ....db.session import get_session
from ....exceptions import (
    BlueprintNotReadyError,
    InvalidParameterError,
    ResourceNotFoundError,
    DatabaseError,
)
from ....schemas.novel import (
    BatchGenerateChaptersRequest,
    GeneratePartChaptersRequest,
    GeneratePartOutlinesRequest,
    NovelProject as NovelProjectSchema,
    PartOutlineGenerationProgress,
    RegeneratePartOutlinesRequest,
)
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService
from ....services.part_outline_service import PartOutlineService
from ....services.vector_store_service import VectorStoreService
from ....repositories.chapter_repository import ChapterOutlineRepository

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/novels/{project_id}/part-outlines/regenerate", response_model=PartOutlineGenerationProgress)
async def regenerate_part_outlines(
    project_id: str,
    request: RegeneratePartOutlinesRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> PartOutlineGenerationProgress:
    """
    重新生成所有部分大纲（串行生成原则）

    支持使用可选的优化提示词来引导AI生成更优质的部分大纲结构。
    会覆盖原有的所有部分大纲，并删除所有已生成的章节大纲。

    串行生成原则：部分大纲变更会影响后续所有章节大纲，因此必须级联删除。

    Args:
        project_id: 项目ID
        request: 包含prompt（优化提示词，可选）

    Returns:
        新的部分大纲生成进度
    """
    logger.info(
        "用户 %s 请求重新生成项目 %s 的所有部分大纲，提示词: %s",
        desktop_user.id,
        project_id,
        request.prompt or "无",
    )

    part_service = PartOutlineService(session)
    chapter_outline_repo = ChapterOutlineRepository(session)

    # 获取项目信息
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint = project_schema.blueprint

    if not blueprint:
        raise BlueprintNotReadyError(project_id)

    # 检查是否需要部分大纲
    if not blueprint.needs_part_outlines:
        raise InvalidParameterError("该项目不需要部分大纲（章节数未超过阈值）")

    # 获取当前配置
    total_chapters = blueprint.total_chapters or 0
    chapters_per_part = blueprint.chapters_per_part or 25

    if total_chapters == 0:
        raise InvalidParameterError("项目总章节数未设置")

    # 串行生成原则：删除所有章节大纲
    # 因为部分大纲变更，基于旧部分大纲生成的章节大纲已经过时
    logger.info("根据串行生成原则，删除项目 %s 的所有章节大纲", project_id)
    await chapter_outline_repo.delete_by_project(project_id)

    # 调用部分大纲生成服务，并传入优化提示词
    # 重新生成时跳过状态更新，避免状态机错误
    result = await part_service.generate_part_outlines(
        project_id=project_id,
        user_id=desktop_user.id,
        total_chapters=total_chapters,
        chapters_per_part=chapters_per_part,
        optimization_prompt=request.prompt,
        skip_status_update=True,  # 重新生成时不更新项目状态
    )
    await session.commit()

    logger.info("项目 %s 部分大纲重新生成完成，已删除所有旧章节大纲", project_id)
    return result


@router.post("/novels/{project_id}/part-outlines/regenerate-last", response_model=PartOutlineGenerationProgress)
async def regenerate_last_part_outline(
    project_id: str,
    request: RegeneratePartOutlinesRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> PartOutlineGenerationProgress:
    """
    重新生成最后一个部分大纲（串行生成原则）

    只允许重新生成最后一个部分，因为它后面没有依赖它的部分。
    会删除该部分对应的章节大纲。

    串行生成原则：只能重新生成最后一个，避免影响后续已生成的内容。

    Args:
        project_id: 项目ID
        request: 包含prompt（优化提示词，可选）

    Returns:
        更新后的部分大纲生成进度
    """
    logger.info(
        "用户 %s 请求重新生成项目 %s 的最后一个部分大纲，提示词: %s",
        desktop_user.id,
        project_id,
        request.prompt or "无",
    )

    part_service = PartOutlineService(session)
    chapter_outline_repo = ChapterOutlineRepository(session)

    # 获取项目信息
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint = project_schema.blueprint

    if not blueprint:
        raise BlueprintNotReadyError(project_id)

    # 检查是否需要部分大纲
    if not blueprint.needs_part_outlines:
        raise InvalidParameterError("该项目不需要部分大纲（章节数未超过阈值）")

    # 获取所有部分大纲
    all_parts = await part_service.repo.get_by_project_id(project_id)
    if not all_parts:
        raise ResourceNotFoundError("部分大纲", project_id)

    # 找到最后一个部分
    last_part = max(all_parts, key=lambda p: p.part_number)
    last_part_number = last_part.part_number

    logger.info(
        "项目 %s 共有 %d 个部分，将重新生成最后一个（第 %d 部分）",
        project_id, len(all_parts), last_part_number
    )

    # 删除最后一个部分对应的章节大纲
    logger.info(
        "删除第 %d 部分的章节大纲（第 %d-%d 章）",
        last_part_number, last_part.start_chapter, last_part.end_chapter
    )
    await chapter_outline_repo.delete_from_chapter(project_id, last_part.start_chapter)

    # 删除最后一个部分大纲
    await part_service.repo.delete(last_part)

    # 获取前面的部分（用于串行生成上下文）
    previous_parts = [p for p in all_parts if p.part_number < last_part_number]

    # 重新生成最后一个部分
    from ....core.constants import LLMConstants
    system_prompt = await part_service.prompt_service.get_prompt("part_outline")

    world_setting, full_synopsis, characters = part_service._prepare_blueprint_data(
        await novel_service.ensure_project_owner(project_id, desktop_user.id)
    )

    total_chapters = blueprint.total_chapters or 0
    chapters_per_part = blueprint.chapters_per_part or 25
    total_parts = len(all_parts)

    user_prompt = part_service.prompt_builder.build_part_outline_prompt(
        total_chapters=total_chapters,
        chapters_per_part=chapters_per_part,
        total_parts=total_parts,
        world_setting=world_setting,
        characters=characters,
        full_synopsis=full_synopsis,
        current_part_number=last_part_number,
        previous_parts=previous_parts,
        optimization_prompt=request.prompt,
    )

    response = await part_service.llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_prompt}],
        temperature=LLMConstants.BLUEPRINT_TEMPERATURE,
        user_id=desktop_user.id,
        response_format="json_object",
        timeout=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
    )

    # 解析并保存新的最后一个部分
    part_data = part_service._parse_single_part_outline(response, last_part_number)
    new_part = part_service._create_single_part_outline_model(project_id, part_data)
    await part_service.repo.add(new_part)

    await session.commit()

    logger.info("项目 %s 最后一个部分大纲重新生成完成", project_id)

    # 返回更新后的进度
    updated_parts = await part_service.repo.get_by_project_id(project_id)
    return PartOutlineGenerationProgress(
        parts=[part_service._to_schema(p) for p in updated_parts],
        total_parts=len(updated_parts),
        completed_parts=len(updated_parts),
        status="completed",
    )


@router.post("/novels/{project_id}/part-outlines/{part_number}/regenerate", response_model=PartOutlineGenerationProgress)
async def regenerate_specific_part_outline(
    project_id: str,
    part_number: int,
    request: RegeneratePartOutlinesRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> PartOutlineGenerationProgress:
    """
    重新生成指定部分大纲（串行生成原则）

    支持重新生成任意指定的部分大纲。

    串行生成原则：
    - 只能重新生成最后一个部分（因为它后面没有依赖它的部分）
    - 如果需要重新生成非最后一个部分，必须设置cascade_delete=True，
      这将级联删除该部分及之后的所有部分大纲和对应的章节大纲

    Args:
        project_id: 项目ID
        part_number: 要重新生成的部分编号
        request: 包含prompt（优化提示词，可选）和cascade_delete（是否级联删除）

    Returns:
        更新后的部分大纲生成进度
    """
    logger.info(
        "用户 %s 请求重新生成项目 %s 的第 %d 部分大纲，提示词: %s，级联删除: %s",
        desktop_user.id,
        project_id,
        part_number,
        request.prompt or "无",
        request.cascade_delete,
    )

    part_service = PartOutlineService(session)
    chapter_outline_repo = ChapterOutlineRepository(session)

    # 获取项目信息
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)
    blueprint = project_schema.blueprint

    if not blueprint:
        raise BlueprintNotReadyError(project_id)

    # 检查是否需要部分大纲
    if not blueprint.needs_part_outlines:
        raise InvalidParameterError("该项目不需要部分大纲（章节数未超过阈值）")

    # 获取所有部分大纲
    all_parts = await part_service.repo.get_by_project_id(project_id)
    if not all_parts:
        raise ResourceNotFoundError("部分大纲", project_id)

    # 检查指定的部分是否存在
    target_part = next((p for p in all_parts if p.part_number == part_number), None)
    if not target_part:
        raise ResourceNotFoundError("部分大纲", f"项目 {project_id} 第 {part_number} 部分")

    # 找到最大部分号
    max_part_number = max(p.part_number for p in all_parts)

    # 串行生成原则检查
    cascade_deleted_parts_count = 0
    cascade_deleted_chapters_count = 0

    if part_number < max_part_number:
        if not request.cascade_delete:
            # 不是最后一个部分且没有设置级联删除，返回错误
            raise InvalidParameterError(
                f"串行生成原则：只能重新生成最后一个部分（当前最后一个部分为第{max_part_number}部分）。"
                f"如需重新生成第{part_number}部分，请设置cascade_delete=True以级联删除第{part_number}部分之后的所有部分大纲和章节大纲。"
            )
        else:
            # 级联删除：删除该部分之后的所有部分大纲和对应的章节大纲
            logger.info(
                "串行生成原则：级联删除第 %d 部分之后的所有内容（第 %d-%d 部分）",
                part_number, part_number + 1, max_part_number
            )

            # 删除后续部分对应的章节大纲（从当前部分的起始章节开始）
            await chapter_outline_repo.delete_from_chapter(project_id, target_part.start_chapter)
            cascade_deleted_chapters_count = "所有后续章节"  # 实际数量难以统计，暂用描述

            # 删除后续部分大纲（包括当前部分）
            cascade_deleted_parts_count = await part_service.repo.delete_from_part(
                project_id, part_number
            )
            logger.info("已删除 %d 个部分大纲和对应的章节大纲", cascade_deleted_parts_count)
    else:
        # 是最后一个部分，只删除该部分的章节大纲和部分大纲本身
        logger.info(
            "删除第 %d 部分的章节大纲（第 %d-%d 章）",
            part_number, target_part.start_chapter, target_part.end_chapter
        )
        await chapter_outline_repo.delete_from_chapter(project_id, target_part.start_chapter)
        await part_service.repo.delete(target_part)

    # 获取前面的部分（用于串行生成上下文）
    # 注意：如果刚进行了级联删除，需要重新获取
    all_parts_fresh = await part_service.repo.get_by_project_id(project_id)
    previous_parts = [p for p in all_parts_fresh if p.part_number < part_number]

    # 重新生成指定部分
    from ....core.constants import LLMConstants
    system_prompt = await part_service.prompt_service.get_prompt("part_outline")

    world_setting, full_synopsis, characters = part_service._prepare_blueprint_data(
        await novel_service.ensure_project_owner(project_id, desktop_user.id)
    )

    total_chapters = blueprint.total_chapters or 0
    chapters_per_part = blueprint.chapters_per_part or 25
    # 总部分数应该是删除后剩余的部分数 + 1（当前要重新生成的）
    total_parts = len(previous_parts) + 1

    user_prompt = part_service.prompt_builder.build_part_outline_prompt(
        total_chapters=total_chapters,
        chapters_per_part=chapters_per_part,
        total_parts=max_part_number,  # 使用原始的总部分数
        world_setting=world_setting,
        characters=characters,
        full_synopsis=full_synopsis,
        current_part_number=part_number,
        previous_parts=previous_parts,
        optimization_prompt=request.prompt,
    )

    response = await part_service.llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_prompt}],
        temperature=LLMConstants.BLUEPRINT_TEMPERATURE,
        user_id=desktop_user.id,
        response_format="json_object",
        timeout=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
    )

    # 解析并保存新的部分
    part_data = part_service._parse_single_part_outline(response, part_number)
    new_part = part_service._create_single_part_outline_model(project_id, part_data)
    await part_service.repo.add(new_part)

    await session.commit()

    logger.info("项目 %s 第 %d 部分大纲重新生成完成", project_id, part_number)

    # 返回更新后的进度
    updated_parts = await part_service.repo.get_by_project_id(project_id)

    result = PartOutlineGenerationProgress(
        parts=[part_service._to_schema(p) for p in updated_parts],
        total_parts=len(updated_parts),
        completed_parts=len(updated_parts),
        status="completed",
    )

    # 如果有级联删除，添加额外信息到响应（通过修改parts中的某个字段或日志）
    if cascade_deleted_parts_count > 0:
        logger.info(
            "级联删除信息：删除了第 %d-%d 部分（共 %d 个）及对应的章节大纲",
            part_number + 1, max_part_number, cascade_deleted_parts_count
        )

    return result


# ------------------------------------------------------------------
# 部分大纲生成接口（用于长篇小说分层大纲）
# ------------------------------------------------------------------


@router.post("/novels/{project_id}/parts/generate", response_model=PartOutlineGenerationProgress)
async def generate_part_outlines(
    project_id: str,
    request: GeneratePartOutlinesRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> PartOutlineGenerationProgress:
    """
    生成部分大纲（大纲的大纲）

    用于长篇小说（51章以上），将整部小说分割成多个部分，
    每个部分包含若干章节，便于后续分批生成详细章节大纲。
    """
    logger.info("用户 %s 请求为项目 %s 生成部分大纲", desktop_user.id, project_id)

    part_service = PartOutlineService(session)

    result = await part_service.generate_part_outlines(
        project_id=project_id,
        user_id=desktop_user.id,
        total_chapters=request.total_chapters,
        chapters_per_part=request.chapters_per_part,
    )
    await session.commit()
    return result


@router.post("/novels/{project_id}/parts/{part_number}/chapters", response_model=NovelProjectSchema)
async def generate_part_chapters(
    project_id: str,
    part_number: int,
    request: GeneratePartChaptersRequest,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> NovelProjectSchema:
    """
    为指定部分生成详细的章节大纲

    使用RAG检索增强：检索已完成章节的摘要，确保新大纲与已有内容一致。

    基于部分大纲的主题、关键事件等信息，
    生成该部分范围内所有章节的详细大纲。
    """
    logger.info("用户 %s 请求为项目 %s 的第 %d 部分生成章节大纲", desktop_user.id, project_id, part_number)

    part_service = PartOutlineService(session, vector_store=vector_store)

    await part_service.generate_part_chapters(
        project_id=project_id,
        user_id=desktop_user.id,
        part_number=part_number,
        regenerate=request.regenerate,
    )

    return await novel_service.get_project_schema(project_id, desktop_user.id)


@router.post("/novels/{project_id}/parts/batch-generate", response_model=PartOutlineGenerationProgress)
async def batch_generate_part_chapters(
    project_id: str,
    request: BatchGenerateChaptersRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
) -> PartOutlineGenerationProgress:
    """
    批量并发生成多个部分的章节大纲

    使用RAG检索增强：检索已完成章节的摘要，确保新大纲与已有内容一致。

    支持并发生成多个部分的章节大纲，提高长篇小说大纲生成效率。
    可以指定要生成的部分编号列表，或自动生成所有待生成的部分。
    """
    logger.info(
        "用户 %s 请求批量生成项目 %s 的章节大纲，part_numbers=%s",
        desktop_user.id,
        project_id,
        request.part_numbers,
    )

    part_service = PartOutlineService(session, vector_store=vector_store)

    return await part_service.batch_generate_chapters(
        project_id=project_id,
        user_id=desktop_user.id,
        part_numbers=request.part_numbers,
        max_concurrent=request.max_concurrent,
    )


@router.post("/novels/{project_id}/parts/{part_number}/cancel")
async def cancel_part_generation(
    project_id: str,
    part_number: int,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    取消指定部分的章节大纲生成

    设置取消标志，正在生成的任务会在下一次检查点停止。
    只能取消状态为 generating 的部分。
    """
    logger.info("用户 %s 请求取消项目 %s 的第 %d 部分生成", desktop_user.id, project_id, part_number)

    part_service = PartOutlineService(session)

    success = await part_service.cancel_part_generation(
        project_id=project_id,
        part_number=part_number,
        user_id=desktop_user.id,
    )

    if success:
        return {
            "success": True,
            "message": f"第 {part_number} 部分的生成正在取消中",
            "part_number": part_number,
        }
    else:
        return {
            "success": False,
            "message": f"第 {part_number} 部分当前无法取消（可能不在生成中）",
            "part_number": part_number,
        }


@router.get("/novels/{project_id}/parts/progress", response_model=PartOutlineGenerationProgress)
async def get_part_outline_progress(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> PartOutlineGenerationProgress:
    """
    查询部分大纲生成进度

    用于中断恢复机制，返回所有部分的生成状态。
    前端可根据状态判断哪些部分需要继续生成。
    """
    try:
        logger.info("用户 %s 查询项目 %s 的部分大纲进度", desktop_user.id, project_id)

        part_service = PartOutlineService(session)

        # 验证权限
        await novel_service.ensure_project_owner(project_id, desktop_user.id)

        # 先清理超时的generating状态（超过15分钟未更新视为超时）
        logger.info("开始清理超时状态...")
        cleaned_count = await part_service.cleanup_stale_generating_status(project_id, timeout_minutes=15)
        if cleaned_count > 0:
            logger.info("清理了 %d 个超时的generating状态", cleaned_count)

        # 获取所有部分大纲
        logger.info("获取所有部分大纲...")
        all_parts = await part_service.repo.get_by_project_id(project_id)

        if not all_parts:
            raise ResourceNotFoundError("部分大纲", project_id)

        completed_count = sum(1 for p in all_parts if p.generation_status == "completed")
        all_completed = completed_count == len(all_parts)

        logger.info("转换数据为schema...")
        return PartOutlineGenerationProgress(
            parts=[part_service._to_schema(p) for p in all_parts],
            total_parts=len(all_parts),
            completed_parts=completed_count,
            status="completed" if all_completed else "partial",
        )
    except (BlueprintNotReadyError, InvalidParameterError, ResourceNotFoundError):
        raise
    except Exception as exc:
        logger.error("查询部分大纲进度失败: %s", exc, exc_info=True)
        raise DatabaseError(f"查询进度失败: {str(exc)}") from exc


@router.delete("/novels/{project_id}/parts/delete-latest")
async def delete_latest_part_outlines(
    project_id: str,
    count: int = 1,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    删除最后N个部分大纲（串行生成原则）

    删除最后N个部分大纲及其对应的章节大纲。

    Args:
        project_id: 项目ID
        count: 要删除的部分数量（从最后开始）

    Returns:
        删除结果
    """
    logger.info(
        "用户 %s 请求删除项目 %s 的最后 %d 个部分大纲",
        desktop_user.id,
        project_id,
        count,
    )

    part_service = PartOutlineService(session)
    chapter_outline_repo = ChapterOutlineRepository(session)

    # 验证权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取所有部分大纲
    all_parts = await part_service.repo.get_by_project_id(project_id)
    if not all_parts:
        raise ResourceNotFoundError("部分大纲", project_id)

    total_parts = len(all_parts)
    if count > total_parts:
        raise InvalidParameterError(f"要删除的数量({count})超过现有部分数量({total_parts})")

    if count == total_parts:
        raise InvalidParameterError("不能删除所有部分大纲，请使用重新生成功能")

    # 计算要删除的起始部分号
    start_part = total_parts - count + 1

    # 找到要删除的第一个部分的起始章节
    parts_to_delete = [p for p in all_parts if p.part_number >= start_part]
    if parts_to_delete:
        first_part_to_delete = min(parts_to_delete, key=lambda p: p.part_number)
        start_chapter = first_part_to_delete.start_chapter

        # 删除对应的章节大纲
        logger.info(
            "删除第 %d 章及之后的章节大纲",
            start_chapter
        )
        await chapter_outline_repo.delete_from_chapter(project_id, start_chapter)

    # 删除部分大纲
    deleted_count = await part_service.repo.delete_from_part(project_id, start_part)

    await session.commit()

    logger.info(
        "项目 %s 删除了 %d 个部分大纲（第 %d-%d 部分）",
        project_id, deleted_count, start_part, total_parts
    )

    return {
        "success": True,
        "message": f"已删除最后 {deleted_count} 个部分大纲",
        "deleted_count": deleted_count,
        "remaining_parts": total_parts - deleted_count,
    }
