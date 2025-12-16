"""
图片生成供应商工厂

使用注册模式管理供应商，支持动态扩展。
"""

import logging
from typing import Dict, Type, Optional

from .base import BaseImageProvider

logger = logging.getLogger(__name__)


class ImageProviderFactory:
    """
    图片生成供应商工厂

    使用装饰器注册供应商，通过provider_type获取实例。

    使用示例:
        @ImageProviderFactory.register("openai_compatible")
        class OpenAICompatibleProvider(BaseImageProvider):
            ...

        # 获取供应商
        provider = ImageProviderFactory.get_provider("openai_compatible")
    """

    _providers: Dict[str, Type[BaseImageProvider]] = {}

    @classmethod
    def register(cls, provider_type: str):
        """
        注册供应商装饰器

        Args:
            provider_type: 供应商类型标识符

        Returns:
            装饰器函数
        """
        def decorator(provider_cls: Type[BaseImageProvider]):
            if not issubclass(provider_cls, BaseImageProvider):
                raise TypeError(
                    f"{provider_cls.__name__} 必须继承自 BaseImageProvider"
                )
            cls._providers[provider_type] = provider_cls
            provider_cls.PROVIDER_TYPE = provider_type
            logger.debug("注册图片生成供应商: %s -> %s", provider_type, provider_cls.__name__)
            return provider_cls
        return decorator

    @classmethod
    def get_provider(cls, provider_type: str) -> Optional[BaseImageProvider]:
        """
        获取供应商实例

        Args:
            provider_type: 供应商类型标识符

        Returns:
            供应商实例，如果不存在返回None
        """
        provider_cls = cls._providers.get(provider_type)
        if provider_cls is None:
            logger.warning("未找到供应商类型: %s", provider_type)
            return None
        return provider_cls()

    @classmethod
    def get_supported_types(cls) -> Dict[str, str]:
        """
        获取所有支持的供应商类型

        Returns:
            类型到显示名称的映射
        """
        return {
            provider_type: provider_cls.DISPLAY_NAME or provider_type
            for provider_type, provider_cls in cls._providers.items()
        }

    @classmethod
    def is_supported(cls, provider_type: str) -> bool:
        """
        检查供应商类型是否支持

        Args:
            provider_type: 供应商类型标识符

        Returns:
            是否支持
        """
        return provider_type in cls._providers
