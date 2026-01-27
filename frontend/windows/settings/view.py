"""
设置页面主视图 - 书籍风格 (侧边导航布局)
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QListWidget, QStackedWidget, QListWidgetItem,
    QGraphicsDropShadowEffect, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen
from pages.base_page import BasePage
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService
from .config_io_helper import export_config_json, import_config_json
from .ui_helpers import force_refresh_widget_style
from api.manager import APIClientManager
from components.dialogs import LoadingDialog


class LoadingSpinner(QWidget):
    """加载旋转动画组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(dp(40), dp(40))

    def _get_angle(self):
        return self._angle

    def _set_angle(self, angle):
        self._angle = angle
        self.update()

    angle = pyqtProperty(int, _get_angle, _set_angle)

    def start(self):
        """开始动画"""
        self._timer.start(33)  # ~30fps，更流畅

    def stop(self):
        """停止动画"""
        self._timer.stop()

    def _rotate(self):
        """旋转更新"""
        self._angle = (self._angle + 15) % 360  # 每帧旋转15度，更平滑
        self.update()

    def paintEvent(self, event):
        """绘制旋转动画"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取主题颜色
        palette = theme_manager.get_book_palette()
        pen = QPen(QColor(palette.accent_color))
        pen.setWidth(dp(3))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        # 绘制弧形
        rect = self.rect().adjusted(dp(5), dp(5), -dp(5), -dp(5))
        painter.drawArc(rect, self._angle * 16, 270 * 16)


class SettingsLoadingOverlay(QWidget):
    """设置页面加载遮罩

    全屏遮罩，阻止用户在初始化完成前进行任何操作。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAutoFillBackground(True)
        self._setup_ui()
        self._apply_theme()
        theme_manager.theme_changed.connect(self._apply_theme)

    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(dp(16))

        # 加载动画
        self.spinner = LoadingSpinner(self)
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        # 加载文字
        self.loading_label = QLabel("正在加载设置...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)

        # 提示文字
        self.hint_label = QLabel("首次加载需要初始化界面组件，请稍候")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hint_label)

    def _apply_theme(self, theme_name: str = None):
        """应用主题"""
        palette = theme_manager.get_book_palette()

        # 半透明背景遮罩
        self.setStyleSheet(f"""
            SettingsLoadingOverlay {{
                background-color: rgba(0, 0, 0, 0.3);
            }}
        """)

        self.loading_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(16)}px;
                font-weight: 500;
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
                padding: {dp(12)}px {dp(24)}px;
                border-radius: {dp(8)}px;
            }}
        """)

        self.hint_label.setStyleSheet(f"""
            QLabel {{
                font-family: {palette.ui_font};
                font-size: {sp(12)}px;
                color: {palette.text_tertiary};
                background-color: transparent;
            }}
        """)

    def showEvent(self, event):
        """显示时启动动画"""
        super().showEvent(event)
        self.spinner.start()

    def hideEvent(self, event):
        """隐藏时停止动画"""
        self.spinner.stop()
        super().hideEvent(event)

    def mousePressEvent(self, event):
        """拦截所有鼠标点击事件"""
        event.accept()

    def mouseReleaseEvent(self, event):
        """拦截所有鼠标释放事件"""
        event.accept()

    def keyPressEvent(self, event):
        """拦截所有键盘事件"""
        event.accept()


class SettingsView(BasePage):
    """设置页面 - 书籍风格 (侧边导航布局)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self._widgets_initialized = False  # 标记子widget是否已初始化
        self._data_loaded = False  # 标记数据是否已加载
        self._is_visible = False  # 标记页面是否可见（用于取消异步操作）
        self._init_timer = None  # 初始化定时器引用
        self._load_timer = None  # 数据加载定时器引用
        self._loading_overlay = None  # 加载遮罩
        self._init_step = 0  # 分步初始化步骤索引
        self._widget_classes = None  # 缓存的widget类引用
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
        self._add_nav_item("Max Tokens")
        self._add_nav_item("Temperature")

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
        self.max_tokens_settings = None
        self.temperature_settings = None

        page_layout.addWidget(self.page_stack)
        content_layout.addWidget(self.page_frame, stretch=1)

        container_layout.addLayout(content_layout, stretch=1)
        main_layout.addWidget(self.main_container)

        # 默认选中第一项
        self.nav_list.setCurrentRow(0)

        # 创建加载遮罩（覆盖整个设置页面）
        self._loading_overlay = SettingsLoadingOverlay(self)
        self._loading_overlay.hide()  # 默认隐藏

    def _is_widget_valid(self) -> bool:
        """检查 widget 是否仍然有效（未被删除）"""
        try:
            # 使用 sip.isdeleted 检查 C++ 对象是否已被删除
            from PyQt6 import sip
            if sip.isdeleted(self):
                return False
            # 同时检查可见性标志
            return self._is_visible
        except (ImportError, RuntimeError):
            return False

    def _init_widgets_async(self):
        """启动异步分步初始化子widget"""
        try:
            if not self._is_widget_valid():
                return

            if self._widgets_initialized:
                return

            # 初始化步骤索引
            self._init_step = 0

            # 延迟导入模块（先导入，避免每步都导入）
            self._widget_classes = None

            # 开始第一步
            self._do_init_step()

        except RuntimeError:
            pass

    def _do_init_step(self):
        """执行单个初始化步骤，然后让出控制权给事件循环"""
        try:
            if not self._is_widget_valid():
                self._hide_loading_overlay()
                return

            # 检查初始化是否被取消（onHide时会清空_widget_classes）
            if self._init_step > 0 and self._widget_classes is None:
                self._hide_loading_overlay()
                return

            step = self._init_step

            # 步骤0: 导入模块
            if step == 0:
                from .llm_settings_widget import LLMSettingsWidget
                from .embedding_settings_widget import EmbeddingSettingsWidget
                from .advanced_settings_widget import AdvancedSettingsWidget
                from .image_settings_widget import ImageSettingsWidget
                from .queue_settings_widget import QueueSettingsWidget
                from .prompt_settings_widget import PromptSettingsWidget
                from .theme_settings import UnifiedThemeSettingsWidget
                from .max_tokens_settings_widget import MaxTokensSettingsWidget
                from .temperature_settings_widget import TemperatureSettingsWidget

                self._widget_classes = {
                    'llm': LLMSettingsWidget,
                    'embedding': EmbeddingSettingsWidget,
                    'image': ImageSettingsWidget,
                    'queue': QueueSettingsWidget,
                    'prompt': PromptSettingsWidget,
                    'theme': UnifiedThemeSettingsWidget,
                    'advanced': AdvancedSettingsWidget,
                    'max_tokens': MaxTokensSettingsWidget,
                    'temperature': TemperatureSettingsWidget,
                }

            # 步骤1-7: 分别创建各个widget
            elif step == 1:
                self.llm_settings = self._widget_classes['llm']()
                self.page_stack.addWidget(self.llm_settings)

            elif step == 2:
                self.embedding_settings = self._widget_classes['embedding']()
                self.page_stack.addWidget(self.embedding_settings)

            elif step == 3:
                self.image_settings = self._widget_classes['image']()
                self.page_stack.addWidget(self.image_settings)

            elif step == 4:
                self.queue_settings = self._widget_classes['queue']()
                self.page_stack.addWidget(self.queue_settings)

            elif step == 5:
                self.prompt_settings = self._widget_classes['prompt']()
                self.page_stack.addWidget(self.prompt_settings)

            elif step == 6:
                self.theme_settings = self._widget_classes['theme']()
                self.page_stack.addWidget(self.theme_settings)

            elif step == 7:
                self.advanced_settings = self._widget_classes['advanced']()
                self.page_stack.addWidget(self.advanced_settings)

            elif step == 8:
                self.max_tokens_settings = self._widget_classes['max_tokens']()
                self.page_stack.addWidget(self.max_tokens_settings)

            elif step == 9:
                self.temperature_settings = self._widget_classes['temperature']()
                self.page_stack.addWidget(self.temperature_settings)

            # 步骤10: 完成初始化
            elif step == 10:
                self._widgets_initialized = True
                self._widget_classes = None  # 释放引用

                # 隐藏加载遮罩
                self._hide_loading_overlay()

                # 设置当前页面索引
                current_row = self.nav_list.currentRow()
                if current_row >= 0:
                    self.page_stack.setCurrentIndex(current_row)

                # 延迟加载当前页面的数据
                self._load_timer = QTimer(self)
                self._load_timer.setSingleShot(True)
                self._load_timer.timeout.connect(self._load_current_page_data)
                self._load_timer.start(50)
                return  # 初始化完成，不再调度下一步

            # 调度下一步（使用 singleShot 让出控制权给事件循环，使动画能更新）
            # 延迟16ms约等于60fps的一帧时间，确保动画流畅
            self._init_step += 1
            QTimer.singleShot(16, self._do_init_step)

        except RuntimeError:
            # Widget 已被删除，静默处理
            self._hide_loading_overlay()

    def _load_current_page_data(self):
        """加载当前页面的数据"""
        try:
            # 检查 widget 是否仍然有效
            if not self._is_widget_valid():
                return

            current_row = self.nav_list.currentRow()
            self._load_page_data(current_row)
        except RuntimeError:
            # Widget 已被删除，静默处理
            pass

    def _load_page_data(self, page_index: int):
        """加载指定页面的数据"""
        try:
            if not self._widgets_initialized:
                return

            if not self._is_widget_valid():
                return

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
            elif page_index == 7 and self.max_tokens_settings:
                self.max_tokens_settings.loadConfig()
            elif page_index == 8 and self.temperature_settings:
                self.temperature_settings.loadConfig()
        except RuntimeError:
            # Widget 已被删除，静默处理
            pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"加载页面数据失败: {e}")

    def onShow(self):
        """页面显示时触发（生命周期钩子）"""
        super().onShow()
        self._is_visible = True

        if not self._widgets_initialized:
            # 显示加载遮罩，阻止用户操作
            self._show_loading_overlay()
            # 使用可取消的定时器延迟初始化
            self._init_timer = QTimer(self)
            self._init_timer.setSingleShot(True)
            self._init_timer.timeout.connect(self._init_widgets_async)
            self._init_timer.start(10)

    def _show_loading_overlay(self):
        """显示加载遮罩"""
        if self._loading_overlay:
            self._loading_overlay.setGeometry(self.rect())
            self._loading_overlay.raise_()
            self._loading_overlay.show()

    def _hide_loading_overlay(self):
        """隐藏加载遮罩"""
        if self._loading_overlay:
            self._loading_overlay.hide()

    def resizeEvent(self, event):
        """处理窗口大小变化"""
        super().resizeEvent(event)
        # 保持遮罩覆盖整个页面
        if self._loading_overlay and self._loading_overlay.isVisible():
            self._loading_overlay.setGeometry(self.rect())

    def onHide(self):
        """页面隐藏时触发（生命周期钩子）"""
        self._is_visible = False

        # 清理分步初始化状态（防止后续步骤继续执行）
        self._widget_classes = None

        # 隐藏加载遮罩
        self._hide_loading_overlay()

        # 取消待处理的初始化定时器
        if self._init_timer is not None and self._init_timer.isActive():
            self._init_timer.stop()
            self._init_timer = None

        # 取消待处理的数据加载定时器
        if self._load_timer is not None and self._load_timer.isActive():
            self._load_timer.stop()
            self._load_timer = None

        super().onHide()

    def cleanup(self):
        """清理资源（主窗口关闭时调用）"""
        # 标记为不可见，防止异步回调执行
        self._is_visible = False

        # 清理分步初始化状态
        self._widget_classes = None

        # 停止加载遮罩动画
        if self._loading_overlay is not None:
            if hasattr(self._loading_overlay, 'spinner'):
                self._loading_overlay.spinner.stop()

        # 取消待处理的定时器
        if self._init_timer is not None and self._init_timer.isActive():
            self._init_timer.stop()
            self._init_timer = None

        if self._load_timer is not None and self._load_timer.isActive():
            self._load_timer.stop()
            self._load_timer = None

        # 清理主题设置widget的异步工作线程
        if self.theme_settings is not None:
            if hasattr(self.theme_settings, '_cleanup_all'):
                self.theme_settings._cleanup_all()
            elif hasattr(self.theme_settings, '_cleanup_child_widgets'):
                self.theme_settings._cleanup_child_widgets()

        # 清理其他可能有异步工作的widget
        for widget in [self.llm_settings, self.embedding_settings,
                       self.image_settings, self.queue_settings,
                       self.prompt_settings, self.advanced_settings,
                       self.max_tokens_settings, self.temperature_settings]:
            if widget is not None and hasattr(widget, '_cleanup_worker'):
                try:
                    widget._cleanup_worker()
                except Exception:
                    pass

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
        """应用书籍风格主题 - 支持透明效果"""
        from PyQt6.QtCore import Qt
        from themes.modern_effects import ModernEffects

        palette = theme_manager.get_book_palette()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        # 使用get_component_opacity获取透明度，自动应用主控透明度系数
        content_opacity = theme_manager.get_component_opacity("content")

        if transparency_enabled:
            # 透明模式：使用RGBA背景色实现半透明效果
            # 当content_opacity=0时，页面完全透明，能看到桌面
            bg_rgba = ModernEffects.hex_to_rgba(palette.bg_primary, content_opacity)
            self.main_container.setStyleSheet(f"""
                QWidget#settings_main_container {{
                    background-color: {bg_rgba};
                }}
            """)

            # 设置WA_TranslucentBackground使透明生效（真正的窗口透明）
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.main_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)
            self.main_container.setAutoFillBackground(False)

            # 指定容器设置透明（不使用findChildren避免影响其他页面）
            transparent_containers = ['nav_list', 'page_frame', 'page_stack']
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)
        else:
            # 主容器背景 - 使用 objectName 选择器避免影响子widget
            self.main_container.setStyleSheet(f"""
                QWidget#settings_main_container {{
                    background-color: {palette.bg_primary};
                }}
            """)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)
            self.main_container.setAutoFillBackground(True)

            # 恢复容器的背景填充
            containers_to_restore = ['nav_list', 'page_frame', 'page_stack']
            for container_name in containers_to_restore:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

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

        # 页面容器 - 支持透明效果
        if transparency_enabled:
            # 使用get_component_opacity获取透明度，自动应用主控透明度系数
            opacity = theme_manager.get_component_opacity("dialog")
            page_bg_rgba = ModernEffects.hex_to_rgba(palette.bg_secondary, opacity)
            border_rgba = ModernEffects.hex_to_rgba(palette.border_color, 0.5)
            self.page_frame.setStyleSheet(f"""
                QFrame#page_frame {{
                    background-color: {page_bg_rgba};
                    border: 1px solid {border_rgba};
                    border-radius: {dp(8)}px;
                }}
            """)
        else:
            self.page_frame.setStyleSheet(f"""
                QFrame#page_frame {{
                    background-color: {palette.bg_secondary};
                    border: 1px solid {palette.border_color};
                    border-radius: {dp(8)}px;
                }}
            """)

        # 确保 page_stack 透明，不覆盖子widget样式
        self.page_stack.setStyleSheet("background-color: transparent;")

        # 强制刷新样式缓存
        force_refresh_widget_style(self)
        force_refresh_widget_style(self.page_stack)

    def refresh(self, **params):
        """刷新页面"""
        if not self._widgets_initialized:
            return

        # 只刷新当前显示的页面
        current_row = self.nav_list.currentRow()
        self._load_page_data(current_row)

    def _export_all_configs(self):
        """导出所有配置"""
        def _on_success(file_path: str, _export_data: dict):
            MessageService.show_operation_success(self, "导出", f"已导出所有配置到：{file_path}")

        export_config_json(
            self,
            "导出所有配置",
            "all_configs.json",
            self.api_client.export_all_configs,
            on_success=_on_success,
            error_title="错误",
            error_template="导出失败：{error}",
        )

    def _import_all_configs(self):
        """导入所有配置"""
        def _on_success(result: dict):
            details = result.get('details', [])
            detail_text = '\n'.join(details) if details else '导入完成'
            MessageService.show_success(self, f"{result.get('message', '导入成功')}\n\n{detail_text}")
            self.refresh()

        import_config_json(
            self,
            "导入配置",
            "all",
            "全局配置导出文件",
            self.api_client.import_all_configs,
            on_success=_on_success,
            error_title="错误",
            error_template="导入失败：{error}",
            warning_title="格式错误",
        )
