"""
可复用UI组件模块
"""

from .loading_spinner import (
    CircularSpinner,
    DotsSpinner,
    LoadingOverlay,
    InlineSpinner
)

from .writing_desk_modals import (
    WDEditChapterModal,
    WDEvaluationDetailModal,
    WDVersionDetailModal,
    WDGenerateOutlineModal
)

from .dialogs import (
    ConfirmDialog,
    AlertDialog,
    InputDialog,
    TextInputDialog,
    IntInputDialog,
    LoadingDialog
)

from .skeleton import (
    SkeletonLine,
    SkeletonCircle,
    SkeletonCard,
    SkeletonList,
    SkeletonTable,
    SkeletonDetailPage,
    SkeletonPresets
)

from .empty_state import (
    EmptyState,
    EmptyStateWithIllustration,
    EmptyStatePresets
)

from .base import (
    ThemeAwareWidget,
    ThemeAwareFrame
)

__all__ = [
    'CircularSpinner',
    'DotsSpinner',
    'LoadingOverlay',
    'InlineSpinner',
    'WDEditChapterModal',
    'WDEvaluationDetailModal',
    'WDVersionDetailModal',
    'WDGenerateOutlineModal',
    'ConfirmDialog',
    'AlertDialog',
    'InputDialog',
    'TextInputDialog',
    'IntInputDialog',
    'LoadingDialog',
    'SkeletonLine',
    'SkeletonCircle',
    'SkeletonCard',
    'SkeletonList',
    'SkeletonTable',
    'SkeletonDetailPage',
    'SkeletonPresets',
    'EmptyState',
    'EmptyStateWithIllustration',
    'EmptyStatePresets',
    'ThemeAwareWidget',
    'ThemeAwareFrame'
]
