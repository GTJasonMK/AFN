"""
写作台主工作区 - 漫画处理 Mixin

包含漫画提示词生成、图片生成、PDF导出等功能的回调处理。
"""

import os
import subprocess
import platform

from PyQt6.QtWidgets import QApplication

from utils.async_worker import AsyncWorker
from utils.message_service import MessageService


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
            'scenes': [],
            'character_profiles': {},
            'style_guide': '',
            'images': [],  # 已生成的图片列表
            'pdf_info': {},  # PDF信息
        }

        # 尝试从API获取已保存的漫画提示词
        if self.project_id and self.current_chapter:
            try:
                result = self.api_client.get_manga_prompts(
                    self.project_id, self.current_chapter
                )
                if result:
                    manga_data['has_manga_prompt'] = True
                    manga_data['scenes'] = result.get('scenes', [])
                    manga_data['character_profiles'] = result.get('character_profiles', {})
                    manga_data['style_guide'] = result.get('style_guide', '')
            except Exception:
                # 如果获取失败，保持默认空状态
                pass

            # 获取已生成的图片列表
            try:
                images = self._loadChapterImages()
                manga_data['images'] = images

                # 统计每个场景的已生成图片数量
                scene_image_counts = {}
                for img in images:
                    scene_id = img.get('scene_id', 0)
                    scene_image_counts[scene_id] = scene_image_counts.get(scene_id, 0) + 1

                # 更新场景数据，添加已生成图片数量
                for scene in manga_data['scenes']:
                    scene_id = scene.get('scene_id', 0)
                    scene['generated_count'] = scene_image_counts.get(scene_id, 0)
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

        def do_load():
            """在后台线程执行的加载函数"""
            return self._prepareMangaData({'chapter_number': loading_chapter})

        def on_success(manga_data):
            """加载成功回调"""
            # 检查章节是否已切换，避免更新错误的Tab
            if self.current_chapter != loading_chapter:
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
            图片列表，每个图片包含 file_path, scene_id, prompt 等信息
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
                    # 图片存储在 backend/storage/generated_images/{project_id}/chapter_{n}/scene_{n}/
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    local_path = os.path.join(base_dir, 'backend', 'storage', 'generated_images', file_path)
                    img['local_path'] = local_path

            return images
        except Exception:
            return []

    def _onGenerateMangaPrompt(self, style: str, scene_count: int, dialogue_language: str = "chinese", continue_from_checkpoint: bool = False):
        """
        生成漫画提示词回调

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            scene_count: 场景数量
            dialogue_language: 对话语言 (chinese/japanese/english/korean/none)
            continue_from_checkpoint: 是否从检查点继续生成
        """
        if not self.project_id or not self.current_chapter:
            MessageService.show_warning(self, "请先选择章节")
            return

        # 显示加载动画
        loading_text = "正在继续生成..." if continue_from_checkpoint else "正在生成提示词..."
        if self._manga_builder:
            self._manga_builder.set_toolbar_loading(True, loading_text)

        def do_generate():
            return self.api_client.generate_manga_prompts(
                self.project_id,
                self.current_chapter,
                style=style,
                scene_count=scene_count,
                dialogue_language=dialogue_language,
                continue_from_checkpoint=continue_from_checkpoint,
            )

        def on_success(result):
            # 显示成功状态
            if self._manga_builder:
                self._manga_builder.set_toolbar_success("生成成功")
            MessageService.show_success(self, "漫画提示词生成成功")
            # 仅刷新漫画面板数据，避免过度刷新整个章节
            self._loadMangaDataAsync()

        def on_error(error):
            # 显示错误状态
            if self._manga_builder:
                self._manga_builder.set_toolbar_error("生成失败")
            # 检查是否有检查点可以继续
            self._checkMangaPromptStatus()
            MessageService.show_error(self, f"生成失败: {error}")

        # 开始异步生成（不阻塞UI显示加载信息）
        worker = AsyncWorker(do_generate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        # 保存worker引用防止被垃圾回收
        self._manga_worker = worker

    def _checkMangaPromptStatus(self):
        """
        检查漫画提示词生成状态

        如果有未完成的检查点，更新UI显示继续生成选项
        """
        if not self.project_id or not self.current_chapter:
            return

        try:
            status = self.api_client.get_manga_prompt_status(
                self.project_id,
                self.current_chapter,
            )

            if self._manga_builder and status.get("has_checkpoint"):
                # 有未完成的检查点，显示继续生成选项
                progress_info = status.get("progress_info", {})
                scene_count = progress_info.get("scene_count", 0)
                has_layout = progress_info.get("has_layout", False)

                if status.get("status") == "failed":
                    failed_step = status.get("failed_step", "unknown")
                    error_msg = status.get("error_message", "")
                    self._manga_builder.show_checkpoint_status(
                        status="failed",
                        message=f"上次在 {failed_step} 步骤失败: {error_msg[:50]}",
                        scene_count=scene_count,
                        has_layout=has_layout,
                    )
                else:
                    step_name = "排版生成" if has_layout else "场景提取"
                    self._manga_builder.show_checkpoint_status(
                        status="incomplete",
                        message=f"已完成 {step_name}，可继续生成",
                        scene_count=scene_count,
                        has_layout=has_layout,
                    )
        except Exception as e:
            # 获取状态失败，忽略
            pass

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
        """删除漫画提示词回调"""
        if not self.project_id or not self.current_chapter:
            return

        if not MessageService.confirm(self, "确定要删除漫画提示词吗?", "此操作不可恢复"):
            return

        def do_delete():
            return self.api_client.delete_manga_prompts(
                self.project_id, self.current_chapter
            )

        def on_success(result):
            MessageService.show_success(self, "漫画提示词已删除")
            # 仅刷新漫画面板数据，避免过度刷新整个章节
            self._loadMangaDataAsync()

        def on_error(error):
            MessageService.show_error(self, f"删除失败: {error}")

        worker = AsyncWorker(do_delete)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        worker.start()

        self._manga_delete_worker = worker

    def _onGenerateImage(self, scene_id: int, prompt: str, negative_prompt: str):
        """
        生成图片回调

        Args:
            scene_id: 场景ID
            prompt: 正面提示词
            negative_prompt: 负面提示词
        """
        if not self.project_id or not self.current_chapter:
            return

        # 显示加载动画
        self._manga_builder.set_scene_loading(scene_id, True, "正在生成图片...")

        def do_generate():
            return self.api_client.generate_scene_image(
                project_id=self.project_id,
                chapter_number=self.current_chapter,
                scene_id=scene_id,
                prompt=prompt,
            )

        def on_success(result):
            if result.get('success', False):
                images = result.get('images', [])
                image_count = len(images) if images else 1
                self._manga_builder.set_scene_success(
                    scene_id,
                    f"已生成 {image_count} 张图片"
                )
                # 刷新漫画面板数据，更新场景卡片的"已生成"状态
                self._loadMangaDataAsync()
            else:
                error_msg = result.get('error_message', '未知错误')
                self._manga_builder.set_scene_error(scene_id, f"失败: {error_msg[:20]}")
                MessageService.show_error(self, f"生成失败: {error_msg}")

        def on_error(error):
            self._manga_builder.set_scene_error(scene_id, "生成失败")
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

        def do_generate():
            return self.api_client.generate_chapter_manga_pdf(
                self.project_id,
                self.current_chapter,
            )

        def on_success(result):
            if result.get('success', False):
                page_count = result.get('page_count', 0)
                MessageService.show_success(self, f"漫画PDF生成成功 ({page_count}页)")
                # 仅刷新漫画面板数据，避免过度刷新整个章节
                self._loadMangaDataAsync()
            else:
                error_msg = result.get('error_message', '未知错误')
                MessageService.show_error(self, f"PDF生成失败: {error_msg}")

        def on_error(error):
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
