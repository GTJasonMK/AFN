"""
图片生成请求队列

管理所有图片生成API调用的并发控制。
"""

from .base import ConfigurableRequestQueue


class ImageRequestQueue(ConfigurableRequestQueue):
    """
    图片生成请求队列（单例模式）

    所有图片生成调用（OpenAI兼容、Stability、ComfyUI等）都通过此队列进行并发控制。
    """

    queue_name = "image"
    settings_key = "image_max_concurrent"
    default_max_concurrent = 2
    log_label = "图片"
