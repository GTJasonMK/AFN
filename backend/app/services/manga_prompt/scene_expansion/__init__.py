"""
场景展开模块

将叙事场景展开为专业漫画分镜（页面+画格）。

主要组件：
- SceneExpansionService: 核心服务类
- SceneAnalyzer: 场景分析器
- LayoutSelector: 布局选择器
- ContentGenerator: 内容生成器
- HistoryManager: 布局历史管理器
"""

# 主服务类
from .service import (
    SceneExpansionService,
    expand_scene_to_manga,
)

# 子组件（供需要自定义流程的场景使用）
from .scene_analyzer import SceneAnalyzer
from .layout_selector import LayoutSelector
from .content_generator import ContentGenerator
from .history_manager import HistoryManager

# 提示词模板（供需要直接访问的场景使用）
from .prompts import (
    SCENE_ANALYSIS_PROMPT,
    PANEL_DISTRIBUTION_PROMPT,
)


__all__ = [
    # 主要导出（向后兼容）
    "SceneExpansionService",
    "expand_scene_to_manga",
    # 子组件
    "SceneAnalyzer",
    "LayoutSelector",
    "ContentGenerator",
    "HistoryManager",
    # 提示词模板
    "SCENE_ANALYSIS_PROMPT",
    "PANEL_DISTRIBUTION_PROMPT",
]
