"""
项目列表窗口 - 现代美学设计

设计原则：
- 玻璃态卡片效果
- 渐变色彩系统
- SVG图标系统
- 流畅动画和过渡效果
"""

import logging
from collections import deque
from PyQt6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QScrollArea, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt, QRect, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QColor
from api.client import ArborisAPIClient
from pages.base_page import BasePage
from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes.svg_icons import SVGIcons
from themes import ButtonStyles
from utils.dpi_utils import dpi_helper, dp, sp
from utils.formatters import get_project_status_text
from utils.message_service import MessageService, confirm

logger = logging.getLogger(__name__)


class ProjectCard(ThemeAwareFrame):
    """现代项目卡片 - 玻璃态设计

    特点：
    - 玻璃态卡片效果
    - 渐变图标背景
    - 流畅hover动画
    - 优雅阴影效果

    使用 ThemeAwareFrame 基类避免信号重复连接
    """

    viewDetailsClicked = pyqtSignal(str)
    continueWritingClicked = pyqtSignal(str)
    deleteClicked = pyqtSignal(str)

    def __init__(self, project_data, parent=None):
        self.project_data = project_data
        self.is_hovering = False
        self.original_y = None  # 记录原始y坐标用于动画

        # 初始化动画对象
        self.opacity_animation = None
        self.move_animation = None

        # 预计算的StyleSheet缓存（在update_theme中生成）
        self._stylesheet_normal = ""
        self._stylesheet_hover = ""

        # 保存组件引用（在 _create_ui_structure 中创建）
        self.icon_container = None
        self.icon_label = None
        self.title_label = None
        self.status_label = None  # 状态标签
        self.time_label = None
        self.progress_label = None
        self.percent_label = None
        self.progress_bar_bg = None
        self.progress_bar_fill = None
        self.genre_tag = None
        self.chapter_tag = None
        self.buttons_container = None
        self.buttons_opacity = None
        self.view_btn = None
        self.delete_btn = None
        self.continue_btn = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(dp(200))
        self.setMaximumWidth(dp(380))  # 限制最大宽度，防止卡片过宽

        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 顶部：图标 + 标题区域
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(16))

        # 渐变图标容器
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(dp(40), dp(40))
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 使用SVG图标
        self.icon_label = QLabel()
        icon_svg = SVGIcons.book(dp(24), "white")
        self.icon_label.setText(icon_svg)
        self.icon_label.setTextFormat(Qt.TextFormat.RichText)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_label)

        header_layout.addWidget(self.icon_container, alignment=Qt.AlignmentFlag.AlignTop)

        # 标题 + 元数据
        title_container = QWidget()
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)

        # 标题（支持换行，限制2行）
        self.title_label = QLabel(self.project_data.get('title', '未命名项目'))
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(dp(48))  # 约2行高度
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        title_layout.addWidget(self.title_label)

        # 状态标签
        status = self.project_data.get('status', 'draft')
        self.status_label = QLabel(get_project_status_text(status))
        title_layout.addWidget(self.status_label)

        # 最后编辑时间
        updated_at = self.project_data.get('updated_at', '')[:10] if self.project_data.get('updated_at') else '未知'
        self.time_label = QLabel(f"编辑于 {updated_at}")
        title_layout.addWidget(self.time_label)

        header_layout.addWidget(title_container, stretch=1)
        layout.addLayout(header_layout)

        # 进度条区域
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(4)

        # 进度计算
        total_chapters = self.project_data.get('total_chapters', 0)
        completed_chapters = self.project_data.get('completed_chapters', 0)
        self.progress_percent = int((completed_chapters / total_chapters * 100) if total_chapters > 0 else 0)

        # 进度文本行（章节数 + 百分比）
        progress_text_layout = QHBoxLayout()
        progress_text_layout.setContentsMargins(0, 0, 0, 0)

        # 章节进度
        if total_chapters > 0:
            self.progress_label = QLabel(f"{completed_chapters}/{total_chapters} 章")
        else:
            self.progress_label = QLabel("暂无章节")
        progress_text_layout.addWidget(self.progress_label)

        progress_text_layout.addStretch()

        # 百分比
        self.percent_label = QLabel(f"{self.progress_percent}%")
        progress_text_layout.addWidget(self.percent_label)
        progress_layout.addLayout(progress_text_layout)

        # 进度条
        self.progress_bar_bg = QFrame()
        self.progress_bar_bg.setFixedHeight(6)

        self.progress_bar_fill = QFrame(self.progress_bar_bg)
        self.progress_bar_fill.setFixedHeight(6)
        self.progress_bar_fill.setFixedWidth(0)

        progress_layout.addWidget(self.progress_bar_bg)
        layout.addWidget(progress_container)

        # 类型标签
        genre = self.project_data.get('blueprint', {}).get('genre', '')
        if genre and genre != '未知类型':
            self.genre_tag = QLabel(genre)
            layout.addWidget(self.genre_tag)

        layout.addStretch()

        # 底部按钮区域（hover时显示）
        self.buttons_container = QWidget()
        buttons_layout = QHBoxLayout(self.buttons_container)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)

        # 查看详情按钮
        self.view_btn = QPushButton("查看")
        self.view_btn.setIcon(dpi_helper.create_icon(SVGIcons.eye(16, theme_manager.TEXT_PRIMARY)))
        self.view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_btn.clicked.connect(self._on_view_details_clicked)
        buttons_layout.addWidget(self.view_btn, stretch=1)

        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setIcon(dpi_helper.create_icon(SVGIcons.trash(16, theme_manager.ERROR)))
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        # 移除固定宽度限制，让按钮根据内容自动调整
        buttons_layout.addWidget(self.delete_btn)

        # 继续按钮 - 根据项目状态显示不同文本和行为
        # 只有已生成蓝图的项目才显示"继续创作"，否则显示"继续灵感模式"
        project_status = self.project_data.get('status', '')
        # 蓝图后的状态列表（这些状态表示项目已有蓝图）
        blueprint_ready_states = ['blueprint_ready', 'part_outlines_ready', 'chapter_outlines_ready', 'writing', 'completed']

        if project_status in blueprint_ready_states:
            # 已有蓝图，显示"继续创作"
            self.continue_btn = QPushButton("继续")
            self.continue_btn.setIcon(dpi_helper.create_icon(SVGIcons.play(16, theme_manager.BUTTON_TEXT)))
        else:
            # 未完成蓝图（draft或其他未知状态），显示"继续灵感"
            self.continue_btn = QPushButton("继续灵感")
            self.continue_btn.setIcon(dpi_helper.create_icon(SVGIcons.sparkles(16, theme_manager.BUTTON_TEXT)))
        
        self.continue_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # 连接到统一的槽方法，避免重复连接lambda
        self.continue_btn.clicked.connect(self._on_continue_clicked)
        buttons_layout.addWidget(self.continue_btn, stretch=1)

        layout.addWidget(self.buttons_container)

        # 设置按钮初始隐藏
        self.buttons_opacity = QGraphicsOpacityEffect(self.buttons_container)
        self.buttons_opacity.setOpacity(0)
        self.buttons_container.setGraphicsEffect(self.buttons_opacity)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        bg_color = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        icon_bg = "transparent"
        icon_color = theme_manager.book_accent_color()

        # 字体设置
        ui_font = theme_manager.ui_font()

        # 图标容器 - 简约风格
        if self.icon_container:
            self.icon_container.setStyleSheet(f"""
                QFrame {{
                    background: {icon_bg};
                    border: none;
                }}
            """)
            # 更新图标颜色
            icon_svg = SVGIcons.book(dp(24), icon_color)
            self.icon_label.setText(icon_svg)

        # 标题
        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(18)}px;
                font-weight: bold;
                color: {text_primary};
            """)

        # 状态标签
        if self.status_label:
            self.status_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                font-style: italic;
            """)

        # 时间
        if self.time_label:
            self.time_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(11)}px;
                color: {text_secondary};
            """)

        # 进度标签
        if self.progress_label:
            self.progress_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
            """)

        if self.percent_label:
            percent_color = icon_color
            self.percent_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {percent_color};
                font-weight: bold;
            """)

        # 进度条背景
        if self.progress_bar_bg:
            self.progress_bar_bg.setStyleSheet(f"""
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {dp(2)}px;
            """)

        # 进度条填充
        if self.progress_bar_fill:
            self.progress_bar_fill.setStyleSheet(f"""
                background-color: {icon_color};
                border-radius: {dp(2)}px;
            """)

        # 类型标签
        if self.genre_tag:
            self.genre_tag.setStyleSheet(f"""
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                font-size: {sp(11)}px;
            """)

        # 按钮样式 - 简约文字按钮风格
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                color: {icon_color};
                border-color: {icon_color};
                background-color: {bg_color};
            }}
        """
        if self.view_btn:
            self.view_btn.setStyleSheet(btn_style)
        if self.delete_btn:
            self.delete_btn.setStyleSheet(btn_style)
        if self.continue_btn:
            self.continue_btn.setStyleSheet(btn_style)

        # 预计算卡片样式 - 书籍封面/档案卡风格
        # 左侧增加一条装饰线模拟书脊
        spine_color = icon_color
        
        self._stylesheet_normal = f"""
            ProjectCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-left: 4px solid {spine_color};
                border-radius: {dp(2)}px; 
            }}
        """
        self._stylesheet_hover = f"""
            ProjectCard {{
                background-color: {bg_color};
                border: 1px solid {spine_color};
                border-left: 6px solid {spine_color};
                border-radius: {dp(2)}px;
            }}
        """

        # 应用当前状态的样式
        if self.is_hovering:
            self.setStyleSheet(self._stylesheet_hover)
        else:
            self.setStyleSheet(self._stylesheet_normal)

    def enterEvent(self, event):
        """鼠标进入 - 优雅动画"""
        self.is_hovering = True

        # 记录原始位置（首次记录）
        if self.original_y is None:
            self.original_y = self.geometry().y()

        # 按钮渐显 - 先停止旧动画
        if self.buttons_opacity:
            if self.opacity_animation and self.opacity_animation.state() == QPropertyAnimation.State.Running:
                self.opacity_animation.stop()

            self.opacity_animation = QPropertyAnimation(self.buttons_opacity, b"opacity")
            self.opacity_animation.setDuration(200)
            self.opacity_animation.setStartValue(0)
            self.opacity_animation.setEndValue(1)
            self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.opacity_animation.start()

        # 卡片上移 - 先停止旧动画
        if self.move_animation and self.move_animation.state() == QPropertyAnimation.State.Running:
            self.move_animation.stop()

        self.move_animation = QPropertyAnimation(self, b"geometry")
        self.move_animation.setDuration(200)
        current_geo = self.geometry()
        target_geo = QRect(
            current_geo.x(),
            self.original_y - dp(4),  # 基于原始位置上移4像素
            current_geo.width(),
            current_geo.height()
        )
        self.move_animation.setEndValue(target_geo)
        self.move_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.move_animation.start()

        # 更新样式 - 使用预计算的样式
        self.setStyleSheet(self._stylesheet_hover)

        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开 - 恢复原位"""
        self.is_hovering = False

        # 如果没有记录原始位置，直接返回
        if self.original_y is None:
            super().leaveEvent(event)
            return

        # 按钮渐隐 - 先停止旧动画
        if self.buttons_opacity:
            if self.opacity_animation and self.opacity_animation.state() == QPropertyAnimation.State.Running:
                self.opacity_animation.stop()

            self.opacity_animation = QPropertyAnimation(self.buttons_opacity, b"opacity")
            self.opacity_animation.setDuration(200)
            self.opacity_animation.setStartValue(1)
            self.opacity_animation.setEndValue(0)
            self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.opacity_animation.start()

        # 卡片恢复到原始位置 - 先停止旧动画
        if self.move_animation and self.move_animation.state() == QPropertyAnimation.State.Running:
            self.move_animation.stop()

        self.move_animation = QPropertyAnimation(self, b"geometry")
        self.move_animation.setDuration(200)
        current_geo = self.geometry()
        target_geo = QRect(
            current_geo.x(),
            self.original_y,  # 恢复到原始y坐标
            current_geo.width(),
            current_geo.height()
        )
        self.move_animation.setEndValue(target_geo)
        self.move_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.move_animation.start()

        # 恢复样式 - 使用预计算的样式
        self.setStyleSheet(self._stylesheet_normal)

        super().leaveEvent(event)

    def closeEvent(self, event):
        """卡片关闭时清理动画资源"""
        self._cleanup_animations()
        super().closeEvent(event)

    def _cleanup_animations(self):
        """清理动画对象"""
        # 停止并清理透明度动画
        if self.opacity_animation:
            if self.opacity_animation.state() == QPropertyAnimation.State.Running:
                self.opacity_animation.stop()
            self.opacity_animation.deleteLater()
            self.opacity_animation = None

        # 停止并清理移动动画
        if self.move_animation:
            if self.move_animation.state() == QPropertyAnimation.State.Running:
                self.move_animation.stop()
            self.move_animation.deleteLater()
            self.move_animation = None

    def showEvent(self, event):
        """组件显示时计算进度条宽度"""
        super().showEvent(event)
        # 等待布局完成后再计算宽度
        QTimer.singleShot(0, self._update_progress_bar_width)

    def resizeEvent(self, event):
        """窗口大小改变时重新计算进度条宽度"""
        super().resizeEvent(event)
        self._update_progress_bar_width()

    def _update_progress_bar_width(self):
        """更新进度条宽度"""
        if self.progress_bar_bg and self.progress_bar_fill:
            # 确保组件可见且有有效宽度
            if self.progress_bar_bg.isVisible() and self.progress_bar_bg.width() > 0:
                bg_width = self.progress_bar_bg.width()
                fill_width = int(bg_width * self.progress_percent / 100)
                self.progress_bar_fill.setFixedWidth(fill_width)

    def _on_continue_clicked(self):
        """继续按钮点击处理 - 根据当前状态发射对应信号"""
        project_id = self.project_data.get('id')
        if not project_id:
            return

        project_status = self.project_data.get('status', '')
        blueprint_ready_states = ['blueprint_ready', 'part_outlines_ready', 'chapter_outlines_ready', 'writing', 'completed']

        if project_status in blueprint_ready_states:
            # 已有蓝图，导航到写作台
            self.continueWritingClicked.emit(project_id)
        else:
            # 未完成蓝图，导航到灵感模式
            self.viewDetailsClicked.emit(project_id)

    def _on_view_details_clicked(self):
        """查看详情按钮点击处理"""
        project_id = self.project_data.get('id')
        if project_id:
            self.viewDetailsClicked.emit(project_id)

    def _on_delete_clicked(self):
        """删除按钮点击处理"""
        project_id = self.project_data.get('id')
        if project_id:
            self.deleteClicked.emit(project_id)

    def updateData(self, new_project_data):
        """更新卡片数据（避免重建卡片）"""
        self.project_data = new_project_data

        # 更新标题
        if self.title_label:
            self.title_label.setText(new_project_data.get('title', '未命名项目'))

        # 更新状态
        if self.status_label:
            status = new_project_data.get('status', 'draft')
            self.status_label.setText(get_project_status_text(status))

        # 更新时间
        if self.time_label:
            updated_at = new_project_data.get('updated_at', '')[:10] if new_project_data.get('updated_at') else '未知'
            self.time_label.setText(f"编辑于 {updated_at}")

        # 更新进度
        total_chapters = new_project_data.get('total_chapters', 0)
        completed_chapters = new_project_data.get('completed_chapters', 0)
        self.progress_percent = int((completed_chapters / total_chapters * 100) if total_chapters > 0 else 0)

        # 更新进度标签
        if self.progress_label:
            if total_chapters > 0:
                self.progress_label.setText(f"{completed_chapters}/{total_chapters} 章")
            else:
                self.progress_label.setText("暂无章节")

        if self.percent_label:
            self.percent_label.setText(f"{self.progress_percent}%")

        self._update_progress_bar_width()

        # 更新类型标签
        genre = new_project_data.get('blueprint', {}).get('genre', '')
        if self.genre_tag:
            self.genre_tag.setText(genre)
            self.genre_tag.setVisible(bool(genre) and genre != '未知类型')

        # 更新继续按钮文本
        if self.continue_btn:
            project_status = new_project_data.get('status', '')
            blueprint_ready_states = ['blueprint_ready', 'part_outlines_ready', 'chapter_outlines_ready', 'writing', 'completed']

            if project_status in blueprint_ready_states:
                self.continue_btn.setText("继续")
                self.continue_btn.setIcon(dpi_helper.create_icon(SVGIcons.play(16, theme_manager.BUTTON_TEXT)))
            else:
                self.continue_btn.setText("继续灵感")
                self.continue_btn.setIcon(dpi_helper.create_icon(SVGIcons.sparkles(16, theme_manager.BUTTON_TEXT)))



class CreateProjectCard(ThemeAwareFrame):
    """创建新项目卡片 - 禅意风格

    使用 ThemeAwareFrame 基类避免信号重复连接
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        # 保存组件引用
        self.plus_label = None
        self.text_label = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(dp(200))
        self.setMaximumWidth(dp(380))  # 与ProjectCard保持一致

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 加号图标
        self.plus_label = QLabel("+")
        self.plus_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.plus_label)

        # 文字
        self.text_label = QLabel("创建新项目")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_label)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        highlight_color = theme_manager.book_accent_color()

        ui_font = theme_manager.ui_font()

        # 加号样式
        if self.plus_label:
            self.plus_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(48)}px;
                color: {highlight_color};
                font-weight: 300;
            """)

        # 文字样式
        if self.text_label:
            self.text_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(14)}px;
                color: {text_secondary};
            """)

        # 虚线框样式
        self.setStyleSheet(f"""
            CreateProjectCard {{
                background-color: transparent;
                border: 2px dashed {border_color};
                border-radius: {dp(4)}px;
            }}
            CreateProjectCard:hover {{
                border-color: {highlight_color};
                background-color: rgba(0,0,0,0.02);
            }}
        """)

    def mousePressEvent(self, event):
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class NovelWorkspace(BasePage):
    """项目列表页面 - 禅意风格"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.api_client = ArborisAPIClient()
        self.projects = []
        self.card_pool = []  # 所有卡片的引用（防止被垃圾回收）
        self.available_cards = deque()  # 可用卡片队列（O(1)获取）

        # 创建新项目卡片（只创建一次）
        self.create_card = CreateProjectCard()
        self.create_card.clicked.connect(self.onCreateProject)

        self.setupUI()
        self.loadProjects()

    def setupUI(self):
        """初始化UI"""
        # 如果布局不存在，创建UI结构
        if not self.layout():
            self._create_ui_structure()
        # 总是应用主题样式
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(24), dp(20), dp(24), dp(20))
        layout.setSpacing(dp(16))

        # 顶部标题栏
        header_layout = QHBoxLayout()

        self.title_label = QLabel("我的小说项目")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # 返回按钮
        self.back_btn = QPushButton("返回首页")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBackToHome)
        header_layout.addWidget(self.back_btn)

        layout.addLayout(header_layout)

        # 分隔线
        self.separator = QFrame()
        self.separator.setFixedHeight(1)
        layout.addWidget(self.separator)

        # 项目网格（滚动区域）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(dp(16))
        self.grid_layout.setContentsMargins(0, dp(8), 0, dp(8))
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area, stretch=1)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        bg_color = theme_manager.book_bg_primary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()

        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"""
                font-family: {serif_font};
                font-size: {sp(28)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(2)}px;
            """)

        if hasattr(self, 'back_btn'):
            # 简单的文字按钮
            self.back_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-family: {ui_font};
                }}
                QPushButton:hover {{
                    color: {text_primary};
                    border-color: {text_secondary};
                }}
            """)

        if hasattr(self, 'separator'):
            self.separator.setStyleSheet(f"background-color: {border_color}; border: none;")

        if hasattr(self, 'scroll_area'):
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                {theme_manager.scrollbar()}
            """)

        # 网格容器透明背景
        if hasattr(self, 'grid_container'):
            self.grid_container.setStyleSheet("background-color: transparent;")

        # 背景样式
        self.setStyleSheet(f"""
            NovelWorkspace {{
                background-color: {bg_color};
            }}
        """)

    def loadProjects(self):
        """加载项目列表"""
        try:
            response = self.api_client.get_novels()
            self.projects = response

            self.renderProjects()

        except Exception as e:
            MessageService.show_error(self, f"加载项目失败：{str(e)}", "错误")

    def renderProjects(self):
        """渲染项目卡片（使用deque优化为O(n)）"""
        # 清空布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            # 不删除widget，只是从布局移除
            # 卡片会保留在card_pool中复用

        # 重置可用卡片队列：将所有卡片隐藏并加入队列
        self.available_cards.clear()
        for card in self.card_pool:
            card.hide()
            self.available_cards.append(card)

        # 添加新项目卡片到第一个位置（复用已创建的）
        self.grid_layout.addWidget(self.create_card, 0, 0)
        self.create_card.show()

        # 渲染项目卡片（3列网格，从队列获取卡片 O(1)）
        for idx, project in enumerate(self.projects):
            row = (idx + 1) // 3
            col = (idx + 1) % 3

            # 从队列获取卡片（O(1)）或创建新卡片
            if self.available_cards:
                card = self.available_cards.popleft()
                card.updateData(project)
            else:
                # 队列空，创建新卡片
                card = ProjectCard(project)
                card.viewDetailsClicked.connect(self.onViewDetails)
                card.continueWritingClicked.connect(self.onContinueWriting)
                card.deleteClicked.connect(self.onDeleteProject)
                self.card_pool.append(card)

            # 显示卡片并添加到布局
            card.show()
            self.grid_layout.addWidget(card, row, col)

    def onCreateProject(self):
        """创建新项目"""
        self.navigateTo('INSPIRATION')

    def goBackToHome(self):
        """返回首页"""
        self.navigateTo('HOME')

    def onViewDetails(self, project_id):
        """查看项目详情"""
        # 获取项目数据，判断状态
        try:
            project = self.api_client.get_novel(project_id)
            status = project.get('status', '')

            # 蓝图后的状态列表（这些状态表示项目已有蓝图）
            blueprint_ready_states = ['blueprint_ready', 'part_outlines_ready', 'chapter_outlines_ready', 'writing', 'completed']

            if status in blueprint_ready_states:
                # 已有蓝图，正常导航到详情页
                self.navigateTo('DETAIL', project_id=project_id)
            else:
                # 未完成蓝图（draft或其他状态），导航回INSPIRATION模式
                self.navigateTo('INSPIRATION', project_id=project_id)

        except Exception as e:
            logger.error(f"获取项目状态失败: {str(e)}")
            # 出错时仍导航到详情页
            self.navigateTo('DETAIL', project_id=project_id)

    def onContinueWriting(self, project_id):
        """继续创作"""
        self.navigateTo('WRITING_DESK', project_id=project_id)

    def onDeleteProject(self, project_id):
        """删除项目"""
        if not confirm(
            self,
            "确定要删除此项目吗？此操作不可恢复！",
            "确认删除"
        ):
            return

        try:
            self.api_client.delete_novels([project_id])
            MessageService.show_success(self, "项目已删除")
            self.loadProjects()

        except Exception as e:
            MessageService.show_error(self, f"删除失败：{str(e)}", "错误")

    def refresh(self, **params):
        """刷新页面数据

        当页面被重新导航到时调用（页面已缓存的情况）
        重新加载项目列表以显示最新数据
        """
        self.loadProjects()
