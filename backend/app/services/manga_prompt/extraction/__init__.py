"""
信息提取模块

从章节内容中提取结构化信息，包括：
- 人物信息（外观/性格/关系）
- 对话信息（说话人/内容/情绪）
- 旁白信息（叙述/场景描述/时间跳转）
- 场景信息（地点/时间/氛围）
- 事件信息（动作/冲突/转折）
- 物品信息（关键道具/环境元素）
"""

from .models import (
    ChapterInfo,
)
from .chapter_info_extractor import ChapterInfoExtractor

__all__ = [
    "ChapterInfo",
    "ChapterInfoExtractor",
]
