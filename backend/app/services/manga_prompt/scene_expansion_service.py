"""
场景展开服务 - 兼容层

此文件为向后兼容保留，实际实现已迁移到 scene_expansion/ 子模块。
请使用新的导入路径：
    from .scene_expansion import SceneExpansionService, expand_scene_to_manga

或直接从包级别导入：
    from app.services.manga_prompt import SceneExpansionService, expand_scene_to_manga
"""

# 从新位置重新导出，保持向后兼容
from .scene_expansion import (
    SceneExpansionService,
    expand_scene_to_manga,
    # 子组件
    SceneAnalyzer,
    LayoutSelector,
    ContentGenerator,
    HistoryManager,
    # 提示词模板
    SCENE_ANALYSIS_PROMPT,
    PANEL_DISTRIBUTION_PROMPT,
)

__all__ = [
    "SceneExpansionService",
    "expand_scene_to_manga",
    "SceneAnalyzer",
    "LayoutSelector",
    "ContentGenerator",
    "HistoryManager",
    "SCENE_ANALYSIS_PROMPT",
    "PANEL_DISTRIBUTION_PROMPT",
]
