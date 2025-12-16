"""
图片生成供应商模块

使用工厂模式管理不同的图片生成服务供应商。
"""

from .base import BaseImageProvider, ProviderTestResult, ProviderGenerateResult
from .factory import ImageProviderFactory
from .openai_compatible import OpenAICompatibleProvider
from .stability import StabilityProvider
from .comfyui import ComfyUIProvider

__all__ = [
    "BaseImageProvider",
    "ProviderTestResult",
    "ProviderGenerateResult",
    "ImageProviderFactory",
    "OpenAICompatibleProvider",
    "StabilityProvider",
    "ComfyUIProvider",
]
