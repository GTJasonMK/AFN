"""
主题配置设置Widget（兼容层）

此文件保留用于向后兼容，实际实现已迁移到 theme_settings 子模块。

新代码请直接从子模块导入：
    from windows.settings.theme_settings import ThemeSettingsWidget, CONFIG_GROUPS
"""

# 从子模块重新导出，保持向后兼容
from .theme_settings import (
    ThemeSettingsWidget,
    CONFIG_GROUPS,
    ThemeStylesMixin,
    ThemeConfigEditorMixin,
    ThemeIOHandlerMixin,
)


__all__ = [
    "ThemeSettingsWidget",
    "CONFIG_GROUPS",
    "ThemeStylesMixin",
    "ThemeConfigEditorMixin",
    "ThemeIOHandlerMixin",
]
