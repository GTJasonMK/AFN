"""
页面规划模块（简化版）

基于章节信息进行全局页面规划：
- 确定总页数
- 分配事件到各页面
"""

from .models import (
    PagePlanItem,
    PagePlanResult,
)
from .page_planner import PagePlanner

__all__ = [
    "PagePlanItem",
    "PagePlanResult",
    "PagePlanner",
]
