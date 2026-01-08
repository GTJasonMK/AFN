"""
编程项目详情页Mixins模块
"""

from .header_manager import HeaderManagerMixin
from .tab_manager import TabManagerMixin
from .section_loader import SectionLoaderMixin
from .save_manager import SaveManagerMixin
from .edit_dispatcher import EditDispatcherMixin

__all__ = [
    "HeaderManagerMixin",
    "TabManagerMixin",
    "SectionLoaderMixin",
    "SaveManagerMixin",
    "EditDispatcherMixin",
]
