"""
信息提取模块数据模型

定义章节信息提取的所有数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class EmotionType(str, Enum):
    """情绪类型"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    CONTEMPTUOUS = "contemptuous"
    EXCITED = "excited"
    CALM = "calm"
    NERVOUS = "nervous"
    DETERMINED = "determined"

    @classmethod
    def from_string(cls, value: str) -> "EmotionType":
        """从字符串转换，支持容错"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        # 常见同义词映射
        synonyms = {
            "joy": cls.HAPPY,
            "happiness": cls.HAPPY,
            "sorrow": cls.SAD,
            "grief": cls.SAD,
            "rage": cls.ANGRY,
            "fury": cls.ANGRY,
            "shock": cls.SURPRISED,
            "fear": cls.FEARFUL,
            "scared": cls.FEARFUL,
            "disgust": cls.DISGUSTED,
            "contempt": cls.CONTEMPTUOUS,
            "excitement": cls.EXCITED,
            "peaceful": cls.CALM,
            "anxious": cls.NERVOUS,
            "worried": cls.NERVOUS,
            "resolute": cls.DETERMINED,
        }
        return synonyms.get(value, cls.NEUTRAL)


class EventType(str, Enum):
    """事件类型"""
    DIALOGUE = "dialogue"       # 对话
    ACTION = "action"           # 动作
    REACTION = "reaction"       # 反应
    TRANSITION = "transition"   # 过渡
    REVELATION = "revelation"   # 揭示
    CONFLICT = "conflict"       # 冲突
    RESOLUTION = "resolution"   # 解决
    DESCRIPTION = "description" # 描述/叙述
    INTERNAL = "internal"       # 内心活动

    @classmethod
    def from_string(cls, value: str) -> "EventType":
        """从字符串转换，支持容错"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        # 常见同义词映射
        synonyms = {
            "talk": cls.DIALOGUE,
            "conversation": cls.DIALOGUE,
            "fight": cls.ACTION,
            "movement": cls.ACTION,
            "response": cls.REACTION,
            "change": cls.TRANSITION,
            "discovery": cls.REVELATION,
            "secret": cls.REVELATION,
            "battle": cls.CONFLICT,
            "argument": cls.CONFLICT,
            "solve": cls.RESOLUTION,
            "ending": cls.RESOLUTION,
            "narration": cls.DESCRIPTION,
            "thought": cls.INTERNAL,
            "thinking": cls.INTERNAL,
        }
        return synonyms.get(value, cls.DESCRIPTION)


class CharacterRole(str, Enum):
    """角色定位"""
    PROTAGONIST = "protagonist"     # 主角
    ANTAGONIST = "antagonist"       # 反派
    SUPPORTING = "supporting"       # 重要配角
    MINOR = "minor"                 # 次要角色
    BACKGROUND = "background"       # 背景角色

    @classmethod
    def from_string(cls, value: str) -> "CharacterRole":
        """从字符串转换"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.MINOR


class ImportanceLevel(str, Enum):
    """重要程度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_string(cls, value: str) -> "ImportanceLevel":
        """从字符串转换"""
        value = value.lower().strip()
        for member in cls:
            if member.value == value:
                return member
        return cls.NORMAL


@dataclass
class CharacterInfo:
    """角色信息"""
    name: str
    appearance: str                 # 英文外观描述（用于AI绘图）
    appearance_zh: str = ""         # 中文外观描述（用于理解）
    personality: str = ""           # 性格特点
    role: CharacterRole = CharacterRole.MINOR
    first_appearance_event: int = 0 # 首次出现的事件索引
    relationships: Dict[str, str] = field(default_factory=dict)  # 与其他角色的关系
    gender: str = ""                # 性别
    age_description: str = ""       # 年龄描述

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "appearance": self.appearance,
            "appearance_zh": self.appearance_zh,
            "personality": self.personality,
            "role": self.role.value,
            "first_appearance_event": self.first_appearance_event,
            "relationships": self.relationships,
            "gender": self.gender,
            "age_description": self.age_description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CharacterInfo":
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            appearance=data.get("appearance", ""),
            appearance_zh=data.get("appearance_zh", ""),
            personality=data.get("personality", ""),
            role=CharacterRole.from_string(data.get("role", "minor")),
            first_appearance_event=data.get("first_appearance_event", 0),
            relationships=data.get("relationships", {}),
            gender=data.get("gender", ""),
            age_description=data.get("age_description", ""),
        )


@dataclass
class DialogueInfo:
    """对话信息"""
    index: int                      # 对话索引
    speaker: str                    # 说话人
    content: str                    # 对话内容（保留原文）
    content_translated: str = ""    # 翻译后的内容（如需要）
    emotion: EmotionType = EmotionType.NEUTRAL
    target: Optional[str] = None    # 对话对象
    event_index: int = 0            # 所属事件索引
    is_internal: bool = False       # 是否是内心独白
    bubble_type: str = "normal"     # 气泡类型: normal/shout/whisper/thought

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "index": self.index,
            "speaker": self.speaker,
            "content": self.content,
            "content_translated": self.content_translated,
            "emotion": self.emotion.value,
            "target": self.target,
            "event_index": self.event_index,
            "is_internal": self.is_internal,
            "bubble_type": self.bubble_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueInfo":
        """从字典创建"""
        return cls(
            index=data.get("index", 0),
            speaker=data.get("speaker", ""),
            content=data.get("content", ""),
            content_translated=data.get("content_translated", ""),
            emotion=EmotionType.from_string(data.get("emotion", "neutral")),
            target=data.get("target"),
            event_index=data.get("event_index", 0),
            is_internal=data.get("is_internal", False),
            bubble_type=data.get("bubble_type", "normal"),
        )


@dataclass
class SceneInfo:
    """场景信息"""
    index: int                      # 场景索引
    location: str                   # 地点
    location_en: str = ""           # 英文地点描述
    time_of_day: str = "day"        # 时间: morning/afternoon/evening/night/dawn/dusk
    atmosphere: str = ""            # 氛围
    weather: Optional[str] = None   # 天气
    lighting: str = "natural"       # 光线: natural/dim/bright/dramatic/soft
    indoor_outdoor: str = "indoor"  # indoor/outdoor
    description: str = ""           # 场景描述
    event_indices: List[int] = field(default_factory=list)  # 包含的事件索引

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "index": self.index,
            "location": self.location,
            "location_en": self.location_en,
            "time_of_day": self.time_of_day,
            "atmosphere": self.atmosphere,
            "weather": self.weather,
            "lighting": self.lighting,
            "indoor_outdoor": self.indoor_outdoor,
            "description": self.description,
            "event_indices": self.event_indices,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneInfo":
        """从字典创建"""
        return cls(
            index=data.get("index", 0),
            location=data.get("location", ""),
            location_en=data.get("location_en", ""),
            time_of_day=data.get("time_of_day", "day"),
            atmosphere=data.get("atmosphere", ""),
            weather=data.get("weather"),
            lighting=data.get("lighting", "natural"),
            indoor_outdoor=data.get("indoor_outdoor", "indoor"),
            description=data.get("description", ""),
            event_indices=data.get("event_indices", []),
        )


@dataclass
class EventInfo:
    """事件信息"""
    index: int                      # 事件索引
    type: EventType                 # 事件类型
    description: str                # 事件描述
    description_en: str = ""        # 英文描述
    participants: List[str] = field(default_factory=list)  # 参与角色
    scene_index: int = 0            # 所属场景索引
    importance: ImportanceLevel = ImportanceLevel.NORMAL
    dialogue_indices: List[int] = field(default_factory=list)  # 关联的对话索引
    action_description: str = ""    # 动作描述（用于绘图）
    visual_focus: str = ""          # 视觉焦点
    emotion_tone: str = ""          # 情绪基调
    is_climax: bool = False         # 是否是高潮点

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "index": self.index,
            "type": self.type.value,
            "description": self.description,
            "description_en": self.description_en,
            "participants": self.participants,
            "scene_index": self.scene_index,
            "importance": self.importance.value,
            "dialogue_indices": self.dialogue_indices,
            "action_description": self.action_description,
            "visual_focus": self.visual_focus,
            "emotion_tone": self.emotion_tone,
            "is_climax": self.is_climax,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventInfo":
        """从字典创建"""
        return cls(
            index=data.get("index", 0),
            type=EventType.from_string(data.get("type", "description")),
            description=data.get("description", ""),
            description_en=data.get("description_en", ""),
            participants=data.get("participants", []),
            scene_index=data.get("scene_index", 0),
            importance=ImportanceLevel.from_string(data.get("importance", "normal")),
            dialogue_indices=data.get("dialogue_indices", []),
            action_description=data.get("action_description", ""),
            visual_focus=data.get("visual_focus", ""),
            emotion_tone=data.get("emotion_tone", ""),
            is_climax=data.get("is_climax", False),
        )


@dataclass
class ItemInfo:
    """物品信息"""
    name: str                       # 物品名
    name_en: str = ""               # 英文名
    description: str = ""           # 描述
    description_en: str = ""        # 英文描述（用于绘图）
    importance: str = "prop"        # prop/key_item/mcguffin
    first_appearance_event: int = 0 # 首次出现的事件索引
    visual_features: str = ""       # 视觉特征

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "name_en": self.name_en,
            "description": self.description,
            "description_en": self.description_en,
            "importance": self.importance,
            "first_appearance_event": self.first_appearance_event,
            "visual_features": self.visual_features,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ItemInfo":
        """从字典创建"""
        return cls(
            name=data.get("name", ""),
            name_en=data.get("name_en", ""),
            description=data.get("description", ""),
            description_en=data.get("description_en", ""),
            importance=data.get("importance", "prop"),
            first_appearance_event=data.get("first_appearance_event", 0),
            visual_features=data.get("visual_features", ""),
        )


@dataclass
class ChapterInfo:
    """章节信息汇总"""
    characters: Dict[str, CharacterInfo] = field(default_factory=dict)
    dialogues: List[DialogueInfo] = field(default_factory=list)
    scenes: List[SceneInfo] = field(default_factory=list)
    events: List[EventInfo] = field(default_factory=list)
    items: List[ItemInfo] = field(default_factory=list)
    chapter_summary: str = ""           # 章节摘要
    chapter_summary_en: str = ""        # 英文摘要
    mood_progression: List[str] = field(default_factory=list)  # 情绪变化轨迹
    climax_event_indices: List[int] = field(default_factory=list)  # 高潮事件索引
    total_estimated_pages: int = 0      # 预估页数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "characters": {k: v.to_dict() for k, v in self.characters.items()},
            "dialogues": [d.to_dict() for d in self.dialogues],
            "scenes": [s.to_dict() for s in self.scenes],
            "events": [e.to_dict() for e in self.events],
            "items": [i.to_dict() for i in self.items],
            "chapter_summary": self.chapter_summary,
            "chapter_summary_en": self.chapter_summary_en,
            "mood_progression": self.mood_progression,
            "climax_event_indices": self.climax_event_indices,
            "total_estimated_pages": self.total_estimated_pages,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChapterInfo":
        """从字典创建"""
        characters = {}
        for k, v in data.get("characters", {}).items():
            if isinstance(v, dict):
                characters[k] = CharacterInfo.from_dict(v)
            elif isinstance(v, str):
                # 兼容旧格式：只有外观描述字符串
                characters[k] = CharacterInfo(name=k, appearance=v)

        return cls(
            characters=characters,
            dialogues=[DialogueInfo.from_dict(d) for d in data.get("dialogues", [])],
            scenes=[SceneInfo.from_dict(s) for s in data.get("scenes", [])],
            events=[EventInfo.from_dict(e) for e in data.get("events", [])],
            items=[ItemInfo.from_dict(i) for i in data.get("items", [])],
            chapter_summary=data.get("chapter_summary", ""),
            chapter_summary_en=data.get("chapter_summary_en", ""),
            mood_progression=data.get("mood_progression", []),
            climax_event_indices=data.get("climax_event_indices", []),
            total_estimated_pages=data.get("total_estimated_pages", 0),
        )

    def get_character_profiles(self) -> Dict[str, str]:
        """
        获取角色外观描述（兼容旧格式）

        Returns:
            Dict[str, str]: 角色名到外观描述的映射
        """
        return {name: char.appearance for name, char in self.characters.items()}

    def get_dialogue_by_event(self, event_index: int) -> List[DialogueInfo]:
        """获取指定事件的对话"""
        return [d for d in self.dialogues if d.event_index == event_index]

    def get_event_by_index(self, event_index: int) -> Optional[EventInfo]:
        """根据事件索引获取事件信息"""
        for event in self.events:
            if event.index == event_index:
                return event
        return None

    def get_events_by_scene(self, scene_index: int) -> List[EventInfo]:
        """获取指定场景的事件"""
        return [e for e in self.events if e.scene_index == scene_index]

    def get_climax_events(self) -> List[EventInfo]:
        """获取高潮事件"""
        return [e for e in self.events if e.is_climax]


__all__ = [
    "EmotionType",
    "EventType",
    "CharacterRole",
    "ImportanceLevel",
    "CharacterInfo",
    "DialogueInfo",
    "SceneInfo",
    "EventInfo",
    "ItemInfo",
    "ChapterInfo",
]
