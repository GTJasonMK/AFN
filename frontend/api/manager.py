"""
API 客户端管理器 - 单例模式

提供统一的 API 客户端访问，避免多个组件各自创建客户端实例导致的资源浪费。

用法:
    from api.manager import APIClientManager

    # 获取客户端实例（自动创建或复用）
    client = APIClientManager.get_client()
    data = client.get_novels()

    # 应用退出时关闭（通常在 MainWindow.closeEvent 中调用）
    APIClientManager.shutdown()
"""

import logging
import threading
from typing import Optional

from api.client import AFNAPIClient

logger = logging.getLogger(__name__)


class APIClientManager:
    """API 客户端单例管理器

    特性：
    - 线程安全的单例实现
    - 自动检测客户端是否已关闭并重新创建
    - 统一的资源清理接口
    """

    _instance: Optional[AFNAPIClient] = None
    _lock = threading.Lock()

    @classmethod
    def get_client(cls) -> AFNAPIClient:
        """获取 API 客户端实例

        如果实例不存在或已关闭，会自动创建新实例。
        此方法是线程安全的。

        Returns:
            AFNAPIClient 实例
        """
        # 双重检查锁定模式
        if cls._instance is None or cls._instance._closed:
            with cls._lock:
                # 再次检查，避免竞态条件
                if cls._instance is None or cls._instance._closed:
                    logger.debug("创建新的 API 客户端实例")
                    cls._instance = AFNAPIClient()
        return cls._instance

    @classmethod
    def shutdown(cls) -> None:
        """关闭 API 客户端，释放资源

        应在应用退出时调用。此方法是线程安全的。
        可以安全地多次调用。
        """
        with cls._lock:
            if cls._instance is not None:
                logger.debug("关闭 API 客户端实例")
                try:
                    cls._instance.close()
                except Exception as e:
                    logger.warning("关闭 API 客户端时发生异常: %s", e)
                finally:
                    cls._instance = None

    @classmethod
    def is_active(cls) -> bool:
        """检查客户端是否处于活跃状态

        Returns:
            True 如果客户端存在且未关闭
        """
        return cls._instance is not None and not cls._instance._closed
