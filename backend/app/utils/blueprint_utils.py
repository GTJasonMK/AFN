"""
蓝图工具函数

提供蓝图数据处理的通用工具函数，统一蓝图准备逻辑。
"""

from typing import Any, Dict


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


__all__ = [
    "BANNED_BLUEPRINT_KEYS",
    "prepare_blueprint_for_generation",
]
