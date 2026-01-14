"""
提示词构建器模块数据模型（简化版）

定义最终输出的提示词数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class PanelPrompt:
    """
    画格提示词结果

    包含排版信息和提示词。
    """
    # 标识
    panel_id: str  # 格式: "page{page}_panel{panel_id}"
    page_number: int
    panel_number: int  # 页内画格序号

    # 画格元信息
    shape: str  # horizontal/vertical/square
    shot_type: str  # long/medium/close_up

    # 排版信息
    row_id: int  # 起始行号（从1开始）
    row_span: int  # 跨越行数（默认1）
    width_ratio: str  # full/two_thirds/half/third
    aspect_ratio: str  # 16:9/4:3/1:1/3:4/9:16

    # 提示词
    prompt: str  # 提示词（中文）
    negative_prompt: str  # 负向提示词

    # 对话（保留原始数据用于参考）
    dialogues: List[Dict[str, Any]] = field(default_factory=list)

    # 角色信息
    characters: List[str] = field(default_factory=list)

    # 参考图
    reference_image_paths: Optional[List[str]] = None  # 角色立绘路径

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "panel_id": self.panel_id,
            "page_number": self.page_number,
            "panel_number": self.panel_number,
            "shape": self.shape,
            "shot_type": self.shot_type,
            "row_id": self.row_id,
            "row_span": self.row_span,
            "width_ratio": self.width_ratio,
            "aspect_ratio": self.aspect_ratio,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "dialogues": self.dialogues,
            "characters": self.characters,
            "reference_image_paths": self.reference_image_paths,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PanelPrompt":
        """从字典创建"""
        return cls(
            panel_id=data.get("panel_id", ""),
            page_number=data.get("page_number", 1),
            panel_number=data.get("panel_number", 1),
            shape=data.get("shape", "horizontal"),
            shot_type=data.get("shot_type", "medium"),
            row_id=data.get("row_id", 1),
            row_span=data.get("row_span", 1),
            width_ratio=data.get("width_ratio", "half"),
            aspect_ratio=data.get("aspect_ratio", "4:3"),
            prompt=data.get("prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            dialogues=data.get("dialogues", []),
            characters=data.get("characters", []),
            reference_image_paths=data.get("reference_image_paths"),
        )


@dataclass
class PagePrompt:
    """
    整页漫画提示词结果

    用于生成带分格布局的整页漫画图片，让AI直接画出完整页面。
    """
    page_number: int

    # 布局模板标识 (如 "3row_1x2x1" 表示3行，第1行1格，第2行2格，第3行1格)
    layout_template: str = ""

    # 布局描述文本 (给AI理解的结构化描述)
    layout_description: str = ""

    # 每个画格的简要描述列表
    panel_summaries: List[Dict[str, Any]] = field(default_factory=list)

    # 整合后的完整页面提示词（中文）
    full_page_prompt: str = ""

    # 负面提示词
    negative_prompt: str = ""

    # 页面宽高比 (漫画页通常是 3:4 或 2:3)
    aspect_ratio: str = "3:4"

    # 原始panel数据引用 (用于前端显示和兼容)
    panels: List["PanelPrompt"] = field(default_factory=list)

    # 角色立绘引用路径（整页使用的所有立绘）
    reference_image_paths: Optional[List[str]] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "page_number": self.page_number,
            "layout_template": self.layout_template,
            "layout_description": self.layout_description,
            "panel_summaries": self.panel_summaries,
            "full_page_prompt": self.full_page_prompt,
            "negative_prompt": self.negative_prompt,
            "aspect_ratio": self.aspect_ratio,
            "panels": [p.to_dict() for p in self.panels],
            "reference_image_paths": self.reference_image_paths,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PagePrompt":
        """从字典创建"""
        return cls(
            page_number=data.get("page_number", 1),
            layout_template=data.get("layout_template", ""),
            layout_description=data.get("layout_description", ""),
            panel_summaries=data.get("panel_summaries", []),
            full_page_prompt=data.get("full_page_prompt", ""),
            negative_prompt=data.get("negative_prompt", ""),
            aspect_ratio=data.get("aspect_ratio", "3:4"),
            panels=[PanelPrompt.from_dict(p) for p in data.get("panels", [])],
            reference_image_paths=data.get("reference_image_paths"),
        )


@dataclass
class PagePromptResult:
    """单页提示词结果（简化版）"""
    page_number: int
    panels: List[PanelPrompt] = field(default_factory=list)
    layout_description: str = ""

    # 间隙配置（单位：像素，由前端解释）
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
    def from_dict(cls, data: dict) -> "PagePromptResult":
        """从字典创建"""
        return cls(
            page_number=data.get("page_number", 1),
            panels=[PanelPrompt.from_dict(p) for p in data.get("panels", [])],
            layout_description=data.get("layout_description", ""),
            gutter_horizontal=data.get("gutter_horizontal", 8),
            gutter_vertical=data.get("gutter_vertical", 8),
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
    # 整页提示词列表（用于整页漫画生成）
    page_prompts: List[PagePrompt] = field(default_factory=list)

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
            "page_prompts": [pp.to_dict() for pp in self.page_prompts],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MangaPromptResult":
        """从字典创建"""
        pages = [PagePromptResult.from_dict(p) for p in data.get("pages", [])]
        page_prompts = [PagePrompt.from_dict(pp) for pp in data.get("page_prompts", [])]
        return cls(
            chapter_number=data.get("chapter_number", 1),
            style=data.get("style", "manga"),
            pages=pages,
            total_pages=data.get("total_pages", len(pages)),
            total_panels=data.get("total_panels", sum(len(p.panels) for p in pages)),
            character_profiles=data.get("character_profiles", {}),
            dialogue_language=data.get("dialogue_language", "chinese"),
            page_prompts=page_prompts,
        )

    def get_all_prompts(self) -> List[PanelPrompt]:
        """获取所有画格提示词"""
        prompts = []
        for page in self.pages:
            prompts.extend(page.panels)
        return prompts

    def get_page_prompt(self, page_number: int) -> Optional[PagePrompt]:
        """获取指定页码的整页提示词"""
        for pp in self.page_prompts:
            if pp.page_number == page_number:
                return pp
        return None


__all__ = [
    "PanelPrompt",
    "PagePrompt",
    "PagePromptResult",
    "MangaPromptResult",
]
