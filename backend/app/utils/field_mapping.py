"""
字段映射工具

用于将输入字典按字段映射应用到目标对象或更新字典，减少重复赋值逻辑。
"""

from typing import Any, Dict, Mapping, Tuple


def build_update_data(
    source: Mapping[str, Any],
    field_map: Mapping[str, str],
    *,
    allow_none: bool = False,
) -> Dict[str, Any]:
    """
    根据字段映射构建更新字典

    Args:
        source: 输入数据（dict或Mapping）
        field_map: 源字段 -> 目标字段映射
        allow_none: 是否允许None值写入结果
    """
    result: Dict[str, Any] = {}
    for source_key, target_key in field_map.items():
        if source_key not in source:
            continue
        value = source[source_key]
        if value is None and not allow_none:
            continue
        result[target_key] = value
    return result


def apply_mapping_with_defaults(
    target: Any,
    source: Mapping[str, Any],
    field_map: Mapping[str, Tuple[str, Any]],
) -> None:
    """
    根据字段映射应用默认值并更新目标对象

    Args:
        target: 需要更新的对象
        source: 输入数据（dict或Mapping）
        field_map: 源字段 -> (目标字段, 默认值) 映射
    """
    for source_key, (target_key, default_value) in field_map.items():
        value = source.get(source_key, default_value)
        setattr(target, target_key, value)
