"""
提示词构建器模块数据模型

定义最终输出的提示词数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class PanelPrompt:
    """
    画格提示词结果

    简化版：移除复杂坐标，使用布局槽位。
    对话、音效等文字元素已整合到 prompt_en 中，由AI直接生成。
    """
    # 标识
    panel_id: str  # 格式: "page{page}_panel{panel_id}"
    page_number: int
    panel_number: int  # 页内画格序号

    # 画格元信息
    size: str  # small/medium/large/half/full
    shape: str  # rectangle/square/vertical/horizontal
    shot_type: str  # establishing/long/medium/close_up/extreme_close_up/etc
    aspect_ratio: str  # 宽高比 (如 "16:9", "4:3", "1:1")

    # 提示词（无默认值的字段必须在有默认值字段之前）
    prompt_en: str  # 英文正向提示词（用于AI绘图）- 包含对话和音效！
    prompt_zh: str  # 中文描述
    negative_prompt: str  # 负向提示词

    # 布局属性（简化版）
    importance: str = "standard"  # hero/major/standard/minor/micro
    layout_slot: str = "third_row"  # full_row/half_row/third_row/quarter_row

    # 文字元素（已整合到 prompt_en，此处保留原始数据用于参考）
    dialogues: List[Dict[str, Any]] = field(default_factory=list)  # 对话列表
    narration: str = ""  # 旁白
    sound_effects: List[Dict[str, Any]] = field(default_factory=list)  # 音效列表

    # 角色信息
    characters: List[str] = field(default_factory=list)
    character_actions: Dict[str, str] = field(default_factory=dict)
    character_expressions: Dict[str, str] = field(default_factory=dict)

    # 视觉信息
    focus_point: str = ""  # 视觉焦点
    lighting: str = ""  # 光线描述
    atmosphere: str = ""  # 氛围描述
    background: str = ""  # 背景描述
    motion_lines: bool = False  # 速度线
    impact_effects: bool = False  # 冲击效果
    is_key_panel: bool = False  # 是否关键画格

    # 参考图
    reference_image_paths: Optional[List[str]] = None  # 角色立绘路径

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "panel_id": self.panel_id,
            "page_number": self.page_number,
            "panel_number": self.panel_number,
            "size": self.size,
            "shape": self.shape,
            "shot_type": self.shot_type,
            "aspect_ratio": self.aspect_ratio,
            # 布局属性（简化版）
            "importance": self.importance,
            "layout_slot": self.layout_slot,
            # 提示词
            "prompt_en": self.prompt_en,
            "prompt_zh": self.prompt_zh,
            "negative_prompt": self.negative_prompt,
            "dialogues": self.dialogues,
            "narration": self.narration,
            "sound_effects": self.sound_effects,
            "characters": self.characters,
            "character_actions": self.character_actions,
            "character_expressions": self.character_expressions,
            "focus_point": self.focus_point,
            "lighting": self.lighting,
            "atmosphere": self.atmosphere,
            "background": self.background,
            "motion_lines": self.motion_lines,
            "impact_effects": self.impact_effects,
            "is_key_panel": self.is_key_panel,
            "reference_image_paths": self.reference_image_paths,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PanelPrompt":
        """从字典创建（兼容旧数据）"""
        # 获取重要性，用于计算布局槽位和宽高比
        importance = data.get("importance", "standard")
        importance_to_slot = {
            "hero": "full_row",
            "major": "half_row",
            "standard": "third_row",
            "minor": "quarter_row",
            "micro": "quarter_row",
        }
        # 重要性到宽高比的映射（与 storyboard/models.py 保持一致）
        importance_to_aspect = {
            "hero": "16:9",
            "major": "4:3",
            "standard": "1:1",
            "minor": "1:1",
            "micro": "1:1",
        }
        layout_slot = data.get("layout_slot") or importance_to_slot.get(importance, "third_row")
        aspect_ratio = data.get("aspect_ratio") or importance_to_aspect.get(importance, "4:3")

        return cls(
            panel_id=data.get("panel_id", ""),
            page_number=data.get("page_number", 1),
            panel_number=data.get("panel_number", 1),
            size=data.get("size", "medium"),
            shape=data.get("shape", "rectangle"),
            shot_type=data.get("shot_type", "medium"),
            aspect_ratio=aspect_ratio,
            # 布局属性（简化版）
            importance=importance,
            layout_slot=layout_slot,
            # 提示词
            prompt_en=data.get("prompt_en", ""),
            prompt_zh=data.get("prompt_zh", ""),
            negative_prompt=data.get("negative_prompt", ""),
            dialogues=data.get("dialogues", []),
            narration=data.get("narration", ""),
            sound_effects=data.get("sound_effects", []),
            characters=data.get("characters", []),
            character_actions=data.get("character_actions", {}),
            character_expressions=data.get("character_expressions", {}),
            focus_point=data.get("focus_point", ""),
            lighting=data.get("lighting", ""),
            atmosphere=data.get("atmosphere", ""),
            background=data.get("background", ""),
            motion_lines=data.get("motion_lines", False),
            impact_effects=data.get("impact_effects", False),
            is_key_panel=data.get("is_key_panel", False),
            reference_image_paths=data.get("reference_image_paths"),
        )


@dataclass
class PagePromptResult:
    """单页提示词结果"""
    page_number: int
    panels: List[PanelPrompt] = field(default_factory=list)
    layout_description: str = ""
    reading_flow: str = "left_to_right"  # 默认从左到右
    # Bug 35 修复: 添加 page_purpose 和 visual_rhythm 字段
    page_purpose: str = ""  # 页面目的（来自 PageStoryboard）
    visual_rhythm: str = ""  # 视觉节奏描述（来自 PageStoryboard）

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "page_number": self.page_number,
            "panels": [p.to_dict() for p in self.panels],
            "layout_description": self.layout_description,
            "reading_flow": self.reading_flow,
            # Bug 35 修复: 保存 page_purpose 和 visual_rhythm
            "page_purpose": self.page_purpose,
            "visual_rhythm": self.visual_rhythm,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PagePromptResult":
        """从字典创建"""
        return cls(
            page_number=data.get("page_number", 1),
            panels=[PanelPrompt.from_dict(p) for p in data.get("panels", [])],
            layout_description=data.get("layout_description", ""),
            reading_flow=data.get("reading_flow", "left_to_right"),
            # Bug 35 修复: 读取 page_purpose 和 visual_rhythm
            page_purpose=data.get("page_purpose", ""),
            visual_rhythm=data.get("visual_rhythm", ""),
        )


@dataclass
class MangaPromptResult:
    """完整漫画提示词结果"""
    chapter_number: int
    style: str
    pages: List[PagePromptResult] = field(default_factory=list)
    total_pages: int = 0
    total_panels: int = 0
    character_profiles: Dict[str, str] = field(default_factory=dict)
    dialogue_language: str = "chinese"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "chapter_number": self.chapter_number,
            "style": self.style,
            "pages": [p.to_dict() for p in self.pages],
            "total_pages": self.total_pages,
            "total_panels": self.total_panels,
            "character_profiles": self.character_profiles,
            "dialogue_language": self.dialogue_language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MangaPromptResult":
        """从字典创建"""
        pages = [PagePromptResult.from_dict(p) for p in data.get("pages", [])]
        return cls(
            chapter_number=data.get("chapter_number", 1),
            style=data.get("style", "manga"),
            pages=pages,
            total_pages=data.get("total_pages", len(pages)),
            total_panels=data.get("total_panels", sum(len(p.panels) for p in pages)),
            character_profiles=data.get("character_profiles", {}),
            dialogue_language=data.get("dialogue_language", "chinese"),
        )

    def get_all_prompts(self) -> List[PanelPrompt]:
        """获取所有画格提示词"""
        prompts = []
        for page in self.pages:
            prompts.extend(page.panels)
        return prompts


__all__ = [
    "PanelPrompt",
    "PagePromptResult",
    "MangaPromptResult",
]
