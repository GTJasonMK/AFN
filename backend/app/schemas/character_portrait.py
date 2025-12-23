"""
角色立绘 Schema

定义角色立绘的请求和响应模型。
"""

from datetime import datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, Field


# 立绘风格类型
PortraitStyle = Literal["anime", "manga", "realistic"]


class CharacterPortraitBase(BaseModel):
    """角色立绘基础模型"""

    character_name: str = Field(..., description="角色名称", max_length=100)
    character_description: Optional[str] = Field(default=None, description="角色外貌描述")
    style: PortraitStyle = Field(default="anime", description="立绘风格: anime/manga/realistic")
    custom_prompt: Optional[str] = Field(default=None, description="用户自定义提示词")


class GeneratePortraitRequest(BaseModel):
    """生成角色立绘请求"""

    character_name: str = Field(..., description="角色名称")
    character_description: Optional[str] = Field(default=None, description="角色外貌描述（如不提供则从蓝图获取）")
    style: PortraitStyle = Field(default="anime", description="立绘风格")
    custom_prompt: Optional[str] = Field(default=None, description="用户自定义提示词（追加到自动生成的提示词后）")


class RegeneratePortraitRequest(BaseModel):
    """重新生成立绘请求"""

    style: Optional[PortraitStyle] = Field(default=None, description="新的风格（可选，不提供则使用原风格）")
    custom_prompt: Optional[str] = Field(default=None, description="新的自定义提示词（可选）")


class CharacterPortraitResponse(BaseModel):
    """角色立绘响应模型"""

    id: str
    project_id: str
    character_name: str
    character_description: Optional[str] = None
    style: str
    prompt: Optional[str] = None  # 实际使用的完整提示词
    custom_prompt: Optional[str] = None
    image_path: Optional[str] = None
    image_url: Optional[str] = None  # 访问URL
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    model_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_url(cls, portrait, base_url: str = "/api/image-generation/files"):
        """从ORM对象创建，并生成图片访问URL"""
        image_url = None
        if portrait.image_path:
            # 确保URL使用正斜杠
            url_path = portrait.image_path.replace("\\", "/")
            image_url = f"{base_url}/{url_path}"

        return cls(
            id=portrait.id,
            project_id=portrait.project_id,
            character_name=portrait.character_name,
            character_description=portrait.character_description,
            style=portrait.style,
            prompt=portrait.prompt,
            custom_prompt=portrait.custom_prompt,
            image_path=portrait.image_path,
            image_url=image_url,
            file_name=portrait.file_name,
            file_size=portrait.file_size,
            width=portrait.width,
            height=portrait.height,
            model_name=portrait.model_name,
            is_active=portrait.is_active,
            created_at=portrait.created_at,
            updated_at=portrait.updated_at,
        )


class CharacterPortraitListResponse(BaseModel):
    """角色立绘列表响应"""

    portraits: List[CharacterPortraitResponse]
    total: int


class GeneratePortraitResponse(BaseModel):
    """生成立绘响应"""

    success: bool
    portrait: Optional[CharacterPortraitResponse] = None
    error_message: Optional[str] = None


class PortraitStyleInfo(BaseModel):
    """立绘风格信息"""

    style: str
    name: str
    description: str
    prompt_prefix: str  # 添加到提示词前的风格描述


# 预定义的立绘风格信息
PORTRAIT_STYLES = [
    PortraitStyleInfo(
        style="anime",
        name="动漫风格",
        description="日系动漫风格，色彩鲜艳，线条流畅",
        prompt_prefix="anime style, vibrant colors, clean lines, high quality illustration",
    ),
    PortraitStyleInfo(
        style="manga",
        name="漫画风格",
        description="黑白漫画风格，强调线条和阴影",
        prompt_prefix="manga style, black and white, detailed linework, dramatic shading",
    ),
    PortraitStyleInfo(
        style="realistic",
        name="写实风格",
        description="写实风格，接近真人照片效果",
        prompt_prefix="realistic portrait, highly detailed, photorealistic, professional lighting",
    ),
]


def get_style_prompt_prefix(style: str) -> str:
    """获取风格对应的提示词前缀"""
    for style_info in PORTRAIT_STYLES:
        if style_info.style == style:
            return style_info.prompt_prefix
    return PORTRAIT_STYLES[0].prompt_prefix  # 默认返回anime风格
