"""
分镜设计模块数据模型

定义分镜设计的所有数据结构。
简化版：使用简单的横框/竖框布局。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ShotType(str, Enum):
    """镜头类型"""
    LONG = "long"                       # 远景
    MEDIUM = "medium"                   # 中景
    CLOSE_UP = "close_up"               # 近景

    @classmethod
    def from_string(cls, value: str) -> "ShotType":
        """从字符串转换"""
        value = value.lower().strip().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == value:
                return member
        return cls.MEDIUM


class PanelShape(str, Enum):
    """画格形状"""
    HORIZONTAL = "horizontal"   # 横向画格
    VERTICAL = "vertical"       # 纵向画格
    SQUARE = "square"           # 正方形

    @classmethod
    def from_string(cls, value: str) -> "PanelShape":
        """从字符串转换"""
        value = value.lower().strip()
        # 兼容旧数据
        if value in ("rectangle", ""):
            return cls.HORIZONTAL
        for member in cls:
            if member.value == value:
                return member
        return cls.HORIZONTAL


class WidthRatio(str, Enum):
    """画格宽度占比"""
    FULL = "full"           # 占整行宽度
    HALF = "half"           # 占半行宽度
    THIRD = "third"         # 占1/3行宽度
    TWO_THIRDS = "two_thirds"  # 占2/3行宽度

    @classmethod
    def from_string(cls, value: str) -> "WidthRatio":
        """从字符串转换"""
        value = value.lower().strip().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == value:
                return member
        return cls.HALF


class AspectRatio(str, Enum):
    """画格宽高比"""
    WIDE = "16:9"           # 宽屏，适合远景、场景
    STANDARD = "4:3"        # 标准，适合中景
    SQUARE = "1:1"          # 正方形，适合特写
    TALL = "3:4"            # 竖向，适合人物全身
    VERY_TALL = "9:16"      # 超竖向，适合纵向动作

    @classmethod
    def from_string(cls, value: str) -> "AspectRatio":
        """从字符串转换"""
        value = value.strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.STANDARD


@dataclass
class DialogueBubble:
    """对话气泡（简化版）"""
    speaker: str                        # 说话人
    content: str                        # 对话内容

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "speaker": self.speaker,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DialogueBubble":
        """从字典创建"""
        return cls(
            speaker=data.get("speaker", ""),
            content=data.get("content", ""),
        )


@dataclass
class PanelDesign:
    """
    分镜设计

    使用行布局系统，确保页面填充饱满。
    支持跨行布局：一个画格可以跨越多行。

    布局规则：
    1. 同一行的画格宽度之和必须等于100%
    2. 同一"列区域"的画格行数之和必须相等
       例如：左边A跨2行，右边B+C各占1行，则 A.row_span = B.row_span + C.row_span
    """
    panel_id: int                       # 分镜ID（页内从1开始）
    row_id: int = 1                     # 起始行号（从1开始）
    row_span: int = 1                   # 跨越行数（默认1，最大3）
    shape: PanelShape = PanelShape.HORIZONTAL
    shot_type: ShotType = ShotType.MEDIUM

    # 排版信息
    width_ratio: WidthRatio = WidthRatio.HALF       # 宽度占比（同一行之和=100%）
    aspect_ratio: AspectRatio = AspectRatio.STANDARD  # 宽高比

    # 内容描述
    visual_description: str = ""        # 画面描述（中文）
    characters: List[str] = field(default_factory=list)  # 出场角色

    # 场景和氛围
    background: str = ""                # 背景/场景描述
    atmosphere: str = ""                # 氛围（如：紧张、温馨、神秘）
    lighting: str = ""                  # 光线（如：明亮、昏暗、逆光）

    # 角色动作和表情
    character_actions: Dict[str, str] = field(default_factory=dict)      # {角色名: 动作}
    character_expressions: Dict[str, str] = field(default_factory=dict)  # {角色名: 表情}

    # 对话
    dialogues: List[DialogueBubble] = field(default_factory=list)

    # 关联信息
    event_indices: List[int] = field(default_factory=list)  # 关联的事件索引

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "panel_id": self.panel_id,
            "row_id": self.row_id,
            "row_span": self.row_span,
            "shape": self.shape.value,
            "shot_type": self.shot_type.value,
            "width_ratio": self.width_ratio.value,
            "aspect_ratio": self.aspect_ratio.value,
            "visual_description": self.visual_description,
            "characters": self.characters,
            "background": self.background,
            "atmosphere": self.atmosphere,
            "lighting": self.lighting,
            "character_actions": self.character_actions,
            "character_expressions": self.character_expressions,
            "dialogues": [d.to_dict() for d in self.dialogues],
            "event_indices": self.event_indices,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PanelDesign":
        """从字典创建"""
        dialogues_data = data.get("dialogues") or []

        return cls(
            panel_id=data.get("panel_id") or 1,
            row_id=data.get("row_id") or 1,
            row_span=data.get("row_span") or 1,
            shape=PanelShape.from_string(data.get("shape") or "horizontal"),
            shot_type=ShotType.from_string(data.get("shot_type") or "medium"),
            width_ratio=WidthRatio.from_string(data.get("width_ratio") or "half"),
            aspect_ratio=AspectRatio.from_string(data.get("aspect_ratio") or "4:3"),
            visual_description=data.get("visual_description") or "",
            characters=data.get("characters") or [],
            background=data.get("background") or "",
            atmosphere=data.get("atmosphere") or "",
            lighting=data.get("lighting") or "",
            character_actions=data.get("character_actions") or {},
            character_expressions=data.get("character_expressions") or {},
            dialogues=[
                DialogueBubble.from_dict(d) for d in dialogues_data
                if isinstance(d, dict)
            ],
            event_indices=data.get("event_indices") or [],
        )


@dataclass
class PageStoryboard:
    """单页分镜结果（简化版）"""
    page_number: int                    # 页码
    panels: List[PanelDesign] = field(default_factory=list)
    layout_description: str = ""        # 布局描述

    # 间隙配置（单位：像素或百分比，由前端解释）
    gutter_horizontal: int = 8          # 水平间隙（列之间）
    gutter_vertical: int = 8            # 垂直间隙（行之间）

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "page_number": self.page_number,
            "panels": [p.to_dict() for p in self.panels],
            "layout_description": self.layout_description,
            "gutter_horizontal": self.gutter_horizontal,
            "gutter_vertical": self.gutter_vertical,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PageStoryboard":
        """从字典创建（兼容旧数据）"""
        return cls(
            page_number=data.get("page_number", 1),
            panels=[PanelDesign.from_dict(p) for p in data.get("panels", [])],
            layout_description=data.get("layout_description", ""),
            gutter_horizontal=data.get("gutter_horizontal", 8),
            gutter_vertical=data.get("gutter_vertical", 8),
        )

    def get_panel_count(self) -> int:
        """获取分镜数量"""
        return len(self.panels)


@dataclass
class StoryboardResult:
    """完整分镜结果"""
    pages: List[PageStoryboard] = field(default_factory=list)
    total_pages: int = 0
    total_panels: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "pages": [p.to_dict() for p in self.pages],
            "total_pages": self.total_pages,
            "total_panels": self.total_panels,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StoryboardResult":
        """从字典创建"""
        pages = [PageStoryboard.from_dict(p) for p in data.get("pages", [])]
        return cls(
            pages=pages,
            total_pages=data.get("total_pages", len(pages)),
            total_panels=data.get("total_panels", sum(p.get_panel_count() for p in pages)),
        )

    def get_page(self, page_number: int) -> Optional[PageStoryboard]:
        """获取指定页码的分镜"""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None


__all__ = [
    "ShotType",
    "PanelShape",
    "WidthRatio",
    "AspectRatio",
    "DialogueBubble",
    "PanelDesign",
    "PageStoryboard",
    "StoryboardResult",
]
