"""
状态管理混入模块

提供检查点状态显示和管理功能。
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QWidget, QPushButton
)
from PyQt6.QtCore import Qt

from themes.button_styles import ButtonStyles
from utils.dpi_utils import dp, sp


class StateMixin:
    """状态管理功能混入类"""

    def _init_checkpoint_state(self):
        """初始化检查点相关状态"""
        self._checkpoint_status: Optional[str] = None
        self._checkpoint_scene_count: int = 0
        self._checkpoint_has_layout: bool = False
        self._continue_btn: Optional[QPushButton] = None
        self._checkpoint_info_label: Optional[QLabel] = None

    # ==================== 断点续传状态显示 ====================

    def show_checkpoint_status(
        self,
        status: str,
        message: str,
        scene_count: int = 0,
        has_layout: bool = False,
    ):
        """显示检查点状态信息

        当生成过程中断时，显示检查点状态并提供"继续生成"按钮。

        Args:
            status: 状态类型 ("failed" 或 "incomplete")
            message: 状态描述信息
            scene_count: 已提取的场景数量
            has_layout: 是否已完成排版生成
        """
        if not self._toolbar_btn_stack:
            return

        s = self._styler

        # 取消之前的恢复定时器，防止被覆盖
        if hasattr(self, '_restore_timer') and self._restore_timer:
            self._restore_timer.stop()
            self._restore_timer = None

        # 保存检查点状态
        self._checkpoint_status = status
        self._checkpoint_scene_count = scene_count
        self._checkpoint_has_layout = has_layout

        # 如果还没有创建检查点状态UI，需要添加第三个状态页面
        if self._toolbar_btn_stack.count() < 3:
            self._create_checkpoint_status_widget()

        # 更新检查点状态信息
        if self._checkpoint_info_label:
            color = s.error if status == "failed" else s.warning
            self._checkpoint_info_label.setText(message)
            self._checkpoint_info_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {color};
                font-weight: 500;
            """)

        # 切换到检查点状态页面
        self._toolbar_btn_stack.setCurrentIndex(2)

    def _create_checkpoint_status_widget(self):
        """创建检查点状态显示控件"""
        if not self._toolbar_btn_stack:
            return

        s = self._styler

        # 状态2: 检查点状态（未完成/失败可继续）
        checkpoint_container = QWidget()
        checkpoint_container.setStyleSheet("background: transparent;")
        checkpoint_layout = QHBoxLayout(checkpoint_container)
        checkpoint_layout.setContentsMargins(dp(8), 0, dp(8), 0)
        checkpoint_layout.setSpacing(dp(8))

        # 警告图标
        warning_icon = QLabel("!")
        warning_icon.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            font-weight: bold;
            color: {s.warning};
            background-color: {s.warning}20;
            padding: {dp(2)}px {dp(6)}px;
            border-radius: {dp(3)}px;
        """)
        checkpoint_layout.addWidget(warning_icon)

        # 状态信息标签
        self._checkpoint_info_label = QLabel("生成未完成")
        self._checkpoint_info_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(11)}px;
            color: {s.warning};
            font-weight: 500;
        """)
        checkpoint_layout.addWidget(self._checkpoint_info_label)

        checkpoint_layout.addStretch()

        # 继续生成按钮
        self._continue_btn = QPushButton("继续生成")
        self._continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._continue_btn.setStyleSheet(ButtonStyles.primary('SM'))
        self._continue_btn.clicked.connect(self._on_continue_clicked)
        checkpoint_layout.addWidget(self._continue_btn)

        # 重新开始按钮
        restart_btn = QPushButton("重新开始")
        restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        restart_btn.setStyleSheet(ButtonStyles.secondary('SM'))
        restart_btn.clicked.connect(self._on_generate_clicked)
        checkpoint_layout.addWidget(restart_btn)

        self._toolbar_btn_stack.addWidget(checkpoint_container)

    def _on_continue_clicked(self):
        """继续生成按钮点击处理"""
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
            # 从检查点继续生成
            self._on_generate(style, scene_count, dialogue_language, True)

    def hide_checkpoint_status(self):
        """隐藏检查点状态，恢复正常按钮显示"""
        if self._toolbar_btn_stack:
            self._toolbar_btn_stack.setCurrentIndex(0)
        self._checkpoint_status = None
        self._checkpoint_scene_count = 0
        self._checkpoint_has_layout = False
