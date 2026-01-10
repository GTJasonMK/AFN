"""
正文优化数据模型

定义优化模式枚举等数据结构。
"""

from enum import Enum


class OptimizationMode(Enum):
    """优化模式枚举 - 参考Claude Code的权限设计

    两层权限控制：
    - 审核模式：每个建议单独确认，提供最高控制度
    - 自动模式：自动应用所有建议，适合快速优化
    """
    REVIEW = "review"      # 审核模式：每个建议暂停等待确认
    AUTO = "auto"          # 自动模式：自动应用建议


__all__ = [
    "OptimizationMode",
]
