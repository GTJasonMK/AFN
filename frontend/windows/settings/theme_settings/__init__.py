"""
主题配置设置模块

提供主题配置的完整编辑界面，支持两种模式：
- V1（旧版）：面向常量的配置编辑
- V2（新版）：面向组件的配置编辑

V1 架构说明：
- ThemeSettingsWidget: V1主Widget类，负责UI布局
- ThemeStylesMixin: 样式应用
- ThemeConfigEditorMixin: 配置CRUD操作
- ThemeIOHandlerMixin: 导入导出功能
- CONFIG_GROUPS: V1配置组定义

V2 架构说明：
- V2ThemeEditorWidget: V2主Widget类，面向组件的编辑
- V2_CONFIG_GROUPS: V2组件配置组定义
- ComponentEditor: 单个组件编辑器
- EffectsEditor: 效果配置编辑器
- CollapsibleSection: 可折叠区域组件

统一界面：
- UnifiedThemeSettingsWidget: 统一主题设置Widget，支持V1/V2模式切换
"""

from .widget import ThemeSettingsWidget
from .config_groups import CONFIG_GROUPS
from .styles import ThemeStylesMixin
from .config_editor import ThemeConfigEditorMixin
from .io_handler import ThemeIOHandlerMixin

# V2 组件
from .v2_config_groups import (
    V2_CONFIG_GROUPS,
    EFFECTS_CONFIG,
    COMPONENT_CONFIGS,
    TOKEN_CONFIGS,
)
from .v2_editor_widget import (
    V2ThemeEditorWidget,
    CollapsibleSection,
    ComponentEditor,
    EffectsEditor,
)

# 统一界面
from .unified_widget import UnifiedThemeSettingsWidget


__all__ = [
    # V1 导出
    "ThemeSettingsWidget",
    "CONFIG_GROUPS",
    "ThemeStylesMixin",
    "ThemeConfigEditorMixin",
    "ThemeIOHandlerMixin",
    # V2 导出
    "V2ThemeEditorWidget",
    "V2_CONFIG_GROUPS",
    "EFFECTS_CONFIG",
    "COMPONENT_CONFIGS",
    "TOKEN_CONFIGS",
    "CollapsibleSection",
    "ComponentEditor",
    "EffectsEditor",
    # 统一界面
    "UnifiedThemeSettingsWidget",
]
