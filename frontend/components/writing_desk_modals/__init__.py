"""
写作台Modal对话框组件

对应Vue3的UI设计规范
"""

from .evaluation_detail_modal import WDEvaluationDetailModal
from .version_detail_modal import WDVersionDetailModal
from .generate_outline_modal import WDGenerateOutlineModal

__all__ = [
    'WDEvaluationDetailModal',
    'WDVersionDetailModal',
    'WDGenerateOutlineModal',
]
