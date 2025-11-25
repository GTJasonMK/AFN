"""
写作台模块 - 章节生成与版本管理

拆分为多个组件：
- WDHeader: 顶部导航栏
- WDSidebar: 左侧章节列表
- WDWorkspace: 主工作区
- WritingDesk: 主类
"""

from .main import WritingDesk

__all__ = ['WritingDesk']
