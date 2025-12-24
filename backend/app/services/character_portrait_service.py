"""
角色立绘服务

负责角色立绘的生成、管理和存储。
"""

import uuid
import logging
import hashlib
import base64
from pathlib import Path
from typing import Optional, List, Dict, TYPE_CHECKING

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.character_portrait import CharacterPortrait
from ..repositories.character_portrait_repository import CharacterPortraitRepository
from ..schemas.character_portrait import (
    GeneratePortraitRequest,
    RegeneratePortraitRequest,
    CharacterPortraitResponse,
    get_style_prompt_prefix,
)
from .image_generation.schemas import ImageGenerationRequest

if TYPE_CHECKING:
    from .image_generation.service import ImageGenerationService
    from .image_generation.config_service import ImageConfigService

logger = logging.getLogger(__name__)

# 使用统一的路径配置
PORTRAITS_ROOT = settings.generated_images_dir


class CharacterPortraitService:
    """角色立绘服务

    职责：
    - 生成角色立绘（调用图片生成服务）
    - 管理立绘（激活、删除）
    - 存储立绘文件
    """

    def __init__(
        self,
        session: AsyncSession,
        image_service: Optional["ImageGenerationService"] = None,
    ):
        """
        初始化角色立绘服务

        Args:
            session: 数据库会话
            image_service: 图片生成服务（可选，用于生成立绘）
        """
        self.session = session
        self.repo = CharacterPortraitRepository(session)
        self._image_service = image_service

    @property
    def image_service(self) -> "ImageGenerationService":
        """获取图片生成服务（延迟初始化）"""
        if self._image_service is None:
            from .image_generation.service import ImageGenerationService
            self._image_service = ImageGenerationService(self.session)
        return self._image_service

    # ==================== 立绘生成 ====================

    async def generate_portrait(
        self,
        user_id: int,
        project_id: str,
        request: GeneratePortraitRequest,
    ) -> CharacterPortrait:
        """
        生成角色立绘

        Args:
            user_id: 用户ID
            project_id: 项目ID
            request: 生成请求

        Returns:
            CharacterPortrait: 生成的立绘记录

        Raises:
            Exception: 生成失败时抛出异常
        """
        # 1. 构建提示词
        prompt = self._build_portrait_prompt(
            character_name=request.character_name,
            character_description=request.character_description,
            style=request.style,
            custom_prompt=request.custom_prompt,
        )

        logger.info(
            "开始生成角色立绘: project=%s, character=%s, style=%s",
            project_id, request.character_name, request.style
        )

        # 2. 调用图片生成服务
        image_request = ImageGenerationRequest(
            prompt=prompt,
            negative_prompt=self._get_portrait_negative_prompt(),
            style=request.style,
            ratio="1:1",  # 立绘使用1:1比例
            resolution="1K",
            quality="high",
            count=1,
        )

        # 使用特殊的场景ID 0 表示立绘
        gen_result = await self.image_service.generate_image(
            user_id=user_id,
            project_id=project_id,
            chapter_number=0,  # 立绘不属于任何章节
            scene_id=0,  # 使用0表示立绘
            request=image_request,
        )

        if not gen_result.success:
            raise Exception(f"生成立绘失败: {gen_result.error_message}")

        if not gen_result.images:
            raise Exception("生成立绘失败: 未能获取到生成的图片")

        # 3. 移动图片到立绘目录并创建记录
        generated_image = gen_result.images[0]

        # 创建立绘专用目录
        safe_name = self._safe_character_name(request.character_name)
        portrait_dir = PORTRAITS_ROOT / project_id / "portraits" / safe_name
        portrait_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        portrait_id = str(uuid.uuid4())
        file_name = f"portrait_{portrait_id[:8]}_{request.style}.png"
        new_path = portrait_dir / file_name

        # 移动文件
        old_path = Path(generated_image.file_path)
        if old_path.exists():
            old_path.rename(new_path)
        else:
            logger.warning("原始图片文件不存在: %s", old_path)

        # 4. 取消同一角色的其他立绘激活状态
        existing_portraits = await self.repo.get_by_character(project_id, request.character_name)
        for p in existing_portraits:
            p.is_active = False
        await self.session.flush()

        # 5. 创建立绘记录
        # 使用正斜杠存储路径，确保URL兼容
        relative_path = str(new_path.relative_to(PORTRAITS_ROOT)).replace("\\", "/")
        portrait = CharacterPortrait(
            id=portrait_id,
            project_id=project_id,
            character_name=request.character_name,
            character_description=request.character_description,
            style=request.style,
            prompt=prompt,
            custom_prompt=request.custom_prompt,
            image_path=relative_path,
            file_name=file_name,
            file_size=generated_image.width * generated_image.height * 4 if generated_image.width else None,
            width=generated_image.width,
            height=generated_image.height,
            model_name=self.image_service.config_service and await self._get_model_name(user_id),
            is_active=True,
        )

        await self.repo.add(portrait)
        await self.session.flush()

        logger.info(
            "角色立绘生成成功: id=%s, character=%s, path=%s",
            portrait_id, request.character_name, relative_path
        )

        return portrait

    async def regenerate_portrait(
        self,
        user_id: int,
        portrait_id: str,
        request: Optional[RegeneratePortraitRequest] = None,
    ) -> CharacterPortrait:
        """
        重新生成立绘

        Args:
            user_id: 用户ID
            portrait_id: 要重新生成的立绘ID
            request: 重新生成请求（可选，用于更改风格或提示词）

        Returns:
            CharacterPortrait: 新生成的立绘记录
        """
        # 获取原立绘信息
        original = await self.repo.get_by_id(portrait_id)
        if not original:
            raise ValueError(f"立绘不存在: {portrait_id}")

        # 使用新参数或原参数
        style = (request.style if request and request.style else original.style)
        custom_prompt = (request.custom_prompt if request and request.custom_prompt else original.custom_prompt)

        # 生成新立绘
        gen_request = GeneratePortraitRequest(
            character_name=original.character_name,
            character_description=original.character_description,
            style=style,
            custom_prompt=custom_prompt,
        )

        return await self.generate_portrait(
            user_id=user_id,
            project_id=original.project_id,
            request=gen_request,
        )

    # ==================== 立绘管理 ====================

    async def get_portrait(self, portrait_id: str) -> Optional[CharacterPortrait]:
        """获取立绘"""
        return await self.repo.get_by_id(portrait_id)

    async def get_project_portraits(
        self,
        project_id: str,
    ) -> List[CharacterPortrait]:
        """获取项目的所有立绘"""
        return await self.repo.get_by_project(project_id)

    async def get_character_portraits(
        self,
        project_id: str,
        character_name: str,
    ) -> List[CharacterPortrait]:
        """获取角色的所有立绘"""
        return await self.repo.get_by_character(project_id, character_name)

    async def get_active_portrait(
        self,
        project_id: str,
        character_name: str,
    ) -> Optional[CharacterPortrait]:
        """获取角色当前激活的立绘"""
        return await self.repo.get_active_by_character(project_id, character_name)

    async def set_active_portrait(
        self,
        portrait_id: str,
    ) -> Optional[CharacterPortrait]:
        """设置立绘为激活状态"""
        return await self.repo.set_active(portrait_id)

    async def delete_portrait(
        self,
        portrait_id: str,
    ) -> bool:
        """
        删除立绘

        同时删除数据库记录和文件
        """
        portrait = await self.repo.get_by_id(portrait_id)
        if not portrait:
            return False

        # 删除文件
        if portrait.image_path:
            file_path = PORTRAITS_ROOT / portrait.image_path
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info("已删除立绘文件: %s", file_path)
                except Exception as e:
                    logger.warning("删除立绘文件失败: %s - %s", file_path, e)

        # 删除数据库记录
        await self.repo.delete(portrait)
        return True

    async def get_active_portraits_map(
        self,
        project_id: str,
    ) -> dict:
        """
        获取项目中所有角色的激活立绘映射

        Returns:
            dict: {角色名: 完整图片路径}，用于漫画生成时的img2img引用
        """
        portraits = await self.repo.get_all_active_by_project(project_id)
        return {
            portrait.character_name: str(PORTRAITS_ROOT / portrait.image_path)
            for portrait in portraits
            if portrait.image_path
        }

    # ==================== 辅助方法 ====================

    def _build_portrait_prompt(
        self,
        character_name: str,
        character_description: Optional[str],
        style: str,
        custom_prompt: Optional[str],
    ) -> str:
        """
        构建立绘生成提示词

        结构：
        [风格前缀], character portrait of [角色名], [角色描述], [自定义提示词], portrait shot, detailed face
        """
        parts = []

        # 1. 风格前缀
        style_prefix = get_style_prompt_prefix(style)
        parts.append(style_prefix)

        # 2. 角色描述
        if character_description:
            parts.append(f"character portrait of {character_name}, {character_description}")
        else:
            parts.append(f"character portrait of {character_name}")

        # 3. 自定义提示词
        if custom_prompt:
            parts.append(custom_prompt)

        # 4. 立绘通用后缀
        parts.append("portrait shot, detailed face, upper body, looking at viewer, simple background")

        return ", ".join(parts)

    def _get_portrait_negative_prompt(self) -> str:
        """获取立绘专用负面提示词"""
        return (
            "low quality, blurry, pixelated, watermark, signature, "
            "bad anatomy, wrong proportions, deformed hands, extra fingers, "
            "ugly face, deformed face, asymmetrical face, crossed eyes, "
            "multiple people, crowd, group shot, full body, legs, "
            "text, logo, frame, border"
        )

    def _safe_character_name(self, character_name: str) -> str:
        """清理角色名用于文件路径"""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in character_name)

    async def _get_model_name(self, user_id: int) -> Optional[str]:
        """获取当前激活的模型名称"""
        try:
            config = await self.image_service.config_service.get_active_config(user_id)
            return config.model_name if config else None
        except Exception:
            return None

    # ==================== 批量生成 ====================

    async def auto_generate_missing_portraits(
        self,
        user_id: int,
        project_id: str,
        character_profiles: Dict[str, str],
        style: str = "anime",
        exclude_existing: bool = True,
    ) -> Dict[str, CharacterPortrait]:
        """
        自动批量生成缺失的角色立绘

        在漫画生成流程中调用此方法，为没有立绘的角色自动生成立绘。
        生成的立绘会标记为次要角色（is_secondary=True）和自动生成（auto_generated=True）。

        Args:
            user_id: 用户ID
            project_id: 项目ID
            character_profiles: 角色外观描述字典 {角色名: 外观描述}
            style: 立绘风格 (anime/manga/realistic)
            exclude_existing: 是否排除已有立绘的角色

        Returns:
            Dict[str, CharacterPortrait]: 生成的立绘字典 {角色名: 立绘对象}
        """
        if not character_profiles:
            return {}

        generated_portraits = {}

        # 获取已有立绘的角色名
        existing_names = set()
        if exclude_existing:
            existing_portraits = await self.repo.get_all_active_by_project(project_id)
            existing_names = {p.character_name for p in existing_portraits}

        # 筛选需要生成立绘的角色
        characters_to_generate = {
            name: desc
            for name, desc in character_profiles.items()
            if name not in existing_names
        }

        if not characters_to_generate:
            logger.info(f"所有角色已有立绘，无需自动生成: project={project_id}")
            return {}

        logger.info(
            f"开始自动生成 {len(characters_to_generate)} 个角色的立绘: "
            f"project={project_id}, characters={list(characters_to_generate.keys())}"
        )

        # 逐个生成立绘
        for character_name, character_description in characters_to_generate.items():
            try:
                portrait = await self._generate_secondary_portrait(
                    user_id=user_id,
                    project_id=project_id,
                    character_name=character_name,
                    character_description=character_description,
                    style=style,
                )
                generated_portraits[character_name] = portrait
                logger.info(f"自动生成立绘成功: character={character_name}")
            except Exception as e:
                # 单个角色生成失败不影响其他角色
                logger.warning(f"自动生成立绘失败: character={character_name}, error={e}")
                continue

        logger.info(
            f"自动生成立绘完成: 成功 {len(generated_portraits)}/{len(characters_to_generate)}"
        )

        return generated_portraits

    async def _generate_secondary_portrait(
        self,
        user_id: int,
        project_id: str,
        character_name: str,
        character_description: str,
        style: str,
    ) -> CharacterPortrait:
        """
        生成次要角色立绘

        与 generate_portrait 类似，但会标记为次要角色和自动生成。

        Args:
            user_id: 用户ID
            project_id: 项目ID
            character_name: 角色名称
            character_description: 角色外观描述
            style: 立绘风格

        Returns:
            CharacterPortrait: 生成的立绘记录
        """
        # 1. 构建提示词
        prompt = self._build_portrait_prompt(
            character_name=character_name,
            character_description=character_description,
            style=style,
            custom_prompt=None,
        )

        logger.info(
            "开始生成次要角色立绘: project=%s, character=%s, style=%s",
            project_id, character_name, style
        )

        # 2. 调用图片生成服务
        image_request = ImageGenerationRequest(
            prompt=prompt,
            negative_prompt=self._get_portrait_negative_prompt(),
            style=style,
            ratio="1:1",
            resolution="1K",
            quality="high",
            count=1,
        )

        gen_result = await self.image_service.generate_image(
            user_id=user_id,
            project_id=project_id,
            chapter_number=0,
            scene_id=0,
            request=image_request,
        )

        if not gen_result.success:
            raise Exception(f"生成立绘失败: {gen_result.error_message}")

        if not gen_result.images:
            raise Exception("生成立绘失败: 未能获取到生成的图片")

        # 3. 移动图片到立绘目录并创建记录
        generated_image = gen_result.images[0]

        safe_name = self._safe_character_name(character_name)
        portrait_dir = PORTRAITS_ROOT / project_id / "portraits" / safe_name
        portrait_dir.mkdir(parents=True, exist_ok=True)

        portrait_id = str(uuid.uuid4())
        file_name = f"portrait_{portrait_id[:8]}_{style}.png"
        new_path = portrait_dir / file_name

        old_path = Path(generated_image.file_path)
        if old_path.exists():
            old_path.rename(new_path)
        else:
            logger.warning("原始图片文件不存在: %s", old_path)

        # 4. 取消同一角色的其他立绘激活状态
        existing_portraits = await self.repo.get_by_character(project_id, character_name)
        for p in existing_portraits:
            p.is_active = False
        await self.session.flush()

        # 5. 创建立绘记录（标记为次要角色和自动生成）
        relative_path = str(new_path.relative_to(PORTRAITS_ROOT)).replace("\\", "/")
        portrait = CharacterPortrait(
            id=portrait_id,
            project_id=project_id,
            character_name=character_name,
            character_description=character_description,
            style=style,
            prompt=prompt,
            custom_prompt=None,
            image_path=relative_path,
            file_name=file_name,
            file_size=generated_image.width * generated_image.height * 4 if generated_image.width else None,
            width=generated_image.width,
            height=generated_image.height,
            model_name=self.image_service.config_service and await self._get_model_name(user_id),
            is_active=True,
            is_secondary=True,  # 标记为次要角色
            auto_generated=True,  # 标记为自动生成
        )

        await self.repo.add(portrait)
        await self.session.flush()

        logger.info(
            "次要角色立绘生成成功: id=%s, character=%s, path=%s",
            portrait_id, character_name, relative_path
        )

        return portrait

    async def get_missing_characters(
        self,
        project_id: str,
        character_profiles: Dict[str, str],
    ) -> List[str]:
        """
        获取缺失立绘的角色列表

        Args:
            project_id: 项目ID
            character_profiles: 角色外观描述字典

        Returns:
            List[str]: 缺失立绘的角色名列表
        """
        existing_portraits = await self.repo.get_all_active_by_project(project_id)
        existing_names = {p.character_name for p in existing_portraits}

        return [name for name in character_profiles.keys() if name not in existing_names]
