"""
RAG自动入库通用辅助

提供统一的异步入库执行入口，复用会话创建与服务实例化流程。
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional, Sequence, Type

from ...db.session import AsyncSessionLocal


def should_skip_auto_ingestion(vector_store: Optional[Any], llm_service: Optional[Any]) -> bool:
    """是否应跳过自动入库（服务未启用）"""
    return not vector_store or not llm_service


def log_skip_auto_ingestion(logger: Any, *, project_id: str, data_type_value: str) -> None:
    """统一的“跳过自动入库”日志"""
    logger.debug(
        "跳过自动入库: project=%s type=%s (服务未启用)",
        project_id,
        data_type_value,
    )


def log_auto_ingestion_failure(logger: Any, *, project_id: str, data_type_value: str, error_message: str) -> None:
    """统一的“自动入库失败”日志"""
    logger.warning(
        "自动入库失败: project=%s type=%s error=%s",
        project_id,
        data_type_value,
        error_message,
    )


def log_auto_ingestion_exception(logger: Any, *, project_id: str, data_type_value: str, exc: Exception) -> None:
    """统一的“自动入库异常”日志"""
    logger.error(
        "自动入库异常: project=%s type=%s error=%s",
        project_id,
        data_type_value,
        str(exc),
    )


async def run_ingestion_task(
    project_id: str,
    user_id: int,
    data_type: Any,
    vector_store: Any,
    llm_service: Any,
    service_factory: Callable[[Any, Any, Any, int], Any],
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


async def trigger_auto_ingestion_task(
    *,
    project_id: str,
    user_id: int,
    data_type: Any,
    vector_store: Optional[Any],
    llm_service: Optional[Any],
    logger: Any,
    service_factory: Callable[[Any, Any, Any, int], Any],
    log_success: Callable[[Any], None],
) -> None:
    """通用的“触发自动入库”模板实现（失败不影响主流程）"""
    if should_skip_auto_ingestion(vector_store, llm_service):
        log_skip_auto_ingestion(logger, project_id=project_id, data_type_value=data_type.value)
        return

    try:
        result = await run_ingestion_task(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
            service_factory=service_factory,
        )

        if result.success:
            log_success(result)
        else:
            log_auto_ingestion_failure(
                logger,
                project_id=project_id,
                data_type_value=data_type.value,
                error_message=result.error_message,
            )

    except Exception as exc:
        log_auto_ingestion_exception(logger, project_id=project_id, data_type_value=data_type.value, exc=exc)


def schedule_auto_ingestion_task(
    *,
    trigger_func: Any,
    task_name: str,
    logger: Any,
    project_id: str,
    user_id: int,
    data_type: Any,
    vector_store: Optional[Any],
    llm_service: Optional[Any],
) -> None:
    """通用的“调度自动入库任务”模板实现（不阻塞当前流程）"""
    if should_skip_auto_ingestion(vector_store, llm_service):
        return

    asyncio.create_task(
        trigger_func(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        ),
        name=task_name,
    )

    logger.debug(
        "已调度入库任务: project=%s type=%s",
        project_id,
        data_type.value,
    )


def schedule_multiple_ingestions(
    schedule_ingestion_func: Callable[..., None],
    project_id: str,
    user_id: int,
    data_types: Sequence[Any],
    vector_store: Optional[Any] = None,
    llm_service: Optional[Any] = None,
) -> None:
    """调度多个类型的异步入库任务（批量循环收敛）"""
    for data_type in data_types:
        schedule_ingestion_func(project_id, user_id, data_type, vector_store, llm_service)

def build_default_service_factory(ingestion_service_cls: Type[Any]) -> Callable[[Any, Any, Any, int], Any]:
    """
    构建默认的入库服务工厂

    重要：在后台 session 内构造 `LLMService(session)`，避免会话混用。
    """

    def _factory(session: Any, store: Any, _llm: Any, user_id: int) -> Any:
        from ...services.llm_service import LLMService

        return ingestion_service_cls(
            session=session,
            vector_store=store,
            llm_service=LLMService(session),
            user_id=user_id,
        )

    return _factory


def build_default_auto_ingestion_hooks(
    *,
    logger: Any,
    ingestion_service_cls: Type[Any],
    task_name_prefix: str,
    success_log_fmt: str,
    success_log_attrs: Sequence[str],
) -> tuple[Any, Any]:
    """构建默认的 `trigger_async_ingestion/schedule_ingestion`（收敛 Coding/Novel 样板）"""
    service_factory = build_default_service_factory(ingestion_service_cls)

    async def trigger_async_ingestion(
        project_id: str,
        user_id: int,
        data_type: Any,
        vector_store: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        def _log_success(result: Any) -> None:
            values = [getattr(result, name, 0) for name in success_log_attrs]
            logger.info(success_log_fmt, project_id, data_type.value, *values)

        await trigger_auto_ingestion_task(
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
            logger=logger,
            service_factory=service_factory,
            log_success=_log_success,
        )

    def schedule_ingestion(
        project_id: str,
        user_id: int,
        data_type: Any,
        vector_store: Optional[Any] = None,
        llm_service: Optional[Any] = None,
    ) -> None:
        schedule_auto_ingestion_task(
            trigger_func=trigger_async_ingestion,
            task_name=f"{task_name_prefix}{project_id}_{data_type.value}",
            logger=logger,
            project_id=project_id,
            user_id=user_id,
            data_type=data_type,
            vector_store=vector_store,
            llm_service=llm_service,
        )

    return trigger_async_ingestion, schedule_ingestion


__all__ = [
    "build_default_auto_ingestion_hooks",
    "build_default_service_factory",
    "log_auto_ingestion_exception",
    "log_auto_ingestion_failure",
    "log_skip_auto_ingestion",
    "run_ingestion_task",
    "schedule_multiple_ingestions",
    "schedule_auto_ingestion_task",
    "should_skip_auto_ingestion",
    "trigger_auto_ingestion_task",
]
