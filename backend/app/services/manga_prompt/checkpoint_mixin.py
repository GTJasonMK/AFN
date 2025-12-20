"""
断点续传Mixin

提供生成进度保存和断点续传相关的方法。
"""

import logging
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.novel import ChapterMangaPrompt

logger = logging.getLogger(__name__)


class CheckpointMixin:
    """断点续传相关方法的Mixin"""

    # 需要被主类提供的属性
    session: AsyncSession

    async def _save_generation_progress(
        self,
        chapter_id: int,
        status: str,
        progress: dict,
        source_version_id: Optional[int] = None,
    ) -> None:
        """
        保存生成进度（用于断点续传）

        Args:
            chapter_id: 章节ID
            status: 生成状态
            progress: 进度数据
            source_version_id: 关联的正文版本ID
        """
        # 检查是否已存在
        existing = await self.session.execute(
            select(ChapterMangaPrompt).where(
                ChapterMangaPrompt.chapter_id == chapter_id
            )
        )
        manga_prompt = existing.scalar_one_or_none()

        if manga_prompt:
            manga_prompt.generation_status = status
            manga_prompt.generation_progress = progress
            manga_prompt.source_version_id = source_version_id
        else:
            manga_prompt = ChapterMangaPrompt(
                chapter_id=chapter_id,
                generation_status=status,
                generation_progress=progress,
                source_version_id=source_version_id,
                character_profiles={},
                scenes=[],
            )
            self.session.add(manga_prompt)

        await self.session.flush()
        await self.session.commit()  # 立即提交，确保中断时数据已保存
        logger.info("已保存生成进度: chapter_id=%d, status=%s", chapter_id, status)

    def _check_checkpoint_status(
        self,
        existing_prompt: Optional[ChapterMangaPrompt],
        current_version_id: Optional[int],
    ) -> tuple[str, dict]:
        """
        检查检查点状态

        Args:
            existing_prompt: 已存在的漫画提示词记录
            current_version_id: 当前章节版本ID

        Returns:
            (status, progress) 元组
        """
        if not existing_prompt:
            return "pending", {}

        progress = existing_prompt.generation_progress or {}
        status = existing_prompt.generation_status

        # 检查版本是否匹配，如果不匹配则需要重新开始
        if existing_prompt.source_version_id != current_version_id:
            logger.info("章节版本已变更，需要重新生成")
            return "pending", {}

        return status, progress

    def _should_resume_from_scene_extraction(
        self, status: str, progress: dict
    ) -> tuple[bool, Optional[list]]:
        """
        检查是否应从场景提取检查点恢复

        Args:
            status: 当前状态
            progress: 进度数据

        Returns:
            (should_resume, scene_summaries) 元组
        """
        if status == "scene_extracted" and "scene_summaries" in progress:
            logger.info("从检查点恢复: 场景提取已完成，继续排版生成")
            return True, progress["scene_summaries"]
        return False, None

    def _should_resume_from_layout(
        self, status: str, progress: dict, restore_layout_func: Any
    ) -> tuple[bool, Optional[list], Optional[Any]]:
        """
        检查是否应从排版检查点恢复

        Args:
            status: 当前状态
            progress: 进度数据
            restore_layout_func: 排版结果恢复函数

        Returns:
            (should_resume, scene_summaries, layout_result) 元组
        """
        if status == "layout_generated" and "layout_result" in progress:
            logger.info("从检查点恢复: 排版已完成，继续提示词生成")
            scene_summaries = progress.get("scene_summaries", [])
            layout_result = restore_layout_func(progress["layout_result"])
            return True, scene_summaries, layout_result
        return False, None, None
