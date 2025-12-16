"""
OpenAI兼容图片生成供应商

支持：
1. 标准图片生成API模式（DALL-E等）：使用 /v1/images/generations 端点
2. 聊天API模式（nano-banana-pro等）：使用 /v1/chat/completions 端点
"""

import re
import logging
from typing import List

import httpx

from .base import BaseImageProvider, ProviderTestResult, ProviderGenerateResult
from .factory import ImageProviderFactory
from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest, QUALITY_PARAMS

logger = logging.getLogger(__name__)


@ImageProviderFactory.register("openai_compatible")
class OpenAICompatibleProvider(BaseImageProvider):
    """OpenAI兼容接口供应商"""

    PROVIDER_TYPE = "openai_compatible"
    DISPLAY_NAME = "OpenAI兼容接口"

    async def test_connection(self, config: ImageGenerationConfig) -> ProviderTestResult:
        """测试OpenAI兼容接口连接"""
        if not config.api_base_url or not config.api_key:
            return ProviderTestResult(
                success=False,
                message="API URL或API Key未配置"
            )

        try:
            async with self.create_http_client(config, for_test=True) as client:
                # 尝试获取模型列表来验证连接
                response = await client.get(
                    f"{config.api_base_url.rstrip('/')}/v1/models",
                    headers=self.get_auth_headers(config, content_type="", accept=""),
                )

                if response.status_code == 200:
                    return ProviderTestResult(success=True, message="连接成功")
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
        使用OpenAI兼容接口生成图片

        根据配置自动选择API模式：
        - use_image_api=True: 使用标准图片生成API
        - use_image_api=False: 使用聊天API模式
        """
        extra_params = config.extra_params or {}
        use_image_api = extra_params.get("use_image_api", False)

        try:
            if use_image_api:
                urls = await self._generate_with_image_api(config, request)
            else:
                urls = await self._generate_with_chat_api(config, request)

            return ProviderGenerateResult(success=True, image_urls=urls)

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            logger.error("OpenAI兼容接口生成失败: %s", error_msg)
            return ProviderGenerateResult(success=False, error_message=error_msg)

    async def _generate_with_image_api(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> List[str]:
        """
        使用标准的 /v1/images/generations 端点生成图片（适用于DALL-E等）
        """
        # 构建提示词（不添加风格后缀，标准API通常不需要）
        prompt = self.CONTEXT_PREFIX + request.prompt

        # 获取配置参数
        extra_params = config.extra_params or {}
        size = extra_params.get("size", "1024x1024")
        response_format = extra_params.get("response_format", "url")

        async with self.create_http_client(config) as client:
            request_body = {
                "model": config.model_name or "dall-e-3",
                "prompt": prompt,
                "n": request.count,
                "size": size,
                "response_format": response_format,
            }

            # 添加可选参数
            if extra_params.get("quality"):
                request_body["quality"] = extra_params["quality"]
            if extra_params.get("style"):
                request_body["style"] = extra_params["style"]

            response = await client.post(
                f"{config.api_base_url.rstrip('/')}/v1/images/generations",
                headers=self.get_auth_headers(config),
                json=request_body,
            )

            if response.status_code != 200:
                error_msg = f"图片生成API错误({response.status_code})"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except Exception:
                    pass
                raise Exception(error_msg)

            result = response.json()
            urls = []

            # 从响应中提取图片URL或Base64数据
            for item in result.get("data", []):
                if "url" in item:
                    urls.append(item["url"])
                elif "b64_json" in item:
                    # 将Base64数据转为data URL
                    urls.append(f"data:image/png;base64,{item['b64_json']}")

            return urls

    async def _generate_with_chat_api(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> List[str]:
        """
        使用聊天API模式生成图片（适用于nano-banana-pro等）
        """
        # 构建完整提示词
        full_prompt = self.build_prompt(request)

        # 获取质量参数
        quality_params = QUALITY_PARAMS.get(
            request.quality or "standard",
            QUALITY_PARAMS["standard"]
        )

        async with self.create_http_client(config) as client:
            response = await client.post(
                f"{config.api_base_url.rstrip('/')}/v1/chat/completions",
                headers=self.get_auth_headers(config),
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
                except Exception:
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
