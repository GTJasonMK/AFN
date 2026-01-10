"""
可翻转的蓝图卡片组件（优化版）

正面：故事蓝图信息（标题行 + 风格/进度行 + 概要区）
背面：主角信息（头像 + 名字 + 身份 + 同步状态 + 查看档案按钮）

设计原则：信息层次清晰，视觉舒适，交互明确
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QStackedWidget, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QPixmap
from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens
from utils.dpi_utils import dp, sp

logger = logging.getLogger(__name__)


class FlippableBlueprintCard(TransparencyAwareMixin, ThemeAwareFrame):
    """可翻转的蓝图卡片（优化版）

    正面：故事蓝图（标题 + 风格/进度 + 可滚动概要）
    背面：主角信息（头像 + 名字 + 身份 + 同步状态）

    Signals:
        viewProfileRequested: 请求查看主角档案
    """

    _transparency_component_id = "card_glass"

    viewProfileRequested = pyqtSignal()

    def __init__(self, parent=None):
        # 状态变量
        self._is_flipped = False
        self._is_animating = False

        # 组件引用 - 正面
        self.stack = None
        self.front_widget = None
        self.back_widget = None
        self.front_title_label = None
        self.portrait_mini = None
        self.flip_to_back_btn = None
        self.bp_style = None
        self.style_scroll = None
        self.progress_label = None
        self.bp_summary_full = None
        self.summary_scroll = None

        # 组件引用 - 背面
        self.back_title_label = None
        self.portrait_label = None
        self.portrait_name_label = None
        self.identity_label = None
        self.sync_status_label = None
        self.view_profile_btn = None
        self.back_flip_btn = None

        # 数据
        self._portrait_pixmap = None
        self._protagonist_name = "主角"
        self._protagonist_identity = ""
        self._full_summary = ""
        self._completed_chapters = 0
        self._total_chapters = 0
        self._synced_chapter = 0

        super().__init__(parent)
        self._init_transparency_state()
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("flippable_blueprint_card")
        # 设置固定高度保证正反面切换时高度一致
        card_height = dp(140)
        self.setFixedHeight(card_height)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setObjectName("card_stack")
        self.stack.setFixedHeight(card_height)

        self.front_widget = self._create_front_side()
        self.stack.addWidget(self.front_widget)

        self.back_widget = self._create_back_side()
        self.stack.addWidget(self.back_widget)

        main_layout.addWidget(self.stack)

    def _create_front_side(self) -> QFrame:
        """创建正面：蓝图信息（简洁布局）"""
        front = QFrame()
        front.setObjectName("front_side")

        layout = QVBoxLayout(front)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(8))

        # === 第一行：标题 + 小头像 + 翻转按钮 ===
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        # 蓝图图标和标题
        self.front_title_label = QLabel("故事蓝图")
        self.front_title_label.setObjectName("front_title")
        header.addWidget(self.front_title_label)

        header.addStretch()

        # 小头像（点击翻转）
        self.portrait_mini = QLabel()
        self.portrait_mini.setObjectName("portrait_mini")
        self.portrait_mini.setFixedSize(dp(28), dp(28))
        self.portrait_mini.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_mini.setText("?")
        self.portrait_mini.setCursor(Qt.CursorShape.PointingHandCursor)
        self.portrait_mini.setToolTip("点击查看主角")
        self.portrait_mini.mousePressEvent = lambda e: self._on_flip_clicked()
        header.addWidget(self.portrait_mini)

        # 翻转按钮
        self.flip_to_back_btn = QPushButton(">>")
        self.flip_to_back_btn.setObjectName("flip_to_back_btn")
        self.flip_to_back_btn.setToolTip("查看主角信息")
        self.flip_to_back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.flip_to_back_btn.setFixedSize(dp(28), dp(28))
        self.flip_to_back_btn.clicked.connect(self._on_flip_clicked)
        header.addWidget(self.flip_to_back_btn)

        layout.addLayout(header)

        # === 第二行：风格（可横向滚动） + 进度 ===
        info_row = QHBoxLayout()
        info_row.setSpacing(dp(8))

        # 风格区域使用横向滚动
        self.style_scroll = QScrollArea()
        self.style_scroll.setObjectName("style_scroll")
        self.style_scroll.setWidgetResizable(True)
        self.style_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.style_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.style_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.style_scroll.setFixedHeight(dp(22))
        self.style_scroll.setMinimumWidth(dp(120))  # 最小宽度

        self.bp_style = QLabel("未设定")
        self.bp_style.setObjectName("bp_style")
        self.style_scroll.setWidget(self.bp_style)

        info_row.addWidget(self.style_scroll, stretch=1)  # 允许拉伸填充空间

        # 进度标签
        self.progress_label = QLabel("0/0 章")
        self.progress_label.setObjectName("progress_label")
        info_row.addWidget(self.progress_label)

        layout.addLayout(info_row)

        # === 第三行：概要区域（可滚动） ===
        self.summary_scroll = QScrollArea()
        self.summary_scroll.setObjectName("summary_scroll")
        self.summary_scroll.setWidgetResizable(True)
        self.summary_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.summary_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.summary_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.summary_scroll.setMaximumHeight(dp(70))

        self.bp_summary_full = QLabel("暂无概要")
        self.bp_summary_full.setObjectName("bp_summary_full")
        self.bp_summary_full.setWordWrap(True)
        self.bp_summary_full.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.bp_summary_full.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.summary_scroll.setWidget(self.bp_summary_full)

        layout.addWidget(self.summary_scroll, stretch=1)

        return front

    def _create_back_side(self) -> QFrame:
        """创建背面：主角信息（优化布局）"""
        back = QFrame()
        back.setObjectName("back_side")

        layout = QVBoxLayout(back)
        layout.setContentsMargins(dp(12), dp(10), dp(12), dp(10))
        layout.setSpacing(dp(6))

        # === 第一行：标题 + 返回按钮 ===
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        self.back_title_label = QLabel("主角档案")
        self.back_title_label.setObjectName("back_title")
        header.addWidget(self.back_title_label)

        header.addStretch()

        # 返回按钮 - 与正面翻转按钮位置对齐
        self.back_flip_btn = QPushButton("<<")
        self.back_flip_btn.setObjectName("back_flip_btn")
        self.back_flip_btn.setToolTip("返回蓝图")
        self.back_flip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_flip_btn.setFixedSize(dp(28), dp(28))
        self.back_flip_btn.clicked.connect(self._on_flip_clicked)
        header.addWidget(self.back_flip_btn)

        layout.addLayout(header)

        # === 第二行：大立绘 + 信息区 ===
        content_row = QHBoxLayout()
        content_row.setSpacing(dp(2))  # 减少间距，靠紧一点

        # 立绘图片 - 放大尺寸
        self.portrait_label = QLabel()
        self.portrait_label.setObjectName("portrait_label")
        self.portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_label.setFixedSize(dp(75), dp(75))
        self.portrait_label.setText("?")
        content_row.addWidget(self.portrait_label, alignment=Qt.AlignmentFlag.AlignBottom)

        # 右侧信息区 - 底部对齐
        info_layout = QVBoxLayout()
        info_layout.setSpacing(dp(2))
        info_layout.setContentsMargins(0, 0, 0, 0)

        # 先添加弹性空间，将内容推到底部
        info_layout.addStretch()

        # 角色名称
        self.portrait_name_label = QLabel("主角")
        self.portrait_name_label.setObjectName("portrait_name_label")
        info_layout.addWidget(self.portrait_name_label)

        # 身份标签
        self.identity_label = QLabel("")
        self.identity_label.setObjectName("identity_label")
        info_layout.addWidget(self.identity_label)

        # 同步状态
        self.sync_status_label = QLabel("尚未创建档案")
        self.sync_status_label.setObjectName("sync_status_label")
        info_layout.addWidget(self.sync_status_label)

        # 查看档案按钮 - 放在同步状态下面
        self.view_profile_btn = QPushButton("查看档案")
        self.view_profile_btn.setObjectName("view_profile_btn")
        self.view_profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_profile_btn.setFixedHeight(dp(30))
        self.view_profile_btn.setFixedWidth(dp(85))
        self.view_profile_btn.clicked.connect(self.viewProfileRequested.emit)
        info_layout.addWidget(self.view_profile_btn)

        content_row.addLayout(info_layout, stretch=1)

        layout.addLayout(content_row)

        return back

    def _apply_theme(self):
        """应用主题样式"""
        self._apply_transparency()

        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()
        is_dark = theme_manager.is_dark_mode()
        overlay_rgb = "0, 0, 0" if is_dark else "255, 255, 255"

        # 文字颜色
        if self._transparency_enabled:
            gradient_text_color = theme_manager.TEXT_PRIMARY
            secondary_text_color = theme_manager.TEXT_SECONDARY
        elif is_dark:
            gradient_text_color = theme_manager.TEXT_PRIMARY
            secondary_text_color = theme_manager.TEXT_SECONDARY
        else:
            gradient_text_color = theme_manager.BUTTON_TEXT
            secondary_text_color = f"rgba(255, 255, 255, 0.8)"

        # 透明度参数
        if self._transparency_enabled:
            base_alpha = self._current_opacity * 0.3
            hover_alpha = self._current_opacity * 0.45
            pressed_alpha = self._current_opacity * 0.2
            container_alpha = self._current_opacity * 0.15
            border_alpha = self._current_opacity * 0.4
        else:
            base_alpha = 0.2
            hover_alpha = 0.35
            pressed_alpha = 0.15
            container_alpha = 0.1
            border_alpha = 0.5

        # 渐变背景
        gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 135)
        back_gradient = ModernEffects.linear_gradient(theme_manager.PRIMARY_GRADIENT, 225)

        # 正面背景
        if self.front_widget:
            self.front_widget.setStyleSheet(f"""
                QFrame#front_side {{
                    background: {gradient};
                    border-radius: {theme_manager.RADIUS_MD};
                    border: none;
                }}
            """)
            if self._transparency_enabled:
                self._make_widget_transparent(self.front_widget)

        # 背面背景
        if self.back_widget:
            self.back_widget.setStyleSheet(f"""
                QFrame#back_side {{
                    background: {back_gradient};
                    border-radius: {theme_manager.RADIUS_MD};
                    border: none;
                }}
            """)
            if self._transparency_enabled:
                self._make_widget_transparent(self.back_widget)

        # 正面标题
        if self.front_title_label:
            self.front_title_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {gradient_text_color};
            """)

        # 背面标题
        if self.back_title_label:
            self.back_title_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {gradient_text_color};
            """)

        # 风格标签
        if self.bp_style:
            self.bp_style.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                color: {gradient_text_color};
            """)

        # 风格滚动区域
        if self.style_scroll:
            self.style_scroll.setStyleSheet(f"""
                QScrollArea#style_scroll {{
                    background-color: transparent;
                    border: none;
                }}
                QScrollArea#style_scroll QScrollBar:horizontal {{
                    height: {dp(3)}px;
                    background: transparent;
                }}
                QScrollArea#style_scroll QScrollBar::handle:horizontal {{
                    background: rgba({overlay_rgb}, 0.3);
                    border-radius: {dp(1)}px;
                }}
            """)

        # 进度标签
        if self.progress_label:
            self.progress_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {secondary_text_color};
            """)

        # 小头像
        if self.portrait_mini:
            if not self._portrait_pixmap:
                self.portrait_mini.setStyleSheet(f"""
                    QLabel#portrait_mini {{
                        background-color: rgba({overlay_rgb}, {base_alpha});
                        border: 1px dashed rgba({overlay_rgb}, {border_alpha});
                        border-radius: {dp(16)}px;
                        font-family: {ui_font};
                        color: {gradient_text_color};
                        font-size: {sp(14)}px;
                    }}
                """)
            else:
                self.portrait_mini.setStyleSheet(f"""
                    QLabel#portrait_mini {{
                        background-color: transparent;
                        border: none;
                        border-radius: {dp(16)}px;
                    }}
                """)

        # 概要滚动区域
        if self.summary_scroll:
            self.summary_scroll.setStyleSheet(f"""
                QScrollArea#summary_scroll {{
                    background-color: rgba({overlay_rgb}, {container_alpha});
                    border-radius: {theme_manager.RADIUS_SM};
                    border: none;
                }}
                QScrollArea#summary_scroll QScrollBar:vertical {{
                    width: {dp(4)}px;
                    background: transparent;
                }}
                QScrollArea#summary_scroll QScrollBar::handle:vertical {{
                    background: rgba({overlay_rgb}, 0.3);
                    border-radius: {dp(2)}px;
                }}
            """)

        # 概要文本
        if self.bp_summary_full:
            self.bp_summary_full.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {serif_font};
                font-size: {sp(11)}px;
                color: {gradient_text_color};
                padding: {dp(4)}px;
            """)

        # 按钮样式
        small_btn_style = f"""
            QPushButton {{
                background-color: rgba({overlay_rgb}, {base_alpha});
                color: {gradient_text_color};
                border: none;
                border-radius: {dp(14)}px;
                font-size: {sp(11)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba({overlay_rgb}, {hover_alpha});
            }}
            QPushButton:pressed {{
                background-color: rgba({overlay_rgb}, {pressed_alpha});
            }}
        """

        if self.flip_to_back_btn:
            self.flip_to_back_btn.setStyleSheet(small_btn_style)
        if self.back_flip_btn:
            self.back_flip_btn.setStyleSheet(small_btn_style)

        # 背面立绘
        if self.portrait_label:
            if not self._portrait_pixmap:
                self.portrait_label.setStyleSheet(f"""
                    QLabel#portrait_label {{
                        background-color: rgba({overlay_rgb}, {container_alpha + 0.05});
                        border: 1px dashed rgba({overlay_rgb}, {border_alpha - 0.1});
                        border-radius: {dp(38)}px;
                        font-family: {ui_font};
                        color: {gradient_text_color};
                        font-size: {sp(24)}px;
                    }}
                """)
            else:
                self.portrait_label.setStyleSheet(f"""
                    QLabel#portrait_label {{
                        background-color: transparent;
                        border: none;
                        border-radius: {dp(38)}px;
                    }}
                """)

        # 角色名称
        if self.portrait_name_label:
            self.portrait_name_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(14)}px;
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {gradient_text_color};
            """)

        # 身份标签
        if self.identity_label:
            self.identity_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {secondary_text_color};
            """)

        # 同步状态
        if self.sync_status_label:
            self.sync_status_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(10)}px;
                color: {secondary_text_color};
            """)

        # 查看档案按钮
        if self.view_profile_btn:
            self.view_profile_btn.setStyleSheet(f"""
                QPushButton#view_profile_btn {{
                    background-color: rgba({overlay_rgb}, {base_alpha});
                    color: {gradient_text_color};
                    border: 1px solid rgba({overlay_rgb}, {border_alpha});
                    border-radius: {theme_manager.RADIUS_SM};
                    font-family: {ui_font};
                    font-size: {sp(12)}px;
                    font-weight: 600;
                    padding: {dp(4)}px {dp(14)}px;
                }}
                QPushButton#view_profile_btn:hover {{
                    background-color: rgba({overlay_rgb}, {hover_alpha});
                }}
                QPushButton#view_profile_btn:pressed {{
                    background-color: rgba({overlay_rgb}, {pressed_alpha});
                }}
            """)

    def _on_flip_clicked(self):
        """翻转按钮点击"""
        if self._is_animating:
            return

        self._is_animating = True
        self._is_flipped = not self._is_flipped

        if self._is_flipped:
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(0)

        QTimer.singleShot(150, self._on_animation_finished)

    def _on_animation_finished(self):
        """动画完成"""
        self._is_animating = False

    # ==================== 公共方法 ====================

    def setStyle(self, style: str):
        """设置风格文本"""
        if self.bp_style:
            display_style = style or "未设定"
            # 不截断，完整显示风格
            self.bp_style.setText(display_style)

    def setSummary(self, summary: str):
        """设置概要文本"""
        self._full_summary = summary or "暂无概要"

        # 设置到滚动区域中的标签
        if self.bp_summary_full:
            self.bp_summary_full.setText(self._full_summary)

    def setProgress(self, completed: int, total: int):
        """设置章节进度

        Args:
            completed: 已完成章节数
            total: 总章节数
        """
        self._completed_chapters = completed
        self._total_chapters = total

        if self.progress_label:
            if total > 0:
                self.progress_label.setText(f"进度: {completed}/{total} 章")
            else:
                self.progress_label.setText("进度: 0/0 章")

    def setPortrait(self, pixmap: QPixmap, name: str = "主角", identity: str = ""):
        """设置主角立绘

        Args:
            pixmap: 立绘图片
            name: 角色名称
            identity: 角色身份（可选）
        """
        self._portrait_pixmap = pixmap
        self._protagonist_name = name
        self._protagonist_identity = identity

        if pixmap and not pixmap.isNull():
            # 创建背面头像（75x75）
            if self.portrait_label:
                size = dp(75)
                rounded = self._create_rounded_pixmap(pixmap, size)
                self.portrait_label.setPixmap(rounded)
                self.portrait_label.setText("")
                self.portrait_label.setStyleSheet(f"""
                    QLabel#portrait_label {{
                        background-color: transparent;
                        border: none;
                    }}
                """)

            # 创建正面小头像（32x32）
            if self.portrait_mini:
                mini_size = dp(32)
                mini_rounded = self._create_rounded_pixmap(pixmap, mini_size)
                self.portrait_mini.setPixmap(mini_rounded)
                self.portrait_mini.setText("")
                self.portrait_mini.setStyleSheet(f"""
                    QLabel#portrait_mini {{
                        background-color: transparent;
                        border: none;
                    }}
                """)

        # 更新名称
        if self.portrait_name_label:
            self.portrait_name_label.setText(self._elide_name(name, 8))
            self.portrait_name_label.setToolTip(name)

        # 更新身份
        if self.identity_label:
            if identity:
                self.identity_label.setText(identity)
                self.identity_label.setVisible(True)
            else:
                self.identity_label.setVisible(False)

    def setSyncStatus(self, synced_chapter: int):
        """设置同步状态 - 简化逻辑，直接根据同步章节数判断

        Args:
            synced_chapter: 已同步至的章节号，-1表示没有档案
        """
        self._synced_chapter = synced_chapter

        if self.sync_status_label:
            if synced_chapter < 0:
                # -1 表示没有创建档案
                self.sync_status_label.setText("尚未创建档案")
            elif synced_chapter == 0:
                # 0 表示有档案但未同步
                self.sync_status_label.setText("尚未同步")
            else:
                # > 0 表示已同步到某章
                self.sync_status_label.setText(f"已同步至第 {synced_chapter} 章")

    def setPortraitPlaceholder(self, name: str = "主角", identity: str = ""):
        """设置立绘占位符"""
        self._portrait_pixmap = None
        self._protagonist_name = name
        self._protagonist_identity = identity

        if self.portrait_label:
            self.portrait_label.clear()
            self.portrait_label.setText("?")

        if self.portrait_mini:
            self.portrait_mini.clear()
            self.portrait_mini.setText("?")

        if self.portrait_name_label:
            self.portrait_name_label.setText(self._elide_name(name, 8))
            self.portrait_name_label.setToolTip(name)

        if self.identity_label:
            if identity:
                self.identity_label.setText(identity)
                self.identity_label.setVisible(True)
            else:
                self.identity_label.setVisible(False)

        self._apply_theme()

    def _create_rounded_pixmap(self, pixmap: QPixmap, size: int) -> QPixmap:
        """创建圆形裁剪的图片"""
        from PyQt6.QtGui import QPainter, QPainterPath
        from PyQt6.QtCore import QRectF

        scaled = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation
        )

        # 居中裁剪
        if scaled.width() > size or scaled.height() > size:
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            scaled = scaled.copy(x, y, size, size)

        # 创建圆形遮罩
        rounded = QPixmap(size, size)
        rounded.fill(Qt.GlobalColor.transparent)

        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addEllipse(QRectF(0, 0, size, size))
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, scaled)
        painter.end()

        return rounded

    def _elide_name(self, name: str, max_chars: int = 6) -> str:
        """省略过长的角色名称

        Args:
            name: 角色名称
            max_chars: 最大显示字符数（中文字符）

        Returns:
            处理后的名称，过长时显示省略号
        """
        if not name:
            return "主角"
        if len(name) <= max_chars:
            return name
        return name[:max_chars] + "..."

    def flipToFront(self):
        """翻转到正面"""
        if self._is_flipped and not self._is_animating:
            self._on_flip_clicked()

    def flipToBack(self):
        """翻转到背面"""
        if not self._is_flipped and not self._is_animating:
            self._on_flip_clicked()

    def isFlipped(self) -> bool:
        """是否处于翻转状态"""
        return self._is_flipped
