"""
API 客户端管理器 - 单例模式

提供统一的 API 客户端访问，避免多个组件各自创建客户端实例导致的资源浪费。

用法:
    from api.manager import APIClientManager

    # 配置后端地址（可选，在应用启动时调用）
    APIClientManager.configure(base_url="http://192.168.1.100:8123")

    # 获取客户端实例（自动创建或复用）
    client = APIClientManager.get_client()
    data = client.get_novels()

    # 应用退出时关闭（通常在 MainWindow.closeEvent 中调用）
    APIClientManager.shutdown()
"""

import logging
import os
import threading
from typing import Optional

from api.client import AFNAPIClient

logger = logging.getLogger(__name__)

# 默认后端地址（可通过环境变量 AFN_API_URL 覆盖）
DEFAULT_API_URL = os.environ.get("AFN_API_URL", "http://127.0.0.1:8123")


class APIClientManager:
    """API 客户端单例管理器

    特性：
    - 线程安全的单例实现
    - 自动检测客户端是否已关闭并重新创建
    - 支持配置后端地址（通过 configure() 或环境变量 AFN_API_URL）
    - 统一的资源清理接口
    """

    _instance: Optional[AFNAPIClient] = None
    _lock = threading.Lock()
    _base_url: str = DEFAULT_API_URL

    @classmethod
    def configure(cls, base_url: str = None) -> None:
        """配置 API 客户端

        Args:
            base_url: 后端服务地址，如 "http://192.168.1.100:8123"
        """
        with cls._lock:
            if base_url:
                cls._base_url = base_url.rstrip('/')
                logger.info("API 客户端配置更新: base_url=%s", cls._base_url)
                # 如果已有实例，需要重新创建
                if cls._instance is not None:
                    cls._instance.close()
                    cls._instance = None

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
                    logger.debug("创建新的 API 客户端实例: base_url=%s", cls._base_url)
                    cls._instance = AFNAPIClient(base_url=cls._base_url)
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
