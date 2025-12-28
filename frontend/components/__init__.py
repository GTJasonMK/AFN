"""
可复用UI组件模块
"""

from .loading_spinner import (
    CircularSpinner,
    DotsSpinner,
    LoadingOverlay,
    InlineLoadingState,
    SkeletonLoader,
    ListLoadingState,
    LoadingStateManager,
    loading_context
)

from .dialogs import (
    ConfirmDialog,
    AlertDialog,
    InputDialog,
    TextInputDialog,
    IntInputDialog,
    LoadingDialog
)

from .empty_state import (
    EmptyState,
    EmptyStateWithIllustration
)

from .base import (
    ThemeAwareWidget,
    ThemeAwareFrame
)

from .virtual_list import VirtualListWidget

from .lazy_tab_widget import LazyTabWidget

__all__ = [
    # 加载状态组件
    'CircularSpinner',
    'DotsSpinner',
    'LoadingOverlay',
    'InlineLoadingState',
    'SkeletonLoader',
    'ListLoadingState',
    'LoadingStateManager',
    'loading_context',
    # 对话框
    'ConfirmDialog',
    'AlertDialog',
    'InputDialog',
    'TextInputDialog',
    'IntInputDialog',
    'LoadingDialog',
    # 空状态
    'EmptyState',
    'EmptyStateWithIllustration',
    # 基础组件
    'ThemeAwareWidget',
    'ThemeAwareFrame',
    # 虚拟列表
    'VirtualListWidget',
    # 懒加载Tab
    'LazyTabWidget',
]
