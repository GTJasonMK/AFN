"""
项目工作流路由

提供显式“回退”能力：
- 回退必须遵循状态机的合法路径（逐步回退，不允许越级跳转）。
- 每一步回退都会触发对应的清理逻辑，避免新旧数据冲突。
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.dependencies import get_default_user, get_novel_service
from ....core.state_machine import ProjectStateMachine, ProjectStatus
from ....db.session import get_session
from ....exceptions import InvalidParameterError
from ....models.novel import Chapter, ChapterOutline
from ....models.part_outline import PartOutline
from ....schemas.project_workflow import (
    ProjectWorkflowCleanupImpact,
    ProjectWorkflowRollbackRequest,
    ProjectWorkflowRollbackPreviewResponse,
    ProjectWorkflowRollbackResponse,
    ProjectWorkflowRollbackStepPreview,
    RollbackTargetStatus,
)
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService

logger = logging.getLogger(__name__)

router = APIRouter()


WORKFLOW_ORDER: List[str] = [
    ProjectStatus.DRAFT.value,
    ProjectStatus.BLUEPRINT_READY.value,
    ProjectStatus.PART_OUTLINES_READY.value,
    ProjectStatus.CHAPTER_OUTLINES_READY.value,
    ProjectStatus.WRITING.value,
    ProjectStatus.COMPLETED.value,
]
WORKFLOW_INDEX: Dict[str, int] = {status: i for i, status in enumerate(WORKFLOW_ORDER)}


def _status_value(status: object) -> str:
    if isinstance(status, ProjectStatus):
        return status.value
    return str(status)


def _find_rollback_path(from_status: str, to_status: str) -> Optional[List[str]]:
    """
    从当前状态找到一条合法的回退路径。

    规则：
    - 只允许“向前置阶段回退”（workflow index 递减）
    - 不允许越过目标状态（避免 overshoot 后无法前进回来）
    - 采用 BFS，保证找到最短路径
    """
    from_status = (from_status or "").strip()
    to_status = (to_status or "").strip()

    if not from_status or not to_status:
        return None
    if from_status == to_status:
        return []
    if from_status not in WORKFLOW_INDEX or to_status not in WORKFLOW_INDEX:
        return None

    from_index = WORKFLOW_INDEX[from_status]
    to_index = WORKFLOW_INDEX[to_status]
    if to_index > from_index:
        return None

    queue = deque([from_status])
    prev: Dict[str, Optional[str]] = {from_status: None}

    while queue:
        current = queue.popleft()
        if current == to_status:
            break

        current_index = WORKFLOW_INDEX.get(current, -1)
        for next_status in ProjectStateMachine.TRANSITIONS.get(current, []):
            next_value = _status_value(next_status)
            next_index = WORKFLOW_INDEX.get(next_value, -1)
            if next_index < 0:
                continue
            # 只允许回退（严格递减），并禁止越过目标
            if next_index >= current_index:
                continue
            if next_index < to_index:
                continue
            if next_value in prev:
                continue
            prev[next_value] = current
            queue.append(next_value)

    if to_status not in prev:
        return None

    path: List[str] = []
    node = to_status
    while node != from_status:
        path.append(node)
        parent = prev.get(node)
        if parent is None:
            return None
        node = parent
    path.reverse()
    return path


async def _get_chapter_stats(session: AsyncSession, project_id: str) -> Dict[str, Optional[int]]:
    result = await session.execute(
        select(
            func.count(Chapter.id),
            func.min(Chapter.chapter_number),
            func.max(Chapter.chapter_number),
        ).where(Chapter.project_id == project_id)
    )
    count, min_num, max_num = result.one()
    return {"count": int(count or 0), "min": min_num, "max": max_num}


async def _get_outline_stats(session: AsyncSession, project_id: str) -> Dict[str, Optional[int]]:
    result = await session.execute(
        select(
            func.count(ChapterOutline.id),
            func.min(ChapterOutline.chapter_number),
            func.max(ChapterOutline.chapter_number),
        ).where(ChapterOutline.project_id == project_id)
    )
    count, min_num, max_num = result.one()
    return {"count": int(count or 0), "min": min_num, "max": max_num}


async def _get_part_outline_stats(session: AsyncSession, project_id: str) -> Dict[str, Optional[int]]:
    result = await session.execute(
        select(
            func.count(PartOutline.id),
            func.min(PartOutline.part_number),
            func.max(PartOutline.part_number),
        ).where(PartOutline.project_id == project_id)
    )
    count, min_num, max_num = result.one()
    return {"count": int(count or 0), "min": min_num, "max": max_num}


async def _get_outlines_linked_to_chapters_stats(
    session: AsyncSession,
    project_id: str,
) -> Dict[str, Optional[int]]:
    """
    统计“与章节正文同章节号”的章节大纲数量。

    说明：回退 writing -> chapter_outlines_ready 时，当前实现会删除章节正文，
    同时也会删除这些章节对应的章节大纲（若存在）。
    """
    chapter_numbers_subq = select(Chapter.chapter_number).where(Chapter.project_id == project_id)
    result = await session.execute(
        select(
            func.count(ChapterOutline.id),
            func.min(ChapterOutline.chapter_number),
            func.max(ChapterOutline.chapter_number),
        ).where(
            ChapterOutline.project_id == project_id,
            ChapterOutline.chapter_number.in_(chapter_numbers_subq),
        )
    )
    count, min_num, max_num = result.one()
    return {"count": int(count or 0), "min": min_num, "max": max_num}


def _label(status: str) -> str:
    return ProjectStateMachine.STATUS_DESCRIPTIONS.get(status, status)


def _build_step_impacts(
    *,
    step_from: str,
    step_to: str,
    chapter_stats: Dict[str, Optional[int]],
    outline_stats: Dict[str, Optional[int]],
    part_stats: Dict[str, Optional[int]],
    outlines_linked_to_chapters_stats: Dict[str, Optional[int]],
    simulated_remaining_outlines: int,
) -> List[ProjectWorkflowCleanupImpact]:
    impacts: List[ProjectWorkflowCleanupImpact] = []

    # completed -> writing：仅阶段回退，不清理数据
    if step_from == ProjectStatus.COMPLETED.value and step_to == ProjectStatus.WRITING.value:
        return impacts

    # writing -> chapter_outlines_ready：删除章节正文（以及相关索引/向量数据）
    if step_from == ProjectStatus.WRITING.value and step_to == ProjectStatus.CHAPTER_OUTLINES_READY.value:
        chapters_count = int(chapter_stats.get("count") or 0)
        impacts.append(
            ProjectWorkflowCleanupImpact(
                kind="delete_chapters",
                title="删除已生成章节正文（含版本/评价/漫画数据/索引）",
                tables=[
                    "chapters",
                    "chapter_versions",
                    "chapter_evaluations",
                    "chapter_manga_prompts",
                    "character_state_index",
                    "foreshadowing_index",
                ],
                count=chapters_count,
                chapter_start=chapter_stats.get("min"),
                chapter_end=chapter_stats.get("max"),
                note="仅删除数据库中已存在的章节（即已生成/已导入过正文的章节）。",
            )
        )

        linked_outlines_count = int(outlines_linked_to_chapters_stats.get("count") or 0)
        if linked_outlines_count > 0:
            impacts.append(
                ProjectWorkflowCleanupImpact(
                    kind="delete_chapter_outlines",
                    title="同步删除这些章节对应的章节大纲（若存在）",
                    tables=["chapter_outlines"],
                    count=linked_outlines_count,
                    chapter_start=outlines_linked_to_chapters_stats.get("min"),
                    chapter_end=outlines_linked_to_chapters_stats.get("max"),
                    note="当前实现会在删除章节正文时一并删除相同章节号的章节大纲。",
                )
            )

        if chapters_count > 0:
            impacts.append(
                ProjectWorkflowCleanupImpact(
                    kind="delete_vector_store",
                    title="清理向量库中的章节内容（RAG）",
                    tables=["vector_store"],
                    chapter_start=chapter_stats.get("min"),
                    chapter_end=chapter_stats.get("max"),
                    note="仅当启用向量库时执行（vector_store_enabled=true）。",
                )
            )
        return impacts

    # chapter_outlines_ready -> part_outlines_ready：删除剩余章节大纲
    if step_from == ProjectStatus.CHAPTER_OUTLINES_READY.value and step_to == ProjectStatus.PART_OUTLINES_READY.value:
        impacts.append(
            ProjectWorkflowCleanupImpact(
                kind="delete_chapter_outlines",
                title="删除章节大纲（用于重新规划分部结构）",
                tables=["chapter_outlines"],
                count=int(simulated_remaining_outlines),
                chapter_start=outline_stats.get("min"),
                chapter_end=outline_stats.get("max"),
                note=(
                    "回退到“部分大纲就绪”需要清空章节大纲，避免与新的分部结构冲突。"
                    if simulated_remaining_outlines > 0
                    else "当前未检测到可删除的章节大纲。"
                ),
            )
        )
        return impacts

    # chapter_outlines_ready -> blueprint_ready：删除章节大纲 + 部分大纲（回到蓝图阶段）
    if step_from == ProjectStatus.CHAPTER_OUTLINES_READY.value and step_to == ProjectStatus.BLUEPRINT_READY.value:
        impacts.append(
            ProjectWorkflowCleanupImpact(
                kind="delete_chapter_outlines",
                title="删除章节大纲（回到蓝图阶段）",
                tables=["chapter_outlines"],
                count=int(simulated_remaining_outlines),
                chapter_start=outline_stats.get("min"),
                chapter_end=outline_stats.get("max"),
            )
        )
        impacts.append(
            ProjectWorkflowCleanupImpact(
                kind="delete_part_outlines",
                title="删除部分大纲（回到蓝图阶段）",
                tables=["part_outlines"],
                count=int(part_stats.get("count") or 0),
                part_start=part_stats.get("min"),
                part_end=part_stats.get("max"),
            )
        )
        return impacts

    # part_outlines_ready -> blueprint_ready：删除部分大纲
    if step_from == ProjectStatus.PART_OUTLINES_READY.value and step_to == ProjectStatus.BLUEPRINT_READY.value:
        impacts.append(
            ProjectWorkflowCleanupImpact(
                kind="delete_part_outlines",
                title="删除部分大纲（回到蓝图阶段）",
                tables=["part_outlines"],
                count=int(part_stats.get("count") or 0),
                part_start=part_stats.get("min"),
                part_end=part_stats.get("max"),
            )
        )
        return impacts

    return impacts


def _build_summary(
    *,
    from_status: str,
    to_status: str,
    steps: List[ProjectWorkflowRollbackStepPreview],
) -> str:
    if not steps:
        return "无需回退。"

    lines: List[str] = []
    lines.append("将执行回退路径：")
    for step in steps:
        lines.append(f"- {step.from_label} → {step.to_label}")
        if not step.impacts:
            lines.append("  - （无清理动作）")
            continue
        for impact in step.impacts:
            detail = impact.title
            if impact.kind == "delete_chapters" and impact.count is not None:
                detail = f"{detail}：{impact.count} 章"
                if impact.chapter_start is not None and impact.chapter_end is not None:
                    detail = f"{detail}（第 {impact.chapter_start}-{impact.chapter_end} 章）"
            elif impact.kind == "delete_chapter_outlines" and impact.count is not None:
                detail = f"{detail}：{impact.count} 条"
                if impact.chapter_start is not None and impact.chapter_end is not None:
                    detail = f"{detail}（第 {impact.chapter_start}-{impact.chapter_end} 章）"
            elif impact.kind == "delete_part_outlines" and impact.count is not None:
                detail = f"{detail}：{impact.count} 条"
                if impact.part_start is not None and impact.part_end is not None:
                    detail = f"{detail}（第 {impact.part_start}-{impact.part_end} 部分）"
            elif impact.kind == "delete_vector_store":
                if not settings.vector_store_enabled:
                    detail = f"{detail}：已禁用（vector_store_enabled=false）"
                elif impact.chapter_start is not None and impact.chapter_end is not None:
                    detail = f"{detail}（第 {impact.chapter_start}-{impact.chapter_end} 章）"
            lines.append(f"  - {detail}")
            if impact.note:
                lines.append(f"    - {impact.note}")

    lines.append("")
    lines.append("注意：回退会删除依赖数据，此操作不可恢复。")
    return "\n".join(lines)


@router.get(
    "/novels/{project_id}/workflow/rollback-preview",
    response_model=ProjectWorkflowRollbackPreviewResponse,
)
async def preview_project_workflow_rollback(
    project_id: str,
    target_status: RollbackTargetStatus = Query(..., description="回退目标状态"),
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ProjectWorkflowRollbackPreviewResponse:
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    from_status = str(project.status or "").strip() or ProjectStatus.DRAFT.value
    to_status = str(target_status).strip()

    path = _find_rollback_path(from_status, to_status)
    if path is None:
        current_desc = _label(from_status)
        target_desc = _label(to_status)
        raise InvalidParameterError(
            f"无法从「{current_desc}」回退到「{target_desc}」。",
            "target_status",
        )

    chapter_stats = await _get_chapter_stats(session, project_id)
    outline_stats = await _get_outline_stats(session, project_id)
    part_stats = await _get_part_outline_stats(session, project_id)
    outlines_linked_to_chapters_stats = await _get_outlines_linked_to_chapters_stats(session, project_id)

    steps: List[ProjectWorkflowRollbackStepPreview] = []

    # 用“模拟剩余值”让预览更接近真实执行顺序（避免明显的重复计数）
    simulated_remaining_outlines = int(outline_stats.get("count") or 0)
    simulated_remaining_parts = int(part_stats.get("count") or 0)

    current = from_status
    for next_status in path:
        impacts = _build_step_impacts(
            step_from=current,
            step_to=next_status,
            chapter_stats=chapter_stats,
            outline_stats=outline_stats,
            part_stats={"count": simulated_remaining_parts, "min": part_stats.get("min"), "max": part_stats.get("max")},
            outlines_linked_to_chapters_stats=outlines_linked_to_chapters_stats,
            simulated_remaining_outlines=simulated_remaining_outlines,
        )

        steps.append(
            ProjectWorkflowRollbackStepPreview(
                from_status=current,  # type: ignore[arg-type]
                to_status=next_status,  # type: ignore[arg-type]
                from_label=_label(current),
                to_label=_label(next_status),
                impacts=impacts,
            )
        )

        # 更新模拟剩余值
        if current == ProjectStatus.WRITING.value and next_status == ProjectStatus.CHAPTER_OUTLINES_READY.value:
            # 删除章节正文会连带删除与其同章节号的大纲（若存在）
            simulated_remaining_outlines = max(
                0,
                simulated_remaining_outlines - int(outlines_linked_to_chapters_stats.get("count") or 0),
            )
        if current == ProjectStatus.CHAPTER_OUTLINES_READY.value and next_status in [
            ProjectStatus.PART_OUTLINES_READY.value,
            ProjectStatus.BLUEPRINT_READY.value,
        ]:
            simulated_remaining_outlines = 0
        if current in [ProjectStatus.PART_OUTLINES_READY.value, ProjectStatus.CHAPTER_OUTLINES_READY.value] and next_status == ProjectStatus.BLUEPRINT_READY.value:
            simulated_remaining_parts = 0

        current = next_status

    summary = _build_summary(from_status=from_status, to_status=to_status, steps=steps)

    return ProjectWorkflowRollbackPreviewResponse(
        project_id=project_id,
        from_status=from_status,  # type: ignore[arg-type]
        to_status=to_status,  # type: ignore[arg-type]
        path=path,  # type: ignore[arg-type]
        steps=steps,
        summary=summary,
    )


@router.post(
    "/novels/{project_id}/workflow/rollback",
    response_model=ProjectWorkflowRollbackResponse,
)
async def rollback_project_workflow(
    project_id: str,
    payload: ProjectWorkflowRollbackRequest = Body(...),
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ProjectWorkflowRollbackResponse:
    """
    显式回退项目工作流状态。

    注意：回退是破坏性操作，会触发数据清理（依赖数据会被删除）。
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    if not payload.confirm:
        raise InvalidParameterError(
            "回退会删除依赖数据（如章节正文/章节大纲等）。请在前端确认后再提交 confirm=true。",
            "confirm",
        )

    from_status = str(project.status or "").strip() or ProjectStatus.DRAFT.value
    to_status = str(payload.target_status).strip()

    if from_status == to_status:
        return ProjectWorkflowRollbackResponse(
            project_id=project_id,
            from_status=from_status,
            to_status=to_status,
            path=[],
            message="当前状态与目标一致，无需回退。",
        )

    path = _find_rollback_path(from_status, to_status)
    if path is None:
        current_desc = ProjectStateMachine.STATUS_DESCRIPTIONS.get(from_status, from_status)
        target_desc = ProjectStateMachine.STATUS_DESCRIPTIONS.get(to_status, to_status)
        raise InvalidParameterError(
            f"无法从「{current_desc}」回退到「{target_desc}」。请按工作流逐步回退，或检查项目状态是否异常。",
            "target_status",
        )

    logger.warning(
        "项目 %s 执行工作流回退: user_id=%s %s -> %s path=%s",
        project_id,
        desktop_user.id,
        from_status,
        to_status,
        path,
    )

    for next_status in path:
        await novel_service.transition_project_status(project, next_status)
        # transition_project_status 内部已 commit，这里无需重复提交

    return ProjectWorkflowRollbackResponse(
        project_id=project_id,
        from_status=from_status,
        to_status=to_status,
        path=path,
        message="回退完成。",
    )


__all__ = ["router"]
