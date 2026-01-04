"""
分镜设计模块数据模型

定义分镜设计的所有数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class ShotType(str, Enum):
    """镜头类型"""
    ESTABLISHING = "establishing"       # 全景/建立镜头
    LONG = "long"                       # 远景
    MEDIUM = "medium"                   # 中景
    CLOSE_UP = "close_up"               # 近景
    EXTREME_CLOSE_UP = "extreme_close_up"  # 特写
    OVER_SHOULDER = "over_shoulder"     # 过肩镜头
    POV = "pov"                         # 主观视角
    BIRD_EYE = "bird_eye"               # 鸟瞰
    WORM_EYE = "worm_eye"               # 仰视

    @classmethod
    def from_string(cls, value: str) -> "ShotType":
        """从字符串转换"""
        value = value.lower().strip().replace("-", "_").replace(" ", "_")
        for member in cls:
            if member.value == value:
                return member
        return cls.MEDIUM


class PanelSize(str, Enum):
    """画格大小"""
    SMALL = "small"       # 小格 (1/6 页)
    MEDIUM = "medium"     # 中格 (1/4 页)
    LARGE = "large"       # 大格 (1/3 页)
    HALF = "half"         # 半页
    FULL = "full"         # 整页
    SPREAD = "spread"     # 跨页

    @classmethod
    def from_string(cls, value: str) -> "PanelSize":
        """从字符串转换"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.MEDIUM


class PanelShape(str, Enum):
    """画格形状"""
    RECTANGLE = "rectangle"     # 矩形（标准）
    SQUARE = "square"           # 正方形
    VERTICAL = "vertical"       # 竖长
    HORIZONTAL = "horizontal"   # 横长
    IRREGULAR = "irregular"     # 不规则
    BORDERLESS = "borderless"   # 无边框

    @classmethod
    def from_string(cls, value: str) -> "PanelShape":
        """从字符串转换"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.RECTANGLE


@dataclass
class DialogueBubble:
    """对话气泡"""
    speaker: str                        # 说话人
    content: str                        # 对话内容
    bubble_type: str = "normal"         # normal/shout/whisper/thought/narration
    position: str = "top_right"         # 气泡位置
    emotion: str = "neutral"            # 说话时的情绪

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "speaker": self.speaker,
            "content": self.content,
            "bubble_type": self.bubble_type,
            "position": self.position,
            "emotion": self.emotion,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DialogueBubble":
        """从字典创建"""
        return cls(
            speaker=data.get("speaker", ""),
            content=data.get("content", ""),
            bubble_type=data.get("bubble_type", "normal"),
            position=data.get("position", "top_right"),
            emotion=data.get("emotion", "neutral"),
        )


@dataclass
class SoundEffect:
    """音效文字"""
    text: str                           # 音效文字
    type: str = "action"                # action/impact/ambient/emotional/vocal
    intensity: str = "medium"           # small/medium/large
    position: str = ""                  # 在画面中的位置

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "text": self.text,
            "type": self.type,
            "intensity": self.intensity,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SoundEffect":
        """从字典创建"""
        return cls(
            text=data.get("text", ""),
            type=data.get("type", "action"),
            intensity=data.get("intensity", "medium"),
            position=data.get("position", ""),
        )


@dataclass
class PanelDesign:
    """分镜设计"""
    panel_id: int                       # 分镜ID（页内从1开始）
    size: PanelSize = PanelSize.MEDIUM
    shape: PanelShape = PanelShape.RECTANGLE
    shot_type: ShotType = ShotType.MEDIUM

    # 内容描述
    visual_description: str = ""        # 画面描述（中文）
    visual_description_en: str = ""     # 画面描述（英文，用于绘图）
    characters: List[str] = field(default_factory=list)  # 出场角色
    character_actions: Dict[str, str] = field(default_factory=dict)  # 角色动作
    character_expressions: Dict[str, str] = field(default_factory=dict)  # 角色表情

    # 文字元素
    dialogues: List[DialogueBubble] = field(default_factory=list)
    narration: str = ""                 # 旁白
    sound_effects: List[SoundEffect] = field(default_factory=list)

    # 视觉效果
    focus_point: str = ""               # 视觉焦点
    lighting: str = ""                  # 光线
    atmosphere: str = ""                # 氛围
    background: str = ""                # 背景描述
    motion_lines: bool = False          # 是否需要速度线
    impact_effects: bool = False        # 是否需要冲击效果

    # 关联信息
    event_indices: List[int] = field(default_factory=list)  # 关联的事件索引
    is_key_panel: bool = False          # 是否关键画格
    transition_hint: str = ""           # 到下一格的过渡方式

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "panel_id": self.panel_id,
            "size": self.size.value,
            "shape": self.shape.value,
            "shot_type": self.shot_type.value,
            "visual_description": self.visual_description,
            "visual_description_en": self.visual_description_en,
            "characters": self.characters,
            "character_actions": self.character_actions,
            "character_expressions": self.character_expressions,
            "dialogues": [d.to_dict() for d in self.dialogues],
            "narration": self.narration,
            "sound_effects": [s.to_dict() for s in self.sound_effects],
            "focus_point": self.focus_point,
            "lighting": self.lighting,
            "atmosphere": self.atmosphere,
            "background": self.background,
            "motion_lines": self.motion_lines,
            "impact_effects": self.impact_effects,
            "event_indices": self.event_indices,
            "is_key_panel": self.is_key_panel,
            "transition_hint": self.transition_hint,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PanelDesign":
        """从字典创建"""
        # 安全获取列表和字典类型的字段，确保不会是 None
        dialogues_data = data.get("dialogues") or []
        sound_effects_data = data.get("sound_effects") or []

        return cls(
            panel_id=data.get("panel_id") or 1,
            size=PanelSize.from_string(data.get("size") or "medium"),
            shape=PanelShape.from_string(data.get("shape") or "rectangle"),
            shot_type=ShotType.from_string(data.get("shot_type") or "medium"),
            visual_description=data.get("visual_description") or "",
            visual_description_en=data.get("visual_description_en") or "",
            characters=data.get("characters") or [],
            character_actions=data.get("character_actions") or {},
            character_expressions=data.get("character_expressions") or {},
            dialogues=[
                DialogueBubble.from_dict(d) for d in dialogues_data
                if isinstance(d, dict)
            ],
            narration=data.get("narration") or "",
            sound_effects=[
                SoundEffect.from_dict(s) for s in sound_effects_data
                if isinstance(s, dict)
            ],
            focus_point=data.get("focus_point") or "",
            lighting=data.get("lighting") or "",
            atmosphere=data.get("atmosphere") or "",
            background=data.get("background") or "",
            motion_lines=bool(data.get("motion_lines")),
            impact_effects=bool(data.get("impact_effects")),
            event_indices=data.get("event_indices") or [],
            is_key_panel=bool(data.get("is_key_panel")),
            transition_hint=data.get("transition_hint") or "",
        )


@dataclass
class PageStoryboard:
    """单页分镜结果"""
    page_number: int                    # 页码
    panels: List[PanelDesign] = field(default_factory=list)
    page_purpose: str = ""              # 页面目的
    reading_flow: str = "right_to_left" # 阅读流向
    visual_rhythm: str = ""             # 视觉节奏描述
    layout_description: str = ""        # 布局描述

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "page_number": self.page_number,
            "panels": [p.to_dict() for p in self.panels],
            "page_purpose": self.page_purpose,
            "reading_flow": self.reading_flow,
            "visual_rhythm": self.visual_rhythm,
            "layout_description": self.layout_description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PageStoryboard":
        """从字典创建"""
        return cls(
            page_number=data.get("page_number", 1),
            panels=[PanelDesign.from_dict(p) for p in data.get("panels", [])],
            page_purpose=data.get("page_purpose", ""),
            reading_flow=data.get("reading_flow", "right_to_left"),
            visual_rhythm=data.get("visual_rhythm", ""),
            layout_description=data.get("layout_description", ""),
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
    style_notes: str = ""               # 风格说明

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "pages": [p.to_dict() for p in self.pages],
            "total_pages": self.total_pages,
            "total_panels": self.total_panels,
            "style_notes": self.style_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StoryboardResult":
        """从字典创建"""
        pages = [PageStoryboard.from_dict(p) for p in data.get("pages", [])]
        return cls(
            pages=pages,
            total_pages=data.get("total_pages", len(pages)),
            total_panels=data.get("total_panels", sum(p.get_panel_count() for p in pages)),
            style_notes=data.get("style_notes", ""),
        )

    def get_page(self, page_number: int) -> Optional[PageStoryboard]:
        """获取指定页码的分镜"""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None


__all__ = [
    "ShotType",
    "PanelSize",
    "PanelShape",
    "DialogueBubble",
    "SoundEffect",
    "PanelDesign",
    "PageStoryboard",
    "StoryboardResult",
]
