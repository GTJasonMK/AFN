"""
漫画提示词服务核心模块

基于页面驱动的漫画分镜生成服务核心。

核心流程：
1. 信息提取 - 从章节内容提取结构化信息
2. 页面规划 - 全局页面规划
3. 分镜设计 - 为每页设计详细分镜
4. 提示词构建 - 生成AI绘图提示词
"""

# 主服务类和便捷函数
from .service import (
    MangaPromptServiceV2,
    generate_manga_prompts,
)

# 数据结构
from .models import MangaStyle

# 辅助组件
from .checkpoint_manager import CheckpointManager
from .result_persistence import ResultPersistence


__all__ = [
    # 主要导出
    "MangaPromptServiceV2",
    "generate_manga_prompts",
    "MangaStyle",
    # 辅助组件
    "CheckpointManager",
    "ResultPersistence",
]
