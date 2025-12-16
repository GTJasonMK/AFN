"""
漫画提示词数据模型

定义请求、响应、场景等数据结构。
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MangaStyle(str, Enum):
    """漫画风格"""
    MANGA = "manga"           # 日式漫画风格
    ANIME = "anime"           # 动漫风格
    COMIC = "comic"           # 西方漫画风格
    WEBTOON = "webtoon"       # 韩式条漫风格


class DialogueLanguage(str, Enum):
    """对话气泡文字语言"""
    CHINESE = "chinese"       # 中文
    JAPANESE = "japanese"     # 日文
    ENGLISH = "english"       # 英文
    KOREAN = "korean"         # 韩文
    NONE = "none"             # 不包含文字


class BubbleType(str, Enum):
    """对话气泡类型"""
    NORMAL = "normal"         # 普通对话气泡
    SHOUT = "shout"           # 大喊/激动（锯齿状气泡）
    WHISPER = "whisper"       # 低语/私语（虚线气泡）
    THOUGHT = "thought"       # 内心独白（云朵形气泡）
    NARRATION = "narration"   # 旁白叙述（矩形框）
    ELECTRONIC = "electronic" # 电子/电话声音（波浪形气泡）


class SoundEffectType(str, Enum):
    """音效文字类型"""
    ACTION = "action"         # 动作音效（砰、嗖、啪）
    IMPACT = "impact"         # 撞击音效（轰、咚、嘭）
    AMBIENT = "ambient"       # 环境音效（沙沙、滴答）
    EMOTIONAL = "emotional"   # 情感音效（咚咚心跳）
    VOCAL = "vocal"           # 人声音效（哼、啊）


class CompositionType(str, Enum):
    """构图类型"""
    CLOSE_UP = "close-up"           # 特写
    MEDIUM_SHOT = "medium shot"     # 中景
    FULL_SHOT = "full shot"         # 全景
    WIDE_SHOT = "wide shot"         # 远景
    BIRDS_EYE = "bird's eye view"   # 鸟瞰
    LOW_ANGLE = "low angle"         # 仰视
    HIGH_ANGLE = "high angle"       # 俯视


class DialogueItem(BaseModel):
    """对话气泡项"""
    speaker: str = Field(..., description="说话者角色名")
    text: str = Field(..., description="对话内容")
    bubble_type: str = Field(default="normal", description="气泡类型: normal/shout/whisper/thought/narration/electronic")
    position: str = Field(default="top-right", description="气泡位置: top-left/top-center/top-right/middle-left/middle-right/bottom-left/bottom-center/bottom-right")


class SoundEffectItem(BaseModel):
    """音效文字项"""
    text: str = Field(..., description="音效文字")
    type: str = Field(default="action", description="音效类型: action/impact/ambient/emotional/vocal")
    intensity: str = Field(default="medium", description="音效强度: small/medium/large")


class PanelInfo(BaseModel):
    """格子排版信息"""
    panel_id: int = Field(..., description="格子ID")
    page_number: int = Field(..., description="所在页码")
    importance: str = Field(default="standard", description="重要性: hero/major/standard/minor")
    x: float = Field(default=0, description="X坐标(0-1)")
    y: float = Field(default=0, description="Y坐标(0-1)")
    width: float = Field(default=0.5, description="宽度(0-1)")
    height: float = Field(default=0.5, description="高度(0-1)")
    aspect_ratio: str = Field(default="1:1", description="推荐宽高比")
    camera_angle: Optional[str] = Field(default=None, description="镜头角度")


class MangaScene(BaseModel):
    """单个漫画场景"""
    scene_id: int = Field(..., description="场景序号")
    scene_summary: str = Field(..., description="场景简述（中文）")
    original_text: str = Field(..., description="对应的原文片段")
    characters: List[str] = Field(default_factory=list, description="出场角色")

    # 对话和文字元素
    dialogues: List[DialogueItem] = Field(default_factory=list, description="对话气泡列表")
    narration: Optional[str] = Field(default=None, description="旁白文字")
    sound_effects: List[SoundEffectItem] = Field(default_factory=list, description="音效文字列表")

    # 核心提示词
    prompt_en: str = Field(..., description="英文提示词（用于AI生成）")
    prompt_zh: str = Field(..., description="中文说明（供用户理解）")
    negative_prompt: str = Field(default="", description="负面提示词")

    # 附加信息
    style_tags: List[str] = Field(default_factory=list, description="风格标签")
    composition: str = Field(default="medium shot", description="构图建议")
    emotion: str = Field(default="", description="情感基调")
    lighting: str = Field(default="", description="光线描述")

    # 排版信息（由LayoutService生成）
    panel_info: Optional[PanelInfo] = Field(default=None, description="格子排版信息")


class LayoutInfo(BaseModel):
    """排版信息摘要"""
    layout_type: str = Field(default="traditional_manga", description="排版类型")
    page_size: str = Field(default="A4", description="页面尺寸")
    reading_direction: str = Field(default="ltr", description="阅读方向")
    total_pages: int = Field(default=0, description="总页数")
    total_panels: int = Field(default=0, description="总格数")
    layout_analysis: str = Field(default="", description="排版设计思路")


class MangaPromptResult(BaseModel):
    """章节漫画提示词结果"""
    chapter_number: int = Field(..., description="章节号")
    character_profiles: Dict[str, str] = Field(
        default_factory=dict,
        description="角色外观描述库（确保一致性）"
    )
    scenes: List[MangaScene] = Field(default_factory=list, description="场景列表")
    style_guide: str = Field(default="", description="整体风格指南")

    # 元数据
    total_scenes: int = Field(default=0, description="总场景数")
    style: MangaStyle = Field(default=MangaStyle.MANGA, description="选用的风格")

    # 排版信息
    layout_info: Optional[LayoutInfo] = Field(default=None, description="排版信息")

    # 版本警告（当漫画提示词基于旧版本正文生成时）
    version_mismatch_warning: Optional[str] = Field(
        default=None,
        description="版本不匹配警告，提示用户漫画提示词可能需要重新生成"
    )


class MangaPromptRequest(BaseModel):
    """生成漫画提示词的请求"""
    style: MangaStyle = Field(default=MangaStyle.MANGA, description="漫画风格")
    scene_count: Optional[int] = Field(
        default=None,
        ge=5,
        le=20,
        description="目标场景数量，为None时由LLM自动决定"
    )
    include_negative_prompt: bool = Field(default=True, description="是否生成负面提示词")

    # 对话和文字选项
    dialogue_language: DialogueLanguage = Field(
        default=DialogueLanguage.CHINESE,
        description="对话气泡中文字的语言"
    )
    include_dialogue: bool = Field(default=True, description="是否在画面中包含对话气泡")
    include_sound_effects: bool = Field(default=True, description="是否包含音效文字")


class SceneUpdateRequest(BaseModel):
    """更新单个场景的请求"""
    prompt_en: Optional[str] = Field(default=None, description="英文提示词")
    prompt_zh: Optional[str] = Field(default=None, description="中文说明")
    negative_prompt: Optional[str] = Field(default=None, description="负面提示词")
    composition: Optional[str] = Field(default=None, description="构图建议")
    emotion: Optional[str] = Field(default=None, description="情感基调")
    lighting: Optional[str] = Field(default=None, description="光线描述")


class CharacterAppearance(BaseModel):
    """角色外观描述（用于存储在BlueprintCharacter.extra中）"""
    age: Optional[str] = Field(default=None, description="年龄")
    gender: Optional[str] = Field(default=None, description="性别")
    hair: Optional[str] = Field(default=None, description="发型发色")
    eyes: Optional[str] = Field(default=None, description="眼睛描述")
    build: Optional[str] = Field(default=None, description="体型")
    clothing: Optional[str] = Field(default=None, description="服装")
    features: Optional[str] = Field(default=None, description="特征（疤痕、饰品等）")

    def to_prompt(self, name: str) -> str:
        """转换为提示词格式"""
        parts = [name]
        if self.age:
            parts.append(self.age)
        if self.gender:
            parts.append(self.gender)
        if self.hair:
            parts.append(self.hair)
        if self.eyes:
            parts.append(self.eyes)
        if self.build:
            parts.append(self.build)
        if self.clothing:
            parts.append(f"wearing {self.clothing}")
        if self.features:
            parts.append(self.features)
        return ", ".join(parts)
