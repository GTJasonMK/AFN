"""
可翻转的蓝图卡片组件（紧凑版）

正面：故事蓝图信息（风格 + 概要预览，可展开）
背面：主角立绘 + 查看档案按钮

设计原则：默认紧凑，按需展开
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QWidget, QStackedWidget, QSizePolicy
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
    """可翻转的蓝图卡片（紧凑版）

    正面：故事蓝图（风格 + 概要预览）
    背面：主角立绘 + 查看档案按钮

    默认收起状态仅占用一行，点击展开查看完整概要。
    使用 TransparencyAwareMixin 提供透明度控制能力。

    Signals:
        viewProfileRequested: 请求查看主角档案
        summaryExpandToggled: 概要展开/收起切换
    """

    # 透明度组件标识符 - 使用玻璃卡片类型
    _transparency_component_id = "card_glass"

    viewProfileRequested = pyqtSignal()
    summaryExpandToggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        # 状态变量
        self._is_flipped = False
        self._is_animating = False
        self._summary_expanded = False

        # 组件引用
        self.stack = None
        self.front_widget = None
        self.back_widget = None
        self.flip_btn = None
        self.bp_style = None
        self.bp_summary_preview = None
        self.bp_summary_full = None
        self.expand_btn = None
        self.summary_container = None
        self.portrait_label = None
        self.portrait_mini = None  # 正面的小头像
        self.portrait_name_label = None
        self.view_profile_btn = None
        self.back_flip_btn = None

        # 立绘数据
        self._portrait_pixmap = None
        self._protagonist_name = "主角"
        self._full_summary = ""

        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setObjectName("flippable_blueprint_card")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 使用QStackedWidget管理正反面
        self.stack = QStackedWidget()
        self.stack.setObjectName("card_stack")

        # 创建正面（蓝图信息）
        self.front_widget = self._create_front_side()
        self.stack.addWidget(self.front_widget)

        # 创建背面（主角立绘）
        self.back_widget = self._create_back_side()
        self.stack.addWidget(self.back_widget)

        main_layout.addWidget(self.stack)

    def _create_front_side(self) -> QFrame:
        """创建正面：蓝图信息（紧凑版）"""
        front = QFrame()
        front.setObjectName("front_side")

        layout = QVBoxLayout(front)
        layout.setContentsMargins(dp(10), dp(8), dp(10), dp(8))
        layout.setSpacing(dp(6))

        # 标题行：小头像 + 图标 + 风格 + 概要预览 + 展开按钮 + 翻转按钮
        header = QHBoxLayout()
        header.setSpacing(dp(8))

        # 小头像（点击翻转）
        self.portrait_mini = QLabel()
        self.portrait_mini.setObjectName("portrait_mini")
        self.portrait_mini.setFixedSize(dp(28), dp(28))
        self.portrait_mini.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_mini.setText("👤")
        self.portrait_mini.setCursor(Qt.CursorShape.PointingHandCursor)
        self.portrait_mini.setToolTip("点击查看主角")
        self.portrait_mini.mousePressEvent = lambda e: self._on_flip_clicked()
        header.addWidget(self.portrait_mini)

        # 分隔符
        sep1 = QLabel("|")
        sep1.setObjectName("separator")
        header.addWidget(sep1)

        # 风格标签
        self.bp_style = QLabel("未设定")
        self.bp_style.setObjectName("bp_style")
        header.addWidget(self.bp_style)

        # 分隔符
        separator = QLabel("|")
        separator.setObjectName("separator")
        header.addWidget(separator)

        # 概要预览（单行，省略号）
        self.bp_summary_preview = QLabel("暂无概要")
        self.bp_summary_preview.setObjectName("bp_summary_preview")
        self.bp_summary_preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.bp_summary_preview.setWordWrap(False)
        header.addWidget(self.bp_summary_preview, stretch=1)

        # 展开/收起按钮
        self.expand_btn = QPushButton("...")
        self.expand_btn.setObjectName("expand_btn")
        self.expand_btn.setToolTip("展开/收起概要")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.expand_btn.setFixedSize(dp(24), dp(24))
        self.expand_btn.clicked.connect(self._toggle_summary_expand)
        header.addWidget(self.expand_btn)

        layout.addLayout(header)

        # 概要展开容器（默认隐藏）
        self.summary_container = QFrame()
        self.summary_container.setObjectName("summary_container")
        self.summary_container.setVisible(False)

        summary_layout = QVBoxLayout(self.summary_container)
        summary_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        summary_layout.setSpacing(0)

        self.bp_summary_full = QLabel("暂无概要")
        self.bp_summary_full.setObjectName("bp_summary_full")
        self.bp_summary_full.setWordWrap(True)
        self.bp_summary_full.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        summary_layout.addWidget(self.bp_summary_full)

        layout.addWidget(self.summary_container)

        return front

    def _create_back_side(self) -> QFrame:
        """创建背面：主角立绘（紧凑版）"""
        back = QFrame()
        back.setObjectName("back_side")

        layout = QHBoxLayout(back)
        layout.setContentsMargins(dp(10), dp(8), dp(10), dp(8))
        layout.setSpacing(dp(10))

        # 立绘图片（小尺寸）
        self.portrait_label = QLabel()
        self.portrait_label.setObjectName("portrait_label")
        self.portrait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.portrait_label.setFixedSize(dp(48), dp(48))
        self.portrait_label.setText("👤")
        layout.addWidget(self.portrait_label)

        # 角色名称
        self.portrait_name_label = QLabel("主角")
        self.portrait_name_label.setObjectName("portrait_name_label")
        self.portrait_name_label.setMinimumWidth(dp(40))  # 最小宽度保证至少显示一些内容
        self.portrait_name_label.setMaximumWidth(dp(80))  # 限制最大宽度避免挤压按钮
        self.portrait_name_label.setToolTip("主角")  # 完整名称通过tooltip显示
        layout.addWidget(self.portrait_name_label)

        layout.addStretch()

        # 查看档案按钮
        self.view_profile_btn = QPushButton("查看档案")
        self.view_profile_btn.setObjectName("view_profile_btn")
        self.view_profile_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_profile_btn.setFixedHeight(dp(28))
        self.view_profile_btn.clicked.connect(self.viewProfileRequested.emit)
        layout.addWidget(self.view_profile_btn)

        # 翻转回正面按钮
        self.back_flip_btn = QPushButton("◐")
        self.back_flip_btn.setObjectName("back_flip_btn")
        self.back_flip_btn.setToolTip("返回蓝图")
        self.back_flip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_flip_btn.setFixedSize(dp(24), dp(24))
        self.back_flip_btn.clicked.connect(self._on_flip_clicked)
        layout.addWidget(self.back_flip_btn)

        return back

    def _apply_theme(self):
        """应用主题样式 - 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        # 判断渐变背景的明暗
        # 亮色主题：渐变是深色赭石色，覆盖层使用白色，文字用白色
        # 深色主题：渐变是亮色琥珀色，覆盖层使用深色，文字用深色
        is_dark = theme_manager.is_dark_mode()
        overlay_rgb = "0, 0, 0" if is_dark else "255, 255, 255"

        # 渐变背景上的文字颜色 - 根据主题正确选择
        # 透明模式下使用主文字色保证可读性
        if self._transparency_enabled:
            gradient_text_color = theme_manager.TEXT_PRIMARY
        elif is_dark:
            # 深色主题：渐变是亮色的，用深色文字
            gradient_text_color = theme_manager.TEXT_PRIMARY
        else:
            # 亮色主题：渐变是深色的，用白色文字
            gradient_text_color = theme_manager.BUTTON_TEXT

        # 计算透明度调整后的alpha值
        # 当透明模式开启时，降低覆盖层的透明度
        if self._transparency_enabled:
            base_alpha = self._current_opacity * 0.3  # 基础半透明
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

        # 正面背景 - 渐变
        gradient = ModernEffects.linear_gradient(
            theme_manager.PRIMARY_GRADIENT,
            135
        )

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

        # 背面背景 - 渐变
        back_gradient = ModernEffects.linear_gradient(
            theme_manager.PRIMARY_GRADIENT,
            225
        )

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

        # 蓝图图标
        if bp_icon := self.findChild(QLabel, "bp_icon"):
            bp_icon.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-size: {sp(16)}px;
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 分隔符
        if separators := self.findChildren(QLabel, "separator"):
            sep_alpha = border_alpha if self._transparency_enabled else 0.5
            for separator in separators:
                separator.setStyleSheet(f"""
                    background: transparent;
                    border: none;
                    color: rgba({overlay_rgb}, {sep_alpha});
                    font-size: {sp(12)}px;
                """)

        # 小头像（正面）
        if self.portrait_mini:
            if not self._portrait_pixmap:
                self.portrait_mini.setStyleSheet(f"""
                    QLabel#portrait_mini {{
                        background-color: rgba({overlay_rgb}, {base_alpha});
                        border: 1px dashed rgba({overlay_rgb}, {border_alpha});
                        border-radius: {dp(14)}px;
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
                        border-radius: {dp(14)}px;
                    }}
                """)

        # 风格标签
        if self.bp_style:
            self.bp_style.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 概要预览
        if self.bp_summary_preview:
            text_alpha = 0.85 if not self._transparency_enabled else self._current_opacity * 0.9
            self.bp_summary_preview.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {serif_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: rgba({overlay_rgb}, {text_alpha});
            """)

        # 小按钮样式
        small_btn_style = f"""
            QPushButton {{
                background-color: rgba({overlay_rgb}, {base_alpha});
                color: {gradient_text_color};
                border: none;
                border-radius: {dp(12)}px;
                font-size: {sp(12)}px;
            }}
            QPushButton:hover {{
                background-color: rgba({overlay_rgb}, {hover_alpha});
            }}
            QPushButton:pressed {{
                background-color: rgba({overlay_rgb}, {pressed_alpha});
            }}
        """

        if self.flip_btn:
            self.flip_btn.setStyleSheet(small_btn_style)
        if self.expand_btn:
            self.expand_btn.setStyleSheet(small_btn_style)
        if self.back_flip_btn:
            self.back_flip_btn.setStyleSheet(small_btn_style)

        # 概要展开容器
        if self.summary_container:
            self.summary_container.setStyleSheet(f"""
                QFrame#summary_container {{
                    background-color: rgba({overlay_rgb}, {container_alpha});
                    border-radius: {theme_manager.RADIUS_SM};
                }}
            """)

        # 完整概要
        if self.bp_summary_full:
            self.bp_summary_full.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {serif_font};
                font-size: {theme_manager.FONT_SIZE_SM};
                color: {theme_manager.BUTTON_TEXT};
                line-height: 1.4;
            """)

        # 立绘图片
        if self.portrait_label:
            if not self._portrait_pixmap:
                self.portrait_label.setStyleSheet(f"""
                    QLabel#portrait_label {{
                        background-color: rgba({overlay_rgb}, {container_alpha + 0.05});
                        border: 1px dashed rgba({overlay_rgb}, {border_alpha - 0.1});
                        border-radius: {dp(24)}px;
                        font-family: {ui_font};
                        color: {gradient_text_color};
                        font-size: {sp(20)}px;
                    }}
                """)
            else:
                self.portrait_label.setStyleSheet(f"""
                    QLabel#portrait_label {{
                        background-color: transparent;
                        border: none;
                        border-radius: {dp(24)}px;
                    }}
                """)

        # 角色名称 - 使用根据主题和透明模式正确选择的文字颜色
        if self.portrait_name_label:
            self.portrait_name_label.setStyleSheet(f"""
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {gradient_text_color};
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
                    font-size: {theme_manager.FONT_SIZE_XS};
                    padding: {dp(4)}px {dp(12)}px;
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

    def _toggle_summary_expand(self):
        """切换故事概要的展开/收起状态"""
        self._summary_expanded = not self._summary_expanded

        if self._summary_expanded:
            self.summary_container.setVisible(True)
            self.expand_btn.setText("▲")
            self.expand_btn.setToolTip("收起概要")
        else:
            self.summary_container.setVisible(False)
            self.expand_btn.setText("...")
            self.expand_btn.setToolTip("展开概要")

        self.summaryExpandToggled.emit(self._summary_expanded)

    # ==================== 公共方法 ====================

    def setStyle(self, style: str):
        """设置风格文本"""
        if self.bp_style:
            # 截断过长的风格文本
            display_style = style or "未设定"
            if len(display_style) > 8:
                display_style = display_style[:8] + "..."
            self.bp_style.setText(display_style)

    def setSummary(self, summary: str):
        """设置概要文本"""
        self._full_summary = summary or "暂无概要"

        # 预览版本：截取前30个字符
        if self.bp_summary_preview:
            preview = self._full_summary
            if len(preview) > 30:
                preview = preview[:30] + "..."
            self.bp_summary_preview.setText(preview)

        # 完整版本
        if self.bp_summary_full:
            self.bp_summary_full.setText(self._full_summary)

    def setPortrait(self, pixmap: QPixmap, name: str = "主角"):
        """设置主角立绘"""
        self._portrait_pixmap = pixmap
        self._protagonist_name = name

        if pixmap and not pixmap.isNull():
            # 创建背面大头像（48x48）
            if self.portrait_label:
                size = dp(48)
                rounded = self._create_rounded_pixmap(pixmap, size)
                self.portrait_label.setPixmap(rounded)
                self.portrait_label.setText("")
                self.portrait_label.setStyleSheet(f"""
                    QLabel#portrait_label {{
                        background-color: transparent;
                        border: none;
                    }}
                """)

            # 创建正面小头像（28x28）
            if self.portrait_mini:
                mini_size = dp(28)
                mini_rounded = self._create_rounded_pixmap(pixmap, mini_size)
                self.portrait_mini.setPixmap(mini_rounded)
                self.portrait_mini.setText("")
                self.portrait_mini.setStyleSheet(f"""
                    QLabel#portrait_mini {{
                        background-color: transparent;
                        border: none;
                    }}
                """)

        if self.portrait_name_label:
            self.portrait_name_label.setText(self._elide_name(name))
            self.portrait_name_label.setToolTip(name)  # 完整名称显示在tooltip

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

    def setPortraitPlaceholder(self, name: str = "主角"):
        """设置立绘占位符"""
        self._portrait_pixmap = None
        self._protagonist_name = name

        if self.portrait_label:
            self.portrait_label.clear()
            self.portrait_label.setText("👤")

        if self.portrait_mini:
            self.portrait_mini.clear()
            self.portrait_mini.setText("👤")

        if self.portrait_name_label:
            self.portrait_name_label.setText(self._elide_name(name))
            self.portrait_name_label.setToolTip(name)  # 完整名称显示在tooltip

        self._apply_theme()

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

    def isSummaryExpanded(self) -> bool:
        """概要是否展开"""
        return self._summary_expanded
