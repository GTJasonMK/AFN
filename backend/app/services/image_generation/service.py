"""
图片生成服务

主服务入口，协调配置管理和图片生成。
支持多厂商的图片生成API调用。
"""

import re
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    ImageGenerationRequest,
    ImageGenerationResult,
    GeneratedImageInfo,
    ImageConfigCreate,
    ImageConfigUpdate,
    ProviderType,
    STYLE_SUFFIXES,
    QUALITY_PARAMS,
    RESOLUTION_SUFFIXES,
)
from ...models.image_config import ImageGenerationConfig, GeneratedImage
from ...core.config import settings

logger = logging.getLogger(__name__)

# 图片存储根目录
IMAGES_ROOT = Path(settings.STORAGE_DIR) / "generated_images"


class ImageGenerationService:
    """图片生成服务

    提供配置管理和图片生成功能。
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== 配置管理 ====================

    async def get_configs(self, user_id: int) -> List[ImageGenerationConfig]:
        """获取用户的所有图片生成配置"""
        result = await self.session.execute(
            select(ImageGenerationConfig)
            .where(ImageGenerationConfig.user_id == user_id)
            .order_by(ImageGenerationConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_config(self, config_id: int, user_id: int) -> Optional[ImageGenerationConfig]:
        """获取单个配置"""
        result = await self.session.execute(
            select(ImageGenerationConfig).where(
                ImageGenerationConfig.id == config_id,
                ImageGenerationConfig.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_config(self, user_id: int) -> Optional[ImageGenerationConfig]:
        """获取用户激活的配置"""
        result = await self.session.execute(
            select(ImageGenerationConfig).where(
                ImageGenerationConfig.user_id == user_id,
                ImageGenerationConfig.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def create_config(
        self, user_id: int, data: ImageConfigCreate
    ) -> ImageGenerationConfig:
        """创建新配置"""
        config = ImageGenerationConfig(
            user_id=user_id,
            config_name=data.config_name,
            provider_type=data.provider_type.value,
            api_base_url=data.api_base_url,
            api_key=data.api_key,
            model_name=data.model_name,
            default_style=data.default_style,
            default_ratio=data.default_ratio,
            default_resolution=data.default_resolution,
            default_quality=data.default_quality,
            extra_params=data.extra_params or {},
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update_config(
        self, config_id: int, user_id: int, data: ImageConfigUpdate
    ) -> Optional[ImageGenerationConfig]:
        """更新配置"""
        config = await self.get_config(config_id, user_id)
        if not config:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "provider_type" and value is not None:
                setattr(config, key, value.value)
            else:
                setattr(config, key, value)

        await self.session.flush()
        return config

    async def delete_config(self, config_id: int, user_id: int) -> bool:
        """删除配置"""
        config = await self.get_config(config_id, user_id)
        if not config:
            return False

        if config.is_active:
            raise ValueError("无法删除激活的配置")

        await self.session.delete(config)
        await self.session.flush()
        return True

    async def activate_config(self, config_id: int, user_id: int) -> bool:
        """激活配置"""
        # 先取消所有其他配置的激活状态
        result = await self.session.execute(
            select(ImageGenerationConfig).where(
                ImageGenerationConfig.user_id == user_id,
                ImageGenerationConfig.is_active == True,
            )
        )
        for old_config in result.scalars().all():
            old_config.is_active = False

        # 激活指定配置
        config = await self.get_config(config_id, user_id)
        if not config:
            return False

        config.is_active = True
        await self.session.flush()
        return True

    async def test_config(self, config_id: int, user_id: int) -> Dict[str, Any]:
        """测试配置连接"""
        config = await self.get_config(config_id, user_id)
        if not config:
            return {"success": False, "message": "配置不存在"}

        try:
            # 根据提供商类型测试连接
            if config.provider_type == ProviderType.OPENAI_COMPATIBLE.value:
                result = await self._test_openai_compatible(config)
            elif config.provider_type == ProviderType.STABILITY.value:
                result = await self._test_stability(config)
            else:
                result = {"success": False, "message": f"不支持的提供商类型: {config.provider_type}"}

            # 更新测试状态
            config.last_test_at = datetime.utcnow()
            config.test_status = "success" if result["success"] else "failed"
            config.test_message = result.get("message", "")
            config.is_verified = result["success"]
            await self.session.flush()

            return result

        except Exception as e:
            logger.error(f"测试配置失败: {e}")
            config.last_test_at = datetime.utcnow()
            config.test_status = "failed"
            config.test_message = str(e)
            await self.session.flush()
            return {"success": False, "message": str(e)}

    async def _test_openai_compatible(self, config: ImageGenerationConfig) -> Dict[str, Any]:
        """测试OpenAI兼容接口"""
        if not config.api_base_url or not config.api_key:
            return {"success": False, "message": "API URL或API Key未配置"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 尝试获取模型列表来验证连接
                response = await client.get(
                    f"{config.api_base_url.rstrip('/')}/v1/models",
                    headers={"Authorization": f"Bearer {config.api_key}"},
                )

                if response.status_code == 200:
                    return {"success": True, "message": "连接成功"}
                elif response.status_code == 401:
                    return {"success": False, "message": "API Key无效"}
                else:
                    return {"success": False, "message": f"连接失败: HTTP {response.status_code}"}

        except httpx.TimeoutException:
            return {"success": False, "message": "连接超时"}
        except Exception as e:
            return {"success": False, "message": f"连接错误: {str(e)}"}

    async def _test_stability(self, config: ImageGenerationConfig) -> Dict[str, Any]:
        """测试Stability AI接口"""
        # TODO: 实现Stability AI测试
        return {"success": False, "message": "Stability AI暂未实现"}

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
        生成图片

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

        # 获取激活的配置
        config = await self.get_active_config(user_id)
        if not config:
            return ImageGenerationResult(
                success=False,
                error_message="未配置图片生成服务，请先在设置中添加配置",
            )

        try:
            # 根据提供商类型调用不同的生成方法
            if config.provider_type == ProviderType.OPENAI_COMPATIBLE.value:
                image_urls = await self._generate_openai_compatible(config, request)
            elif config.provider_type == ProviderType.STABILITY.value:
                image_urls = await self._generate_stability(config, request)
            else:
                return ImageGenerationResult(
                    success=False,
                    error_message=f"不支持的提供商类型: {config.provider_type}",
                )

            if not image_urls:
                return ImageGenerationResult(
                    success=False,
                    error_message="未能获取到生成的图片",
                )

            # 下载并保存图片
            saved_images = await self._download_and_save_images(
                image_urls=image_urls,
                project_id=project_id,
                chapter_number=chapter_number,
                scene_id=scene_id,
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                model_name=config.model_name,
                style=request.style,
            )

            generation_time = time.time() - start_time

            return ImageGenerationResult(
                success=True,
                images=saved_images,
                generation_time=generation_time,
            )

        except Exception as e:
            logger.error(f"图片生成失败: {e}")
            return ImageGenerationResult(
                success=False,
                error_message=str(e),
            )

    async def _generate_openai_compatible(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> List[str]:
        """
        使用OpenAI兼容接口生成图片

        Returns:
            图片URL列表
        """
        # 构建完整提示词
        full_prompt = self._build_prompt(request)

        # 获取质量参数
        quality_params = QUALITY_PARAMS.get(request.quality or "standard", QUALITY_PARAMS["standard"])

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{config.api_base_url.rstrip('/')}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model_name or "nano-banana-pro",
                    "messages": [{"role": "user", "content": full_prompt}],
                    "max_tokens": quality_params["max_tokens"],
                    "temperature": quality_params["temperature"],
                    "n": request.count,
                },
            )

            if response.status_code != 200:
                error_msg = f"API错误({response.status_code})"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except:
                    pass
                raise Exception(error_msg)

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 从Markdown格式中提取图片URL
            urls = []

            # 提取完整URL: ![xxx](https://xxx.xxx/xxx.png)
            full_urls = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', content)
            urls.extend(full_urls)

            # 提取本地路径: ![xxx](/images/xxx/xxx.png)
            local_paths = re.findall(r'!\[.*?\]\((/images/[^\s\)]+)\)', content)
            for path in local_paths:
                urls.append(f"{config.api_base_url.rstrip('/')}{path}")

            return urls

    async def _generate_stability(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> List[str]:
        """使用Stability AI生成图片"""
        # TODO: 实现Stability AI生成
        raise NotImplementedError("Stability AI暂未实现")

    def _build_prompt(self, request: ImageGenerationRequest) -> str:
        """构建完整提示词"""
        prompt = request.prompt

        # 添加风格后缀
        if request.style:
            style_suffix = STYLE_SUFFIXES.get(request.style, "")
            if style_suffix:
                prompt = f"{prompt}, {style_suffix}"

        # 添加分辨率后缀
        if request.resolution:
            res_suffix = RESOLUTION_SUFFIXES.get(request.resolution, "")
            if res_suffix:
                prompt = f"{prompt}{res_suffix}"

        # 添加宽高比
        if request.ratio:
            prompt = f"{prompt}, aspect ratio {request.ratio}"

        # 添加负面提示词
        if request.negative_prompt:
            prompt = f"{prompt}\n\nNegative: {request.negative_prompt}"

        return prompt

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
    ) -> List[GeneratedImageInfo]:
        """下载并保存图片"""
        saved_images = []

        # 确保目录存在
        save_dir = IMAGES_ROOT / project_id / f"chapter_{chapter_number}" / f"scene_{scene_id}"
        save_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, url in enumerate(image_urls):
                try:
                    response = await client.get(url)
                    if response.status_code != 200:
                        logger.warning(f"下载图片失败: {url}, status={response.status_code}")
                        continue

                    # 生成文件名
                    content_hash = hashlib.md5(response.content).hexdigest()[:8]
                    timestamp = int(time.time())
                    file_name = f"img_{timestamp}_{content_hash}_{i}.png"
                    file_path = save_dir / file_name

                    # 保存文件
                    file_path.write_bytes(response.content)

                    # 创建数据库记录
                    image_record = GeneratedImage(
                        project_id=project_id,
                        chapter_number=chapter_number,
                        scene_id=scene_id,
                        file_name=file_name,
                        file_path=str(file_path.relative_to(IMAGES_ROOT)),
                        file_size=len(response.content),
                        mime_type="image/png",
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        model_name=model_name,
                        style=style,
                        source_url=url,
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
                            prompt=prompt,
                            created_at=image_record.created_at,
                        )
                    )

                except Exception as e:
                    logger.error(f"保存图片失败: {e}")
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
    ) -> List[GeneratedImage]:
        """获取章节的所有图片"""
        result = await self.session.execute(
            select(GeneratedImage)
            .where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
            )
            .order_by(GeneratedImage.scene_id, GeneratedImage.created_at.desc())
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
