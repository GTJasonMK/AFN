"""
写作台主工作区模块

将原有的大型 workspace.py 拆分为多个小模块：
- core.py: 主类定义、信号、初始化
- theme_refresh.py: 主题刷新相关方法
- chapter_display.py: 章节加载和显示
- inline_diff.py: 内联diff功能
- manga_handlers.py: 漫画相关处理方法
- generation_handlers.py: 章节生成过程的UI处理
"""

from .core import WDWorkspace

__all__ = ['WDWorkspace']
