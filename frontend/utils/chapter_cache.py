"""
章节数据LRU缓存

性能优化：缓存最近访问的章节数据，避免重复API调用。

特性：
- LRU淘汰策略：超出容量时移除最久未访问的
- 时间过期：超过TTL的数据视为过期
- 线程安全：使用锁保护
- 预取支持：后台预取相邻章节

用法：
    from utils.chapter_cache import get_chapter_cache

    cache = get_chapter_cache()

    # 获取（命中返回数据，未命中返回None）
    chapter = cache.get(project_id, chapter_number)

    # 存入
    cache.set(project_id, chapter_number, chapter_data)

    # 失效
    cache.invalidate(project_id, chapter_number)
"""

import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass
from time import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Dict[str, Any]
    timestamp: float
    version_hash: str  # 用于检测数据是否过期


class ChapterCache:
    """章节数据LRU缓存

    特性：
    - LRU淘汰策略：超出容量时移除最久未访问的
    - 时间过期：超过TTL的数据视为过期
    - 线程安全：使用锁保护
    - 预取支持：后台预取相邻章节
    """

    def __init__(self, max_size: int = 20, ttl: float = 300.0):
        """
        Args:
            max_size: 最大缓存章节数
            ttl: 过期时间（秒），默认5分钟
        """
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()

        # 预取相关
        self._prefetch_in_progress: set = set()  # 正在预取的章节

        # 统计
        self._hits = 0
        self._misses = 0

    def _make_key(self, project_id: str, chapter_number: int) -> str:
        """生成缓存键"""
        return f"{project_id}:{chapter_number}"

    def _compute_version_hash(self, data: Dict[str, Any]) -> str:
        """计算数据版本哈希（用于检测变更）"""
        # 使用关键字段生成简单哈希
        content = data.get('content', '') or ''
        versions = data.get('versions', []) or []
        selected = data.get('selected_version')
        return f"{len(content)}:{len(versions)}:{selected}"

    def get(self, project_id: str, chapter_number: int) -> Optional[Dict[str, Any]]:
        """获取缓存的章节数据

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节数据，未命中或已过期返回None
        """
        key = self._make_key(project_id, chapter_number)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if time() - entry.timestamp > self._ttl:
                del self._cache[key]
                self._misses += 1
                logger.debug(f"章节缓存已过期: {key}")
                return None

            # 移到末尾（最近访问）
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"章节缓存命中: 第{chapter_number}章")
            return entry.data

    def set(self, project_id: str, chapter_number: int, data: Dict[str, Any]):
        """存入章节数据

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            data: 章节数据
        """
        key = self._make_key(project_id, chapter_number)

        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                del self._cache[key]

            # 添加新条目
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=time(),
                version_hash=self._compute_version_hash(data)
            )

            # LRU淘汰
            while len(self._cache) > self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"章节缓存淘汰: {oldest_key}")

            logger.debug(f"章节缓存存入: 第{chapter_number}章")

    def invalidate(self, project_id: str, chapter_number: int = None):
        """失效缓存

        Args:
            project_id: 项目ID
            chapter_number: 章节号，为None时失效该项目所有章节
        """
        with self._lock:
            if chapter_number is not None:
                key = self._make_key(project_id, chapter_number)
                if key in self._cache:
                    del self._cache[key]
                    logger.debug(f"章节缓存失效: 第{chapter_number}章")
            else:
                # 失效该项目所有章节
                keys_to_remove = [
                    k for k in self._cache.keys()
                    if k.startswith(f"{project_id}:")
                ]
                for key in keys_to_remove:
                    del self._cache[key]
                if keys_to_remove:
                    logger.debug(f"项目缓存失效: {project_id}, 共{len(keys_to_remove)}章")

    def invalidate_all(self):
        """清空所有缓存"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            if count:
                logger.debug(f"清空所有章节缓存: {count}章")

    def contains(self, project_id: str, chapter_number: int) -> bool:
        """检查是否包含指定章节（不更新LRU顺序）

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            是否包含且未过期
        """
        key = self._make_key(project_id, chapter_number)

        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            # 检查是否过期
            if time() - entry.timestamp > self._ttl:
                del self._cache[key]
                return False

            return True

    def prefetch_adjacent(
        self,
        project_id: str,
        current_chapter: int,
        total_chapters: int,
        fetch_func: Callable[[str, int], Dict[str, Any]],
        direction: str = "both"
    ):
        """预取相邻章节（后台执行）

        Args:
            project_id: 项目ID
            current_chapter: 当前章节号
            total_chapters: 总章节数
            fetch_func: 获取章节的函数 (project_id, chapter_number) -> data
            direction: 预取方向 "forward"(后), "backward"(前), "both"(双向)
        """
        # 计算要预取的章节
        to_prefetch = []

        if direction in ("backward", "both") and current_chapter > 1:
            to_prefetch.append(current_chapter - 1)

        if direction in ("forward", "both") and current_chapter < total_chapters:
            to_prefetch.append(current_chapter + 1)

        # 过滤已缓存的和正在预取的
        to_prefetch = [
            ch for ch in to_prefetch
            if not self.contains(project_id, ch)
            and self._make_key(project_id, ch) not in self._prefetch_in_progress
        ]

        if not to_prefetch:
            return

        # 标记为正在预取
        for ch in to_prefetch:
            self._prefetch_in_progress.add(self._make_key(project_id, ch))

        def do_prefetch():
            for chapter_num in to_prefetch:
                key = self._make_key(project_id, chapter_num)
                try:
                    data = fetch_func(project_id, chapter_num)
                    self.set(project_id, chapter_num, data)
                    logger.debug(f"预取完成: 第{chapter_num}章")
                except Exception as e:
                    logger.warning(f"预取失败: 第{chapter_num}章 - {e}")
                finally:
                    self._prefetch_in_progress.discard(key)

        # 使用线程后台预取
        thread = threading.Thread(target=do_prefetch, daemon=True)
        thread.start()

    def prefetch_single(
        self,
        project_id: str,
        chapter_number: int,
        fetch_func: Callable[[str, int], Dict[str, Any]]
    ):
        """预取单个章节（后台执行）

        用于悬停预加载场景。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            fetch_func: 获取章节的函数
        """
        # 检查是否已缓存或正在预取
        if self.contains(project_id, chapter_number):
            return

        key = self._make_key(project_id, chapter_number)
        if key in self._prefetch_in_progress:
            return

        # 标记为正在预取
        self._prefetch_in_progress.add(key)

        def do_prefetch():
            try:
                data = fetch_func(project_id, chapter_number)
                self.set(project_id, chapter_number, data)
                logger.debug(f"悬停预取完成: 第{chapter_number}章")
            except Exception as e:
                logger.warning(f"悬停预取失败: 第{chapter_number}章 - {e}")
            finally:
                self._prefetch_in_progress.discard(key)

        # 使用线程后台预取
        thread = threading.Thread(target=do_prefetch, daemon=True)
        thread.start()

    @property
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1%}",
            'prefetch_in_progress': len(self._prefetch_in_progress)
        }

    def log_stats(self):
        """记录缓存统计到日志"""
        stats = self.stats
        logger.info(
            f"章节缓存统计: "
            f"大小={stats['size']}/{stats['max_size']}, "
            f"命中率={stats['hit_rate']}, "
            f"命中={stats['hits']}, "
            f"未命中={stats['misses']}"
        )


# 全局单例
_chapter_cache: Optional[ChapterCache] = None


def get_chapter_cache() -> ChapterCache:
    """获取全局章节缓存实例"""
    global _chapter_cache
    if _chapter_cache is None:
        _chapter_cache = ChapterCache(max_size=20, ttl=300)
    return _chapter_cache


def reset_chapter_cache():
    """重置全局缓存（用于测试）"""
    global _chapter_cache
    if _chapter_cache:
        _chapter_cache.invalidate_all()
    _chapter_cache = None


__all__ = [
    'ChapterCache',
    'get_chapter_cache',
    'reset_chapter_cache',
]
