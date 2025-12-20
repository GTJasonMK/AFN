"""
工具栏模块

提供漫画提示词生成的工具栏UI和状态管理。
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QFrame, QPushButton, QComboBox, QStackedWidget, QWidget
)
from PyQt6.QtCore import Qt

from themes.button_styles import ButtonStyles
from components.loading_spinner import CircularSpinner
from utils.dpi_utils import dp, sp


class ToolbarMixin:
    """工具栏功能混入类"""

    def _init_toolbar_state(self):
        """初始化工具栏状态"""
        self._style_combo: Optional[QComboBox] = None
        self._scene_count_combo: Optional[QComboBox] = None
        self._language_combo: Optional[QComboBox] = None
        self._toolbar_btn_stack: Optional[QStackedWidget] = None
        self._toolbar_generate_btn: Optional[QPushButton] = None
        self._toolbar_spinner: Optional[CircularSpinner] = None
        self._toolbar_loading_label: Optional[QLabel] = None
        self._sub_tab_widget = None
        self._restore_timer = None  # 恢复状态的定时器

    def _create_toolbar(self, has_content: bool) -> QFrame:
        """创建顶部工具栏

        Args:
            has_content: 是否已有漫画提示词内容

        Returns:
            工具栏Frame
        """
        s = self._styler

        toolbar = QFrame()
        toolbar.setObjectName("manga_toolbar")
        toolbar.setStyleSheet(f"""
            QFrame#manga_toolbar {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(6)}px;
                padding: {dp(6)}px;
            }}
        """)

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(dp(12), dp(6), dp(12), dp(6))
        layout.setSpacing(dp(10))

        # 风格选择
        style_label = QLabel("风格:")
        style_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(style_label)

        self._style_combo = QComboBox()
        self._style_combo.addItems(["漫画", "动漫", "美漫", "条漫"])
        self._style_combo.setStyleSheet(self._get_combo_style())
        self._style_combo.setFixedWidth(dp(75))
        layout.addWidget(self._style_combo)

        # 场景数选择
        scene_label = QLabel("场景:")
        scene_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(scene_label)

        self._scene_count_combo = QComboBox()
        self._scene_count_combo.addItem("自动", None)
        for i in range(5, 21):
            self._scene_count_combo.addItem(str(i), i)
        self._scene_count_combo.setCurrentIndex(0)
        self._scene_count_combo.setStyleSheet(self._get_combo_style())
        self._scene_count_combo.setFixedWidth(dp(65))
        layout.addWidget(self._scene_count_combo)

        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setStyleSheet(f"background-color: {s.border_light}; max-width: 1px;")
        layout.addWidget(separator1)

        # 语言选择
        lang_label = QLabel("语言:")
        lang_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        layout.addWidget(lang_label)

        self._language_combo = QComboBox()
        self._language_combo.addItem("中文", "chinese")
        self._language_combo.addItem("日文", "japanese")
        self._language_combo.addItem("英文", "english")
        self._language_combo.addItem("韩文", "korean")
        self._language_combo.addItem("无文字", "none")
        self._language_combo.setCurrentIndex(0)
        self._language_combo.setStyleSheet(self._get_combo_style())
        self._language_combo.setFixedWidth(dp(70))
        layout.addWidget(self._language_combo)

        layout.addStretch()

        # 生成按钮容器
        self._toolbar_btn_stack = QStackedWidget()
        self._toolbar_btn_stack.setFixedHeight(dp(32))

        # 状态0: 生成/重新生成按钮
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(8))

        if has_content:
            self._toolbar_generate_btn = QPushButton("重新生成")
            self._toolbar_generate_btn.setObjectName("manga_regenerate_btn")
        else:
            self._toolbar_generate_btn = QPushButton("生成提示词")
            self._toolbar_generate_btn.setObjectName("manga_generate_btn")

        self._toolbar_generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toolbar_generate_btn.setStyleSheet(ButtonStyles.primary('SM'))
        self._toolbar_generate_btn.clicked.connect(self._on_generate_clicked)
        btn_layout.addWidget(self._toolbar_generate_btn)

        # 删除按钮（仅当有内容时显示）
        if has_content:
            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("manga_delete_btn")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet(ButtonStyles.danger('SM'))
            if self._on_delete:
                delete_btn.clicked.connect(self._on_delete)
            btn_layout.addWidget(delete_btn)

        self._toolbar_btn_stack.addWidget(btn_container)

        # 状态1: 加载中状态
        loading_container = QWidget()
        loading_container.setStyleSheet("background: transparent;")
        loading_layout = QHBoxLayout(loading_container)
        loading_layout.setContentsMargins(dp(8), 0, dp(8), 0)
        loading_layout.setSpacing(dp(8))

        self._toolbar_spinner = CircularSpinner(size=dp(20), color=s.accent_color, auto_start=False)
        loading_layout.addWidget(self._toolbar_spinner)

        self._toolbar_loading_label = QLabel("正在生成提示词...")
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.accent_color};
            font-weight: 500;
        """)
        loading_layout.addWidget(self._toolbar_loading_label)
        loading_layout.addStretch()

        self._toolbar_btn_stack.addWidget(loading_container)
        self._toolbar_btn_stack.setCurrentIndex(0)

        layout.addWidget(self._toolbar_btn_stack)

        return toolbar

    def _get_combo_style(self) -> str:
        """获取下拉框统一样式"""
        s = self._styler
        return f"""
            QComboBox {{
                font-family: {s.ui_font};
                background-color: {s.bg_secondary};
                color: {s.text_primary};
                padding: {dp(4)}px {dp(8)}px;
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
            }}
            QComboBox:focus {{
                border: 1px solid {s.accent_color};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {dp(4)}px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {s.bg_card};
                color: {s.text_primary};
                selection-background-color: {s.accent_color};
                selection-color: {s.button_text};
            }}
        """

    def _on_generate_clicked(self):
        """生成按钮点击处理"""
        if self._on_generate and self._style_combo and self._scene_count_combo:
            style_map = {
                "漫画": "manga",
                "动漫": "anime",
                "美漫": "comic",
                "条漫": "webtoon",
            }
            style_text = self._style_combo.currentText()
            style = style_map.get(style_text, "manga")
            scene_count = self._scene_count_combo.currentData()
            dialogue_language = self._language_combo.currentData() if self._language_combo else "chinese"
            self._on_generate(style, scene_count, dialogue_language, False)

    # ==================== 工具栏加载状态控制 ====================

    def set_toolbar_loading(self, loading: bool, message: str = "正在生成提示词..."):
        """设置工具栏的加载状态

        Args:
            loading: 是否显示加载状态
            message: 加载时显示的消息
        """
        if not self._toolbar_btn_stack:
            return

        if loading:
            self._toolbar_btn_stack.setCurrentIndex(1)
            if self._toolbar_loading_label:
                self._toolbar_loading_label.setText(message)
            if self._toolbar_spinner:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self._toolbar_spinner.start)
        else:
            self._toolbar_btn_stack.setCurrentIndex(0)
            if self._toolbar_spinner:
                self._toolbar_spinner.stop()

    def set_toolbar_success(self, message: str = "生成成功"):
        """设置工具栏生成成功状态"""
        if not self._toolbar_btn_stack or not self._toolbar_loading_label:
            return

        s = self._styler
        if self._toolbar_spinner:
            self._toolbar_spinner.stop()

        self._toolbar_loading_label.setText(message)
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.success};
            font-weight: 500;
        """)

        from PyQt6.QtCore import QTimer
        # 取消之前的定时器
        if self._restore_timer:
            self._restore_timer.stop()
        self._restore_timer = QTimer()
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._restore_toolbar_state)
        self._restore_timer.start(2000)

    def set_toolbar_error(self, message: str = "生成失败"):
        """设置工具栏生成失败状态"""
        if not self._toolbar_btn_stack or not self._toolbar_loading_label:
            return

        s = self._styler
        if self._toolbar_spinner:
            self._toolbar_spinner.stop()

        self._toolbar_loading_label.setText(message)
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.error};
            font-weight: 500;
        """)

        from PyQt6.QtCore import QTimer
        # 取消之前的定时器
        if self._restore_timer:
            self._restore_timer.stop()
        self._restore_timer = QTimer()
        self._restore_timer.setSingleShot(True)
        self._restore_timer.timeout.connect(self._restore_toolbar_state)
        self._restore_timer.start(3000)

    def _restore_toolbar_state(self):
        """恢复工具栏按钮状态"""
        if not self._toolbar_btn_stack:
            return

        s = self._styler

        if self._toolbar_loading_label:
            self._toolbar_loading_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.accent_color};
                font-weight: 500;
            """)
            self._toolbar_loading_label.setText("正在生成提示词...")

        self._toolbar_btn_stack.setCurrentIndex(0)
