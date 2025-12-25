"""
项目详情主页面 - 现代化设计

采用顶部Tab导航，提高空间利用率
集成所有Section组件，提供流畅的浏览体验
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QWidget,
    QScrollArea, QStackedWidget, QFileDialog, QGraphicsDropShadowEffect,
    QToolTip
)
from PyQt6.QtCore import pyqtSignal, Qt, QByteArray
from PyQt6.QtGui import QColor, QCursor
from PyQt6.QtSvgWidgets import QSvgWidget
from pages.base_page import BasePage
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from themes import ButtonStyles, ModernEffects
from utils.error_handler import handle_errors
from utils.message_service import MessageService, confirm
from utils.formatters import get_project_status_text
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncAPIWorker
from utils.constants import WorkerTimeouts

from .overview_section import OverviewSection
from .world_setting_section import WorldSettingSection
from .characters_section import CharactersSection
from .relationships_section import RelationshipsSection
from .chapter_outline import ChapterOutlineSection
from .chapters_section import ChaptersSection
from .edit_dialog import EditDialog
from .refine_dialog import RefineDialog
from .dirty_tracker import DirtyTracker


class NovelDetail(BasePage):
    """项目详情页面 - 现代化设计"""

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        self.api_client = APIClientManager.get_client()
        self.project_data = None
        self.section_data = {}
        self.active_section = 'overview'

        # Section组件映射
        self.section_widgets = {}

        # 异步任务管理
        self.refine_worker = None  # 蓝图优化异步worker

        # 脏数据追踪器
        self.dirty_tracker = DirtyTracker()

        self.setupUI()
        self.loadProjectBasicInfo()
        self.loadSection('overview')

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次，优化版：分步创建避免卡顿）"""
        from PyQt6.QtWidgets import QApplication

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部Header（项目信息 + 操作按钮）
        self.createHeader()
        main_layout.addWidget(self.header)

        # 让出事件循环
        QApplication.processEvents()

        # Tab导航栏
        self.createTabBar()
        main_layout.addWidget(self.tab_bar)

        # 让出事件循环
        QApplication.processEvents()

        # 内容区域
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack, stretch=1)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        bg_color = theme_manager.book_bg_primary()
        header_bg = theme_manager.book_bg_secondary()
        tab_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        border_color = theme_manager.book_border_color()

        self.setStyleSheet(f"""
            NovelDetail {{
                background-color: {bg_color};
            }}
        """)

        # 更新Header和Tab栏样式
        if hasattr(self, 'header') and self.header:
            self._applyHeaderStyle()
        if hasattr(self, 'tab_bar') and self.tab_bar:
            self._applyTabStyle()

    def createHeader(self):
        """创建顶部Header - 书香风格"""
        self.header = QFrame()
        self.header.setObjectName("detail_header")
        self.header.setFixedHeight(dp(100))

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(16))
        header_layout.setSpacing(dp(16))

        # 左侧：项目图标 + 信息
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(dp(16))

        # 项目图标（支持SVG头像或默认占位符）
        self.icon_container = QFrame()
        self.icon_container.setFixedSize(dp(64), dp(64))
        self.icon_container.setObjectName("project_icon")
        self.icon_container.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_container.setToolTip("点击生成小说头像")
        icon_layout = QVBoxLayout(self.icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SVG头像显示组件
        self.avatar_svg_widget = QSvgWidget()
        self.avatar_svg_widget.setFixedSize(dp(60), dp(60))
        self.avatar_svg_widget.setVisible(False)
        icon_layout.addWidget(self.avatar_svg_widget)

        # 默认占位符（字母B）
        self.icon_placeholder = QLabel("B")
        self.icon_placeholder.setStyleSheet(f"font-size: {sp(28)}px; font-weight: bold;")
        self.icon_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(self.icon_placeholder)

        # 为icon_container添加点击事件
        self.icon_container.mousePressEvent = self._onIconClicked

        left_layout.addWidget(self.icon_container)

        # 项目信息
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        # 标题行
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(8))

        self.project_title = QLabel("加载中...")
        self.project_title.setObjectName("project_title")
        title_row.addWidget(self.project_title)

        # 编辑标题按钮
        edit_title_btn = QPushButton("编辑")
        edit_title_btn.setObjectName("edit_title_btn")
        edit_title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_title_btn.setFixedHeight(dp(32))  # 修正：24px不符合触控目标最小值32px
        edit_title_btn.clicked.connect(self.editProjectTitle)
        title_row.addWidget(edit_title_btn)
        title_row.addStretch()

        info_layout.addLayout(title_row)

        # 元信息行（类型 + 状态标签）
        meta_row = QHBoxLayout()
        meta_row.setSpacing(dp(8))

        self.genre_tag = QLabel("")
        self.genre_tag.setObjectName("genre_tag")
        meta_row.addWidget(self.genre_tag)

        self.status_tag = QLabel("")
        self.status_tag.setObjectName("status_tag")
        meta_row.addWidget(self.status_tag)

        meta_row.addStretch()
        info_layout.addLayout(meta_row)

        left_layout.addWidget(info_container, stretch=1)

        header_layout.addWidget(left_container, stretch=1)

        # 右侧：操作按钮
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(12))

        # 保存按钮（初始禁用）
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.onSaveAll)
        btn_layout.addWidget(self.save_btn)

        # 返回按钮 - 返回写作台
        self.back_btn = QPushButton("返回写作台")
        self.back_btn.setObjectName("back_btn")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.openWritingDesk)
        btn_layout.addWidget(self.back_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(lambda: self.exportNovel('txt'))
        btn_layout.addWidget(self.export_btn)

        # 优化蓝图按钮
        self.refine_btn = QPushButton("优化蓝图")
        self.refine_btn.setObjectName("refine_btn")
        self.refine_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refine_btn.clicked.connect(self.onRefineBlueprint)
        btn_layout.addWidget(self.refine_btn)

        # 开始分析按钮（仅导入项目显示）
        self.analyze_btn = QPushButton("开始分析")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self.onStartAnalysis)
        self.analyze_btn.setVisible(False)  # 默认隐藏
        btn_layout.addWidget(self.analyze_btn)

        # 开始创作按钮（主按钮）
        self.create_btn = QPushButton("开始创作")
        self.create_btn.setObjectName("create_btn")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.clicked.connect(self.openWritingDesk)
        btn_layout.addWidget(self.create_btn)

        header_layout.addWidget(btn_container)

        # 应用Header样式
        self._applyHeaderStyle()

    def _applyHeaderStyle(self):
        """应用Header样式 - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        header_bg = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        icon_color = theme_manager.book_accent_color()
        tag_bg = "transparent"

        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        # 设置header容器和子组件样式
        self.header.setStyleSheet(f"""
            QFrame#detail_header {{
                background-color: {header_bg};
                border-bottom: 1px solid {border_color};
            }}
            QFrame#project_icon {{
                background: transparent;
                border: 2px solid {icon_color};
                border-radius: {dp(4)}px;
            }}
            QLabel#project_title {{
                font-family: {serif_font};
                font-size: {sp(28)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(2)}px;
            }}
            QPushButton#edit_title_btn {{
                background: transparent;
                border: none;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                color: {text_secondary};
                text-decoration: underline;
            }}
            QPushButton#edit_title_btn:hover {{
                color: {icon_color};
            }}
            QLabel#genre_tag {{
                background-color: {tag_bg};
                color: {text_secondary};
                border: 1px solid {border_color};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(2)}px;
                font-family: {ui_font};
                font-size: {sp(12)}px;
            }}
            QLabel#status_tag {{
                background-color: {tag_bg};
                color: {text_secondary};
                border: 1px solid {border_color};
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(2)}px;
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-style: italic;
            }}
        """)

        # 操作按钮样式
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                padding: {dp(6)}px {dp(12)}px;
            }}
            QPushButton:hover {{
                color: {icon_color};
                border-color: {icon_color};
                background-color: rgba(0,0,0,0.05);
            }}
        """
        
        primary_btn_style = f"""
            QPushButton {{
                background-color: {icon_color};
                color: #FFFFFF;
                border: 1px solid {icon_color};
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                padding: {dp(6)}px {dp(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {text_primary};
                border-color: {text_primary};
            }}
        """

        if hasattr(self, 'back_btn') and self.back_btn:
            self.back_btn.setStyleSheet(btn_style)
        if hasattr(self, 'export_btn') and self.export_btn:
            self.export_btn.setStyleSheet(btn_style)
        if hasattr(self, 'refine_btn') and self.refine_btn:
            self.refine_btn.setStyleSheet(btn_style)
        if hasattr(self, 'analyze_btn') and self.analyze_btn:
            # 分析按钮使用高亮样式
            self.analyze_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.INFO};
                    color: #FFFFFF;
                    border: 1px solid {theme_manager.INFO};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    padding: {dp(6)}px {dp(12)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)
        if hasattr(self, 'create_btn') and self.create_btn:
            self.create_btn.setStyleSheet(primary_btn_style)

        # 保存按钮样式（特殊处理，有修改时高亮）
        if hasattr(self, 'save_btn') and self.save_btn:
            self._updateSaveButtonStyle()

    def createTabBar(self):
        """创建Tab导航栏"""
        self.tab_bar = QFrame()
        self.tab_bar.setObjectName("tab_bar")
        self.tab_bar.setFixedHeight(dp(48))

        tab_layout = QHBoxLayout(self.tab_bar)
        tab_layout.setContentsMargins(dp(24), 0, dp(24), 0)
        tab_layout.setSpacing(dp(24)) # 增加间距

        # Tab定义
        tabs = [
            ('overview', '概览'),
            ('world_setting', '世界观'),
            ('characters', '角色'),
            ('relationships', '关系'),
            ('chapter_outline', '章节大纲'),
            ('chapters', '已生成章节')
        ]

        self.tab_buttons = {}
        for tab_id, tab_name in tabs:
            btn = QPushButton(tab_name)
            btn.setObjectName(f"tab_{tab_id}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(dp(48)) # 占满高度
            btn.clicked.connect(lambda checked, tid=tab_id: self.switchSection(tid))
            tab_layout.addWidget(btn)
            self.tab_buttons[tab_id] = btn

        tab_layout.addStretch()

        # 应用Tab样式
        self._applyTabStyle()

    def _applyTabStyle(self):
        """应用Tab样式 - 书香风格"""
        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        tab_bg = theme_manager.book_bg_secondary()
        border_color = theme_manager.book_border_color()

        self.tab_bar.setStyleSheet(f"""
            QFrame#tab_bar {{
                background-color: {tab_bg};
                border-bottom: 1px solid {border_color};
            }}
        """)

        # 更新所有Tab按钮样式
        for tab_id, btn in self.tab_buttons.items():
            self._updateTabButtonStyle(btn, tab_id == self.active_section)

    def _updateTabButtonStyle(self, btn, is_active):
        """更新Tab按钮样式"""
        ui_font = theme_manager.ui_font()

        # 使用 theme_manager 的书香风格便捷方法，避免硬编码颜色
        text_active = theme_manager.book_accent_color()
        text_normal = theme_manager.book_text_secondary()
        hover_color = theme_manager.book_text_primary()
        border_active = theme_manager.book_accent_color()

        if is_active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_active};
                    border: none;
                    border-bottom: 2px solid {border_active};
                    border-radius: 0;
                    padding: 0 {dp(4)}px;
                    font-family: {ui_font};
                    font-size: {sp(15)}px;
                    font-weight: bold;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_normal};
                    border: none;
                    border-bottom: 2px solid transparent;
                    border-radius: 0;
                    padding: 0 {dp(4)}px;
                    font-family: {ui_font};
                    font-size: {sp(15)}px;
                    font-weight: normal;
                }}
                QPushButton:hover {{
                    color: {hover_color};
                }}
            """)

    def switchSection(self, section_id):
        """切换到指定Section"""
        self.active_section = section_id

        # 更新Tab样式
        for tid, btn in self.tab_buttons.items():
            self._updateTabButtonStyle(btn, tid == section_id)

        # 加载Section内容
        self.loadSection(section_id)

    def loadSection(self, section_id):
        """加载Section内容"""
        # 如果已缓存，直接显示
        if section_id in self.section_widgets:
            self.content_stack.setCurrentWidget(self.section_widgets[section_id])
            return

        # 创建新的Section widget
        section_widget = self.createSectionWidget(section_id)
        if section_widget:
            self.section_widgets[section_id] = section_widget
            self.content_stack.addWidget(section_widget)
            self.content_stack.setCurrentWidget(section_widget)

    def createSectionWidget(self, section_id):
        """创建Section widget"""
        import logging
        logger = logging.getLogger(__name__)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            {theme_manager.scrollbar()}
        """)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        section = None

        try:
            # 根据section_id创建对应组件
            if section_id == 'overview':
                blueprint = self._safe_get_blueprint()
                section = OverviewSection(data=blueprint, editable=True)
                section.editRequested.connect(self.onEditRequested)
            elif section_id == 'world_setting':
                world_setting = self._safe_get_nested(self._safe_get_blueprint(), 'world_setting', {})
                section = WorldSettingSection(data=world_setting, editable=True)
                section.editRequested.connect(self.onEditRequested)
            elif section_id == 'characters':
                characters = self._safe_get_nested(self._safe_get_blueprint(), 'characters', [])
                # 确保是列表
                if not isinstance(characters, list):
                    logger.warning("characters数据类型错误，期望list，实际为%s，使用空列表", type(characters).__name__)
                    characters = []
                section = CharactersSection(data=characters, editable=True, project_id=self.project_id)
                section.editRequested.connect(self.onEditRequested)
            elif section_id == 'relationships':
                relationships = self._safe_get_nested(self._safe_get_blueprint(), 'relationships', [])
                # 确保是列表
                if not isinstance(relationships, list):
                    logger.warning("relationships数据类型错误，期望list，实际为%s，使用空列表", type(relationships).__name__)
                    relationships = []
                section = RelationshipsSection(data=relationships, editable=True)
                section.editRequested.connect(self.onEditRequested)
            elif section_id == 'chapter_outline':
                blueprint = self._safe_get_blueprint()
                # 章节大纲在 blueprint.chapter_outline 中，不是顶层 chapter_outlines
                outline = self._safe_get_nested(blueprint, 'chapter_outline', [])
                # 确保是列表
                if not isinstance(outline, list):
                    logger.warning("chapter_outline数据类型错误，期望list，实际为%s，使用空列表", type(outline).__name__)
                    outline = []

                # 调试日志
                logger.info(
                    f"创建ChapterOutlineSection: "
                    f"blueprint存在={bool(blueprint)}, "
                    f"outline章节数={len(outline)}, "
                    f"needs_part_outlines={blueprint.get('needs_part_outlines', False)}"
                )

                # 获取保存的tab状态（如果有）
                initial_tab_index = 0
                if hasattr(self, '_saved_section_state') and self._saved_section_state:
                    initial_tab_index = self._saved_section_state.get('tab_index', 0)
                    logger.info(f"使用保存的tab索引: {initial_tab_index}")
                    # 使用后清除，避免影响其他刷新
                    self._saved_section_state = {}

                section = ChapterOutlineSection(
                    outline=outline,
                    blueprint=blueprint,
                    project_id=self.project_id,
                    editable=True,
                    initial_tab_index=initial_tab_index
                )
                section.editRequested.connect(self.onEditRequested)
                section.refreshRequested.connect(self.refreshProject)
            elif section_id == 'chapters':
                chapters = self._safe_get_data('chapters', [])
                # 确保是列表
                if not isinstance(chapters, list):
                    logger.warning("chapters数据类型错误，期望list，实际为%s，使用空列表", type(chapters).__name__)
                    chapters = []
                section = ChaptersSection(chapters=chapters)
                section.setProjectId(self.project_id)
                section.dataChanged.connect(self.refreshProject)
            else:
                section = QLabel("未知Section")

        except Exception as e:
            logger.error("创建Section '%s' 时出错: %s", section_id, str(e), exc_info=True)
            # 创建一个错误提示widget
            section = QLabel(f"加载 {section_id} 失败: {str(e)}")
            section.setWordWrap(True)
            section.setStyleSheet(f"color: {theme_manager.ERROR}; padding: {dp(20)}px;")

        if section:
            layout.addWidget(section, stretch=1)

        scroll.setWidget(container)
        return scroll

    def _safe_get_blueprint(self):
        """安全获取蓝图数据"""
        if not self.project_data:
            return {}
        blueprint = self.project_data.get('blueprint')
        if blueprint is None or not isinstance(blueprint, dict):
            return {}
        return blueprint

    def _safe_get_data(self, key, default=None):
        """安全获取项目数据"""
        if not self.project_data:
            return default
        return self.project_data.get(key, default)

    def _safe_get_nested(self, data, key, default=None):
        """安全获取嵌套数据"""
        if not data or not isinstance(data, dict):
            return default
        return data.get(key, default)

    def loadProjectBasicInfo(self):
        """加载项目基本信息（异步非阻塞，带加载指示器）"""
        import logging
        logger = logging.getLogger(__name__)

        # 显示加载动画
        self.show_loading("正在加载项目信息...")

        # 使用异步worker加载项目，避免阻塞UI线程
        worker = AsyncAPIWorker(self.api_client.get_novel, self.project_id)
        worker.success.connect(self._onProjectBasicInfoLoaded)
        worker.error.connect(self._onProjectBasicInfoError)

        # 保持worker引用，防止被垃圾回收
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def _onProjectBasicInfoLoaded(self, response):
        """项目基本信息加载成功回调"""
        import logging
        logger = logging.getLogger(__name__)

        # 隐藏加载动画
        self.hide_loading()

        self.project_data = response

        # 调试日志：检查API返回的数据
        blueprint = self.project_data.get('blueprint', {})
        chapter_outline = blueprint.get('chapter_outline', [])
        logger.info(
            f"loadProjectBasicInfo: project_id={self.project_id}, "
            f"status={self.project_data.get('status')}, "
            f"blueprint存在={bool(blueprint)}, "
            f"chapter_outline数量={len(chapter_outline)}"
        )

        # 更新Header信息
        title = self.project_data.get('title', '未命名项目')
        self.project_title.setText(title)

        genre = self.project_data.get('blueprint', {}).get('genre', '未知类型')
        status = self.project_data.get('status', 'draft')

        self.genre_tag.setText(genre)
        self.status_tag.setText(get_project_status_text(status))

        # 根据状态更新状态标签样式
        self._updateStatusTagStyle(status)

        # 根据项目类型动态调整按钮可见性
        is_imported = self.project_data.get('is_imported', False)
        analysis_status = self.project_data.get('import_analysis_status', '')
        analysis_completed = analysis_status == 'completed'

        # 导入项目且分析未完成时的按钮逻辑
        if is_imported and not analysis_completed:
            # 显示"开始分析"或"继续分析"按钮
            if hasattr(self, 'analyze_btn') and self.analyze_btn:
                self.analyze_btn.setVisible(True)
                if analysis_status == 'analyzing':
                    self.analyze_btn.setText("分析中...")
                    self.analyze_btn.setEnabled(False)
                elif analysis_status in ('failed', 'cancelled'):
                    # 之前分析中断，显示"继续分析"
                    self.analyze_btn.setText("继续分析")
                    self.analyze_btn.setEnabled(True)
                else:
                    self.analyze_btn.setText("开始分析")
                    self.analyze_btn.setEnabled(True)
            # 隐藏"优化蓝图"按钮（没有蓝图可优化）
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setVisible(False)
            # 隐藏"开始创作"按钮（还没分析完）
            if hasattr(self, 'create_btn') and self.create_btn:
                self.create_btn.setVisible(False)
        else:
            # 非导入项目或分析已完成
            if hasattr(self, 'analyze_btn') and self.analyze_btn:
                self.analyze_btn.setVisible(False)
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setVisible(True)
            if hasattr(self, 'create_btn') and self.create_btn:
                self.create_btn.setVisible(True)

        # 加载头像（如果有）
        blueprint = self.project_data.get('blueprint', {})
        avatar_svg = blueprint.get('avatar_svg') if blueprint else None
        self._loadAvatar(avatar_svg)

        # 刷新当前显示的section（因为初始加载时project_data还是空的）
        if self.active_section in self.section_widgets:
            # 删除旧的section，重新创建
            old_widget = self.section_widgets.pop(self.active_section)
            self.content_stack.removeWidget(old_widget)
            old_widget.deleteLater()
        self.loadSection(self.active_section)

    def _onProjectBasicInfoError(self, error_msg):
        """项目基本信息加载失败回调"""
        import logging
        logger = logging.getLogger(__name__)

        # 隐藏加载动画
        self.hide_loading()

        logger.error(f"加载项目基本信息失败: {error_msg}")
        MessageService.show_error(self, f"加载项目失败：\n\n{error_msg}", "错误")

    def _updateStatusTagStyle(self, status):
        """根据状态更新状态标签样式"""
        if status == 'completed':
            bg_color = theme_manager.SUCCESS_BG
            text_color = theme_manager.SUCCESS
        elif status == 'writing':
            bg_color = theme_manager.INFO_BG
            text_color = theme_manager.INFO
        elif status in ['blueprint_ready', 'chapter_outlines_ready', 'part_outlines_ready']:
            bg_color = theme_manager.WARNING_BG
            text_color = theme_manager.WARNING
        else:
            bg_color = theme_manager.BG_TERTIARY
            text_color = theme_manager.TEXT_SECONDARY

        self.status_tag.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            padding: {dp(4)}px {dp(12)}px;
            border-radius: {dp(4)}px;
            font-size: {sp(12)}px;
            font-weight: 500;
        """)

    def _loadAvatar(self, avatar_svg: str = None):
        """加载并显示头像SVG

        Args:
            avatar_svg: SVG字符串，为None时显示占位符
        """
        import logging
        logger = logging.getLogger(__name__)

        if avatar_svg:
            try:
                # 使用QSvgRenderer验证SVG有效性
                from PyQt6.QtSvg import QSvgRenderer
                svg_bytes = QByteArray(avatar_svg.encode('utf-8'))
                renderer = QSvgRenderer(svg_bytes)

                if renderer.isValid():
                    # SVG有效，加载到widget
                    self.avatar_svg_widget.load(svg_bytes)
                    self.avatar_svg_widget.setVisible(True)
                    self.icon_placeholder.setVisible(False)
                    self.icon_container.setToolTip("点击重新生成头像")
                    # 强制重绘确保显示更新
                    self.avatar_svg_widget.update()
                    self.avatar_svg_widget.repaint()
                    logger.debug(f"头像SVG加载成功, size={len(avatar_svg)}")
                else:
                    # SVG无效，显示占位符并记录警告
                    logger.warning(f"头像SVG无效，无法渲染: size={len(avatar_svg)}, preview={avatar_svg[:100]}...")
                    self._showAvatarPlaceholder()
            except Exception as e:
                logger.error(f"加载头像SVG失败: {e}")
                self._showAvatarPlaceholder()
        else:
            self._showAvatarPlaceholder()

    def _showAvatarPlaceholder(self):
        """显示头像占位符"""
        self.avatar_svg_widget.setVisible(False)
        self.icon_placeholder.setVisible(True)
        # 使用项目标题首字作为占位符
        if self.project_data:
            title = self.project_data.get('title', 'B')
            first_char = title[0] if title else 'B'
            self.icon_placeholder.setText(first_char)
        self.icon_container.setToolTip("点击生成小说头像")

    def _onIconClicked(self, event):
        """点击头像图标时触发生成"""
        import logging
        logger = logging.getLogger(__name__)

        # 检查是否有蓝图
        if not self.project_data or not self.project_data.get('blueprint'):
            MessageService.show_warning(self, "请先生成蓝图后再生成头像", "提示")
            return

        # 确认生成
        blueprint = self.project_data.get('blueprint', {})
        has_avatar = blueprint.get('avatar_svg') is not None

        if has_avatar:
            if not confirm(self, "确定要重新生成头像吗？\n当前头像将被替换。", "重新生成头像"):
                return

        logger.info(f"开始生成头像: project_id={self.project_id}")
        self._generateAvatar()

    def _generateAvatar(self):
        """执行头像生成（异步）"""
        from components.dialogs import LoadingDialog

        # 创建加载对话框
        self._avatar_loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在生成小说头像...",
            cancelable=True
        )
        self._avatar_loading_dialog.show()

        # 创建异步worker
        self._avatar_worker = AsyncAPIWorker(
            self.api_client.generate_avatar,
            self.project_id
        )

        self._avatar_worker.success.connect(self._onAvatarGenerated)
        self._avatar_worker.error.connect(self._onAvatarGenerateError)
        self._avatar_loading_dialog.rejected.connect(self._onAvatarGenerateCancelled)

        # 保持worker引用
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(self._avatar_worker)

        self._avatar_worker.start()

    def _onAvatarGenerated(self, result):
        """头像生成成功回调"""
        import logging
        logger = logging.getLogger(__name__)

        # 关闭加载对话框
        if hasattr(self, '_avatar_loading_dialog') and self._avatar_loading_dialog:
            self._avatar_loading_dialog.close()

        avatar_svg = result.get('avatar_svg')
        animal_cn = result.get('animal_cn', '小动物')

        logger.info(f"头像生成成功: animal={result.get('animal')}, animal_cn={animal_cn}")

        # 更新显示
        self._loadAvatar(avatar_svg)

        # 更新本地缓存的项目数据
        if self.project_data and self.project_data.get('blueprint'):
            self.project_data['blueprint']['avatar_svg'] = avatar_svg
            self.project_data['blueprint']['avatar_animal'] = result.get('animal')

        MessageService.show_success(self, f"已生成{animal_cn}头像")

    def _onAvatarGenerateError(self, error_msg):
        """头像生成失败回调"""
        import logging
        logger = logging.getLogger(__name__)

        # 关闭加载对话框
        if hasattr(self, '_avatar_loading_dialog') and self._avatar_loading_dialog:
            self._avatar_loading_dialog.close()

        logger.error(f"头像生成失败: {error_msg}")
        MessageService.show_api_error(self, error_msg, "生成头像")

    def _onAvatarGenerateCancelled(self):
        """头像生成取消回调"""
        import logging
        logger = logging.getLogger(__name__)

        if hasattr(self, '_avatar_worker') and self._avatar_worker:
            try:
                if self._avatar_worker.isRunning():
                    self._avatar_worker.cancel()
                    self._avatar_worker.quit()
                    self._avatar_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass

        logger.info("头像生成已取消")

    def refreshProject(self):
        """刷新项目数据"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"refreshProject被调用: project_id={self.project_id}, active_section={self.active_section}")

        # 保存当前section的状态（如tab索引）
        saved_section_state = {}
        if self.active_section == 'chapter_outline' and 'chapter_outline' in self.section_widgets:
            section = self.section_widgets['chapter_outline']
            if hasattr(section, 'getCurrentTabIndex'):
                saved_section_state['tab_index'] = section.getCurrentTabIndex()
                logger.info(f"保存章节大纲tab状态: tab_index={saved_section_state['tab_index']}")

        # 保存状态到实例变量，供后续创建section时使用
        self._saved_section_state = saved_section_state

        # 安全地停止所有section的异步任务
        for section_id, widget in list(self.section_widgets.items()):
            try:
                if widget is not None and hasattr(widget, 'stopAllTasks'):
                    widget.stopAllTasks()
            except RuntimeError:
                logger.debug(f"section {section_id} 已被删除，跳过清理")
            except Exception as e:
                logger.warning(f"停止section {section_id} 异步任务时出错: {e}")

        # 清除缓存的Section widgets
        self.section_widgets.clear()

        # 安全地移除content_stack中的widgets
        while self.content_stack.count() > 0:
            try:
                widget = self.content_stack.widget(0)
                if widget is not None:
                    self.content_stack.removeWidget(widget)
                    widget.deleteLater()
                else:
                    # widget为None，直接跳出循环避免无限循环
                    break
            except RuntimeError:
                logger.debug("widget已被删除，跳过")
                break
            except Exception as e:
                logger.warning(f"移除widget时出错: {e}")
                break

        # 重新加载
        try:
            logger.info("开始重新加载项目基本信息")
            self.loadProjectBasicInfo()
            logger.info(f"重新加载section: {self.active_section}")
            self.loadSection(self.active_section)
            logger.info("refreshProject完成")
        except Exception as e:
            logger.error(f"刷新项目数据时出错: {e}", exc_info=True)

    def editProjectTitle(self):
        """编辑项目标题"""
        from components.dialogs import InputDialog
        current_title = self.project_data.get('title', '') if self.project_data else ''
        new_title, ok = InputDialog.getTextStatic(
            parent=self,
            title="编辑项目标题",
            label="请输入新标题：",
            text=current_title
        )

        if ok and new_title:
            @handle_errors("更新标题")
            def _update_title():
                self.api_client.update_project(self.project_id, {'title': new_title})
                self.project_title.setText(new_title)
                MessageService.show_operation_success(self, "标题更新")

            _update_title()

    def openWritingDesk(self):
        """打开写作台"""
        if not self._checkUnsavedChanges():
            return
        self.navigateTo('WRITING_DESK', project_id=self.project_id)

    def goBackToWorkspace(self):
        """返回首页"""
        if not self._checkUnsavedChanges():
            return
        self.navigateTo('HOME')

    def goToWorkspace(self):
        """返回首页"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("goToWorkspace called, navigating to HOME")
        if not self._checkUnsavedChanges():
            return
        self.navigateTo('HOME')

    def _updateSaveButtonStyle(self):
        """更新保存按钮样式和状态"""
        if not hasattr(self, 'save_btn') or not self.save_btn:
            return

        ui_font = theme_manager.ui_font()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()

        is_dirty = self.dirty_tracker.is_dirty()
        self.save_btn.setEnabled(is_dirty)

        if is_dirty:
            # 有修改时，高亮显示
            self.save_btn.setText("保存*")
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent_color};
                    color: #FFFFFF;
                    border: 1px solid {accent_color};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    padding: {dp(6)}px {dp(12)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                    border-color: {text_primary};
                }}
            """)
        else:
            # 无修改时，普通样式
            self.save_btn.setText("保存")
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    padding: {dp(6)}px {dp(12)}px;
                }}
                QPushButton:hover {{
                    color: {accent_color};
                    border-color: {accent_color};
                    background-color: rgba(0,0,0,0.05);
                }}
                QPushButton:disabled {{
                    color: {border_color};
                    border-color: {border_color};
                    background-color: transparent;
                }}
            """)

    def onEditRequested(self, field, label, value):
        """处理编辑请求 - 暂存修改，不立即保存

        支持的字段类型：
        1. 章节大纲: chapter_outline:N
        2. 简单文本字段: one_sentence_summary, genre, style, tone, target_audience, full_synopsis
        3. 世界观文本字段: world_setting.core_rules
        4. 世界观列表字段: world_setting.key_locations, world_setting.factions
        5. 角色列表: characters
        6. 关系列表: relationships
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"onEditRequested: field={field}, label={label}, value_type={type(value).__name__}")

        # 1. 章节大纲编辑请求（来自ChapterOutlineSection）
        if field.startswith('chapter_outline:'):
            self._stageChapterOutlineEdit(value)
            return

        # 2. 世界观相关字段
        if field.startswith('world_setting.'):
            self._handleWorldSettingEdit(field, label, value)
            return

        # 3. 角色列表
        if field == 'characters':
            self._handleCharactersEdit(label, value)
            return

        # 4. 关系列表
        if field == 'relationships':
            self._handleRelationshipsEdit(label, value)
            return

        # 5. 简单蓝图字段 - 使用EditDialog
        self._handleSimpleFieldEdit(field, label, value)

    def _handleSimpleFieldEdit(self, field, label, value):
        """处理简单文本字段编辑"""
        # 确定是否多行编辑（长文本字段）
        multiline_fields = ['full_synopsis', 'one_sentence_summary']
        multiline = field in multiline_fields

        # 显示编辑对话框
        dialog = EditDialog(label, value, multiline=multiline, parent=self)
        if dialog.exec() != EditDialog.DialogCode.Accepted:
            return

        new_value = dialog.getValue()
        if not new_value or new_value == str(value):
            return

        # 暂存修改到脏数据追踪器
        self._stageFieldEdit(field, value, new_value, label)

    def _handleWorldSettingEdit(self, field, label, value):
        """处理世界观字段编辑"""
        # world_setting.core_rules - 文本字段
        if field == 'world_setting.core_rules':
            dialog = EditDialog(label, value or '', multiline=True, parent=self)
            if dialog.exec() != EditDialog.DialogCode.Accepted:
                return

            new_value = dialog.getValue()
            if new_value == (value or ''):
                return

            self._stageFieldEdit(field, value, new_value, label)
            return

        # world_setting.key_locations, world_setting.factions - 列表字段
        if field in ['world_setting.key_locations', 'world_setting.factions']:
            from .list_edit_dialog import ListEditDialog

            items = value if isinstance(value, list) else []
            dialog = ListEditDialog(
                title=f"编辑{label}",
                items=items,
                item_fields=['name', 'description'],
                field_labels={'name': '名称', 'description': '描述'},
                parent=self
            )

            if dialog.exec() != ListEditDialog.DialogCode.Accepted:
                return

            new_items = dialog.get_items()
            # 简单比较（可能不完美但足够）
            if new_items == items:
                return

            self._stageFieldEdit(field, value, new_items, label)

    def _handleCharactersEdit(self, label, value):
        """处理角色列表编辑"""
        from .character_edit_dialog import CharacterListEditDialog

        characters = value if isinstance(value, list) else []
        dialog = CharacterListEditDialog(characters=characters, parent=self)

        if dialog.exec() != CharacterListEditDialog.DialogCode.Accepted:
            return

        new_characters = dialog.get_characters()
        if new_characters == characters:
            return

        self._stageFieldEdit('characters', value, new_characters, label)

    def _handleRelationshipsEdit(self, label, value):
        """处理关系列表编辑"""
        from .relationship_edit_dialog import RelationshipListEditDialog

        # 获取角色列表用于选择
        characters = []
        if self.project_data and self.project_data.get('blueprint'):
            characters = self.project_data['blueprint'].get('characters', [])

        relationships = value if isinstance(value, list) else []
        dialog = RelationshipListEditDialog(
            relationships=relationships,
            characters=characters,
            parent=self
        )

        if dialog.exec() != RelationshipListEditDialog.DialogCode.Accepted:
            return

        new_relationships = dialog.get_relationships()
        if new_relationships == relationships:
            return

        self._stageFieldEdit('relationships', value, new_relationships, label)

    def _stageChapterOutlineEdit(self, edit_data: dict):
        """暂存章节大纲编辑（不立即保存到后端）"""
        chapter_number = edit_data.get('chapter_number')
        original_title = edit_data.get('original_title', '')
        original_summary = edit_data.get('original_summary', '')
        new_title = edit_data.get('new_title', '')
        new_summary = edit_data.get('new_summary', '')

        # 标记为脏数据
        self.dirty_tracker.mark_outline_dirty(
            chapter_number=chapter_number,
            original_title=original_title,
            original_summary=original_summary,
            current_title=new_title,
            current_summary=new_summary,
            is_new=False
        )

        # 更新保存按钮状态
        self._updateSaveButtonStyle()

    def _stageFieldEdit(self, field, original_value, new_value, label):
        """暂存字段修改（不立即保存到后端）

        支持的字段类型：
        1. 简单蓝图字段: one_sentence_summary, genre, style, tone, target_audience, full_synopsis, title
        2. 世界观字段: world_setting.core_rules, world_setting.key_locations, world_setting.factions
        3. 复杂列表字段: characters, relationships
        """
        # 所有支持的字段
        simple_blueprint_fields = [
            'one_sentence_summary', 'genre', 'style', 'tone',
            'target_audience', 'full_synopsis', 'title'
        ]
        world_setting_fields = [
            'world_setting.core_rules',
            'world_setting.key_locations',
            'world_setting.factions'
        ]
        complex_list_fields = ['characters', 'relationships']

        all_supported_fields = simple_blueprint_fields + world_setting_fields + complex_list_fields

        if field not in all_supported_fields:
            MessageService.show_warning(self, f"暂不支持编辑该字段：{label}", "提示")
            return

        # 标记为脏数据
        self.dirty_tracker.mark_field_dirty(
            section=self.active_section,
            field=field,
            original_value=original_value,
            current_value=new_value
        )

        # 更新保存按钮状态
        self._updateSaveButtonStyle()

        # 更新当前section的显示（本地更新，不重新从后端加载）
        self._updateSectionDisplay(field, new_value)

    def _updateSectionDisplay(self, field, new_value):
        """更新当前section的显示（本地更新）

        支持的字段类型：
        1. 简单蓝图字段: one_sentence_summary, genre, style, tone等
        2. 世界观字段: world_setting.core_rules, world_setting.key_locations等
        3. 复杂列表字段: characters, relationships
        """
        if not self.project_data or not self.project_data.get('blueprint'):
            return

        blueprint = self.project_data.get('blueprint', {})

        # 更新本地缓存
        if field.startswith('world_setting.'):
            # 世界观嵌套字段
            sub_field = field.replace('world_setting.', '')
            if 'world_setting' not in blueprint:
                blueprint['world_setting'] = {}
            blueprint['world_setting'][sub_field] = new_value
        else:
            # 简单字段或复杂列表字段
            blueprint[field] = new_value

        # 刷新对应的section显示
        if self.active_section not in self.section_widgets:
            return

        widget = self.section_widgets[self.active_section]
        scroll_widget = widget.widget()
        if not scroll_widget:
            return

        layout = scroll_widget.layout()
        if not layout or layout.count() == 0:
            return

        section = layout.itemAt(0).widget()

        # 尝试调用section的局部更新方法
        if hasattr(section, 'updateField'):
            section.updateField(field, new_value)
        elif hasattr(section, 'updateData'):
            # 根据当前section类型调用updateData
            if self.active_section == 'overview':
                section.updateData(blueprint)
            elif self.active_section == 'world_setting':
                world_setting = blueprint.get('world_setting', {})
                section.updateData(world_setting)
            elif self.active_section == 'characters':
                characters = blueprint.get('characters', [])
                section.updateData(characters)
            elif self.active_section == 'relationships':
                relationships = blueprint.get('relationships', [])
                section.updateData(relationships)

    def onSaveAll(self):
        """批量保存所有修改"""
        if not self.dirty_tracker.is_dirty():
            MessageService.show_info(self, "没有需要保存的修改", "提示")
            return

        # 获取脏数据
        dirty_data = self.dirty_tracker.get_dirty_data()
        summary = self.dirty_tracker.get_dirty_summary()

        import logging
        logger = logging.getLogger(__name__)
        logger.info("开始批量保存: %s", summary)

        # 异步保存
        self._doSaveAll(dirty_data)

    def _doSaveAll(self, dirty_data):
        """执行批量保存（异步）"""
        from components.dialogs import LoadingDialog

        # 创建加载对话框
        loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在保存修改...",
            cancelable=False
        )
        loading_dialog.show()

        # 创建异步worker
        worker = AsyncAPIWorker(
            self.api_client.batch_update_blueprint,
            self.project_id,
            dirty_data.get("blueprint_updates"),
            dirty_data.get("chapter_outline_updates")
        )

        def on_success(result):
            loading_dialog.close()
            # 重置脏数据追踪器
            self.dirty_tracker.reset()
            # 更新保存按钮状态
            self._updateSaveButtonStyle()
            # 更新本地数据
            self.project_data = result
            # 刷新当前section
            self._refreshCurrentSection()
            MessageService.show_success(self, "保存成功")

        def on_error(error_msg):
            loading_dialog.close()
            MessageService.show_api_error(self, error_msg, "保存修改")

        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def _checkUnsavedChanges(self) -> bool:
        """检查未保存的修改，返回是否可以继续

        Returns:
            True: 可以继续（无修改或用户选择不保存/已保存）
            False: 用户取消操作
        """
        if not self.dirty_tracker.is_dirty():
            return True

        summary = self.dirty_tracker.get_dirty_summary()

        # 显示三按钮对话框
        from components.dialogs import SaveDiscardDialog, SaveDiscardResult

        dialog = SaveDiscardDialog(
            parent=self,
            title="确认离开",
            message=f"有未保存的修改（{summary}）",
            detail="是否保存修改？",
            save_text="保存",
            discard_text="不保存",
            cancel_text="取消"
        )

        result = dialog.exec()

        if result == SaveDiscardResult.SAVE:
            # 同步保存（阻塞）
            try:
                dirty_data = self.dirty_tracker.get_dirty_data()
                self.api_client.batch_update_blueprint(
                    self.project_id,
                    dirty_data.get("blueprint_updates"),
                    dirty_data.get("chapter_outline_updates")
                )
                self.dirty_tracker.reset()
                return True
            except Exception as e:
                MessageService.show_error(self, f"保存失败：{str(e)}", "错误")
                return False
        elif result == SaveDiscardResult.DISCARD:
            # 不保存，直接继续
            self.dirty_tracker.reset()
            return True
        else:
            # 取消
            return False

    @handle_errors("保存修改")
    def _saveFieldEdit(self, field, new_value, label):
        """保存字段修改到后端（已废弃，保留兼容性）"""
        # 构建更新数据
        blueprint_fields = [
            'one_sentence_summary', 'genre', 'style', 'tone',
            'target_audience', 'full_synopsis'
        ]

        if field in blueprint_fields:
            update_data = {field: new_value}
            self.api_client.update_blueprint(self.project_id, update_data)
        else:
            MessageService.show_warning(self, f"暂不支持编辑该字段：{label}", "提示")
            return

        MessageService.show_operation_success(self, f"{label}更新")
        self._refreshCurrentSection()

    def _refreshCurrentSection(self):
        """刷新当前显示的section"""
        # 重新加载项目数据
        response = self.api_client.get_novel(self.project_id)
        self.project_data = response

        # 如果当前section已缓存且支持updateData，使用updateData更新
        if self.active_section in self.section_widgets:
            widget = self.section_widgets[self.active_section]

            # 获取内部的section组件（在QScrollArea内）
            scroll_widget = widget.widget()
            if scroll_widget:
                layout = scroll_widget.layout()
                if layout and layout.count() > 0:
                    section = layout.itemAt(0).widget()

                    if self.active_section == 'overview' and hasattr(section, 'updateData'):
                        blueprint = self.project_data.get('blueprint', {})
                        section.updateData(blueprint)
                        return
                    elif self.active_section == 'world_setting' and hasattr(section, 'updateData'):
                        world_setting = self.project_data.get('blueprint', {}).get('world_setting', {})
                        section.updateData(world_setting)
                        return
                    elif self.active_section == 'characters' and hasattr(section, 'updateData'):
                        characters = self.project_data.get('blueprint', {}).get('characters', [])
                        section.updateData(characters)
                        return
                    elif self.active_section == 'relationships' and hasattr(section, 'updateData'):
                        relationships = self.project_data.get('blueprint', {}).get('relationships', [])
                        section.updateData(relationships)
                        return
                    elif self.active_section == 'chapter_outline' and hasattr(section, 'updateData'):
                        blueprint = self.project_data.get('blueprint', {})
                        # 章节大纲在 blueprint.chapter_outline 中，不是顶层 chapter_outlines
                        outline = blueprint.get('chapter_outline', [])
                        section.updateData(outline, blueprint)
                        return
                    elif self.active_section == 'chapters' and hasattr(section, 'updateData'):
                        chapters = self.project_data.get('chapters', [])
                        section.updateData(chapters)
                        return

            # 如果不支持updateData，重建section
            if hasattr(widget, 'stopAllTasks'):
                widget.stopAllTasks()

            self.content_stack.removeWidget(widget)
            widget.deleteLater()
            del self.section_widgets[self.active_section]

        self.loadSection(self.active_section)

    def exportNovel(self, format_type):
        """导出小说"""
        @handle_errors("导出小说")
        def _export():
            response = self.api_client.export_novel(self.project_id, format_type)

            file_filter = "文本文件 (*.txt)" if format_type == 'txt' else "Markdown文件 (*.md)"
            default_name = f"{self.project_data.get('title', '小说')}.{format_type if format_type == 'md' else 'txt'}"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存导出文件",
                default_name,
                file_filter
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response)
                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")

        _export()

    def onRefineBlueprint(self):
        """优化蓝图"""
        # 检查是否有蓝图
        if not self.project_data or not self.project_data.get('blueprint'):
            MessageService.show_warning(self, "请先生成蓝图后再进行优化", "提示")
            return

        # 显示优化对话框
        dialog = RefineDialog(self)
        if dialog.exec() != RefineDialog.DialogCode.Accepted:
            return

        instruction = dialog.getValue()
        if not instruction:
            MessageService.show_warning(self, "请输入优化指令", "提示")
            return

        # 执行优化
        self._doRefineBlueprint(instruction)

    def _doRefineBlueprint(self, instruction, force=False):
        """执行蓝图优化(异步方式, 不阻塞UI)

        Args:
            instruction: 优化指令
            force: 是否强制优化(将删除所有章节大纲, 部分大纲, 章节内容)
        """
        # 创建加载提示对话框
        from components.dialogs import LoadingDialog
        loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在优化蓝图...",
            cancelable=True
        )
        loading_dialog.show()

        # 禁用优化按钮，防止重复点击
        if hasattr(self, 'refine_btn') and self.refine_btn:
            self.refine_btn.setEnabled(False)

        # 清理之前的worker（如果有）
        if hasattr(self, 'refine_worker') and self.refine_worker is not None:
            try:
                if self.refine_worker.isRunning():
                    self.refine_worker.cancel()
                    self.refine_worker.quit()
                    self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                # Worker已被删除，忽略
                pass
            self.refine_worker = None

        # 创建异步worker（传递force参数）
        self.refine_worker = AsyncAPIWorker(
            self.api_client.refine_blueprint,
            self.project_id,
            instruction,
            force=force
        )

        # 成功回调
        def on_success(result):
            loading_dialog.close()
            # 恢复按钮状态
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setEnabled(True)
            # 显示成功消息
            ai_message = result.get('ai_message', '蓝图优化完成')
            MessageService.show_success(self, ai_message)
            # 刷新页面
            self.refreshProject()

        # 错误回调
        def on_error(error_msg):
            loading_dialog.close()
            # 恢复按钮状态
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setEnabled(True)

            # 检查是否是冲突错误（已有章节大纲）
            if "已有" in error_msg and "章节大纲" in error_msg:
                # 显示确认对话框，明确告知会删除所有数据
                if confirm(
                    self,
                    "检测到项目已有章节大纲。\n\n" 
                    "优化蓝图将会删除以下所有数据：\n" 
                    "• 所有章节大纲\n" 
                    "• 所有部分大纲（如有）\n" 
                    "• 所有已生成的章节内容\n" 
                    "• 所有章节版本\n" 
                    "• 向量库数据\n\n" 
                    "此操作不可恢复，确定要继续吗？",
                    "确认优化蓝图"
                ):
                    # 用户确认，强制优化
                    self._doRefineBlueprint(instruction, force=True)
            else:
                # 其他错误，直接显示
                MessageService.show_api_error(self, error_msg, "优化蓝图")

        # 取消回调
        def on_cancel():
            try:
                if self.refine_worker and self.refine_worker.isRunning():
                    self.refine_worker.cancel()
                    self.refine_worker.quit()
                    self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass  # C++ 对象已被删除，忽略
            # 恢复按钮状态
            if hasattr(self, 'refine_btn') and self.refine_btn:
                self.refine_btn.setEnabled(True)

        self.refine_worker.success.connect(on_success)
        self.refine_worker.error.connect(on_error)
        loading_dialog.rejected.connect(on_cancel)
        self.refine_worker.start()

    def refresh(self, **params):
        """页面刷新"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            self.refreshProject()

        # 支持通过section参数切换到指定Tab
        if 'section' in params:
            section_id = params['section']
            # 验证section_id是否有效
            valid_sections = ['overview', 'world_setting', 'characters', 'relationships', 'chapter_outline', 'chapters']
            if section_id in valid_sections:
                self.switchSection(section_id)

    def onHide(self):
        """页面隐藏时清理资源"""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("NovelDetail.onHide() called for project_id=%s", self.project_id)

        # 清理蓝图优化worker
        try:
            if self.refine_worker and self.refine_worker.isRunning():
                self.refine_worker.cancel()
                self.refine_worker.quit()
                self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
        except RuntimeError:
            pass  # C++对象已被删除，忽略
        except Exception as e:
            logger.warning("清理refine_worker时出错: %s", str(e))
        finally:
            self.refine_worker = None

        # 安全地清理所有section widgets
        try:
            for section_id, section in self.section_widgets.items():
                try:
                    if section is not None and hasattr(section, 'cleanup'):
                        section.cleanup()
                except RuntimeError:
                    # C++对象已被删除
                    logger.debug("%s section已被删除，跳过清理", section_id)
                except Exception as e:
                    logger.warning("清理%s section时出错: %s", section_id, str(e))
        except Exception as e:
            logger.warning("访问section_widgets时出错: %s", str(e))

        logger.debug("NovelDetail.onHide() completed")

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 检查未保存的修改
        if self.dirty_tracker.is_dirty():
            if not self._checkUnsavedChanges():
                event.ignore()
                return
        self.onHide()
        super().closeEvent(event)

    def onStartAnalysis(self):
        """开始分析导入的小说"""
        import logging
        logger = logging.getLogger(__name__)

        # 检查是否是继续分析（之前中断过）
        analysis_status = self.project_data.get('import_analysis_status', '')
        is_resume = analysis_status in ('failed', 'cancelled')

        # 根据状态显示不同的确认对话框
        if is_resume:
            confirm_message = (
                "检测到之前的分析进度，将从断点继续：\n\n"
                "- 已生成的分析数据会被保留\n"
                "- 已生成的章节摘要会被复用\n"
                "- 只处理未完成的内容\n\n"
                "确定要继续分析吗？"
            )
            confirm_title = "确认继续分析"
        else:
            confirm_message = (
                "将开始分析导入的小说内容，包括：\n\n"
                "1. 逐章生成分析数据\n"
                "2. 逐章生成章节摘要\n"
                "3. 更新章节大纲\n"
                "4. 生成分部大纲（长篇）\n"
                "5. 反推蓝图信息\n\n"
                "此过程可能需要较长时间，确定要开始吗？"
            )
            confirm_title = "确认开始分析"

        if not confirm(self, confirm_message, confirm_title):
            return

        logger.info(f"{'继续' if is_resume else '开始'}分析导入项目: project_id={self.project_id}")

        # 禁用按钮
        if hasattr(self, 'analyze_btn') and self.analyze_btn:
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.setText("启动中...")

        # 异步启动分析
        self._doStartAnalysis()

    def _doStartAnalysis(self):
        """执行启动分析"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)

        logger.info("=== _doStartAnalysis 开始 ===")
        print("=== DEBUG: _doStartAnalysis 开始 ===")

        def start_analysis():
            logger.info("start_analysis 函数被调用")
            print("DEBUG: start_analysis 函数被调用")
            result = self.api_client.start_import_analysis(self.project_id)
            logger.info(f"API 返回: {result}")
            print(f"DEBUG: API 返回: {result}")
            return result

        def on_success(result):
            try:
                logger.info(f"=== on_success 回调开始 ===")
                print(f"=== DEBUG: on_success 回调开始 ===")
                logger.info(f"分析任务启动成功: {result}")
                print(f"DEBUG: 分析任务启动成功: {result}")
                # 显示进度对话框
                logger.info("即将调用 _showAnalysisProgressDialog...")
                print("DEBUG: 即将调用 _showAnalysisProgressDialog...")
                self._showAnalysisProgressDialog()
                logger.info("_showAnalysisProgressDialog 返回")
                print("DEBUG: _showAnalysisProgressDialog 返回")
            except Exception as e:
                logger.error(f"on_success 回调异常: {e}")
                logger.error(traceback.format_exc())
                print(f"DEBUG ERROR: on_success 回调异常: {e}")
                print(traceback.format_exc())

        def on_error(error_msg):
            logger.error(f"启动分析失败: {error_msg}")
            print(f"DEBUG ERROR: 启动分析失败: {error_msg}")
            MessageService.show_error(self, f"启动分析失败：{error_msg}", "错误")
            # 恢复按钮状态
            if hasattr(self, 'analyze_btn') and self.analyze_btn:
                self.analyze_btn.setEnabled(True)
                # 根据状态恢复按钮文案
                analysis_status = self.project_data.get('import_analysis_status', '')
                if analysis_status in ('failed', 'cancelled'):
                    self.analyze_btn.setText("继续分析")
                else:
                    self.analyze_btn.setText("开始分析")

        worker = AsyncAPIWorker(start_analysis)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        logger.info("启动 AsyncAPIWorker...")
        print("DEBUG: 启动 AsyncAPIWorker...")
        worker.start()

    def _showAnalysisProgressDialog(self):
        """显示分析进度对话框"""
        import logging
        import traceback
        logger = logging.getLogger(__name__)

        logger.info("=== 开始显示分析进度对话框 ===")
        print("=== DEBUG: 开始显示分析进度对话框 ===")

        try:
            logger.info("导入 ImportProgressDialog...")
            print("DEBUG: 导入 ImportProgressDialog...")
            from components.dialogs import ImportProgressDialog
            logger.info("导入成功")
            print("DEBUG: 导入成功")

            logger.info(f"创建对话框实例: project_id={self.project_id}")
            print(f"DEBUG: 创建对话框实例: project_id={self.project_id}")
            dialog = ImportProgressDialog(
                parent=self,
                project_id=self.project_id,
                api_client=self.api_client
            )
            logger.info("对话框实例创建成功")
            print("DEBUG: 对话框实例创建成功")

            # 对话框关闭后刷新页面
            logger.info("调用 dialog.exec()...")
            print("DEBUG: 调用 dialog.exec()...")
            result = dialog.exec()
            logger.info(f"dialog.exec() 返回: {result}")
            print(f"DEBUG: dialog.exec() 返回: {result}")

            if dialog.was_completed():
                MessageService.show_success(self, "分析完成！")
                # 刷新项目数据
                self.refreshProject()
            elif dialog.was_cancelled():
                MessageService.show_info(self, "分析已取消")
                # 刷新项目数据以更新状态
                self.loadProjectBasicInfo()

        except Exception as e:
            logger.error(f"显示进度对话框时发生异常: {e}")
            logger.error(traceback.format_exc())
            print(f"DEBUG ERROR: 显示进度对话框时发生异常: {e}")
            print(traceback.format_exc())
            MessageService.show_error(self, f"显示进度对话框失败：{e}", "错误")