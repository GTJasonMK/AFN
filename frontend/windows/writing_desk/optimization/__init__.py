"""
正文优化模块

提供正文优化内容组件和相关类。

模块结构：
    - content.py: 主OptimizationContent组件
    - models.py: 数据模型（OptimizationMode枚举）
"""

from .content import OptimizationContent
from .models import OptimizationMode

__all__ = [
    "OptimizationContent",
    "OptimizationMode",
]
