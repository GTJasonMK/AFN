"""
主题管理器模块

提供统一的主题切换接口，让用户可以在不同主题间自由切换。
集成现代美学效果（渐变、玻璃态、新拟态）。

主要导出:
    - theme_manager: 全局主题管理器实例（单例）
    - ThemeManager: 主题管理器类
    - ThemeMode: 主题模式枚举 (LIGHT/DARK)
    - BookPalette: 书香风格调色板命名元组
    - LightTheme: 亮色主题类
    - DarkTheme: 深色主题类
"""

from .core import ThemeManager, theme_manager
from .themes import ThemeMode, BookPalette, LightTheme, DarkTheme
from .constants import DesignSystemConstants

__all__ = [
    # 核心导出
    'theme_manager',
    'ThemeManager',
    'ThemeMode',
    'BookPalette',
    # 主题类（可选使用）
    'LightTheme',
    'DarkTheme',
    'DesignSystemConstants',
]
