"""
Settings模块 - 系统配置管理

目录结构：
settings/
├── view.py                     # SettingsView 主视图
├── llm_settings_widget.py      # LLM配置管理
├── embedding_settings_widget.py # 嵌入模型配置
├── image_settings_widget.py    # 图片生成配置
├── queue_settings_widget.py    # 队列配置
├── prompt_settings_widget.py   # 提示词管理
├── advanced_settings_widget.py # 高级设置
├── theme_settings_widget.py    # 主题设置入口（兼容层）
├── theme_settings/             # 主题设置子模块
│   ├── widget.py               # V1主题编辑器（经典模式，含透明度配置）
│   ├── config_editor.py        # V1配置编辑器Mixin
│   ├── config_groups.py        # V1配置组定义（含透明度配置组）
│   ├── io_handler.py           # 导入导出Mixin
│   ├── styles.py               # V1样式Mixin
│   ├── v2_config_groups.py     # V2组件配置组定义
│   ├── v2_editor_widget.py     # V2主题编辑器（组件模式）
│   └── unified_widget.py       # 统一主题设置Widget（V1/V2切换）
└── dialogs/                    # 对话框组件
    ├── test_result_dialog.py
    ├── config_dialog.py
    ├── embedding_config_dialog.py
    └── prompt_edit_dialog.py

架构说明：
- V1经典模式：面向常量的主题配置，包含透明度配置
- V2组件模式：面向组件的主题配置
- 透明度配置保存在本地，不同步到后端
"""

from .view import SettingsView

# 对话框（从 dialogs/ 子目录导入，保持向后兼容）
from .dialogs import (
    TestResultDialog,
    LLMConfigDialog,
    EmbeddingConfigDialog,
    PromptEditDialog,
)

__all__ = [
    'SettingsView',
    # Dialogs
    'TestResultDialog',
    'LLMConfigDialog',
    'EmbeddingConfigDialog',
    'PromptEditDialog',
]
