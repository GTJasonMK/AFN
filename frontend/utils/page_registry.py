"""
页面注册表模块

实现注册表模式（Registry Pattern），解耦MainWindow与具体页面类的依赖。
遵循开闭原则（OCP）：新增页面只需注册，无需修改MainWindow。

使用方法：
1. 简单页面（只需parent参数）：使用 @register_page 装饰器
2. 复杂页面（需要额外参数）：使用 @register_page_factory 装饰器

示例：
    # 简单页面
    @register_page('HOME')
    class HomePage(BasePage):
        pass

    # 复杂页面
    @register_page_factory('DETAIL')
    def create_detail_page(parent, **kwargs):
        project_id = kwargs.get('project_id')
        return NovelDetail(project_id, parent)
"""

import logging
from typing import Callable, Dict, Optional, Type

from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


# 页面类注册表
_page_registry: Dict[str, Type[QWidget]] = {}

# 页面工厂函数注册表
_page_factory_registry: Dict[str, Callable[..., Optional[QWidget]]] = {}


def register_page(page_type: str):
    """
    页面注册装饰器

    用于注册简单页面类，构造函数只接受 parent 参数。

    Args:
        page_type: 页面类型标识符（如 'HOME', 'SETTINGS'）

    Example:
        @register_page('HOME')
        class HomePage(BasePage):
            def __init__(self, parent=None):
                super().__init__(parent)
    """
    def decorator(cls: Type[QWidget]) -> Type[QWidget]:
        _page_registry[page_type] = cls
        logger.debug("注册页面类: %s -> %s", page_type, cls.__name__)
        return cls
    return decorator


def register_page_factory(page_type: str):
    """
    页面工厂函数注册装饰器

    用于注册需要特殊构造逻辑的页面（如需要额外参数）。

    Args:
        page_type: 页面类型标识符

    Example:
        @register_page_factory('DETAIL')
        def create_detail_page(parent, **kwargs):
            project_id = kwargs.get('project_id')
            if not project_id:
                return None
            return NovelDetail(project_id, parent)
    """
    def decorator(factory_func: Callable[..., Optional[QWidget]]) -> Callable[..., Optional[QWidget]]:
        _page_factory_registry[page_type] = factory_func
        logger.debug("注册页面工厂: %s -> %s", page_type, factory_func.__name__)
        return factory_func
    return decorator


def create_page(page_type: str, parent: QWidget, **kwargs) -> Optional[QWidget]:
    """
    创建页面实例

    优先使用工厂函数，其次使用注册的类。

    Args:
        page_type: 页面类型标识符
        parent: 父组件
        **kwargs: 传递给页面构造函数的额外参数

    Returns:
        页面实例，如果页面类型未注册则返回 None
    """
    # 优先使用工厂函数
    if page_type in _page_factory_registry:
        factory = _page_factory_registry[page_type]
        try:
            return factory(parent, **kwargs)
        except Exception as e:
            logger.error("创建页面 %s 失败: %s", page_type, e)
            return None

    # 使用注册的类
    if page_type in _page_registry:
        cls = _page_registry[page_type]
        try:
            return cls(parent)
        except Exception as e:
            logger.error("创建页面 %s 失败: %s", page_type, e)
            return None

    # 未注册
    return None


def is_page_registered(page_type: str) -> bool:
    """检查页面类型是否已注册"""
    return page_type in _page_registry or page_type in _page_factory_registry


def get_registered_page_types() -> list:
    """获取所有已注册的页面类型"""
    return list(set(_page_registry.keys()) | set(_page_factory_registry.keys()))


# ------------------------------------------------------------------
# 页面注册（使用工厂函数注册需要参数的页面）
# ------------------------------------------------------------------

@register_page_factory('HOME')
def _create_home_page(parent, **kwargs):
    """创建首页"""
    from pages.home_page import HomePage
    return HomePage(parent)


@register_page_factory('SETTINGS')
def _create_settings_page(parent, **kwargs):
    """创建设置页"""
    from windows.settings import SettingsView
    return SettingsView(parent)


@register_page_factory('INSPIRATION')
def _create_inspiration_page(parent, **kwargs):
    """创建灵感对话页"""
    from windows.inspiration_mode import InspirationMode
    return InspirationMode(parent)


@register_page_factory('DETAIL')
def _create_detail_page(parent, **kwargs):
    """创建项目详情页"""
    from windows.novel_detail import NovelDetail
    project_id = kwargs.get('project_id')
    if not project_id:
        logger.error("DETAIL页面缺少project_id参数")
        return None
    return NovelDetail(project_id, parent)


@register_page_factory('WRITING_DESK')
def _create_writing_desk_page(parent, **kwargs):
    """创建写作台页"""
    from windows.writing_desk import WritingDesk
    project_id = kwargs.get('project_id')
    if not project_id:
        logger.error("WRITING_DESK页面缺少project_id参数")
        return None
    return WritingDesk(project_id, parent)


@register_page_factory('CODING_DETAIL')
def _create_coding_detail_page(parent, **kwargs):
    """创建编程项目详情页"""
    from windows.coding_detail import CodingDetail
    project_id = kwargs.get('project_id')
    if not project_id:
        logger.error("CODING_DETAIL页面缺少project_id参数")
        return None
    return CodingDetail(project_id, parent)


@register_page_factory('CODING_DESK')
def _create_coding_desk_page(parent, **kwargs):
    """创建Prompt生成工作台页"""
    from windows.coding_desk import CodingDesk
    project_id = kwargs.get('project_id')
    if not project_id:
        logger.error("CODING_DESK页面缺少project_id参数")
        return None
    return CodingDesk(project_id, parent)


@register_page_factory('CODING_INSPIRATION')
def _create_coding_inspiration_page(parent, **kwargs):
    """创建编程项目需求分析对话页"""
    from windows.coding_inspiration import CodingInspirationMode
    return CodingInspirationMode(parent)
