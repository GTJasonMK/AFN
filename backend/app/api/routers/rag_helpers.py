"""
RAG 路由辅助函数

用于复用 completeness/diagnose 的类型明细构建逻辑。
"""

from typing import Any, Callable, Dict, TypeVar


DetailT = TypeVar("DetailT")


def build_type_details(
    type_details: Dict[str, Dict[str, Any]],
    builder: Callable[[str, Dict[str, Any]], DetailT],
) -> Dict[str, DetailT]:
    """根据类型明细字典构建响应模型集合。"""
    result: Dict[str, DetailT] = {}
    for type_name, detail in type_details.items():
        result[type_name] = builder(type_name, detail)
    return result


__all__ = ["build_type_details"]
