"""
图片生成服务

负责图片生成和图片管理功能。
配置管理已拆分到 ImageConfigService。
"""

import asyncio
import time
import uuid
import base64
import hashlib
import logging
import shutil
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

import httpx


# ============================================================================
# 异步文件操作辅助函数
# ============================================================================

async def async_exists(path: Path) -> bool:
    """异步检查文件是否存在"""
    return await asyncio.to_thread(path.exists)


async def async_mkdir(path: Path, parents: bool = False, exist_ok: bool = False) -> None:
    """异步创建目录"""
    await asyncio.to_thread(path.mkdir, parents=parents, exist_ok=exist_ok)


async def async_read_bytes(path: Path) -> bytes:
    """异步读取文件内容"""
    return await asyncio.to_thread(path.read_bytes)


async def async_write_bytes(path: Path, data: bytes) -> None:
    """异步写入文件内容"""
    await asyncio.to_thread(path.write_bytes, data)


async def async_rename(src: Path, dst: Path) -> None:
    """异步重命名文件"""
    await asyncio.to_thread(src.rename, dst)


async def async_unlink(path: Path, missing_ok: bool = False) -> None:
    """异步删除文件"""
    await asyncio.to_thread(path.unlink, missing_ok=missing_ok)


async def async_rmdir(path: Path) -> None:
    """异步删除空目录"""
    await asyncio.to_thread(path.rmdir)


async def async_is_dir(path: Path) -> bool:
    """异步检查是否为目录"""
    return await asyncio.to_thread(path.is_dir)


async def async_iterdir(path: Path) -> List[Path]:
    """异步列出目录内容"""
    return await asyncio.to_thread(lambda: list(path.iterdir()))


from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    ImageGenerationRequest,
    ImageGenerationResult,
    GeneratedImageInfo,
    PageImageGenerationRequest,
    DEFAULT_MANGA_NEGATIVE_PROMPT,
)
from .providers import ImageProviderFactory
from .providers.base import ReferenceImageInfo
from ...models.image_config import GeneratedImage
from ...core.config import settings
from ...services.queue import ImageRequestQueue

if TYPE_CHECKING:
    from .config_service import ImageConfigService

logger = logging.getLogger(__name__)

NEGATIVE_PROMPT_QUALITY_KEYWORDS = [
    "模糊",
    "低质量",
    "变形",
    "扭曲",
    "多余",
    "禁止",
]


def _is_complete_negative_prompt(negative_prompt: str) -> bool:
    """检测负面提示词是否足够完整（由 LLM 生成）"""
    if not negative_prompt:
        return False

    prompt_lower = negative_prompt.lower()
    match_count = sum(1 for kw in NEGATIVE_PROMPT_QUALITY_KEYWORDS if kw in prompt_lower)
    return match_count >= 3


def smart_merge_negative_prompt(user_negative: Optional[str]) -> str:
    """智能合并负面提示词，避免重复追加默认值"""
    if not user_negative:
        return DEFAULT_MANGA_NEGATIVE_PROMPT

    if _is_complete_negative_prompt(user_negative):
        return user_negative

    return f"{DEFAULT_MANGA_NEGATIVE_PROMPT}, {user_negative}"


def get_images_root() -> Path:
    """获取图片根目录（支持热更新）"""
    return settings.generated_images_dir


# ============================================================================
# HTTP客户端管理（连接池复用）
# ============================================================================

class HTTPClientManager:
    """
    HTTP客户端管理器

    提供全局共享的httpx.AsyncClient，支持连接池复用。
    避免每次请求都创建新的TCP连接，提高性能。
    使用双重检查锁定模式确保线程安全。
    """
    _client: Optional[httpx.AsyncClient] = None
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """获取锁实例（必须在事件循环运行时调用）"""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """获取共享的HTTP客户端（懒加载，线程安全）"""
        # 第一次检查（无锁，快速路径）
        if cls._client is not None:
            return cls._client

        # 需要创建客户端，获取锁
        async with cls._get_lock():
            # 第二次检查（持锁，确保只创建一次）
            if cls._client is None:
                cls._client = httpx.AsyncClient(
                    timeout=60.0,
                    limits=httpx.Limits(
                        max_keepalive_connections=20,  # 保持活跃的连接数
                        max_connections=50,            # 最大连接数
                        keepalive_expiry=30.0,         # 连接过期时间（秒）
                    ),
                    http2=False,  # 禁用HTTP/2，避免需要额外安装h2包
                )
                logger.info("HTTP客户端已创建，连接池配置: max_connections=50, keepalive=20")
        return cls._client

    @classmethod
    async def close_client(cls) -> None:
        """关闭HTTP客户端（应用关闭时调用）"""
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None
            logger.info("HTTP客户端已关闭")


class ImageGenerationService:
    """图片生成服务

    职责：
    - 图片生成（调用供应商API）
    - 图片下载和保存
    - 图片管理（查询、删除）

    遵循单一职责原则，配置管理已拆分到 ImageConfigService。
    """

    def __init__(
        self,
        session: AsyncSession,
        config_service: Optional["ImageConfigService"] = None,
    ):
        """
        初始化图片生成服务

        Args:
            session: 数据库会话
            config_service: 配置服务（可选，用于获取激活配置）
        """
        self.session = session
        self._config_service = config_service

    @property
    def config_service(self) -> "ImageConfigService":
        """获取配置服务（延迟初始化）"""
        if self._config_service is None:
            from .config_service import ImageConfigService
            self._config_service = ImageConfigService(self.session)
        return self._config_service

    async def _resolve_portrait_paths(
        self,
        project_id: str,
        character_names: List[str],
    ) -> List[str]:
        """根据角色名获取当前激活的立绘路径"""
        if not character_names:
            return []

        from ...repositories.character_portrait_repository import CharacterPortraitRepository

        portrait_repo = CharacterPortraitRepository(self.session)
        active_portraits = await portrait_repo.get_all_active_by_project(project_id)
        portrait_map = {
            p.character_name: str(settings.generated_images_dir / p.image_path)
            for p in active_portraits
            if p.image_path
        }
        return [
            portrait_map[name] for name in character_names if name in portrait_map
        ]

    async def prepare_scene_request(
        self,
        project_id: str,
        request: ImageGenerationRequest,
    ) -> ImageGenerationRequest:
        """合并负面提示词与立绘路径（场景生图）"""
        merged_negative = smart_merge_negative_prompt(request.negative_prompt)
        reference_image_paths = request.reference_image_paths or []

        if request.characters:
            dynamic_paths = await self._resolve_portrait_paths(
                project_id, request.characters
            )
            if dynamic_paths:
                reference_image_paths = dynamic_paths
                logger.info(
                    "动态获取立绘路径: characters=%s, paths=%d",
                    request.characters, len(dynamic_paths)
                )

        return ImageGenerationRequest(
            prompt=request.prompt,
            negative_prompt=merged_negative,
            style=request.style,
            ratio=request.ratio,
            resolution=request.resolution,
            quality=request.quality,
            count=request.count,
            seed=request.seed,
            chapter_version_id=request.chapter_version_id,
            panel_id=request.panel_id,
            reference_image_paths=reference_image_paths if reference_image_paths else None,
            reference_strength=request.reference_strength,
            dialogue=request.dialogue,
            dialogue_speaker=request.dialogue_speaker,
            dialogue_bubble_type=request.dialogue_bubble_type,
            dialogue_emotion=request.dialogue_emotion,
            dialogue_position=request.dialogue_position,
            narration=request.narration,
            narration_position=request.narration_position,
            sound_effects=request.sound_effects,
            sound_effect_details=request.sound_effect_details,
            composition=request.composition,
            camera_angle=request.camera_angle,
            is_key_panel=request.is_key_panel,
            characters=request.characters,
            lighting=request.lighting,
            atmosphere=request.atmosphere,
            key_visual_elements=request.key_visual_elements,
            dialogue_language=request.dialogue_language,
        )

    async def prepare_page_request(
        self,
        project_id: str,
        request: PageImageGenerationRequest,
    ) -> PageImageGenerationRequest:
        """合并负面提示词与立绘路径（整页生图）"""
        merged_negative = smart_merge_negative_prompt(request.negative_prompt)
        reference_image_paths = request.reference_image_paths or []

        all_characters = set()
        for panel in request.panel_summaries or []:
            characters = panel.get("characters", [])
            all_characters.update(characters)

        if all_characters:
            dynamic_paths = await self._resolve_portrait_paths(
                project_id, list(all_characters)
            )
            if dynamic_paths:
                reference_image_paths = dynamic_paths
                logger.info(
                    "整页生成: 动态获取立绘路径, characters=%s, paths=%d",
                    list(all_characters), len(dynamic_paths)
                )

        return PageImageGenerationRequest(
            full_page_prompt=request.full_page_prompt,
            negative_prompt=merged_negative,
            layout_template=request.layout_template,
            layout_description=request.layout_description,
            ratio=request.ratio,
            resolution=request.resolution,
            style=request.style,
            chapter_version_id=request.chapter_version_id,
            reference_image_paths=reference_image_paths if reference_image_paths else None,
            reference_strength=request.reference_strength,
            panel_summaries=request.panel_summaries,
            dialogue_language=request.dialogue_language,
        )

    # ==================== 图片生成 ====================

    async def generate_image(
        self,
        user_id: int,
        project_id: str,
        chapter_number: int,
        scene_id: int,
        request: ImageGenerationRequest,
    ) -> ImageGenerationResult:
        """
        生成图片（使用工厂模式）

        支持普通文生图和 img2img（使用参考图）。
        当 request.reference_image_paths 不为空时，自动使用 img2img 模式。

        Args:
            user_id: 用户ID
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID
            request: 生成请求

        Returns:
            ImageGenerationResult: 生成结果
        """
        start_time = time.time()

        # 如果指定了panel_id，先删除该画格的旧图片（保持每个画格只有一张图片）
        if request.panel_id:
            deleted_count = await self.delete_panel_images(
                project_id=project_id,
                chapter_number=chapter_number,
                panel_id=request.panel_id,
            )
            if deleted_count > 0:
                logger.info(
                    "重新生成前已删除旧图片: panel_id=%s, count=%d",
                    request.panel_id, deleted_count
                )

        # 获取激活的配置（通过配置服务）
        config = await self.config_service.get_active_config(user_id)
        if not config:
            # 检查是否有配置但未激活
            all_configs = await self.config_service.get_configs(user_id)
            if all_configs:
                # 有配置但未激活
                config_names = ", ".join(c.config_name for c in all_configs[:3])
                if len(all_configs) > 3:
                    config_names += f" 等{len(all_configs)}个"
                return ImageGenerationResult(
                    success=False,
                    error_message=f"请先激活图片生成配置。已有配置: {config_names}，请在设置中选择并激活",
                )
            else:
                # 没有任何配置
                return ImageGenerationResult(
                    success=False,
                    error_message="未配置图片生成服务，请先在设置中添加配置",
                )

        try:
            # 使用工厂获取对应的供应商
            provider = ImageProviderFactory.get_provider(config.provider_type)
            if not provider:
                return ImageGenerationResult(
                    success=False,
                    error_message=f"不支持的提供商类型: {config.provider_type}",
                )

            # 通过队列控制并发
            queue = ImageRequestQueue.get_instance()
            async with queue.request_slot():
                # 检查是否需要使用 img2img
                if request.reference_image_paths and len(request.reference_image_paths) > 0:
                    logger.info(
                        "准备参考图: 路径数量=%d, get_images_root()=%s",
                        len(request.reference_image_paths), get_images_root()
                    )
                    for i, p in enumerate(request.reference_image_paths[:3]):  # 只打印前3个
                        logger.info("  参考图路径[%d]: %s", i, p)

                    # 准备参考图信息
                    reference_images = await self._prepare_reference_images(
                        request.reference_image_paths,
                        request.reference_strength,
                    )

                    if reference_images:
                        if provider.supports_img2img():
                            # 使用 img2img 模式
                            logger.info(
                                "使用 img2img 模式生成图片: provider=%s, reference_count=%d",
                                config.provider_type, len(reference_images)
                            )
                            gen_result = await provider.generate_with_reference(
                                config, request, reference_images
                            )
                        else:
                            # 供应商不支持 img2img，降级为普通生成
                            logger.warning(
                                "供应商 %s 不支持 img2img，降级为普通生成",
                                config.provider_type
                            )
                            gen_result = await provider.generate(config, request)
                    else:
                        # 参考图加载失败，降级为普通生成
                        logger.warning(
                            "参考图加载失败（共 %d 个路径），降级为普通生成",
                            len(request.reference_image_paths)
                        )
                        gen_result = await provider.generate(config, request)
                else:
                    # 普通文生图
                    gen_result = await provider.generate(config, request)

            if not gen_result.success:
                return ImageGenerationResult(
                    success=False,
                    error_message=gen_result.error_message,
                )

            if not gen_result.image_urls:
                return ImageGenerationResult(
                    success=False,
                    error_message="未能获取到生成的图片",
                )

            # 下载并保存图片（传递宽高比用于后处理裁切）
            saved_images = await self._download_and_save_images(
                image_urls=gen_result.image_urls,
                project_id=project_id,
                chapter_number=chapter_number,
                scene_id=scene_id,
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                model_name=config.model_name,
                style=request.style,
                chapter_version_id=request.chapter_version_id,
                panel_id=request.panel_id,
                target_aspect_ratio=request.ratio,  # 用于后处理裁切
            )

            generation_time = time.time() - start_time

            return ImageGenerationResult(
                success=True,
                images=saved_images,
                generation_time=generation_time,
            )

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            logger.error(f"图片生成失败: {error_msg}", exc_info=True)
            return ImageGenerationResult(
                success=False,
                error_message=error_msg,
            )

    async def generate_page_image(
        self,
        user_id: int,
        project_id: str,
        chapter_number: int,
        page_number: int,
        request: PageImageGenerationRequest,
    ) -> ImageGenerationResult:
        """
        生成整页漫画图片

        让AI直接生成带分格布局的整页漫画，包含对话气泡和音效文字。
        相比逐panel生成，整页生成的画面更统一，布局更自然。

        Args:
            user_id: 用户ID
            project_id: 项目ID
            chapter_number: 章节号
            page_number: 页码
            request: 页面级生成请求

        Returns:
            ImageGenerationResult: 生成结果
        """
        start_time = time.time()

        # 构建 page_id 用于标识整页图片
        page_id = f"page{page_number}"

        # 先删除该页的旧图片（保持每页只有一张整页图片）
        deleted_count = await self.delete_page_images(
            project_id=project_id,
            chapter_number=chapter_number,
            page_number=page_number,
        )
        if deleted_count > 0:
            logger.info(
                "重新生成整页前已删除旧图片: page=%d, count=%d",
                page_number, deleted_count
            )

        # 获取激活的配置
        config = await self.config_service.get_active_config(user_id)
        if not config:
            all_configs = await self.config_service.get_configs(user_id)
            if all_configs:
                config_names = ", ".join(c.config_name for c in all_configs[:3])
                if len(all_configs) > 3:
                    config_names += f" 等{len(all_configs)}个"
                return ImageGenerationResult(
                    success=False,
                    error_message=f"请先激活图片生成配置。已有配置: {config_names}，请在设置中选择并激活",
                )
            else:
                return ImageGenerationResult(
                    success=False,
                    error_message="未配置图片生成服务，请先在设置中添加配置",
                )

        try:
            # 使用工厂获取对应的供应商
            provider = ImageProviderFactory.get_provider(config.provider_type)
            if not provider:
                return ImageGenerationResult(
                    success=False,
                    error_message=f"不支持的提供商类型: {config.provider_type}",
                )

            # 构建内部生成请求（复用现有的 ImageGenerationRequest）
            internal_request = ImageGenerationRequest(
                prompt=request.full_page_prompt,
                negative_prompt=request.negative_prompt,
                style=request.style,
                ratio=request.ratio,
                resolution=request.resolution,
                count=1,  # 整页生成只需要1张
                panel_id=page_id,  # 使用 page_id 作为标识
                chapter_version_id=request.chapter_version_id,
                reference_image_paths=request.reference_image_paths,
                reference_strength=request.reference_strength,
                dialogue_language=request.dialogue_language,
            )

            # 通过队列控制并发
            queue = ImageRequestQueue.get_instance()
            async with queue.request_slot():
                # 检查是否需要使用 img2img
                if request.reference_image_paths and len(request.reference_image_paths) > 0:
                    reference_images = await self._prepare_reference_images(
                        request.reference_image_paths,
                        request.reference_strength,
                    )

                    if reference_images and provider.supports_img2img():
                        logger.info(
                            "整页生成使用 img2img 模式: provider=%s, reference_count=%d",
                            config.provider_type, len(reference_images)
                        )
                        gen_result = await provider.generate_with_reference(
                            config, internal_request, reference_images
                        )
                    else:
                        gen_result = await provider.generate(config, internal_request)
                else:
                    gen_result = await provider.generate(config, internal_request)

            if not gen_result.success:
                return ImageGenerationResult(
                    success=False,
                    error_message=gen_result.error_message,
                )

            if not gen_result.image_urls:
                return ImageGenerationResult(
                    success=False,
                    error_message="未能获取到生成的图片",
                )

            # 下载并保存图片（整页使用 scene_id = page_number）
            saved_images = await self._download_and_save_images(
                image_urls=gen_result.image_urls,
                project_id=project_id,
                chapter_number=chapter_number,
                scene_id=page_number,  # 使用页码作为 scene_id
                prompt=request.full_page_prompt,
                negative_prompt=request.negative_prompt,
                model_name=config.model_name,
                style=request.style,
                chapter_version_id=request.chapter_version_id,
                panel_id=page_id,  # 标识为整页图片
                target_aspect_ratio=request.ratio,
                image_type="page",  # 标记为整页类型
            )

            generation_time = time.time() - start_time

            logger.info(
                "整页漫画生成完成: project=%s, chapter=%d, page=%d, time=%.2fs",
                project_id, chapter_number, page_number, generation_time
            )

            return ImageGenerationResult(
                success=True,
                images=saved_images,
                generation_time=generation_time,
            )

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            logger.error(f"整页图片生成失败: {error_msg}", exc_info=True)
            return ImageGenerationResult(
                success=False,
                error_message=error_msg,
            )

    async def delete_page_images(
        self,
        project_id: str,
        chapter_number: int,
        page_number: int,
    ) -> int:
        """删除页面的整页图片

        用于重新生成整页图片时清理旧图片。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            page_number: 页码

        Returns:
            删除的图片数量
        """
        page_id = f"page{page_number}"

        # 查询该页的整页图片
        result = await self.session.execute(
            select(GeneratedImage).where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
                GeneratedImage.panel_id == page_id,
            )
        )
        images = list(result.scalars().all())

        if not images:
            return 0

        deleted_count = 0
        for image in images:
            file_path = get_images_root() / image.file_path
            if await async_exists(file_path):
                try:
                    await async_unlink(file_path)
                    logger.debug("已删除整页图片文件: %s", file_path)
                except Exception as e:
                    logger.warning("删除整页图片文件失败: %s - %s", file_path, e)

            await self.session.delete(image)
            deleted_count += 1

        await self.session.flush()

        logger.info(
            "已删除整页旧图片: project_id=%s, chapter=%d, page=%d, count=%d",
            project_id, chapter_number, page_number, deleted_count
        )
        return deleted_count

    async def _prepare_reference_images(
        self,
        image_paths: List[str],
        strength: float = 0.7,
    ) -> List[ReferenceImageInfo]:
        """
        准备参考图信息

        读取图片文件并转换为 Base64 格式。
        使用异步文件操作避免阻塞事件循环。

        Args:
            image_paths: 图片路径列表
            strength: 参考强度

        Returns:
            参考图信息列表
        """
        reference_images = []

        for path in image_paths:
            try:
                full_path = None

                # 1. 如果是绝对路径，直接使用
                if Path(path).is_absolute():
                    full_path = Path(path)
                    if await async_exists(full_path):
                        logger.debug("使用绝对路径: %s", full_path)
                    else:
                        full_path = None

                # 2. 尝试作为相对于 get_images_root() 的路径
                if full_path is None:
                    candidate = get_images_root() / path
                    if await async_exists(candidate):
                        full_path = candidate
                        logger.debug("使用 get_images_root() 相对路径: %s", full_path)

                # 3. 如果路径以 / 开头，去掉后再尝试
                if full_path is None and path.startswith("/"):
                    candidate = get_images_root() / path.lstrip("/")
                    if await async_exists(candidate):
                        full_path = candidate
                        logger.debug("使用去除前缀的路径: %s", full_path)

                if full_path is None:
                    logger.warning(
                        "参考图片不存在: %s (尝试的完整路径: %s)",
                        path, get_images_root() / path
                    )
                    continue

                # 异步读取并转换为 Base64
                image_content = await async_read_bytes(full_path)
                b64_data = base64.b64encode(image_content).decode("utf-8")

                reference_images.append(ReferenceImageInfo(
                    file_path=str(full_path),
                    base64_data=b64_data,
                    strength=strength,
                ))

                logger.debug("已加载参考图: %s", path)

            except Exception as e:
                logger.warning("加载参考图失败: %s - %s", path, e)
                continue

        return reference_images

    async def _crop_to_aspect_ratio(
        self,
        image_content: bytes,
        target_ratio: str,
    ) -> bytes:
        """
        将图片裁切到目标宽高比（中心裁切）

        核心优化：解决AI生图模型不严格遵循宽高比的问题。
        通过后处理强制裁切，确保图片比例与画格匹配，消除留白。

        Args:
            image_content: 原始图片bytes
            target_ratio: 目标宽高比，如 "16:9", "4:3", "1:1"

        Returns:
            裁切后的图片bytes
        """
        try:
            from PIL import Image
            import io

            # 解析目标比例
            if ":" not in target_ratio:
                logger.debug("无效的宽高比格式: %s，跳过裁切", target_ratio)
                return image_content

            parts = target_ratio.split(":")
            if len(parts) != 2:
                return image_content

            try:
                w_ratio, h_ratio = float(parts[0]), float(parts[1])
                if h_ratio == 0:
                    return image_content
                target_aspect = w_ratio / h_ratio
            except ValueError:
                return image_content

            # 打开图片
            img = Image.open(io.BytesIO(image_content))
            if img.width == 0 or img.height == 0:
                return image_content

            current_aspect = img.width / img.height

            # 如果比例相近（误差<5%），不裁切
            if abs(current_aspect - target_aspect) / max(target_aspect, 0.01) < 0.05:
                logger.debug(
                    "图片比例 %.2f 接近目标 %.2f，无需裁切",
                    current_aspect, target_aspect
                )
                return image_content

            # 中心裁切
            if current_aspect > target_aspect:
                # 图片太宽，裁左右
                new_width = int(img.height * target_aspect)
                left = (img.width - new_width) // 2
                crop_box = (left, 0, left + new_width, img.height)
                logger.debug(
                    "图片太宽，中心裁切: %dx%d -> %dx%d",
                    img.width, img.height, new_width, img.height
                )
            else:
                # 图片太高，裁上下
                new_height = int(img.width / target_aspect)
                top = (img.height - new_height) // 2
                crop_box = (0, top, img.width, top + new_height)
                logger.debug(
                    "图片太高，中心裁切: %dx%d -> %dx%d",
                    img.width, img.height, img.width, new_height
                )

            cropped = img.crop(crop_box)

            # 转回bytes
            output = io.BytesIO()
            # 保持原始格式，如果是PNG则保持PNG
            img_format = img.format or "PNG"
            cropped.save(output, format=img_format)
            return output.getvalue()

        except Exception as e:
            logger.warning("图片裁切失败，使用原图: %s", e)
            return image_content

    async def _download_and_save_images(
        self,
        image_urls: List[str],
        project_id: str,
        chapter_number: int,
        scene_id: int,
        prompt: str,
        negative_prompt: Optional[str],
        model_name: Optional[str],
        style: Optional[str],
        chapter_version_id: Optional[int] = None,
        panel_id: Optional[str] = None,
        target_aspect_ratio: Optional[str] = None,
        image_type: str = "panel",
    ) -> List[GeneratedImageInfo]:
        """下载并保存图片

        支持两种URL格式：
        1. 标准HTTP(S) URL：从远程服务器下载图片
        2. Base64数据URL（data:image/png;base64,...）：直接解码保存

        使用异步文件操作避免阻塞事件循环。

        Args:
            chapter_version_id: 章节版本ID，用于版本追溯
            panel_id: 画格ID，用于精确匹配
            target_aspect_ratio: 目标宽高比，如 "16:9"，用于后处理裁切
            image_type: 图片类型 "panel"(单画格) 或 "page"(整页)
        """

        saved_images = []

        # 异步确保目录存在
        # 根据图片类型分目录存储：panels/ 或 pages/
        type_subdir = "pages" if image_type == "page" else "panels"
        save_dir = get_images_root() / project_id / f"chapter_{chapter_number}" / type_subdir / f"scene_{scene_id}"
        await async_mkdir(save_dir, parents=True, exist_ok=True)

        # 使用共享的HTTP客户端（连接池复用）
        client = await HTTPClientManager.get_client()

        for i, url in enumerate(image_urls):
            try:
                # 检查是否是Base64数据URL
                if url.startswith("data:image/"):
                    # 解析Base64数据URL
                    # 格式: data:image/png;base64,<base64_data>
                    try:
                        header, b64_data = url.split(",", 1)
                        # 安全检查：限制Base64数据大小（50MB）
                        MAX_BASE64_SIZE = 50 * 1024 * 1024  # 50MB
                        if len(b64_data) > MAX_BASE64_SIZE:
                            logger.warning(
                                "Base64图片数据过大: %d bytes (max: %d), scene_id=%d",
                                len(b64_data), MAX_BASE64_SIZE, scene_id
                            )
                            continue
                        image_content = base64.b64decode(b64_data)
                    except Exception as e:
                        logger.warning(
                            "解析Base64图片数据失败: %s, scene_id=%d", e, scene_id
                        )
                        continue
                else:
                    # 标准HTTP下载
                    response = await client.get(url)
                    if response.status_code != 200:
                        logger.warning(f"下载图片失败: {url}, status={response.status_code}")
                        continue
                    image_content = response.content

                # 后处理：裁切到目标宽高比（解决AI生图不遵循比例的问题）
                if target_aspect_ratio:
                    image_content = await self._crop_to_aspect_ratio(
                        image_content, target_aspect_ratio
                    )

                # 生成唯一文件名（使用UUID保证唯一性，避免并发冲突）
                unique_id = uuid.uuid4().hex[:12]  # 12位足够避免冲突
                content_hash = hashlib.sha256(image_content).hexdigest()[:8]
                file_name = f"img_{unique_id}_{content_hash}.png"
                file_path = save_dir / file_name

                # 原子写入：先写入临时文件，再重命名（防止写入中断导致文件损坏）
                temp_path = save_dir / f".tmp_{unique_id}.png"
                try:
                    await async_write_bytes(temp_path, image_content)
                    await async_rename(temp_path, file_path)  # rename在大多数文件系统上是原子操作
                except Exception:
                    # 异步清理临时文件
                    if await async_exists(temp_path):
                        await async_unlink(temp_path)
                    raise

                # 创建数据库记录
                # 对于Base64数据URL，source_url存储为空（数据太大）
                source_url_to_save = url if not url.startswith("data:") else None
                image_record = GeneratedImage(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    scene_id=scene_id,
                    panel_id=panel_id,  # 画格ID
                    chapter_version_id=chapter_version_id,  # 版本追溯
                    file_name=file_name,
                    file_path=str(file_path.relative_to(get_images_root())),
                    file_size=len(image_content),
                    mime_type="image/png",
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model_name,
                    style=style,
                    source_url=source_url_to_save,
                    image_type=image_type,  # 图片类型：panel或page
                )
                self.session.add(image_record)
                await self.session.flush()

                # 构建访问URL
                access_url = f"/api/images/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{file_name}"

                saved_images.append(
                    GeneratedImageInfo(
                        id=image_record.id,
                        file_name=file_name,
                        file_path=str(file_path),
                        url=access_url,
                        scene_id=scene_id,
                        panel_id=panel_id,
                        prompt=prompt,
                        created_at=image_record.created_at,
                    )
                )

            except Exception as e:
                error_msg = str(e) if str(e) else f"{type(e).__name__}"
                logger.error(f"保存图片失败: {error_msg}", exc_info=True)
                continue

        return saved_images

    # ==================== 图片管理 ====================

    async def get_scene_images(
        self,
        project_id: str,
        chapter_number: int,
        scene_id: int,
    ) -> List[GeneratedImage]:
        """获取场景的所有图片"""
        result = await self.session.execute(
            select(GeneratedImage)
            .where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
                GeneratedImage.scene_id == scene_id,
            )
            .order_by(GeneratedImage.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_chapter_images(
        self,
        project_id: str,
        chapter_number: int,
        version_id: Optional[int] = None,
        include_legacy: bool = False,
    ) -> List[GeneratedImage]:
        """获取章节的图片

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            version_id: 章节版本ID，用于过滤特定版本的图片
            include_legacy: 是否包含历史版本的图片（无版本ID的旧数据）

        Returns:
            图片列表，按场景ID和创建时间排序
        """

        query = select(GeneratedImage).where(
            GeneratedImage.project_id == project_id,
            GeneratedImage.chapter_number == chapter_number,
        )

        # P1修复: 版本过滤逻辑
        # - include_legacy=False（默认）: 严格匹配指定版本，不包含历史数据
        # - include_legacy=True: 同时包含指定版本和无版本ID的历史数据（向后兼容）
        if version_id is not None:
            if include_legacy:
                # 包含指定版本 + 无版本ID的历史数据
                query = query.where(
                    or_(
                        GeneratedImage.chapter_version_id == version_id,
                        GeneratedImage.chapter_version_id.is_(None),
                    )
                )
            else:
                # 严格匹配指定版本，不包含历史数据
                query = query.where(
                    GeneratedImage.chapter_version_id == version_id
                )

        result = await self.session.execute(
            query.order_by(GeneratedImage.scene_id, GeneratedImage.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_image(self, image_id: int) -> bool:
        """删除图片（使用异步文件操作）"""
        result = await self.session.execute(
            select(GeneratedImage).where(GeneratedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return False

        # 异步删除文件
        file_path = get_images_root() / image.file_path
        if await async_exists(file_path):
            await async_unlink(file_path)

        # 删除数据库记录
        await self.session.delete(image)
        await self.session.flush()
        return True

    async def delete_panel_images(
        self,
        project_id: str,
        chapter_number: int,
        panel_id: str,
    ) -> int:
        """删除画格的所有图片

        用于重新生成画格图片时清理旧图片，确保每个画格只保留最新生成的图片。
        使用异步文件操作避免阻塞事件循环。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            panel_id: 画格ID

        Returns:
            删除的图片数量
        """
        # 查询该画格的所有图片
        result = await self.session.execute(
            select(GeneratedImage).where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
                GeneratedImage.panel_id == panel_id,
            )
        )
        images = list(result.scalars().all())

        if not images:
            return 0

        deleted_count = 0
        for image in images:
            # 异步删除文件
            file_path = get_images_root() / image.file_path
            if await async_exists(file_path):
                try:
                    await async_unlink(file_path)
                    logger.debug("已删除图片文件: %s", file_path)
                except Exception as e:
                    logger.warning("删除图片文件失败: %s - %s", file_path, e)

            # 删除数据库记录
            await self.session.delete(image)
            deleted_count += 1

        await self.session.flush()

        logger.info(
            "已删除画格旧图片: project_id=%s, chapter=%d, panel_id=%s, count=%d",
            project_id, chapter_number, panel_id, deleted_count
        )
        return deleted_count

    async def delete_chapter_images(
        self,
        project_id: str,
        chapter_number: int,
    ) -> int:
        """删除章节的所有图片

        用于重新生成漫画提示词时清理旧图片。
        使用异步文件操作避免阻塞事件循环。

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            删除的图片数量
        """
        # 查询该章节的所有图片
        result = await self.session.execute(
            select(GeneratedImage).where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
            )
        )
        images = list(result.scalars().all())

        if not images:
            return 0

        deleted_count = 0
        for image in images:
            # 异步删除文件
            file_path = get_images_root() / image.file_path
            if await async_exists(file_path):
                try:
                    await async_unlink(file_path)
                except Exception as e:
                    logger.warning("删除图片文件失败: %s - %s", file_path, e)

            # 删除数据库记录
            await self.session.delete(image)
            deleted_count += 1

        await self.session.flush()

        # 尝试异步清理空目录（支持新的 panels/pages 子目录结构）
        try:
            chapter_dir = get_images_root() / project_id / f"chapter_{chapter_number}"
            if await async_exists(chapter_dir):
                # 遍历 panels/ 和 pages/ 子目录
                type_dirs = await async_iterdir(chapter_dir)
                for type_dir in type_dirs:
                    if await async_is_dir(type_dir):
                        # 删除空的场景子目录
                        scene_dirs = await async_iterdir(type_dir)
                        for scene_dir in scene_dirs:
                            if await async_is_dir(scene_dir):
                                scene_contents = await async_iterdir(scene_dir)
                                if not scene_contents:
                                    await async_rmdir(scene_dir)
                        # 如果类型目录也空了，删除它
                        type_contents = await async_iterdir(type_dir)
                        if not type_contents:
                            await async_rmdir(type_dir)
                # 如果章节目录也空了，删除它
                chapter_contents = await async_iterdir(chapter_dir)
                if not chapter_contents:
                    await async_rmdir(chapter_dir)
        except Exception as e:
            logger.warning("清理空目录失败: %s", e)

        logger.info(
            "已删除章节图片: project_id=%s, chapter=%d, count=%d",
            project_id, chapter_number, deleted_count
        )
        return deleted_count

    async def delete_chapter_images_by_type(
        self,
        project_id: str,
        chapter_number: int,
        image_type: str,
    ) -> int:
        """按类型删除章节的图片

        用于重新生成某种类型的图片时清理旧图片。
        例如重新生成整页图片时只删除page类型，保留panel类型。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            image_type: 图片类型 "panel"(单画格) 或 "page"(整页)

        Returns:
            删除的图片数量
        """
        # 查询该章节指定类型的图片
        result = await self.session.execute(
            select(GeneratedImage).where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
                GeneratedImage.image_type == image_type,
            )
        )
        images = list(result.scalars().all())

        if not images:
            return 0

        deleted_count = 0
        for image in images:
            # 异步删除文件
            file_path = get_images_root() / image.file_path
            if await async_exists(file_path):
                try:
                    await async_unlink(file_path)
                except Exception as e:
                    logger.warning("删除图片文件失败: %s - %s", file_path, e)

            # 删除数据库记录
            await self.session.delete(image)
            deleted_count += 1

        await self.session.flush()

        # 尝试异步清理空目录
        try:
            type_subdir = "pages" if image_type == "page" else "panels"
            type_dir = get_images_root() / project_id / f"chapter_{chapter_number}" / type_subdir
            if await async_exists(type_dir):
                # 删除空的场景子目录
                scene_dirs = await async_iterdir(type_dir)
                for scene_dir in scene_dirs:
                    if await async_is_dir(scene_dir):
                        scene_contents = await async_iterdir(scene_dir)
                        if not scene_contents:
                            await async_rmdir(scene_dir)
                # 如果类型目录也空了，删除它
                type_contents = await async_iterdir(type_dir)
                if not type_contents:
                    await async_rmdir(type_dir)
        except Exception as e:
            logger.warning("清理空目录失败: %s", e)

        logger.info(
            "已删除章节%s类型图片: project_id=%s, chapter=%d, count=%d",
            image_type, project_id, chapter_number, deleted_count
        )
        return deleted_count

    async def toggle_image_selection(self, image_id: int, selected: bool) -> bool:
        """切换图片选中状态（用于PDF导出）"""
        result = await self.session.execute(
            select(GeneratedImage).where(GeneratedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return False

        image.is_selected = selected
        await self.session.flush()
        return True

    # ==================== 提示词预览 ====================

    async def preview_prompt(
        self,
        user_id: int,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: Optional[str] = None,
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        # 漫画画格元数据 - 对话相关
        dialogue: Optional[str] = None,
        dialogue_speaker: Optional[str] = None,
        dialogue_bubble_type: Optional[str] = None,
        dialogue_emotion: Optional[str] = None,
        dialogue_position: Optional[str] = None,
        # 漫画画格元数据 - 旁白相关
        narration: Optional[str] = None,
        narration_position: Optional[str] = None,
        # 漫画画格元数据 - 音效相关
        sound_effects: Optional[List[str]] = None,
        sound_effect_details: Optional[List[dict]] = None,
        # 漫画画格元数据 - 视觉相关
        composition: Optional[str] = None,
        camera_angle: Optional[str] = None,
        is_key_panel: bool = False,
        characters: Optional[List[str]] = None,
        lighting: Optional[str] = None,
        atmosphere: Optional[str] = None,
        key_visual_elements: Optional[List[str]] = None,
        # 语言设置
        dialogue_language: Optional[str] = None,
    ) -> dict:
        """
        预览处理后的提示词（不生成图片）

        展示发送给生图模型的实际提示词，包括：
        - 场景类型检测结果
        - 动态添加的上下文前缀
        - 风格后缀（如果需要）
        - 分辨率后缀（如果需要）
        - 宽高比描述
        - 漫画视觉元素（对话、旁白、音效、构图、镜头等）
        - 语言约束
        - 负面提示词

        Args:
            user_id: 用户ID
            prompt: 原始提示词
            negative_prompt: 负面提示词
            style: 风格
            ratio: 宽高比
            resolution: 分辨率
            dialogue: 对话内容
            dialogue_speaker: 对话说话者
            dialogue_bubble_type: 气泡类型
            dialogue_emotion: 说话情绪
            dialogue_position: 气泡位置
            narration: 旁白内容
            narration_position: 旁白位置
            sound_effects: 音效列表
            sound_effect_details: 详细音效信息
            composition: 构图
            camera_angle: 镜头角度
            is_key_panel: 是否为关键画格
            characters: 角色列表
            lighting: 光线描述
            atmosphere: 氛围描述
            key_visual_elements: 关键视觉元素
            dialogue_language: 对话/文字语言（chinese/japanese/english/korean）

        Returns:
            包含预览信息的字典
        """
        # 获取激活的配置
        config = await self.config_service.get_active_config(user_id)
        if not config:
            return {
                "success": False,
                "error": "未配置图片生成服务，请先在设置中添加配置",
            }

        try:
            # 使用工厂获取对应的供应商
            provider = ImageProviderFactory.get_provider(config.provider_type)
            if not provider:
                return {
                    "success": False,
                    "error": f"不支持的提供商类型: {config.provider_type}",
                }

            # 构建请求对象（包含所有漫画元数据）
            request = ImageGenerationRequest(
                prompt=prompt,
                negative_prompt=negative_prompt,
                style=style,
                ratio=ratio,
                resolution=resolution,
                # 漫画画格元数据 - 对话相关
                dialogue=dialogue,
                dialogue_speaker=dialogue_speaker,
                dialogue_bubble_type=dialogue_bubble_type,
                dialogue_emotion=dialogue_emotion,
                dialogue_position=dialogue_position,
                # 漫画画格元数据 - 旁白相关
                narration=narration,
                narration_position=narration_position,
                # 漫画画格元数据 - 音效相关
                sound_effects=sound_effects,
                sound_effect_details=sound_effect_details,
                # 漫画画格元数据 - 视觉相关
                composition=composition,
                camera_angle=camera_angle,
                is_key_panel=is_key_panel,
                characters=characters,
                lighting=lighting,
                atmosphere=atmosphere,
                key_visual_elements=key_visual_elements,
                # 语言设置
                dialogue_language=dialogue_language,
            )

            # 检测场景类型
            scene_type = provider._detect_scene_type(prompt)

            # 构建完整提示词（包含漫画视觉元素）
            final_prompt = provider.build_prompt(request, add_context=True)

            # 构建不带上下文的提示词（用于对比）
            prompt_without_context = provider.build_prompt(request, add_context=False)

            # 构建漫画视觉元素描述（单独展示）
            manga_visual_elements = provider._build_manga_visual_elements(request)

            return {
                "success": True,
                "original_prompt": prompt,
                "scene_type": scene_type,
                "scene_type_zh": {
                    "action": "动作/战斗",
                    "romantic": "浪漫/情感",
                    "horror": "恐怖/悬疑",
                    "comedy": "喜剧/轻松",
                    "emotional": "情感/戏剧",
                    "mystery": "悬疑/紧张",
                    "daily": "日常生活",
                }.get(scene_type, scene_type),
                "final_prompt": final_prompt,
                "prompt_without_context": prompt_without_context,
                "manga_visual_elements": manga_visual_elements,  # 漫画视觉元素
                "negative_prompt": negative_prompt,
                "style": style,
                "ratio": ratio,
                "resolution": resolution,
                "provider": config.provider_type,
                "model": config.model_name,
            }

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            logger.error(f"预览提示词失败: {error_msg}", exc_info=True)
            return {
                "success": False,
                "error": error_msg,
            }
