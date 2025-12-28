"""
结果持久化管理器

管理漫画生成结果的保存、读取和删除。
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chapter_repository import ChapterRepository
from app.repositories.manga_prompt_repository import MangaPromptRepository
from app.services.image_generation.service import ImageGenerationService

from .models import MangaGenerationResult

logger = logging.getLogger(__name__)


class ResultPersistence:
    """
    结果持久化管理器

    管理漫画生成结果的保存、读取和删除
    """

    def __init__(
        self,
        session: AsyncSession,
        chapter_repo: ChapterRepository,
        manga_prompt_repo: MangaPromptRepository,
        image_service: ImageGenerationService,
    ):
        """
        初始化管理器

        Args:
            session: 数据库会话
            chapter_repo: 章节仓库
            manga_prompt_repo: 漫画提示词仓库
            image_service: 图片生成服务
        """
        self.session = session
        self.chapter_repo = chapter_repo
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

    async def save_result(
        self,
        project_id: str,
        chapter_number: int,
        result: MangaGenerationResult,
    ):
        """
        保存生成结果到数据库

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            result: 漫画生成结果
        """
        # 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            logger.warning(f"章节不存在: project={project_id}, chapter={chapter_number}")
            return

        # 将结果转为可存储的格式
        data = result.to_dict()

        # 获取当前选中的版本ID
        source_version_id = chapter.selected_version_id

        # 使用upsert保存
        await self.manga_prompt_repo.upsert(
            chapter_id=chapter.id,
            style=result.style,
            total_pages=result.get_total_pages(),
            total_panels=result.get_total_panels(),
            character_profiles=result.character_profiles,
            scenes=data["scenes"],
            panels=data["panels"],
            source_version_id=source_version_id,
        )

        logger.info(
            f"保存漫画分镜结果: project={project_id}, chapter={chapter_number}, "
            f"pages={result.get_total_pages()}, panels={result.get_total_panels()}"
        )

    async def get_result(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取已保存的生成结果

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            漫画分镜数据字典，不存在或未完成返回None
        """
        manga_prompt = await self.manga_prompt_repo.get_by_project_and_chapter(
            project_id, chapter_number
        )

        if not manga_prompt:
            return None

        # 确保是已完成的结果（有panels数据且状态为completed）
        # 如果只有断点数据但没有panels，不认为是完成的结果
        if not manga_prompt.panels or manga_prompt.generation_status != "completed":
            return None

        # 转换为API响应格式
        return {
            "chapter_number": chapter_number,
            "style": manga_prompt.style,
            "character_profiles": manga_prompt.character_profiles or {},
            "total_pages": manga_prompt.total_pages,
            "total_panels": manga_prompt.total_panels,
            "scenes": manga_prompt.scenes or [],
            "panels": manga_prompt.panels or [],
            "created_at": manga_prompt.created_at.isoformat() if manga_prompt.created_at else None,
        }

    async def delete_result(
        self,
        project_id: str,
        chapter_number: int,
    ) -> bool:
        """
        删除生成结果

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            是否删除成功
        """
        # 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            return False

        # 删除漫画提示词
        deleted = await self.manga_prompt_repo.delete_by_chapter_id(chapter.id)

        if deleted:
            logger.info(f"删除漫画分镜: project={project_id}, chapter={chapter_number}")

        return deleted


__all__ = [
    "ResultPersistence",
]
