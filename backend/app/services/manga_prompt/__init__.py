"""
漫画提示词服务模块

基于页面驱动的漫画分镜生成服务。

核心流程：
1. 信息提取 - 从章节内容提取结构化信息（角色、对话、事件、场景）
2. 页面规划 - 全局页面规划，确定页数和事件分配
3. 分镜设计 - 为每页设计分镜（支持排版信息）
4. 提示词构建 - 生成AI绘图提示词

模块结构：
- extraction/ - 章节信息提取
- planning/ - 页面规划
- storyboard/ - 分镜设计
- prompt_builder/ - 提示词构建
- core/ - 主服务
"""

# 主服务
from .core import (
    MangaPromptServiceV2,
)

# 提示词构建
from .prompt_builder import (
    MangaPromptResult,
)


__all__ = [
    "MangaPromptServiceV2",
    "MangaPromptResult",
]
