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

    包含生成单个画格图像所需的所有提示词信息
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

    # 提示词
    prompt_en: str  # 英文正向提示词（用于AI绘图）
    prompt_zh: str  # 中文描述
    negative_prompt: str  # 负向提示词

    # 文字元素
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
        """从字典创建"""
        return cls(
            panel_id=data.get("panel_id", ""),
            page_number=data.get("page_number", 1),
            panel_number=data.get("panel_number", 1),
            size=data.get("size", "medium"),
            shape=data.get("shape", "rectangle"),
            shot_type=data.get("shot_type", "medium"),
            aspect_ratio=data.get("aspect_ratio", "4:3"),
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
    reading_flow: str = "right_to_left"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "page_number": self.page_number,
            "panels": [p.to_dict() for p in self.panels],
            "layout_description": self.layout_description,
            "reading_flow": self.reading_flow,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PagePromptResult":
        """从字典创建"""
        return cls(
            page_number=data.get("page_number", 1),
            panels=[PanelPrompt.from_dict(p) for p in data.get("panels", [])],
            layout_description=data.get("layout_description", ""),
            reading_flow=data.get("reading_flow", "right_to_left"),
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
