# -*- coding: utf-8 -*-
"""
图像处理模块
负责图像的裁剪、缩放、分割等处理
"""

import os
from io import BytesIO
from typing import List, Tuple, Optional
from datetime import datetime
from PIL import Image


class ImageProcessor:
    """图像处理器类"""

    # 分辨率映射
    RESOLUTION_MAP = {
        "1K": 1024,
        "2K": 2048,
    }

    @staticmethod
    def crop_to_ratio(img: Image.Image, ratio: Tuple[int, int]) -> Image.Image:
        """
        将图片裁剪为指定比例（居中裁剪）

        Args:
            img: PIL Image对象
            ratio: 目标比例元组 (宽, 高)

        Returns:
            裁剪后的Image对象
        """
        w, h = img.size
        target_w, target_h = ratio

        current_ratio = w / h
        target_ratio = target_w / target_h

        # 比例已匹配
        if abs(current_ratio - target_ratio) < 0.01:
            return img

        if current_ratio > target_ratio:
            # 图片太宽，需要裁剪宽度
            new_w = int(h * target_ratio)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            # 图片太高，需要裁剪高度
            new_h = int(w / target_ratio)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

        return img

    @staticmethod
    def resize_image(img: Image.Image, resolution: str) -> Image.Image:
        """
        调整图片分辨率

        Args:
            img: PIL Image对象
            resolution: 分辨率选项 ("原始", "1K", "2K")

        Returns:
            调整后的Image对象
        """
        if resolution == "原始":
            return img

        w, h = img.size
        target = ImageProcessor.RESOLUTION_MAP.get(resolution, w)

        # 已经小于等于目标尺寸
        if max(w, h) <= target:
            return img

        # 按长边缩放
        if w >= h:
            new_w = target
            new_h = int(h * target / w)
        else:
            new_h = target
            new_w = int(w * target / h)

        return img.resize((new_w, new_h), Image.LANCZOS)

    @staticmethod
    def bytes_to_image(data: bytes) -> Optional[Image.Image]:
        """
        将字节数据转换为PIL Image

        Args:
            data: 图片字节数据

        Returns:
            PIL Image对象，失败返回None
        """
        try:
            return Image.open(BytesIO(data))
        except Exception as e:
            print(f"转换图片失败: {e}")
            return None

    @staticmethod
    def save_image(
        img: Image.Image,
        save_dir: str,
        prefix: str = "banana",
        index: int = 1
    ) -> Optional[str]:
        """
        保存图片到指定目录

        Args:
            img: PIL Image对象
            save_dir: 保存目录
            prefix: 文件名前缀
            index: 文件序号

        Returns:
            保存的文件路径，失败返回None
        """
        try:
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}_{index}.png"
            filepath = os.path.join(save_dir, filename)
            img.save(filepath)
            return filepath
        except Exception as e:
            print(f"保存图片失败: {e}")
            return None

    @staticmethod
    def split_sprite_sheet(
        img: Image.Image,
        rows: int,
        cols: int
    ) -> List[Image.Image]:
        """
        分割精灵图为多个帧

        Args:
            img: 精灵图PIL Image对象
            rows: 行数
            cols: 列数

        Returns:
            帧列表
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        frame_w = img.width // cols
        frame_h = img.height // rows

        if frame_w < 1 or frame_h < 1:
            return []

        frames = []
        for row in range(rows):
            for col in range(cols):
                x = col * frame_w
                y = row * frame_h
                frame = img.crop((x, y, x + frame_w, y + frame_h))
                frames.append(frame)

        return frames

    @staticmethod
    def create_thumbnail(
        img: Image.Image,
        size: int = 70
    ) -> Image.Image:
        """
        创建缩略图

        Args:
            img: PIL Image对象
            size: 缩略图最大尺寸

        Returns:
            缩略图Image对象
        """
        thumb = img.copy()
        thumb.thumbnail((size, size), Image.LANCZOS)
        return thumb

    @staticmethod
    def scale_image(
        img: Image.Image,
        scale: float,
        resample: int = Image.NEAREST
    ) -> Image.Image:
        """
        按比例缩放图片

        Args:
            img: PIL Image对象
            scale: 缩放比例
            resample: 重采样方法

        Returns:
            缩放后的Image对象
        """
        if scale == 1.0:
            return img

        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        return img.resize((new_w, new_h), resample)

    @staticmethod
    def load_image(path: str) -> Optional[Image.Image]:
        """
        从文件加载图片

        Args:
            path: 文件路径

        Returns:
            PIL Image对象，失败返回None
        """
        try:
            img = Image.open(path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            return img
        except Exception as e:
            print(f"加载图片失败: {e}")
            return None

    @staticmethod
    def export_frames(
        frames: List[Image.Image],
        frame_indices: List[int],
        output_dir: str,
        base_name: str = "sprite"
    ) -> Tuple[int, str]:
        """
        导出选中的帧

        Args:
            frames: 帧列表
            frame_indices: 要导出的帧索引列表
            output_dir: 输出目录
            base_name: 基础文件名

        Returns:
            (成功导出的数量, 错误信息)
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            count = 0
            for i, frame_idx in enumerate(frame_indices):
                if 0 <= frame_idx < len(frames):
                    frame = frames[frame_idx]
                    filename = f"{base_name}_frame_{i:03d}.png"
                    filepath = os.path.join(output_dir, filename)
                    frame.save(filepath)
                    count += 1
            return count, ""
        except Exception as e:
            return 0, str(e)
