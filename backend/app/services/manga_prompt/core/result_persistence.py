"""
结果持久化管理器

管理漫画生成过程中的旧数据清理。
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.manga_prompt_repository import MangaPromptRepository
from app.services.image_generation.service import ImageGenerationService

logger = logging.getLogger(__name__)


class ResultPersistence:
    """
    结果持久化管理器

    主要负责清理旧数据，确保重新生成时数据一致性。
    注意：保存结果直接使用 manga_prompt_repo.save_result()，不经过此类。
    """

    def __init__(
        self,
        session: AsyncSession,
        manga_prompt_repo: MangaPromptRepository,
        image_service: ImageGenerationService,
    ):
        """
        初始化管理器

        Args:
            session: 数据库会话
            manga_prompt_repo: 漫画提示词仓库
            image_service: 图片生成服务
        """
        self.session = session
        self.manga_prompt_repo = manga_prompt_repo
        self.image_service = image_service

    async def cleanup_old_data(
        self,
        project_id: str,
        chapter_number: int,
        chapter_id: Optional[int],
    ):
        """
        清理旧的分镜数据和相关图片

        在重新生成分镜时调用，确保数据一致性：
        1. 删除该章节的所有生成图片（文件和数据库记录）
        2. 清除旧的分镜提示词数据

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            chapter_id: 章节数据库ID
        """
        # 1. 删除该章节的所有生成图片
        deleted_images = await self.image_service.delete_chapter_images(
            project_id, chapter_number
        )
        if deleted_images > 0:
            logger.info(
                f"清理旧数据: 删除了 {deleted_images} 张图片 "
                f"(project={project_id}, chapter={chapter_number})"
            )

        # 2. 删除旧的分镜提示词数据（如果存在）
        if chapter_id:
            deleted = await self.manga_prompt_repo.delete_by_chapter_id(chapter_id)
            if deleted:
                logger.info(
                    f"清理旧数据: 删除了旧的分镜提示词 "
                    f"(project={project_id}, chapter={chapter_number})"
                )

        # 提交清理操作
        await self.session.commit()


__all__ = [
    "ResultPersistence",
]
