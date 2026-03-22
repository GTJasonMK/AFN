"""
章节生成模块

将原来的章节生成服务拆分为多个职责单一的子模块：
- context: 数据结构定义
- prompt_builder: 提示词构建
- version_processor: 版本处理
- workflow: 完整工作流
- service: 核心服务（协调者）
"""

from .workflow import ChapterGenerationWorkflow
from .service import ChapterGenerationService

__all__ = [
    # 工作流
    "ChapterGenerationWorkflow",
    # 核心服务
    "ChapterGenerationService",
]
