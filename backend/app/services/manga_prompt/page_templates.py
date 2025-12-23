"""
漫画页面模板系统

基于专业漫画分镜实践设计的页面布局模板。
每个模板定义了画格的位置、大小、用途和视觉特性。

核心概念：
- PageTemplate: 页面布局模板，包含多个画格槽位
- PanelSlot: 画格槽位，定义位置、形状、用途
- 模板选择基于场景的情感类型和叙事需求
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class PanelShape(str, Enum):
    """画格形状"""
    RECTANGLE = "rectangle"  # 标准矩形
    DIAGONAL_LEFT = "diagonal_left"  # 左斜切
    DIAGONAL_RIGHT = "diagonal_right"  # 右斜切
    BORDERLESS = "borderless"  # 无边框（梦幻/回忆）
    ROUNDED = "rounded"  # 圆角（柔和场景）
    JAGGED = "jagged"  # 锯齿边（冲击/爆炸）
    IRREGULAR = "irregular"  # 不规则多边形


class PanelPurpose(str, Enum):
    """画格用途/功能"""
    ESTABLISHING = "establishing"  # 环境建立镜头
    ACTION = "action"  # 动作场景
    REACTION = "reaction"  # 角色反应
    CLOSEUP = "closeup"  # 特写
    DETAIL = "detail"  # 细节（手、物品等）
    EMOTION = "emotion"  # 情感表达
    TRANSITION = "transition"  # 转场
    EMPHASIS = "emphasis"  # 强调/冲击


class SceneMood(str, Enum):
    """场景情感类型"""
    CALM = "calm"  # 平静日常
    TENSION = "tension"  # 紧张对峙
    ACTION = "action"  # 动作战斗
    EMOTIONAL = "emotional"  # 情感爆发
    MYSTERY = "mystery"  # 悬疑神秘
    COMEDY = "comedy"  # 轻松搞笑
    DRAMATIC = "dramatic"  # 戏剧性转折
    ROMANTIC = "romantic"  # 浪漫温馨
    HORROR = "horror"  # 恐怖惊悚
    FLASHBACK = "flashback"  # 回忆/闪回


class DialogueBubbleType(str, Enum):
    """对话气泡类型"""
    NORMAL = "normal"  # 普通对话 - 圆形边框
    SHOUT = "shout"  # 大喊/激动 - 锯齿边框
    WHISPER = "whisper"  # 低语/私语 - 虚线边框
    THOUGHT = "thought"  # 内心独白 - 云朵形状
    NARRATION = "narration"  # 旁白叙述 - 矩形方框
    ELECTRONIC = "electronic"  # 电话/电子设备 - 波浪边框


class SoundEffectType(str, Enum):
    """音效类型"""
    ACTION = "action"  # 动作音效 (砰、嗖、啪)
    IMPACT = "impact"  # 撞击音效 (轰、咚、嘭)
    AMBIENT = "ambient"  # 环境音效 (沙沙、滴答、呼呼)
    EMOTIONAL = "emotional"  # 情感音效 (咚咚心跳、嘶抽气)
    VOCAL = "vocal"  # 人声音效 (哼、啊、嘶)


class SoundEffectIntensity(str, Enum):
    """音效强度"""
    SMALL = "small"  # 次要音效，画面边缘，小字体
    MEDIUM = "medium"  # 中等音效，适当位置，中等字体
    LARGE = "large"  # 主要音效，显眼位置，大字体


@dataclass
class SoundEffectInfo:
    """
    音效信息

    包含音效的文字、类型、强度和位置信息
    """
    text: str  # 音效文字 (砰、嗖、咚等)
    effect_type: SoundEffectType = SoundEffectType.ACTION
    intensity: SoundEffectIntensity = SoundEffectIntensity.MEDIUM
    position: str = ""  # 在画面中的位置描述


@dataclass
class DialogueInfo:
    """
    对话信息

    包含对话的文字、说话者、气泡类型和位置信息
    """
    text: str  # 对话内容
    speaker: str = ""  # 说话者
    bubble_type: DialogueBubbleType = DialogueBubbleType.NORMAL
    position: str = "top-right"  # 气泡位置 (top-right/top-left/bottom-center等)
    emotion: str = ""  # 说话时的情绪


@dataclass
class PanelSlot:
    """
    画格槽位定义

    坐标系统：以页面左上角为原点(0,0)，右下角为(1,1)
    """
    slot_id: int
    x: float  # 左上角x坐标 (0-1)
    y: float  # 左上角y坐标 (0-1)
    width: float  # 宽度 (0-1)
    height: float  # 高度 (0-1)
    shape: PanelShape = PanelShape.RECTANGLE
    purpose: PanelPurpose = PanelPurpose.ACTION

    # 视觉指导
    suggested_composition: str = "medium shot"  # 建议构图
    suggested_angle: str = "eye level"  # 建议视角
    aspect_ratio: str = "16:9"  # 建议生成比例

    # 特殊效果
    can_break_frame: bool = False  # 是否允许角色突破边框
    is_key_panel: bool = False  # 是否为关键画格（更大/更重要）

    # 边框样式
    border_weight: str = "normal"  # thin/normal/thick/none

    # 视线引导
    visual_flow_to: Optional[int] = None  # 视线指向的下一个画格ID


@dataclass
class PageTemplate:
    """
    页面布局模板

    每个模板定义了一种专业漫画常用的页面布局方式
    """
    id: str
    name: str
    name_zh: str
    description: str

    # 适用场景
    suitable_moods: List[SceneMood]

    # 画格槽位
    panel_slots: List[PanelSlot]

    # 页面特性
    reading_direction: str = "rtl"  # rtl(日漫)/ltr(美漫)
    gutter_style: str = "standard"  # tight/standard/loose

    # 叙事特性
    pacing: str = "normal"  # slow/normal/fast
    intensity: int = 5  # 1-10 视觉冲击强度

    # 使用建议
    usage_notes: str = ""

    def get_panel_count(self) -> int:
        """获取画格数量"""
        return len(self.panel_slots)

    def get_key_panels(self) -> List[PanelSlot]:
        """获取关键画格"""
        return [p for p in self.panel_slots if p.is_key_panel]


# ============================================================
# 预设页面模板
# ============================================================

# 模板1：标准三段式（日常对话、情节推进）
TEMPLATE_STANDARD_THREE_TIER = PageTemplate(
    id="standard_three_tier",
    name="Standard Three-Tier",
    name_zh="标准三段式",
    description="经典的三行布局，适合日常对话和情节推进。节奏稳定，阅读流畅。",
    suitable_moods=[SceneMood.CALM, SceneMood.TENSION, SceneMood.COMEDY],
    panel_slots=[
        # 第一行：两格
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=0.55, height=0.32,
            purpose=PanelPurpose.ESTABLISHING,
            suggested_composition="wide shot",
            suggested_angle="eye level",
            aspect_ratio="16:9",
            visual_flow_to=2
        ),
        PanelSlot(
            slot_id=2, x=0.57, y=0.0, width=0.43, height=0.32,
            purpose=PanelPurpose.REACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=3
        ),
        # 第二行：两格
        PanelSlot(
            slot_id=3, x=0.0, y=0.34, width=0.48, height=0.32,
            purpose=PanelPurpose.ACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=4
        ),
        PanelSlot(
            slot_id=4, x=0.50, y=0.34, width=0.50, height=0.32,
            purpose=PanelPurpose.REACTION,
            suggested_composition="medium close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=5
        ),
        # 第三行：一格（结尾重点）
        PanelSlot(
            slot_id=5, x=0.0, y=0.68, width=1.0, height=0.32,
            purpose=PanelPurpose.EMPHASIS,
            suggested_composition="wide shot",
            suggested_angle="eye level",
            aspect_ratio="21:9",
            is_key_panel=True
        ),
    ],
    pacing="normal",
    intensity=4,
    usage_notes="适合日常场景、对话推进。第一格建立场景，中间展示互动，最后一格做小结或过渡。"
)


# 模板2：正反打对话（紧张对话、对峙）
TEMPLATE_SHOT_REVERSE_SHOT = PageTemplate(
    id="shot_reverse_shot",
    name="Shot-Reverse-Shot",
    name_zh="正反打对话",
    description="经典的电影对话分镜，左右交替展示对话双方，营造紧张对峙感。",
    suitable_moods=[SceneMood.TENSION, SceneMood.DRAMATIC, SceneMood.ROMANTIC],
    panel_slots=[
        # 开场建立镜头
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=1.0, height=0.25,
            purpose=PanelPurpose.ESTABLISHING,
            suggested_composition="wide shot",
            suggested_angle="eye level",
            aspect_ratio="21:9",
            visual_flow_to=2
        ),
        # 正反打第一组
        PanelSlot(
            slot_id=2, x=0.0, y=0.27, width=0.48, height=0.22,
            purpose=PanelPurpose.CLOSEUP,
            suggested_composition="close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=3
        ),
        PanelSlot(
            slot_id=3, x=0.52, y=0.27, width=0.48, height=0.22,
            purpose=PanelPurpose.CLOSEUP,
            suggested_composition="close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=4
        ),
        # 正反打第二组（更近的特写）
        PanelSlot(
            slot_id=4, x=0.0, y=0.51, width=0.48, height=0.22,
            purpose=PanelPurpose.EMOTION,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=5
        ),
        PanelSlot(
            slot_id=5, x=0.52, y=0.51, width=0.48, height=0.22,
            purpose=PanelPurpose.EMOTION,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=6
        ),
        # 结尾反应
        PanelSlot(
            slot_id=6, x=0.0, y=0.75, width=1.0, height=0.25,
            purpose=PanelPurpose.REACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="21:9",
            is_key_panel=True
        ),
    ],
    pacing="slow",
    intensity=6,
    usage_notes="适合重要对话、对峙场景。通过逐渐拉近的镜头增强紧张感。"
)


# 模板3：动作爆发式（战斗、冲击）
TEMPLATE_ACTION_BURST = PageTemplate(
    id="action_burst",
    name="Action Burst",
    name_zh="动作爆发",
    description="中央大格爆发，周围小格铺垫，适合战斗高潮和冲击时刻。",
    suitable_moods=[SceneMood.ACTION, SceneMood.DRAMATIC, SceneMood.HORROR],
    panel_slots=[
        # 顶部铺垫（快速小格）
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=0.33, height=0.18,
            purpose=PanelPurpose.ACTION,
            suggested_composition="medium shot",
            suggested_angle="dynamic",
            aspect_ratio="4:3",
            shape=PanelShape.DIAGONAL_RIGHT,
            visual_flow_to=2
        ),
        PanelSlot(
            slot_id=2, x=0.35, y=0.0, width=0.32, height=0.18,
            purpose=PanelPurpose.DETAIL,
            suggested_composition="close-up",
            suggested_angle="dynamic",
            aspect_ratio="1:1",
            visual_flow_to=3
        ),
        PanelSlot(
            slot_id=3, x=0.69, y=0.0, width=0.31, height=0.18,
            purpose=PanelPurpose.REACTION,
            suggested_composition="close-up",
            suggested_angle="low angle",
            aspect_ratio="4:3",
            shape=PanelShape.DIAGONAL_LEFT,
            visual_flow_to=4
        ),
        # 中央大格（爆发）
        PanelSlot(
            slot_id=4, x=0.0, y=0.20, width=1.0, height=0.55,
            purpose=PanelPurpose.EMPHASIS,
            suggested_composition="dynamic wide shot",
            suggested_angle="dramatic",
            aspect_ratio="16:9",
            shape=PanelShape.JAGGED,
            can_break_frame=True,
            is_key_panel=True,
            border_weight="thick",
            visual_flow_to=5
        ),
        # 底部反应
        PanelSlot(
            slot_id=5, x=0.0, y=0.77, width=0.5, height=0.23,
            purpose=PanelPurpose.REACTION,
            suggested_composition="close-up",
            suggested_angle="low angle",
            aspect_ratio="4:3",
            visual_flow_to=6
        ),
        PanelSlot(
            slot_id=6, x=0.52, y=0.77, width=0.48, height=0.23,
            purpose=PanelPurpose.EMOTION,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3"
        ),
    ],
    pacing="fast",
    intensity=9,
    gutter_style="tight",
    usage_notes="适合动作高潮、冲击瞬间。中央大格是视觉焦点，周围小格快速铺垫和反应。"
)


# 模板4：情感递进（情感爆发、内心戏）
TEMPLATE_EMOTIONAL_PROGRESSION = PageTemplate(
    id="emotional_progression",
    name="Emotional Progression",
    name_zh="情感递进",
    description="从远到近的镜头推进，逐步聚焦角色情感，适合情感爆发场景。",
    suitable_moods=[SceneMood.EMOTIONAL, SceneMood.DRAMATIC, SceneMood.ROMANTIC],
    panel_slots=[
        # 远景铺垫
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=1.0, height=0.28,
            purpose=PanelPurpose.ESTABLISHING,
            suggested_composition="wide shot",
            suggested_angle="eye level",
            aspect_ratio="21:9",
            visual_flow_to=2
        ),
        # 中景过渡
        PanelSlot(
            slot_id=2, x=0.0, y=0.30, width=0.55, height=0.25,
            purpose=PanelPurpose.ACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            visual_flow_to=3
        ),
        PanelSlot(
            slot_id=3, x=0.57, y=0.30, width=0.43, height=0.25,
            purpose=PanelPurpose.REACTION,
            suggested_composition="medium close-up",
            suggested_angle="eye level",
            aspect_ratio="3:4",
            visual_flow_to=4
        ),
        # 特写高潮
        PanelSlot(
            slot_id=4, x=0.0, y=0.57, width=1.0, height=0.43,
            purpose=PanelPurpose.EMOTION,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="16:9",
            is_key_panel=True,
            can_break_frame=True,
            border_weight="thin"
        ),
    ],
    pacing="slow",
    intensity=7,
    gutter_style="loose",
    usage_notes="适合情感宣泄、内心独白。从全景逐步推进到特写，最后大格聚焦情感。"
)


# 模板5：时间蒙太奇（时间流逝、回忆）
TEMPLATE_TIME_MONTAGE = PageTemplate(
    id="time_montage",
    name="Time Montage",
    name_zh="时间蒙太奇",
    description="多个等大小格排列，表现时间流逝或回忆片段。",
    suitable_moods=[SceneMood.FLASHBACK, SceneMood.CALM, SceneMood.MYSTERY],
    panel_slots=[
        # 6格均匀布局
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=0.48, height=0.32,
            purpose=PanelPurpose.TRANSITION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            shape=PanelShape.BORDERLESS,
            border_weight="none",
            visual_flow_to=2
        ),
        PanelSlot(
            slot_id=2, x=0.52, y=0.0, width=0.48, height=0.32,
            purpose=PanelPurpose.TRANSITION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            shape=PanelShape.BORDERLESS,
            border_weight="none",
            visual_flow_to=3
        ),
        PanelSlot(
            slot_id=3, x=0.0, y=0.34, width=0.48, height=0.32,
            purpose=PanelPurpose.TRANSITION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            shape=PanelShape.BORDERLESS,
            border_weight="none",
            visual_flow_to=4
        ),
        PanelSlot(
            slot_id=4, x=0.52, y=0.34, width=0.48, height=0.32,
            purpose=PanelPurpose.TRANSITION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            shape=PanelShape.BORDERLESS,
            border_weight="none",
            visual_flow_to=5
        ),
        PanelSlot(
            slot_id=5, x=0.0, y=0.68, width=0.48, height=0.32,
            purpose=PanelPurpose.TRANSITION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            shape=PanelShape.BORDERLESS,
            border_weight="none",
            visual_flow_to=6
        ),
        PanelSlot(
            slot_id=6, x=0.52, y=0.68, width=0.48, height=0.32,
            purpose=PanelPurpose.EMPHASIS,
            suggested_composition="close-up",
            suggested_angle="eye level",
            aspect_ratio="4:3",
            shape=PanelShape.BORDERLESS,
            border_weight="none",
            is_key_panel=True
        ),
    ],
    pacing="slow",
    intensity=3,
    gutter_style="loose",
    usage_notes="适合回忆、蒙太奇、时间流逝。无边框设计营造梦幻/怀旧感。"
)


# 模板6：全页冲击（关键转折、高潮）
TEMPLATE_FULL_PAGE_IMPACT = PageTemplate(
    id="full_page_impact",
    name="Full Page Impact",
    name_zh="全页冲击",
    description="整页单格，用于最重要的视觉冲击时刻。",
    suitable_moods=[SceneMood.DRAMATIC, SceneMood.ACTION, SceneMood.HORROR, SceneMood.EMOTIONAL],
    panel_slots=[
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=1.0, height=1.0,
            purpose=PanelPurpose.EMPHASIS,
            suggested_composition="dynamic composition",
            suggested_angle="dramatic",
            aspect_ratio="3:4",
            can_break_frame=True,
            is_key_panel=True,
            border_weight="thick"
        ),
    ],
    pacing="slow",
    intensity=10,
    usage_notes="仅用于最关键的时刻：重大转折、角色登场、情感高潮。不要频繁使用。"
)


# 模板7：悬念递进（悬疑、恐怖）
TEMPLATE_SUSPENSE_BUILD = PageTemplate(
    id="suspense_build",
    name="Suspense Build",
    name_zh="悬念递进",
    description="逐渐缩小的画格，营造压迫感和悬念。",
    suitable_moods=[SceneMood.MYSTERY, SceneMood.HORROR, SceneMood.TENSION],
    panel_slots=[
        # 大格开场
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=1.0, height=0.35,
            purpose=PanelPurpose.ESTABLISHING,
            suggested_composition="wide shot",
            suggested_angle="high angle",
            aspect_ratio="21:9",
            visual_flow_to=2
        ),
        # 中等格
        PanelSlot(
            slot_id=2, x=0.0, y=0.37, width=0.65, height=0.28,
            purpose=PanelPurpose.ACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="16:9",
            visual_flow_to=3
        ),
        PanelSlot(
            slot_id=3, x=0.67, y=0.37, width=0.33, height=0.28,
            purpose=PanelPurpose.DETAIL,
            suggested_composition="close-up",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            visual_flow_to=4
        ),
        # 小格压迫
        PanelSlot(
            slot_id=4, x=0.0, y=0.67, width=0.25, height=0.15,
            purpose=PanelPurpose.DETAIL,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            visual_flow_to=5
        ),
        PanelSlot(
            slot_id=5, x=0.27, y=0.67, width=0.25, height=0.15,
            purpose=PanelPurpose.DETAIL,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            visual_flow_to=6
        ),
        PanelSlot(
            slot_id=6, x=0.54, y=0.67, width=0.46, height=0.15,
            purpose=PanelPurpose.REACTION,
            suggested_composition="close-up",
            suggested_angle="low angle",
            aspect_ratio="3:1",
            visual_flow_to=7
        ),
        # 黑色/留白结尾
        PanelSlot(
            slot_id=7, x=0.0, y=0.84, width=1.0, height=0.16,
            purpose=PanelPurpose.EMPHASIS,
            suggested_composition="extreme close-up",
            suggested_angle="eye level",
            aspect_ratio="6:1",
            is_key_panel=True,
            border_weight="thick"
        ),
    ],
    pacing="slow",
    intensity=8,
    gutter_style="tight",
    usage_notes="适合悬疑揭示、恐怖氛围。画格逐渐缩小创造压迫感，最后一格是悬念点。"
)


# 模板8：轻松网格（日常、搞笑）
TEMPLATE_CASUAL_GRID = PageTemplate(
    id="casual_grid",
    name="Casual Grid",
    name_zh="轻松网格",
    description="规整的网格布局，适合轻松日常和搞笑场景。",
    suitable_moods=[SceneMood.CALM, SceneMood.COMEDY],
    panel_slots=[
        # 4格均匀网格
        PanelSlot(
            slot_id=1, x=0.0, y=0.0, width=0.48, height=0.48,
            purpose=PanelPurpose.ACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            shape=PanelShape.ROUNDED,
            visual_flow_to=2
        ),
        PanelSlot(
            slot_id=2, x=0.52, y=0.0, width=0.48, height=0.48,
            purpose=PanelPurpose.REACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            shape=PanelShape.ROUNDED,
            visual_flow_to=3
        ),
        PanelSlot(
            slot_id=3, x=0.0, y=0.52, width=0.48, height=0.48,
            purpose=PanelPurpose.ACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            shape=PanelShape.ROUNDED,
            visual_flow_to=4
        ),
        PanelSlot(
            slot_id=4, x=0.52, y=0.52, width=0.48, height=0.48,
            purpose=PanelPurpose.REACTION,
            suggested_composition="medium shot",
            suggested_angle="eye level",
            aspect_ratio="1:1",
            shape=PanelShape.ROUNDED,
            is_key_panel=True
        ),
    ],
    pacing="normal",
    intensity=2,
    gutter_style="standard",
    usage_notes="适合四格漫画风格、轻松日常。节奏轻快，适合简单的起承转合。"
)


# ============================================================
# 模板注册表
# ============================================================

ALL_TEMPLATES: Dict[str, PageTemplate] = {
    "standard_three_tier": TEMPLATE_STANDARD_THREE_TIER,
    "shot_reverse_shot": TEMPLATE_SHOT_REVERSE_SHOT,
    "action_burst": TEMPLATE_ACTION_BURST,
    "emotional_progression": TEMPLATE_EMOTIONAL_PROGRESSION,
    "time_montage": TEMPLATE_TIME_MONTAGE,
    "full_page_impact": TEMPLATE_FULL_PAGE_IMPACT,
    "suspense_build": TEMPLATE_SUSPENSE_BUILD,
    "casual_grid": TEMPLATE_CASUAL_GRID,
}


def get_template(template_id: str) -> Optional[PageTemplate]:
    """根据ID获取模板"""
    return ALL_TEMPLATES.get(template_id)


def get_templates_for_mood(mood: SceneMood) -> List[PageTemplate]:
    """根据情感类型获取适合的模板列表"""
    return [t for t in ALL_TEMPLATES.values() if mood in t.suitable_moods]


def recommend_template(
    mood: SceneMood,
    is_climax: bool = False,
    has_dialogue: bool = False,
    is_action: bool = False,
) -> PageTemplate:
    """
    根据场景特征推荐最佳模板

    Args:
        mood: 场景情感
        is_climax: 是否为高潮场景
        has_dialogue: 是否有重要对话
        is_action: 是否为动作场景

    Returns:
        推荐的页面模板
    """
    # 高潮场景优先使用全页冲击
    if is_climax:
        return TEMPLATE_FULL_PAGE_IMPACT

    # 动作场景
    if is_action:
        return TEMPLATE_ACTION_BURST

    # 对话场景
    if has_dialogue:
        if mood in [SceneMood.TENSION, SceneMood.DRAMATIC]:
            return TEMPLATE_SHOT_REVERSE_SHOT
        else:
            return TEMPLATE_STANDARD_THREE_TIER

    # 根据情感选择
    mood_template_map = {
        SceneMood.CALM: TEMPLATE_CASUAL_GRID,
        SceneMood.TENSION: TEMPLATE_SHOT_REVERSE_SHOT,
        SceneMood.ACTION: TEMPLATE_ACTION_BURST,
        SceneMood.EMOTIONAL: TEMPLATE_EMOTIONAL_PROGRESSION,
        SceneMood.MYSTERY: TEMPLATE_SUSPENSE_BUILD,
        SceneMood.COMEDY: TEMPLATE_CASUAL_GRID,
        SceneMood.DRAMATIC: TEMPLATE_EMOTIONAL_PROGRESSION,
        SceneMood.ROMANTIC: TEMPLATE_SHOT_REVERSE_SHOT,
        SceneMood.HORROR: TEMPLATE_SUSPENSE_BUILD,
        SceneMood.FLASHBACK: TEMPLATE_TIME_MONTAGE,
    }

    return mood_template_map.get(mood, TEMPLATE_STANDARD_THREE_TIER)


# ============================================================
# 场景展开结果数据结构
# ============================================================

@dataclass
class PanelContent:
    """
    画格内容定义

    描述一个具体画格中应该展示的内容
    """
    slot_id: int  # 对应模板中的槽位ID

    # 内容描述
    content_description: str  # 这个画格要展示什么
    narrative_purpose: str  # 叙事目的

    # 角色
    characters: List[str] = field(default_factory=list)
    character_emotions: Dict[str, str] = field(default_factory=dict)  # 角色名 -> 情绪

    # 镜头
    composition: str = "medium shot"
    camera_angle: str = "eye level"

    # 文字元素 - 基础字段（兼容旧数据）
    dialogue: Optional[str] = None
    dialogue_speaker: Optional[str] = None
    narration: Optional[str] = None
    sound_effects: List[str] = field(default_factory=list)

    # 文字元素 - 扩展字段（新增）
    dialogue_bubble_type: str = "normal"  # normal/shout/whisper/thought/narration/electronic
    dialogue_position: str = "top-right"  # 气泡位置
    dialogue_emotion: str = ""  # 说话时的情绪
    narration_position: str = "top"  # 旁白位置
    sound_effect_details: List[Dict[str, Any]] = field(default_factory=list)  # 详细音效信息列表

    # 视觉指导
    key_visual_elements: List[str] = field(default_factory=list)  # 关键视觉元素
    atmosphere: str = ""  # 氛围描述
    lighting: str = ""  # 光线描述

    # LLM生成的提示词（优先使用，如果为空则由PanelPromptBuilder生成）
    prompt_en: str = ""  # LLM直接生成的英文提示词
    negative_prompt: str = ""  # LLM直接生成的负面提示词

    def get_bubble_type(self) -> DialogueBubbleType:
        """获取气泡类型枚举"""
        try:
            return DialogueBubbleType(self.dialogue_bubble_type)
        except ValueError:
            return DialogueBubbleType.NORMAL

    def get_sound_effects_info(self) -> List[SoundEffectInfo]:
        """获取结构化的音效信息列表"""
        result = []
        # 处理详细音效信息
        for detail in self.sound_effect_details:
            # 处理detail可能不是dict的情况
            if not isinstance(detail, dict):
                if isinstance(detail, str):
                    result.append(SoundEffectInfo(
                        text=detail,
                        effect_type=SoundEffectType.ACTION,
                        intensity=SoundEffectIntensity.MEDIUM,
                    ))
                continue

            try:
                effect_type = SoundEffectType(detail.get("type", "action"))
            except ValueError:
                effect_type = SoundEffectType.ACTION
            try:
                intensity = SoundEffectIntensity(detail.get("intensity", "medium"))
            except ValueError:
                intensity = SoundEffectIntensity.MEDIUM

            # 处理text可能是dict的情况（LLM返回格式不规范）
            text_value = detail.get("text", "")
            if isinstance(text_value, dict):
                # 尝试从dict中提取text内容
                text_value = text_value.get("content", "") or text_value.get("text", "") or str(text_value)
            elif not isinstance(text_value, str):
                text_value = str(text_value) if text_value else ""

            # 处理position可能是dict的情况
            position_value = detail.get("position", "")
            if isinstance(position_value, dict):
                position_value = position_value.get("value", "") or str(position_value)
            elif not isinstance(position_value, str):
                position_value = str(position_value) if position_value else ""

            result.append(SoundEffectInfo(
                text=text_value,
                effect_type=effect_type,
                intensity=intensity,
                position=position_value,
            ))

        # 处理简单音效列表（兼容旧数据）
        if not result and self.sound_effects:
            for sfx in self.sound_effects:
                # 确保sfx是字符串
                if isinstance(sfx, dict):
                    sfx_text = sfx.get("text", "") or sfx.get("content", "") or str(sfx)
                elif isinstance(sfx, str):
                    sfx_text = sfx
                else:
                    sfx_text = str(sfx) if sfx else ""

                result.append(SoundEffectInfo(
                    text=sfx_text,
                    effect_type=SoundEffectType.ACTION,
                    intensity=SoundEffectIntensity.MEDIUM,
                ))

        return result


@dataclass
class PagePlan:
    """
    页面规划

    一个完整页面的所有画格内容
    """
    page_number: int
    template: PageTemplate
    panels: List[PanelContent]

    # 页面级信息
    page_purpose: str = ""  # 这一页的叙事目的
    transition_from_previous: str = ""  # 与上一页的转场方式

    def validate(self) -> bool:
        """验证页面规划的完整性"""
        template_slot_ids = {s.slot_id for s in self.template.panel_slots}
        panel_slot_ids = {p.slot_id for p in self.panels}
        return template_slot_ids == panel_slot_ids


@dataclass
class SceneExpansion:
    """
    场景展开结果

    一个叙事场景展开为多个页面
    """
    scene_id: int
    scene_summary: str
    original_text: str

    # 展开后的页面
    pages: List[PagePlan]

    # 元信息
    mood: SceneMood
    importance: str = "normal"  # low/normal/high/critical

    def get_total_panels(self) -> int:
        """获取总画格数"""
        return sum(len(page.panels) for page in self.pages)

    def get_all_panels(self) -> List[PanelContent]:
        """获取所有画格内容"""
        panels = []
        for page in self.pages:
            panels.extend(page.panels)
        return panels
