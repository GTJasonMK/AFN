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
            'character_profiles': {},
            'total_pages': 0,
            'total_panels': 0,
            'style': '',
            'images': [],            # 已生成的图片列表
            'pdf_info': {},          # PDF信息
            # 断点续传信息
            'can_resume': False,
            'resume_progress': None,
        }

        # 尝试从API获取已保存的漫画分镜
        if self.project_id and self.current_chapter:
            try:
                result = self.api_client.get_manga_prompts(
                    self.project_id, self.current_chapter
                )
                if result:
                    manga_data['has_manga_prompt'] = True
                    manga_data['scenes'] = result.get('scenes', [])
                    manga_data['panels'] = result.get('panels', [])
                    manga_data['character_profiles'] = result.get('character_profiles', {})
                    manga_data['total_pages'] = result.get('total_pages', 0)
                    manga_data['total_panels'] = result.get('total_panels', 0)
                    manga_data['style'] = result.get('style', '')
            except Exception:
                # 如果获取失败，保持默认空状态
                pass

            # 检查断点状态（仅当没有完成的内容时）
            if not manga_data['has_manga_prompt']:
                try:
                    progress = self.api_client.get_manga_prompt_progress(
                        self.project_id, self.current_chapter
                    )
                    if progress and progress.get('can_resume', False):
                        manga_data['can_resume'] = True
                        manga_data['resume_progress'] = progress
                except Exception:
                    pass

            # 获取已生成的图片列表
            try:
                images = self._loadChapterImages()
                manga_data['images'] = images

                # 按 panel_id 精确匹配图片
                # 只有精确匹配 panel_id 的画格才显示"已生成"状态
                # 旧图片（没有panel_id）不会显示在任何画格上，需要重新生成
                panel_image_map = {}  # panel_id -> [images]

                for img in images:
                    panel_id = img.get('panel_id')
                    if panel_id:
                        # 有 panel_id，精确匹配
                        if panel_id not in panel_image_map:
                            panel_image_map[panel_id] = []
                        panel_image_map[panel_id].append(img)

                # 更新画格数据，标记已生成图片的画格（仅精确匹配）
                for panel in manga_data['panels']:
                    panel_id = panel.get('panel_id', '')

                    if panel_id in panel_image_map:
                        panel['has_image'] = True
                        panel['image_path'] = panel_image_map[panel_id][-1].get('local_path', '')
                        panel['image_count'] = len(panel_image_map[panel_id])
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

        # 如果正在生成漫画提示词，跳过加载避免破坏加载状态显示
        if getattr(self, '_manga_generating', False):
            logger.info("Skipping manga data load - generation in progress")
            return

        # 保存当前章节号，用于验证回调时章节未切换
        loading_chapter = self.current_chapter

        def do_load():
            """在后台线程执行的加载函数"""
            return self._prepareMangaData({'chapter_number': loading_chapter})

        def on_success(manga_data):
            """加载成功回调"""
            # 检查章节是否已切换，避免更新错误的Tab
            if self.current_chapter != loading_chapter:
                return

            # 如果正在生成，跳过更新
            if getattr(self, '_manga_generating', False):
                logger.info("Skipping manga tab update - generation in progress")
                return

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

                # 恢复之前选中的Tab索引
                # 注意：移除和插入Tab后，QTabWidget可能自动切换了Tab
                # 需要确保恢复到用户之前查看的Tab
                self.tab_widget.setCurrentIndex(current_tab_index)

        def on_error(error):
            """加载失败回调 - 静默处理，保持空状态"""
            pass

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

            # 转换图片路径为本地绝对路径
            for img in images:
                file_path = img.get('file_path', '')
                if file_path:
                    # 构建完整的本地路径
                    # 图片存储在 backend/storage/generated_images/{project_id}/chapter_{n}/
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    local_path = os.path.join(base_dir, 'backend', 'storage', 'generated_images', file_path)
                    img['local_path'] = local_path

            return images
        except Exception:
            return []

    def _onGenerateMangaPrompt(self, style: str = "manga", min_scenes: int = 5, max_scenes: int = 15, language: str = "chinese", use_portraits: bool = True):
        """
        生成漫画分镜回调

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            min_scenes: 最少场景数 (3-10)
            max_scenes: 最多场景数 (5-25)
            language: 对话/音效语言 (chinese/japanese/english/korean)
            use_portraits: 是否使用角色立绘作为参考图（img2img）
        """
        logger.info(f"_onGenerateMangaPrompt called: style={style}, min_scenes={min_scenes}, max_scenes={max_scenes}, language={language}, use_portraits={use_portraits}")

        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        # 防止重复点击：如果正在生成中，忽略请求
        if getattr(self, '_manga_generating', False):
            logger.warning("漫画分镜正在生成中，忽略重复请求")
            MessageService.show_info(self, "正在生成中，请稍候...")
            return

        # 检查是否已有完成的分镜数据
        try:
            existing = self.api_client.get_manga_prompts(
                self.project_id, self.current_chapter
            )
            if existing and existing.get('total_panels', 0) > 0:
                # 已有分镜数据，询问用户
                if not MessageService.confirm(
                    self,
                    "当前章节已有分镜数据，重新生成将覆盖现有数据。",
                    "确定要重新生成吗？"
                ):
                    return
        except Exception:
            # 获取失败，检查是否有未完成的断点
            try:
                progress = self.api_client.get_manga_prompt_progress(
                    self.project_id, self.current_chapter
                )
                if progress and progress.get('can_resume', False):
                    stage_label = progress.get('stage_label', '处理中')
                    current = progress.get('current', 0)
                    total = progress.get('total', 0)
                    progress_text = f"({current}/{total})" if total > 0 else ""

                    # 有未完成的断点，询问用户
                    MessageService.show_info(
                        self,
                        f"检测到上次未完成的生成任务（{stage_label} {progress_text}），将自动继续..."
                    )
            except Exception:
                pass

        # 设置生成标志，防止异步加载覆盖UI状态
        self._manga_generating = True

        # 显示加载动画
        loading_text = "正在生成漫画分镜..."
        logger.info(f"Setting loading state, _manga_builder exists: {self._manga_builder is not None}")
        if self._manga_builder:
            self._manga_builder.set_toolbar_loading(True, loading_text)

        def do_generate():
            return self.api_client.generate_manga_prompts(
                self.project_id,
                self.current_chapter,
                style=style,
                min_scenes=min_scenes,
                max_scenes=max_scenes,
                language=language,
                use_portraits=use_portraits,
            )

        def on_success(result):
            # 清除生成标志
            self._manga_generating = False
            # 显示成功状态
            total_pages = result.get('total_pages', 0)
            total_panels = result.get('total_panels', 0)
            if self._manga_builder:
                self._manga_builder.set_toolbar_success(f"生成成功: {total_pages}页 {total_panels}格")
            MessageService.show_success(self, f"漫画分镜生成成功: {total_pages}页, {total_panels}格")
            # 仅刷新漫画面板数据，避免过度刷新整个章节
            self._loadMangaDataAsync()

        def on_error(error):
            # 清除生成标志
            self._manga_generating = False
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

    def _onGenerateImage(self, panel_id: str, prompt: str, negative_prompt: str, aspect_ratio: str = "16:9", reference_image_paths: list = None):
        """
        生成画格图片回调

        Args:
            panel_id: 画格ID (格式: scene{n}_page{n}_panel{n})
            prompt: 正面提示词
            negative_prompt: 负面提示词
            aspect_ratio: 宽高比 (如 "16:9", "4:3", "1:1" 等)
            reference_image_paths: 参考图片路径列表 (角色立绘等)
        """
        if not self.project_id or not self.current_chapter:
            return

        # 从panel_id解析scene_id
        # 格式: scene{scene_id}_page{page}_panel{slot_id}
        try:
            parts = panel_id.split('_')
            scene_id = int(parts[0].replace('scene', ''))
        except (ValueError, IndexError):
            scene_id = 0

        # 显示加载动画
        self._manga_builder.set_panel_loading(panel_id, True, "正在生成图片...")

        # 准备参考图路径
        ref_paths = reference_image_paths if reference_image_paths else []

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

        def do_generate():
            return self.api_client.generate_chapter_manga_pdf(
                self.project_id,
                self.current_chapter,
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

        使用并发方式生成所有未生成图片的画格，并发数量由队列配置决定。
        """
        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        # 获取当前漫画数据
        manga_data = self._prepareMangaData({'chapter_number': self.current_chapter})
        panels = manga_data.get('panels', [])

        if not panels:
            MessageService.show_warning(self, "没有画格可以生成图片")
            return

        # 过滤出未生成图片的画格
        panels_to_generate = [
            p for p in panels
            if not p.get('has_image', False) and p.get('prompt_en')
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

        # 启动初始并发任务
        initial_count = min(max_concurrent, len(self._batch_generate_queue))
        logger.info(f"启动 {initial_count} 个并发任务")
        for i in range(initial_count):
            logger.info(f"启动第 {i + 1} 个初始任务")
            self._processNextBatchImage()

    def _processNextBatchImage(self):
        """处理批量生成队列中的下一个画格（支持并发）"""
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

        panel_id = panel.get('panel_id', '')
        prompt_en = panel.get('prompt_en', '')
        negative_prompt = panel.get('negative_prompt', '')
        panel_aspect_ratio = panel.get('aspect_ratio', '16:9')
        ref_paths = panel.get('reference_image_paths', [])

        # 从panel_id解析scene_id
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

        def do_generate():
            return self.api_client.generate_scene_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                scene_id=scene_id,
                prompt=prompt_en,
                negative_prompt=negative_prompt,
                panel_id=panel_id,
                aspect_ratio=panel_aspect_ratio,
                reference_image_paths=ref_paths if ref_paths else None,
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

        logger.info(f"批量生成完成: 成功 {success_count}, 失败 {failed_count}, 总计 {total}")

        if self._manga_builder:
            if failed_count == 0:
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
