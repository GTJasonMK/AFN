"""
主窗口 - 页面导航容器

功能：
- 使用QStackedWidget管理所有页面
- 统一的页面导航系统
- 导航历史栈支持返回按钮
- LRU页面缓存淘汰机制避免内存泄漏
- DPI感知和响应式布局
- 页面切换时的加载动画
"""

import json
import logging
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QPushButton, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from typing import Dict, List, Tuple
from collections import OrderedDict
from themes.theme_manager import theme_manager, ThemeMode
from themes.modern_effects import ModernEffects
from themes.svg_icons import SVGIcons
from utils.dpi_utils import dpi_helper, dp, sp
from utils.window_blur import WindowBlurManager
from api.manager import APIClientManager
from components.loading_spinner import LoadingOverlay
from components.theme_transition import ThemeSwitchHelper

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口 - 页面导航容器

    使用QStackedWidget实现单页面应用风格的页面切换

    特性：
    - LRU缓存：最多缓存10个页面，超出时淘汰最久未使用的页面
    - 重要页面（HOME, SETTINGS）永不淘汰
    - 页面淘汰前调用onHide()钩子，允许保存状态
    """

    # 缓存配置
    MAX_CACHED_PAGES = 10  # 最多缓存10个页面
    IMPORTANT_PAGES = {'HOME', 'SETTINGS'}  # 重要页面永不淘汰

    @staticmethod
    def _make_nav_key(page_type: str, params: dict) -> str:
        """生成导航历史的比较键

        将页面类型和参数序列化为字符串，确保相同的导航目标
        产生相同的键，用于避免重复的历史记录。

        Args:
            page_type: 页面类型
            params: 页面参数字典

        Returns:
            序列化后的导航键字符串
        """
        # 使用 sort_keys 确保相同内容的 dict 产生相同的序列化结果
        params_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return f"{page_type}:{params_str}"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AFN - AI 长篇小说创作助手")

        # 使用DPI感知的最小窗口尺寸
        min_width, min_height = dpi_helper.min_window_size()
        self.setMinimumSize(min_width, min_height)

        # 初始窗口大小（比最小尺寸略大）
        self.resize(int(min_width * 1.2), int(min_height * 1.2))

        # 创建中心容器
        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")  # 立即设置objectName以便样式选择器匹配
        self.setCentralWidget(self.central_widget)

        # 主布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 页面容器
        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("mainPageStack")
        main_layout.addWidget(self.page_stack)

        # 创建浮动工具栏（包含主题切换按钮）
        self.create_floating_toolbar()

        # 页面缓存：使用OrderedDict实现LRU
        # {cache_key: page_widget}
        self.pages = OrderedDict()

        # 导航历史栈：[(page_type, params)]
        self.navigation_history: List[Tuple[str, dict]] = []

        # 创建页面切换加载覆盖层
        self._nav_loading_overlay = LoadingOverlay(
            text="正在加载...",
            parent=self.central_widget,
            translucent=True
        )
        self._nav_loading_overlay.hide()

        # 主题信号连接标志
        self._theme_connected = False
        self._connect_theme_signal()

        # 防止主题切换时重复加载配置
        self._is_reloading_theme_config = False
        # 主题配置加载的 AsyncWorker（防止被垃圾回收）
        self._theme_config_worker = None

        # 创建主题切换辅助类（带过渡动画）
        self._theme_switch_helper = ThemeSwitchHelper(self)

        # 应用主题样式到窗口
        self.apply_window_theme()

        # 设置键盘快捷键
        self.setup_shortcuts()

        # 初始化首页
        self.navigateTo('HOME')

    def _connect_theme_signal(self):
        """连接主题信号（只连接一次）"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self.on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self.on_theme_changed)
            except TypeError:
                pass  # 信号可能已断开
            self._theme_connected = False

    def create_floating_toolbar(self):
        """创建浮动工具栏（改进的主题按钮定位）"""
        # 创建浮动容器
        self.floating_widget = QWidget(self)
        self.floating_widget.setObjectName("floatingToolbar")

        # 设置浮动样式（半透明背景）
        self.floating_widget.setStyleSheet("""
            #floatingToolbar {
                background-color: transparent;
            }
        """)

        # 工具栏布局
        toolbar_layout = QHBoxLayout(self.floating_widget)
        toolbar_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        toolbar_layout.setSpacing(dp(8))

        # 添加弹簧，将按钮推到右侧
        toolbar_layout.addStretch()

        # 主题切换按钮
        self.theme_button = QPushButton()
        self.theme_button.setFixedSize(QSize(dp(48), dp(48)))
        self.theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setToolTip("切换主题 (Ctrl+T)")

        # 更新按钮样式
        self.update_theme_button()

        toolbar_layout.addWidget(self.theme_button)

        # 设置浮动widget的初始位置（右下角）
        self.position_floating_toolbar()

    def position_floating_toolbar(self):
        """定位浮动工具栏到右下角（响应式）"""
        if hasattr(self, 'floating_widget'):
            # 获取窗口大小
            window_rect = self.rect()

            # 工具栏大小（响应式）
            toolbar_width = dp(80)
            toolbar_height = dp(80)

            # 计算位置（右下角，留出边距）
            x = window_rect.width() - toolbar_width
            y = window_rect.height() - toolbar_height

            self.floating_widget.setGeometry(x, y, toolbar_width, toolbar_height)
            self.floating_widget.raise_()  # 确保在最上层

    def setup_shortcuts(self):
        """设置键盘快捷键（改善无障碍性）"""
        # 主题切换快捷键
        theme_action = QAction("切换主题", self)
        theme_action.setShortcut(QKeySequence("Ctrl+T"))
        theme_action.triggered.connect(self.toggle_theme)
        self.addAction(theme_action)

        # 返回快捷键
        back_action = QAction("返回", self)
        back_action.setShortcut(QKeySequence.StandardKey.Back)
        back_action.triggered.connect(self.goBack)
        self.addAction(back_action)

        # 刷新快捷键
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut(QKeySequence.StandardKey.Refresh)
        refresh_action.triggered.connect(self.refresh_current_page)
        self.addAction(refresh_action)

    def refresh_current_page(self):
        """刷新当前页面"""
        current_widget = self.page_stack.currentWidget()
        if current_widget and hasattr(current_widget, 'refresh'):
            current_widget.refresh()

    def update_theme_button(self):
        """更新主题切换按钮的样式和图标"""
        is_dark = theme_manager.is_dark_mode()
        ui_font = theme_manager.ui_font()

        logger.info(f"=== update_theme_button: is_dark={is_dark} ===")
        logger.info(f"BG_SECONDARY={theme_manager.BG_SECONDARY}, TEXT_PRIMARY={theme_manager.TEXT_PRIMARY}")

        # 简化的文字标签
        button_text = "深" if is_dark else "浅"
        self.theme_button.setText(button_text)
        self.theme_button.setToolTip("切换主题 (Ctrl+T)")

        # 简化的按钮样式
        self.theme_button.setStyleSheet(f"""
            QPushButton {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(24)}px;
                font-size: {sp(14)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme_manager.BG_TERTIARY};
            }}
        """)

    def toggle_theme(self):
        """切换主题（带平滑过渡动画）"""
        self._theme_switch_helper.switch_theme()

    def apply_window_theme(self):
        """应用主题样式到窗口和容器 - 支持真正的窗口透明

        透明模式实现真正的窗口透明效果，能看到窗口后面的桌面和其他应用。
        透明度为0时完全透明，透明度为1时完全不透明。
        """
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QWidget

        try:
            # 获取透明效果配置
            transparency_config = theme_manager.get_transparency_config()
            transparency_enabled = transparency_config.get("enabled", False)
            system_blur = transparency_config.get("system_blur", False)  # 系统级模糊开关
            # 使用get_component_opacity获取已应用主控透明度的值
            content_opacity = theme_manager.get_component_opacity("content")

            logger.info(f"=== MainWindow.apply_window_theme ===")
            logger.info(f"transparency_enabled: {transparency_enabled}, system_blur: {system_blur}, content_opacity: {content_opacity}, master_opacity: {transparency_config.get('master_opacity', 1.0)}")

            # 获取背景色
            bg_color = theme_manager.BG_PRIMARY

            # 获取当前显示的页面
            current_page = self.page_stack.currentWidget()

            if transparency_enabled:
                # 透明模式：使用真正的窗口透明效果（能看到桌面）
                is_dark = theme_manager.is_dark_mode()

                # 1. 首先隐藏所有非当前页面（必须在设置透明属性之前）
                #    这是防止页面重合的关键步骤
                for i in range(self.page_stack.count()):
                    page = self.page_stack.widget(i)
                    if page and page != current_page:
                        page.hide()
                        # 同时设置页面为不透明，防止透过去看到
                        page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                        # 将页面放到最底层
                        page.lower()

                # 2. 设置透明属性
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.central_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.page_stack.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                self.setAutoFillBackground(False)
                self.central_widget.setAutoFillBackground(False)
                self.page_stack.setAutoFillBackground(False)

                # 3. Qt窗口和容器都设置为透明
                window_style = f"""
                    QMainWindow {{
                        background-color: transparent;
                    }}
                    QWidget#centralWidget {{
                        background-color: transparent;
                    }}
                    QStackedWidget#mainPageStack {{
                        background-color: transparent;
                    }}
                """
                self.setStyleSheet(window_style)

                # 4. 启用系统级窗口透明
                #    - blur=True: 使用DWM Acrylic/BlurBehind效果（毛玻璃）
                #    - blur=False: 纯透明，不使用DWM模糊（可以清晰看到桌面）
                try:
                    success = WindowBlurManager.enable_window_transparency(
                        self,
                        opacity=content_opacity,
                        blur=system_blur,  # 根据用户设置决定是否启用模糊
                        is_dark=is_dark
                    )
                    blur_status = "模糊" if system_blur else "纯透明"
                    logger.info(f"窗口透明效果({blur_status}): {'成功' if success else '失败'}")
                except Exception as e:
                    logger.warning(f"启用窗口透明效果失败: {e}")

                # 5. 确保当前页面可见并设置正确的透明属性
                if current_page:
                    # 当前页面需要支持透明
                    current_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                    current_page.show()
                    current_page.raise_()

                blur_desc = "（带模糊）" if system_blur else "（纯透明）"
                logger.info(f"透明模式已启用{blur_desc}，透明度: {content_opacity}")

            else:
                # 非透明模式：完全不透明

                # 1. 首先隐藏所有非当前页面
                for i in range(self.page_stack.count()):
                    page = self.page_stack.widget(i)
                    if page and page != current_page:
                        page.hide()
                        # 确保页面不透明
                        page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                        # 将页面放到最底层
                        page.lower()

                # 2. 禁用系统级透明效果（传入背景色以匹配主题）
                try:
                    WindowBlurManager.disable_window_transparency(self, bg_color=bg_color)
                except Exception as e:
                    logger.debug(f"禁用透明效果: {e}")

                # 3. 禁用Qt透明属性
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                self.central_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                self.page_stack.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

                # 4. 启用自动填充背景
                self.setAutoFillBackground(True)
                self.central_widget.setAutoFillBackground(True)
                self.page_stack.setAutoFillBackground(True)

                # 5. 设置实色背景样式
                window_style = f"""
                    QMainWindow {{
                        background-color: {bg_color};
                    }}
                    QWidget#centralWidget {{
                        background-color: {bg_color};
                    }}
                    QStackedWidget#mainPageStack {{
                        background-color: {bg_color};
                    }}
                """
                self.setStyleSheet(window_style)

                # 6. 确保当前页面可见并正确显示
                if current_page:
                    current_page.show()
                    current_page.raise_()

                # 7. 强制刷新窗口
                self.style().unpolish(self)
                self.style().polish(self)
                self.update()
                self.repaint()
                self.central_widget.update()
                self.central_widget.repaint()
                self.page_stack.update()
                self.page_stack.repaint()
                if current_page:
                    current_page.update()
                    current_page.repaint()

                logger.info(f"普通模式：使用实色背景 {bg_color}")

        except Exception as e:
            logger.error(f"apply_window_theme 失败: {e}")
            # 回退到安全的不透明模式
            try:
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                window_style = f"""
                    QMainWindow {{
                        background-color: {theme_manager.BG_PRIMARY};
                    }}
                """
                self.setStyleSheet(window_style)
            except Exception:
                pass

    def on_theme_changed(self, mode: str):
        """主题改变时的处理

        优化说明：
        - 各组件已通过 ThemeAware 基类自动响应主题信号
        - 此处只需更新主窗口自身的样式和浮动工具栏
        - 不再遍历整棵组件树，提升性能
        - 新增：从后端重新加载对应模式的激活配置
        """
        # 应用窗口主题
        self.apply_window_theme()

        # 更新按钮样式
        self.update_theme_button()

        # 强制刷新主窗口的样式缓存（仅顶层）
        self._refresh_top_level_style()

        # 从后端加载激活的配置（异步，防止重复调用）
        if not self._is_reloading_theme_config:
            self._reload_active_theme_config(mode)

    def _reload_active_theme_config(self, mode: str):
        """从后端重新加载激活的主题配置

        Args:
            mode: 主题模式（'light' 或 'dark'）
        """
        from utils.async_worker import AsyncWorker

        # 设置标志防止重复加载
        self._is_reloading_theme_config = True

        def do_load():
            try:
                api_client = APIClientManager.get_client()
                return api_client.get_active_unified_theme_config(mode)
            except Exception as e:
                logger.warning(f"加载激活的主题配置失败: {e}")
                return None

        def on_success(config):
            try:
                if config is None:
                    logger.info(f"没有激活的{mode}主题配置，使用默认主题")
                    return

                config_version = config.get('config_version', 1)
                config_name = config.get('config_name', '未命名')
                logger.info(f"重新加载激活的主题配置: {config_name} (V{config_version})")

                if config_version == 2 and config.get('effects'):
                    # V2配置：直接设置配置数据，不发射信号
                    theme_manager._v2_config = config
                    theme_manager._use_v2 = True
                    # 重置V1配置
                    theme_manager._use_custom = False
                    theme_manager._custom_theme_config = None
                elif any(config.get(k) for k in ['primary_colors', 'text_colors', 'background_colors']):
                    # V1配置：合并为平面字典
                    flat_config = {}
                    v1_groups = [
                        'primary_colors', 'accent_colors', 'semantic_colors',
                        'text_colors', 'background_colors', 'border_effects',
                        'button_colors', 'typography', 'border_radius',
                        'spacing', 'animation', 'button_sizes'
                    ]
                    for group in v1_groups:
                        group_values = config.get(group, {}) or {}
                        flat_config.update(group_values)
                    if flat_config:
                        # 直接设置配置，不发射信号
                        theme_manager._custom_theme_config = flat_config
                        theme_manager._use_custom = True
                        theme_manager._v2_config = None
                        theme_manager._use_v2 = False
                        theme_manager._current_theme = theme_manager._create_theme_from_config(flat_config)

                # 注意：不再调用 apply_window_theme()，因为：
                # 1. on_theme_changed 已经调用了 apply_window_theme()
                # 2. 异步回调中再次调用可能导致竞态条件
                # 3. 透明效果在初始 apply_window_theme() 中已应用
            except Exception as e:
                logger.error(f"应用主题配置失败: {e}")
            finally:
                # 重置标志
                self._is_reloading_theme_config = False

        def on_error(error):
            logger.warning(f"加载主题配置失败: {error}")
            self._is_reloading_theme_config = False

        # 使用 AsyncWorker 异步加载（存储引用防止垃圾回收）
        self._theme_config_worker = AsyncWorker(do_load)
        self._theme_config_worker.success.connect(on_success)
        self._theme_config_worker.error.connect(on_error)
        self._theme_config_worker.start()

    def _refresh_top_level_style(self):
        """刷新顶层组件的样式（轻量级刷新）

        只刷新主窗口和浮动工具栏，不遍历整棵组件树。
        各子组件通过主题信号自行处理。
        """
        try:
            # 刷新主窗口
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()

            # 刷新中心容器
            self.central_widget.style().unpolish(self.central_widget)
            self.central_widget.style().polish(self.central_widget)
            self.central_widget.update()

            # 刷新页面堆栈
            if hasattr(self, 'page_stack'):
                self.page_stack.style().unpolish(self.page_stack)
                self.page_stack.style().polish(self.page_stack)
                self.page_stack.update()

            # 刷新浮动工具栏
            if hasattr(self, 'floating_widget'):
                self.floating_widget.style().unpolish(self.floating_widget)
                self.floating_widget.style().polish(self.floating_widget)
                self.floating_widget.update()

        except RuntimeError:
            # 组件可能已被删除，跳过
            pass

    def showEvent(self, event):
        """窗口显示时，确保浮动工具栏位置正确"""
        super().showEvent(event)
        self.position_floating_toolbar()

        # 更新DPI信息
        dpi_helper.update_screen_info(self)

    def resizeEvent(self, event):
        """窗口大小改变时，重新定位浮动工具栏"""
        super().resizeEvent(event)
        self.position_floating_toolbar()

        # 更新响应式断点
        dpi_helper.update_screen_info(self)

    def navigateTo(self, page_type: str, params: dict = None):
        """导航到指定页面（性能优化版）

        Args:
            page_type: 页面类型（HOME, INSPIRATION, DETAIL, WRITING_DESK, SETTINGS）
            params: 页面参数（如project_id等）

        性能优化：
        - 移除50ms人为延迟，改为最小延迟(10ms)仅用于动画启动
        - 减少processEvents()调用次数
        """
        from PyQt6.QtWidgets import QApplication

        if params is None:
            params = {}

        logger.info("navigateTo called: page_type=%s, params=%s", page_type, params)

        # 检查页面是否已缓存
        cache_key = page_type
        if page_type in ['DETAIL', 'WRITING_DESK']:
            project_id = params.get('project_id')
            if project_id:
                cache_key = f"{page_type}_{project_id}"

        is_cached = cache_key in self.pages

        # 对于需要创建的新页面（复杂页面），显示加载动画
        needs_loading = not is_cached and page_type in ['DETAIL', 'WRITING_DESK']

        if needs_loading:
            # 显示加载动画
            self._show_nav_loading("正在加载页面...")
            # 最小延迟：仅给动画一帧的启动时间(约16ms)，然后立即执行导航
            QTimer.singleShot(10, lambda: self._doNavigate(page_type, params))
        else:
            # 已缓存的页面或简单页面，直接切换
            self._doNavigate(page_type, params)

    def _show_nav_loading(self, text="正在加载..."):
        """显示导航加载动画"""
        if self._nav_loading_overlay:
            self._nav_loading_overlay.setText(text)
            self._nav_loading_overlay.setGeometry(self.central_widget.rect())
            self._nav_loading_overlay.show_with_animation(text)

    def _hide_nav_loading(self):
        """隐藏导航加载动画"""
        if self._nav_loading_overlay:
            self._nav_loading_overlay.hide_with_animation()

    def _doNavigate(self, page_type: str, params: dict):
        """执行实际的页面导航

        Args:
            page_type: 页面类型
            params: 页面参数

        性能优化：将4次processEvents()调用减少到1次（仅在页面创建后刷新前）
        """
        from PyQt6.QtWidgets import QApplication

        # 记录当前页面（用于后续隐藏，防止透明穿透）
        old_widget = self.page_stack.currentWidget()

        # 获取或创建页面
        page = self.getOrCreatePage(page_type, params)

        if page is None:
            logger.error(
                "无法创建页面: page_type=%s, params=%s (可能缺少必需参数)",
                page_type, params
            )
            self._hide_nav_loading()
            return

        logger.info("Page created/retrieved successfully: %s", type(page).__name__)

        # 仅在页面创建完成后调用一次processEvents，确保UI更新
        QApplication.processEvents()

        # 调用页面刷新方法
        if hasattr(page, 'refresh'):
            page.refresh(**params)

        # 调用旧页面隐藏钩子
        if old_widget and old_widget != page:
            if hasattr(old_widget, 'onHide'):
                try:
                    old_widget.onHide()
                except RuntimeError:
                    pass
            # 显式隐藏旧页面，防止透明模式下的穿透
            old_widget.hide()
            # 确保旧页面不透明，防止透过新页面看到
            old_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            # 将旧页面放到最底层
            old_widget.lower()

        # 确保新页面可见
        # 根据透明模式设置正确的透明属性
        transparency_enabled = theme_manager.get_transparency_config().get("enabled", False)
        if transparency_enabled:
            page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        page.show()
        page.raise_()  # 确保在最上层

        # 切换到页面
        self.page_stack.setCurrentWidget(page)
        logger.info("Page switched to: %s", page_type)

        # 隐藏加载动画
        self._hide_nav_loading()

        # 调用页面显示钩子
        if hasattr(page, 'onShow'):
            page.onShow()

        # 添加到导航历史（使用序列化键比较避免重复）
        current_nav_key = self._make_nav_key(page_type, params)
        last_nav_key = self._make_nav_key(*self.navigation_history[-1]) if self.navigation_history else None
        if current_nav_key != last_nav_key:
            self.navigation_history.append((page_type, params))
            logger.info("Navigation history updated: %s", [(p, dict(pr) if pr else {}) for p, pr in self.navigation_history[-3:]])

    def goBack(self):
        """返回上一页"""
        if len(self.navigation_history) <= 1:
            # 已经是第一页，无法返回
            return

        # 移除当前页
        current_page_info = self.navigation_history.pop()

        # 安全地调用当前页面隐藏钩子
        current_widget = self.page_stack.currentWidget()
        try:
            if current_widget and hasattr(current_widget, 'onHide'):
                current_widget.onHide()
        except RuntimeError:
            logger.debug("当前页面已被删除，跳过onHide")
        except Exception as e:
            logger.warning(f"调用当前页面onHide时出错: {e}")

        # 获取上一页信息
        prev_page_type, prev_params = self.navigation_history[-1]

        # 获取页面实例
        prev_page = self.getOrCreatePage(prev_page_type, prev_params)

        if prev_page is None:
            return

        # 刷新上一页
        if hasattr(prev_page, 'refresh'):
            prev_page.refresh(**prev_params)

        # 显式隐藏当前页面，防止透明模式下的穿透
        if current_widget and current_widget != prev_page:
            current_widget.hide()
            # 确保旧页面不透明，防止透过新页面看到
            current_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            # 将旧页面放到最底层
            current_widget.lower()

        # 确保目标页面可见
        # 根据透明模式设置正确的透明属性
        transparency_enabled = theme_manager.get_transparency_config().get("enabled", False)
        if transparency_enabled:
            prev_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        else:
            prev_page.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        prev_page.show()
        prev_page.raise_()  # 确保在最上层

        # 切换到上一页
        self.page_stack.setCurrentWidget(prev_page)

        # 调用显示钩子
        if hasattr(prev_page, 'onShow'):
            prev_page.onShow()

    def getOrCreatePage(self, page_type: str, params: dict):
        """获取或创建页面实例（支持LRU淘汰）

        Args:
            page_type: 页面类型
            params: 页面参数

        Returns:
            页面widget实例
        """
        # 对于需要多实例的页面（如DETAIL, WRITING_DESK），使用参数作为缓存键
        cache_key = page_type
        if page_type in ['DETAIL', 'WRITING_DESK']:
            project_id = params.get('project_id')
            if not project_id:
                logger.error(
                    "页面 %s 缺少必需的 project_id 参数，params=%s",
                    page_type, params
                )
                return None
            cache_key = f"{page_type}_{project_id}"

        # 检查缓存
        if cache_key in self.pages:
            # LRU: 移到最后（标记为最近使用）
            self.pages.move_to_end(cache_key)
            return self.pages[cache_key]

        # 创建新页面
        page = self.createPage(page_type, params)

        if page is None:
            return None

        # 连接导航信号
        if hasattr(page, 'navigateRequested'):
            page.navigateRequested.connect(self.onNavigateRequested)

        if hasattr(page, 'goBackRequested'):
            page.goBackRequested.connect(self.goBack)

        if hasattr(page, 'navigateReplaceRequested'):
            page.navigateReplaceRequested.connect(self.onNavigateReplaceRequested)

        # 添加到容器和缓存
        self.page_stack.addWidget(page)
        self.pages[cache_key] = page

        # LRU淘汰：检查是否超出缓存限制
        self._evict_if_needed(cache_key)

        return page

    def _evict_if_needed(self, current_key: str):
        """如果超出缓存限制，淘汰最久未使用的页面

        Args:
            current_key: 当前新添加的页面缓存键（不应被淘汰）
        """
        if len(self.pages) <= self.MAX_CACHED_PAGES:
            return

        # 创建候选列表（排除重要页面、当前页面、正在显示的页面）
        current_widget = self.page_stack.currentWidget()
        candidates = []
        for key in self.pages.keys():
            page_type = key.split('_')[0]
            page = self.pages[key]
            # 跳过重要页面、当前键、当前显示的页面
            if page_type in self.IMPORTANT_PAGES:
                continue
            if key == current_key:
                continue
            if page == current_widget:
                continue
            candidates.append(key)

        if not candidates:
            logger.warning("LRU缓存已满但没有可淘汰的页面")
            return

        # 淘汰第一个候选（最久未使用的）
        oldest_key = candidates[0]
        oldest_page = self.pages.pop(oldest_key)

        # 使用统一的页面清理方法
        self._safe_cleanup_page(oldest_page, oldest_key)

        logger.info(f"LRU淘汰页面: {oldest_key} (缓存大小: {len(self.pages)}/{self.MAX_CACHED_PAGES})")

    def _safe_cleanup_page(self, page, page_key: str):
        """安全地清理单个页面

        按顺序执行清理操作，确保所有资源被正确释放：
        1. 调用 onHide() - 通知页面即将隐藏
        2. 调用 cleanup() - 清理内部资源（Timer、Worker等）
        3. 从堆栈移除
        4. 调用 deleteLater() - 延迟删除

        Args:
            page: 要清理的页面widget
            page_key: 页面缓存键（用于日志）
        """
        # 1. 调用页面的隐藏钩子
        try:
            if hasattr(page, 'onHide'):
                page.onHide()
        except RuntimeError:
            logger.debug(f"页面 {page_key} 已被删除，跳过onHide")
        except Exception as e:
            logger.warning(f"调用页面 {page_key} 的onHide时出错: {e}")

        # 2. 调用页面的清理方法（释放Timer、Worker等内部资源）
        try:
            if hasattr(page, 'cleanup'):
                page.cleanup()
        except RuntimeError:
            logger.debug(f"页面 {page_key} 已被删除，跳过cleanup")
        except Exception as e:
            logger.warning(f"调用页面 {page_key} 的cleanup时出错: {e}")

        # 3. 从堆栈中移除
        try:
            self.page_stack.removeWidget(page)
        except RuntimeError:
            logger.debug(f"页面 {page_key} 已被删除，跳过removeWidget")
        except Exception as e:
            logger.warning(f"移除页面 {page_key} 时出错: {e}")

        # 4. 延迟删除widget
        try:
            page.deleteLater()
        except RuntimeError:
            pass  # 对象已被删除
        except Exception as e:
            logger.warning(f"删除页面 {page_key} 时出错: {e}")

    def clearCache(self, exclude_current=True):
        """手动清空页面缓存

        Args:
            exclude_current: 是否保留当前页面
        """
        current_widget = self.page_stack.currentWidget()
        keys_to_remove = []

        for key, page in list(self.pages.items()):
            # 保留当前页面
            if exclude_current and page == current_widget:
                continue

            # 保留重要页面
            page_type = key.split('_')[0]
            if page_type in self.IMPORTANT_PAGES:
                continue

            keys_to_remove.append(key)

        # 执行删除
        for key in keys_to_remove:
            page = self.pages.pop(key)
            self._safe_cleanup_page(page, key)

        logger.info(f"清理了 {len(keys_to_remove)} 个页面，剩余 {len(self.pages)} 个")

    def createPage(self, page_type: str, params: dict):
        """创建页面实例

        使用PageRegistry模式，解耦页面创建逻辑。
        新增页面只需在page_registry.py中注册，无需修改此方法。

        Args:
            page_type: 页面类型
            params: 页面参数

        Returns:
            新创建的页面widget，页面类型未注册则返回 None
        """
        from utils.page_registry import create_page, is_page_registered

        if not is_page_registered(page_type):
            logger.error("未注册的页面类型: %s", page_type)
            return None

        try:
            return create_page(page_type, self, **params)
        except Exception as e:
            logger.exception("创建页面 %s 失败: %s", page_type, e)
            return None

    def onNavigateRequested(self, page_type: str, params: dict):
        """处理页面导航请求信号

        Args:
            page_type: 目标页面类型
            params: 页面参数
        """
        self.navigateTo(page_type, params)

    def onNavigateReplaceRequested(self, page_type: str, params: dict):
        """处理替换导航请求信号

        导航到新页面，并移除当前页面在历史栈中的记录。
        这样返回时会跳过当前页面，直接返回到更早的页面。

        Args:
            page_type: 目标页面类型
            params: 页面参数
        """
        # 移除当前页面的历史记录
        if self.navigation_history:
            self.navigation_history.pop()

        # 安全地调用当前页面隐藏钩子
        current_widget = self.page_stack.currentWidget()
        try:
            if current_widget and hasattr(current_widget, 'onHide'):
                current_widget.onHide()
        except RuntimeError:
            logger.debug("当前页面已被删除，跳过onHide")
        except Exception as e:
            logger.warning(f"调用当前页面onHide时出错: {e}")

        # 导航到新页面
        self.navigateTo(page_type, params)

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 断开主题信号
        self._disconnect_theme_signal()

        # 清理主题配置加载 worker
        if hasattr(self, '_theme_config_worker') and self._theme_config_worker is not None:
            try:
                if hasattr(self._theme_config_worker, 'cancel'):
                    self._theme_config_worker.cancel()
                if self._theme_config_worker.isRunning():
                    self._theme_config_worker.wait(100)
            except Exception:
                pass
            self._theme_config_worker = None

        # 清理主题切换辅助类
        if hasattr(self, '_theme_switch_helper'):
            self._theme_switch_helper.cleanup()

        # 清理所有缓存的页面（使用统一的清理方法）
        for cache_key, page in list(self.pages.items()):
            self._safe_cleanup_page(page, cache_key)

        self.pages.clear()

        # 关闭 API 客户端单例
        APIClientManager.shutdown()

        super().closeEvent(event)
