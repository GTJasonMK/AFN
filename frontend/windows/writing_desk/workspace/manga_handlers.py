"""
写作台主工作区 - 漫画处理 Mixin

包含漫画提示词生成、图片生成、PDF导出等功能的回调处理。
基于专业漫画分镜架构，支持页面模板和画格级提示词。
"""

import logging
import os
import subprocess
import platform

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from utils.async_worker import AsyncWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class MangaHandlersMixin:
    """漫画相关处理方法的 Mixin"""

    def _prepareMangaData(self, chapter_data: dict) -> dict:
        """
        准备漫画面板数据

        Args:
            chapter_data: 章节数据

        Returns:
            漫画面板所需的数据字典
        """
        manga_data = {
            'has_manga_prompt': False,
            'scenes': [],            # 场景列表（含页面信息）
            'panels': [],            # 画格提示词列表
            'page_prompts': [],      # 整页提示词列表（用于整页生成）
            'character_profiles': {},
            'total_pages': 0,
            'total_panels': 0,
            'style': '',
            'dialogue_language': 'chinese',  # 对话/音效语言
            'images': [],            # 已生成的图片列表
            'pdf_info': {},          # PDF信息
            # 断点续传信息
            'can_resume': False,
            'resume_progress': None,
            # 分析数据（详细信息Tab使用）
            'analysis_data': None,
            # 增量生成状态
            'is_complete': True,
            'completed_pages_count': 0,
        }

        # 使用传入的章节号，避免在后台线程中访问可能已变化的 self.current_chapter
        chapter_number = chapter_data.get('chapter_number') if chapter_data else self.current_chapter

        # 尝试从API获取已保存的漫画分镜
        if self.project_id and chapter_number:
            try:
                result = self.api_client.get_manga_prompts(
                    self.project_id, chapter_number
                )
                if result:
                    manga_data['has_manga_prompt'] = True
                    manga_data['character_profiles'] = result.get('character_profiles', {})
                    manga_data['total_pages'] = result.get('total_pages', 0)
                    manga_data['total_panels'] = result.get('total_panels', 0)
                    manga_data['style'] = result.get('style', '')
                    # 保存对话语言设置
                    dialogue_language = result.get('dialogue_language', 'chinese')
                    manga_data['dialogue_language'] = dialogue_language
                    # 获取分析数据（详细信息Tab显示）
                    manga_data['analysis_data'] = result.get('analysis_data')
                    # 增量生成状态
                    manga_data['is_complete'] = result.get('is_complete', True)
                    manga_data['completed_pages_count'] = result.get('completed_pages_count', 0)
                    # 整页提示词列表（用于整页生成）
                    manga_data['page_prompts'] = result.get('page_prompts', [])

                    # 后端返回 pages，前端需要 scenes
                    # 将 page_number 转换为 scene_id
                    pages = result.get('pages', [])
                    scenes = []
                    for page in pages:
                        scene = dict(page)
                        scene['scene_id'] = page.get('page_number', 0)
                        scenes.append(scene)
                    manga_data['scenes'] = scenes

                    # 为每个 panel 添加 scene_id 和 dialogue_language
                    panels = result.get('panels', [])
                    for panel in panels:
                        if 'scene_id' not in panel:
                            panel['scene_id'] = panel.get('page_number', 0)
                        # 确保每个panel都有dialogue_language字段
                        if 'dialogue_language' not in panel:
                            panel['dialogue_language'] = dialogue_language
                    manga_data['panels'] = panels
            except Exception as e:
                # 如果获取失败，记录错误并保持默认空状态
                logger.warning("获取漫画分镜数据失败: %s", e)

            # 检查断点状态（无论是否有内容，都检查生成状态）
            # 如果有内容但状态不是completed，说明生成中途失败，应该可以继续
            try:
                progress = self.api_client.get_manga_prompt_progress(
                    self.project_id, self.current_chapter
                )
                if progress:
                    status = progress.get('status', '')
                    can_resume = progress.get('can_resume', False)
                    # 如果状态不是completed/pending且can_resume=True，允许继续
                    if can_resume and status not in ('completed', 'pending'):
                        manga_data['can_resume'] = True
                        manga_data['resume_progress'] = progress
                    # 如果没有内容但可以继续（之前的断点逻辑）
                    elif not manga_data['has_manga_prompt'] and can_resume:
                        manga_data['can_resume'] = True
                        manga_data['resume_progress'] = progress
            except Exception:
                pass

            # 获取已生成的图片列表
            try:
                images = self._loadChapterImages()
                manga_data['images'] = images

                # 按 panel_id 精确匹配图片（画格级）
                # 只有精确匹配 panel_id 的画格才显示"已生成"状态
                # 旧图片（没有panel_id）不会显示在任何画格上，需要重新生成
                panel_image_map = {}  # panel_id -> [images]
                # 按 page_number 匹配图片（整页级）
                page_image_map = {}  # page_number -> [images]

                for img in images:
                    image_type = img.get('image_type', 'panel')
                    if image_type == 'page':
                        # 整页类型图片，按 scene_id（实际存的是page_number）匹配
                        page_num = img.get('scene_id')
                        if page_num:
                            if page_num not in page_image_map:
                                page_image_map[page_num] = []
                            page_image_map[page_num].append(img)
                    else:
                        # 画格类型图片
                        panel_id = img.get('panel_id')
                        if panel_id:
                            if panel_id not in panel_image_map:
                                panel_image_map[panel_id] = []
                            panel_image_map[panel_id].append(img)

                # 更新画格数据，标记已生成图片的画格（仅精确匹配）
                for panel in manga_data['panels']:
                    panel_id = panel.get('panel_id', '')

                    if panel_id in panel_image_map:
                        panel['has_image'] = True
                        # Bug 39 修复: 后端按 created_at.desc() 排序（最新在前）
                        # 使用 [0] 获取最新图片，而非 [-1] 获取最旧图片
                        panel['image_path'] = panel_image_map[panel_id][0].get('local_path', '')
                        panel['image_count'] = len(panel_image_map[panel_id])

                # 更新整页提示词数据，标记已生成图片的页面
                for page_prompt in manga_data.get('page_prompts', []):
                    page_num = page_prompt.get('page_number')
                    if page_num and page_num in page_image_map:
                        page_prompt['has_image'] = True
                        page_prompt['image_path'] = page_image_map[page_num][0].get('local_path', '')
                        page_prompt['image_count'] = len(page_image_map[page_num])
            except Exception:
                pass

            # 获取最新的漫画PDF信息
            try:
                pdf_info = self._loadChapterMangaPDF()
                manga_data['pdf_info'] = pdf_info
            except Exception:
                pass

        return manga_data

    def _loadMangaDataAsync(self):
        """
        异步加载漫画数据，避免UI阻塞

        使用AsyncWorker在后台线程加载漫画提示词、图片和PDF信息，
        加载完成后更新漫画Tab的内容。
        """
        if not self.project_id or not self.current_chapter:
            return

        # 保存当前章节号，用于验证回调时章节未切换
        loading_chapter = self.current_chapter

        # 如果当前章节正在生成漫画提示词，跳过加载避免破坏加载状态显示
        # 注意：只跳过正在生成的章节，其他章节应该正常加载
        if getattr(self, '_manga_generating_chapter', None) == loading_chapter:
            logger.info("Skipping manga data load - generation in progress for chapter %d", loading_chapter)
            return

        # 防止重复加载：如果已有加载任务正在进行，跳过
        if getattr(self, '_manga_loading', False):
            logger.info("Skipping manga data load - already loading")
            return

        # 设置加载标志
        self._manga_loading = True

        def do_load():
            """在后台线程执行的加载函数"""
            return self._prepareMangaData({'chapter_number': loading_chapter})

        def on_success(manga_data):
            """加载成功回调"""
            # 清除加载标志
            self._manga_loading = False

            # 检查章节是否已切换，避免更新错误的Tab
            if self.current_chapter != loading_chapter:
                return

            # 如果当前章节正在生成，跳过更新
            if getattr(self, '_manga_generating_chapter', None) == loading_chapter:
                logger.info("Skipping manga tab update - generation in progress for chapter %d", loading_chapter)
                return

            # 缓存漫画数据，用于主题切换时重建Tab
            self._cached_manga_data = manga_data

            # 更新漫画Tab
            if self.tab_widget and self.tab_widget.count() >= 6:
                # 保存当前选中的Tab索引，避免刷新后跳转到其他页面
                current_tab_index = self.tab_widget.currentIndex()

                # 移除旧的漫画Tab
                old_manga_tab = self.tab_widget.widget(5)  # 漫画是第6个Tab（索引5）
                if old_manga_tab:
                    self.tab_widget.removeTab(5)
                    old_manga_tab.deleteLater()

                # 创建新的漫画Tab
                new_manga_tab = self._manga_builder.create_manga_tab(manga_data, self)
                self.tab_widget.insertTab(5, new_manga_tab, "漫画")

                # 更新LazyTabWidget的已加载标记，防止再次触发懒加载
                # 这是必要的，因为我们绕过了LazyTabWidget的加载机制直接替换了Tab
                if hasattr(self.tab_widget, '_tab_loaded'):
                    self.tab_widget._tab_loaded.add(5)

                # 恢复之前选中的Tab索引
                # 注意：移除和插入Tab后，QTabWidget可能自动切换了Tab
                # 需要确保恢复到用户之前查看的Tab
                self.tab_widget.setCurrentIndex(current_tab_index)

        def on_error(error):
            """加载失败回调 - 静默处理，保持空状态"""
            # 清除加载标志
            self._manga_loading = False

        worker = AsyncWorker(do_load)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()
        # 保存worker引用，防止被垃圾回收导致线程崩溃
        self._manga_loader_worker = worker

    def _loadChapterImages(self):
        """
        加载当前章节的所有已生成图片

        Returns:
            图片列表，每个图片包含 file_path, panel_id, prompt 等信息
        """
        if not self.project_id or not self.current_chapter:
            return []

        try:
            # API 直接返回图片列表
            images = self.api_client.get_chapter_images(
                self.project_id, self.current_chapter
            )

            # 确保返回的是列表
            if not isinstance(images, list):
                images = []

            # 为每个图片添加可用的路径
            for img in images:
                file_path = img.get('file_path', '')
                url = img.get('url', '')  # 后端返回的相对URL

                # 构造完整的HTTP URL（用于远程部署）
                if url:
                    img['http_url'] = f"{self.api_client.base_url}{url}"

                # 构造本地路径（用于单机部署，性能更好）
                if file_path:
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
                    local_path = os.path.join(base_dir, 'backend', 'storage', 'generated_images', file_path)
                    # 只有文件存在时才使用本地路径，否则回退到HTTP URL
                    if os.path.exists(local_path):
                        img['local_path'] = local_path
                    elif url:
                        img['local_path'] = img['http_url']

            return images
        except Exception:
            return []

    def _onGenerateMangaPrompt(
        self,
        style: str = "manga",
        min_pages: int = 8,
        max_pages: int = 15,
        language: str = "chinese",
        use_portraits: bool = True,
        auto_generate_portraits: bool = True,
        force_restart: bool = False,
        start_from_stage: str = None,
        auto_generate_page_images: bool = False,
        page_prompt_concurrency: int = 5,
    ):
        """
        生成漫画分镜回调

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            min_pages: 最少页数 (3-20)
            max_pages: 最多页数 (5-30)
            language: 对话/音效语言 (chinese/japanese/english/korean)
            use_portraits: 是否使用角色立绘作为参考图
            auto_generate_portraits: 是否自动为缺失立绘的角色生成立绘
            force_restart: 是否强制从头开始，忽略断点
            start_from_stage: 指定从哪个阶段开始 (extraction/planning/storyboard/prompt_building)
            auto_generate_page_images: 是否在分镜生成完成后自动生成所有整页图片
            page_prompt_concurrency: 整页提示词LLM生成的并发数 (1-20)
        """
        logger.info(f"=== _onGenerateMangaPrompt ENTRY === style={style}, force_restart={force_restart}, start_from_stage={start_from_stage}")

        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        # 防止重复点击：如果当前章节正在生成中，忽略请求
        if getattr(self, '_manga_generating_chapter', None) == self.current_chapter:
            logger.warning("漫画分镜正在生成中，忽略重复请求")
            MessageService.show_info(self, "正在生成中，请稍候...")
            return

        # 立即设置生成标志，防止竞态条件
        # 必须在任何阻塞操作（如确认对话框）之前设置，否则在对话框显示期间
        # 其他点击事件也会通过防重复检查，导致多个生成任务同时启动
        self._manga_generating_chapter = self.current_chapter
        logger.info(f"已设置 _manga_generating_chapter={self.current_chapter}")

        # 使用缓存数据检查是否已有分镜（避免同步API调用导致UI卡顿）
        # _cached_manga_data 在 _loadMangaDataAsync 成功后会被设置
        cached_data = getattr(self, '_cached_manga_data', None)
        has_existing_content = cached_data and cached_data.get('has_manga_prompt', False)

        # 只有强制从头开始且有现有内容时才需要确认
        if force_restart and has_existing_content:
            if not MessageService.confirm(
                self,
                "当前章节已有分镜数据，重新生成将覆盖现有数据。",
                "确定要重新生成吗？"
            ):
                # 用户取消，清除标志
                self._manga_generating_chapter = None
                return
        # 清除上一次的进度记录，用于检测变化
        self._manga_last_progress_stage = None
        self._manga_last_progress_current = -1

        # 根据 start_from_stage 显示不同的初始加载消息
        stage_loading_texts = {
            "extraction": "正在重新提取信息...",
            "planning": "正在重新规划页面...",
            "storyboard": "正在重新设计分镜...",
            "prompt_building": "正在重新构建提示词...",
            "page_prompt_building": "正在重新生成整页提示词...",
        }
        if start_from_stage and start_from_stage in stage_loading_texts:
            loading_text = stage_loading_texts[start_from_stage]
        elif force_restart:
            loading_text = "正在从头生成漫画分镜..."
        else:
            loading_text = "正在生成漫画分镜..."
        logger.info(f"Setting loading state, _manga_builder exists: {self._manga_builder is not None}")
        if self._manga_builder:
            self._manga_builder.set_toolbar_loading(True, loading_text)

        def do_generate():
            return self.api_client.generate_manga_prompts(
                self.project_id,
                self.current_chapter,
                style=style,
                min_pages=min_pages,
                max_pages=max_pages,
                language=language,
                use_portraits=use_portraits,
                auto_generate_portraits=auto_generate_portraits,
                force_restart=force_restart,
                start_from_stage=start_from_stage,
                auto_generate_page_images=auto_generate_page_images,
                page_prompt_concurrency=page_prompt_concurrency,
            )

        def on_success(result):
            # 停止进度轮询
            self._stopMangaProgressPolling()
            # 清除生成标志
            self._manga_generating_chapter = None
            # 显示成功状态
            total_pages = result.get('total_pages', 0)
            total_panels = result.get('total_panels', 0)
            if self._manga_builder:
                self._manga_builder.set_toolbar_success(f"生成成功: {total_pages}页 {total_panels}格")
            MessageService.show_success(self, f"漫画分镜生成成功: {total_pages}页, {total_panels}格")
            # 仅刷新漫画面板数据，避免过度刷新整个章节
            self._loadMangaDataAsync()

        def on_error(error):
            # 停止进度轮询
            self._stopMangaProgressPolling()
            # 清除生成标志
            self._manga_generating_chapter = None
            # 显示错误状态
            if self._manga_builder:
                self._manga_builder.set_toolbar_error("生成失败")
            MessageService.show_error(self, f"生成失败: {error}")

        # 开始异步生成（不阻塞UI显示加载信息）
        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._manga_worker = worker

        # 启动进度轮询定时器（每2秒查询一次进度）
        self._startMangaProgressPolling()

    def _startMangaProgressPolling(self):
        """启动漫画生成进度轮询"""
        # 停止之前可能存在的定时器
        self._stopMangaProgressPolling()

        # 创建新的定时器
        self._manga_progress_timer = QTimer()
        self._manga_progress_timer.timeout.connect(self._pollMangaProgress)
        self._manga_progress_timer.start(2000)  # 每2秒轮询一次
        logger.info("启动漫画生成进度轮询")

    def _stopMangaProgressPolling(self):
        """停止漫画生成进度轮询"""
        if hasattr(self, '_manga_progress_timer') and self._manga_progress_timer:
            self._manga_progress_timer.stop()
            self._manga_progress_timer = None
            logger.info("停止漫画生成进度轮询")

        # 停止进度查询的worker
        if hasattr(self, '_manga_progress_worker') and self._manga_progress_worker:
            self._manga_progress_worker = None

    def _onStopMangaGenerate(self):
        """停止漫画分镜生成回调"""
        if not self.project_id or not self._manga_generating_chapter:
            logger.warning("没有正在进行的漫画生成任务")
            return

        logger.info(f"用户请求停止漫画生成: chapter={self._manga_generating_chapter}")

        # 首先取消正在进行的生成 worker，避免其回调触发错误提示
        if hasattr(self, '_manga_worker') and self._manga_worker:
            try:
                # 断开信号连接，避免取消后仍触发 on_error
                self._manga_worker.success.disconnect()
                self._manga_worker.error.disconnect()
            except (TypeError, RuntimeError):
                # 信号可能已经断开
                pass
            # 取消 worker（如果支持）
            if hasattr(self._manga_worker, 'cancel'):
                self._manga_worker.cancel()
            self._manga_worker = None

        def do_cancel():
            return self.api_client.cancel_manga_prompt_generation(
                self.project_id, self._manga_generating_chapter
            )

        def on_success(result):
            if result.get('success', False):
                # 停止进度轮询
                self._stopMangaProgressPolling()
                # 清除生成标志
                self._manga_generating_chapter = None
                # 清除加载标志，确保可以重新加载
                self._manga_loading = False
                # 更新UI状态
                if self._manga_builder:
                    self._manga_builder.set_toolbar_error("已停止生成")
                MessageService.show_info(self, "已停止漫画分镜生成")
                # 刷新漫画面板数据
                self._loadMangaDataAsync()
            else:
                message = result.get('message', '取消失败')
                MessageService.show_warning(self, message)

        def on_error(error):
            MessageService.show_error(self, f"停止生成失败: {error}")

        worker = AsyncWorker(do_cancel)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用
        self._manga_cancel_worker = worker

    def _pollMangaProgress(self):
        """轮询漫画生成进度并更新UI"""
        # 检查是否仍在生成中
        if not getattr(self, '_manga_generating_chapter', None):
            self._stopMangaProgressPolling()
            return

        # 防止重复请求：如果上一次查询还未完成，跳过本次
        if getattr(self, '_manga_progress_polling', False):
            return

        self._manga_progress_polling = True

        def do_poll():
            return self.api_client.get_manga_prompt_progress(
                self.project_id, self._manga_generating_chapter
            )

        def on_success(progress):
            self._manga_progress_polling = False

            if not progress:
                return

            # 根据进度状态更新UI
            status = progress.get('status', '')
            stage = progress.get('stage', '')
            stage_label = progress.get('stage_label', '')
            current = progress.get('current', 0)
            total = progress.get('total', 0)
            message = progress.get('message', '')
            analysis_data = progress.get('analysis_data')

            # 构建进度消息
            if status == 'completed':
                # 如果轮询先于 on_success 收到 completed 状态，主动更新 UI
                # 这样可以避免 UI 卡在最后一次非 completed 的进度状态
                logger.info("进度轮询检测到 completed 状态，主动更新 UI")
                self._stopMangaProgressPolling()
                # 只更新工具栏状态，不清除 _manga_generating_chapter
                # _manga_generating_chapter 由 on_success 清除，避免竞态条件
                if self._manga_builder:
                    self._manga_builder.set_toolbar_success("生成完成")
                return

            # 检测阶段变化或进度变化，实时更新详细信息Tab
            last_stage = getattr(self, '_manga_last_progress_stage', None)
            last_current = getattr(self, '_manga_last_progress_current', -1)

            # 阶段变化或关键阶段进度变化时更新
            should_update = False
            if stage != last_stage:
                should_update = True
                self._manga_last_progress_stage = stage
            elif stage == 'extracting' and current != last_current:
                # 信息提取阶段每完成一步都更新（共4步）
                should_update = True
            elif stage == 'storyboard' and current != last_current:
                # storyboard阶段每完成一页都更新
                should_update = True
            elif stage == 'page_prompt_building' and current != last_current:
                # 整页提示词阶段每完成一页都更新
                should_update = True

            self._manga_last_progress_current = current

            if should_update and analysis_data and self._manga_builder:
                try:
                    self._manga_builder.update_details_tab(analysis_data)
                    logger.info(f"进度更新 stage={stage} current={current}，已更新详细信息Tab")
                except Exception as e:
                    logger.warning(f"更新详细信息Tab失败: {e}")

            # 根据阶段构建合适的进度消息
            if total > 0:
                if stage == 'storyboard':
                    # 分镜设计阶段显示页数
                    progress_msg = f"{stage_label}: {current}/{total} 页"
                elif stage == 'page_prompt_building':
                    # 整页提示词生成阶段显示页数
                    progress_msg = f"{stage_label}: {current}/{total} 页"
                elif stage == 'extracting':
                    # 提取阶段显示步骤数
                    progress_msg = f"{stage_label}: {current}/{total}"
                else:
                    # 其他阶段
                    progress_msg = f"{stage_label}: {current}/{total}"
            elif stage_label:
                progress_msg = f"{stage_label}..."
            elif message:
                progress_msg = message
            else:
                progress_msg = "正在生成漫画分镜..."

            # 更新工具栏加载标签
            if self._manga_builder:
                self._manga_builder.set_toolbar_loading(True, progress_msg)

        def on_error(error):
            self._manga_progress_polling = False
            # 进度查询失败不影响主流程，只记录日志
            logger.warning(f"漫画生成进度查询失败: {error}")

        worker = AsyncWorker(do_poll)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用
        self._manga_progress_worker = worker

    def _onCopyPrompt(self, prompt: str):
        """
        复制提示词到剪贴板

        Args:
            prompt: 要复制的提示词内容
        """
        if not prompt:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(prompt)
        MessageService.show_success(self, "已复制到剪贴板")

    def _onDeleteMangaPrompt(self):
        """删除漫画分镜回调"""
        if not self.project_id or not self.current_chapter:
            return

        if not MessageService.confirm(self, "确定要删除漫画分镜吗?", "此操作不可恢复"):
            return

        def do_delete():
            return self.api_client.delete_manga_prompts(
                self.project_id, self.current_chapter
            )

        def on_success(result):
            MessageService.show_success(self, "漫画分镜已删除")
            # 仅刷新漫画面板数据，避免过度刷新整个章节
            self._loadMangaDataAsync()

        def on_error(error):
            MessageService.show_error(self, f"删除失败: {error}")

        worker = AsyncWorker(do_delete)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        self._manga_delete_worker = worker

    def _onGenerateImage(self, panel: dict):
        """
        生成画格图片回调

        Args:
            panel: 完整的画格数据字典，包含:
                - panel_id: 画格ID (格式: scene{n}_page{n}_panel{n})
                - prompt: 正面提示词
                - negative_prompt: 负面提示词
                - aspect_ratio: 宽高比 (如 "16:9", "4:3", "1:1" 等)
                - reference_image_paths: 参考图片路径列表 (角色立绘等)
                - dialogue: 对话内容
                - dialogue_speaker: 对话说话者
                - dialogue_bubble_type: 气泡类型
                - dialogue_emotion: 说话情绪
                - dialogue_position: 气泡位置
                - narration: 旁白内容
                - narration_position: 旁白位置
                - sound_effects: 音效列表
                - sound_effect_details: 详细音效信息
                - composition: 构图
                - camera_angle: 镜头角度
                - is_key_panel: 是否为关键画格
                - characters: 角色列表
                - lighting: 光线描述
                - atmosphere: 氛围描述
                - key_visual_elements: 关键视觉元素
        """
        if not self.project_id or not self.current_chapter:
            return

        # 从画格数据中提取所有字段
        panel_id = panel.get('panel_id', '')
        prompt = panel.get('prompt', '')
        negative_prompt = panel.get('negative_prompt', '')
        aspect_ratio = panel.get('aspect_ratio', '16:9')
        reference_image_paths = panel.get('reference_image_paths', [])

        # 漫画元数据 - 对话相关
        # Bug 22 修复: 后端返回 dialogues 列表，需要正确处理
        dialogues = panel.get('dialogues', [])
        # 为兼容旧格式，也支持单数形式
        dialogue = ''
        dialogue_speaker = ''
        dialogue_bubble_type = ''
        dialogue_emotion = ''
        dialogue_position = ''
        if dialogues and len(dialogues) > 0:
            # 取第一条对话作为主对话（用于传统单对话接口）
            first_dialogue = dialogues[0]
            if isinstance(first_dialogue, dict):
                dialogue = first_dialogue.get('content', '')
                dialogue_speaker = first_dialogue.get('speaker', '')
                dialogue_bubble_type = first_dialogue.get('bubble_type', '')
                dialogue_emotion = first_dialogue.get('emotion', '')
                dialogue_position = first_dialogue.get('position', '')
        else:
            # 兼容旧的单对话格式
            dialogue = panel.get('dialogue', '')
            dialogue_speaker = panel.get('dialogue_speaker', '')
            dialogue_bubble_type = panel.get('dialogue_bubble_type', '')
            dialogue_emotion = panel.get('dialogue_emotion', '')
            dialogue_position = panel.get('dialogue_position', '')

        # 漫画元数据 - 旁白相关
        narration = panel.get('narration', '')
        narration_position = panel.get('narration_position', '')

        # 漫画元数据 - 音效相关
        # 注意：sound_effects 可能是字符串列表或字典列表
        # API期望 sound_effects 是 List[str]，sound_effect_details 是 List[Dict]
        raw_sound_effects = panel.get('sound_effects', [])
        sound_effect_details = panel.get('sound_effect_details', [])

        # Bug 23 修复: 判断是否需要从raw_sound_effects构建details
        # 只有当 sound_effect_details 原本就为空时，才从raw_sound_effects中提取
        should_build_details = not sound_effect_details

        # 将 sound_effects 转换为纯文本列表
        sound_effects = []
        for sfx in raw_sound_effects:
            if isinstance(sfx, dict):
                # 字典格式：提取text字段
                sfx_text = sfx.get('text', '')
                if sfx_text:
                    sound_effects.append(sfx_text)
                # Bug 23 修复: 每个字典都添加到details（不仅是第一个）
                if should_build_details:
                    sound_effect_details.append(sfx)
            elif isinstance(sfx, str) and sfx:
                sound_effects.append(sfx)

        # 漫画元数据 - 视觉相关
        composition = panel.get('composition', '')
        camera_angle = panel.get('camera_angle', '')
        is_key_panel = panel.get('is_key_panel', False)
        characters = panel.get('characters', [])
        lighting = panel.get('lighting', '')
        atmosphere = panel.get('atmosphere', '')
        key_visual_elements = panel.get('key_visual_elements', [])

        # 语言设置
        dialogue_language = panel.get('dialogue_language', '')

        # 优先使用画格数据中的 scene_id，缺失时再解析 panel_id
        scene_id = panel.get('scene_id')
        if isinstance(scene_id, str) and scene_id.isdigit():
            scene_id = int(scene_id)
        if not isinstance(scene_id, int) or scene_id <= 0:
            try:
                parts = panel_id.split('_')
                scene_id = int(parts[0].replace('scene', ''))
            except (ValueError, IndexError):
                scene_id = 0

        # 显示加载动画
        self._manga_builder.set_panel_loading(panel_id, True, "正在生成图片...")

        # 准备参考图路径
        ref_paths = reference_image_paths if reference_image_paths else []

        # 获取当前章节版本ID（用于版本追踪）
        chapter_version_id = None
        if hasattr(self, 'current_chapter_data') and self.current_chapter_data:
            chapter_version_id = self.current_chapter_data.get('selected_version_id')

        def do_generate():
            return self.api_client.generate_scene_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                scene_id=scene_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                panel_id=panel_id,
                aspect_ratio=aspect_ratio,
                reference_image_paths=ref_paths if ref_paths else None,
                chapter_version_id=chapter_version_id,
                # 漫画元数据 - 对话相关
                dialogue=dialogue if dialogue else None,
                dialogue_speaker=dialogue_speaker if dialogue_speaker else None,
                dialogue_bubble_type=dialogue_bubble_type if dialogue_bubble_type else None,
                dialogue_emotion=dialogue_emotion if dialogue_emotion else None,
                dialogue_position=dialogue_position if dialogue_position else None,
                # 漫画元数据 - 旁白相关
                narration=narration if narration else None,
                narration_position=narration_position if narration_position else None,
                # 漫画元数据 - 音效相关
                sound_effects=sound_effects if sound_effects else None,
                sound_effect_details=sound_effect_details if sound_effect_details else None,
                # 漫画元数据 - 视觉相关
                composition=composition if composition else None,
                camera_angle=camera_angle if camera_angle else None,
                is_key_panel=is_key_panel,
                characters=characters if characters else None,
                lighting=lighting if lighting else None,
                atmosphere=atmosphere if atmosphere else None,
                key_visual_elements=key_visual_elements if key_visual_elements else None,
                # 语言设置
                dialogue_language=dialogue_language if dialogue_language else None,
            )

        def on_success(result):
            if result.get('success', False):
                images = result.get('images', [])
                image_count = len(images) if images else 1
                self._manga_builder.set_panel_success(
                    panel_id,
                    f"已生成 {image_count} 张图片"
                )
                # 刷新漫画面板数据，更新画格卡片的"已生成"状态
                self._loadMangaDataAsync()
            else:
                error_msg = result.get('error_message', '未知错误')
                self._manga_builder.set_panel_error(panel_id, f"失败: {error_msg[:20]}")
                MessageService.show_error(self, f"生成失败: {error_msg}")

        def on_error(error):
            self._manga_builder.set_panel_error(panel_id, "生成失败")
            MessageService.show_error(self, f"图片生成失败: {error}")

        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._image_gen_worker = worker

    def _onGeneratePageImage(self, page_data: dict):
        """
        生成整页漫画图片回调

        让AI直接生成带分格布局的整页漫画，包含对话气泡和音效文字。

        Args:
            page_data: 页面数据字典，包含:
                - page_number: 页码
                - layout_template: 布局模板名（如 "3row_1x2x1"）
                - layout_description: 布局描述
                - full_page_prompt: 整页提示词
                - negative_prompt: 负面提示词
                - aspect_ratio: 页面宽高比（默认 3:4）
                - panel_summaries: 画格简要信息列表
                - reference_image_paths: 参考图路径列表
        """
        if not self.project_id or not self.current_chapter:
            return

        page_number = page_data.get('page_number', 1)
        full_page_prompt = page_data.get('full_page_prompt', '')
        negative_prompt = page_data.get('negative_prompt', '')
        layout_template = page_data.get('layout_template', '')
        layout_description = page_data.get('layout_description', '')
        aspect_ratio = page_data.get('aspect_ratio', '3:4')
        panel_summaries = page_data.get('panel_summaries', [])
        reference_image_paths = page_data.get('reference_image_paths', [])

        if not full_page_prompt:
            MessageService.show_warning(self, "缺少页面级提示词")
            return

        # 显示加载动画
        page_id = f"page{page_number}"
        if self._manga_builder:
            self._manga_builder.set_page_loading(page_number, True, "正在生成整页漫画...")

        # 获取当前章节版本ID
        chapter_version_id = None
        if hasattr(self, 'current_chapter_data') and self.current_chapter_data:
            chapter_version_id = self.current_chapter_data.get('selected_version_id')

        def do_generate():
            return self.api_client.generate_page_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                page_number=page_number,
                full_page_prompt=full_page_prompt,
                negative_prompt=negative_prompt,
                layout_template=layout_template,
                layout_description=layout_description,
                aspect_ratio=aspect_ratio,
                chapter_version_id=chapter_version_id,
                reference_image_paths=reference_image_paths if reference_image_paths else None,
                panel_summaries=panel_summaries,
            )

        def on_success(result):
            if result.get('success', False):
                images = result.get('images', [])
                if self._manga_builder:
                    self._manga_builder.set_page_success(page_number, f"第{page_number}页生成成功")
                MessageService.show_success(self, f"整页漫画生成成功: 第{page_number}页")
                # 刷新漫画面板数据
                self._loadMangaDataAsync()
            else:
                error_msg = result.get('error_message', '未知错误')
                if self._manga_builder:
                    self._manga_builder.set_page_error(page_number, f"失败: {error_msg[:20]}")
                MessageService.show_error(self, f"整页生成失败: {error_msg}")

        def on_error(error):
            if self._manga_builder:
                self._manga_builder.set_page_error(page_number, "生成失败")
            MessageService.show_error(self, f"整页漫画生成失败: {error}")

        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._page_image_gen_worker = worker

    def _loadChapterMangaPDF(self) -> dict:
        """
        加载当前章节的最新漫画PDF信息

        Returns:
            PDF信息字典，包含 success, file_path, file_name, download_url 等
        """
        if not self.project_id or not self.current_chapter:
            return {}

        try:
            result = self.api_client.get_latest_chapter_manga_pdf(
                self.project_id, self.current_chapter
            )
            return result
        except Exception:
            return {}

    def _onGenerateMangaPDF(self):
        """
        生成漫画PDF回调
        """
        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        # 显示加载动画
        if self._manga_builder:
            self._manga_builder.set_pdf_loading(True, "正在生成PDF...")

        # 获取当前章节版本ID（用于过滤特定版本的图片）
        chapter_version_id = None
        if hasattr(self, 'current_chapter_data') and self.current_chapter_data:
            chapter_version_id = self.current_chapter_data.get('selected_version_id')

        def do_generate():
            return self.api_client.generate_chapter_manga_pdf(
                self.project_id,
                self.current_chapter,
                chapter_version_id=chapter_version_id,
            )

        def on_success(result):
            if result.get('success', False):
                page_count = result.get('page_count', 0)
                if self._manga_builder:
                    self._manga_builder.set_pdf_success(f"生成成功 ({page_count}页)")
                MessageService.show_success(self, f"漫画PDF生成成功 ({page_count}页)")
                # 仅刷新漫画面板数据，避免过度刷新整个章节
                self._loadMangaDataAsync()
            else:
                error_msg = result.get('error_message', '未知错误')
                if self._manga_builder:
                    self._manga_builder.set_pdf_error("生成失败")
                MessageService.show_error(self, f"PDF生成失败: {error_msg}")

        def on_error(error):
            if self._manga_builder:
                self._manga_builder.set_pdf_error("生成失败")
            MessageService.show_error(self, f"PDF生成失败: {error}")

        # 开始异步生成
        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._pdf_gen_worker = worker

    def _onDownloadPDF(self, file_name: str):
        """
        下载PDF文件

        Args:
            file_name: PDF文件名
        """
        if not file_name:
            return

        # 获取下载URL
        download_url = self.api_client.get_export_download_url(file_name)

        try:
            # 使用系统默认浏览器打开下载链接
            if platform.system() == 'Windows':
                subprocess.Popen(['start', '', download_url], shell=True)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', download_url])
            else:  # Linux
                subprocess.Popen(['xdg-open', download_url])

            MessageService.show_success(self, "已打开下载链接")
        except Exception as e:
            MessageService.show_error(self, f"下载失败: {e}")

    def _onGenerateAllImages(self):
        """
        一键生成所有图片回调

        根据"整页图片"复选框状态选择生成模式:
        - 勾选: 使用整页提示词生成整页漫画
        - 未勾选: 使用画格提示词逐个生成画格图片
        """
        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        # 检查是否启用整页图片模式
        is_page_mode = False
        if self._manga_builder and self._manga_builder.is_page_image_mode():
            is_page_mode = True

        # 获取当前漫画数据
        manga_data = self._prepareMangaData({'chapter_number': self.current_chapter})

        if is_page_mode:
            # 整页模式：使用 page_prompts 生成整页漫画
            self._onGenerateAllPageImages(manga_data)
        else:
            # 画格模式：使用 panels 逐个生成画格图片
            self._onGenerateAllPanelImages(manga_data)

    def _onGenerateAllPageImages(self, manga_data: dict):
        """
        一键生成所有整页漫画（整页模式）

        Args:
            manga_data: 漫画数据，包含 page_prompts 列表
        """
        page_prompts = manga_data.get('page_prompts', [])

        if not page_prompts:
            MessageService.show_warning(self, "没有整页提示词可以生成图片，请先生成整页提示词")
            return

        # 过滤出有提示词且未生成图片的页面
        pages_to_generate = [
            pp for pp in page_prompts
            if pp.get('full_page_prompt') and not pp.get('has_image', False)
        ]

        if not pages_to_generate:
            MessageService.show_info(self, "所有页面都已生成图片")
            return

        total = len(pages_to_generate)
        skipped = len(page_prompts) - total
        if skipped > 0:
            logger.info(f"开始一键生成整页图片: 共 {total} 页待生成, 跳过 {skipped} 页已完成")
        else:
            logger.info(f"开始一键生成整页图片: 共 {total} 页")

        # 获取并发配置
        try:
            queue_config = self.api_client.get_queue_config()
            max_concurrent = queue_config.get('image_max_concurrent', 1)
        except Exception as e:
            logger.warning(f"获取队列配置失败，使用默认并发数1: {e}")
            max_concurrent = 1

        logger.info(f"整页图片生成并发数: {max_concurrent}")

        # 显示加载状态
        if self._manga_builder:
            self._manga_builder.set_generate_all_loading(True, 0, total)

        # 初始化批量生成状态（使用不同的状态变量以区分两种模式）
        self._batch_page_generate_queue = list(pages_to_generate)
        self._batch_page_generate_total = total
        self._batch_page_generate_current = 0
        self._batch_page_generate_success = 0
        self._batch_page_generate_failed = 0
        self._batch_page_generate_max_concurrent = max_concurrent
        self._batch_page_generate_active = 0
        self._batch_page_image_workers = []
        self._batch_page_generate_stopped = False

        # 启动初始并发任务
        initial_count = min(max_concurrent, len(self._batch_page_generate_queue))
        logger.info(f"启动 {initial_count} 个并发整页生成任务")
        for i in range(initial_count):
            self._processNextBatchPageImage()

    def _processNextBatchPageImage(self):
        """处理批量整页生成队列中的下一页"""
        # 检查是否已停止
        if getattr(self, '_batch_page_generate_stopped', False):
            if self._batch_page_generate_active == 0:
                self._onBatchPageGenerateComplete()
            return

        # 检查是否还有任务需要处理
        if not hasattr(self, '_batch_page_generate_queue') or not self._batch_page_generate_queue:
            if self._batch_page_generate_active == 0:
                self._onBatchPageGenerateComplete()
            return

        # 取出下一页
        page_prompt = self._batch_page_generate_queue.pop(0)
        self._batch_page_generate_current += 1
        self._batch_page_generate_active += 1

        # 提取页面数据
        page_number = page_prompt.get('page_number', 1)
        full_page_prompt = page_prompt.get('full_page_prompt', '')
        negative_prompt = page_prompt.get('negative_prompt', '')
        layout_template = page_prompt.get('layout_template', '')
        layout_description = page_prompt.get('layout_description', '')
        aspect_ratio = page_prompt.get('aspect_ratio', '3:4')
        panel_summaries = page_prompt.get('panel_summaries', [])
        reference_image_paths = page_prompt.get('reference_image_paths', [])

        # 更新进度
        if self._manga_builder:
            self._manga_builder.update_generate_all_progress(
                self._batch_page_generate_current,
                self._batch_page_generate_total
            )

        logger.info(f"批量生成整页图片 {self._batch_page_generate_current}/{self._batch_page_generate_total}: 第{page_number}页 (活跃: {self._batch_page_generate_active})")

        # 获取当前章节版本ID
        chapter_version_id = None
        if hasattr(self, 'current_chapter_data') and self.current_chapter_data:
            chapter_version_id = self.current_chapter_data.get('selected_version_id')

        def do_generate():
            return self.api_client.generate_page_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                page_number=page_number,
                full_page_prompt=full_page_prompt,
                negative_prompt=negative_prompt,
                layout_template=layout_template,
                layout_description=layout_description,
                aspect_ratio=aspect_ratio,
                chapter_version_id=chapter_version_id,
                reference_image_paths=reference_image_paths if reference_image_paths else None,
                panel_summaries=panel_summaries,
            )

        def on_success(result):
            self._batch_page_generate_active -= 1
            if result.get('success', False):
                self._batch_page_generate_success += 1
            else:
                self._batch_page_generate_failed += 1
                error_msg = result.get('error_message', '未知错误')
                logger.warning(f"第{page_number}页生成失败: {error_msg}")

            # 继续处理下一个
            self._processNextBatchPageImage()

        def on_error(error):
            self._batch_page_generate_active -= 1
            self._batch_page_generate_failed += 1
            logger.warning(f"第{page_number}页生成失败: {error}")

            # 继续处理下一个
            self._processNextBatchPageImage()

        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用
        self._batch_page_image_workers.append(worker)

    def _onBatchPageGenerateComplete(self):
        """批量整页生成完成回调"""
        success_count = getattr(self, '_batch_page_generate_success', 0)
        failed_count = getattr(self, '_batch_page_generate_failed', 0)
        total = getattr(self, '_batch_page_generate_total', 0)
        was_stopped = getattr(self, '_batch_page_generate_stopped', False)

        logger.info(f"批量整页生成完成: 成功 {success_count}, 失败 {failed_count}, 总计 {total}, 停止={was_stopped}")

        if self._manga_builder:
            if was_stopped:
                self._manga_builder.set_generate_all_error(f"已停止 ({success_count}页成功)")
                if success_count > 0:
                    MessageService.show_info(self, f"批量整页生成已停止: 成功 {success_count} 页")
            elif failed_count == 0:
                self._manga_builder.set_generate_all_success(f"完成 {success_count} 页")
                MessageService.show_success(self, f"成功生成 {success_count} 页整页漫画")
            elif success_count == 0:
                self._manga_builder.set_generate_all_error(f"全部失败 ({failed_count})")
                MessageService.show_error(self, f"整页漫画生成失败")
            else:
                self._manga_builder.set_generate_all_success(f"完成 {success_count}/{total}")
                MessageService.show_warning(self, f"整页生成完成: 成功 {success_count}, 失败 {failed_count}")

        # 刷新漫画面板数据
        self._loadMangaDataAsync()

        # 清理状态
        self._batch_page_generate_queue = []
        self._batch_page_generate_total = 0
        self._batch_page_generate_current = 0
        self._batch_page_generate_success = 0
        self._batch_page_generate_failed = 0
        self._batch_page_generate_max_concurrent = 1
        self._batch_page_generate_active = 0
        self._batch_page_image_workers = []

    def _onGenerateAllPanelImages(self, manga_data: dict):
        """
        一键生成所有画格图片（画格模式）

        Args:
            manga_data: 漫画数据，包含 panels 列表
        """
        panels = manga_data.get('panels', [])

        if not panels:
            MessageService.show_warning(self, "没有画格可以生成图片")
            return

        # 过滤出未生成图片的画格
        panels_to_generate = [
            p for p in panels
            if not p.get('has_image', False) and p.get('prompt')
        ]

        if not panels_to_generate:
            MessageService.show_info(self, "所有画格都已生成图片")
            return

        total = len(panels_to_generate)
        logger.info(f"开始一键生成图片: 共 {total} 个画格")

        # 获取并发配置
        try:
            queue_config = self.api_client.get_queue_config()
            max_concurrent = queue_config.get('image_max_concurrent', 1)
        except Exception as e:
            logger.warning(f"获取队列配置失败，使用默认并发数1: {e}")
            max_concurrent = 1

        logger.info(f"图片生成并发数: {max_concurrent}")

        # 显示加载状态
        if self._manga_builder:
            self._manga_builder.set_generate_all_loading(True, 0, total)

        # 初始化批量生成状态
        self._batch_generate_queue = list(panels_to_generate)
        self._batch_generate_total = total
        self._batch_generate_current = 0
        self._batch_generate_success = 0
        self._batch_generate_failed = 0
        self._batch_generate_max_concurrent = max_concurrent
        self._batch_generate_active = 0  # 当前活跃的任务数
        self._batch_image_workers = []   # 保存所有活跃的worker引用
        self._batch_generate_stopped = False  # 停止标志

        # 启动初始并发任务
        initial_count = min(max_concurrent, len(self._batch_generate_queue))
        logger.info(f"启动 {initial_count} 个并发任务")
        for i in range(initial_count):
            logger.info(f"启动第 {i + 1} 个初始任务")
            self._processNextBatchImage()

    def _onStopGenerateAllImages(self):
        """停止批量生成图片回调（支持画格模式和整页模式）"""
        # 检查是否有整页模式的任务正在进行
        has_page_tasks = (
            hasattr(self, '_batch_page_generate_queue') and self._batch_page_generate_queue
        ) or getattr(self, '_batch_page_generate_active', 0) > 0

        # 检查是否有画格模式的任务正在进行
        has_panel_tasks = (
            hasattr(self, '_batch_generate_queue') and self._batch_generate_queue
        ) or getattr(self, '_batch_generate_active', 0) > 0

        if not has_page_tasks and not has_panel_tasks:
            logger.warning("没有正在进行的批量图片生成任务")
            return

        logger.info("用户请求停止批量图片生成")

        # 处理整页模式停止
        if has_page_tasks:
            self._batch_page_generate_stopped = True
            remaining_pages = len(getattr(self, '_batch_page_generate_queue', []))
            self._batch_page_generate_queue = []
            active_pages = getattr(self, '_batch_page_generate_active', 0)

            if self._manga_builder:
                if active_pages > 0:
                    self._manga_builder.set_generate_all_error(f"正在停止...({active_pages}页执行中)")
                else:
                    self._manga_builder.set_generate_all_error("已停止")

            MessageService.show_info(
                self,
                f"已停止批量整页生成，跳过 {remaining_pages} 页，{active_pages} 页正在完成中"
            )
            return

        # 处理画格模式停止（原有逻辑）
        self._batch_generate_stopped = True
        remaining = len(getattr(self, '_batch_generate_queue', []))
        self._batch_generate_queue = []
        active = getattr(self, '_batch_generate_active', 0)

        if self._manga_builder:
            if active > 0:
                self._manga_builder.set_generate_all_error(f"正在停止...({active}个任务执行中)")
            else:
                self._manga_builder.set_generate_all_error("已停止")

        MessageService.show_info(
            self,
            f"已停止批量生成，跳过 {remaining} 个画格，{active} 个任务正在完成中"
        )

    def _processNextBatchImage(self):
        """处理批量生成队列中的下一个画格（支持并发）"""
        # 检查是否已停止
        if getattr(self, '_batch_generate_stopped', False):
            # 如果所有活跃任务都完成了，触发完成回调
            if self._batch_generate_active == 0:
                self._onBatchGenerateComplete()
            return

        # 检查是否还有任务需要处理
        if not hasattr(self, '_batch_generate_queue') or not self._batch_generate_queue:
            # 队列为空，检查是否所有任务都完成了
            if self._batch_generate_active == 0:
                self._onBatchGenerateComplete()
            return

        # 取出下一个画格
        panel = self._batch_generate_queue.pop(0)
        self._batch_generate_current += 1
        self._batch_generate_active += 1

        # 提取画格数据 - 基础字段
        panel_id = panel.get('panel_id', '')
        prompt = panel.get('prompt', '')
        negative_prompt = panel.get('negative_prompt', '')
        panel_aspect_ratio = panel.get('aspect_ratio', '16:9')
        ref_paths = panel.get('reference_image_paths', [])

        # 漫画元数据 - 对话相关
        dialogue = panel.get('dialogue', '')
        dialogue_speaker = panel.get('dialogue_speaker', '')
        dialogue_bubble_type = panel.get('dialogue_bubble_type', '')
        dialogue_emotion = panel.get('dialogue_emotion', '')
        dialogue_position = panel.get('dialogue_position', '')

        # 漫画元数据 - 旁白相关
        narration = panel.get('narration', '')
        narration_position = panel.get('narration_position', '')

        # 漫画元数据 - 音效相关
        # 注意：sound_effects 可能是字符串列表或字典列表
        # API期望 sound_effects 是 List[str]，sound_effect_details 是 List[Dict]
        raw_sound_effects = panel.get('sound_effects', [])
        sound_effect_details = panel.get('sound_effect_details', [])

        # Bug 23 修复: 判断是否需要从raw_sound_effects构建details
        # 只有当 sound_effect_details 原本就为空时，才从raw_sound_effects中提取
        should_build_details = not sound_effect_details

        # 将 sound_effects 转换为纯文本列表
        sound_effects = []
        for sfx in raw_sound_effects:
            if isinstance(sfx, dict):
                # 字典格式：提取text字段
                sfx_text = sfx.get('text', '')
                if sfx_text:
                    sound_effects.append(sfx_text)
                # Bug 23 修复: 每个字典都添加到details（不仅是第一个）
                if should_build_details:
                    sound_effect_details.append(sfx)
            elif isinstance(sfx, str) and sfx:
                sound_effects.append(sfx)

        # 漫画元数据 - 视觉相关
        composition = panel.get('composition', '')
        camera_angle = panel.get('camera_angle', '')
        is_key_panel = panel.get('is_key_panel', False)
        characters = panel.get('characters', [])
        lighting = panel.get('lighting', '')
        atmosphere = panel.get('atmosphere', '')
        key_visual_elements = panel.get('key_visual_elements', [])

        # 语言设置
        dialogue_language = panel.get('dialogue_language', '')

        scene_id = panel.get('scene_id')
        if isinstance(scene_id, str) and scene_id.isdigit():
            scene_id = int(scene_id)
        if not isinstance(scene_id, int) or scene_id <= 0:
            try:
                parts = panel_id.split('_')
                scene_id = int(parts[0].replace('scene', ''))
            except (ValueError, IndexError):
                scene_id = 0

        # 更新进度（显示已启动的任务数）
        if self._manga_builder:
            self._manga_builder.update_generate_all_progress(
                self._batch_generate_current,
                self._batch_generate_total
            )

        logger.info(f"批量生成图片 {self._batch_generate_current}/{self._batch_generate_total}: {panel_id} (活跃: {self._batch_generate_active})")

        # 获取当前章节版本ID（用于版本追踪）
        chapter_version_id = None
        if hasattr(self, 'current_chapter_data') and self.current_chapter_data:
            chapter_version_id = self.current_chapter_data.get('selected_version_id')

        def do_generate():
            return self.api_client.generate_scene_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                scene_id=scene_id,
                prompt=prompt,
                negative_prompt=negative_prompt,
                panel_id=panel_id,
                aspect_ratio=panel_aspect_ratio,
                reference_image_paths=ref_paths if ref_paths else None,
                chapter_version_id=chapter_version_id,
                # 漫画元数据 - 对话相关
                dialogue=dialogue if dialogue else None,
                dialogue_speaker=dialogue_speaker if dialogue_speaker else None,
                dialogue_bubble_type=dialogue_bubble_type if dialogue_bubble_type else None,
                dialogue_emotion=dialogue_emotion if dialogue_emotion else None,
                dialogue_position=dialogue_position if dialogue_position else None,
                # 漫画元数据 - 旁白相关
                narration=narration if narration else None,
                narration_position=narration_position if narration_position else None,
                # 漫画元数据 - 音效相关
                sound_effects=sound_effects if sound_effects else None,
                sound_effect_details=sound_effect_details if sound_effect_details else None,
                # 漫画元数据 - 视觉相关
                composition=composition if composition else None,
                camera_angle=camera_angle if camera_angle else None,
                is_key_panel=is_key_panel,
                characters=characters if characters else None,
                lighting=lighting if lighting else None,
                atmosphere=atmosphere if atmosphere else None,
                key_visual_elements=key_visual_elements if key_visual_elements else None,
                # 语言设置
                dialogue_language=dialogue_language if dialogue_language else None,
            )

        def on_success(result):
            self._batch_generate_active -= 1
            if result.get('success', False):
                self._batch_generate_success += 1
            else:
                self._batch_generate_failed += 1
                error_msg = result.get('error_message', '未知错误')
                logger.warning(f"画格 {panel_id} 生成失败: {error_msg}")

            # 继续处理下一个（保持并发）
            self._processNextBatchImage()

        def on_error(error):
            self._batch_generate_active -= 1
            self._batch_generate_failed += 1
            logger.warning(f"画格 {panel_id} 生成失败: {error}")

            # 继续处理下一个（保持并发）
            self._processNextBatchImage()

        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._batch_image_workers.append(worker)

    def _onBatchGenerateComplete(self):
        """批量生成完成回调"""
        success_count = getattr(self, '_batch_generate_success', 0)
        failed_count = getattr(self, '_batch_generate_failed', 0)
        total = getattr(self, '_batch_generate_total', 0)
        was_stopped = getattr(self, '_batch_generate_stopped', False)

        logger.info(f"批量生成完成: 成功 {success_count}, 失败 {failed_count}, 总计 {total}, 停止={was_stopped}")

        if self._manga_builder:
            if was_stopped:
                # 被用户停止
                self._manga_builder.set_generate_all_error(f"已停止 ({success_count}成功)")
                if success_count > 0:
                    MessageService.show_info(self, f"批量生成已停止: 成功 {success_count} 张")
            elif failed_count == 0:
                self._manga_builder.set_generate_all_success(f"完成 {success_count} 张")
                MessageService.show_success(self, f"成功生成 {success_count} 张图片")
            elif success_count == 0:
                self._manga_builder.set_generate_all_error(f"全部失败 ({failed_count})")
                MessageService.show_error(self, f"图片生成失败")
            else:
                self._manga_builder.set_generate_all_success(f"完成 {success_count}/{total}")
                MessageService.show_warning(self, f"生成完成: 成功 {success_count}, 失败 {failed_count}")

        # 刷新漫画面板数据
        self._loadMangaDataAsync()

        # 清理状态
        self._batch_generate_queue = []
        self._batch_generate_total = 0
        self._batch_generate_current = 0
        self._batch_generate_success = 0
        self._batch_generate_failed = 0
        self._batch_generate_max_concurrent = 1
        self._batch_generate_active = 0
        self._batch_image_workers = []

    def _onPreviewPrompt(self, panel: dict):
        """
        预览实际发送给生图模型的提示词

        Args:
            panel: 完整的画格数据字典，包含:
                - prompt: 原始提示词
                - negative_prompt: 负面提示词
                - aspect_ratio: 宽高比
                - dialogue: 对话内容
                - dialogue_speaker: 对话说话者
                - dialogue_bubble_type: 气泡类型
                - dialogue_emotion: 说话情绪
                - dialogue_position: 气泡位置
                - narration: 旁白内容
                - narration_position: 旁白位置
                - sound_effects: 音效列表
                - sound_effect_details: 详细音效信息
                - composition: 构图
                - camera_angle: 镜头角度
                - is_key_panel: 是否为关键画格
                - characters: 角色列表
                - lighting: 光线描述
                - atmosphere: 氛围描述
                - key_visual_elements: 关键视觉元素
                - is_page_prompt: 是否为整页提示词（可选）
                - prompt_cn: 中文提示词（可选，用于整页提示词）
        """
        prompt = panel.get('prompt', '')
        if not prompt:
            MessageService.show_warning(self, "没有可预览的提示词")
            return

        # 整页提示词特殊处理：直接显示本地数据
        if panel.get('is_page_prompt'):
            negative = panel.get('negative_prompt', '')
            # 获取当前风格设置
            current_style = ''
            if self._manga_builder:
                settings = self._manga_builder.get_current_settings()
                current_style = settings.get('style', '')
            # 构建与实际生成一致的完整提示词（风格追加到末尾）
            final = prompt
            if current_style:
                final = f"{prompt}, {current_style}"
            if negative:
                final = f"{final}\n\n负面提示词: {negative}"
            preview_data = {
                'success': True,
                'original_prompt': prompt,
                'final_prompt': final,
                'negative_prompt': negative,
                'provider': '整页生成',
                'model': '-',
                'style': current_style if current_style else '-',
                'ratio': panel.get('aspect_ratio', '3:4'),
                'scene_type': 'page_layout',
                'scene_type_zh': '整页布局',
                'is_page_prompt': True,
            }
            from windows.writing_desk.panels.manga.prompt_preview_dialog import PromptPreviewDialog
            dialog = PromptPreviewDialog(preview_data, self)
            dialog.exec()
            return

        # 提取基础字段
        negative_prompt = panel.get('negative_prompt', '')
        aspect_ratio = panel.get('aspect_ratio', '16:9')

        # 漫画元数据 - 对话相关
        dialogue = panel.get('dialogue', '')
        dialogue_speaker = panel.get('dialogue_speaker', '')
        dialogue_bubble_type = panel.get('dialogue_bubble_type', '')
        dialogue_emotion = panel.get('dialogue_emotion', '')
        dialogue_position = panel.get('dialogue_position', '')

        # 漫画元数据 - 旁白相关
        narration = panel.get('narration', '')
        narration_position = panel.get('narration_position', '')

        # 漫画元数据 - 音效相关
        # 注意：sound_effects 可能是字符串列表或字典列表
        # API期望 sound_effects 是 List[str]，sound_effect_details 是 List[Dict]
        raw_sound_effects = panel.get('sound_effects', [])
        sound_effect_details = panel.get('sound_effect_details', [])

        # Bug 23 修复: 判断是否需要从raw_sound_effects构建details
        # 只有当 sound_effect_details 原本就为空时，才从raw_sound_effects中提取
        should_build_details = not sound_effect_details

        # 将 sound_effects 转换为纯文本列表
        sound_effects = []
        for sfx in raw_sound_effects:
            if isinstance(sfx, dict):
                # 字典格式：提取text字段
                sfx_text = sfx.get('text', '')
                if sfx_text:
                    sound_effects.append(sfx_text)
                # Bug 23 修复: 每个字典都添加到details（不仅是第一个）
                if should_build_details:
                    sound_effect_details.append(sfx)
            elif isinstance(sfx, str) and sfx:
                sound_effects.append(sfx)

        # 漫画元数据 - 视觉相关
        composition = panel.get('composition', '')
        camera_angle = panel.get('camera_angle', '')
        is_key_panel = panel.get('is_key_panel', False)
        characters = panel.get('characters', [])
        lighting = panel.get('lighting', '')
        atmosphere = panel.get('atmosphere', '')
        key_visual_elements = panel.get('key_visual_elements', [])

        # 语言设置
        dialogue_language = panel.get('dialogue_language', '')

        # 获取当前风格设置
        current_style = ''
        if self._manga_builder:
            settings = self._manga_builder.get_current_settings()
            current_style = settings.get('style', '')

        def do_preview():
            return self.api_client.preview_image_prompt(
                prompt=prompt,
                negative_prompt=negative_prompt,
                style=current_style if current_style else None,
                ratio=aspect_ratio,
                # 漫画元数据 - 对话相关
                dialogue=dialogue if dialogue else None,
                dialogue_speaker=dialogue_speaker if dialogue_speaker else None,
                dialogue_bubble_type=dialogue_bubble_type if dialogue_bubble_type else None,
                dialogue_emotion=dialogue_emotion if dialogue_emotion else None,
                dialogue_position=dialogue_position if dialogue_position else None,
                # 漫画元数据 - 旁白相关
                narration=narration if narration else None,
                narration_position=narration_position if narration_position else None,
                # 漫画元数据 - 音效相关
                sound_effects=sound_effects if sound_effects else None,
                sound_effect_details=sound_effect_details if sound_effect_details else None,
                # 漫画元数据 - 视觉相关
                composition=composition if composition else None,
                camera_angle=camera_angle if camera_angle else None,
                is_key_panel=is_key_panel,
                characters=characters if characters else None,
                lighting=lighting if lighting else None,
                atmosphere=atmosphere if atmosphere else None,
                key_visual_elements=key_visual_elements if key_visual_elements else None,
                # 语言设置
                dialogue_language=dialogue_language if dialogue_language else None,
            )

        def on_success(result):
            # 导入并显示预览对话框
            from windows.writing_desk.panels.manga.prompt_preview_dialog import PromptPreviewDialog
            dialog = PromptPreviewDialog(result, self)
            dialog.exec()

        def on_error(error):
            # 即使API调用失败，也显示原始提示词
            fallback_data = {
                'success': False,
                'error': str(error),
            }
            from windows.writing_desk.panels.manga.prompt_preview_dialog import PromptPreviewDialog
            dialog = PromptPreviewDialog(fallback_data, self)
            dialog.exec()

        worker = AsyncWorker(do_preview)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._preview_worker = worker
