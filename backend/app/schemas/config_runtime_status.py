"""
配置运行时状态字段（Schema）

用于在 LLM/嵌入 等配置响应模型之间复用运行时状态字段，避免重复定义与漂移。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConfigRuntimeStatus(BaseModel):
    """配置运行时状态字段（可被 Read schema 继承）。"""

    is_active: bool
    is_verified: bool
    last_test_at: Optional[datetime] = None
    test_status: Optional[str] = Field(default=None, description="success, failed, pending")
    test_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


__all__ = ["ConfigRuntimeStatus"]
