"""
Stability AI图片生成供应商

支持Stability AI的图片生成API，包括 text-to-image 和 image-to-image。
"""

import logging
from typing import List

import httpx

from .base import BaseImageProvider, ProviderTestResult, ProviderGenerateResult, ReferenceImageInfo
from .factory import ImageProviderFactory
from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest, get_size_for_ratio

logger = logging.getLogger(__name__)


@ImageProviderFactory.register("stability")
class StabilityProvider(BaseImageProvider):
    """Stability AI供应商"""

    PROVIDER_TYPE = "stability"
    DISPLAY_NAME = "Stability AI"

    # Stability AI API端点
    API_HOST = "https://api.stability.ai"

    async def test_connection(self, config: ImageGenerationConfig) -> ProviderTestResult:
        """测试Stability AI连接"""
        if not config.api_key:
            return ProviderTestResult(
                success=False,
                message="API Key未配置"
            )

        async def _run() -> ProviderTestResult:
            async with self.create_http_client(config, for_test=True) as client:
                # 获取账户余额来验证API Key
                api_host = config.api_base_url or self.API_HOST
                response = await client.get(
                    f"{api_host.rstrip('/')}/v1/user/balance",
                    headers=self.get_auth_headers(config, content_type=""),
                )

                def _on_success(resp: httpx.Response) -> ProviderTestResult:
                    data = resp.json()
                    credits = data.get("credits", 0)
                    return ProviderTestResult(
                        success=True,
                        message=f"连接成功，剩余额度: {credits}",
                        extra_info={"credits": credits},
                    )

                return self._build_test_connection_result_for_response(response, on_success=_on_success)

        return await self._wrap_test_connection(_run)

    async def generate(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> ProviderGenerateResult:
        """
        使用Stability AI生成图片

        支持的模型：
        - stable-diffusion-xl-1024-v1-0
        - stable-diffusion-v1-6
        - stable-image-core
        - stable-image-ultra
        """
        try:
            urls = await self._generate_image(config, request)
            return ProviderGenerateResult(success=True, image_urls=urls)
        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            logger.error("Stability AI生成失败: %s", error_msg)
            return ProviderGenerateResult(success=False, error_message=error_msg)

    async def _generate_image(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> List[str]:
        """调用Stability AI生成图片"""
        api_host = config.api_base_url or self.API_HOST
        model = config.model_name or "stable-diffusion-xl-1024-v1-0"

        # 构建提示词（Stability AI有内容审核，启用上下文说明）
        prompt = self.build_prompt(request, add_context=True)

        # 获取额外参数
        extra_params = config.extra_params or {}

        # 确定图片尺寸：优先使用请求中的ratio，其次使用配置中的width/height
        if request.ratio:
            width, height = get_size_for_ratio(request.ratio, request.resolution or "1K")
            logger.info(f"Stability AI: 使用宽高比 {request.ratio} 计算尺寸: {width}x{height}")
        else:
            width = extra_params.get("width", 1024)
            height = extra_params.get("height", 1024)

        # 构建请求体
        request_body = {
            "text_prompts": [
                {"text": prompt, "weight": 1.0}
            ],
            "cfg_scale": extra_params.get("cfg_scale", 7),
            "samples": request.count,
            "steps": extra_params.get("steps", 30),
            "width": width,
            "height": height,
        }

        # 添加负面提示词
        if request.negative_prompt:
            request_body["text_prompts"].append({
                "text": request.negative_prompt,
                "weight": -1.0
            })

        # 添加风格预设
        if extra_params.get("style_preset"):
            request_body["style_preset"] = extra_params["style_preset"]

        async with self.create_http_client(config) as client:
            result = await self._request_json(
                client,
                "POST",
                f"{api_host.rstrip('/')}/v1/generation/{model}/text-to-image",
                headers=self.get_auth_headers(config),
                json_body=request_body,
                error_message="Stability API错误",
                error_paths=[["message"]],
                error_fallback=False,
            )
            urls = []

            # 从响应中提取Base64图片数据
            for artifact in result.get("artifacts", []):
                if artifact.get("finishReason") == "SUCCESS":
                    b64_data = artifact.get("base64")
                    if b64_data:
                        urls.append(f"data:image/png;base64,{b64_data}")

            return urls

    def get_supported_features(self) -> dict:
        """获取Stability AI支持的特性"""
        return {
            "negative_prompt": True,
            "style": True,
            "quality": False,  # 通过steps控制
            "resolution": True,
            "ratio": True,  # 支持宽高比转换
            "cfg_scale": True,
            "steps": True,
            "style_preset": True,
            "img2img": True,  # 支持 img2img
        }

    async def _generate_with_reference_urls(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
        reference_images: List[ReferenceImageInfo],
    ) -> List[str]:
        """img2img：使用 Stability AI 的 image-to-image 端点（默认取第一张参考图）"""
        ref_image = reference_images[0]
        return await self._generate_image_to_image(config, request, ref_image)

    async def _generate_image_to_image(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
        ref_image: ReferenceImageInfo,
    ) -> List[str]:
        """调用Stability AI image-to-image 端点生成图片"""
        api_host = config.api_base_url or self.API_HOST
        model = config.model_name or "stable-diffusion-xl-1024-v1-0"

        # 构建提示词（Stability AI有内容审核，启用上下文说明）
        prompt = self.build_prompt(request, add_context=True)

        # 获取额外参数
        extra_params = config.extra_params or {}

        # 准备参考图数据
        init_image_data = self._load_reference_image_bytes(ref_image)

        # 计算 image_strength (与 denoise 相反)
        # strength 0.7 表示参考图影响 70%，对应 image_strength 0.7
        image_strength = ref_image.strength

        async with self.create_http_client(config) as client:
            # 使用 multipart/form-data 格式
            files = {
                "init_image": ("init_image.png", init_image_data, "image/png"),
            }
            data = {
                "text_prompts[0][text]": prompt,
                "text_prompts[0][weight]": "1.0",
                "cfg_scale": str(extra_params.get("cfg_scale", 7)),
                "samples": str(request.count),
                "steps": str(extra_params.get("steps", 30)),
                "image_strength": str(image_strength),
            }

            # 添加负面提示词
            if request.negative_prompt:
                data["text_prompts[1][text]"] = request.negative_prompt
                data["text_prompts[1][weight]"] = "-1.0"

            # 添加风格预设
            if extra_params.get("style_preset"):
                data["style_preset"] = extra_params["style_preset"]

            headers = {
                "Authorization": f"Bearer {config.api_key}",
                "Accept": "application/json",
            }

            result = await self._request_json(
                client,
                "POST",
                f"{api_host.rstrip('/')}/v1/generation/{model}/image-to-image",
                headers=headers,
                files=files,
                data=data,
                error_message="Stability API错误",
                error_paths=[["message"]],
                error_fallback=False,
            )
            urls = []

            # 从响应中提取Base64图片数据
            for artifact in result.get("artifacts", []):
                if artifact.get("finishReason") == "SUCCESS":
                    b64_data = artifact.get("base64")
                    if b64_data:
                        urls.append(f"data:image/png;base64,{b64_data}")

            return urls
