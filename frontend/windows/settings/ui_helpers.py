"""
设置页通用 UI Helper

目标：减少多个设置页重复的按钮栏与按钮样式代码，避免后续调整多处同步。
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton

from utils.dpi_utils import dp, sp


def build_import_export_reset_save_bar(
    *,
    on_import: Callable[[], None],
    on_export: Callable[[], None],
    on_reset: Callable[[], None],
    on_save: Callable[[], None],
    import_text: str = "导入配置",
    export_text: str = "导出配置",
    reset_text: str = "恢复默认值",
    save_text: str = "保存配置",
    spacing: Optional[int] = None,
) -> Tuple[QHBoxLayout, Dict[str, QPushButton]]:
    """构建设置页底部按钮栏（导入/导出/重置/保存）

    注意：QPushButton.clicked 信号携带 bool 参数，仍使用 lambda 包装，规避回调签名不匹配。
    """

    def _make_btn(text: str, callback: Callable[[], None]) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _checked=False: callback())
        return btn

    bar = QHBoxLayout()
    bar.setSpacing(spacing if spacing is not None else dp(12))

    import_btn = _make_btn(import_text, on_import)
    bar.addWidget(import_btn)

    export_btn = _make_btn(export_text, on_export)
    bar.addWidget(export_btn)

    bar.addStretch()

    reset_btn = _make_btn(reset_text, on_reset)
    bar.addWidget(reset_btn)

    save_btn = _make_btn(save_text, on_save)
    bar.addWidget(save_btn)

    return (
        bar,
        {
            "import_btn": import_btn,
            "export_btn": export_btn,
            "reset_btn": reset_btn,
            "save_btn": save_btn,
        },
    )


def build_settings_secondary_button_style(palette) -> str:
    """构建设置页“次要按钮”样式（用于导入/导出/重置）"""
    return f"""
        QPushButton {{
            font-family: {palette.ui_font};
            background-color: transparent;
            color: {palette.text_secondary};
            border: 1px solid {palette.border_color};
            border-radius: {dp(6)}px;
            padding: {dp(8)}px {dp(24)}px;
            font-size: {sp(14)}px;
        }}
        QPushButton:hover {{
            color: {palette.accent_color};
            border-color: {palette.accent_color};
            background-color: {palette.bg_primary};
        }}
    """


def build_settings_primary_button_style(palette) -> str:
    """构建设置页“主要按钮”样式（用于保存）"""
    return f"""
        QPushButton {{
            font-family: {palette.ui_font};
            background-color: {palette.accent_color};
            color: {palette.bg_primary};
            border: none;
            border-radius: {dp(6)}px;
            padding: {dp(8)}px {dp(24)}px;
            font-size: {sp(14)}px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {palette.text_primary};
        }}
        QPushButton:pressed {{
            background-color: {palette.accent_light};
        }}
    """

