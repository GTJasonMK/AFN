"""
图片生成供应商模块

使用工厂模式管理不同的图片生成服务供应商。
"""

from .factory import ImageProviderFactory

__all__ = [
    "ImageProviderFactory",
]
