"""
漫画提示词数据模型

定义请求、响应、场景等数据结构。
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field


class MangaStyle(str, Enum):
    """漫画风格"""
    MANGA = "manga"           # 日式漫画风格
    ANIME = "anime"           # 动漫风格
    COMIC = "comic"           # 西方漫画风格
    WEBTOON = "webtoon"       # 韩式条漫风格


class CompositionType(str, Enum):
    """构图类型"""
    CLOSE_UP = "close-up"           # 特写
    MEDIUM_SHOT = "medium shot"     # 中景
    FULL_SHOT = "full shot"         # 全景
    WIDE_SHOT = "wide shot"         # 远景
    BIRDS_EYE = "bird's eye view"   # 鸟瞰
    LOW_ANGLE = "low angle"         # 仰视
    HIGH_ANGLE = "high angle"       # 俯视


class MangaScene(BaseModel):
    """单个漫画场景"""
    scene_id: int = Field(..., description="场景序号")
    scene_summary: str = Field(..., description="场景简述（中文）")
    original_text: str = Field(..., description="对应的原文片段")
    characters: List[str] = Field(default_factory=list, description="出场角色")

    # 核心提示词
    prompt_en: str = Field(..., description="英文提示词（用于AI生成）")
    prompt_zh: str = Field(..., description="中文说明（供用户理解）")
    negative_prompt: str = Field(default="", description="负面提示词")

    # 附加信息
    style_tags: List[str] = Field(default_factory=list, description="风格标签")
    composition: str = Field(default="medium shot", description="构图建议")
    emotion: str = Field(default="", description="情感基调")
    lighting: str = Field(default="", description="光线描述")


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
