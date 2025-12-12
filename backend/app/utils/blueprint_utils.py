"""
蓝图工具函数

提供蓝图数据处理的通用工具函数，统一蓝图准备逻辑。
"""

from typing import Any, Dict, List, Optional


# 禁止包含在生成提示词中的蓝图字段
# 这些字段包含章节级别的细节，可能导致LLM生成时产生混淆
BANNED_BLUEPRINT_KEYS = frozenset({
    "chapter_outline",
    "chapter_summaries",
    "chapter_details",
    "chapter_dialogues",
    "chapter_events",
    "conversation_history",
    "character_timelines",
})


def prepare_blueprint_for_generation(blueprint_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    准备用于生成的蓝图数据，清理敏感字段

    执行以下清理操作：
    1. 转换relationships字段名（character_from -> from, character_to -> to）
    2. 移除禁止的章节级别细节字段

    Args:
        blueprint_dict: 原始蓝图字典

    Returns:
        清理后的蓝图字典（注意：会修改原字典）
    """
    # 转换relationships字段名
    if "relationships" in blueprint_dict and blueprint_dict["relationships"]:
        for relation in blueprint_dict["relationships"]:
            if "character_from" in relation:
                relation["from"] = relation.pop("character_from")
            if "character_to" in relation:
                relation["to"] = relation.pop("character_to")

    # 移除禁止的章节级别细节
    for key in BANNED_BLUEPRINT_KEYS:
        blueprint_dict.pop(key, None)

    return blueprint_dict


def extract_blueprint_characters(blueprint: Any) -> List[Dict[str, Any]]:
    """
    从蓝图对象或字典中提取角色列表

    支持多种输入格式：
    - 带characters属性的蓝图对象
    - 包含characters键的字典
    - 包含BlueprintCharacter模型的列表

    Args:
        blueprint: 蓝图对象或字典

    Returns:
        角色字典列表
    """
    characters = []

    # 尝试从对象属性获取
    if hasattr(blueprint, "characters"):
        raw_chars = blueprint.characters
    elif isinstance(blueprint, dict):
        raw_chars = blueprint.get("characters", [])
    else:
        return characters

    # 转换为字典列表
    for char in raw_chars:
        if isinstance(char, dict):
            characters.append(char)
        elif hasattr(char, "name"):
            # BlueprintCharacter模型转换
            char_dict = {
                "name": char.name,
                "identity": getattr(char, "identity", "") or "",
                "personality": getattr(char, "personality", "") or "",
                "goals": getattr(char, "goals", "") or "",
                "abilities": getattr(char, "abilities", "") or "",
            }
            # 合并extra字段
            if hasattr(char, "extra") and char.extra:
                char_dict.update(char.extra)
            characters.append(char_dict)

    return characters


def extract_world_setting(blueprint: Any) -> Dict[str, Any]:
    """
    从蓝图对象或字典中提取世界观设定

    Args:
        blueprint: 蓝图对象或字典

    Returns:
        世界观设定字典
    """
    if hasattr(blueprint, "world_setting"):
        return blueprint.world_setting or {}
    elif isinstance(blueprint, dict):
        return blueprint.get("world_setting", {})
    return {}


def extract_full_synopsis(blueprint: Any) -> str:
    """
    从蓝图对象或字典中提取完整故事大纲

    Args:
        blueprint: 蓝图对象或字典

    Returns:
        故事大纲文本
    """
    if hasattr(blueprint, "full_synopsis"):
        return blueprint.full_synopsis or ""
    elif isinstance(blueprint, dict):
        return blueprint.get("full_synopsis", "") or blueprint.get("synopsis", "")
    return ""


def build_blueprint_info_dict(blueprint: Any) -> Dict[str, Any]:
    """
    构建蓝图信息字典（用于上下文构建）

    Args:
        blueprint: 蓝图对象或字典

    Returns:
        标准化的蓝图信息字典
    """
    if isinstance(blueprint, dict):
        return {
            "title": blueprint.get("title", ""),
            "genre": blueprint.get("genre", ""),
            "style": blueprint.get("writing_style", "") or blueprint.get("style", ""),
            "tone": blueprint.get("tone", ""),
            "one_sentence_summary": blueprint.get("one_sentence_summary", ""),
            "full_synopsis": blueprint.get("full_synopsis", "") or blueprint.get("synopsis", ""),
            "world_setting": blueprint.get("world_setting", {}),
            "characters": blueprint.get("characters", []),
            "relationships": blueprint.get("relationships", []),
        }

    # 从对象属性构建
    return {
        "title": getattr(blueprint, "title", "") or "",
        "genre": getattr(blueprint, "genre", "") or "",
        "style": getattr(blueprint, "writing_style", "") or getattr(blueprint, "style", "") or "",
        "tone": getattr(blueprint, "tone", "") or "",
        "one_sentence_summary": getattr(blueprint, "one_sentence_summary", "") or "",
        "full_synopsis": getattr(blueprint, "full_synopsis", "") or "",
        "world_setting": getattr(blueprint, "world_setting", {}) or {},
        "characters": extract_blueprint_characters(blueprint),
        "relationships": getattr(blueprint, "relationships", []) or [],
    }


__all__ = [
    "BANNED_BLUEPRINT_KEYS",
    "prepare_blueprint_for_generation",
    "extract_blueprint_characters",
    "extract_world_setting",
    "extract_full_synopsis",
    "build_blueprint_info_dict",
]
