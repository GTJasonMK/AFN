"""
自定义对话框组件 - 主题适配

提供与主题系统完美适配的对话框组件：
- ConfirmDialog: 确认对话框
- AlertDialog: 警告/错误对话框
- InputDialog: 单行文本输入对话框
- TextInputDialog: 多行文本输入对话框
- IntInputDialog: 整数输入对话框
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget,
    QLineEdit, QTextEdit, QSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from themes.theme_manager import theme_manager
from themes.button_styles import ButtonStyles
from utils.dpi_utils import dp, sp
from typing import Tuple, Optional


class BaseDialog(QDialog):
    """对话框基类 - 主题适配"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._theme_connected = False
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题信号"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._on_theme_changed)
            except TypeError:
                pass
            self._theme_connected = False

    def _on_theme_changed(self):
        """主题变更回调"""
        self._apply_theme()

    def _apply_theme(self):
        """应用主题 - 子类实现"""
        pass

    def closeEvent(self, event):
        """关闭时断开信号"""
        self._disconnect_theme_signal()
        super().closeEvent(event)


class ConfirmDialog(BaseDialog):
    """确认对话框 - 主题适配

    使用方式：
        dialog = ConfirmDialog(
            parent=self,
            title="确认删除",
            message="确定要删除这个项目吗？",
            confirm_text="删除",
            cancel_text="取消",
            dialog_type="danger"  # normal, danger, warning
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 用户点击了确认
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "确认",
        message: str = "",
        confirm_text: str = "确认",
        cancel_text: str = "取消",
        dialog_type: str = "normal"  # normal, danger, warning
    ):
        self.title_text = title
        self.message_text = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.dialog_type = dialog_type

        # UI组件引用
        self.container = None
        self.icon_label = None
        self.title_label = None
        self.message_label = None
        self.confirm_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器（用于圆角和阴影）
        self.container = QFrame()
        self.container.setObjectName("dialog_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 图标和标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(12))

        # 图标
        self.icon_label = QLabel(self._get_icon())
        self.icon_label.setObjectName("dialog_icon")
        self.icon_label.setFixedSize(dp(32), dp(32))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("dialog_title")
        header_layout.addWidget(self.title_label, stretch=1)

        container_layout.addLayout(header_layout)

        # 消息内容
        self.message_label = QLabel(self.message_text)
        self.message_label.setObjectName("dialog_message")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        container_layout.addWidget(self.message_label)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        # 取消按钮
        self.cancel_btn = QPushButton(self.cancel_text)
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        # 确认按钮
        self.confirm_btn = QPushButton(self.confirm_text)
        self.confirm_btn.setObjectName("confirm_btn")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setFixedHeight(dp(38))
        self.confirm_btn.setMinimumWidth(dp(80))
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setDefault(True)
        button_layout.addWidget(self.confirm_btn)

        container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(400))

    def _get_icon(self) -> str:
        """获取图标"""
        icons = {
            "normal": "?",
            "danger": "!",
            "warning": "!"
        }
        return icons.get(self.dialog_type, "?")

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 获取类型对应的颜色
        if self.dialog_type == "danger":
            accent_color = theme_manager.ERROR
            accent_bg = theme_manager.ERROR_BG if hasattr(theme_manager, 'ERROR_BG') else theme_manager.PRIMARY_PALE
        elif self.dialog_type == "warning":
            accent_color = theme_manager.WARNING
            accent_bg = theme_manager.WARNING_BG if hasattr(theme_manager, 'WARNING_BG') else theme_manager.PRIMARY_PALE
        else:
            accent_color = theme_manager.PRIMARY
            accent_bg = theme_manager.PRIMARY_PALE

        # 容器样式
        self.container.setStyleSheet(f"""
            #dialog_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 图标样式
        self.icon_label.setStyleSheet(f"""
            #dialog_icon {{
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {accent_color};
                background-color: {accent_bg};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #dialog_title {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 消息样式
        self.message_label.setStyleSheet(f"""
            #dialog_message {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding-left: {dp(44)}px;
                line-height: 1.5;
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            #cancel_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #cancel_btn:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
            #cancel_btn:pressed {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """)

        # 确认按钮样式（根据类型）
        if self.dialog_type == "danger":
            self.confirm_btn.setStyleSheet(f"""
                #confirm_btn {{
                    font-family: {ui_font};
                    background-color: {theme_manager.ERROR};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(8)}px;
                    padding: 0 {dp(20)}px;
                    font-size: {sp(14)}px;
                    font-weight: 600;
                }}
                #confirm_btn:hover {{
                    background-color: {theme_manager.ERROR_DARK};
                }}
                #confirm_btn:pressed {{
                    background-color: {theme_manager.ERROR_DARK};
                }}
            """)
        elif self.dialog_type == "warning":
            self.confirm_btn.setStyleSheet(f"""
                #confirm_btn {{
                    font-family: {ui_font};
                    background-color: {theme_manager.WARNING};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(8)}px;
                    padding: 0 {dp(20)}px;
                    font-size: {sp(14)}px;
                    font-weight: 600;
                }}
                #confirm_btn:hover {{
                    background-color: {theme_manager.WARNING_DARK};
                }}
                #confirm_btn:pressed {{
                    background-color: {theme_manager.WARNING_DARK};
                }}
            """)
        else:
            self.confirm_btn.setStyleSheet(f"""
                #confirm_btn {{
                    font-family: {ui_font};
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(8)}px;
                    padding: 0 {dp(20)}px;
                    font-size: {sp(14)}px;
                    font-weight: 600;
                }}
                #confirm_btn:hover {{
                    background-color: {theme_manager.PRIMARY_LIGHT};
                }}
                #confirm_btn:pressed {{
                    background-color: {theme_manager.PRIMARY_DARK};
                }}
            """)


class AlertDialog(BaseDialog):
    """警告/信息对话框 - 主题适配

    单按钮对话框，用于显示需要用户确认的信息

    使用方式：
        dialog = AlertDialog(
            parent=self,
            title="操作失败",
            message="网络连接失败，请检查网络设置",
            button_text="知道了",
            dialog_type="error"  # info, success, warning, error
        )
        dialog.exec()
    """

    def __init__(
        self,
        parent=None,
        title: str = "提示",
        message: str = "",
        button_text: str = "确定",
        dialog_type: str = "info"  # info, success, warning, error
    ):
        self.title_text = title
        self.message_text = message
        self.button_text = button_text
        self.dialog_type = dialog_type

        # UI组件引用
        self.container = None
        self.icon_label = None
        self.title_label = None
        self.message_label = None
        self.message_scroll = None
        self.ok_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("alert_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 图标和标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(12))

        # 图标
        self.icon_label = QLabel(self._get_icon())
        self.icon_label.setObjectName("alert_icon")
        self.icon_label.setFixedSize(dp(32), dp(32))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icon_label)

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("alert_title")
        header_layout.addWidget(self.title_label, stretch=1)

        container_layout.addLayout(header_layout)

        # 消息内容 - 使用滚动区域防止内容过长
        self.message_scroll = QScrollArea()
        self.message_scroll.setObjectName("alert_message_scroll")
        self.message_scroll.setWidgetResizable(True)
        self.message_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.message_scroll.setMaximumHeight(dp(300))  # 最大高度限制

        message_container = QWidget()
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)

        self.message_label = QLabel(self.message_text)
        self.message_label.setObjectName("alert_message")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        message_layout.addWidget(self.message_label)

        self.message_scroll.setWidget(message_container)
        container_layout.addWidget(self.message_scroll)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.ok_btn = QPushButton(self.button_text)
        self.ok_btn.setObjectName("alert_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(100))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(400))

    def _get_icon(self) -> str:
        """获取图标"""
        icons = {
            "info": "i",
            "success": "*",
            "warning": "!",
            "error": "x"
        }
        return icons.get(self.dialog_type, "i")

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 获取类型对应的颜色
        colors = {
            "info": (theme_manager.INFO, getattr(theme_manager, 'INFO_BG', theme_manager.PRIMARY_PALE)),
            "success": (theme_manager.SUCCESS, getattr(theme_manager, 'SUCCESS_BG', theme_manager.PRIMARY_PALE)),
            "warning": (theme_manager.WARNING, getattr(theme_manager, 'WARNING_BG', theme_manager.PRIMARY_PALE)),
            "error": (theme_manager.ERROR, getattr(theme_manager, 'ERROR_BG', theme_manager.PRIMARY_PALE)),
        }
        accent_color, accent_bg = colors.get(self.dialog_type, colors["info"])

        # 容器样式
        self.container.setStyleSheet(f"""
            #alert_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 图标样式
        self.icon_label.setStyleSheet(f"""
            #alert_icon {{
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {accent_color};
                background-color: {accent_bg};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #alert_title {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 消息样式
        self.message_label.setStyleSheet(f"""
            #alert_message {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                padding-left: {dp(44)}px;
                line-height: 1.5;
            }}
        """)

        # 滚动区域样式
        if hasattr(self, 'message_scroll'):
            self.message_scroll.setStyleSheet(f"""
                QScrollArea#alert_message_scroll {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea#alert_message_scroll > QWidget > QWidget {{
                    background: transparent;
                }}
                {theme_manager.scrollbar()}
            """)

        # 按钮样式
        self.ok_btn.setStyleSheet(f"""
            #alert_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #alert_btn:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #alert_btn:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)


class InputDialog(BaseDialog):
    """单行文本输入对话框 - 主题适配

    替代 QInputDialog.getText()

    使用方式：
        text, ok = InputDialog.getText(
            parent=self,
            title="编辑标题",
            label="请输入新标题：",
            text="默认值"
        )
        if ok and text:
            # 用户输入了内容
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "输入",
        label: str = "",
        text: str = "",
        placeholder: str = ""
    ):
        self.title_text = title
        self.label_text = label
        self.default_text = text
        self.placeholder_text = placeholder

        # UI组件引用
        self.container = None
        self.title_label = None
        self.label_widget = None
        self.input_field = None
        self.ok_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("input_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("input_title")
        container_layout.addWidget(self.title_label)

        # 提示文本
        if self.label_text:
            self.label_widget = QLabel(self.label_text)
            self.label_widget.setObjectName("input_label")
            self.label_widget.setWordWrap(True)
            container_layout.addWidget(self.label_widget)

        # 输入框
        self.input_field = QLineEdit()
        self.input_field.setObjectName("input_field")
        self.input_field.setText(self.default_text)
        if self.placeholder_text:
            self.input_field.setPlaceholderText(self.placeholder_text)
        self.input_field.setFixedHeight(dp(40))
        container_layout.addWidget(self.input_field)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("input_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("input_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(400))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(f"""
            #input_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #input_title {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 提示文本样式
        if self.label_widget:
            self.label_widget.setStyleSheet(f"""
                #input_label {{
                    font-family: {ui_font};
                    font-size: {sp(14)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
            """)

        # 输入框样式
        self.input_field.setStyleSheet(f"""
            #input_field {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(12)}px;
                font-size: {sp(14)}px;
            }}
            #input_field:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            #input_cancel_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #input_cancel_btn:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
            #input_cancel_btn:pressed {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """)

        # 确定按钮样式
        self.ok_btn.setStyleSheet(f"""
            #input_ok_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #input_ok_btn:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #input_ok_btn:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def getText(self) -> str:
        """获取输入的文本"""
        return self.input_field.text()

    @staticmethod
    def getTextStatic(
        parent=None,
        title: str = "输入",
        label: str = "",
        text: str = "",
        placeholder: str = ""
    ) -> Tuple[str, bool]:
        """静态方法：显示对话框并获取输入

        Returns:
            (text, ok): 输入的文本和用户是否确认
        """
        dialog = InputDialog(parent, title, label, text, placeholder)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getText(), True
        return "", False


class TextInputDialog(BaseDialog):
    """多行文本输入对话框 - 主题适配

    替代 QInputDialog.getMultiLineText()

    使用方式：
        text, ok = TextInputDialog.getText(
            parent=self,
            title="输入内容",
            label="请输入详细描述：",
            text="默认内容"
        )
        if ok and text:
            # 用户输入了内容
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "输入",
        label: str = "",
        text: str = "",
        placeholder: str = ""
    ):
        self.title_text = title
        self.label_text = label
        self.default_text = text
        self.placeholder_text = placeholder

        # UI组件引用
        self.container = None
        self.title_label = None
        self.label_widget = None
        self.text_edit = None
        self.ok_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("text_input_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("text_input_title")
        container_layout.addWidget(self.title_label)

        # 提示文本
        if self.label_text:
            self.label_widget = QLabel(self.label_text)
            self.label_widget.setObjectName("text_input_label")
            self.label_widget.setWordWrap(True)
            container_layout.addWidget(self.label_widget)

        # 多行输入框
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("text_input_field")
        self.text_edit.setPlainText(self.default_text)
        if self.placeholder_text:
            self.text_edit.setPlaceholderText(self.placeholder_text)
        self.text_edit.setMinimumHeight(dp(120))
        self.text_edit.setMaximumHeight(dp(200))
        container_layout.addWidget(self.text_edit)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("text_input_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("text_input_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(480))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(f"""
            #text_input_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #text_input_title {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 提示文本样式
        if self.label_widget:
            self.label_widget.setStyleSheet(f"""
                #text_input_label {{
                    font-family: {ui_font};
                    font-size: {sp(14)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
            """)

        # 多行输入框样式
        self.text_edit.setStyleSheet(f"""
            #text_input_field {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(10)}px;
                font-size: {sp(14)}px;
            }}
            #text_input_field:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            #text_input_cancel_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #text_input_cancel_btn:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
            #text_input_cancel_btn:pressed {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """)

        # 确定按钮样式
        self.ok_btn.setStyleSheet(f"""
            #text_input_ok_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #text_input_ok_btn:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #text_input_ok_btn:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def getText(self) -> str:
        """获取输入的文本"""
        return self.text_edit.toPlainText()

    @staticmethod
    def getTextStatic(
        parent=None,
        title: str = "输入",
        label: str = "",
        text: str = "",
        placeholder: str = ""
    ) -> Tuple[str, bool]:
        """静态方法：显示对话框并获取输入

        Returns:
            (text, ok): 输入的文本和用户是否确认
        """
        dialog = TextInputDialog(parent, title, label, text, placeholder)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getText(), True
        return "", False


class IntInputDialog(BaseDialog):
    """整数输入对话框 - 主题适配

    替代 QInputDialog.getInt()

    使用方式：
        value, ok = IntInputDialog.getInt(
            parent=self,
            title="设置数量",
            label="请输入章节数量：",
            value=10,
            min_value=1,
            max_value=100
        )
        if ok:
            # 用户输入了数值
            pass
    """

    def __init__(
        self,
        parent=None,
        title: str = "输入",
        label: str = "",
        value: int = 0,
        min_value: int = 0,
        max_value: int = 100,
        step: int = 1
    ):
        self.title_text = title
        self.label_text = label
        self.default_value = value
        self.min_value = min_value
        self.max_value = max_value
        self.step = step

        # UI组件引用
        self.container = None
        self.title_label = None
        self.label_widget = None
        self.spin_box = None
        self.ok_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("int_input_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("int_input_title")
        container_layout.addWidget(self.title_label)

        # 提示文本
        if self.label_text:
            self.label_widget = QLabel(self.label_text)
            self.label_widget.setObjectName("int_input_label")
            self.label_widget.setWordWrap(True)
            container_layout.addWidget(self.label_widget)

        # 数字输入框
        self.spin_box = QSpinBox()
        self.spin_box.setObjectName("int_input_field")
        self.spin_box.setRange(self.min_value, self.max_value)
        self.spin_box.setValue(self.default_value)
        self.spin_box.setSingleStep(self.step)
        self.spin_box.setFixedHeight(dp(40))
        container_layout.addWidget(self.spin_box)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("int_input_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.setObjectName("int_input_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(80))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(360))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(f"""
            #int_input_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #int_input_title {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 提示文本样式
        if self.label_widget:
            self.label_widget.setStyleSheet(f"""
                #int_input_label {{
                    font-family: {ui_font};
                    font-size: {sp(14)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
            """)

        # 数字输入框样式
        self.spin_box.setStyleSheet(f"""
            #int_input_field {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(12)}px;
                font-size: {sp(14)}px;
            }}
            #int_input_field:focus {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
            }}
            #int_input_field::up-button, #int_input_field::down-button {{
                width: {dp(24)}px;
                border: none;
                background-color: {theme_manager.BG_TERTIARY};
            }}
            #int_input_field::up-button:hover, #int_input_field::down-button:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
            #int_input_field::up-arrow {{
                image: none;
                border-left: {dp(5)}px solid transparent;
                border-right: {dp(5)}px solid transparent;
                border-bottom: {dp(6)}px solid {theme_manager.TEXT_SECONDARY};
            }}
            #int_input_field::down-arrow {{
                image: none;
                border-left: {dp(5)}px solid transparent;
                border-right: {dp(5)}px solid transparent;
                border-top: {dp(6)}px solid {theme_manager.TEXT_SECONDARY};
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            #int_input_cancel_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #int_input_cancel_btn:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
            #int_input_cancel_btn:pressed {{
                background-color: {theme_manager.BORDER_LIGHT};
            }}
        """)

        # 确定按钮样式
        self.ok_btn.setStyleSheet(f"""
            #int_input_ok_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #int_input_ok_btn:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            #int_input_ok_btn:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
            }}
        """)

    def getValue(self) -> int:
        """获取输入的数值"""
        return self.spin_box.value()

    @staticmethod
    def getIntStatic(
        parent=None,
        title: str = "输入",
        label: str = "",
        value: int = 0,
        min_value: int = 0,
        max_value: int = 100,
        step: int = 1
    ) -> Tuple[int, bool]:
        """静态方法：显示对话框并获取输入

        Returns:
            (value, ok): 输入的数值和用户是否确认
        """
        dialog = IntInputDialog(parent, title, label, value, min_value, max_value, step)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getValue(), True
        return 0, False


class LoadingDialog(BaseDialog):
    """加载中对话框 - 主题适配

    替代 QProgressDialog，提供与主题系统完美适配的加载动画

    使用方式：
        # 方式1：手动控制
        dialog = LoadingDialog(
            parent=self,
            message="正在处理...",
            cancelable=True
        )
        dialog.show()
        # ... 异步操作
        dialog.close()

        # 方式2：配合异步Worker
        dialog = LoadingDialog(parent=self, message="正在生成...")
        worker.finished.connect(dialog.close)
        worker.start()
        dialog.exec()  # 阻塞直到close被调用
    """

    def __init__(
        self,
        parent=None,
        message: str = "加载中...",
        title: str = "请稍候",
        cancelable: bool = False
    ):
        self.message_text = message
        self.title_text = title
        self.cancelable = cancelable
        self._cancelled = False

        # UI组件引用
        self.container = None
        self.title_label = None
        self.message_label = None
        self.spinner = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """创建UI"""
        from components.loading_spinner import CircularSpinner

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("loading_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(32), dp(28), dp(32), dp(28))
        container_layout.setSpacing(dp(20))
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.title_label = QLabel(self.title_text)
        self.title_label.setObjectName("loading_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.title_label)

        # 加载动画
        spinner_container = QHBoxLayout()
        spinner_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner = CircularSpinner(size=dp(48))
        spinner_container.addWidget(self.spinner)
        container_layout.addLayout(spinner_container)

        # 消息文本
        self.message_label = QLabel(self.message_text)
        self.message_label.setObjectName("loading_message")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setWordWrap(True)
        container_layout.addWidget(self.message_label)

        # 取消按钮（可选）
        if self.cancelable:
            button_layout = QHBoxLayout()
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            self.cancel_btn = QPushButton("取消")
            self.cancel_btn.setObjectName("loading_cancel_btn")
            self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.cancel_btn.setFixedHeight(dp(36))
            self.cancel_btn.setMinimumWidth(dp(100))
            self.cancel_btn.clicked.connect(self._on_cancel)
            button_layout.addWidget(self.cancel_btn)

            container_layout.addLayout(button_layout)

        layout.addWidget(self.container)

        # 设置对话框大小
        self.setFixedWidth(dp(320))

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(f"""
            #loading_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #loading_title {{
                font-family: {ui_font};
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 消息样式
        self.message_label.setStyleSheet(f"""
            #loading_message {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.5;
            }}
        """)

        # 取消按钮样式
        if self.cancel_btn:
            self.cancel_btn.setStyleSheet(f"""
                #loading_cancel_btn {{
                    font-family: {ui_font};
                    background-color: {theme_manager.BG_SECONDARY};
                    color: {theme_manager.TEXT_PRIMARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {dp(8)}px;
                    padding: 0 {dp(20)}px;
                    font-size: {sp(14)}px;
                    font-weight: 500;
                }}
                #loading_cancel_btn:hover {{
                    background-color: {theme_manager.BG_TERTIARY};
                    border-color: {theme_manager.BORDER_DARK};
                }}
                #loading_cancel_btn:pressed {{
                    background-color: {theme_manager.BORDER_LIGHT};
                }}
            """)

    def setMessage(self, message: str):
        """更新消息文本"""
        self.message_text = message
        if self.message_label:
            self.message_label.setText(message)

    def setTitle(self, title: str):
        """更新标题"""
        self.title_text = title
        if self.title_label:
            self.title_label.setText(title)

    def _on_cancel(self):
        """取消按钮点击"""
        self._cancelled = True
        self.reject()

    def wasCancelled(self) -> bool:
        """是否被取消"""
        return self._cancelled

    def show(self):
        """显示对话框"""
        super().show()
        if self.spinner:
            self.spinner.start()

    def close(self):
        """关闭对话框"""
        if self.spinner:
            self.spinner.stop()
        super().close()

    def accept(self):
        """接受并关闭"""
        if self.spinner:
            self.spinner.stop()
        super().accept()

    def reject(self):
        """拒绝并关闭"""
        if self.spinner:
            self.spinner.stop()
        super().reject()


class PartOutlineConfigDialog(BaseDialog):
    """部分大纲配置对话框 - 主题适配

    支持配置：
    1. 生成章节范围：可以选择只生成前N章的部分大纲（增量生成）
    2. 分部方式：按部分数量或按每部分章节数

    使用方式：
        result = PartOutlineConfigDialog.getConfigStatic(
            parent=self,
            total_chapters=200
        )
        if result:
            generate_chapters, chapters_per_part = result
            # generate_chapters: 生成多少章的大纲（如100表示生成前100章）
            # chapters_per_part: 每部分章节数
    """

    def __init__(
        self,
        parent=None,
        total_chapters: int = 100
    ):
        self.total_chapters = total_chapters

        # UI组件引用
        self.container = None
        self.title_label = None
        self.info_label = None
        self.range_spin = None
        self.range_hint_label = None
        self.mode_by_parts = None
        self.mode_by_chapters = None
        self.parts_spin = None
        self.chapters_spin = None
        self.preview_label = None
        self.ok_btn = None
        self.cancel_btn = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()
        self._update_preview()

    def _setup_ui(self):
        """创建UI"""
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        import math

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("part_config_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题
        self.title_label = QLabel("生成部分大纲")
        self.title_label.setObjectName("part_config_title")
        container_layout.addWidget(self.title_label)

        # 信息提示
        self.info_label = QLabel(f"小说总计 {self.total_chapters} 章")
        self.info_label.setObjectName("part_config_info")
        container_layout.addWidget(self.info_label)

        # === 章节范围选择 ===
        range_container = QWidget()
        range_layout = QHBoxLayout(range_container)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(dp(12))

        range_label = QLabel("生成范围：前")
        range_label.setObjectName("part_config_label")
        range_layout.addWidget(range_label)

        self.range_spin = QSpinBox()
        self.range_spin.setObjectName("part_config_spin")
        # 最小20章（至少能分2个部分，每部分10章），最大=总章节数
        min_chapters = min(20, self.total_chapters)
        self.range_spin.setRange(min_chapters, self.total_chapters)
        self.range_spin.setValue(self.total_chapters)  # 默认生成全部
        self.range_spin.setSingleStep(10)  # 步进10章
        self.range_spin.setFixedHeight(dp(36))
        self.range_spin.setFixedWidth(dp(100))
        self.range_spin.valueChanged.connect(self._on_range_changed)
        range_layout.addWidget(self.range_spin)

        range_suffix = QLabel("章")
        range_suffix.setObjectName("part_config_suffix")
        range_layout.addWidget(range_suffix)

        range_layout.addStretch()

        # 快捷按钮
        self.half_btn = QPushButton("一半")
        self.half_btn.setObjectName("quick_btn")
        self.half_btn.setFixedSize(dp(50), dp(32))
        self.half_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.half_btn.clicked.connect(lambda: self.range_spin.setValue(self.total_chapters // 2))
        range_layout.addWidget(self.half_btn)

        self.all_btn = QPushButton("全部")
        self.all_btn.setObjectName("quick_btn")
        self.all_btn.setFixedSize(dp(50), dp(32))
        self.all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.all_btn.clicked.connect(lambda: self.range_spin.setValue(self.total_chapters))
        range_layout.addWidget(self.all_btn)

        container_layout.addWidget(range_container)

        # 范围提示
        self.range_hint_label = QLabel("")
        self.range_hint_label.setObjectName("part_config_hint")
        container_layout.addWidget(self.range_hint_label)

        # 分隔线
        separator = QFrame()
        separator.setObjectName("config_separator")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)

        # === 分部方式选择 ===
        method_label = QLabel("分部方式：")
        method_label.setObjectName("part_config_label")
        container_layout.addWidget(method_label)

        # 单选按钮组
        self.button_group = QButtonGroup(self)

        # 模式1：按部分数量
        mode1_container = QWidget()
        mode1_layout = QHBoxLayout(mode1_container)
        mode1_layout.setContentsMargins(dp(20), 0, 0, 0)
        mode1_layout.setSpacing(dp(12))

        self.mode_by_parts = QRadioButton("按部分数量")
        self.mode_by_parts.setObjectName("mode_radio")
        self.mode_by_parts.setChecked(True)
        self.button_group.addButton(self.mode_by_parts, 1)
        mode1_layout.addWidget(self.mode_by_parts)

        self.parts_spin = QSpinBox()
        self.parts_spin.setObjectName("part_config_spin")
        self.parts_spin.setFixedHeight(dp(36))
        self.parts_spin.setFixedWidth(dp(80))
        self.parts_spin.valueChanged.connect(self._on_parts_changed)
        mode1_layout.addWidget(self.parts_spin)

        parts_suffix = QLabel("个部分")
        parts_suffix.setObjectName("part_config_suffix")
        mode1_layout.addWidget(parts_suffix)
        mode1_layout.addStretch()

        container_layout.addWidget(mode1_container)

        # 模式2：按每部分章节数
        mode2_container = QWidget()
        mode2_layout = QHBoxLayout(mode2_container)
        mode2_layout.setContentsMargins(dp(20), 0, 0, 0)
        mode2_layout.setSpacing(dp(12))

        self.mode_by_chapters = QRadioButton("按每部分章节数")
        self.mode_by_chapters.setObjectName("mode_radio")
        self.button_group.addButton(self.mode_by_chapters, 2)
        mode2_layout.addWidget(self.mode_by_chapters)

        self.chapters_spin = QSpinBox()
        self.chapters_spin.setObjectName("part_config_spin")
        self.chapters_spin.setRange(10, 100)
        self.chapters_spin.setValue(25)
        self.chapters_spin.setFixedHeight(dp(36))
        self.chapters_spin.setFixedWidth(dp(80))
        self.chapters_spin.valueChanged.connect(self._on_chapters_changed)
        self.chapters_spin.setEnabled(False)
        mode2_layout.addWidget(self.chapters_spin)

        chapters_suffix = QLabel("章/部分")
        chapters_suffix.setObjectName("part_config_suffix")
        mode2_layout.addWidget(chapters_suffix)
        mode2_layout.addStretch()

        container_layout.addWidget(mode2_container)

        # 连接单选按钮切换
        self.mode_by_parts.toggled.connect(self._on_mode_changed)
        self.mode_by_chapters.toggled.connect(self._on_mode_changed)

        # 预览区域
        preview_container = QFrame()
        preview_container.setObjectName("preview_container")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))

        self.preview_label = QLabel()
        self.preview_label.setObjectName("part_config_preview")
        self.preview_label.setWordWrap(True)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.preview_label)

        container_layout.addWidget(preview_container)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))
        button_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("part_config_cancel_btn")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setFixedHeight(dp(38))
        self.cancel_btn.setMinimumWidth(dp(80))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("开始生成")
        self.ok_btn.setObjectName("part_config_ok_btn")
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setFixedHeight(dp(38))
        self.ok_btn.setMinimumWidth(dp(100))
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        container_layout.addLayout(button_layout)
        layout.addWidget(self.container)

        self.setFixedWidth(dp(450))

        # 初始化部分数量范围
        self._update_parts_range()

    def _update_parts_range(self):
        """根据当前章节范围更新部分数量的范围"""
        import math
        generate_chapters = self.range_spin.value()

        # 计算合理的部分数量范围
        default_parts = max(2, math.ceil(generate_chapters / 25))
        max_parts = max(2, math.ceil(generate_chapters / 10))
        min_parts = 2

        self.parts_spin.setRange(min_parts, min(max_parts, 20))
        self.parts_spin.setValue(min(default_parts, min(max_parts, 20)))

    def _on_range_changed(self):
        """章节范围改变"""
        self._update_parts_range()
        self._update_preview()

    def _on_mode_changed(self):
        """模式切换"""
        is_parts_mode = self.mode_by_parts.isChecked()
        self.parts_spin.setEnabled(is_parts_mode)
        self.chapters_spin.setEnabled(not is_parts_mode)
        self._update_preview()

    def _on_parts_changed(self):
        """部分数量改变"""
        if self.mode_by_parts.isChecked():
            self._update_preview()

    def _on_chapters_changed(self):
        """每部分章节数改变"""
        if self.mode_by_chapters.isChecked():
            self._update_preview()

    def _update_preview(self):
        """更新预览信息"""
        import math

        generate_chapters = self.range_spin.value()

        # 更新范围提示
        if generate_chapters < self.total_chapters:
            remaining = self.total_chapters - generate_chapters
            self.range_hint_label.setText(f"将生成第1-{generate_chapters}章的部分大纲，剩余{remaining}章可稍后生成")
            self.range_hint_label.setVisible(True)
        else:
            self.range_hint_label.setText("将生成全部章节的部分大纲")
            self.range_hint_label.setVisible(True)

        # 计算部分分配
        if self.mode_by_parts.isChecked():
            parts_count = self.parts_spin.value()
            chapters_per_part = math.ceil(generate_chapters / parts_count)
            last_part_chapters = generate_chapters - (parts_count - 1) * chapters_per_part
            if last_part_chapters <= 0:
                chapters_per_part = math.floor(generate_chapters / parts_count)
                last_part_chapters = generate_chapters - (parts_count - 1) * chapters_per_part
        else:
            chapters_per_part = self.chapters_spin.value()
            parts_count = math.ceil(generate_chapters / chapters_per_part)
            last_part_chapters = generate_chapters % chapters_per_part
            if last_part_chapters == 0:
                last_part_chapters = chapters_per_part

        # 生成预览文本
        if last_part_chapters == chapters_per_part or parts_count == 1:
            preview_text = f"将生成 {parts_count} 个部分，每部分约 {chapters_per_part} 章"
        else:
            preview_text = f"将生成 {parts_count} 个部分\n前 {parts_count-1} 部分各 {chapters_per_part} 章，最后一部分 {last_part_chapters} 章"

        self.preview_label.setText(preview_text)

    def _apply_theme(self):
        """应用主题样式"""
        ui_font = theme_manager.ui_font()

        # 容器样式
        self.container.setStyleSheet(f"""
            #part_config_container {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(16)}px;
            }}
        """)

        # 标题样式
        self.title_label.setStyleSheet(f"""
            #part_config_title {{
                font-family: {ui_font};
                font-size: {sp(17)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)

        # 信息提示样式
        self.info_label.setStyleSheet(f"""
            #part_config_info {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
        """)

        # 标签样式
        label_style = f"""
            QLabel#part_config_label {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                font-weight: 500;
            }}
        """
        for widget in self.container.findChildren(QLabel):
            if widget.objectName() == "part_config_label":
                widget.setStyleSheet(label_style)

        # 范围提示样式
        self.range_hint_label.setStyleSheet(f"""
            #part_config_hint {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_TERTIARY};
                padding-left: {dp(4)}px;
            }}
        """)

        # 分隔线样式
        separator = self.container.findChild(QFrame, "config_separator")
        if separator:
            separator.setStyleSheet(f"""
                #config_separator {{
                    background-color: {theme_manager.BORDER_LIGHT};
                }}
            """)

        # 单选按钮样式
        radio_style = f"""
            QRadioButton {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_PRIMARY};
                spacing: {dp(8)}px;
            }}
            QRadioButton::indicator {{
                width: {dp(18)}px;
                height: {dp(18)}px;
                border: 2px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(9)}px;
                background-color: {theme_manager.BG_SECONDARY};
            }}
            QRadioButton::indicator:checked {{
                border-color: {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY};
            }}
        """
        self.mode_by_parts.setStyleSheet(radio_style)
        self.mode_by_chapters.setStyleSheet(radio_style)

        # 数字输入框样式
        spin_style = f"""
            QSpinBox {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(6)}px;
                padding: 0 {dp(8)}px;
                font-size: {sp(14)}px;
            }}
            QSpinBox:focus {{
                border-color: {theme_manager.PRIMARY};
            }}
            QSpinBox:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_TERTIARY};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(20)}px;
                border: none;
                background-color: {theme_manager.BG_TERTIARY};
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
            }}
        """
        self.range_spin.setStyleSheet(spin_style)
        self.parts_spin.setStyleSheet(spin_style)
        self.chapters_spin.setStyleSheet(spin_style)

        # 后缀标签样式
        suffix_style = f"""
            QLabel#part_config_suffix {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
        """
        for widget in self.container.findChildren(QLabel):
            if widget.objectName() == "part_config_suffix":
                widget.setStyleSheet(suffix_style)

        # 快捷按钮样式
        quick_btn_style = f"""
            QPushButton#quick_btn {{
                font-family: {ui_font};
                font-size: {sp(12)}px;
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
            }}
            QPushButton#quick_btn:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                color: {theme_manager.PRIMARY};
                border-color: {theme_manager.PRIMARY};
            }}
        """
        self.half_btn.setStyleSheet(quick_btn_style)
        self.all_btn.setStyleSheet(quick_btn_style)

        # 预览区域样式
        preview_container = self.container.findChild(QFrame, "preview_container")
        if preview_container:
            preview_container.setStyleSheet(f"""
                #preview_container {{
                    background-color: {theme_manager.PRIMARY_PALE};
                    border: 1px solid {theme_manager.PRIMARY};
                    border-radius: {dp(8)}px;
                }}
            """)

        self.preview_label.setStyleSheet(f"""
            #part_config_preview {{
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {theme_manager.PRIMARY};
                font-weight: 500;
            }}
        """)

        # 取消按钮样式
        self.cancel_btn.setStyleSheet(f"""
            #part_config_cancel_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 500;
            }}
            #part_config_cancel_btn:hover {{
                background-color: {theme_manager.BG_TERTIARY};
                border-color: {theme_manager.BORDER_DARK};
            }}
        """)

        # 确定按钮样式
        self.ok_btn.setStyleSheet(f"""
            #part_config_ok_btn {{
                font-family: {ui_font};
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {dp(8)}px;
                padding: 0 {dp(20)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            #part_config_ok_btn:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
        """)

    def getConfig(self) -> Tuple[int, int]:
        """获取配置结果

        Returns:
            (generate_chapters, chapters_per_part): 生成章节数和每部分章节数
        """
        import math

        generate_chapters = self.range_spin.value()

        if self.mode_by_parts.isChecked():
            parts_count = self.parts_spin.value()
            chapters_per_part = math.ceil(generate_chapters / parts_count)
        else:
            chapters_per_part = self.chapters_spin.value()

        return generate_chapters, chapters_per_part

    @staticmethod
    def getConfigStatic(
        parent=None,
        total_chapters: int = 100
    ) -> Optional[Tuple[int, int]]:
        """静态方法：显示对话框并获取配置

        Returns:
            (generate_chapters, chapters_per_part) 或 None（用户取消）
        """
        dialog = PartOutlineConfigDialog(parent, total_chapters)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getConfig()
        return None