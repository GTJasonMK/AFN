"""
章节 RAG 预处理辅助函数

用于在路由层复用“章节摘要/章节分析”的调用骨架，减少重复样板并避免参数漂移。
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ...schemas.novel import ChapterAnalysisData
from ...services.chapter_analysis_service import ChapterAnalysisService
from ...services.summary_service import SummaryService

logger = logging.getLogger(__name__)


def get_project_display_title(project_id: str, title: Optional[str]) -> str:
    """统一项目标题兜底逻辑（避免 title=None 影响提示词与日志）。"""
    return title or f"项目{project_id[:8]}"


async def ensure_chapter_summary(
    *,
    chapter: Any,
    content: str,
    project_id: str,
    user_id: int,
    llm_service: Any,
    chapter_outline_repo: Optional[Any] = None,
    chapter_title: Optional[str] = None,
    force_regenerate: bool = False,
    use_fallback: bool = False,
    summary_service: Optional[SummaryService] = None,
) -> Optional[str]:
    """确保章节摘要可用（内部会自行判断是否需要生成）。"""
    if not content or not content.strip():
        return None

    service = summary_service or SummaryService(llm_service)
    return await service.ensure_summary(
        chapter=chapter,
        content=content,
        project_id=project_id,
        user_id=user_id,
        chapter_outline_repo=chapter_outline_repo,
        chapter_title=chapter_title,
        force_regenerate=force_regenerate,
        use_fallback=use_fallback,
    )


async def ensure_chapter_analysis_data_safely(
    *,
    project_id: str,
    session: Any,
    chapter: Any,
    content: str,
    title: str,
    chapter_number: int,
    novel_title: str,
    user_id: int,
    timeout: float = 300.0,
    force_regenerate: bool = False,
    analysis_service: Optional[ChapterAnalysisService] = None,
    log: Optional[logging.Logger] = None,
) -> Optional[ChapterAnalysisData]:
    """确保章节分析可用；失败时记录日志并降级返回 None。"""
    if not content or not content.strip():
        return None

    service = analysis_service or ChapterAnalysisService(session)
    use_logger = log or logger
    try:
        return await service.ensure_analysis_data(
            chapter=chapter,
            content=content,
            title=title,
            chapter_number=chapter_number,
            novel_title=novel_title,
            user_id=user_id,
            timeout=timeout,
            force_regenerate=force_regenerate,
        )
    except Exception as exc:
        use_logger.error("项目 %s 第 %s 章分析失败: %s", project_id, chapter_number, exc)
        return None


async def ensure_chapter_summary_and_analysis_data_safely(
    *,
    project_id: str,
    session: Any,
    chapter: Any,
    content: str,
    title: str,
    chapter_number: int,
    novel_title: str,
    user_id: int,
    llm_service: Any,
    chapter_outline_repo: Optional[Any] = None,
    timeout: float = 300.0,
    force_regenerate_summary: bool = False,
    use_fallback_summary: bool = False,
    force_regenerate_analysis: bool = False,
    analysis_service: Optional[ChapterAnalysisService] = None,
    summary_service: Optional[SummaryService] = None,
    log: Optional[logging.Logger] = None,
) -> Optional[ChapterAnalysisData]:
    """一次性确保章节摘要与章节分析可用（失败时章节分析降级为 None）。"""
    if not content or not content.strip():
        return None

    await ensure_chapter_summary(
        chapter=chapter,
        content=content,
        project_id=project_id,
        user_id=user_id,
        llm_service=llm_service,
        chapter_outline_repo=chapter_outline_repo,
        chapter_title=title,
        force_regenerate=force_regenerate_summary,
        use_fallback=use_fallback_summary,
        summary_service=summary_service,
    )

    return await ensure_chapter_analysis_data_safely(
        project_id=project_id,
        session=session,
        chapter=chapter,
        content=content,
        title=title,
        chapter_number=chapter_number,
        novel_title=novel_title,
        user_id=user_id,
        timeout=timeout,
        force_regenerate=force_regenerate_analysis,
        analysis_service=analysis_service,
        log=log,
    )


__all__ = [
    "ensure_chapter_analysis_data_safely",
    "ensure_chapter_summary",
    "ensure_chapter_summary_and_analysis_data_safely",
    "get_project_display_title",
]
