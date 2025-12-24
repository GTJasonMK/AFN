"""
设置页面主视图 - 书籍风格 (侧边导航布局)
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QListWidget, QStackedWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor
from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from api.manager import APIClientManager
from .llm_settings_widget import LLMSettingsWidget
from .embedding_settings_widget import EmbeddingSettingsWidget
from .advanced_settings_widget import AdvancedSettingsWidget
from .image_settings_widget import ImageSettingsWidget
from .queue_settings_widget import QueueSettingsWidget
from .prompt_settings_widget import PromptSettingsWidget
import json


class SettingsView(BasePage):
    """设置页面 - 书籍风格 (侧边导航布局)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self._create_ui_structure()
        self._apply_theme()
        theme_manager.theme_changed.connect(lambda _: self._apply_theme())

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 主容器
        self.main_container = QWidget()
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(dp(32), dp(24), dp(32), dp(24))
        container_layout.setSpacing(dp(16))

        # 顶部：返回按钮 + 标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(16))

        # 返回按钮
        self.back_btn = QPushButton("< 返回")
        self.back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_btn.clicked.connect(self.goBack)
        header_layout.addWidget(self.back_btn)

        # 页面标题
        self.title_label = QLabel("系统设置")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # 全局导入按钮
        self.global_import_btn = QPushButton("全局导入")
        self.global_import_btn.setObjectName("global_action_btn")
        self.global_import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.global_import_btn.clicked.connect(self._import_all_configs)
        header_layout.addWidget(self.global_import_btn)

        # 全局导出按钮
        self.global_export_btn = QPushButton("全局导出")
        self.global_export_btn.setObjectName("global_action_btn")
        self.global_export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.global_export_btn.clicked.connect(self._export_all_configs)
        header_layout.addWidget(self.global_export_btn)

        container_layout.addLayout(header_layout)

        # 内容区域 - 左右分栏
        content_layout = QHBoxLayout()
        content_layout.setSpacing(dp(24))

        # 左侧：导航列表
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("nav_list")
        self.nav_list.setFixedWidth(dp(180))
        self.nav_list.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setCursor(Qt.CursorShape.PointingHandCursor)

        # 添加导航项
        self._add_nav_item("LLM 服务")
        self._add_nav_item("嵌入模型")
        self._add_nav_item("生图模型")
        self._add_nav_item("请求队列")
        self._add_nav_item("提示词管理")
        self._add_nav_item("高级配置")

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        content_layout.addWidget(self.nav_list)

        # 右侧：内容区域
        self.page_frame = QFrame()
        self.page_frame.setObjectName("page_frame")

        # 添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(dp(16))
        shadow.setXOffset(0)
        shadow.setYOffset(dp(2))
        shadow.setColor(QColor(0, 0, 0, 20))
        self.page_frame.setGraphicsEffect(shadow)

        page_layout = QVBoxLayout(self.page_frame)
        page_layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))  # 修正：20不符合8pt网格，改为24
        page_layout.setSpacing(0)

        # 堆叠页面
        self.page_stack = QStackedWidget()

        self.llm_settings = LLMSettingsWidget()
        self.page_stack.addWidget(self.llm_settings)

        self.embedding_settings = EmbeddingSettingsWidget()
        self.page_stack.addWidget(self.embedding_settings)

        self.image_settings = ImageSettingsWidget()
        self.page_stack.addWidget(self.image_settings)

        self.queue_settings = QueueSettingsWidget()
        self.page_stack.addWidget(self.queue_settings)

        self.prompt_settings = PromptSettingsWidget()
        self.page_stack.addWidget(self.prompt_settings)

        self.advanced_settings = AdvancedSettingsWidget()
        self.page_stack.addWidget(self.advanced_settings)

        page_layout.addWidget(self.page_stack)
        content_layout.addWidget(self.page_frame, stretch=1)

        container_layout.addLayout(content_layout, stretch=1)
        main_layout.addWidget(self.main_container)

        # 默认选中第一项
        self.nav_list.setCurrentRow(0)

    def _add_nav_item(self, title):
        """添加导航项"""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, dp(48)))  # 修正：44不符合8pt网格，改为48
        item.setText(title)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.nav_list.addItem(item)

    def _on_nav_changed(self, row):
        """导航切换"""
        self.page_stack.setCurrentIndex(row)

    def _apply_theme(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 主容器背景
        self.main_container.setStyleSheet(f"""
            QWidget {{
                background-color: {palette.bg_primary};
            }}
        """)

        # 返回按钮
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: none;
                font-size: {sp(14)}px;
                padding: {dp(4)}px {dp(8)}px;
            }}
            QPushButton:hover {{
                color: {palette.accent_color};
            }}
        """)

        # 标题
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.serif_font};
                font-size: {sp(24)}px;
                font-weight: 700;
                color: {palette.text_primary};
            }}
        """)

        # 全局操作按钮样式
        global_btn_style = f"""
            QPushButton#global_action_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}
            QPushButton#global_action_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_secondary};
            }}
        """
        self.global_import_btn.setStyleSheet(global_btn_style)
        self.global_export_btn.setStyleSheet(global_btn_style)

        # 导航列表
        self.nav_list.setStyleSheet(f"""
            QListWidget#nav_list {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QListWidget#nav_list::item {{
                background-color: transparent;
                color: {palette.text_secondary};
                border: none;
                border-left: 2px solid transparent;
                padding: {dp(12)}px {dp(12)}px;  /* 修正：10不符合8pt网格，改为12 */
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
            }}
            QListWidget#nav_list::item:hover {{
                color: {palette.text_primary};
                background-color: rgba(0,0,0,0.02);
            }}
            QListWidget#nav_list::item:selected {{
                color: {palette.accent_color};
                border-left: 2px solid {palette.accent_color};
                background-color: {palette.bg_secondary};
                font-weight: 500;
            }}
        """)

        # 页面容器
        self.page_frame.setStyleSheet(f"""
            QFrame#page_frame {{
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
            }}
        """)

    def refresh(self, **params):
        """刷新页面"""
        if hasattr(self, 'llm_settings'):
            self.llm_settings.loadConfigs()
        if hasattr(self, 'embedding_settings'):
            self.embedding_settings.loadConfigs()
        if hasattr(self, 'image_settings'):
            self.image_settings.loadConfigs()
        if hasattr(self, 'queue_settings'):
            self.queue_settings._load_config()
        if hasattr(self, 'prompt_settings'):
            self.prompt_settings.loadPrompts()
        if hasattr(self, 'advanced_settings'):
            self.advanced_settings.loadConfig()

    def _export_all_configs(self):
        """导出所有配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出所有配置",
            "all_configs.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                export_data = self.api_client.export_all_configs()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                MessageService.show_operation_success(self, "导出", f"已导出所有配置到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"导出失败：{str(e)}", "错误")

    def _import_all_configs(self):
        """导入所有配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            "",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                # 验证数据格式
                if not isinstance(import_data, dict):
                    MessageService.show_warning(self, "导入文件格式不正确", "格式错误")
                    return

                if import_data.get('export_type') != 'all':
                    MessageService.show_warning(self, "导入文件类型不正确，需要全局配置导出文件", "格式错误")
                    return

                result = self.api_client.import_all_configs(import_data)
                if result.get('success'):
                    # 显示详细导入结果
                    details = result.get('details', [])
                    detail_text = '\n'.join(details) if details else '导入完成'
                    MessageService.show_success(self, f"{result.get('message', '导入成功')}\n\n{detail_text}")
                    # 刷新所有设置页面
                    self.refresh()
                else:
                    MessageService.show_error(self, result.get('message', '导入失败'), "错误")
            except Exception as e:
                MessageService.show_error(self, f"导入失败：{str(e)}", "错误")
