"""
写作台面板组件模块

包含写作台各个Tab面板的独立实现，从 WDWorkspace 中解耦以提高可维护性。
每个 Builder 类负责创建特定Tab的所有UI组件，遵循单一职责原则。

架构说明：
- BasePanelBuilder: 所有面板构建器的抽象基类
- *PanelBuilder: 具体的面板构建器实现
"""

from .base import BasePanelBuilder
from .analysis_panel import AnalysisPanelBuilder
from .version_panel import VersionPanelBuilder
from .review_panel import ReviewPanelBuilder
from .summary_panel import SummaryPanelBuilder
from .content_panel import ContentPanelBuilder

__all__ = [
    'BasePanelBuilder',
    'AnalysisPanelBuilder',
    'VersionPanelBuilder',
    'ReviewPanelBuilder',
    'SummaryPanelBuilder',
    'ContentPanelBuilder',
]
