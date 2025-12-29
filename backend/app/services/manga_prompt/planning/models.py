"""
页面规划模块数据模型

定义全局页面规划的所有数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class PacingType(str, Enum):
    """节奏类型"""
    SLOW = "slow"           # 慢节奏，铺垫
    MEDIUM = "medium"       # 中等节奏
    FAST = "fast"           # 快节奏，紧张
    EXPLOSIVE = "explosive" # 爆发，高潮

    @classmethod
    def from_string(cls, value: str) -> "PacingType":
        """从字符串转换"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.MEDIUM


class PageRole(str, Enum):
    """页面角色"""
    OPENING = "opening"         # 开场
    SETUP = "setup"             # 铺垫
    RISING = "rising"           # 上升
    CLIMAX = "climax"           # 高潮
    FALLING = "falling"         # 下降
    RESOLUTION = "resolution"   # 收尾
    TRANSITION = "transition"   # 过渡

    @classmethod
    def from_string(cls, value: str) -> "PageRole":
        """从字符串转换"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.SETUP


@dataclass
class PagePlanItem:
    """单页规划"""
    page_number: int                      # 页码（从1开始）
    event_indices: List[int] = field(default_factory=list)  # 包含的事件索引
    content_summary: str = ""             # 内容摘要
    content_summary_en: str = ""          # 英文内容摘要
    pacing: PacingType = PacingType.MEDIUM
    role: PageRole = PageRole.SETUP
    key_characters: List[str] = field(default_factory=list)  # 主要角色
    has_dialogue: bool = False
    has_action: bool = False
    suggested_panel_count: int = 4        # 建议分镜数 (3-7)
    notes: str = ""                       # 特殊说明

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "page_number": self.page_number,
            "event_indices": self.event_indices,
            "content_summary": self.content_summary,
            "content_summary_en": self.content_summary_en,
            "pacing": self.pacing.value,
            "role": self.role.value,
            "key_characters": self.key_characters,
            "has_dialogue": self.has_dialogue,
            "has_action": self.has_action,
            "suggested_panel_count": self.suggested_panel_count,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PagePlanItem":
        """从字典创建"""
        return cls(
            page_number=data.get("page_number", 1),
            event_indices=data.get("event_indices", []),
            content_summary=data.get("content_summary", ""),
            content_summary_en=data.get("content_summary_en", ""),
            pacing=PacingType.from_string(data.get("pacing", "medium")),
            role=PageRole.from_string(data.get("role", "setup")),
            key_characters=data.get("key_characters", []),
            has_dialogue=data.get("has_dialogue", False),
            has_action=data.get("has_action", False),
            suggested_panel_count=data.get("suggested_panel_count", 4),
            notes=data.get("notes", ""),
        )


@dataclass
class PagePlanResult:
    """页面规划结果"""
    total_pages: int = 0
    pages: List[PagePlanItem] = field(default_factory=list)
    pacing_notes: str = ""                # 整体节奏说明
    climax_pages: List[int] = field(default_factory=list)  # 高潮页码

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "total_pages": self.total_pages,
            "pages": [p.to_dict() for p in self.pages],
            "pacing_notes": self.pacing_notes,
            "climax_pages": self.climax_pages,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PagePlanResult":
        """从字典创建"""
        return cls(
            total_pages=data.get("total_pages", 0),
            pages=[PagePlanItem.from_dict(p) for p in data.get("pages", [])],
            pacing_notes=data.get("pacing_notes", ""),
            climax_pages=data.get("climax_pages", []),
        )

    def get_page(self, page_number: int) -> Optional[PagePlanItem]:
        """获取指定页码的规划"""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None


__all__ = [
    "PacingType",
    "PageRole",
    "PagePlanItem",
    "PagePlanResult",
]
