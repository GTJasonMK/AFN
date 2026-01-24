"""
RAG检索辅助工具

用于构建查询文本与获取查询向量，减少不同服务的重复逻辑。
"""

from typing import Iterable, Optional, Any


def build_query_text(parts: Iterable[str], fallback: str = "") -> str:
    """
    构建检索查询文本

    Args:
        parts: 候选文本片段
        fallback: 兜底文本（当所有片段为空时使用）
    """
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if cleaned:
        return "\n".join(cleaned)
    return fallback


async def get_query_embedding(
    llm_service: Any,
    query_text: str,
    user_id: int,
    *,
    logger: Optional[Any] = None,
) -> Optional[Any]:
    """
    生成查询向量

    Args:
        llm_service: LLM服务（提供 get_embedding）
        query_text: 查询文本
        user_id: 用户ID
        logger: 可选日志实例
    """
    if not query_text:
        return None

    try:
        return await llm_service.get_embedding(query_text, user_id=user_id)
    except Exception as exc:
        if logger:
            logger.warning("获取查询embedding失败: %s", exc)
        return None
