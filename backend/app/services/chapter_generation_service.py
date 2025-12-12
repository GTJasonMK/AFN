"""
章节生成服务 - 向后兼容模块

此文件作为兼容性shim，所有实现已迁移至 chapter_generation/ 子模块。
新代码请直接导入 from app.services.chapter_generation import ...

模块结构：
- chapter_generation/context.py: 数据结构定义
- chapter_generation/prompt_builder.py: 提示词构建
- chapter_generation/version_processor.py: 版本处理
- chapter_generation/workflow.py: 完整工作流
- chapter_generation/service.py: 核心服务（协调者）
"""

import warnings

warnings.warn(
    "从 'app.services.chapter_generation_service' 导入已废弃，"
    "请改用 'from app.services.chapter_generation import ...'",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有公开API，保持向后兼容
from .chapter_generation import (
    # 数据结构
    ChapterGenerationContext,
    ChapterGenerationResult,
    # 提示词构建
    ChapterPromptBuilder,
    get_chapter_prompt_builder,
    # 版本处理
    ChapterVersionProcessor,
    get_version_processor,
    # 工作流
    ChapterGenerationWorkflow,
    # 核心服务
    ChapterGenerationService,
)

__all__ = [
    "ChapterGenerationContext",
    "ChapterGenerationResult",
    "ChapterPromptBuilder",
    "get_chapter_prompt_builder",
    "ChapterVersionProcessor",
    "get_version_processor",
    "ChapterGenerationWorkflow",
    "ChapterGenerationService",
]
