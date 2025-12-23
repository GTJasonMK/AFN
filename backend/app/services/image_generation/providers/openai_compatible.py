"""
OpenAI兼容图片生成供应商

支持：
1. 标准图片生成API模式（DALL-E等）：使用 /v1/images/generations 端点
2. 聊天API模式（nano-banana-pro等）：使用 /v1/chat/completions 端点
"""

import re
import logging
from typing import List, Dict, Any

import httpx

from .base import BaseImageProvider, ProviderTestResult, ProviderGenerateResult, ReferenceImageInfo
from .factory import ImageProviderFactory
from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest, QUALITY_PARAMS, get_size_for_ratio

logger = logging.getLogger(__name__)


def fix_base_url(base_url: str) -> str:
    """
    修复base_url中可能存在的问题

    - 移除尾部斜杠
    - 修复双斜杠问题
    """
    if not base_url:
        return base_url

    fixed_url = base_url.rstrip('/')

    # 检查是否存在双斜杠（排除协议部分的://）
    url_without_protocol = fixed_url.replace('https://', '').replace('http://', '')
    if '//' in url_without_protocol:
        # 修复双斜杠
        fixed_url = fixed_url.replace('//v1', '/v1').replace('//chat', '/chat').replace('//images', '/images')
        logger.warning("base_url包含双斜杠，已自动修复: %s -> %s", base_url, fixed_url)

    return fixed_url


def build_chat_endpoint(base_url: str) -> str:
    """
    构建聊天API端点

    智能处理各种base_url格式：
    - http://api.example.com -> http://api.example.com/v1/chat/completions
    - http://api.example.com/v1 -> http://api.example.com/v1/chat/completions
    - http://api.example.com/v1/chat/completions -> 保持不变
    """
    base = fix_base_url(base_url)

    if base.endswith('/chat/completions'):
        return base
    elif base.endswith('/v1'):
        return f"{base}/chat/completions"
    else:
        return f"{base}/v1/chat/completions"


def build_image_endpoint(base_url: str) -> str:
    """
    构建图片生成API端点

    智能处理各种base_url格式：
    - http://api.example.com -> http://api.example.com/v1/images/generations
    - http://api.example.com/v1 -> http://api.example.com/v1/images/generations
    """
    base = fix_base_url(base_url)

    if base.endswith('/images/generations'):
        return base
    elif base.endswith('/v1'):
        return f"{base}/images/generations"
    else:
        return f"{base}/v1/images/generations"


def get_browser_headers() -> Dict[str, str]:
    """获取模拟浏览器的请求头，帮助绕过一些API限制"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }


@ImageProviderFactory.register("openai_compatible")
class OpenAICompatibleProvider(BaseImageProvider):
    """OpenAI兼容接口供应商"""

    PROVIDER_TYPE = "openai_compatible"
    DISPLAY_NAME = "OpenAI兼容接口"

    def get_supported_features(self) -> Dict[str, bool]:
        """获取供应商支持的特性"""
        return {
            "negative_prompt": True,
            "style": True,
            "quality": True,
            "resolution": True,
            "ratio": True,
            "img2img": True,  # 支持 img2img（通过聊天API的图片输入）
        }

    async def test_connection(self, config: ImageGenerationConfig) -> ProviderTestResult:
        """测试OpenAI兼容接口连接"""
        if not config.api_base_url or not config.api_key:
            return ProviderTestResult(
                success=False,
                message="API URL或API Key未配置"
            )

        try:
            # 构建模型列表端点
            base = fix_base_url(config.api_base_url)
            if base.endswith('/v1'):
                models_url = f"{base}/models"
            else:
                models_url = f"{base}/v1/models"

            async with self.create_http_client(config, for_test=True) as client:
                # 合并认证头和浏览器头
                headers = {**self.get_auth_headers(config, content_type="", accept=""), **get_browser_headers()}

                response = await client.get(models_url, headers=headers)

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

        logger.info(
            "开始生成图片: model=%s, use_image_api=%s, api_base_url=%s",
            config.model_name, use_image_api, config.api_base_url
        )

        try:
            if use_image_api:
                urls = await self._generate_with_image_api(config, request)
            else:
                urls = await self._generate_with_chat_api(config, request)

            logger.info("图片生成完成: 获取到 %d 个URL", len(urls))
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
        response_format = extra_params.get("response_format", "url")

        # 确定图片尺寸：优先使用请求中的ratio，其次使用配置中的size
        if request.ratio:
            # 从宽高比计算实际尺寸
            width, height = get_size_for_ratio(request.ratio, request.resolution or "1K")
            size = f"{width}x{height}"
            logger.info(f"使用宽高比 {request.ratio} 计算尺寸: {size}")
        else:
            size = extra_params.get("size", "1024x1024")

        # 构建API端点
        api_url = build_image_endpoint(config.api_base_url)
        logger.info("图片生成API请求URL: %s", api_url)

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

            # 合并认证头和浏览器头
            headers = {**self.get_auth_headers(config), **get_browser_headers()}

            response = await client.post(api_url, headers=headers, json=request_body)

            logger.info("图片生成API响应状态码: %d", response.status_code)

            if response.status_code != 200:
                error_msg = f"图片生成API错误({response.status_code})"
                try:
                    error_data = response.json()
                    logger.error("图片生成API错误响应: %s", error_data)
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except Exception:
                    logger.error("图片生成API错误响应(非JSON): %s", response.text[:500])
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

        # 构建完整的API URL（智能处理各种base_url格式）
        api_url = build_chat_endpoint(config.api_base_url)
        logger.info("聊天API请求URL: %s", api_url)
        logger.info("聊天API请求模型: %s", config.model_name)

        async with self.create_http_client(config) as client:
            request_body = {
                "model": config.model_name or "nano-banana-pro",
                "messages": [{"role": "user", "content": full_prompt}],
                "max_tokens": quality_params["max_tokens"],
                "temperature": quality_params["temperature"],
                "n": request.count,
            }
            logger.debug("聊天API请求体: %s", {**request_body, "messages": "[省略]"})

            # 合并认证头和浏览器头
            headers = {**self.get_auth_headers(config), **get_browser_headers()}

            response = await client.post(api_url, headers=headers, json=request_body)

            logger.info("聊天API响应状态码: %d", response.status_code)

            if response.status_code != 200:
                error_msg = f"API错误({response.status_code})"
                try:
                    error_data = response.json()
                    logger.error("聊天API错误响应: %s", error_data)
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except Exception:
                    logger.error("聊天API错误响应(非JSON): %s", response.text[:500])
                raise Exception(error_msg)

            result = response.json()
            logger.debug("聊天API原始响应: %s", result)

            content = result["choices"][0]["message"]["content"]
            logger.info("聊天API返回内容(前500字符): %s", content[:500] if content else "(空)")

            # 从Markdown格式中提取图片URL
            urls = []

            # 提取完整URL: ![xxx](https://xxx.xxx/xxx.png)
            full_urls = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', content)
            urls.extend(full_urls)
            logger.debug("提取到的完整URL: %s", full_urls)

            # 提取本地路径: ![xxx](/images/xxx/xxx.png)
            local_paths = re.findall(r'!\[.*?\]\((/images/[^\s\)]+)\)', content)
            for path in local_paths:
                urls.append(f"{config.api_base_url.rstrip('/')}{path}")
            logger.debug("提取到的本地路径: %s", local_paths)

            # 如果没有找到Markdown格式的URL，尝试提取纯URL
            if not urls:
                # 尝试提取任何http(s)图片URL
                plain_urls = re.findall(r'(https?://[^\s\"\'\)]+\.(?:png|jpg|jpeg|gif|webp))', content, re.IGNORECASE)
                urls.extend(plain_urls)
                logger.debug("提取到的纯URL: %s", plain_urls)

            logger.info("最终提取到的图片URL数量: %d", len(urls))
            return urls

    async def generate_with_reference(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
        reference_images: List[ReferenceImageInfo],
    ) -> ProviderGenerateResult:
        """
        使用参考图生成图片（img2img）

        通过聊天API的图片输入功能实现。
        将参考图作为 image_url 类型的消息内容发送给API。

        Args:
            config: 供应商配置
            request: 生成请求
            reference_images: 参考图列表

        Returns:
            ProviderGenerateResult: 生成结果
        """
        if not reference_images:
            # 没有参考图，降级为普通生成
            return await self.generate(config, request)

        logger.info(
            "开始img2img生成: model=%s, 参考图数量=%d",
            config.model_name, len(reference_images)
        )

        try:
            urls = await self._generate_with_chat_api_and_images(
                config, request, reference_images
            )
            logger.info("img2img生成完成: 获取到 %d 个URL", len(urls))
            return ProviderGenerateResult(success=True, image_urls=urls)

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            logger.error("OpenAI兼容接口img2img生成失败: %s", error_msg)
            return ProviderGenerateResult(success=False, error_message=error_msg)

    async def _generate_with_chat_api_and_images(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
        reference_images: List[ReferenceImageInfo],
    ) -> List[str]:
        """
        使用聊天API模式生成图片，包含参考图（img2img）

        支持recons等OpenAI兼容API的图片输入格式。
        """
        # 构建完整提示词
        full_prompt = self.build_prompt(request)

        # 添加参考图说明
        ref_count = len(reference_images)
        if ref_count == 1:
            ref_instruction = (
                "\n\n[REFERENCE IMAGE INSTRUCTION]\n"
                "Use the provided reference image as a style and character guide. "
                "Maintain the character's appearance, clothing, and visual style from the reference. "
                "Generate a new image following the scene description while keeping character consistency.\n"
                "[END INSTRUCTION]\n"
            )
        else:
            ref_instruction = (
                f"\n\n[REFERENCE IMAGE INSTRUCTION]\n"
                f"Use the provided {ref_count} reference images as character guides. "
                "Maintain each character's appearance from their respective reference. "
                "Generate a new image following the scene description while keeping character consistency.\n"
                "[END INSTRUCTION]\n"
            )
        full_prompt = ref_instruction + full_prompt

        # 获取质量参数
        quality_params = QUALITY_PARAMS.get(
            request.quality or "standard",
            QUALITY_PARAMS["standard"]
        )

        # 构建消息内容（数组格式，包含文本和图片）
        message_content = []

        # 添加参考图（使用OpenAI的image_url格式）
        for i, ref_image in enumerate(reference_images):
            if ref_image.base64_data:
                # 使用data URL格式
                # 尝试从文件路径推断MIME类型
                mime_type = "image/png"
                if ref_image.file_path:
                    file_ext = ref_image.file_path.lower().split('.')[-1]
                    mime_map = {
                        'jpg': 'image/jpeg',
                        'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'webp': 'image/webp',
                    }
                    mime_type = mime_map.get(file_ext, 'image/png')

                data_url = f"data:{mime_type};base64,{ref_image.base64_data}"
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": data_url}
                })
                logger.debug("添加参考图 %d: %s (base64, %s)", i + 1, ref_image.file_path, mime_type)

        # 添加文本提示词
        message_content.append({
            "type": "text",
            "text": full_prompt
        })

        # 构建完整的API URL
        api_url = build_chat_endpoint(config.api_base_url)
        logger.info("img2img聊天API请求URL: %s", api_url)
        logger.info("img2img聊天API请求模型: %s, 参考图: %d张", config.model_name, len(reference_images))

        async with self.create_http_client(config) as client:
            request_body = {
                "model": config.model_name or "nano-banana-pro",
                "messages": [{"role": "user", "content": message_content}],
                "max_tokens": quality_params["max_tokens"],
                "temperature": quality_params["temperature"],
                "n": request.count,
            }
            logger.debug("img2img请求体: model=%s, content_items=%d",
                        request_body["model"], len(message_content))

            # 合并认证头和浏览器头
            headers = {**self.get_auth_headers(config), **get_browser_headers()}

            response = await client.post(api_url, headers=headers, json=request_body)

            logger.info("img2img API响应状态码: %d", response.status_code)

            if response.status_code != 200:
                error_msg = f"API错误({response.status_code})"
                try:
                    error_data = response.json()
                    logger.error("img2img API错误响应: %s", error_data)
                    if "error" in error_data:
                        error_msg = error_data["error"].get("message", error_msg)
                except Exception:
                    logger.error("img2img API错误响应(非JSON): %s", response.text[:500])
                raise Exception(error_msg)

            result = response.json()
            logger.debug("img2img API原始响应: %s", str(result)[:500])

            content = result["choices"][0]["message"]["content"]
            logger.info("img2img API返回内容(前500字符): %s", content[:500] if content else "(空)")

            # 从Markdown格式中提取图片URL（与普通生成相同）
            urls = []

            # 提取完整URL: ![xxx](https://xxx.xxx/xxx.png)
            full_urls = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', content)
            urls.extend(full_urls)

            # 提取本地路径: ![xxx](/images/xxx/xxx.png)
            local_paths = re.findall(r'!\[.*?\]\((/images/[^\s\)]+)\)', content)
            for path in local_paths:
                urls.append(f"{config.api_base_url.rstrip('/')}{path}")

            # 如果没有找到Markdown格式的URL，尝试提取纯URL
            if not urls:
                plain_urls = re.findall(r'(https?://[^\s\"\'\)]+\.(?:png|jpg|jpeg|gif|webp))', content, re.IGNORECASE)
                urls.extend(plain_urls)

            logger.info("img2img最终提取到的图片URL数量: %d", len(urls))
            return urls
