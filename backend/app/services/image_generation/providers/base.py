"""
图片生成供应商基类

定义供应商接口规范，所有具体供应商都需要实现这些方法。
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx

from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest


# HTTP客户端默认配置
DEFAULT_TEST_TIMEOUT = 30.0  # 测试连接超时
DEFAULT_GENERATE_TIMEOUT = 180.0  # 图片生成超时（较长，因为生成需要时间）


@dataclass
class ProviderTestResult:
    """供应商测试结果"""
    success: bool
    message: str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderGenerateResult:
    """供应商生成结果"""
    success: bool
    image_urls: List[str] = field(default_factory=list)
    error_message: str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)


class BaseImageProvider(ABC):
    """
    图片生成供应商抽象基类

    所有具体供应商需要实现以下方法：
    - test_connection: 测试连接是否正常
    - generate: 生成图片

    可选重写：
    - get_supported_features: 获取供应商支持的特性
    """

    # 供应商标识符，子类必须设置
    PROVIDER_TYPE: str = ""

    # 供应商显示名称
    DISPLAY_NAME: str = ""

    # 使用场景上下文前缀 - 向图像生成模型说明这是合法的漫画创作用途
    CONTEXT_PREFIX = (
        "[Context: This is a professional manga/comic illustration for a licensed novel adaptation. "
        "The artwork is for legitimate storytelling purposes in a published creative work. "
        "Please generate appropriate manga-style artwork for the following scene description.]\n\n"
    )

    @asynccontextmanager
    async def create_http_client(
        self,
        config: ImageGenerationConfig,
        timeout: Optional[float] = None,
        for_test: bool = False,
    ) -> AsyncIterator[httpx.AsyncClient]:
        """
        创建配置好的HTTP客户端（工厂方法）

        统一管理超时设置、请求头等配置，避免重复代码。

        Args:
            config: 供应商配置
            timeout: 自定义超时时间（秒），None则使用默认值
            for_test: 是否用于连接测试（使用较短超时）

        Yields:
            配置好的 httpx.AsyncClient 实例

        Usage:
            async with self.create_http_client(config, for_test=True) as client:
                response = await client.get(url, headers=self.get_auth_headers(config))
        """
        if timeout is None:
            timeout = DEFAULT_TEST_TIMEOUT if for_test else DEFAULT_GENERATE_TIMEOUT

        async with httpx.AsyncClient(timeout=timeout) as client:
            yield client

    def get_auth_headers(
        self,
        config: ImageGenerationConfig,
        content_type: str = "application/json",
        accept: str = "application/json",
    ) -> Dict[str, str]:
        """
        获取认证请求头

        Args:
            config: 供应商配置
            content_type: Content-Type 头
            accept: Accept 头

        Returns:
            请求头字典
        """
        headers = {
            "Authorization": f"Bearer {config.api_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if accept:
            headers["Accept"] = accept
        return headers

    @abstractmethod
    async def test_connection(self, config: ImageGenerationConfig) -> ProviderTestResult:
        """
        测试供应商连接

        Args:
            config: 供应商配置

        Returns:
            ProviderTestResult: 测试结果
        """
        pass

    @abstractmethod
    async def generate(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> ProviderGenerateResult:
        """
        生成图片

        Args:
            config: 供应商配置
            request: 生成请求

        Returns:
            ProviderGenerateResult: 生成结果，包含图片URL列表
        """
        pass

    def get_supported_features(self) -> Dict[str, bool]:
        """
        获取供应商支持的特性

        Returns:
            特性支持映射，如 {"negative_prompt": True, "style": True}
        """
        return {
            "negative_prompt": True,
            "style": True,
            "quality": True,
            "resolution": True,
            "ratio": True,
        }

    def build_prompt(self, request: ImageGenerationRequest, add_context: bool = True) -> str:
        """
        构建完整提示词

        Args:
            request: 生成请求
            add_context: 是否添加上下文前缀

        Returns:
            构建后的提示词
        """
        from ..schemas import STYLE_SUFFIXES, RESOLUTION_SUFFIXES

        # 添加使用场景上下文前缀
        prompt = self.CONTEXT_PREFIX + request.prompt if add_context else request.prompt

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
