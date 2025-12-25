"""
设置页面主视图 - 书籍风格 (侧边导航布局)
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QListWidget, QStackedWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor
from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from api.manager import APIClientManager
from components.dialogs import LoadingDialog
import json


class SettingsView(BasePage):
    """设置页面 - 书籍风格 (侧边导航布局)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self._widgets_initialized = False  # 标记子widget是否已初始化
        self._data_loaded = False  # 标记数据是否已加载
        self._create_ui_structure()
        self._apply_theme()
        # 注意：不需要额外连接 theme_changed 信号
        # BasePage 已经连接了信号，会自动调用 on_theme_changed -> _apply_theme()

    def _create_ui_structure(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 主容器
        self.main_container = QWidget()
        self.main_container.setObjectName("settings_main_container")
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
        self._add_nav_item("主题配置")
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
        shadow.setColor(QColor(theme_manager.SHADOW_COLOR))
        self.page_frame.setGraphicsEffect(shadow)

        page_layout = QVBoxLayout(self.page_frame)
        page_layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))  # 修正：20不符合8pt网格，改为24
        page_layout.setSpacing(0)

        # 堆叠页面
        self.page_stack = QStackedWidget()

        # 使用占位符，延迟创建真正的widget
        self.llm_settings = None
        self.embedding_settings = None
        self.image_settings = None
        self.queue_settings = None
        self.prompt_settings = None
        self.theme_settings = None
        self.advanced_settings = None

        # 创建加载占位页面
        self._loading_placeholder = self._create_loading_placeholder()
        self.page_stack.addWidget(self._loading_placeholder)

        page_layout.addWidget(self.page_stack)
        content_layout.addWidget(self.page_frame, stretch=1)

        container_layout.addLayout(content_layout, stretch=1)
        main_layout.addWidget(self.main_container)

        # 默认选中第一项
        self.nav_list.setCurrentRow(0)

    def _create_loading_placeholder(self) -> QWidget:
        """创建加载占位页面"""
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(16))

        # 加载动画指示器（使用文字动画）
        loading_label = QLabel("正在加载设置...")
        loading_label.setObjectName("loading_label")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(loading_label)

        # 提示文字
        hint_label = QLabel("首次加载需要初始化界面组件")
        hint_label.setObjectName("loading_hint")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint_label)

        return placeholder

    def _init_widgets_async(self):
        """异步初始化子widget（在事件循环中执行，不阻塞UI）"""
        if self._widgets_initialized:
            return

        # 延迟导入，减少初始加载时间
        from .llm_settings_widget import LLMSettingsWidget
        from .embedding_settings_widget import EmbeddingSettingsWidget
        from .advanced_settings_widget import AdvancedSettingsWidget
        from .image_settings_widget import ImageSettingsWidget
        from .queue_settings_widget import QueueSettingsWidget
        from .prompt_settings_widget import PromptSettingsWidget
        from .theme_settings_widget import ThemeSettingsWidget

        # 移除占位符
        self.page_stack.removeWidget(self._loading_placeholder)
        self._loading_placeholder.deleteLater()

        # 创建各个设置widget（它们的__init__中不再调用loadConfigs）
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

        self.theme_settings = ThemeSettingsWidget()
        self.page_stack.addWidget(self.theme_settings)

        self.advanced_settings = AdvancedSettingsWidget()
        self.page_stack.addWidget(self.advanced_settings)

        self._widgets_initialized = True

        # 设置当前页面索引
        current_row = self.nav_list.currentRow()
        if current_row >= 0:
            self.page_stack.setCurrentIndex(current_row)

        # 延迟加载当前页面的数据
        QTimer.singleShot(50, self._load_current_page_data)

    def _load_current_page_data(self):
        """加载当前页面的数据"""
        current_row = self.nav_list.currentRow()
        self._load_page_data(current_row)

    def _load_page_data(self, page_index: int):
        """加载指定页面的数据"""
        if not self._widgets_initialized:
            return

        try:
            if page_index == 0 and self.llm_settings:
                self.llm_settings.loadConfigs()
            elif page_index == 1 and self.embedding_settings:
                self.embedding_settings.loadConfigs()
            elif page_index == 2 and self.image_settings:
                self.image_settings.loadConfigs()
            elif page_index == 3 and self.queue_settings:
                self.queue_settings._load_config()
            elif page_index == 4 and self.prompt_settings:
                self.prompt_settings.loadPrompts()
            elif page_index == 5 and self.theme_settings:
                self.theme_settings.refresh()
            elif page_index == 6 and self.advanced_settings:
                self.advanced_settings.loadConfig()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"加载页面数据失败: {e}")

    def onShow(self):
        """页面显示时触发（生命周期钩子）"""
        super().onShow()
        if not self._widgets_initialized:
            # 使用 QTimer.singleShot 延迟初始化，让页面先显示
            QTimer.singleShot(10, self._init_widgets_async)

    def _add_nav_item(self, title):
        """添加导航项"""
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, dp(48)))  # 修正：44不符合8pt网格，改为48
        item.setText(title)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.nav_list.addItem(item)

    def _on_nav_changed(self, row):
        """导航切换"""
        if self._widgets_initialized:
            self.page_stack.setCurrentIndex(row)
            # 加载该页面的数据
            self._load_page_data(row)

    def _apply_theme(self):
        """应用书籍风格主题"""
        # 调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== SettingsView._apply_theme() called ===")
        logger.info(f"is_dark_mode: {theme_manager.is_dark_mode()}")

        palette = theme_manager.get_book_palette()
        logger.info(f"bg_primary: {palette.bg_primary}, text_primary: {palette.text_primary}")

        # 主容器背景 - 使用 objectName 选择器避免影响子widget
        self.main_container.setStyleSheet(f"""
            QWidget#settings_main_container {{
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
                background-color: {theme_manager.PRIMARY_PALE};
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

        # 确保 page_stack 透明，不覆盖子widget样式
        self.page_stack.setStyleSheet("background-color: transparent;")

        # 加载占位符样式
        loading_label = self.findChild(QLabel, "loading_label")
        if loading_label:
            loading_label.setStyleSheet(f"""
                QLabel#loading_label {{
                    font-family: {palette.ui_font};
                    font-size: {sp(16)}px;
                    color: {palette.text_primary};
                    padding: {dp(40)}px {dp(40)}px {dp(8)}px {dp(40)}px;
                }}
            """)

        loading_hint = self.findChild(QLabel, "loading_hint")
        if loading_hint:
            loading_hint.setStyleSheet(f"""
                QLabel#loading_hint {{
                    font-family: {palette.ui_font};
                    font-size: {sp(12)}px;
                    color: {palette.text_tertiary};
                    font-style: italic;
                }}
            """)

        # 强制刷新样式缓存
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

        # 刷新 page_stack 样式
        self.page_stack.style().unpolish(self.page_stack)
        self.page_stack.style().polish(self.page_stack)
        self.page_stack.update()

    def refresh(self, **params):
        """刷新页面"""
        if not self._widgets_initialized:
            return

        # 只刷新当前显示的页面
        current_row = self.nav_list.currentRow()
        self._load_page_data(current_row)

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
