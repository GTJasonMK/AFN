"""
漫画排版数据模型

定义专业漫画排版的数据结构，支持传统漫画、条漫等多种格式。
参考专业漫画制作规范：
- 页面尺寸、出血线、安全区域
- 分格布局（大小、位置、形状）
- 阅读顺序和视觉引导
- 叙事节拍和框线语言
- 翻页钩子和视线引导
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LayoutType(str, Enum):
    """排版类型"""
    TRADITIONAL_MANGA = "traditional_manga"   # 传统漫画 (A4/B5, 右到左阅读)
    WEBTOON = "webtoon"                       # 条漫 (垂直滚动, 800px宽)
    COMIC = "comic"                           # 西方漫画 (左到右阅读)
    FOUR_PANEL = "four_panel"                 # 四格漫画


class PageSize(str, Enum):
    """页面尺寸"""
    A4 = "A4"           # 210x297mm (常见漫画尺寸)
    B5 = "B5"           # 182x257mm (日本漫画常用)
    A5 = "A5"           # 148x210mm (同人志常用)
    WEBTOON = "webtoon" # 800x自适应 (条漫)
    LETTER = "letter"   # 8.5x11inch (美国漫画)


class PanelShape(str, Enum):
    """格子形状"""
    RECTANGULAR = "rectangular"   # 矩形（最常见）
    DIAGONAL = "diagonal"         # 斜向（表现动感）
    IRREGULAR = "irregular"       # 不规则（特殊效果）
    BORDERLESS = "borderless"     # 无边框（强调重点）


class PanelImportance(str, Enum):
    """格子重要性（决定大小）"""
    HERO = "hero"           # 主角镜头/高潮场景 (占页面50%+)
    MAJOR = "major"         # 重要场景 (占页面25-40%)
    STANDARD = "standard"   # 普通场景 (占页面15-25%)
    MINOR = "minor"         # 次要场景/过渡 (占页面10-15%)
    MICRO = "micro"         # 微型镜头 (占页面3-8%)


class StoryBeat(str, Enum):
    """叙事节拍类型"""
    SETUP = "setup"               # 建立 - 展示环境和人物位置关系
    BUILD_UP = "build-up"         # 铺垫 - 逐渐累积张力
    TURN = "turn"                 # 转折 - 剧情转折点
    CLIMAX = "climax"             # 高潮 - 情感/动作爆发
    AFTERMATH = "aftermath"       # 余韵 - 消化情感的空间
    TRANSITION = "transition"     # 过渡 - 连接两个场景
    DIALOGUE = "dialogue"         # 对话 - 信息传递
    ACTION = "action"             # 动作 - 动态场景
    INTROSPECTION = "introspection"  # 内心 - 心理刻画
    FLASHBACK = "flashback"       # 闪回 - 回忆场景


class FrameStyle(str, Enum):
    """框线风格"""
    STANDARD = "standard"         # 标准直线框 - 中性、稳定
    BOLD = "bold"                 # 粗线框 - 强调、冲击
    THIN = "thin"                 # 细线框 - 轻柔、细腻
    ROUNDED = "rounded"           # 圆角框 - 温暖、柔和、回忆
    JAGGED = "jagged"             # 锯齿框 - 紧张、不安、恐惧
    DASHED = "dashed"             # 虚线框 - 虚幻、回忆、想象
    BORDERLESS = "borderless"     # 无边框 - 突破、自由、强调
    DIAGONAL = "diagonal"         # 斜向框 - 动感、失衡
    IRREGULAR = "irregular"       # 不规则框 - 混乱、情绪化


class BleedType(str, Enum):
    """出血类型"""
    NONE = "none"                 # 无出血
    FULL = "full"                 # 全出血（四边）
    TOP = "top"                   # 上出血
    BOTTOM = "bottom"             # 下出血
    LEFT = "left"                 # 左出血
    RIGHT = "right"               # 右出血
    HORIZONTAL = "horizontal"     # 左右出血
    VERTICAL = "vertical"         # 上下出血


class FlowDirection(str, Enum):
    """视线引导方向"""
    DOWN = "down"                 # 向下引导
    RIGHT = "right"               # 向右引导（LTR）
    LEFT = "left"                 # 向左引导（RTL）
    DOWN_LEFT = "down-left"       # 斜向左下
    DOWN_RIGHT = "down-right"     # 斜向右下
    CENTER_FOCUS = "center-focus" # 中心聚焦
    NEXT_PAGE = "next-page"       # 引向下一页


class PageFunction(str, Enum):
    """页面功能类型"""
    SETUP = "setup"               # 建立页 - 介绍场景/角色
    BUILD = "build"               # 铺垫页 - 逐步累积张力
    CLIMAX = "climax"             # 高潮页 - 情感/动作爆发
    AFTERMATH = "aftermath"       # 余韵页 - 消化情感
    TRANSITION = "transition"     # 过渡页 - 场景切换
    DIALOGUE = "dialogue"         # 对话页 - 信息传递
    ACTION = "action"             # 动作页 - 连续动作


class PageRhythm(str, Enum):
    """页面节奏"""
    SLOW = "slow"                 # 慢节奏 - 格子少，留白多
    MEDIUM = "medium"             # 中等节奏 - 标准排版
    FAST = "fast"                 # 快节奏 - 格子密集
    EXPLOSIVE = "explosive"       # 爆发式 - 大格子冲击


class CompositionHint(str, Enum):
    """构图提示（影响图片生成）"""
    EXTREME_CLOSEUP = "extreme close-up"  # 超特写（眼睛、细节）
    CLOSEUP = "close-up"                  # 特写（头部、表情）
    MEDIUM_CLOSEUP = "medium close-up"    # 中特写（头肩）
    MEDIUM_SHOT = "medium shot"           # 中景（上半身）
    MEDIUM_FULL = "medium full shot"      # 中全景（膝上）
    FULL_SHOT = "full shot"               # 全身
    WIDE_SHOT = "wide shot"               # 远景（环境+人物）
    ESTABLISHING = "establishing shot"    # 建立镜头（全景环境）
    BIRDS_EYE = "bird's eye view"         # 鸟瞰
    WORMS_EYE = "worm's eye view"         # 仰视
    OVER_SHOULDER = "over the shoulder"   # 过肩镜头
    POV = "point of view"                 # 主观视角


# ==================== 单格定义 ====================

class Panel(BaseModel):
    """单个格子（分镜）"""
    panel_id: int = Field(..., description="格子ID（页面内唯一）")
    scene_id: int = Field(..., description="关联的场景ID")

    # 位置和尺寸（相对值 0-1，相对于可用区域）
    x: float = Field(..., ge=-0.1, le=1.1, description="左上角X坐标（相对位置，出血可超出0-1）")
    y: float = Field(..., ge=-0.1, le=1.1, description="左上角Y坐标（相对位置，出血可超出0-1）")
    width: float = Field(..., gt=0, le=1.2, description="宽度（相对值，出血可超过1）")
    height: float = Field(..., gt=0, le=1.2, description="高度（相对值，出血可超过1）")

    # 格子属性
    shape: PanelShape = Field(default=PanelShape.RECTANGULAR, description="格子形状")
    importance: PanelImportance = Field(default=PanelImportance.STANDARD, description="重要性")
    bleed: BleedType = Field(default=BleedType.NONE, description="出血类型")

    # 叙事属性
    story_beat: StoryBeat = Field(default=StoryBeat.DIALOGUE, description="叙事节拍类型")
    frame_style: FrameStyle = Field(default=FrameStyle.STANDARD, description="框线风格")

    # 构图指导（传递给图片生成）
    composition: CompositionHint = Field(
        default=CompositionHint.MEDIUM_SHOT,
        description="构图类型"
    )
    camera_angle: Optional[str] = Field(default=None, description="镜头角度提示")

    # 视觉引导
    flow_direction: FlowDirection = Field(
        default=FlowDirection.DOWN,
        description="视线引导方向"
    )
    visual_focus: Optional[str] = Field(default=None, description="画面焦点描述")
    size_hint: Optional[str] = Field(default=None, description="大小和位置说明")

    # 排版标记
    z_index: int = Field(default=0, description="层级（用于重叠格子）")
    reading_order: int = Field(default=0, description="阅读顺序")


# ==================== 页面定义 ====================

class Page(BaseModel):
    """单页排版"""
    page_number: int = Field(..., description="页码")
    panels: List[Panel] = Field(default_factory=list, description="页面上的格子列表")

    # 页面属性
    is_spread: bool = Field(default=False, description="是否为跨页")
    is_chapter_start: bool = Field(default=False, description="是否为章节起始页")

    # 页面叙事属性
    page_function: PageFunction = Field(
        default=PageFunction.DIALOGUE,
        description="页面功能类型"
    )
    page_rhythm: PageRhythm = Field(
        default=PageRhythm.MEDIUM,
        description="页面节奏"
    )
    page_note: Optional[str] = Field(default=None, description="页面设计说明")
    page_turn_hook: Optional[str] = Field(default=None, description="翻页钩子设计说明")

    # 页面留白（gutter）
    gutter_h: float = Field(default=0.02, description="格子间水平间距（相对值）")
    gutter_v: float = Field(default=0.03, description="格子间垂直间距（相对值）")


# ==================== 条漫段落定义 ====================

class WebtoonSegment(BaseModel):
    """条漫段落（一个场景在条漫中的展示）"""
    scene_id: int = Field(..., description="关联的场景ID")
    height_ratio: float = Field(default=1.0, description="高度比例（相对于标准高度）")
    composition: CompositionHint = Field(default=CompositionHint.MEDIUM_SHOT)
    story_beat: StoryBeat = Field(default=StoryBeat.DIALOGUE, description="叙事节拍类型")

    # 特效
    background_extend: bool = Field(default=False, description="背景是否延伸到段落边缘")
    add_spacing_before: float = Field(default=0, description="前置留白（像素）")
    add_spacing_after: float = Field(default=50, description="后置留白（像素）")


# ==================== 场景构图指南 ====================

class SceneCompositionGuide(BaseModel):
    """场景构图指南"""
    recommended_composition: CompositionHint = Field(
        default=CompositionHint.MEDIUM_SHOT,
        description="推荐构图"
    )
    camera_angle: Optional[str] = Field(default=None, description="镜头角度")
    framing_note: Optional[str] = Field(default=None, description="取景说明")
    lighting_suggestion: Optional[str] = Field(default=None, description="光线建议")
    emotion_keywords: List[str] = Field(default_factory=list, description="情感关键词")


# ==================== 节奏统计 ====================

class RhythmSummary(BaseModel):
    """排版节奏统计"""
    total_scenes: int = Field(default=0, description="总场景数")
    hero_panels: int = Field(default=0, description="hero级格子数")
    major_panels: int = Field(default=0, description="major级格子数")
    standard_panels: int = Field(default=0, description="standard级格子数")
    minor_panels: int = Field(default=0, description="minor级格子数")
    micro_panels: int = Field(default=0, description="micro级格子数")
    average_panels_per_page: float = Field(default=0, description="每页平均格子数")
    climax_pages: List[int] = Field(default_factory=list, description="高潮页码列表")
    breathing_pages: List[int] = Field(default_factory=list, description="呼吸/留白页码列表")


# ==================== 整体排版定义 ====================

class MangaLayout(BaseModel):
    """漫画整体排版方案"""
    layout_type: LayoutType = Field(..., description="排版类型")
    page_size: PageSize = Field(default=PageSize.A4, description="页面尺寸")

    # 阅读方向
    reading_direction: str = Field(
        default="ltr",
        description="阅读方向: ltr(左到右), rtl(右到左)"
    )

    # 整体节奏策略
    pacing_strategy: Optional[str] = Field(
        default=None,
        description="节奏策略说明，如'渐进式，前期铺垫，高潮爆发'"
    )
    layout_analysis: Optional[str] = Field(
        default=None,
        description="排版设计思路分析"
    )

    # 印刷规范（单位: mm）
    bleed_margin: float = Field(default=3.0, description="出血线距离(mm)")
    safe_margin: float = Field(default=5.0, description="安全区域距离(mm)")
    inner_margin: float = Field(default=15.0, description="内边距(mm)，书脊侧更大")

    # 传统漫画页面列表
    pages: List[Page] = Field(default_factory=list, description="页面列表（传统漫画用）")

    # 条漫段落列表
    segments: List[WebtoonSegment] = Field(
        default_factory=list,
        description="段落列表（条漫用）"
    )

    # 场景构图指南
    scene_composition_guide: Dict[str, SceneCompositionGuide] = Field(
        default_factory=dict,
        description="场景ID到构图指南的映射"
    )

    # 节奏统计
    rhythm_summary: Optional[RhythmSummary] = Field(
        default=None,
        description="排版节奏统计"
    )

    # 元数据
    total_pages: int = Field(default=0, description="总页数")
    total_panels: int = Field(default=0, description="总格数")
    aspect_ratio: str = Field(default="3:4", description="默认格子宽高比")


# ==================== 排版请求/结果 ====================

class LayoutGenerationRequest(BaseModel):
    """排版生成请求"""
    layout_type: LayoutType = Field(default=LayoutType.TRADITIONAL_MANGA)
    page_size: PageSize = Field(default=PageSize.A4)
    target_pages: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="目标页数（None则自动计算）"
    )
    panels_per_page: int = Field(
        default=6,
        ge=1,
        le=12,
        description="每页平均格数"
    )
    reading_direction: str = Field(default="ltr")

    # 高级选项
    emphasis_scenes: List[int] = Field(
        default_factory=list,
        description="需要强调的场景ID（会分配更大格子）"
    )
    action_scenes: List[int] = Field(
        default_factory=list,
        description="动作场景ID（会使用动感排版）"
    )


class LayoutGenerationResult(BaseModel):
    """排版生成结果"""
    success: bool = Field(default=True)
    layout: Optional[MangaLayout] = Field(default=None)
    scene_panel_mapping: Dict[int, List[int]] = Field(
        default_factory=dict,
        description="场景ID到格子ID的映射"
    )
    error_message: Optional[str] = Field(default=None)


# ==================== 页面尺寸常量 ====================

PAGE_DIMENSIONS = {
    PageSize.A4: {"width": 210, "height": 297, "dpi": 300},
    PageSize.B5: {"width": 182, "height": 257, "dpi": 300},
    PageSize.A5: {"width": 148, "height": 210, "dpi": 300},
    PageSize.LETTER: {"width": 216, "height": 279, "dpi": 300},
    PageSize.WEBTOON: {"width": 800, "height": 1280, "dpi": 72},  # 像素
}


# ==================== 预设排版模板 ====================

# 6格标准排版（2列3行）
TEMPLATE_6_PANEL = [
    {"x": 0, "y": 0, "width": 0.48, "height": 0.32},
    {"x": 0.52, "y": 0, "width": 0.48, "height": 0.32},
    {"x": 0, "y": 0.34, "width": 0.48, "height": 0.32},
    {"x": 0.52, "y": 0.34, "width": 0.48, "height": 0.32},
    {"x": 0, "y": 0.68, "width": 0.48, "height": 0.32},
    {"x": 0.52, "y": 0.68, "width": 0.48, "height": 0.32},
]

# 5格标准排版（上2下3）
TEMPLATE_5_PANEL = [
    {"x": 0, "y": 0, "width": 0.48, "height": 0.38},
    {"x": 0.52, "y": 0, "width": 0.48, "height": 0.38},
    {"x": 0, "y": 0.42, "width": 0.32, "height": 0.58},
    {"x": 0.34, "y": 0.42, "width": 0.32, "height": 0.58},
    {"x": 0.68, "y": 0.42, "width": 0.32, "height": 0.58},
]

# 4格标准排版（2x2）
TEMPLATE_4_PANEL = [
    {"x": 0, "y": 0, "width": 0.48, "height": 0.48},
    {"x": 0.52, "y": 0, "width": 0.48, "height": 0.48},
    {"x": 0, "y": 0.52, "width": 0.48, "height": 0.48},
    {"x": 0.52, "y": 0.52, "width": 0.48, "height": 0.48},
]

# 主角镜头排版（1大2小）
TEMPLATE_HERO_PANEL = [
    {"x": 0, "y": 0, "width": 1.0, "height": 0.6, "importance": "hero"},
    {"x": 0, "y": 0.64, "width": 0.48, "height": 0.36},
    {"x": 0.52, "y": 0.64, "width": 0.48, "height": 0.36},
]

# 动作场景排版（斜向分割）
TEMPLATE_ACTION_PANEL = [
    {"x": 0, "y": 0, "width": 0.55, "height": 0.45, "shape": "diagonal"},
    {"x": 0.45, "y": 0.35, "width": 0.55, "height": 0.45, "shape": "diagonal"},
    {"x": 0, "y": 0.7, "width": 1.0, "height": 0.3},
]

LAYOUT_TEMPLATES = {
    "6_panel": TEMPLATE_6_PANEL,
    "5_panel": TEMPLATE_5_PANEL,
    "4_panel": TEMPLATE_4_PANEL,
    "hero": TEMPLATE_HERO_PANEL,
    "action": TEMPLATE_ACTION_PANEL,
}
