"""
项目详情主页面 - 现代化设计

采用顶部Tab导航，提高空间利用率
集成所有Section组件，提供流畅的浏览体验
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QWidget,
    QScrollArea, QStackedWidget, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
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

        self.setupUI()
        self.loadProjectBasicInfo()
        self.loadSection('overview')

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部Header（项目信息 + 操作按钮）
        self.createHeader()
        main_layout.addWidget(self.header)

        # Tab导航栏
        self.createTabBar()
        main_layout.addWidget(self.tab_bar)

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

        # 项目图标（书本图标）
        icon_container = QFrame()
        icon_container.setFixedSize(dp(64), dp(64))
        icon_container.setObjectName("project_icon")
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("B")  # 使用字母代替emoji
        icon_label.setStyleSheet(f"font-size: {sp(28)}px; font-weight: bold;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)

        left_layout.addWidget(icon_container)

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
        edit_title_btn.setFixedHeight(dp(24))
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
        if hasattr(self, 'create_btn') and self.create_btn:
            self.create_btn.setStyleSheet(primary_btn_style)

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
                section = CharactersSection(data=characters, editable=True)
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

                section = ChapterOutlineSection(outline=outline, blueprint=blueprint, project_id=self.project_id, editable=True)
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

    @handle_errors("加载项目")
    def loadProjectBasicInfo(self):
        """加载项目基本信息"""
        import logging
        logger = logging.getLogger(__name__)

        response = self.api_client.get_novel(self.project_id)
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

    def refreshProject(self):
        """刷新项目数据"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"refreshProject被调用: project_id={self.project_id}, active_section={self.active_section}")

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
        self.navigateTo('WRITING_DESK', project_id=self.project_id)

    def goBackToWorkspace(self):
        """返回首页"""
        self.navigateTo('HOME')

    def goToWorkspace(self):
        """返回首页"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("goToWorkspace called, navigating to HOME")
        self.navigateTo('HOME')

    def onEditRequested(self, field, label, value):
        """处理编辑请求"""
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

        # 保存修改
        self._saveFieldEdit(field, new_value, label)

    @handle_errors("保存修改")
    def _saveFieldEdit(self, field, new_value, label):
        """保存字段修改到后端"""
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
            if self.refine_worker and self.refine_worker.isRunning():
                self.refine_worker.cancel()
                self.refine_worker.quit()
                self.refine_worker.wait(WorkerTimeouts.DEFAULT_MS)
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
        self.onHide()
        super().closeEvent(event)