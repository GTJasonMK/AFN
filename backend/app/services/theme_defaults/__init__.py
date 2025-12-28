"""
主题默认配置模块

提供V1和V2版本的亮色/暗色主题默认值。
"""

from .v1_defaults import LIGHT_THEME_DEFAULTS, DARK_THEME_DEFAULTS
from .v2_defaults import LIGHT_THEME_V2_DEFAULTS, DARK_THEME_V2_DEFAULTS
from .utils import get_theme_defaults, get_theme_v2_defaults

__all__ = [
    # V1默认值
    "LIGHT_THEME_DEFAULTS",
    "DARK_THEME_DEFAULTS",
    # V2默认值
    "LIGHT_THEME_V2_DEFAULTS",
    "DARK_THEME_V2_DEFAULTS",
    # 工具函数
    "get_theme_defaults",
    "get_theme_v2_defaults",
]
