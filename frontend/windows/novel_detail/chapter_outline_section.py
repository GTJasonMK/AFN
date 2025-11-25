"""
章节大纲 Section - 现代化设计

此文件已重构为模块化设计，保留此文件以兼容旧代码导入。
实际实现位于 chapter_outline/ 子目录。

管理章节大纲的生成、展示和编辑，支持长篇和短篇流程
"""

# 从新模块导入，保持向后兼容
from .chapter_outline import ChapterOutlineSection

__all__ = ['ChapterOutlineSection']
