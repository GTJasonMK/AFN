"""
首页核心类模块

VS风格欢迎页面，左侧操作区域，右侧项目列表Tab切换。
"""

import logging
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QScrollArea, QFrame, QStackedWidget,
    QFileDialog
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer

from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from api.manager import APIClientManager
from utils.dpi_utils import dp
from components.dialogs import CreateModeDialog, InputDialog, ImportProgressDialog
from components.loading_spinner import ListLoadingState

from .constants import CREATIVE_QUOTES, get_title_sort_key
from .particles import ParticleBackground
from .cards import RecentProjectCard, TabBar


logger = logging.getLogger(__name__)


class HomePage(BasePage):
    """首页 - VS风格欢迎页面"""

    def __init__(self, parent=None):
        self.api_client = APIClientManager.get_client()
        self.recent_projects = []  # 最近项目（按时间排序，最多10个）
        self.all_projects = []  # 全部项目（按首字母排序）
        self._entrance_animated = False  # 入场动画是否已播放
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()
        # 只在首次显示时播放入场动画
        if not self._entrance_animated:
            self._entrance_animated = True
            QTimer.singleShot(100, self._animate_entrance)

    def _create_ui_structure(self):
        # 设置objectName以便CSS选择器生效
        self.setObjectName("home_page")

        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 添加浮动粒子背景
        self.particle_bg = ParticleBackground(self)
        self.particle_bg.lower()
        self.particle_bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # ========== 左侧区域 ==========
        self.left_widget = QWidget()
        self.left_widget.setMinimumWidth(dp(400))
        self.left_widget.setMaximumWidth(dp(504))
        left_layout = QVBoxLayout(self.left_widget)
        left_layout.setContentsMargins(dp(64), dp(64), dp(40), dp(64))
        left_layout.setSpacing(dp(24))

        # 右上角设置按钮
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        self.settings_btn = QPushButton("设置")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedSize(dp(60), dp(32))
        self.settings_btn.clicked.connect(lambda: self.navigateTo('SETTINGS'))
        header_layout.addWidget(self.settings_btn)
        left_layout.addLayout(header_layout)

        left_layout.addSpacing(dp(40))

        # 主标题
        self.title = QLabel("AFN")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        left_layout.addWidget(self.title)

        # 副标题
        self.subtitle = QLabel("AI 驱动的长篇小说创作助手")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        left_layout.addWidget(self.subtitle)

        # 创作箴言 - 艺术气息的启发性标语
        self.quote_container = QWidget()
        quote_layout = QVBoxLayout(self.quote_container)
        quote_layout.setContentsMargins(0, dp(16), 0, 0)
        quote_layout.setSpacing(dp(4))

        # 随机选择一句箴言
        self._current_quote = random.choice(CREATIVE_QUOTES)

        # 中文主标语
        self.quote_label = QLabel(self._current_quote[0])
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.quote_label.setWordWrap(True)
        quote_layout.addWidget(self.quote_label)

        # 英文副标语（更小、更淡）
        self.quote_sub_label = QLabel(self._current_quote[1])
        self.quote_sub_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.quote_sub_label.setWordWrap(True)
        quote_layout.addWidget(self.quote_sub_label)

        left_layout.addWidget(self.quote_container)

        # 为引言添加透明度效果
        self.quote_opacity = QGraphicsOpacityEffect()
        self.quote_container.setGraphicsEffect(self.quote_opacity)

        left_layout.addSpacing(dp(48))

        # 操作按钮区域
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(dp(16))

        # 创建小说按钮（主要）
        self.create_btn = QPushButton("创建小说")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.setMinimumHeight(dp(48))
        self.create_btn.clicked.connect(self._on_create_novel)
        buttons_layout.addWidget(self.create_btn)

        # 打开现有项目按钮（次要）- 切换到全部项目Tab
        self.open_btn = QPushButton("查看全部项目")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setMinimumHeight(dp(48))
        self.open_btn.clicked.connect(lambda: self._switch_tab(1))
        buttons_layout.addWidget(self.open_btn)

        left_layout.addWidget(buttons_widget)
        left_layout.addStretch()

        main_layout.addWidget(self.left_widget)

        # ========== 右侧区域（Tab切换：最近项目 / 全部项目） ==========
        self.right_widget = QWidget()
        right_layout = QVBoxLayout(self.right_widget)
        right_layout.setContentsMargins(dp(40), dp(64), dp(64), dp(64))
        right_layout.setSpacing(0)

        # Tab栏
        self.tab_bar = TabBar()
        self.tab_bar.recent_btn.clicked.connect(lambda: self._switch_tab(0))
        self.tab_bar.all_btn.clicked.connect(lambda: self._switch_tab(1))
        right_layout.addWidget(self.tab_bar)

        # 堆叠页面（用于Tab切换）
        self.projects_stack = QStackedWidget()

        # ===== Tab 0: 最近项目页面 =====
        self.recent_page = QWidget()
        recent_page_layout = QVBoxLayout(self.recent_page)
        recent_page_layout.setContentsMargins(0, 0, 0, 0)
        recent_page_layout.setSpacing(0)

        self.recent_scroll = QScrollArea()
        self.recent_scroll.setWidgetResizable(True)
        self.recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.recent_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, dp(8), 0)
        self.recent_layout.setSpacing(dp(8))
        self.recent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 最近项目加载骨架屏
        self.recent_loading = ListLoadingState(
            row_count=5,
            row_height=dp(64),
            spacing=dp(8),
            parent=self.recent_container
        )
        self.recent_layout.addWidget(self.recent_loading)

        # 最近项目空状态提示
        self.recent_empty_label = QLabel("暂无最近项目\n点击\"创建小说\"开始您的创作之旅")
        self.recent_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_empty_label.setWordWrap(True)
        self.recent_layout.addWidget(self.recent_empty_label)
        self.recent_layout.addStretch()

        self.recent_scroll.setWidget(self.recent_container)
        recent_page_layout.addWidget(self.recent_scroll)
        self.projects_stack.addWidget(self.recent_page)

        # ===== Tab 1: 全部项目页面 =====
        self.all_page = QWidget()
        all_page_layout = QVBoxLayout(self.all_page)
        all_page_layout.setContentsMargins(0, 0, 0, 0)
        all_page_layout.setSpacing(0)

        self.all_scroll = QScrollArea()
        self.all_scroll.setWidgetResizable(True)
        self.all_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.all_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.all_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.all_container = QWidget()
        self.all_layout = QVBoxLayout(self.all_container)
        self.all_layout.setContentsMargins(0, 0, dp(8), 0)
        self.all_layout.setSpacing(dp(8))
        self.all_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 全部项目加载骨架屏
        self.all_loading = ListLoadingState(
            row_count=8,
            row_height=dp(64),
            spacing=dp(8),
            parent=self.all_container
        )
        self.all_layout.addWidget(self.all_loading)

        # 全部项目空状态提示
        self.all_empty_label = QLabel("暂无项目\n点击\"创建小说\"开始您的创作之旅")
        self.all_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_empty_label.setWordWrap(True)
        self.all_layout.addWidget(self.all_empty_label)
        self.all_layout.addStretch()

        self.all_scroll.setWidget(self.all_container)
        all_page_layout.addWidget(self.all_scroll)
        self.projects_stack.addWidget(self.all_page)

        right_layout.addWidget(self.projects_stack, 1)

        main_layout.addWidget(self.right_widget, 1)  # 右侧占据剩余空间

        # 为动画准备透明度效果
        self.title_opacity = QGraphicsOpacityEffect()
        self.title.setGraphicsEffect(self.title_opacity)
        self.subtitle_opacity = QGraphicsOpacityEffect()
        self.subtitle.setGraphicsEffect(self.subtitle_opacity)

    def _apply_theme(self):
        # 调试日志
        logger.info("=== HomePage._apply_theme() called ===")
        logger.info(f"is_dark_mode: {theme_manager.is_dark_mode()}")

        bg_color = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        logger.info(f"bg_color: {bg_color}, text_primary: {text_primary}")
        logger.info(f"accent_color: {accent_color}, bg_secondary: {bg_secondary}")
        logger.info(f"text_secondary: {text_secondary}, border_color: {border_color}")

        # 检查透明效果是否启用
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QWidget
        from themes.modern_effects import ModernEffects
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = transparency_config.get("content_opacity", 0.95)

        logger.info("="*50)
        logger.info(f"HomePage._apply_theme() 透明效果配置:")
        logger.info(f"  enabled={transparency_enabled}")
        logger.info(f"  content_opacity={content_opacity}")
        logger.info("="*50)

        if transparency_enabled:
            # 透明模式：页面背景使用RGBA实现半透明
            # 当content_opacity=0时，页面完全透明，能看到桌面
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            logger.info(f"应用透明背景: {bg_rgba}")

            # 直接设置样式
            self.setStyleSheet(f"background-color: {bg_rgba};")

            # 设置WA_TranslucentBackground使透明生效
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            # 确保指定子容器透明（不使用findChildren避免影响其他页面）
            transparent_containers = [
                'left_widget', 'right_widget', 'quote_container',
                'projects_stack', 'recent_page', 'all_page',
                'recent_container', 'all_container', 'tab_bar'
            ]
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setStyleSheet("background-color: transparent;")
                    container.setAutoFillBackground(False)

            # 设置ScrollArea和viewport透明
            for scroll_name in ['recent_scroll', 'all_scroll']:
                scroll = getattr(self, scroll_name, None)
                if scroll:
                    scroll.setStyleSheet(f"""
                        QScrollArea {{
                            background-color: transparent;
                            border: none;
                        }}
                        {theme_manager.scrollbar()}
                    """)
                    scroll.setAutoFillBackground(False)
                    if scroll.viewport():
                        scroll.viewport().setStyleSheet("background-color: transparent;")
                        scroll.viewport().setAutoFillBackground(False)

            # 粒子背景也需要透明
            if hasattr(self, 'particle_bg') and self.particle_bg:
                self.particle_bg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        else:
            # 非透明模式：使用实色背景，恢复所有背景填充
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            # 恢复所有容器的背景填充
            containers_to_restore = [
                'left_widget', 'right_widget', 'quote_container',
                'projects_stack', 'recent_page', 'all_page',
                'recent_container', 'all_container', 'tab_bar'
            ]
            for container_name in containers_to_restore:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

            # 恢复ScrollArea背景
            for scroll_name in ['recent_scroll', 'all_scroll']:
                scroll = getattr(self, scroll_name, None)
                if scroll:
                    scroll.setStyleSheet(f"""
                        QScrollArea {{
                            background-color: {bg_secondary};
                            border: none;
                        }}
                        {theme_manager.scrollbar()}
                    """)
                    scroll.setAutoFillBackground(True)
                    if scroll.viewport():
                        scroll.viewport().setStyleSheet(f"background-color: {bg_secondary};")
                        scroll.viewport().setAutoFillBackground(True)

        self.title.setStyleSheet(f"""
            QLabel {{
                font-family: {serif_font};
                font-size: {dp(56)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(2)}px;
            }}
        """)

        self.subtitle.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(16)}px;
                color: {text_secondary};
                letter-spacing: {dp(1)}px;
            }}
        """)

        # 创作箴言样式 - 艺术字体，斜体，淡雅
        quote_color = text_secondary
        self.quote_container.setStyleSheet("background: transparent;")

        # 中文箴言 - 使用衬线字体，营造文学气息
        self.quote_label.setStyleSheet(f"""
            QLabel {{
                font-family: {serif_font};
                font-size: {dp(15)}px;
                font-style: italic;
                color: {quote_color};
                letter-spacing: {dp(3)}px;
                line-height: 1.5;
                background: transparent;
            }}
        """)

        # 英文副标语 - 更小、更淡，作为点缀
        self.quote_sub_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Georgia", "Times New Roman", {serif_font};
                font-size: {dp(11)}px;
                font-style: italic;
                color: {border_color};
                letter-spacing: {dp(1)}px;
                line-height: 1.4;
                background: transparent;
            }}
        """)

        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid transparent;
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                font-size: {dp(13)}px;
            }}
            QPushButton:hover {{
                color: {accent_color};
                border-color: {border_color};
            }}
        """)

        # 创建按钮样式（主要按钮）
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color};
                color: {bg_color};
                border: none;
                border-radius: {dp(8)}px;
                padding: {dp(12)}px {dp(24)}px;
                font-family: {ui_font};
                font-size: {dp(16)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {text_primary};
            }}
            QPushButton:pressed {{
                background-color: {text_secondary};
            }}
        """)

        # 打开按钮样式（次要按钮）- 透明模式下使用半透明背景
        if transparency_enabled:
            open_btn_bg = ModernEffects.hex_to_rgba(bg_secondary, 0.7)
            open_btn_pressed_bg = ModernEffects.hex_to_rgba(bg_color, 0.5)
        else:
            open_btn_bg = bg_secondary
            open_btn_pressed_bg = bg_color

        self.open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {open_btn_bg};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px {dp(24)}px;
                font-family: {ui_font};
                font-size: {dp(16)}px;
            }}
            QPushButton:hover {{
                border-color: {accent_color};
                color: {accent_color};
            }}
            QPushButton:pressed {{
                background-color: {open_btn_pressed_bg};
            }}
        """)

        # 滚动区域样式
        scroll_style = f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: {dp(6)}px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {border_color};
                border-radius: {dp(3)}px;
                min-height: {dp(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {text_secondary};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """

        self.recent_scroll.setStyleSheet(scroll_style)
        self.all_scroll.setStyleSheet(scroll_style)

        # 设置ScrollArea的viewport透明背景（重要：viewport是实际绘制内容的区域）
        if self.recent_scroll.viewport():
            self.recent_scroll.viewport().setStyleSheet("background-color: transparent;")
        if self.all_scroll.viewport():
            self.all_scroll.viewport().setStyleSheet("background-color: transparent;")

        # 容器透明背景
        for container_name in ['recent_container', 'all_container', 'recent_page', 'all_page']:
            container = getattr(self, container_name, None)
            if container:
                container.setStyleSheet("background-color: transparent;")

        # 堆叠页面透明背景
        self.projects_stack.setStyleSheet("background-color: transparent;")

        # 空状态标签样式
        empty_label_style = f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(14)}px;
                color: {text_secondary};
                padding: {dp(40)}px;
            }}
        """

        self.recent_empty_label.setStyleSheet(empty_label_style)
        self.all_empty_label.setStyleSheet(empty_label_style)

        # 强制刷新样式缓存
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _animate_entrance(self):
        """入场动画"""
        title_anim = QPropertyAnimation(self.title_opacity, b"opacity")
        title_anim.setDuration(600)
        title_anim.setStartValue(0.0)
        title_anim.setEndValue(1.0)
        title_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        title_anim.start()
        self.title_animation = title_anim

        subtitle_anim = QPropertyAnimation(self.subtitle_opacity, b"opacity")
        subtitle_anim.setDuration(600)
        subtitle_anim.setStartValue(0.0)
        subtitle_anim.setEndValue(1.0)
        subtitle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(150, subtitle_anim.start)
        self.subtitle_animation = subtitle_anim

        # 引言淡入动画 - 延迟更久，更缓慢地出现，增加诗意感
        quote_anim = QPropertyAnimation(self.quote_opacity, b"opacity")
        quote_anim.setDuration(800)
        quote_anim.setStartValue(0.0)
        quote_anim.setEndValue(0.85)
        quote_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(400, quote_anim.start)
        self.quote_animation = quote_anim

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'particle_bg'):
            self.particle_bg.setGeometry(self.rect())

    def _on_create_novel(self):
        """创建小说 - 显示模式选择对话框"""
        dialog = CreateModeDialog(self)
        result = dialog.exec()

        if result == CreateModeDialog.MODE_AI:
            # AI辅助创作：进入灵感对话模式
            self.navigateTo('INSPIRATION')
        elif result == CreateModeDialog.MODE_FREE:
            # 自由创作：先输入标题，然后创建空项目
            self._create_free_project()
        elif result == CreateModeDialog.MODE_IMPORT:
            # 导入分析：选择TXT文件，导入并分析
            self._create_import_project()

    def _create_free_project(self):
        """创建自由创作项目（跳过灵感对话）"""
        # 弹出标题输入对话框
        title_dialog = InputDialog(
            parent=self,
            title="新建项目",
            label="请输入小说标题：",
            placeholder="我的小说"
        )

        if title_dialog.exec():
            title = title_dialog.getText().strip()
            if not title:
                title = "未命名小说"

            # 异步创建项目
            self._do_create_free_project(title)

    def _do_create_free_project(self, title: str):
        """执行自由创作项目创建"""
        from utils.async_worker import AsyncWorker
        from utils.message_service import MessageService

        def do_create():
            return self.api_client.create_novel(
                title=title,
                initial_prompt="",
                skip_inspiration=True
            )

        def on_success(project):
            project_id = project.get('id')
            logger.info("自由创作项目创建成功: %s", project_id)
            # 直接进入项目详情页进行手动编辑
            self.navigateTo('DETAIL', project_id=project_id)

        def on_error(error_msg):
            MessageService.show_error(self, f"创建项目失败：{error_msg}", "错误")

        worker = AsyncWorker(do_create)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def _create_import_project(self):
        """创建导入分析项目"""
        # 1. 选择TXT文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要导入的小说文件",
            "",
            "文本文件 (*.txt);;所有文件 (*.*)"
        )

        if not file_path:
            return

        # 2. 输入项目标题
        import os
        default_title = os.path.splitext(os.path.basename(file_path))[0]

        title_dialog = InputDialog(
            parent=self,
            title="导入项目",
            label="请输入项目标题：",
            text=default_title,  # 设置初始值
            placeholder="请输入项目标题"
        )

        if not title_dialog.exec():
            return

        title = title_dialog.getText().strip()
        if not title:
            title = default_title

        # 3. 执行导入流程
        self._do_import_project(title, file_path)

    def _do_import_project(self, title: str, file_path: str):
        """执行导入项目流程"""
        from utils.async_worker import AsyncWorker
        from utils.message_service import MessageService
        from components.dialogs import LoadingDialog

        # 显示加载对话框
        loading_dialog = LoadingDialog(
            parent=self,
            message="正在创建项目并导入文件...",
            title="导入中"
        )
        loading_dialog.show()

        def do_import():
            # 1. 创建空项目
            project = self.api_client.create_novel(
                title=title,
                initial_prompt="",
                skip_inspiration=True
            )
            project_id = project.get('id')

            # 2. 导入TXT文件
            import_result = self.api_client.import_txt_file(
                project_id=project_id,
                file_path=file_path
            )

            return {
                'project_id': project_id,
                'import_result': import_result
            }

        def on_success(result):
            loading_dialog.close()
            project_id = result['project_id']
            import_result = result['import_result']

            total_chapters = import_result.get('total_chapters', 0)
            MessageService.show_success(
                self,
                f"导入成功！共识别 {total_chapters} 章"
            )

            # 进入项目详情页，用户可以在那里手动启动分析
            self.navigateTo('DETAIL', project_id=project_id)

        def on_error(error_msg):
            loading_dialog.close()
            MessageService.show_error(self, f"导入失败：{error_msg}", "错误")

        worker = AsyncWorker(do_import)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def _on_project_clicked(self, project_data: dict):
        """点击项目卡片"""
        project_id = project_data.get('id')
        status = project_data.get('status', 'draft')

        # 根据状态决定导航目标
        if status in ['blueprint_ready', 'part_outlines_ready', 'chapter_outlines_ready', 'writing', 'completed']:
            # 已有蓝图，直接进入写作台
            self.navigateTo('WRITING_DESK', project_id=project_id)
        else:
            # 未完成蓝图（draft状态），导航回灵感对话继续
            self.navigateTo('INSPIRATION', project_id=project_id)

    def _switch_tab(self, index: int):
        """切换Tab页面"""
        self.tab_bar.setCurrentIndex(index)
        self.projects_stack.setCurrentIndex(index)

    def _load_recent_projects(self):
        """加载项目数据（最近项目 + 全部项目）

        使用AsyncWorker在后台线程执行API调用，避免UI线程阻塞。
        加载期间显示骨架屏，提升用户感知体验。
        """
        from utils.async_worker import AsyncWorker

        # 显示加载骨架屏
        self._show_loading_state()

        def fetch_projects():
            """后台线程执行的API调用"""
            return self.api_client.get_novels()

        def on_success(projects):
            """API调用成功回调（在主线程执行）"""
            if projects:
                # 最近项目：按更新时间排序，取前10个
                sorted_by_time = sorted(
                    projects,
                    key=lambda x: x.get('updated_at', ''),
                    reverse=True
                )
                self.recent_projects = sorted_by_time[:10]

                # 全部项目：按首字母排序
                self.all_projects = sorted(
                    projects,
                    key=lambda x: (get_title_sort_key(x.get('title', '')), x.get('title', '').lower())
                )
            else:
                self.recent_projects = []
                self.all_projects = []

            self._update_projects_ui()

        def on_error(error):
            """API调用失败回调（在主线程执行）"""
            logger.error("加载项目失败: %s", error, exc_info=True)
            self.recent_projects = []
            self.all_projects = []
            self._update_projects_ui()

        # 创建并启动异步工作线程
        worker = AsyncWorker(fetch_projects)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        # 保持worker引用，防止被垃圾回收
        if not hasattr(self, '_workers'):
            self._workers = []
        # 清理已完成的worker（安全检查，避免访问已删除的C++对象）
        valid_workers = []
        for w in self._workers:
            try:
                if w.isRunning():
                    valid_workers.append(w)
            except RuntimeError:
                # C++ 对象已被删除，跳过
                pass
        self._workers = valid_workers
        self._workers.append(worker)

        worker.start()

    def _clear_layout(self, layout, preserve_widgets=None):
        """清空布局中的所有组件（可选保留指定widget）

        Args:
            layout: 要清空的布局
            preserve_widgets: 要保留的widget列表（不删除，只从布局中移除）
        """
        if preserve_widgets is None:
            preserve_widgets = []

        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                # 如果是要保留的widget，只从布局中移除，不删除
                if widget in preserve_widgets:
                    continue
                # 使用 deleteLater() 删除，ThemeAware 基类会自动断开信号
                widget.deleteLater()

    def _show_loading_state(self):
        """显示加载骨架屏"""
        # 隐藏空状态提示
        if hasattr(self, 'recent_empty_label'):
            self.recent_empty_label.hide()
        if hasattr(self, 'all_empty_label'):
            self.all_empty_label.hide()

        # 显示骨架屏
        if hasattr(self, 'recent_loading'):
            self.recent_loading.show()
            self.recent_loading.start()
        if hasattr(self, 'all_loading'):
            self.all_loading.show()
            self.all_loading.start()

    def _hide_loading_state(self):
        """隐藏加载骨架屏"""
        if hasattr(self, 'recent_loading'):
            self.recent_loading.stop()
            self.recent_loading.hide()
        if hasattr(self, 'all_loading'):
            self.all_loading.stop()
            self.all_loading.hide()

    def _update_projects_ui(self):
        """更新项目列表UI（最近项目Tab + 全部项目Tab）"""
        # 隐藏加载骨架屏
        self._hide_loading_state()

        # 清空现有内容（保留empty_label和loading不被删除）
        preserve_recent = [self.recent_empty_label]
        preserve_all = [self.all_empty_label]
        if hasattr(self, 'recent_loading'):
            preserve_recent.append(self.recent_loading)
        if hasattr(self, 'all_loading'):
            preserve_all.append(self.all_loading)

        self._clear_layout(self.recent_layout, preserve_widgets=preserve_recent)
        self._clear_layout(self.all_layout, preserve_widgets=preserve_all)

        # ===== 更新最近项目Tab（不显示删除按钮） =====
        if self.recent_projects:
            self.recent_empty_label.hide()
            for project in self.recent_projects:
                card = RecentProjectCard(project, self.recent_container, show_delete=False)
                self.recent_layout.addWidget(card)
            self.recent_layout.addStretch()
        else:
            self.recent_layout.addWidget(self.recent_empty_label)
            self.recent_empty_label.show()
            self.recent_layout.addStretch()

        # ===== 更新全部项目Tab（显示删除按钮） =====
        if self.all_projects:
            self.all_empty_label.hide()
            for project in self.all_projects:
                card = RecentProjectCard(project, self.all_container, show_delete=True)
                card.deleteRequested.connect(self._on_delete_project)
                self.all_layout.addWidget(card)
            self.all_layout.addStretch()
        else:
            self.all_layout.addWidget(self.all_empty_label)
            self.all_empty_label.show()
            self.all_layout.addStretch()

    def refresh(self, **params):
        """刷新页面"""
        self._load_recent_projects()

    def onShow(self):
        """页面显示时"""
        # 随机更换箴言，每次返回首页时显示不同的启发性标语
        if hasattr(self, 'quote_label') and hasattr(self, 'quote_sub_label'):
            self._current_quote = random.choice(CREATIVE_QUOTES)
            self.quote_label.setText(self._current_quote[0])
            self.quote_sub_label.setText(self._current_quote[1])

        # 加载最近项目
        self._load_recent_projects()

        # 启动粒子动画
        if hasattr(self, 'particle_bg'):
            self.particle_bg.start()

    def onHide(self):
        """页面隐藏时停止动画"""
        if hasattr(self, 'particle_bg'):
            self.particle_bg.stop()

    def _on_delete_project(self, project_id: str, title: str):
        """删除项目处理"""
        from utils.message_service import confirm, MessageService
        from utils.async_worker import AsyncWorker

        # 确认删除
        if not confirm(
            self,
            f"确定要删除项目「{title}」吗？\n\n此操作不可恢复，所有章节内容将被永久删除。",
            "确认删除"
        ):
            return

        def do_delete():
            return self.api_client.delete_novels([project_id])

        def on_success(result):
            MessageService.show_success(self, f"项目「{title}」已删除")
            # 刷新项目列表
            self._load_recent_projects()

        def on_error(error_msg):
            MessageService.show_error(self, f"删除失败：{error_msg}", "错误")

        # 异步执行删除
        worker = AsyncWorker(do_delete)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        # 保持worker引用
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 清理粒子背景资源
        if hasattr(self, 'particle_bg'):
            self.particle_bg.cleanup()
        super().closeEvent(event)
