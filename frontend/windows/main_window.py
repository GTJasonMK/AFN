"""
主窗口 - 页面导航容器

功能：
- 使用QStackedWidget管理所有页面
- 统一的页面导航系统
- 导航历史栈支持返回按钮
- LRU页面缓存淘汰机制避免内存泄漏
- DPI感知和响应式布局
"""

import json
import logging
from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QPushButton, QWidget, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QKeySequence
from typing import Dict, List, Tuple
from collections import OrderedDict
from themes.theme_manager import theme_manager, ThemeMode
from themes.modern_effects import ModernEffects
from themes.svg_icons import SVGIcons
from utils.dpi_utils import dpi_helper, dp, sp
from api.manager import APIClientManager

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
        self.setCentralWidget(self.central_widget)

        # 主布局
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 页面容器
        self.page_stack = QStackedWidget()
        main_layout.addWidget(self.page_stack)

        # 创建浮动工具栏（包含主题切换按钮）
        self.create_floating_toolbar()

        # 页面缓存：使用OrderedDict实现LRU
        # {cache_key: page_widget}
        self.pages = OrderedDict()

        # 导航历史栈：[(page_type, params)]
        self.navigation_history: List[Tuple[str, dict]] = []

        # 主题信号连接标志
        self._theme_connected = False
        self._connect_theme_signal()

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
        """切换主题"""
        theme_manager.switch_theme()

    def apply_window_theme(self):
        """应用主题样式到窗口和容器"""
        # 设置主窗口和中心容器的背景色
        window_style = f"""
            QMainWindow {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QWidget#centralWidget {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QStackedWidget {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
        """
        self.setStyleSheet(window_style)

        # 设置central_widget的对象名称以便样式选择器使用
        self.central_widget.setObjectName("centralWidget")

    def on_theme_changed(self, mode: str):
        """主题改变时的处理

        优化说明：
        - 各组件已通过 ThemeAware 基类自动响应主题信号
        - 此处只需更新主窗口自身的样式和浮动工具栏
        - 不再遍历整棵组件树，提升性能
        """
        # 应用窗口主题
        self.apply_window_theme()

        # 更新按钮样式
        self.update_theme_button()

        # 强制刷新主窗口的样式缓存（仅顶层）
        self._refresh_top_level_style()

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
        """导航到指定页面

        Args:
            page_type: 页面类型（HOME, INSPIRATION, DETAIL, WRITING_DESK, SETTINGS）
            params: 页面参数（如project_id等）
        """
        if params is None:
            params = {}

        logger.info("navigateTo called: page_type=%s, params=%s", page_type, params)

        # 获取或创建页面
        page = self.getOrCreatePage(page_type, params)

        if page is None:
            logger.error(
                "无法创建页面: page_type=%s, params=%s (可能缺少必需参数)",
                page_type, params
            )
            return

        logger.info("Page created/retrieved successfully: %s", type(page).__name__)

        # 调用页面刷新方法
        if hasattr(page, 'refresh'):
            page.refresh(**params)

        # 切换到页面
        self.page_stack.setCurrentWidget(page)
        logger.info("Page switched to: %s", page_type)

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

        Args:
            page_type: 页面类型
            params: 页面参数

        Returns:
            新创建的页面widget
        """
        try:
            if page_type == 'HOME':
                from pages.home_page import HomePage
                return HomePage(self)

            elif page_type == 'INSPIRATION':
                from windows.inspiration_mode import InspirationMode
                return InspirationMode(self)

            elif page_type == 'DETAIL':
                from windows.novel_detail import NovelDetail
                project_id = params.get('project_id')
                if not project_id:
                    logger.error("DETAIL页面缺少project_id参数")
                    return None
                return NovelDetail(project_id, self)

            elif page_type == 'WRITING_DESK':
                from windows.writing_desk import WritingDesk
                project_id = params.get('project_id')
                if not project_id:
                    logger.error("WRITING_DESK页面缺少project_id参数")
                    return None
                return WritingDesk(project_id, self)

            elif page_type == 'SETTINGS':
                from windows.settings import SettingsView
                return SettingsView(self)

            else:
                logger.error(f"未知页面类型 {page_type}")
                return None

        except Exception as e:
            logger.exception(f"创建页面 {page_type} 失败: {e}")
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

        # 清理所有缓存的页面（使用统一的清理方法）
        for cache_key, page in list(self.pages.items()):
            self._safe_cleanup_page(page, cache_key)

        self.pages.clear()

        # 关闭 API 客户端单例
        APIClientManager.shutdown()

        super().closeEvent(event)
