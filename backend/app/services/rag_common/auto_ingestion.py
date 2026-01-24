"""
RAG自动入库通用辅助

提供统一的异步入库执行入口，复用会话创建与服务实例化流程。
"""

from typing import Any, Callable

from ...db.session import AsyncSessionLocal


async def run_ingestion_task(
    project_id: str,
    user_id: str,
    data_type: Any,
    vector_store: Any,
    llm_service: Any,
    service_factory: Callable[[Any, Any, Any, str], Any],
) -> Any:
    """
    执行单次入库任务（不包含日志与异常处理）

    Args:
        project_id: 项目ID
        user_id: 用户ID
        data_type: 数据类型枚举
        vector_store: 向量库服务
        llm_service: LLM服务（用于传递或仅作启用检查）
        service_factory: 入库服务工厂，签名为 (session, vector_store, llm_service, user_id)

    Returns:
        入库结果对象
    """
    async with AsyncSessionLocal() as session:
        service = service_factory(session, vector_store, llm_service, user_id)
        return await service.ingest_by_type(project_id, data_type)


__all__ = ["run_ingestion_task"]
