"""
LLM请求队列

管理所有LLM API调用的并发控制。
"""

import logging
from typing import Optional

from .base import RequestQueue

logger = logging.getLogger(__name__)


class LLMRequestQueue(RequestQueue):
    """
    LLM请求队列（单例模式）

    所有LLM调用（灵感对话、蓝图生成、章节生成等）都通过此队列进行并发控制。
    """

    _instance: Optional["LLMRequestQueue"] = None

    def __init__(self, max_concurrent: int = 3):
        super().__init__(name="llm", max_concurrent=max_concurrent)

    @classmethod
    def get_instance(cls) -> "LLMRequestQueue":
        """
        获取队列单例

        首次调用时会根据settings配置初始化队列。
        """
        if cls._instance is None:
            # 延迟导入避免循环引用
            from ...core.config import settings
            max_concurrent = getattr(settings, 'llm_max_concurrent', 3)
            cls._instance = cls(max_concurrent=max_concurrent)
            logger.info("LLM请求队列已创建: max_concurrent=%d", max_concurrent)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例（仅用于测试）
        """
        cls._instance = None
