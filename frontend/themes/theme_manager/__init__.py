"""
主题管理器模块

提供统一的主题切换接口，让用户可以在不同主题间自由切换。
集成现代美学效果（渐变、玻璃态、新拟态）。

支持两种配置格式：
- V1（旧版）：面向常量的配置
- V2（新版）：面向组件的配置

主要导出:
    - theme_manager: 全局主题管理器实例（单例）
    - ThemeManager: 主题管理器类
    - ThemeMode: 主题模式枚举 (LIGHT/DARK)
    - BookPalette: 书香风格调色板命名元组
    - LightTheme: 亮色主题类
    - DarkTheme: 深色主题类
    - V2ConfigMixin: V2配置访问Mixin
"""

from .core import theme_manager
from .themes import ThemeMode

__all__ = [
    'theme_manager',
    'ThemeMode',
]
