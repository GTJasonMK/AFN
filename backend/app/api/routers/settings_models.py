"""
settings 路由共享模型

说明：集中放置多个 settings 子路由共同使用的 Pydantic 模型，避免重复定义。
"""

from typing import List

from pydantic import BaseModel


class ConfigImportResult(BaseModel):
    """配置导入结果"""

    success: bool
    message: str
    details: List[str] = []


__all__ = ["ConfigImportResult"]

