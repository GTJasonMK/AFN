"""
漫画提示词服务 V2 - 兼容层

此文件为向后兼容保留，实际实现已迁移到 core/ 子模块。
请使用新的导入路径：
    from .core import MangaPromptServiceV2, MangaGenerationResult, MangaStyle

或直接从包级别导入：
    from app.services.manga_prompt import MangaPromptServiceV2, MangaGenerationResult, MangaStyle
"""

# 从新位置重新导出，保持向后兼容
from .core import (
    # 主服务
    MangaPromptServiceV2,
    generate_manga_prompts,
    # 数据结构
    MangaStyle,
    MangaGenerationResult,
    # 子组件
    SceneExtractor,
    CheckpointManager,
    ResultPersistence,
    # 提示词
    SCENE_EXTRACTION_PROMPT,
    LANGUAGE_HINTS,
)

__all__ = [
    "MangaPromptServiceV2",
    "generate_manga_prompts",
    "MangaStyle",
    "MangaGenerationResult",
    "SceneExtractor",
    "CheckpointManager",
    "ResultPersistence",
    "SCENE_EXTRACTION_PROMPT",
    "LANGUAGE_HINTS",
]
