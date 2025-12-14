# -*- coding: utf-8 -*-
"""
后台工作线程模块
"""

from PyQt6.QtCore import QThread, pyqtSignal
from backend import ApiClient, ImageProcessor

class GeneratorThread(QThread):
    """图片生成线程"""

    # 信号
    progress = pyqtSignal(str)  # 进度信息
    finished = pyqtSignal(list)  # 生成完成，参数为文件路径列表
    error = pyqtSignal(str)  # 错误信息

    def __init__(
        self,
        api_client: ApiClient,
        api_key: str,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        count: int,
        ratio: tuple,
        resolution: str,
        save_dir: str
    ):
        super().__init__()
        self.api_client = api_client
        self.api_key = api_key
        self.prompt = prompt
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.count = count
        self.ratio = ratio
        self.resolution = resolution
        self.save_dir = save_dir

    def run(self):
        """执行生成"""
        # 调用API生成
        result = self.api_client.generate_images(
            api_key=self.api_key,
            prompt=self.prompt,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            count=self.count,
            progress_callback=lambda msg: self.progress.emit(msg)
        )

        if not result.success:
            self.error.emit(result.error_message)
            return

        self.progress.emit(f"下载{len(result.image_urls)}张图片...")

        # 下载并处理图片
        saved_files = []
        for i, url in enumerate(result.image_urls):
            data = self.api_client.download_image(url)
            if data:
                img = ImageProcessor.bytes_to_image(data)
                if img:
                    # 裁剪和缩放
                    img = ImageProcessor.crop_to_ratio(img, self.ratio)
                    img = ImageProcessor.resize_image(img, self.resolution)
                    # 保存
                    path = ImageProcessor.save_image(img, self.save_dir, "banana", i + 1)
                    if path:
                        saved_files.append(path)

        if saved_files:
            self.finished.emit(saved_files)
        else:
            self.error.emit("下载或保存图片失败")
