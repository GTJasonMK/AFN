"""
主题默认值工具函数
"""

from typing import Any, Dict

from .v1_defaults import LIGHT_THEME_DEFAULTS, DARK_THEME_DEFAULTS
from .v2_defaults import LIGHT_THEME_V2_DEFAULTS, DARK_THEME_V2_DEFAULTS


def get_theme_defaults(mode: str, version: int = 1) -> Dict[str, Any]:
    """获取指定模式的默认主题值

    Args:
        mode: 主题模式 ("light" 或 "dark")
        version: 配置版本 (1 = V1面向常量, 2 = V2面向组件)

    Returns:
        dict: 默认主题配置
    """
    if version == 2:
        return DARK_THEME_V2_DEFAULTS if mode == "dark" else LIGHT_THEME_V2_DEFAULTS
    return DARK_THEME_DEFAULTS if mode == "dark" else LIGHT_THEME_DEFAULTS


def get_theme_v2_defaults(mode: str) -> Dict[str, Any]:
    """获取指定模式的V2默认主题值（面向组件）

    Args:
        mode: 主题模式 ("light" 或 "dark")

    Returns:
        dict: V2默认主题配置
    """
    return DARK_THEME_V2_DEFAULTS if mode == "dark" else LIGHT_THEME_V2_DEFAULTS
