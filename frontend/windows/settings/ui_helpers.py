"""
设置页通用 UI Helper

目标：减少多个设置页重复的按钮栏与按钮样式代码，避免后续调整多处同步。
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Optional, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QPushButton

from themes.theme_manager import theme_manager
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


def build_settings_group_box_style(palette) -> str:
    """构建“书香风格”GroupBox 样式（Advanced/Temperature/MaxTokens 等复用）"""
    return (
        f"QGroupBox {{ font-family: {palette.serif_font}; font-size: {sp(16)}px; font-weight: 700; "
        f"color: {palette.text_primary}; background-color: {palette.bg_secondary}; "
        f"border: 1px solid {palette.border_color}; border-radius: {dp(8)}px; "
        f"margin-top: {dp(24)}px; padding-top: {dp(24)}px; }} "
        f"QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; "
        f"left: {dp(16)}px; top: {dp(8)}px; padding: 0 {dp(8)}px; "
        f"background-color: {palette.bg_secondary}; color: {palette.accent_color}; }}"
    )


def build_settings_label_style(palette) -> str:
    """构建设置页“标题 Label”样式（用于 FormLayout 左侧字段名）"""
    return (
        f"QLabel {{ font-family: {palette.ui_font}; font-size: {sp(14)}px; font-weight: 600; "
        f"color: {palette.text_primary}; background: transparent; }}"
    )


def build_settings_help_label_style(palette) -> str:
    """构建设置页“帮助文字”样式（右侧说明）"""
    return (
        f"QLabel {{ font-family: {palette.ui_font}; font-size: {sp(13)}px; color: {palette.text_tertiary}; "
        f"background: transparent; font-style: italic; }}"
    )


def build_settings_spinbox_style(palette, *, widget_type: str) -> str:
    """构建设置页 SpinBox 样式

    widget_type:
    - QSpinBox
    - QDoubleSpinBox
    """
    return (
        f"{widget_type} {{ font-family: {palette.ui_font}; padding: {dp(8)}px {dp(12)}px; "
        f"border: 1px solid {palette.border_color}; border-radius: {dp(6)}px; "
        f"background-color: {palette.bg_primary}; color: {palette.text_primary}; "
        f"font-size: {sp(14)}px; font-weight: 500; }} "
        f"{widget_type}:focus {{ border: 1px solid {palette.accent_color}; background-color: {palette.bg_secondary}; }} "
        f"{widget_type}::up-button, {widget_type}::down-button {{ width: {dp(24)}px; background-color: transparent; "
        f"border: none; border-radius: {dp(4)}px; }} "
        f"{widget_type}::up-button:hover, {widget_type}::down-button:hover {{ background-color: {palette.border_color}; }}"
    )


def build_settings_scroll_area_style(palette) -> str:
    """构建设置页滚动区域/滚动条样式"""
    return (
        "QScrollArea { background-color: transparent; border: none; } "
        "QScrollArea > QWidget > QWidget { background-color: transparent; } "
        f"QScrollBar:vertical {{ background-color: {palette.bg_secondary}; width: {dp(8)}px; border-radius: {dp(4)}px; }} "
        f"QScrollBar::handle:vertical {{ background-color: {palette.border_color}; border-radius: {dp(4)}px; "
        f"min-height: {dp(32)}px; }} "
        f"QScrollBar::handle:vertical:hover {{ background-color: {palette.text_tertiary}; }} "
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
    )


def force_refresh_widget_style(widget) -> None:
    """强制刷新样式缓存（部分 Qt 样式会缓存旧的 StyleSheet）"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def apply_settings_import_export_reset_save_styles(
    widget,
    palette,
    *,
    save_btn: QPushButton,
    secondary_btns: Iterable[QPushButton],
    scroll_area=None,
    force_refresh: bool = True,
) -> None:
    """统一应用设置页底部按钮样式 +（可选）滚动区域样式 +（可选）强制刷新"""
    secondary_btn_style = build_settings_secondary_button_style(palette)
    for btn in secondary_btns:
        btn.setStyleSheet(secondary_btn_style)

    save_btn.setStyleSheet(build_settings_primary_button_style(palette))

    if scroll_area is not None:
        scroll_area.setStyleSheet(build_settings_scroll_area_style(palette))

    if force_refresh:
        force_refresh_widget_style(widget)


def build_config_list_primary_button_style(palette, *, with_pressed: bool) -> str:
    """构建“配置列表页”的主要按钮样式（新增配置）"""
    pressed = (
        f"""
        QPushButton#primary_btn:pressed {{
            background-color: {palette.accent_light};
        }}
        """
        if with_pressed
        else ""
    )
    return f"""
        QPushButton#primary_btn {{
            font-family: {palette.ui_font};
            background-color: {palette.accent_color};
            color: {palette.bg_primary};
            border: none;
            border-radius: {dp(6)}px;
            padding: {dp(8)}px {dp(24)}px;
            font-size: {sp(13)}px;
            font-weight: 600;
        }}
        QPushButton#primary_btn:hover {{
            background-color: {palette.text_primary};
        }}
        {pressed}
    """


def build_config_list_secondary_button_style(palette, *, variant: str) -> str:
    """构建“配置列表页”的次要按钮样式（导入/导出/测试/激活/编辑）

    variant:
    - full：Embedding/LLM 使用（含 hover 背景色与 disabled 边框色）
    - simple：Image 使用（保持其更简化的 hover/disabled 规则）
    """
    if variant == "simple":
        return f"""
            QPushButton#secondary_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton#secondary_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
            }}
            QPushButton#secondary_btn:disabled {{
                color: {palette.border_color};
            }}
        """

    return f"""
        QPushButton#secondary_btn {{
            font-family: {palette.ui_font};
            background-color: transparent;
            color: {palette.text_secondary};
            border: 1px solid {palette.border_color};
            border-radius: {dp(6)}px;
            padding: {dp(8)}px {dp(16)}px;
            font-size: {sp(13)}px;
            font-weight: 500;
        }}
        QPushButton#secondary_btn:hover {{
            color: {palette.accent_color};
            border-color: {palette.accent_color};
            background-color: {palette.bg_primary};
        }}
        QPushButton#secondary_btn:disabled {{
            color: {palette.border_color};
            border-color: {palette.border_color};
        }}
    """


def build_config_list_danger_button_style(palette, *, variant: str) -> str:
    """构建“配置列表页”的危险按钮样式（删除）

    variant:
    - full：Embedding/LLM 使用（含 hover 边框色与 disabled 边框色）
    - simple：Image 使用（保持其更简化的 hover/disabled 规则）
    """
    if variant == "simple":
        return f"""
            QPushButton#danger_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {theme_manager.ERROR};
                border: 1px solid {theme_manager.ERROR_LIGHT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton#danger_btn:hover {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
            }}
            QPushButton#danger_btn:disabled {{
                color: {palette.border_color};
            }}
        """

    return f"""
        QPushButton#danger_btn {{
            font-family: {palette.ui_font};
            background-color: transparent;
            color: {theme_manager.ERROR};
            border: 1px solid {theme_manager.ERROR_LIGHT};
            border-radius: {dp(6)}px;
            padding: {dp(8)}px {dp(16)}px;
            font-size: {sp(13)}px;
            font-weight: 500;
        }}
        QPushButton#danger_btn:hover {{
            background-color: {theme_manager.ERROR};
            color: {theme_manager.BUTTON_TEXT};
            border-color: {theme_manager.ERROR};
        }}
        QPushButton#danger_btn:disabled {{
            color: {palette.border_color};
            border-color: {palette.border_color};
        }}
    """


def build_config_list_widget_style(palette) -> str:
    """构建“配置列表页”的 QListWidget 样式（Embedding/LLM 共用）"""
    return f"""
        QListWidget#config_list {{
            font-family: {palette.ui_font};
            background-color: {palette.bg_primary};
            border: 1px solid {palette.border_color};
            border-radius: {dp(8)}px;
            padding: {dp(8)}px;
            outline: none;
        }}
        QListWidget#config_list::item {{
            background-color: transparent;
            border: none;
            border-left: 3px solid transparent;
            border-radius: 0;
            padding: {dp(16)}px {dp(12)}px;
            margin: 0;
            color: {palette.text_primary};
            border-bottom: 1px solid {palette.border_color};
        }}
        QListWidget#config_list::item:last-child {{
            border-bottom: none;
        }}
        QListWidget#config_list::item:hover {{
            background-color: {palette.bg_secondary};
            border-left: 3px solid {palette.accent_light};
        }}
        QListWidget#config_list::item:selected {{
            background-color: {palette.bg_secondary};
            border-left: 3px solid {palette.accent_color};
            color: {palette.text_primary};
        }}
        QScrollBar:vertical {{
            background-color: transparent;
            width: {dp(6)}px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background-color: {palette.border_color};
            border-radius: {dp(3)}px;
            min-height: {dp(30)}px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {palette.text_secondary};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
    """
