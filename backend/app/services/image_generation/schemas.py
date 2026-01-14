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
    RATIO_3_1 = "3:1"   # 超宽画格（悬念条）
    RATIO_6_1 = "6:1"   # 极宽画格（全景条）
    RATIO_1_3 = "1:3"   # 竖长画格
    RATIO_2_1 = "2:1"   # 宽幅画格


# 宽高比到像素尺寸的映射
# 基于AI图片生成服务实际支持的固定规格（5种）
# 注意：大多数AI服务只支持有限的固定尺寸，请求其他尺寸会被自动调整到最接近的支持尺寸
ASPECT_RATIO_TO_SIZE = {
    # === AI实际支持的5种固定规格 ===
    "1:1": (1024, 1024),     # 正方形 - 特写、头像
    "16:9": (1376, 768),     # 宽屏横向 - 远景、场景建立
    "9:16": (768, 1376),     # 宽屏竖向 - 纵向动作、全身
    "4:3": (1200, 896),      # 标准横向 - 中景、对话
    "3:4": (896, 1200),      # 标准竖向 - 人物全身
    # === 以下比例会被AI映射到最接近的支持尺寸 ===
    "3:2": (1200, 896),      # 映射到 4:3
    "2:3": (896, 1200),      # 映射到 3:4
    "21:9": (1376, 768),     # 映射到 16:9（AI不支持超宽）
    "3:1": (1376, 768),      # 映射到 16:9（AI不支持超宽）
    "6:1": (1376, 768),      # 映射到 16:9（AI不支持极宽）
    "1:3": (768, 1376),      # 映射到 9:16
    "2:1": (1376, 768),      # 映射到 16:9
}


def get_size_for_ratio(ratio: str, base_resolution: str = "1K") -> tuple:
    """
    根据宽高比和基础分辨率获取像素尺寸

    Args:
        ratio: 宽高比字符串，如 "16:9"
        base_resolution: 基础分辨率 "1K" 或 "2K"

    Returns:
        (width, height) 元组
    """
    # 获取基础尺寸
    size = ASPECT_RATIO_TO_SIZE.get(ratio, (1024, 1024))

    # 如果是2K分辨率，尺寸翻倍
    if base_resolution == "2K":
        size = (size[0] * 2, size[1] * 2)

    return size


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
    # 版本追溯：记录图片基于哪个章节版本生成
    chapter_version_id: Optional[int] = Field(default=None, description="章节版本ID，用于版本追溯")
    # 画格ID：精确标识图片属于哪个画格
    panel_id: Optional[str] = Field(default=None, description="画格ID，格式如 scene1_page1_panel1")
    # img2img 参考图支持
    reference_image_paths: Optional[List[str]] = Field(default=None, description="参考图片路径列表（用于img2img）")
    reference_strength: float = Field(default=0.7, ge=0.0, le=1.0, description="参考图影响强度（0.0-1.0）")

    # ==================== 漫画画格元数据 ====================
    # 对话相关
    dialogue: Optional[str] = Field(default=None, description="对话内容")
    dialogue_speaker: Optional[str] = Field(default=None, description="对话说话者")
    dialogue_bubble_type: Optional[str] = Field(default=None, description="气泡类型: normal/shout/whisper/thought")
    dialogue_emotion: Optional[str] = Field(default=None, description="说话情绪")
    dialogue_position: Optional[str] = Field(default=None, description="气泡位置: top-right/top-left/bottom-center等")
    # 旁白相关
    narration: Optional[str] = Field(default=None, description="旁白内容")
    narration_position: Optional[str] = Field(default=None, description="旁白位置: top/bottom/left/right")
    # 音效相关
    sound_effects: Optional[List[str]] = Field(default=None, description="音效列表")
    sound_effect_details: Optional[List[Dict[str, Any]]] = Field(default=None, description="详细音效信息（含类型、强度）")

    # ==================== 画格视觉元数据 ====================
    composition: Optional[str] = Field(default=None, description="构图: wide shot/medium shot/close-up等")
    camera_angle: Optional[str] = Field(default=None, description="镜头角度: eye level/low angle/high angle/dutch angle等")
    is_key_panel: bool = Field(default=False, description="是否为关键画格")
    characters: Optional[List[str]] = Field(default=None, description="角色列表")
    lighting: Optional[str] = Field(default=None, description="光线描述")
    atmosphere: Optional[str] = Field(default=None, description="氛围描述")
    key_visual_elements: Optional[List[str]] = Field(default=None, description="关键视觉元素")

    # ==================== 语言设置 ====================
    dialogue_language: Optional[str] = Field(default=None, description="对话/文字语言: chinese/japanese/english/korean")


class PageImageGenerationRequest(BaseModel):
    """整页漫画图片生成请求

    用于生成带分格布局的整页漫画图片，AI直接画出包含多个panel的完整页面。
    """
    # 页面级提示词（由 PromptBuilder.build_page_prompt() 生成）
    full_page_prompt: str = Field(..., description="整页漫画提示词")
    negative_prompt: Optional[str] = Field(default=None, description="负面提示词")

    # 布局信息
    layout_template: str = Field(default="", description="布局模板名，如 3row_1x2x1")
    layout_description: str = Field(default="", description="布局描述文本")

    # 图片参数
    ratio: str = Field(default="3:4", description="页面宽高比（漫画页标准比例）")
    resolution: str = Field(default="2K", description="分辨率，整页建议2K")
    style: Optional[str] = Field(default="manga", description="风格")

    # 版本追溯
    chapter_version_id: Optional[int] = Field(default=None, description="章节版本ID")

    # 参考图（角色立绘等）
    reference_image_paths: Optional[List[str]] = Field(default=None, description="参考图片路径列表")
    reference_strength: float = Field(default=0.5, ge=0.0, le=1.0, description="参考图影响强度")

    # 每个画格的简要信息（用于后续处理，如PDF导出时的区域裁切）
    panel_summaries: Optional[List[Dict[str, Any]]] = Field(default=None, description="画格简要信息列表")

    # 语言设置
    dialogue_language: Optional[str] = Field(default="chinese", description="对话/文字语言")


class GeneratedImageInfo(BaseModel):
    """生成的图片信息"""
    id: int
    file_name: str
    file_path: str
    url: str  # 访问URL
    scene_id: int  # 场景ID
    panel_id: Optional[str] = None  # 画格ID
    image_type: str = "panel"  # 图片类型: "panel"(单画格) 或 "page"(整页)
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
    download_url: Optional[str] = None  # 下载URL
    error_message: Optional[str] = None


class ChapterMangaPDFRequest(BaseModel):
    """章节漫画PDF生成请求"""
    title: Optional[str] = Field(default=None, description="PDF标题")
    include_prompts: bool = Field(default=False, description="是否包含提示词")
    page_size: str = Field(default="A4", description="页面大小: A4, A3, Letter")
    layout: str = Field(default="full", description="布局: full(全页), manga(漫画分格)")
    # 版本过滤：仅导出当前版本的图片
    chapter_version_id: Optional[int] = Field(default=None, description="章节版本ID，用于过滤特定版本的图片")


class ChapterMangaPDFResponse(BaseModel):
    """章节漫画PDF响应"""
    success: bool
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    download_url: Optional[str] = None
    page_count: int = 0
    error_message: Optional[str] = None


# ==================== 常量定义 ====================

# 风格映射（风格标识 -> 英文后缀）
# 注意：强调线稿风格，避免厚涂/塑料感
# 这是回退方案：当LLM生成的提示词已包含风格关键词时，不会添加这些后缀
STYLE_SUFFIXES = {
    "none": "",
    "anime": "anime style, clean line art, cel shading, flat colors",
    "realistic": "realistic photography style",
    "oil_painting": "oil painting art style",
    "watercolor": "watercolor illustration style",
    "render_3d": "3D render style",
    "pixel": "pixel art style",
    "cyberpunk": "cyberpunk style",
    "minimalist": "minimalist style",
    "manga": "manga style, clean bold outlines, ink drawing, screentone shading, black and white, high contrast",
    "manga_color": "manga style, clean line art, flat cel shading, minimal highlights, vibrant colors",
    "comic": "comic book style, strong black outlines, flat colors, graphic novel art",
    "webtoon": "webtoon style, clean digital lines, soft cel shading, minimal rendering",
}

# 风格检测关键词：用于判断提示词是否已经包含风格描述
# 如果提示词包含这些关键词之一，则跳过风格后缀添加（LLM优先）
STYLE_DETECTION_KEYWORDS = [
    "manga style", "anime style", "comic style", "webtoon style",
    "clean line art", "cel shading", "ink drawing", "screentone",
    "realistic photography", "oil painting", "watercolor illustration",
    "3d render", "pixel art", "cyberpunk style", "minimalist style",
]


def has_style_keywords(prompt: str) -> bool:
    """
    检测提示词是否已包含风格关键词

    如果返回True，表示提示词是由LLM智能生成的，已包含风格信息，
    不需要再添加STYLE_SUFFIXES中的后缀。

    Args:
        prompt: 提示词文本

    Returns:
        bool: 是否包含风格关键词
    """
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in STYLE_DETECTION_KEYWORDS)

# 漫画专用默认负面提示词（中文，自然语言）
DEFAULT_MANGA_NEGATIVE_PROMPT = (
    "禁止出现以下问题："
    "模糊低质量、像素化、水印签名、"
    "塑料感皮肤、僵硬表情、呆滞眼神、"
    "解剖错误、比例失调、手指变形、多余肢体、"
    "3D渲染风格、过度真实、厚涂油画质感、"
    "文字错误乱码、"
    "面部变形不对称"
)

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


# ==================== 导入导出相关 ====================

class ImageConfigExport(BaseModel):
    """导出的图片配置数据（不包含运行时状态）。"""

    config_name: str
    provider_type: str
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    default_style: Optional[str] = None
    default_ratio: Optional[str] = None
    default_resolution: Optional[str] = None
    default_quality: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None


class ImageConfigExportData(BaseModel):
    """导出文件的完整数据结构。"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="image", description="导出类型")
    configs: List[ImageConfigExport] = Field(..., description="配置列表")


class ImageConfigImportResult(BaseModel):
    """导入结果。"""

    success: bool
    message: str
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    details: List[str] = []
