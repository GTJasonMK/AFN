"""
配置导入通用工具

集中处理“导入配置时名称重名”的统一策略，避免在多个 Service 中重复维护。
"""

from __future__ import annotations

from typing import Set, Tuple


def resolve_unique_name(original_name: str, existing_names: Set[str]) -> Tuple[str, bool]:
    """
    生成不与现有集合冲突的名称（suffix 递增）。

    Args:
        original_name: 原始名称
        existing_names: 已存在名称集合（会被用于查重）

    Returns:
        (resolved_name, renamed)：
        - resolved_name：可用名称
        - renamed：是否发生重命名
    """
    config_name = original_name
    suffix = 1

    while config_name in existing_names:
        config_name = f"{original_name} ({suffix})"
        suffix += 1

    return config_name, config_name != original_name

