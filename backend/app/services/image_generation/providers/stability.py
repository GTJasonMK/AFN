"""
Stability AI图片生成供应商

支持Stability AI的图片生成API。
"""

import logging
from typing import List

import httpx

from .base import BaseImageProvider, ProviderTestResult, ProviderGenerateResult
from .factory import ImageProviderFactory
from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest

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

        try:
            async with self.create_http_client(config, for_test=True) as client:
                # 获取账户余额来验证API Key
                api_host = config.api_base_url or self.API_HOST
                response = await client.get(
                    f"{api_host.rstrip('/')}/v1/user/balance",
                    headers=self.get_auth_headers(config, content_type=""),
                )

                if response.status_code == 200:
                    data = response.json()
                    credits = data.get("credits", 0)
                    return ProviderTestResult(
                        success=True,
                        message=f"连接成功，剩余额度: {credits}",
                        extra_info={"credits": credits}
                    )
                elif response.status_code == 401:
                    return ProviderTestResult(success=False, message="API Key无效")
                else:
                    return ProviderTestResult(
                        success=False,
                        message=f"连接失败: HTTP {response.status_code}"
                    )

        except httpx.TimeoutException:
            return ProviderTestResult(success=False, message="连接超时")
        except Exception as e:
            return ProviderTestResult(success=False, message=f"连接错误: {str(e)}")

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

        # 确定图片尺寸
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
            response = await client.post(
                f"{api_host.rstrip('/')}/v1/generation/{model}/text-to-image",
                headers=self.get_auth_headers(config),
                json=request_body,
            )

            if response.status_code != 200:
                error_msg = f"Stability API错误({response.status_code})"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = error_data["message"]
                except Exception:
                    pass
                raise Exception(error_msg)

            result = response.json()
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
            "ratio": False,  # 通过width/height控制
            "cfg_scale": True,
            "steps": True,
            "style_preset": True,
        }
