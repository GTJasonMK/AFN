"""
工具栏模块

提供漫画分镜生成的工具栏UI和状态管理。
基于页面驱动的漫画分镜架构，支持风格选择和页数范围设置。
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QFrame, QPushButton, QComboBox, QStackedWidget, QWidget, QSpinBox, QCheckBox, QMenu
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
        self._language_combo: Optional[QComboBox] = None  # 语言选择
        self._min_pages_spin: Optional[QSpinBox] = None
        self._max_pages_spin: Optional[QSpinBox] = None
        self._use_portraits_checkbox: Optional[QCheckBox] = None  # 使用角色立绘
        self._auto_generate_portraits_checkbox: Optional[QCheckBox] = None  # 自动生成缺失立绘
        self._toolbar_btn_stack: Optional[QStackedWidget] = None
        self._toolbar_generate_btn: Optional[QPushButton] = None
        self._toolbar_spinner: Optional[CircularSpinner] = None
        self._toolbar_loading_label: Optional[QLabel] = None
        self._toolbar_stop_btn: Optional[QPushButton] = None  # 停止按钮
        self._sub_tab_widget = None
        self._restore_timer = None  # 恢复状态的定时器
        # 一键生成所有图片相关状态
        self._generate_all_btn: Optional[QPushButton] = None
        self._generate_all_btn_stack: Optional[QStackedWidget] = None
        self._generate_all_spinner: Optional[CircularSpinner] = None
        self._generate_all_progress_label: Optional[QLabel] = None
        self._generate_all_stop_btn: Optional[QPushButton] = None  # 批量生成停止按钮
        self._generate_all_restore_timer = None

    def _create_toolbar(self, has_content: bool, can_resume: bool = False, resume_progress: dict = None) -> QFrame:
        """创建顶部工具栏

        Args:
            has_content: 是否已有漫画分镜内容
            can_resume: 是否可以继续之前的生成任务
            resume_progress: 断点续传进度信息

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
            }}
        """)

        # 使用垂直布局，分两行显示
        main_layout = QVBoxLayout(toolbar)
        main_layout.setContentsMargins(dp(12), dp(10), dp(12), dp(12))
        main_layout.setSpacing(dp(10))

        # ==================== 第一行：配置选项 ====================
        config_row = QHBoxLayout()
        config_row.setSpacing(dp(12))

        # 风格选择
        style_label = QLabel("风格:")
        style_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        config_row.addWidget(style_label)

        self._style_combo = QComboBox()
        self._style_combo.addItems(["漫画", "动漫", "美漫", "条漫"])
        self._style_combo.setStyleSheet(self._get_combo_style())
        self._style_combo.setMinimumWidth(dp(80))
        config_row.addWidget(self._style_combo)

        # 语言选择
        language_label = QLabel("语言:")
        language_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        config_row.addWidget(language_label)

        self._language_combo = QComboBox()
        self._language_combo.addItems(["中文", "日语", "英语", "韩语"])
        self._language_combo.setStyleSheet(self._get_combo_style())
        self._language_combo.setMinimumWidth(dp(76))
        self._language_combo.setToolTip("对话、旁白和音效的语言")
        config_row.addWidget(self._language_combo)

        # 页数范围选择
        pages_label = QLabel("页数:")
        pages_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        config_row.addWidget(pages_label)

        self._min_pages_spin = QSpinBox()
        self._min_pages_spin.setRange(3, 20)
        self._min_pages_spin.setValue(8)
        self._min_pages_spin.setStyleSheet(self._get_spin_style())
        self._min_pages_spin.setMinimumWidth(dp(56))
        self._min_pages_spin.setToolTip("最少页数")
        config_row.addWidget(self._min_pages_spin)

        range_label = QLabel("-")
        range_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(12)}px;
            color: {s.text_secondary};
        """)
        config_row.addWidget(range_label)

        self._max_pages_spin = QSpinBox()
        self._max_pages_spin.setRange(5, 30)
        self._max_pages_spin.setValue(15)
        self._max_pages_spin.setStyleSheet(self._get_spin_style())
        self._max_pages_spin.setMinimumWidth(dp(56))
        self._max_pages_spin.setToolTip("最多页数")
        config_row.addWidget(self._max_pages_spin)

        # 分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(f"background-color: {s.border_light};")
        separator.setFixedWidth(dp(1))
        separator.setFixedHeight(dp(20))
        config_row.addWidget(separator)

        # 使用角色立绘复选框
        self._use_portraits_checkbox = QCheckBox("角色立绘")
        self._use_portraits_checkbox.setChecked(True)  # 默认启用
        self._use_portraits_checkbox.setToolTip("使用角色立绘作为参考图（img2img）\n保持画格中角色外观一致")
        self._use_portraits_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                spacing: {dp(4)}px;
            }}
            QCheckBox::indicator {{
                width: {dp(14)}px;
                height: {dp(14)}px;
                border: 1px solid {s.border_light};
                border-radius: {dp(3)}px;
                background-color: {s.bg_secondary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {s.accent_color};
                border-color: {s.accent_color};
            }}
            QCheckBox::indicator:hover {{
                border-color: {s.accent_color};
            }}
        """)
        config_row.addWidget(self._use_portraits_checkbox)

        # 自动生成缺失立绘复选框
        self._auto_generate_portraits_checkbox = QCheckBox("自动生成")
        self._auto_generate_portraits_checkbox.setChecked(True)  # 默认启用
        self._auto_generate_portraits_checkbox.setToolTip("自动为缺失立绘的角色生成立绘")
        self._auto_generate_portraits_checkbox.setStyleSheet(f"""
            QCheckBox {{
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                spacing: {dp(4)}px;
            }}
            QCheckBox::indicator {{
                width: {dp(14)}px;
                height: {dp(14)}px;
                border: 1px solid {s.border_light};
                border-radius: {dp(3)}px;
                background-color: {s.bg_secondary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {s.accent_color};
                border-color: {s.accent_color};
            }}
            QCheckBox::indicator:hover {{
                border-color: {s.accent_color};
            }}
        """)
        config_row.addWidget(self._auto_generate_portraits_checkbox)

        config_row.addStretch()
        main_layout.addLayout(config_row)

        # ==================== 第二行：操作按钮 ====================
        btn_row = QHBoxLayout()
        btn_row.setSpacing(dp(8))

        # 生成按钮容器（XS按钮需要足够空间）
        self._toolbar_btn_stack = QStackedWidget()
        self._toolbar_btn_stack.setFixedHeight(dp(32))

        # 状态0: 生成/继续生成/重新生成按钮
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(6))

        if has_content:
            # 已有内容：显示重新生成按钮（带下拉菜单）
            self._toolbar_generate_btn = QPushButton("重新生成")
            self._toolbar_generate_btn.setObjectName("manga_regenerate_btn")
            self._toolbar_generate_btn.setStyleSheet(ButtonStyles.primary('XS'))
            self._toolbar_generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # 创建下拉菜单
            regenerate_menu = QMenu(self._toolbar_generate_btn)
            regenerate_menu.setStyleSheet(self._get_menu_style())

            # 菜单项
            action_full = regenerate_menu.addAction("完整重新生成")
            action_full.setToolTip("从头开始，重新提取信息、规划、分镜")
            action_full.triggered.connect(lambda: self._on_generate_clicked(force_restart=True, start_from_stage="extraction"))

            action_planning = regenerate_menu.addAction("从规划开始 (保留信息提取)")
            action_planning.setToolTip("保留已提取的角色、对话等信息，重新规划页面")
            action_planning.triggered.connect(lambda: self._on_generate_clicked(force_restart=True, start_from_stage="planning"))

            action_storyboard = regenerate_menu.addAction("从分镜开始 (保留规划)")
            action_storyboard.setToolTip("保留页面规划，只重新设计分镜布局")
            action_storyboard.triggered.connect(lambda: self._on_generate_clicked(force_restart=True, start_from_stage="storyboard"))

            action_prompt = regenerate_menu.addAction("仅重新构建提示词")
            action_prompt.setToolTip("保留分镜设计，只重新生成提示词文本")
            action_prompt.triggered.connect(lambda: self._on_generate_clicked(force_restart=True, start_from_stage="prompt_building"))

            self._toolbar_generate_btn.setMenu(regenerate_menu)
            btn_layout.addWidget(self._toolbar_generate_btn)
        elif can_resume:
            # 有断点：显示两个按钮 - 从头生成 和 继续生成
            # 从头生成按钮
            restart_btn = QPushButton("从头生成")
            restart_btn.setObjectName("manga_restart_btn")
            restart_btn.setStyleSheet(ButtonStyles.secondary('XS'))
            restart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            restart_btn.setToolTip("忽略断点，重新开始生成漫画分镜")
            restart_btn.clicked.connect(lambda: self._on_generate_clicked(force_restart=True))
            btn_layout.addWidget(restart_btn)

            # 继续生成按钮
            stage_label = ""
            progress_text = ""
            if resume_progress:
                stage = resume_progress.get('stage', '')
                stage_label = resume_progress.get('stage_label', '')
                current = resume_progress.get('current', 0)
                total = resume_progress.get('total', 0)
                if total > 0:
                    progress_text = f" ({current}/{total})"

            if stage_label:
                btn_text = f"继续: {stage_label}{progress_text}"
            else:
                btn_text = f"继续生成{progress_text}"

            self._toolbar_generate_btn = QPushButton(btn_text)
            self._toolbar_generate_btn.setObjectName("manga_resume_btn")
            self._toolbar_generate_btn.setStyleSheet(ButtonStyles.warning('XS'))
            self._toolbar_generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._toolbar_generate_btn.setToolTip("从上次中断的位置继续生成")
            self._toolbar_generate_btn.clicked.connect(lambda: self._on_generate_clicked(force_restart=False))
            btn_layout.addWidget(self._toolbar_generate_btn)
        else:
            # 无内容：显示生成分镜按钮
            self._toolbar_generate_btn = QPushButton("生成分镜")
            self._toolbar_generate_btn.setObjectName("manga_generate_btn")
            self._toolbar_generate_btn.setStyleSheet(ButtonStyles.primary('XS'))
            self._toolbar_generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._toolbar_generate_btn.clicked.connect(lambda: self._on_generate_clicked(force_restart=False))
            btn_layout.addWidget(self._toolbar_generate_btn)

        # 删除按钮（仅当有内容时显示）
        if has_content:
            delete_btn = QPushButton("删除")
            delete_btn.setObjectName("manga_delete_btn")
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.setStyleSheet(ButtonStyles.danger('XS'))
            if self._on_delete:
                delete_btn.clicked.connect(self._on_delete)
            btn_layout.addWidget(delete_btn)

        self._toolbar_btn_stack.addWidget(btn_container)

        # 状态1: 加载中状态
        loading_container = QWidget()
        loading_container.setStyleSheet("background: transparent;")
        loading_layout = QHBoxLayout(loading_container)
        loading_layout.setContentsMargins(dp(6), 0, dp(6), 0)
        loading_layout.setSpacing(dp(6))

        self._toolbar_spinner = CircularSpinner(size=dp(16), color=s.accent_color, auto_start=False)
        loading_layout.addWidget(self._toolbar_spinner)

        self._toolbar_loading_label = QLabel("生成中...")
        self._toolbar_loading_label.setStyleSheet(f"""
            font-family: {s.ui_font};
            font-size: {sp(11)}px;
            color: {s.accent_color};
            font-weight: 500;
        """)
        loading_layout.addWidget(self._toolbar_loading_label)

        # 停止按钮
        self._toolbar_stop_btn = QPushButton("停止")
        self._toolbar_stop_btn.setObjectName("manga_stop_btn")
        self._toolbar_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toolbar_stop_btn.setStyleSheet(ButtonStyles.danger('XS'))
        self._toolbar_stop_btn.setFixedWidth(dp(50))
        self._toolbar_stop_btn.clicked.connect(self._on_stop_generate_clicked)
        loading_layout.addWidget(self._toolbar_stop_btn)

        loading_layout.addStretch()

        self._toolbar_btn_stack.addWidget(loading_container)
        self._toolbar_btn_stack.setCurrentIndex(0)

        btn_row.addWidget(self._toolbar_btn_stack)

        # 一键生成所有图片按钮（仅当有漫画分镜内容时显示）
        if has_content:
            self._generate_all_btn_stack = QStackedWidget()
            self._generate_all_btn_stack.setFixedHeight(dp(32))

            # 状态0: 一键生成按钮
            gen_all_btn_container = QWidget()
            gen_all_btn_container.setStyleSheet("background: transparent;")
            gen_all_btn_layout = QHBoxLayout(gen_all_btn_container)
            gen_all_btn_layout.setContentsMargins(0, 0, 0, 0)

            self._generate_all_btn = QPushButton("生成全部图片")
            self._generate_all_btn.setObjectName("generate_all_images_btn")
            self._generate_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._generate_all_btn.setStyleSheet(ButtonStyles.secondary('XS'))
            self._generate_all_btn.clicked.connect(self._on_generate_all_clicked)
            gen_all_btn_layout.addWidget(self._generate_all_btn)
            gen_all_btn_layout.addStretch()  # 防止按钮被拉伸

            self._generate_all_btn_stack.addWidget(gen_all_btn_container)

            # 状态1: 生成进度显示
            gen_all_progress_container = QWidget()
            gen_all_progress_container.setStyleSheet("background: transparent;")
            gen_all_progress_layout = QHBoxLayout(gen_all_progress_container)
            gen_all_progress_layout.setContentsMargins(dp(6), 0, dp(6), 0)
            gen_all_progress_layout.setSpacing(dp(4))

            self._generate_all_spinner = CircularSpinner(size=dp(14), color=s.accent_color, auto_start=False)
            gen_all_progress_layout.addWidget(self._generate_all_spinner)

            self._generate_all_progress_label = QLabel("生成中 0/0")
            self._generate_all_progress_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.accent_color};
                font-weight: 500;
            """)
            gen_all_progress_layout.addWidget(self._generate_all_progress_label)

            # 批量生成停止按钮
            self._generate_all_stop_btn = QPushButton("停止")
            self._generate_all_stop_btn.setObjectName("generate_all_stop_btn")
            self._generate_all_stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._generate_all_stop_btn.setStyleSheet(ButtonStyles.danger('XS'))
            self._generate_all_stop_btn.setFixedWidth(dp(50))
            self._generate_all_stop_btn.clicked.connect(self._on_stop_generate_all_clicked)
            gen_all_progress_layout.addWidget(self._generate_all_stop_btn)

            gen_all_progress_layout.addStretch()

            self._generate_all_btn_stack.addWidget(gen_all_progress_container)
            self._generate_all_btn_stack.setCurrentIndex(0)

            btn_row.addWidget(self._generate_all_btn_stack, stretch=1)  # 让这个容器占用剩余空间

        main_layout.addLayout(btn_row)

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

    def _get_spin_style(self) -> str:
        """获取数字输入框统一样式"""
        s = self._styler
        return f"""
            QSpinBox {{
                font-family: {s.ui_font};
                background-color: {s.bg_secondary};
                color: {s.text_primary};
                padding: {dp(2)}px {dp(4)}px;
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
                font-size: {sp(12)}px;
            }}
            QSpinBox:focus {{
                border: 1px solid {s.accent_color};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: {dp(16)}px;
            }}
        """

    def _get_menu_style(self) -> str:
        """获取下拉菜单统一样式"""
        s = self._styler
        return f"""
            QMenu {{
                background-color: {s.bg_card};
                border: 1px solid {s.border_light};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px;
            }}
            QMenu::item {{
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_primary};
                padding: {dp(6)}px {dp(12)}px;
                border-radius: {dp(3)}px;
            }}
            QMenu::item:selected {{
                background-color: {s.accent_color};
                color: {s.button_text};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {s.border_light};
                margin: {dp(4)}px {dp(8)}px;
            }}
        """

    def _on_generate_clicked(self, force_restart: bool = False, start_from_stage: Optional[str] = None):
        """生成按钮点击处理

        Args:
            force_restart: 是否强制从头开始，忽略断点
            start_from_stage: 指定从哪个阶段开始（extraction/planning/storyboard/prompt_building）
        """
        if self._on_generate and self._style_combo and self._min_pages_spin and self._max_pages_spin:
            style_map = {
                "漫画": "manga",
                "动漫": "anime",
                "美漫": "comic",
                "条漫": "webtoon",
            }
            language_map = {
                "中文": "chinese",
                "日语": "japanese",
                "英语": "english",
                "韩语": "korean",
            }
            style_text = self._style_combo.currentText()
            style = style_map.get(style_text, "manga")
            language_text = self._language_combo.currentText() if self._language_combo else "中文"
            language = language_map.get(language_text, "chinese")
            min_pages = self._min_pages_spin.value()
            max_pages = self._max_pages_spin.value()
            use_portraits = self._use_portraits_checkbox.isChecked() if self._use_portraits_checkbox else True
            auto_generate_portraits = self._auto_generate_portraits_checkbox.isChecked() if self._auto_generate_portraits_checkbox else True

            # 确保max >= min
            if max_pages < min_pages:
                max_pages = min_pages

            self._on_generate(
                style, min_pages, max_pages, language,
                use_portraits, auto_generate_portraits, force_restart, start_from_stage
            )

    # ==================== 工具栏加载状态控制 ====================

    def set_toolbar_loading(self, loading: bool, message: str = "生成中..."):
        """设置工具栏的加载状态

        Args:
            loading: 是否显示加载状态
            message: 加载时显示的消息
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"set_toolbar_loading called: loading={loading}, stack exists={self._toolbar_btn_stack is not None}")

        if not self._toolbar_btn_stack:
            logger.warning("_toolbar_btn_stack is None, cannot show loading state")
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
            self._toolbar_loading_label.setText("生成中...")

        self._toolbar_btn_stack.setCurrentIndex(0)

    # ==================== 一键生成所有图片 ====================

    def _on_generate_all_clicked(self):
        """一键生成所有图片按钮点击处理"""
        if hasattr(self, '_on_generate_all_images') and self._on_generate_all_images:
            self._on_generate_all_images()

    def _on_stop_generate_clicked(self):
        """停止生成分镜按钮点击处理"""
        if hasattr(self, '_on_stop_generate') and self._on_stop_generate:
            self._on_stop_generate()

    def _on_stop_generate_all_clicked(self):
        """停止批量生成图片按钮点击处理"""
        if hasattr(self, '_on_stop_generate_all') and self._on_stop_generate_all:
            self._on_stop_generate_all()

    def set_generate_all_loading(self, loading: bool, current: int = 0, total: int = 0):
        """设置一键生成的加载状态

        Args:
            loading: 是否显示加载状态
            current: 当前进度
            total: 总数
        """
        try:
            if not self._generate_all_btn_stack:
                return

            if loading:
                self._generate_all_btn_stack.setCurrentIndex(1)
                if self._generate_all_progress_label:
                    self._generate_all_progress_label.setText(f"生成中 {current}/{total}")
                if self._generate_all_spinner:
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(50, self._generate_all_spinner.start)
            else:
                self._generate_all_btn_stack.setCurrentIndex(0)
                if self._generate_all_spinner:
                    self._generate_all_spinner.stop()
        except RuntimeError:
            # 组件已被删除，忽略更新
            pass

    def update_generate_all_progress(self, current: int, total: int):
        """更新一键生成进度

        Args:
            current: 当前进度
            total: 总数
        """
        try:
            if self._generate_all_progress_label and not self._generate_all_progress_label.isHidden():
                self._generate_all_progress_label.setText(f"生成中 {current}/{total}")
        except RuntimeError:
            # 组件已被删除，忽略更新
            pass

    def set_generate_all_success(self, message: str = "全部生成完成"):
        """设置一键生成成功状态"""
        try:
            if not self._generate_all_btn_stack or not self._generate_all_progress_label:
                return

            s = self._styler
            if self._generate_all_spinner:
                self._generate_all_spinner.stop()

            self._generate_all_progress_label.setText(message)
            self._generate_all_progress_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.success};
                font-weight: 500;
            """)

            from PyQt6.QtCore import QTimer
            if self._generate_all_restore_timer:
                self._generate_all_restore_timer.stop()
            self._generate_all_restore_timer = QTimer()
            self._generate_all_restore_timer.setSingleShot(True)
            self._generate_all_restore_timer.timeout.connect(self._restore_generate_all_state)
            self._generate_all_restore_timer.start(2000)
        except RuntimeError:
            # 组件已被删除，忽略更新
            pass

    def set_generate_all_error(self, message: str = "生成失败"):
        """设置一键生成失败状态"""
        try:
            if not self._generate_all_btn_stack or not self._generate_all_progress_label:
                return

            s = self._styler
            if self._generate_all_spinner:
                self._generate_all_spinner.stop()

            self._generate_all_progress_label.setText(message)
            self._generate_all_progress_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(11)}px;
                color: {s.error};
                font-weight: 500;
            """)

            from PyQt6.QtCore import QTimer
            if self._generate_all_restore_timer:
                self._generate_all_restore_timer.stop()
            self._generate_all_restore_timer = QTimer()
            self._generate_all_restore_timer.setSingleShot(True)
            self._generate_all_restore_timer.timeout.connect(self._restore_generate_all_state)
            self._generate_all_restore_timer.start(3000)
        except RuntimeError:
            # 组件已被删除，忽略更新
            pass

    def _restore_generate_all_state(self):
        """恢复一键生成按钮状态"""
        try:
            if not self._generate_all_btn_stack:
                return

            s = self._styler

            if self._generate_all_progress_label:
                self._generate_all_progress_label.setStyleSheet(f"""
                    font-family: {s.ui_font};
                    font-size: {sp(11)}px;
                    color: {s.accent_color};
                    font-weight: 500;
                """)
                self._generate_all_progress_label.setText("生成中 0/0")

            self._generate_all_btn_stack.setCurrentIndex(0)
        except RuntimeError:
            # 组件已被删除，忽略更新
            pass
