"""
页面规划模块

基于章节信息进行全局页面规划：
- 确定总页数
- 分配事件到各页面
- 控制叙事节奏
- 识别高潮页面
"""

from .models import (
    PacingType,
    PageRole,
    PagePlanItem,
    PagePlanResult,
)
from .prompts import (
    PROMPT_NAME,
    PAGE_PLANNING_PROMPT,
    PLANNING_SYSTEM_PROMPT,
)
from .page_planner import PagePlanner

__all__ = [
    # 枚举类型
    "PacingType",
    "PageRole",
    # 数据类
    "PagePlanItem",
    "PagePlanResult",
    # 规划器
    "PagePlanner",
    # 提示词
    "PROMPT_NAME",
    "PAGE_PLANNING_PROMPT",
    "PLANNING_SYSTEM_PROMPT",
]
