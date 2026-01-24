"""
RAG 路由辅助函数

用于复用 completeness/diagnose 的类型明细构建逻辑。
"""

from typing import Any, Callable, Dict, Optional, Tuple, TypeVar


DetailT = TypeVar("DetailT")
ReportT = TypeVar("ReportT")


def build_type_details(
    type_details: Dict[str, Dict[str, Any]],
    builder: Callable[[str, Dict[str, Any]], DetailT],
) -> Dict[str, DetailT]:
    """根据类型明细字典构建响应模型集合。"""
    result: Dict[str, DetailT] = {}
    for type_name, detail in type_details.items():
        result[type_name] = builder(type_name, detail)
    return result


async def run_completeness_check(
    *,
    project_id: str,
    session: Any,
    vector_store: Any,
    llm_service: Any,
    user_id: int,
    service_factory: Callable[..., Any],
    build_detail: Callable[[str, Dict[str, Any]], DetailT],
    log_message: Optional[Callable[[ReportT], None]] = None,
) -> Tuple[ReportT, Dict[str, DetailT]]:
    """执行完整性检查并返回报告与类型详情。"""
    service = service_factory(
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=user_id,
    )

    report: ReportT = await service.check_completeness(project_id)
    types_detail = build_type_details(report.type_details, build_detail)
    if log_message:
        log_message(report)
    return report, types_detail


__all__ = ["build_type_details", "run_completeness_check"]
