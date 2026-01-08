"""
写作台主工作区 - 章节显示 Mixin

包含章节加载、显示和创建章节Widget相关的方法。

性能优化：
- LRU缓存：缓存最近访问的章节，避免重复API调用
- 相邻预取：加载章节时预取前后章节
"""

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QFrame,
    QTabWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from utils.error_handler import handle_errors
from utils.formatters import count_chinese_characters, format_word_count
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncAPIWorker
from utils.chapter_cache import get_chapter_cache
from components.loading_spinner import LoadingOverlay

import logging

logger = logging.getLogger(__name__)


class ChapterDisplayMixin:
    """章节显示相关方法的 Mixin"""

    def _ensure_loading_overlay(self):
        """确保加载覆盖层已创建"""
        if not hasattr(self, '_chapter_loading_overlay') or self._chapter_loading_overlay is None:
            self._chapter_loading_overlay = LoadingOverlay(
                text="正在加载章节...",
                parent=self,
                translucent=True
            )

    def loadChapter(self, chapter_number):
        """异步加载章节（带缓存和节流）

        性能优化：
        1. 优先从缓存获取，命中则直接显示（无需加载动画）
        2. 缓存未命中时才发起API请求
        3. 加载完成后存入缓存并预取相邻章节
        4. 节流机制：快速连续切换时只执行最后一次请求
        """
        from PyQt6.QtCore import QTimer

        # 如果请求的是当前已加载的章节，直接返回
        if hasattr(self, '_last_loaded_chapter') and self._last_loaded_chapter == chapter_number:
            return

        # 章节切换：重置漫画加载标志，防止旧的加载任务阻止新的加载
        self._manga_loading = False

        # 记录待加载的章节
        self._pending_load_chapter = chapter_number
        self.current_chapter = chapter_number

        if not self.project_id:
            return

        # 优先从缓存获取
        cache = get_chapter_cache()
        cached_data = cache.get(self.project_id, chapter_number)

        if cached_data:
            # 缓存命中，直接显示（无需加载动画，响应更快）
            logger.debug(f"章节缓存命中: 第{chapter_number}章")
            self._last_loaded_chapter = chapter_number

            # 取消可能正在进行的加载任务
            self._cancel_chapter_load_worker()

            # 隐藏加载动画（如果有）
            if hasattr(self, '_chapter_loading_overlay') and self._chapter_loading_overlay:
                self._chapter_loading_overlay.hide_with_animation()

            # 直接显示章节
            self.displayChapter(cached_data)

            # 后台预取相邻章节
            self._prefetch_adjacent_chapters(chapter_number)
            return

        # 缓存未命中，走异步加载流程
        logger.debug(f"章节缓存未命中: 第{chapter_number}章")

        # 节流机制：复用定时器，只重置时间
        if not hasattr(self, '_load_chapter_timer') or self._load_chapter_timer is None:
            self._load_chapter_timer = QTimer()
            self._load_chapter_timer.setSingleShot(True)
            self._load_chapter_timer.timeout.connect(self._on_throttle_timeout)
        else:
            # 停止当前定时器
            self._load_chapter_timer.stop()

        # 立即取消正在进行的加载任务
        self._cancel_chapter_load_worker()

        # 立即显示加载动画（给用户即时反馈）
        self._ensure_loading_overlay()
        self._chapter_loading_overlay.show_with_animation("正在加载章节...")

        # 延迟执行实际加载（节流：50ms内的连续请求只执行最后一次）
        self._load_chapter_timer.start(50)

    def _on_throttle_timeout(self):
        """节流定时器超时回调"""
        chapter_number = getattr(self, '_pending_load_chapter', None)
        if chapter_number is not None:
            self._do_load_chapter(chapter_number)

    def _do_load_chapter(self, chapter_number):
        """执行实际的章节加载"""
        # 验证这仍然是用户想要的章节
        if getattr(self, '_pending_load_chapter', None) != chapter_number:
            return

        if not self.project_id:
            return

        # 再次取消可能存在的旧任务
        self._cancel_chapter_load_worker()

        # 异步加载章节数据
        worker = AsyncAPIWorker(
            self.api_client.get_chapter,
            self.project_id,
            chapter_number
        )
        worker.success.connect(self._onChapterLoaded)
        worker.error.connect(self._onChapterLoadError)

        # 保存worker引用避免被垃圾回收
        self._chapter_load_worker = worker
        worker.start()

    def _cancel_chapter_load_worker(self):
        """取消正在进行的章节加载任务（非阻塞）"""
        if hasattr(self, '_chapter_load_worker') and self._chapter_load_worker:
            worker = self._chapter_load_worker
            try:
                # 安全检查：C++ 对象可能已被删除
                if worker.isRunning():
                    # 断开信号连接，防止旧任务回调干扰新任务
                    try:
                        worker.success.disconnect()
                        worker.error.disconnect()
                    except (TypeError, RuntimeError):
                        pass
                    worker.cancel()
                    # 不再等待线程结束，避免阻塞主线程
                    # worker.wait(500)  # 移除阻塞等待
            except RuntimeError:
                # C++ 对象已被删除，忽略
                pass
            self._chapter_load_worker = None

    def _onChapterLoaded(self, chapter_data):
        """章节数据加载成功回调"""
        # 验证加载的章节是否是用户当前请求的
        loaded_chapter = chapter_data.get('chapter_number')
        pending_chapter = getattr(self, '_pending_load_chapter', None)

        if pending_chapter is not None and loaded_chapter != pending_chapter:
            # 用户已切换到其他章节，丢弃这个结果
            return

        # 存入缓存
        cache = get_chapter_cache()
        cache.set(self.project_id, loaded_chapter, chapter_data)

        # 记录已加载的章节
        self._last_loaded_chapter = loaded_chapter

        # 隐藏加载动画
        if hasattr(self, '_chapter_loading_overlay') and self._chapter_loading_overlay:
            self._chapter_loading_overlay.hide_with_animation()

        # 显示章节内容
        self.displayChapter(chapter_data)

        # 后台预取相邻章节
        self._prefetch_adjacent_chapters(loaded_chapter)

    def _prefetch_adjacent_chapters(self, current_chapter: int):
        """后台预取相邻章节

        Args:
            current_chapter: 当前章节号
        """
        if not self.project_id or not hasattr(self, 'project') or not self.project:
            return

        # 获取总章节数
        chapters = self.project.get('chapters', [])
        total_chapters = len(chapters)

        if total_chapters <= 1:
            return

        # 使用缓存的预取功能
        cache = get_chapter_cache()
        cache.prefetch_adjacent(
            self.project_id,
            current_chapter,
            total_chapters,
            self.api_client.get_chapter
        )

    def _onChapterLoadError(self, error_msg):
        """章节数据加载失败回调"""
        # 隐藏加载动画
        if hasattr(self, '_chapter_loading_overlay') and self._chapter_loading_overlay:
            self._chapter_loading_overlay.hide_with_animation()

        # 清除版本切换状态，重新启用保存按钮
        # 即使加载失败也要清除状态，避免按钮永久禁用
        if hasattr(self, '_version_switching'):
            self._version_switching = False
            self._updateSaveButtonState()

        # 显示错误提示
        from utils.message_service import MessageService
        MessageService.show_error(self, f"加载章节失败：{error_msg}")

    def displayChapter(self, chapter_data):
        """显示章节内容 - 优化版：复用组件减少重建开销"""
        # 保存章节数据用于主题切换
        self.current_chapter_data = chapter_data

        # 清理旧章节的漫画缓存和状态
        self._clear_manga_cache()

        # 清除版本切换状态，重新启用保存按钮
        # 这确保了在章节内容完全加载后才允许保存
        if hasattr(self, '_version_switching'):
            self._version_switching = False
            self._updateSaveButtonState()

        # 记录当前版本ID（用于保存时验证）
        if hasattr(self, '_current_version_id'):
            self._current_version_id = chapter_data.get('selected_version_id')

        # 尝试复用现有组件（如果结构相同）
        if self.content_widget and self.tab_widget:
            # 复用模式：更新现有组件数据
            self._updateChapterContent(chapter_data)
        else:
            # 首次创建或需要重建
            if self.content_widget:
                self.stack.removeWidget(self.content_widget)
                self.content_widget.deleteLater()

            self.content_widget = self.createChapterWidget(chapter_data)
            self.stack.addWidget(self.content_widget)

        self.stack.setCurrentWidget(self.content_widget)

        # 发射章节内容加载完成信号（用于优化面板）
        chapter_number = chapter_data.get('chapter_number')
        # 注意：get('content', '') 在 content 为 None 时仍返回 None，需要用 or
        content = chapter_data.get('content') or ''
        if chapter_number:
            # 即使内容为空也发射信号，让优化面板显示正确的状态
            self.chapterContentLoaded.emit(chapter_number, content)

    def _clear_manga_cache(self):
        """清理漫画相关的缓存和状态

        在切换章节时调用，确保旧章节的漫画数据不会影响新章节。
        """
        # 清理漫画数据缓存
        if hasattr(self, '_cached_manga_data'):
            self._cached_manga_data = None

    def _updateChapterContent(self, chapter_data):
        """更新现有组件的数据（复用模式）

        使用批量更新优化：
        1. 禁用UI更新，避免多次重绘
        2. 更新懒加载Tab的数据引用，标记需要重新加载
        3. 只有当前激活的Tab才立即刷新
        """
        # 禁用UI更新，批量操作完成后统一重绘
        if self.content_widget:
            self.content_widget.setUpdatesEnabled(False)

        try:
            # 更新懒加载数据引用（供懒加载器使用）
            self._current_lazy_chapter_data = chapter_data

            # 1. 更新章节标题（最重要的视觉反馈）
            if self.chapter_title:
                title = chapter_data.get('title', f"第{chapter_data.get('chapter_number', '')}章")
                self.chapter_title.setText(title)

            # 2. 更新章节元信息标签
            if hasattr(self, 'content_widget') and self.content_widget:
                meta_label = self.content_widget.findChild(QLabel, "chapter_meta_label")
                if meta_label:
                    meta_text = f"第 {chapter_data.get('chapter_number', '')} 章"
                    content = chapter_data.get('content', '')
                    if content:
                        word_count = count_chinese_characters(content)
                        meta_text += f" | {format_word_count(word_count)}"
                    meta_label.setText(meta_text)

            # 3. 更新正文Tab（使用ContentPanelBuilder的set_content方法）
            content = chapter_data.get('content') or ''
            if content:
                self._content_builder.set_content(content)
            else:
                self._content_builder.set_content('暂无内容，请点击"生成章节"按钮')

            # 4. 更新字数统计标签
            if self.content_widget:
                word_count_label = self.content_widget.findChild(QLabel, "word_count_label")
                if word_count_label:
                    word_count = count_chinese_characters(content) if content else 0
                    word_count_label.setText(f"字数：{format_word_count(word_count)}")

            # 5. 标记所有懒加载Tab需要重新加载
            # 由于使用了懒加载，只需失效Tab即可，下次切换时会自动重新加载
            if self.tab_widget and hasattr(self.tab_widget, 'invalidate_all_lazy_tabs'):
                self.tab_widget.invalidate_all_lazy_tabs()

                # 如果当前激活的是懒加载Tab（非正文Tab），立即刷新
                current_index = self.tab_widget.currentIndex()
                if current_index > 0:  # 0 是正文Tab，不需要懒加载
                    self.tab_widget.reload_tab(current_index)

            # 失效主题缓存（因为Tab内容变化了）
            self._invalidate_theme_cache()

        finally:
            # 恢复UI更新，触发一次重绘
            if self.content_widget:
                self.content_widget.setUpdatesEnabled(True)

    def createChapterWidget(self, chapter_data):
        """创建章节内容widget（优化版：分步创建，避免UI卡顿）"""
        from PyQt6.QtWidgets import QApplication

        # 使用书香风格字体
        serif_font = theme_manager.serif_font()

        widget = QWidget()
        # 设置明确的颜色以避免系统默认
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {theme_manager.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(dp(20), dp(16), dp(20), dp(16))  # 压缩外边距
        layout.setSpacing(dp(12))  # 减少间距

        # 章节标题卡片 - 紧凑版渐变设计
        header = QFrame()
        header.setObjectName("chapter_header")

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(dp(12))
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, dp(2))
        header.setGraphicsEffect(shadow)

        # 应用渐变背景
        gradient = ModernEffects.linear_gradient(
            theme_manager.PRIMARY_GRADIENT,
            135
        )
        header.setStyleSheet(f"""
            QFrame#chapter_header {{
                background: {gradient};
                border: none;
                border-radius: {theme_manager.RADIUS_MD};
                padding: {dp(12)}px;
            }}
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setSpacing(dp(12))
        header_layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))  # 紧凑内边距

        # 左侧：章节信息
        info_widget = QWidget()
        # 确保透明背景以显示父元素的渐变背景
        info_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(dp(4))

        self.chapter_title = QLabel(chapter_data.get('title', f"第{chapter_data.get('chapter_number', '')}章"))
        self.chapter_title.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(18)}px;
            font-weight: 700;
            color: {theme_manager.BUTTON_TEXT};
        """)
        info_layout.addWidget(self.chapter_title)

        # 章节元信息
        meta_text = f"第 {chapter_data.get('chapter_number', '')} 章"
        content = chapter_data.get('content', '')
        if content:
            word_count = count_chinese_characters(content)
            meta_text += f" | {format_word_count(word_count)}"

        meta_label = QLabel(meta_text)
        meta_label.setObjectName("chapter_meta_label")  # 添加objectName用于主题切换
        meta_label.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {sp(12)}px;
            color: {theme_manager.BUTTON_TEXT};
            opacity: 0.85;
        """)
        info_layout.addWidget(meta_label)

        header_layout.addWidget(info_widget, stretch=1)

        # 右侧：按钮组 - 紧凑版
        btn_widget = QWidget()
        btn_widget.setStyleSheet("background-color: transparent;")
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(dp(8))

        # 渐变背景的动态覆盖色
        # 亮色主题：渐变是深色赭石色，覆盖层使用白色
        # 深色主题：渐变是亮色琥珀色，覆盖层使用深色
        is_dark = theme_manager.is_dark_mode()
        overlay_rgb = "0, 0, 0" if is_dark else "255, 255, 255"

        # 预览提示词按钮
        self.preview_btn = QPushButton("预览提示词")
        self.preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.preview_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {serif_font};
                background-color: transparent;
                color: {theme_manager.BUTTON_TEXT};
                border: 1px solid rgba({overlay_rgb}, 0.3);
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(12)}px;
                font-size: {sp(12)}px;
            }}
            QPushButton:hover {{
                background-color: rgba({overlay_rgb}, 0.15);
                border-color: rgba({overlay_rgb}, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba({overlay_rgb}, 0.1);
            }}
        """)
        self.preview_btn.clicked.connect(lambda: self.previewPromptRequested.emit(self.current_chapter))
        btn_layout.addWidget(self.preview_btn)

        # 生成章节按钮
        self.generate_btn = QPushButton("生成章节")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: {serif_font};
                background-color: rgba({overlay_rgb}, 0.2);
                color: {theme_manager.BUTTON_TEXT};
                border: 1px solid rgba({overlay_rgb}, 0.3);
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba({overlay_rgb}, 0.3);
                border-color: rgba({overlay_rgb}, 0.5);
            }}
            QPushButton:pressed {{
                background-color: rgba({overlay_rgb}, 0.15);
            }}
        """)
        self.generate_btn.clicked.connect(lambda: self.generateChapterRequested.emit(self.current_chapter))
        btn_layout.addWidget(self.generate_btn)

        header_layout.addWidget(btn_widget)

        layout.addWidget(header)

        # TabWidget：使用懒加载Tab优化首次渲染性能
        # 正文Tab立即加载（用户最常用），其他Tab懒加载
        from components.lazy_tab_widget import LazyTabWidget

        self.tab_widget = LazyTabWidget()
        self.tab_widget.setStyleSheet(theme_manager.tabs())

        # 保存当前chapter_data引用，供懒加载器使用
        self._current_lazy_chapter_data = chapter_data

        # Tab 1: 正文 - 立即加载（最重要，用户切换章节首先看到的）
        content_tab = self._content_builder.create_content_tab(chapter_data)
        self.content_text = self._content_builder.content_text  # 保存引用用于主题切换
        self.tab_widget.addTab(content_tab, "正文")

        # Tab 2: 版本历史 - 懒加载
        self.tab_widget.addLazyTab(
            "版本",
            loader_func=lambda: self._version_builder.create_versions_tab(
                self._current_lazy_chapter_data, self
            ),
            placeholder_text="正在加载版本历史..."
        )

        # Tab 3: 评审 - 懒加载
        self.tab_widget.addLazyTab(
            "评审",
            loader_func=lambda: self._review_builder.create_review_tab(
                self._current_lazy_chapter_data, self
            ),
            placeholder_text="正在加载评审信息..."
        )

        # Tab 4: 章节摘要 - 懒加载
        self.tab_widget.addLazyTab(
            "摘要",
            loader_func=lambda: self._summary_builder.create_summary_tab(
                self._current_lazy_chapter_data, self
            ),
            placeholder_text="正在加载章节摘要..."
        )

        # Tab 5: 章节分析 - 懒加载
        self.tab_widget.addLazyTab(
            "分析",
            loader_func=lambda: self._analysis_builder.create_analysis_tab(
                self._current_lazy_chapter_data
            ),
            placeholder_text="正在加载章节分析..."
        )

        # Tab 6: 漫画提示词 - 懒加载（异步加载数据）
        self.tab_widget.addLazyTab(
            "漫画",
            loader_func=self._create_manga_tab_lazy,
            placeholder_text="正在加载漫画数据..."
        )

        layout.addWidget(self.tab_widget, stretch=1)

        return widget

    def _create_manga_tab_lazy(self):
        """懒加载创建漫画Tab

        在Tab首次激活时调用，触发异步加载漫画数据。
        """
        # 先创建空状态的漫画Tab
        empty_manga_data = {
            'has_manga_prompt': False,
            'scenes': [],
            'character_profiles': {},
            'style_guide': '',
            'images': [],
            'pdf_info': {},
            '_is_loading': True,
        }
        manga_tab = self._manga_builder.create_manga_tab(empty_manga_data, self)

        # 异步加载漫画数据
        self._loadMangaDataAsync()

        return manga_tab
