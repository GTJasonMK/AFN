"""
书香风格的“可增删列表编辑”对话框基类

本模块用于收敛 NovelDetail 里多个列表编辑对话框的重复 UI 骨架：
- 标题 + 工具栏（新增按钮/数量统计）
- 滚动区域（内容容器 + 垂直布局 + 末尾 stretch）
- 底部按钮栏（取消/确定）
- 统一的对话框样式（book_* 调色板 + scrollbar）

子类只需要提供：
- 如何创建单个 item widget（必须包含 delete_btn / get_data / update_index）
- 计数文案与结果过滤规则
- 新增后聚焦的控件
"""

from __future__ import annotations

from typing import Any, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from components.dialogs import BookStyleDialog
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp


class BaseBookListEditDialog(BookStyleDialog):
    """书香风格列表编辑对话框基类（可增删/可滚动）"""

    def __init__(
        self,
        *,
        dialog_title: str,
        items: Optional[List[dict]],
        add_button_text: str,
        min_width_dp: int,
        min_height_dp: int,
        default_width_dp: int,
        default_height_dp: int,
        content_spacing_dp: int = 16,
        parent=None,
    ):
        super().__init__(parent)
        self._dialog_title = dialog_title
        self._raw_items = items or []
        self._add_button_text = add_button_text
        self._min_width_dp = min_width_dp
        self._min_height_dp = min_height_dp
        self._default_width_dp = default_width_dp
        self._default_height_dp = default_height_dp
        self._content_spacing_dp = content_spacing_dp

        self.item_widgets: List[Any] = []

        # UI 组件引用
        self.add_btn: Optional[QPushButton] = None
        self.count_label: Optional[QLabel] = None
        self.scroll: Optional[QScrollArea] = None
        self.content: Optional[QWidget] = None
        self.content_layout: Optional[QVBoxLayout] = None

        self._setup_ui()
        self._apply_theme()

    # ==================== 子类可覆写的契约方法 ====================

    def _create_item_widget(self, item_data: dict, index: int) -> QWidget:
        """创建单个 item widget（子类必须实现）"""
        raise NotImplementedError("子类必须实现 _create_item_widget")

    def _format_count_text(self, count: int) -> str:
        """格式化计数文案（子类可覆写）"""
        return f"共 {count} 项"

    def _should_keep_item_data(self, data: dict) -> bool:
        """结果过滤（子类可覆写）"""
        return bool(data.get("name"))

    def _focus_new_item(self, widget: QWidget) -> None:
        """新增后聚焦（子类可覆写）"""
        return

    # ==================== UI 构建 ====================

    def _setup_ui(self):
        """创建通用 UI 骨架"""
        self.setWindowTitle(self._dialog_title)
        self.setMinimumSize(dp(self._min_width_dp), dp(self._min_height_dp))
        self.resize(dp(self._default_width_dp), dp(self._default_height_dp))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(16))

        # 标题
        title_label = QLabel(self._dialog_title)
        title_label.setObjectName("dialog_title")
        layout.addWidget(title_label)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(dp(12))

        self.add_btn = QPushButton(self._add_button_text)
        self.add_btn.setObjectName("add_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_item)
        toolbar.addWidget(self.add_btn)

        toolbar.addStretch()

        self.count_label = QLabel()
        self.count_label.setObjectName("count_label")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, dp(8), 0)
        self.content_layout.setSpacing(dp(self._content_spacing_dp))

        self._create_items()

        self.content_layout.addStretch()
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, stretch=1)

        # 底部按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(12))
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setFixedHeight(dp(38))
        cancel_btn.setMinimumWidth(dp(80))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确定")
        confirm_btn.setObjectName("confirm_btn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.setFixedHeight(dp(38))
        confirm_btn.setMinimumWidth(dp(80))
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setDefault(True)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

        self._update_count()

    # ==================== 列表操作（通用实现）====================

    def _create_items(self):
        """创建所有 item widgets（基于 _raw_items）"""
        if not self.content_layout:
            return

        # 清理旧组件（支持后续可能的重建）
        for widget in list(self.item_widgets):
            try:
                self.content_layout.removeWidget(widget)
                widget.deleteLater()
            except RuntimeError:
                pass
        self.item_widgets.clear()

        for idx, item in enumerate(self._raw_items):
            widget = self._create_item_widget(item, idx)
            self._bind_delete(widget)
            self.item_widgets.append(widget)
            self.content_layout.addWidget(widget)

    def _bind_delete(self, widget: Any) -> None:
        """绑定删除按钮（约定：widget.delete_btn 存在）"""
        try:
            widget.delete_btn.clicked.connect(lambda checked, w=widget: self._delete_item(w))
        except Exception:
            # 若子类 item widget 不满足约定，尽早暴露问题
            raise

    def _add_item(self):
        """新增一个空 item"""
        if not self.content_layout:
            return

        idx = len(self.item_widgets)
        widget = self._create_item_widget({}, idx)
        self._bind_delete(widget)
        self.item_widgets.append(widget)

        # 在 stretch 之前插入
        self.content_layout.insertWidget(self.content_layout.count() - 1, widget)
        self._update_count()
        self._focus_new_item(widget)

    def _delete_item(self, widget: QWidget):
        """删除一个 item"""
        if not self.content_layout:
            return

        if widget in self.item_widgets:
            self.item_widgets.remove(widget)
            self.content_layout.removeWidget(widget)
            widget.deleteLater()
            self._update_indices()
            self._update_count()

    def _update_indices(self):
        """更新所有 item 的序号（约定：widget.update_index 存在）"""
        for idx, widget in enumerate(self.item_widgets):
            try:
                widget.update_index(idx)
            except Exception:
                raise

    def _update_count(self):
        """更新计数"""
        if self.count_label:
            self.count_label.setText(self._format_count_text(len(self.item_widgets)))

    # ==================== 结果获取 ====================

    def get_items(self) -> List[dict]:
        """获取编辑后的列表结果（带默认过滤规则）"""
        result: List[dict] = []
        for widget in self.item_widgets:
            try:
                data = widget.get_data()
            except Exception:
                raise

            if self._should_keep_item_data(data):
                result.append(data)
        return result

    # ==================== 主题样式 ====================

    def _apply_theme(self):
        """应用书香风格主题（对话框通用样式）"""
        if not self.add_btn or not self.content:
            return

        ui_font = theme_manager.ui_font()
        bg_color = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
            }}
            QLabel#dialog_title {{
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {text_primary};
            }}
            QLabel#count_label {{
                font-family: {ui_font};
                font-size: {sp(13)}px;
                color: {text_secondary};
            }}
            QPushButton#add_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {accent_color};
                background-color: transparent;
                border: 1px dashed {accent_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
            }}
            QPushButton#add_btn:hover {{
                background-color: {bg_secondary};
            }}
            QPushButton#cancel_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_secondary};
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: {dp(6)}px;
            }}
            QPushButton#cancel_btn:hover {{
                color: {accent_color};
                border-color: {accent_color};
            }}
            QPushButton#confirm_btn {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {theme_manager.BUTTON_TEXT};
                background-color: {accent_color};
                border: none;
                border-radius: {dp(6)}px;
            }}
            QPushButton#confirm_btn:hover {{
                background-color: {text_primary};
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {theme_manager.scrollbar()}
        """)

        self.content.setStyleSheet("background: transparent;")

        # 尽量让子组件跟随主题刷新（保持容错，不强制子类都实现）
        for widget in list(self.item_widgets):
            try:
                if hasattr(widget, "_apply_style"):
                    widget._apply_style()
                elif hasattr(widget, "_apply_theme"):
                    widget._apply_theme()
            except RuntimeError:
                pass


__all__ = [
    "BaseBookListEditDialog",
]

