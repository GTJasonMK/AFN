"""
提示词管理界面 - 分层标签页结构

支持多项目类型（小说/编程），每个项目类型下有子分类标签页。
便于后续扩展新的项目类型。
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QTabWidget, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from utils.error_handler import handle_errors
from .dialogs import PromptEditDialog
from .ui_helpers import (
    build_settings_primary_button_style,
    build_settings_secondary_button_style,
    force_refresh_widget_style,
)


# 项目类型配置：project_type -> (显示名称, 图标, 顺序)
PROJECT_TYPE_CONFIG = {
    "novel": ("小说项目", None, 1),
    "coding": ("Vibe Coding", None, 2),
}

# 分类配置：project_type -> {category_id -> (显示名称, 顺序)}
CATEGORY_CONFIG = {
    "novel": {
        "inspiration": ("构思", 1),
        "blueprint": ("蓝图", 2),
        "outline": ("大纲", 3),
        "writing": ("写作", 4),
        "analysis": ("分析", 5),
        "manga": ("漫画", 6),
        "protagonist": ("主角", 7),
    },
    "coding": {
        "coding": ("全部", 1),  # 编程类型暂时只有一个分类
    },
}

# 分类到项目类型的映射（用于快速查找）
CATEGORY_TO_PROJECT = {}
for project_type, categories in CATEGORY_CONFIG.items():
    for category in categories:
        CATEGORY_TO_PROJECT[category] = project_type


class PromptListWidget(QWidget):
    """单个类别的提示词列表"""

    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self.category = category
        self.prompts_data = []
        self._create_ui()

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, dp(8), 0, 0)
        layout.setSpacing(0)

        self.prompt_list = QListWidget()
        self.prompt_list.setObjectName("prompt_list")
        self.prompt_list.setFrameShape(QFrame.Shape.NoFrame)
        self.prompt_list.setSpacing(dp(4))
        layout.addWidget(self.prompt_list)

    def setPrompts(self, prompts: list):
        """设置提示词数据"""
        self.prompts_data = prompts
        self._update_list()

    def _update_list(self):
        """更新列表显示"""
        self.prompt_list.clear()

        for prompt in self.prompts_data:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, dp(72)))
            item.setData(Qt.ItemDataRole.UserRole, prompt)

            title = prompt.get('title') or prompt.get('name', '未命名')
            description = prompt.get('description') or ''
            is_modified = prompt.get('is_modified', False)

            if description and len(description) > 60:
                description = description[:60] + '...'

            modified_mark = ' [已修改]' if is_modified else ''
            display_text = f"{title}{modified_mark}\n{description}"
            item.setText(display_text)

            self.prompt_list.addItem(item)

    def getCurrentPrompt(self):
        """获取当前选中的提示词"""
        current_item = self.prompt_list.currentItem()
        if current_item:
            return current_item.data(Qt.ItemDataRole.UserRole)
        return None

    def applyStyle(self, style: str):
        """应用样式"""
        self.prompt_list.setStyleSheet(style)


class ProjectTypeWidget(QWidget):
    """单个项目类型的容器（包含子分类标签页）"""

    def __init__(self, project_type: str, parent=None):
        super().__init__(parent)
        self.project_type = project_type
        self.category_widgets = {}  # category -> PromptListWidget
        self._create_ui()

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 子分类标签页
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setObjectName("sub_tabs")
        self.sub_tabs.setDocumentMode(True)

        # 获取该项目类型的分类配置
        categories = CATEGORY_CONFIG.get(self.project_type, {})
        sorted_categories = sorted(categories.items(), key=lambda x: x[1][1])

        for category_id, (label, _) in sorted_categories:
            widget = PromptListWidget(category_id, self)
            self.category_widgets[category_id] = widget
            self.sub_tabs.addTab(widget, label)

        layout.addWidget(self.sub_tabs)

    def setPrompts(self, prompts_by_category: dict):
        """设置各分类的提示词数据"""
        for category, widget in self.category_widgets.items():
            widget.setPrompts(prompts_by_category.get(category, []))

    def getCurrentPrompt(self):
        """获取当前选中的提示词"""
        current_widget = self.sub_tabs.currentWidget()
        if isinstance(current_widget, PromptListWidget):
            return current_widget.getCurrentPrompt()
        return None

    def applyListStyle(self, style: str):
        """应用列表样式到所有子分类"""
        for widget in self.category_widgets.values():
            widget.applyStyle(style)

    def applyTabStyle(self, style: str):
        """应用标签页样式"""
        self.sub_tabs.setStyleSheet(style)

    def connectSignals(self, double_click_handler, selection_changed_handler):
        """连接信号"""
        for widget in self.category_widgets.values():
            widget.prompt_list.itemDoubleClicked.connect(double_click_handler)
            widget.prompt_list.currentItemChanged.connect(selection_changed_handler)
        self.sub_tabs.currentChanged.connect(
            lambda _: selection_changed_handler(None, None)
        )


class PromptSettingsWidget(QWidget):
    """提示词管理界面 - 分层标签页结构"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.prompts_data = []
        self.project_widgets = {}  # project_type -> ProjectTypeWidget
        self._create_ui_structure()
        self._apply_styles()

        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 顶部说明
        self.description_label = QLabel(
            "管理系统中的LLM提示词。选择项目类型和分类查看对应的提示词，"
            "修改后的提示词会在系统更新时保留。"
        )
        self.description_label.setWordWrap(True)
        layout.addWidget(self.description_label)

        # 顶层项目类型标签页
        self.main_tabs = QTabWidget()
        self.main_tabs.setObjectName("main_tabs")
        self.main_tabs.setDocumentMode(True)

        # 为每个项目类型创建容器
        sorted_projects = sorted(
            PROJECT_TYPE_CONFIG.items(),
            key=lambda x: x[1][2]
        )
        for project_type, (label, _, _) in sorted_projects:
            widget = ProjectTypeWidget(project_type, self)
            widget.connectSignals(
                self._on_item_double_clicked,
                self._on_selection_changed
            )
            self.project_widgets[project_type] = widget
            self.main_tabs.addTab(widget, label)

        layout.addWidget(self.main_tabs, stretch=1)

        # 底部按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(12))

        self.reset_all_btn = QPushButton("恢复全部默认值")
        self.reset_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        button_layout.addWidget(self.reset_all_btn)

        button_layout.addStretch()

        self.reset_btn = QPushButton("恢复默认值")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._on_reset_single)
        button_layout.addWidget(self.reset_btn)

        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit)
        button_layout.addWidget(self.edit_btn)

        layout.addLayout(button_layout)

        # 连接顶层标签页切换信号
        self.main_tabs.currentChanged.connect(self._on_main_tab_changed)

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 说明文字样式
        self.description_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(13)}px;
                color: {palette.text_tertiary};
                padding: {dp(8)}px 0;
                background: transparent;
            }}
        """)

        # 顶层标签页样式（较大的标签）
        self.main_tabs.setStyleSheet(f"""
            QTabWidget#main_tabs::pane {{
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                background-color: {palette.bg_primary};
            }}
            QTabWidget#main_tabs > QTabBar::tab {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {palette.text_secondary};
                background-color: transparent;
                padding: {dp(10)}px {dp(24)}px;
                margin-right: {dp(8)}px;
                border: 1px solid transparent;
                border-bottom: none;
                border-top-left-radius: {dp(8)}px;
                border-top-right-radius: {dp(8)}px;
            }}
            QTabWidget#main_tabs > QTabBar::tab:selected {{
                color: {palette.accent_color};
                background-color: {palette.bg_primary};
                border-color: {palette.border_color};
            }}
            QTabWidget#main_tabs > QTabBar::tab:hover:!selected {{
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
            }}
        """)

        # 子标签页样式（较小的标签）
        sub_tab_style = f"""
            QTabWidget#sub_tabs::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabWidget#sub_tabs > QTabBar::tab {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_secondary};
                background-color: transparent;
                padding: {dp(6)}px {dp(12)}px;
                margin-right: {dp(2)}px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabWidget#sub_tabs > QTabBar::tab:selected {{
                color: {palette.accent_color};
                border-bottom-color: {palette.accent_color};
            }}
            QTabWidget#sub_tabs > QTabBar::tab:hover:!selected {{
                color: {palette.text_primary};
            }}
        """

        # 列表样式
        list_style = f"""
            QListWidget#prompt_list {{
                background-color: {palette.bg_primary};
                border: none;
                outline: none;
            }}
            QListWidget#prompt_list::item {{
                background-color: transparent;
                color: {palette.text_primary};
                border-bottom: 1px solid {palette.border_color};
                padding: {dp(12)}px {dp(16)}px;
            }}
            QListWidget#prompt_list::item:last-child {{
                border-bottom: none;
            }}
            QListWidget#prompt_list::item:hover {{
                background-color: {palette.bg_secondary};
                color: {palette.text_primary};
            }}
            QListWidget#prompt_list::item:selected {{
                background-color: {palette.accent_light};
                color: {palette.text_primary};
            }}
        """

        # 应用样式到所有项目类型容器
        for widget in self.project_widgets.values():
            widget.applyTabStyle(sub_tab_style)
            widget.applyListStyle(list_style)

        # 次要按钮样式
        secondary_btn_style = build_settings_secondary_button_style(palette) + f"""
            QPushButton:disabled {{
                color: {palette.text_tertiary};
                border-color: {palette.border_color};
            }}
        """
        self.reset_all_btn.setStyleSheet(secondary_btn_style)
        self.reset_btn.setStyleSheet(secondary_btn_style)

        # 主要按钮样式
        primary_btn_style = build_settings_primary_button_style(palette) + f"""
            QPushButton:disabled {{
                background-color: {palette.border_color};
                color: {palette.text_tertiary};
            }}
        """
        self.edit_btn.setStyleSheet(primary_btn_style)

        force_refresh_widget_style(self)

    @handle_errors("加载提示词")
    def loadPrompts(self):
        """加载提示词列表"""
        self.prompts_data = self.api_client.get_prompts()
        self._distribute_prompts()

    def _distribute_prompts(self):
        """将提示词分发到对应的项目类型和分类"""
        # 按项目类型和分类分组
        distributed = {
            project_type: {cat: [] for cat in categories}
            for project_type, categories in CATEGORY_CONFIG.items()
        }

        for prompt in self.prompts_data:
            category = prompt.get('category', '')
            # 优先使用API返回的project_type，回退到本地映射
            project_type = prompt.get('project_type') or CATEGORY_TO_PROJECT.get(category)
            if project_type and category in distributed.get(project_type, {}):
                distributed[project_type][category].append(prompt)

        # 分发到各项目类型Widget
        for project_type, widget in self.project_widgets.items():
            widget.setPrompts(distributed.get(project_type, {}))

    def _on_main_tab_changed(self, index: int):
        """顶层标签页切换时更新按钮状态"""
        self._update_button_state()

    def _on_selection_changed(self, current, previous):
        """选择项变化时更新按钮状态"""
        self._update_button_state()

    def _update_button_state(self):
        """更新按钮状态"""
        # 防护：初始化阶段按钮可能尚未创建
        if not hasattr(self, 'edit_btn') or not hasattr(self, 'reset_btn'):
            return
        prompt = self._get_current_prompt()
        has_selection = prompt is not None
        self.edit_btn.setEnabled(has_selection)
        self.reset_btn.setEnabled(has_selection)

    def _on_item_double_clicked(self, item):
        """双击项时打开编辑"""
        self._on_edit()

    def _get_current_prompt(self):
        """获取当前选中的提示词"""
        current_project_widget = self.main_tabs.currentWidget()
        if isinstance(current_project_widget, ProjectTypeWidget):
            return current_project_widget.getCurrentPrompt()
        return None

    def _on_edit(self):
        """编辑选中的提示词"""
        prompt_data = self._get_current_prompt()
        if not prompt_data:
            return

        dialog = PromptEditDialog(prompt_data, self)
        if dialog.exec():
            # 对话框确认后重新加载
            self.loadPrompts()

    def _on_reset_single(self):
        """恢复单个提示词默认值"""
        prompt_data = self._get_current_prompt()
        if not prompt_data:
            return

        name = prompt_data.get('name', '')
        title = prompt_data.get('title') or name

        # 确认对话框
        if MessageService.confirm(
            self,
            f"确定要将「{title}」恢复到默认值吗？\n您的修改将会丢失。",
            "确认恢复"
        ):
            self._do_reset_single(name)

    @handle_errors("恢复默认值")
    def _do_reset_single(self, name: str):
        """执行单个恢复"""
        self.api_client.reset_prompt(name)
        MessageService.show_success(self, "已恢复默认值")
        self.loadPrompts()

    def _on_reset_all(self):
        """恢复全部提示词默认值"""
        # 确认对话框
        if MessageService.confirm(
            self,
            "确定要将所有提示词恢复到默认值吗？\n您的所有修改将会丢失。",
            "确认恢复全部"
        ):
            self._do_reset_all()

    @handle_errors("恢复全部默认值")
    def _do_reset_all(self):
        """执行全部恢复"""
        result = self.api_client.reset_all_prompts()
        count = result.get('reset_count', 0)
        MessageService.show_success(self, f"已恢复 {count} 个提示词到默认值")
        self.loadPrompts()

    def __del__(self):
        """析构时断开主题信号连接"""
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
