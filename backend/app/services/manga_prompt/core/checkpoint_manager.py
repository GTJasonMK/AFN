"""
断点管理器

管理漫画生成过程中的断点保存和恢复。
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.manga_prompt_repository import MangaPromptRepository

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    断点管理器

    管理漫画生成过程中的断点保存和恢复。
    新架构使用简化的断点存储，只存储可序列化的数据结构。
    """

    def __init__(self, session: AsyncSession, manga_prompt_repo: MangaPromptRepository):
        """
        初始化管理器

        Args:
            session: 数据库会话
            manga_prompt_repo: 漫画提示词仓库
        """
        self.session = session
        self.manga_prompt_repo = manga_prompt_repo

    async def save_checkpoint(
        self,
        chapter_id: int,
        status: str,
        progress: dict,
        checkpoint_data: dict,
        style: str,
        source_version_id: Optional[int],
    ):
        """
        保存断点并提交事务

        Args:
            chapter_id: 章节ID
            status: 当前状态
            progress: 进度信息
            checkpoint_data: 断点数据（包含 chapter_info, page_plan, storyboard）
            style: 漫画风格
            source_version_id: 源版本ID
        """
        await self.manga_prompt_repo.save_checkpoint(
            chapter_id=chapter_id,
            status=status,
            progress=progress,
            checkpoint_data=checkpoint_data,
            style=style,
            source_version_id=source_version_id,
        )
        await self.session.commit()

    async def get_checkpoint(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取断点数据

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            断点数据字典，包含：
            - status: 状态
            - progress: 进度信息
            - checkpoint_data: 断点数据
        """
        return await self.manga_prompt_repo.get_checkpoint(project_id, chapter_number)

    async def clear_checkpoint(
        self,
        chapter_id: int,
    ):
        """
        清除断点

        Args:
            chapter_id: 章节ID
        """
        await self.manga_prompt_repo.clear_checkpoint(chapter_id)
        await self.session.commit()


__all__ = [
    "CheckpointManager",
]
