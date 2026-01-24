"""
场景描述结构

用于统一不同链路的场景字段命名与格式输出。
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


_TIME_OF_DAY_ALIASES = {
    "dawn": "dawn",
    "morning": "morning",
    "afternoon": "afternoon",
    "evening": "evening",
    "night": "night",
    "dusk": "dusk",
    "day": "day",
}

_TIME_MARKER_MAPPING = [
    (("清晨", "凌晨"), "dawn"),
    (("早上", "上午"), "morning"),
    (("中午", "下午"), "afternoon"),
    (("傍晚", "黄昏"), "dusk"),
    (("夜晚", "深夜", "子时", "丑时", "寅时", "戌时", "亥时"), "night"),
]


def normalize_time_of_day(value: Optional[str]) -> str:
    """规范化时间段枚举"""
    if not value:
        return "day"
    normalized = value.strip().lower()
    return _TIME_OF_DAY_ALIASES.get(normalized, "day")


def normalize_time_marker(marker: Optional[str]) -> str:
    """根据时间标记推断 time_of_day"""
    if not marker:
        return "day"
    for keywords, mapped in _TIME_MARKER_MAPPING:
        if any(k in marker for k in keywords):
            return mapped
    return "day"


@dataclass
class SceneDescriptor:
    """统一场景描述"""
    location: str = ""
    time_marker: Optional[str] = None
    time_of_day: str = "day"
    atmosphere: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "location": self.location,
            "time_marker": self.time_marker,
            "time_of_day": self.time_of_day,
            "atmosphere": self.atmosphere,
        }

    @classmethod
    def from_paragraph_analysis(cls, analysis: Any) -> "SceneDescriptor":
        """从段落分析结果生成描述"""
        scene = getattr(analysis, "scene", None) or ""
        time_marker = getattr(analysis, "time_marker", None)
        emotion_tone = getattr(analysis, "emotion_tone", None) or ""
        return cls(
            location=scene or "",
            time_marker=time_marker,
            time_of_day=normalize_time_marker(time_marker),
            atmosphere=emotion_tone,
        )

    @classmethod
    def from_scene_state(cls, scene_state: Any) -> "SceneDescriptor":
        """从 SceneState 生成描述"""
        location = getattr(scene_state, "primary_location", None) or ""
        time_marker = getattr(scene_state, "time_marker", None)
        tone = getattr(scene_state, "tone", None) or ""
        return cls(
            location=location,
            time_marker=time_marker,
            time_of_day=normalize_time_marker(time_marker),
            atmosphere=tone,
        )

    @classmethod
    def from_scene_info(cls, scene_info: Any) -> "SceneDescriptor":
        """从 SceneInfo 生成描述"""
        location = getattr(scene_info, "location", None) or ""
        time_of_day = normalize_time_of_day(getattr(scene_info, "time_of_day", None))
        atmosphere = getattr(scene_info, "atmosphere", None) or ""
        return cls(
            location=location,
            time_marker=None,
            time_of_day=time_of_day,
            atmosphere=atmosphere,
        )
