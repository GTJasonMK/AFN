"""
摘要生成服务

统一管理章节摘要的生成逻辑，消除重复代码。
"""

import logging
from typing import Optional, TYPE_CHECKING

from ..core.config import settings
from ..core.constants import LLMConstants
from ..utils.json_utils import remove_think_tags

if TYPE_CHECKING:
    from ..models.novel import Chapter
    from ..repositories.chapter_repository import ChapterOutlineRepository
    from .llm_service import LLMService

logger = logging.getLogger(__name__)


class SummaryService:
    """
    摘要生成服务

    统一处理章节摘要的生成、更新和错误处理。

    使用示例:
        summary_service = SummaryService(llm_service)
        await summary_service.generate_and_save_summary(
            chapter=chapter,
            content=content,
            project_id=project_id,
            user_id=user_id,
        )
    """

    # 摘要生成失败时的默认消息
    FALLBACK_SUMMARY = "摘要生成失败，请稍后手动生成"

    def __init__(self, llm_service: "LLMService"):
        """
        初始化摘要服务

        Args:
            llm_service: LLM服务实例
        """
        self.llm_service = llm_service

    async def generate_summary(
        self,
        content: str,
        user_id: int,
        timeout: Optional[float] = None,
    ) -> Optional[str]:
        """
        生成内容摘要

        Args:
            content: 章节内容
            user_id: 用户ID
            timeout: 超时时间（秒），默认使用配置值

        Returns:
            生成的摘要，失败时返回None
        """
        if not content or not content.strip():
            return None

        try:
            summary = await self.llm_service.get_summary(
                content,
                temperature=settings.llm_temp_summary,
                user_id=user_id,
                timeout=timeout or LLMConstants.SUMMARY_GENERATION_TIMEOUT,
            )
            return remove_think_tags(summary) if summary else None
        except Exception as exc:
            logger.error("摘要生成失败: %s", exc)
            return None

    async def generate_and_save_summary(
        self,
        chapter: "Chapter",
        content: str,
        project_id: str,
        user_id: int,
        chapter_outline_repo: Optional["ChapterOutlineRepository"] = None,
        chapter_title: Optional[str] = None,
        use_fallback: bool = True,
    ) -> Optional[str]:
        """
        生成摘要并保存到章节对象

        Args:
            chapter: 章节对象
            content: 章节内容
            project_id: 项目ID
            user_id: 用户ID
            chapter_outline_repo: 大纲仓库（可选，用于同步更新大纲摘要）
            chapter_title: 章节标题（可选，用于更新大纲）
            use_fallback: 失败时是否使用默认消息

        Returns:
            生成的摘要，失败时根据use_fallback返回默认消息或None
        """
        chapter_number = chapter.chapter_number

        summary = await self.generate_summary(content, user_id)

        if summary:
            chapter.real_summary = summary
            logger.info(
                "项目 %s 第 %s 章摘要已生成",
                project_id,
                chapter_number,
            )

            # 同步更新大纲摘要
            if chapter_outline_repo and chapter_title:
                try:
                    await chapter_outline_repo.upsert_outline(
                        project_id=project_id,
                        chapter_number=chapter_number,
                        title=chapter_title,
                        summary=summary,
                    )
                except Exception as exc:
                    logger.warning(
                        "项目 %s 第 %s 章大纲摘要更新失败: %s",
                        project_id,
                        chapter_number,
                        exc,
                    )
        else:
            logger.error(
                "项目 %s 第 %s 章摘要生成失败",
                project_id,
                chapter_number,
            )
            if use_fallback:
                chapter.real_summary = self.FALLBACK_SUMMARY
            else:
                chapter.real_summary = None

        return chapter.real_summary

    async def ensure_summary(
        self,
        chapter: "Chapter",
        content: str,
        project_id: str,
        user_id: int,
        force_regenerate: bool = False,
    ) -> Optional[str]:
        """
        确保章节有摘要（如果没有则生成）

        Args:
            chapter: 章节对象
            content: 章节内容
            project_id: 项目ID
            user_id: 用户ID
            force_regenerate: 是否强制重新生成

        Returns:
            现有或新生成的摘要
        """
        if chapter.real_summary and not force_regenerate:
            return chapter.real_summary

        return await self.generate_and_save_summary(
            chapter=chapter,
            content=content,
            project_id=project_id,
            user_id=user_id,
            use_fallback=False,
        )


__all__ = ["SummaryService"]
