"""
配置对话框集合 - 主题适配

包含各种配置相关的对话框。
"""

import math
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget,
    QSpinBox, QRadioButton, QButtonGroup, QDialog
)
from PyQt6.QtCore import Qt
from utils.dpi_utils import dp
from typing import Tuple, Optional

from ..base import BaseDialog
from ..styles import DialogStyles


class PartOutlineConfigDialog(BaseDialog):
    """部分大纲配置对话框 - 主题适配

    支持配置：
    1. 生成章节范围：可以选择只生成前N章的部分大纲（增量生成）
    2. 分部方式：按部分数量或按每部分章节数

    支持两种模式：
    - 首次生成：可自由配置所有参数
    - 继续生成：锁定每部分章节数，只能选择生成范围

    使用方式：
        # 首次生成
        result = PartOutlineConfigDialog.getConfigStatic(
            parent=self,
            total_chapters=200
        )

        # 继续生成
        result = PartOutlineConfigDialog.getContinueConfigStatic(
            parent=self,
            total_chapters=200,
            current_covered_chapter=50,
            current_parts=2,
            chapters_per_part=25
        )

        if result:
            generate_chapters, chapters_per_part = result
    """

    def __init__(
        self,
        parent=None,
        total_chapters: int = 100,
        current_covered_chapter: int = 0,
        current_parts: int = 0,
        fixed_chapters_per_part: Optional[int] = None
    ):
        self.total_chapters = total_chapters
        self.current_covered_chapter = current_covered_chapter
        self.current_parts = current_parts
        self.fixed_chapters_per_part = fixed_chapters_per_part
        self.is_continue_mode = current_covered_chapter > 0

        # UI组件引用
        self.container = None
        self.title_label = None
        self.info_label = None
        self.range_label = None
        self.range_spin = None
        self.range_hint_label = None
        self.mode_by_parts = None
        self.mode_by_chapters = None
        self.parts_spin = None
        self.chapters_spin = None
        self.preview_label = None
        self.ok_btn = None
        self.cancel_btn = None
        self.method_container = None
        self.half_btn = None
        self.all_btn = None
        self.button_group = None

        super().__init__(parent)
        self._setup_ui()
        self._apply_theme()
        self._update_preview()

    def _setup_ui(self):
        """创建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 容器
        self.container = QFrame()
        self.container.setObjectName("part_config_container")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(dp(28), dp(24), dp(28), dp(24))
        container_layout.setSpacing(dp(16))

        # 标题 - 根据模式显示不同文本
        if self.is_continue_mode:
            self.title_label = QLabel("继续生成部分大纲")
        else:
            self.title_label = QLabel("生成部分大纲")
        self.title_label.setObjectName("part_config_title")
        container_layout.addWidget(self.title_label)

        # 信息提示 - 根据模式显示不同内容
        if self.is_continue_mode:
            self.info_label = QLabel(
                f"小说总计 {self.total_chapters} 章，"
                f"已生成 {self.current_parts} 个部分（覆盖到第 {self.current_covered_chapter} 章）"
            )
        else:
            self.info_label = QLabel(f"小说总计 {self.total_chapters} 章")
        self.info_label.setObjectName("part_config_info")
        self.info_label.setWordWrap(True)
        container_layout.addWidget(self.info_label)

        # === 章节范围选择 ===
        range_container = QWidget()
        range_layout = QHBoxLayout(range_container)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(dp(12))

        # 根据模式显示不同的标签
        if self.is_continue_mode:
            self.range_label = QLabel("生成到第")
        else:
            self.range_label = QLabel("生成范围：前")
        self.range_label.setObjectName("part_config_label")
        range_layout.addWidget(self.range_label)

        self.range_spin = QSpinBox()
        self.range_spin.setObjectName("part_config_spin")

        if self.is_continue_mode:
            # 继续模式：从当前覆盖章节+1开始，到总章节数
            min_chapters = self.current_covered_chapter + 1
            self.range_spin.setRange(min_chapters, self.total_chapters)
            self.range_spin.setValue(self.total_chapters)  # 默认生成到最后
        else:
            # 首次模式：最小20章，最大=总章节数
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

        # 快捷按钮 - 计算一半的目标值
        if self.is_continue_mode:
            remaining = self.total_chapters - self.current_covered_chapter
            half_value = self.current_covered_chapter + remaining // 2
        else:
            half_value = self.total_chapters // 2

        self.half_btn = QPushButton("一半")
        self.half_btn.setObjectName("quick_btn")
        self.half_btn.setFixedSize(dp(50), dp(32))
        self.half_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.half_btn.clicked.connect(lambda _, v=half_value: self.range_spin.setValue(v))
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

        # === 分部方式选择（继续模式下隐藏或显示锁定信息）===
        self.method_container = QWidget()
        method_layout = QVBoxLayout(self.method_container)
        method_layout.setContentsMargins(0, 0, 0, 0)
        method_layout.setSpacing(dp(12))

        if self.is_continue_mode and self.fixed_chapters_per_part:
            # 继续模式：显示锁定的每部分章节数，不需要分部方式选择控件
            locked_label = QLabel(f"每部分章节数：{self.fixed_chapters_per_part} 章（与已生成部分保持一致）")
            locked_label.setObjectName("part_config_locked")
            method_layout.addWidget(locked_label)

            # 继续模式不需要这些控件，设为 None
            self.button_group = None
            self.mode_by_parts = None
            self.mode_by_chapters = None
            self.parts_spin = None
            self.chapters_spin = None
        else:
            # 首次模式：完整的分部方式选择
            method_label = QLabel("分部方式：")
            method_label.setObjectName("part_config_label")
            method_layout.addWidget(method_label)

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

            method_layout.addWidget(mode1_container)

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

            method_layout.addWidget(mode2_container)

            # 连接单选按钮切换
            self.mode_by_parts.toggled.connect(self._on_mode_changed)
            self.mode_by_chapters.toggled.connect(self._on_mode_changed)

        container_layout.addWidget(self.method_container)

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

        # 按钮文本根据模式调整
        if self.is_continue_mode:
            self.ok_btn = QPushButton("继续生成")
        else:
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

        # 初始化部分数量范围（仅首次模式需要）
        if not self.is_continue_mode:
            self._update_parts_range()

    def _update_parts_range(self):
        """根据当前章节范围更新部分数量的范围"""
        generate_chapters = self.range_spin.value()

        # 计算合理的部分数量范围
        default_parts = max(2, math.ceil(generate_chapters / 25))
        max_parts = max(2, math.ceil(generate_chapters / 10))
        min_parts = 2

        self.parts_spin.setRange(min_parts, min(max_parts, 20))
        self.parts_spin.setValue(min(default_parts, min(max_parts, 20)))

    def _on_range_changed(self):
        """章节范围改变"""
        # 只有首次模式需要更新部分数量范围
        if not self.is_continue_mode and self.parts_spin:
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
        generate_chapters = self.range_spin.value()

        if self.is_continue_mode:
            # 继续模式的预览
            new_chapters = generate_chapters - self.current_covered_chapter
            chapters_per_part = self.fixed_chapters_per_part or 25

            # 计算将新增多少部分
            total_parts_after = math.ceil(generate_chapters / chapters_per_part)
            new_parts = total_parts_after - self.current_parts

            # 更新范围提示
            if generate_chapters < self.total_chapters:
                remaining = self.total_chapters - generate_chapters
                self.range_hint_label.setText(
                    f"将覆盖第 {self.current_covered_chapter + 1}-{generate_chapters} 章，"
                    f"剩余 {remaining} 章可稍后生成"
                )
            else:
                self.range_hint_label.setText(
                    f"将覆盖第 {self.current_covered_chapter + 1}-{generate_chapters} 章（全部剩余章节）"
                )
            self.range_hint_label.setVisible(True)

            # 生成预览文本
            if new_parts <= 0:
                preview_text = "当前范围无需新增部分"
            elif new_parts == 1:
                preview_text = f"将新增 1 个部分（第 {self.current_parts + 1} 部分）"
            else:
                preview_text = (
                    f"将新增 {new_parts} 个部分\n"
                    f"（第 {self.current_parts + 1} 至第 {total_parts_after} 部分）"
                )

            self.preview_label.setText(preview_text)
        else:
            # 首次模式的预览（原有逻辑）
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
        # 使用 DialogStyles 辅助类
        self.container.setStyleSheet(DialogStyles.container("part_config_container"))
        self.title_label.setStyleSheet(DialogStyles.title("part_config_title"))
        self.info_label.setStyleSheet(DialogStyles.label("part_config_info"))

        # 标签样式（应用到多个同名label）
        label_style = DialogStyles.label("part_config_label")
        for widget in self.container.findChildren(QLabel):
            if widget.objectName() == "part_config_label":
                widget.setStyleSheet(label_style)

        # 范围提示样式
        self.range_hint_label.setStyleSheet(DialogStyles.hint_label("part_config_hint"))

        # 分隔线样式
        separator = self.container.findChild(QFrame, "config_separator")
        if separator:
            separator.setStyleSheet(DialogStyles.separator("config_separator"))

        # 单选按钮样式（仅首次模式）
        radio_style = DialogStyles.radio_button()
        if self.mode_by_parts:
            self.mode_by_parts.setStyleSheet(radio_style)
        if self.mode_by_chapters:
            self.mode_by_chapters.setStyleSheet(radio_style)

        # 锁定标签样式（继续模式）
        locked_label = self.method_container.findChild(QLabel, "part_config_locked")
        if locked_label:
            locked_label.setStyleSheet(DialogStyles.locked_label("part_config_locked"))

        # 数字输入框样式（通用）
        spin_style = DialogStyles.spin_box_generic()
        self.range_spin.setStyleSheet(spin_style)
        if self.parts_spin:
            self.parts_spin.setStyleSheet(spin_style)
        if self.chapters_spin:
            self.chapters_spin.setStyleSheet(spin_style)

        # 后缀标签样式
        suffix_style = DialogStyles.label("part_config_suffix")
        for widget in self.container.findChildren(QLabel):
            if widget.objectName() == "part_config_suffix":
                widget.setStyleSheet(suffix_style)

        # 快捷按钮样式
        quick_btn_style = DialogStyles.quick_button()
        self.half_btn.setStyleSheet(quick_btn_style)
        self.all_btn.setStyleSheet(quick_btn_style)

        # 预览区域样式
        preview_container = self.container.findChild(QFrame, "preview_container")
        if preview_container:
            preview_container.setStyleSheet(DialogStyles.preview_container("preview_container"))

        self.preview_label.setStyleSheet(DialogStyles.preview_label("part_config_preview"))

        # 按钮样式
        self.cancel_btn.setStyleSheet(DialogStyles.button_secondary("part_config_cancel_btn"))
        self.ok_btn.setStyleSheet(DialogStyles.button_primary("part_config_ok_btn"))

    def getConfig(self) -> Tuple[int, int]:
        """获取配置结果

        Returns:
            (generate_chapters, chapters_per_part): 生成章节数和每部分章节数
        """
        generate_chapters = self.range_spin.value()

        if self.is_continue_mode and self.fixed_chapters_per_part:
            # 继续模式：使用固定的每部分章节数
            chapters_per_part = self.fixed_chapters_per_part
        elif self.mode_by_parts and self.mode_by_parts.isChecked():
            parts_count = self.parts_spin.value()
            chapters_per_part = math.ceil(generate_chapters / parts_count)
        elif self.chapters_spin:
            chapters_per_part = self.chapters_spin.value()
        else:
            # 默认值（理论上不应该到达这里）
            chapters_per_part = 25

        return generate_chapters, chapters_per_part

    @staticmethod
    def getConfigStatic(
        parent=None,
        total_chapters: int = 100
    ) -> Optional[Tuple[int, int]]:
        """静态方法：显示对话框并获取配置（首次生成）

        Returns:
            (generate_chapters, chapters_per_part) 或 None（用户取消）
        """
        dialog = PartOutlineConfigDialog(parent, total_chapters)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getConfig()
        return None

    @staticmethod
    def getContinueConfigStatic(
        parent=None,
        total_chapters: int = 100,
        current_covered_chapter: int = 0,
        current_parts: int = 0,
        chapters_per_part: int = 25
    ) -> Optional[Tuple[int, int]]:
        """静态方法：显示对话框并获取配置（继续生成）

        Args:
            parent: 父窗口
            total_chapters: 小说总章节数
            current_covered_chapter: 当前已覆盖到第几章
            current_parts: 当前已有多少部分
            chapters_per_part: 每部分章节数（锁定，不可修改）

        Returns:
            (generate_chapters, chapters_per_part) 或 None（用户取消）
        """
        dialog = PartOutlineConfigDialog(
            parent,
            total_chapters=total_chapters,
            current_covered_chapter=current_covered_chapter,
            current_parts=current_parts,
            fixed_chapters_per_part=chapters_per_part
        )
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            return dialog.getConfig()
        return None
