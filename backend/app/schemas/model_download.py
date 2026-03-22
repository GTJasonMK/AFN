"""
模型下载相关 Schema

用于桌面端在设置页中下载“本地嵌入默认模型”等资源时的请求参数定义。
"""

from typing import Optional

from pydantic import BaseModel, Field


class DownloadDefaultLocalEmbeddingModelRequest(BaseModel):
    """
    下载默认本地嵌入模型的请求体。

    说明：
    - 默认 repo_id 为空时，会使用服务端内置的默认模型（如 BAAI/bge-base-zh-v1.5）。
    - activate_after_download 为 True 时，会在下载完成后自动创建/激活嵌入配置（若配置已存在则仅激活）。
    """

    repo_id: Optional[str] = Field(
        default=None,
        description="HuggingFace 仓库ID（如 BAAI/bge-base-zh-v1.5）。留空使用默认。",
    )
    activate_after_download: bool = Field(
        default=True,
        description="下载完成后是否自动激活该嵌入配置。",
    )

