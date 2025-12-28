"""
通用组件对象池

性能优化：复用频繁创建/销毁的UI组件，避免重复创建开销。

适用场景：
- 章节卡片列表（ChapterCard）
- 角色行列表（CharacterRow）
- 关系行列表（RelationshipRow）
- 版本卡片列表

用法示例：
    from utils.component_pool import ComponentPool

    # 创建池
    pool = ComponentPool(ChapterCard, max_size=50)

    # 获取组件
    card = pool.acquire()
    card.update_data(chapter_data)
    layout.addWidget(card)

    # 释放组件（而不是deleteLater）
    layout.removeWidget(card)
    pool.release(card)

    # 清理池
    pool.clear()
"""

import logging
from typing import TypeVar, Generic, List, Callable, Optional, Any
from weakref import WeakSet

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=QWidget)


class ComponentPool(Generic[T]):
    """通用组件对象池

    泛型类，支持任意QWidget子类的复用。

    特性：
    - 懒创建：只在需要时创建新组件
    - 容量限制：超出max_size时销毁多余组件
    - 安全释放：检查组件是否有效再入池
    - 自动隐藏：释放时自动隐藏组件
    - 重置回调：支持自定义重置逻辑
    """

    def __init__(
        self,
        component_class: type,
        max_size: int = 50,
        factory_args: tuple = (),
        factory_kwargs: Optional[dict] = None,
        reset_callback: Optional[Callable[[T], None]] = None
    ):
        """初始化组件池

        Args:
            component_class: 组件类（必须是QWidget子类）
            max_size: 池的最大容量
            factory_args: 创建组件时传递的位置参数
            factory_kwargs: 创建组件时传递的关键字参数
            reset_callback: 组件重置回调，用于清理组件状态
        """
        self._component_class = component_class
        self._max_size = max_size
        self._factory_args = factory_args
        self._factory_kwargs = factory_kwargs or {}
        self._reset_callback = reset_callback

        # 可用组件池（已创建但未使用）
        self._available: List[T] = []
        # 正在使用的组件（弱引用集合，避免阻止GC）
        self._in_use: WeakSet[T] = WeakSet()

        # 统计信息
        self._created_count = 0
        self._reused_count = 0

    def acquire(self, *args, **kwargs) -> T:
        """获取一个组件

        优先从池中取出已有组件，如果池为空则创建新组件。

        Args:
            *args: 传递给update_data的位置参数（如果组件有此方法）
            **kwargs: 传递给update_data的关键字参数

        Returns:
            可用的组件实例
        """
        component = None

        # 尝试从池中获取
        while self._available:
            candidate = self._available.pop()
            try:
                # 检查组件是否有效（C++对象未被删除）
                if candidate is not None:
                    # 尝试访问属性来验证有效性
                    _ = candidate.isVisible()
                    component = candidate
                    self._reused_count += 1
                    break
            except RuntimeError:
                # C++对象已删除，跳过
                continue

        # 池为空，创建新组件
        if component is None:
            component = self._create_component()
            self._created_count += 1

        # 标记为使用中
        self._in_use.add(component)

        # 注意：不在这里调用show()，组件添加到布局后会自动显示
        # 如果在这里调用show()，而组件还没有父组件，会导致它作为独立窗口弹出

        # 如果传入了数据参数，调用update_data
        if (args or kwargs) and hasattr(component, 'update_data'):
            component.update_data(*args, **kwargs)

        return component

    def release(self, component: T) -> bool:
        """释放组件回池

        Args:
            component: 要释放的组件

        Returns:
            是否成功释放（池满时返回False，组件会被销毁）
        """
        if component is None:
            return False

        try:
            # 检查组件是否有效
            _ = component.isVisible()
        except RuntimeError:
            # C++对象已删除
            return False

        # 从使用中集合移除
        self._in_use.discard(component)

        # 隐藏组件
        component.hide()

        # 从父容器移除（如果有）
        if component.parent():
            component.setParent(None)

        # 执行重置回调
        if self._reset_callback:
            try:
                self._reset_callback(component)
            except Exception as e:
                logger.warning(f"组件重置回调失败: {e}")

        # 检查池容量
        if len(self._available) < self._max_size:
            self._available.append(component)
            return True
        else:
            # 池已满，销毁组件
            try:
                component.deleteLater()
            except RuntimeError:
                pass
            return False

    def release_all(self, components: List[T]):
        """批量释放组件

        Args:
            components: 要释放的组件列表
        """
        for component in components:
            self.release(component)

    def clear(self):
        """清空池，销毁所有组件"""
        # 清空可用池
        for component in self._available:
            try:
                component.deleteLater()
            except RuntimeError:
                pass
        self._available.clear()

        # 使用中的组件由持有者负责销毁
        self._in_use.clear()

        logger.debug(
            f"组件池已清空: {self._component_class.__name__}, "
            f"创建{self._created_count}次, 复用{self._reused_count}次"
        )

    def _create_component(self) -> T:
        """创建新组件"""
        return self._component_class(*self._factory_args, **self._factory_kwargs)

    @property
    def available_count(self) -> int:
        """可用组件数量"""
        return len(self._available)

    @property
    def in_use_count(self) -> int:
        """使用中的组件数量"""
        return len(self._in_use)

    @property
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            'component_class': self._component_class.__name__,
            'max_size': self._max_size,
            'available': len(self._available),
            'in_use': len(self._in_use),
            'created': self._created_count,
            'reused': self._reused_count,
            'reuse_rate': (
                self._reused_count / (self._created_count + self._reused_count)
                if (self._created_count + self._reused_count) > 0
                else 0
            )
        }


class PoolManager:
    """组件池管理器（单例）

    集中管理所有组件池，提供全局访问和统计。
    """

    _instance: Optional['PoolManager'] = None

    def __init__(self):
        self._pools: dict[str, ComponentPool] = {}

    @classmethod
    def instance(cls) -> 'PoolManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_pool(
        self,
        name: str,
        component_class: type = None,
        max_size: int = 50,
        **kwargs
    ) -> ComponentPool:
        """获取或创建命名池

        Args:
            name: 池名称
            component_class: 组件类（首次创建时必须提供）
            max_size: 池的最大容量
            **kwargs: 传递给ComponentPool的其他参数

        Returns:
            组件池实例
        """
        if name not in self._pools:
            if component_class is None:
                raise ValueError(f"首次创建池 '{name}' 时必须提供 component_class")
            self._pools[name] = ComponentPool(
                component_class,
                max_size=max_size,
                **kwargs
            )
        return self._pools[name]

    def clear_all(self):
        """清空所有池"""
        for pool in self._pools.values():
            pool.clear()
        self._pools.clear()

    def get_all_stats(self) -> dict:
        """获取所有池的统计信息"""
        return {name: pool.stats for name, pool in self._pools.items()}

    def log_stats(self):
        """记录所有池的统计信息"""
        for name, stats in self.get_all_stats().items():
            logger.info(
                f"组件池 [{name}]: "
                f"可用{stats['available']}/{stats['max_size']}, "
                f"使用中{stats['in_use']}, "
                f"复用率{stats['reuse_rate']:.1%}"
            )


# 便捷函数
def get_pool(name: str, component_class: type = None, **kwargs) -> ComponentPool:
    """获取或创建命名池（便捷函数）"""
    return PoolManager.instance().get_pool(name, component_class, **kwargs)


def reset_chapter_card(card):
    """ChapterCard重置回调"""
    card.is_selected = False
    card._is_hovered = False
    if hasattr(card, 'chapter_data'):
        card.chapter_data = {}


def reset_character_row(row):
    """CharacterRow重置回调"""
    if hasattr(row, 'data'):
        row.data = {}


def reset_relationship_row(row):
    """RelationshipRow重置回调"""
    if hasattr(row, 'data'):
        row.data = {}


def reset_chapter_outline_card(card):
    """ChapterOutlineCard重置回调"""
    if hasattr(card, 'chapter'):
        card.chapter = {}
    if hasattr(card, 'chapter_number'):
        card.chapter_number = 0


def reset_outline_row(row):
    """OutlineRow重置回调"""
    if hasattr(row, 'data'):
        row.data = {}


__all__ = [
    'ComponentPool',
    'PoolManager',
    'get_pool',
    'reset_chapter_card',
    'reset_character_row',
    'reset_relationship_row',
    'reset_chapter_outline_card',
    'reset_outline_row',
]
