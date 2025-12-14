"""
图片生成数据模型

定义请求、响应、配置等数据结构。
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class ProviderType(str, Enum):
    """图片生成服务提供商类型"""
    OPENAI_COMPATIBLE = "openai_compatible"  # OpenAI兼容接口（DALL-E、nano-banana-pro等）
    STABILITY = "stability"  # Stability AI
    MIDJOURNEY = "midjourney"  # Midjourney API
    COMFYUI = "comfyui"  # 本地ComfyUI


class ImageStyle(str, Enum):
    """图片风格"""
    NONE = "none"  # 无风格
    ANIME = "anime"  # 动漫卡通
    REALISTIC = "realistic"  # 写实摄影
    OIL_PAINTING = "oil_painting"  # 油画艺术
    WATERCOLOR = "watercolor"  # 水彩插画
    RENDER_3D = "render_3d"  # 3D渲染
    PIXEL = "pixel"  # 像素艺术
    CYBERPUNK = "cyberpunk"  # 赛博朋克
    MINIMALIST = "minimalist"  # 极简主义
    MANGA = "manga"  # 日式漫画


class AspectRatio(str, Enum):
    """宽高比"""
    RATIO_1_1 = "1:1"
    RATIO_16_9 = "16:9"
    RATIO_9_16 = "9:16"
    RATIO_4_3 = "4:3"
    RATIO_3_4 = "3:4"
    RATIO_3_2 = "3:2"
    RATIO_2_3 = "2:3"
    RATIO_21_9 = "21:9"


class QualityPreset(str, Enum):
    """质量预设"""
    DRAFT = "draft"  # 草稿
    STANDARD = "standard"  # 标准
    HIGH = "high"  # 高质量


# ==================== 配置相关 ====================

class ImageConfigBase(BaseModel):
    """图片生成配置基类"""
    config_name: str = Field(..., description="配置名称", max_length=100)
    provider_type: ProviderType = Field(default=ProviderType.OPENAI_COMPATIBLE, description="服务提供商类型")
    api_base_url: Optional[str] = Field(default=None, description="API基础URL")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    model_name: Optional[str] = Field(default="nano-banana-pro", description="模型名称")
    default_style: Optional[str] = Field(default="anime", description="默认风格")
    default_ratio: Optional[str] = Field(default="16:9", description="默认宽高比")
    default_resolution: Optional[str] = Field(default="1K", description="默认分辨率")
    default_quality: Optional[str] = Field(default="standard", description="默认质量")
    extra_params: Optional[Dict[str, Any]] = Field(default=None, description="额外参数")


class ImageConfigCreate(ImageConfigBase):
    """创建图片生成配置"""
    pass


class ImageConfigUpdate(BaseModel):
    """更新图片生成配置"""
    config_name: Optional[str] = Field(default=None, max_length=100)
    provider_type: Optional[ProviderType] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    default_style: Optional[str] = None
    default_ratio: Optional[str] = None
    default_resolution: Optional[str] = None
    default_quality: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None


class ImageConfigResponse(ImageConfigBase):
    """图片生成配置响应"""
    id: int
    is_active: bool = False
    is_verified: bool = False
    last_test_at: Optional[datetime] = None
    test_status: Optional[str] = None
    test_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 生成请求/响应 ====================

class ImageGenerationRequest(BaseModel):
    """图片生成请求"""
    prompt: str = Field(..., description="提示词（英文）")
    negative_prompt: Optional[str] = Field(default=None, description="负面提示词")
    style: Optional[str] = Field(default=None, description="风格")
    ratio: Optional[str] = Field(default="16:9", description="宽高比")
    resolution: Optional[str] = Field(default="1K", description="分辨率")
    quality: Optional[str] = Field(default="standard", description="质量预设")
    count: int = Field(default=1, ge=1, le=4, description="生成数量")
    seed: Optional[int] = Field(default=None, description="随机种子")


class GeneratedImageInfo(BaseModel):
    """生成的图片信息"""
    id: int
    file_name: str
    file_path: str
    url: str  # 访问URL
    width: Optional[int] = None
    height: Optional[int] = None
    prompt: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ImageGenerationResult(BaseModel):
    """图片生成结果"""
    success: bool
    images: List[GeneratedImageInfo] = Field(default_factory=list)
    error_message: Optional[str] = None
    generation_time: Optional[float] = None  # 生成耗时（秒）


# ==================== 图片管理 ====================

class SceneImagesResponse(BaseModel):
    """场景图片列表响应"""
    project_id: str
    chapter_number: int
    scene_id: int
    images: List[GeneratedImageInfo]
    total: int


class PDFExportRequest(BaseModel):
    """PDF导出请求"""
    project_id: str
    title: Optional[str] = Field(default=None, description="PDF标题")
    image_ids: List[int] = Field(..., description="要导出的图片ID列表")
    include_prompts: bool = Field(default=False, description="是否包含提示词")
    page_size: str = Field(default="A4", description="页面大小")
    images_per_page: int = Field(default=2, ge=1, le=4, description="每页图片数量")


class PDFExportResult(BaseModel):
    """PDF导出结果"""
    success: bool
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    error_message: Optional[str] = None


# ==================== 常量定义 ====================

# 风格映射（中文 -> 英文后缀）
STYLE_SUFFIXES = {
    "none": "",
    "anime": "anime cartoon style",
    "realistic": "realistic photography style",
    "oil_painting": "oil painting art style",
    "watercolor": "watercolor illustration style",
    "render_3d": "3D render style",
    "pixel": "pixel art style",
    "cyberpunk": "cyberpunk style",
    "minimalist": "minimalist style",
    "manga": "Japanese manga style, black and white ink drawing",
}

# 质量预设参数
QUALITY_PARAMS = {
    "draft": {"temperature": 0.9, "max_tokens": 2000},
    "standard": {"temperature": 0.7, "max_tokens": 4000},
    "high": {"temperature": 0.5, "max_tokens": 6000},
}

# 分辨率后缀
RESOLUTION_SUFFIXES = {
    "原始": "",
    "1K": ", high resolution 1K",
    "2K": ", high resolution 2K, detailed",
}

# 支持的模型列表
SUPPORTED_MODELS = {
    ProviderType.OPENAI_COMPATIBLE: [
        "nano-banana-pro",
        "dall-e-3",
        "dall-e-2",
        "gemini-2.5-flash",
        "gemini-3-pro-image-preview",
    ],
    ProviderType.STABILITY: [
        "stable-diffusion-xl-1024-v1-0",
        "stable-diffusion-v1-6",
    ],
    ProviderType.COMFYUI: [
        "custom",
    ],
}
