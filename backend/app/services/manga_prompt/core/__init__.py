"""
漫画提示词服务核心模块

基于专业漫画分镜理念设计的服务核心。

主要组件：
- MangaPromptServiceV2: 主服务类
- MangaGenerationResult: 生成结果数据结构
- MangaStyle: 漫画风格常量
- SceneExtractor: 场景提取器
- CheckpointManager: 断点管理器
- ResultPersistence: 结果持久化管理器
"""

# 主服务类和便捷函数
from .service import (
    MangaPromptServiceV2,
    generate_manga_prompts,
)

# 数据结构
from .models import (
    MangaStyle,
    MangaGenerationResult,
)

# 子组件（供需要自定义流程的场景使用）
from .scene_extractor import SceneExtractor
from .checkpoint_manager import CheckpointManager
from .result_persistence import ResultPersistence

# 提示词模板（供需要直接访问的场景使用）
from .prompts import (
    SCENE_EXTRACTION_PROMPT,
    LANGUAGE_HINTS,
)


__all__ = [
    # 主要导出（向后兼容）
    "MangaPromptServiceV2",
    "generate_manga_prompts",
    "MangaStyle",
    "MangaGenerationResult",
    # 子组件
    "SceneExtractor",
    "CheckpointManager",
    "ResultPersistence",
    # 提示词模板
    "SCENE_EXTRACTION_PROMPT",
    "LANGUAGE_HINTS",
]
