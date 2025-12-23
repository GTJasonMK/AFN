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
from pathlib import Path
from typing import Optional, List, TYPE_CHECKING

import httpx
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    ImageGenerationRequest,
    ImageGenerationResult,
    GeneratedImageInfo,
)
from .providers import ImageProviderFactory
from .providers.base import ReferenceImageInfo
from ...models.image_config import GeneratedImage
from ...core.config import settings
from ...services.queue import ImageRequestQueue

if TYPE_CHECKING:
    from .config_service import ImageConfigService

logger = logging.getLogger(__name__)

# 使用统一的路径配置
IMAGES_ROOT = settings.generated_images_dir


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
                    # 准备参考图信息
                    reference_images = await self._prepare_reference_images(
                        request.reference_image_paths,
                        request.reference_strength,
                    )

                    if reference_images and provider.supports_img2img():
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

            # 下载并保存图片
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

    async def _prepare_reference_images(
        self,
        image_paths: List[str],
        strength: float = 0.7,
    ) -> List[ReferenceImageInfo]:
        """
        准备参考图信息

        读取图片文件并转换为 Base64 格式。

        Args:
            image_paths: 图片路径列表
            strength: 参考强度

        Returns:
            参考图信息列表
        """
        reference_images = []

        for path in image_paths:
            try:
                # 处理相对路径和绝对路径
                if path.startswith("/"):
                    # 相对于 IMAGES_ROOT
                    full_path = IMAGES_ROOT / path.lstrip("/")
                else:
                    full_path = Path(path)

                if not full_path.exists():
                    # 尝试 IMAGES_ROOT 下查找
                    full_path = IMAGES_ROOT / path
                    if not full_path.exists():
                        logger.warning("参考图片不存在: %s", path)
                        continue

                # 读取并转换为 Base64
                image_content = full_path.read_bytes()
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
    ) -> List[GeneratedImageInfo]:
        """下载并保存图片

        支持两种URL格式：
        1. 标准HTTP(S) URL：从远程服务器下载图片
        2. Base64数据URL（data:image/png;base64,...）：直接解码保存

        Args:
            chapter_version_id: 章节版本ID，用于版本追溯
            panel_id: 画格ID，用于精确匹配
        """

        saved_images = []

        # 确保目录存在
        save_dir = IMAGES_ROOT / project_id / f"chapter_{chapter_number}" / f"scene_{scene_id}"
        save_dir.mkdir(parents=True, exist_ok=True)

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

                # 生成唯一文件名（使用UUID保证唯一性，避免并发冲突）
                unique_id = uuid.uuid4().hex[:12]  # 12位足够避免冲突
                content_hash = hashlib.sha256(image_content).hexdigest()[:8]
                file_name = f"img_{unique_id}_{content_hash}.png"
                file_path = save_dir / file_name

                # 原子写入：先写入临时文件，再重命名（防止写入中断导致文件损坏）
                temp_path = save_dir / f".tmp_{unique_id}.png"
                try:
                    temp_path.write_bytes(image_content)
                    temp_path.rename(file_path)  # rename在大多数文件系统上是原子操作
                except Exception:
                    # 清理临时文件
                    if temp_path.exists():
                        temp_path.unlink()
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
                    file_path=str(file_path.relative_to(IMAGES_ROOT)),
                    file_size=len(image_content),
                    mime_type="image/png",
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model_name,
                    style=style,
                    source_url=source_url_to_save,
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
        """删除图片"""
        result = await self.session.execute(
            select(GeneratedImage).where(GeneratedImage.id == image_id)
        )
        image = result.scalar_one_or_none()
        if not image:
            return False

        # 删除文件
        file_path = IMAGES_ROOT / image.file_path
        if file_path.exists():
            file_path.unlink()

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
            # 删除文件
            file_path = IMAGES_ROOT / image.file_path
            if file_path.exists():
                try:
                    file_path.unlink()
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
            # 删除文件
            file_path = IMAGES_ROOT / image.file_path
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception as e:
                    logger.warning("删除图片文件失败: %s - %s", file_path, e)

            # 删除数据库记录
            await self.session.delete(image)
            deleted_count += 1

        await self.session.flush()

        # 尝试清理空目录
        try:
            chapter_dir = IMAGES_ROOT / project_id / f"chapter_{chapter_number}"
            if chapter_dir.exists():
                # 删除空的场景子目录
                for scene_dir in chapter_dir.iterdir():
                    if scene_dir.is_dir() and not any(scene_dir.iterdir()):
                        scene_dir.rmdir()
                # 如果章节目录也空了，删除它
                if not any(chapter_dir.iterdir()):
                    chapter_dir.rmdir()
        except Exception as e:
            logger.warning("清理空目录失败: %s", e)

        logger.info(
            "已删除章节图片: project_id=%s, chapter=%d, count=%d",
            project_id, chapter_number, deleted_count
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
