"""
请求队列基类

提供基于Semaphore的并发控制和状态跟踪功能。
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RequestQueue:
    """
    请求队列基类

    使用asyncio.Semaphore实现并发控制，支持：
    - 最大并发数限制
    - 队列状态跟踪（活跃数、等待数、已处理数）
    - 动态调整并发数
    """

    def __init__(self, name: str, max_concurrent: int = 3):
        """
        初始化队列

        Args:
            name: 队列名称（用于日志标识）
            max_concurrent: 最大并发数
        """
        self.name = name
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()

        # 状态计数器
        self._active_count = 0      # 正在执行的请求数
        self._waiting_count = 0     # 等待中的请求数
        self._total_processed = 0   # 已处理总数

        logger.info(
            "队列 %s 已初始化: max_concurrent=%d",
            self.name, self._max_concurrent
        )

    async def acquire(self) -> None:
        """
        获取执行槽位

        如果当前并发数已达上限，将阻塞等待直到有槽位释放。
        """
        async with self._lock:
            self._waiting_count += 1

        logger.debug(
            "队列 %s: 请求等待槽位 (active=%d, waiting=%d)",
            self.name, self._active_count, self._waiting_count
        )

        await self._semaphore.acquire()

        async with self._lock:
            self._waiting_count -= 1
            self._active_count += 1

        logger.debug(
            "队列 %s: 获取到槽位 (active=%d, waiting=%d)",
            self.name, self._active_count, self._waiting_count
        )

    async def release(self) -> None:
        """释放执行槽位"""
        async with self._lock:
            self._active_count -= 1
            self._total_processed += 1

        self._semaphore.release()

        logger.debug(
            "队列 %s: 释放槽位 (active=%d, total=%d)",
            self.name, self._active_count, self._total_processed
        )

    @asynccontextmanager
    async def request_slot(self):
        """
        上下文管理器，自动管理槽位的获取和释放

        使用示例：
            async with queue.request_slot():
                await do_something()
        """
        await self.acquire()
        try:
            yield
        finally:
            await self.release()

    def get_status(self) -> Dict[str, int]:
        """
        获取队列状态

        Returns:
            包含 active, waiting, max_concurrent, total_processed 的字典
        """
        return {
            "active": self._active_count,
            "waiting": self._waiting_count,
            "max_concurrent": self._max_concurrent,
            "total_processed": self._total_processed,
        }

    def set_max_concurrent(self, value: int) -> None:
        """
        动态调整最大并发数

        注意：调整后立即生效，但不会中断正在执行的请求。
        如果新值小于当前活跃数，新请求将等待直到活跃数降低。

        Args:
            value: 新的最大并发数
        """
        if value < 1:
            raise ValueError("最大并发数必须大于0")

        old_value = self._max_concurrent
        self._max_concurrent = value

        # 重建Semaphore
        # 注意：这里简单重建，当前等待的请求会继续等待旧的semaphore
        # 更复杂的实现可以考虑使用自定义的可调整Semaphore
        self._semaphore = asyncio.Semaphore(value)

        logger.info(
            "队列 %s: 调整最大并发数 %d -> %d",
            self.name, old_value, value
        )

    @property
    def max_concurrent(self) -> int:
        """获取当前最大并发数"""
        return self._max_concurrent


class ConfigurableRequestQueue(RequestQueue):
    """
    可配置的请求队列单例基类

    通过类属性指定队列名称与配置键，统一单例获取逻辑。
    """

    queue_name: str = ""
    settings_key: str = ""
    default_max_concurrent: int = 1
    log_label: str = ""

    _instance: Optional["ConfigurableRequestQueue"] = None

    def __init__(self, max_concurrent: Optional[int] = None):
        if max_concurrent is None:
            max_concurrent = self.default_max_concurrent
        super().__init__(name=self.queue_name, max_concurrent=max_concurrent)

    @classmethod
    def get_instance(cls) -> "ConfigurableRequestQueue":
        """
        获取队列单例

        首次调用时会根据settings配置初始化队列。
        """
        if cls._instance is None:
            # 延迟导入避免循环引用
            from ...core.config import settings

            max_concurrent = getattr(
                settings,
                cls.settings_key,
                cls.default_max_concurrent
            )
            cls._instance = cls(max_concurrent=max_concurrent)
            label = cls.log_label or cls.queue_name
            logger.info("%s请求队列已创建: max_concurrent=%d", label, max_concurrent)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（仅用于测试）"""
        cls._instance = None
