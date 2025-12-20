"""
图片生成请求队列

管理所有图片生成API调用的并发控制。
"""

import logging
from typing import Optional

from .base import RequestQueue

logger = logging.getLogger(__name__)


class ImageRequestQueue(RequestQueue):
    """
    图片生成请求队列（单例模式）

    所有图片生成调用（OpenAI兼容、Stability、ComfyUI等）都通过此队列进行并发控制。
    """

    _instance: Optional["ImageRequestQueue"] = None

    def __init__(self, max_concurrent: int = 2):
        super().__init__(name="image", max_concurrent=max_concurrent)

    @classmethod
    def get_instance(cls) -> "ImageRequestQueue":
        """
        获取队列单例

        首次调用时会根据settings配置初始化队列。
        """
        if cls._instance is None:
            # 延迟导入避免循环引用
            from ...core.config import settings
            max_concurrent = getattr(settings, 'image_max_concurrent', 2)
            cls._instance = cls(max_concurrent=max_concurrent)
            logger.info("图片请求队列已创建: max_concurrent=%d", max_concurrent)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例（仅用于测试）
        """
        cls._instance = None
