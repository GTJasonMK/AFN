"""
RAG 查询路由

提供RAG检索测试接口，用于实时验证向量检索效果。
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user, get_vector_store
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.vector_store_service import VectorStoreService, RetrievedChunk, RetrievedSummary
from ....services.embedding_service import EmbeddingService
from ....exceptions import LLMConfigurationError

logger = logging.getLogger(__name__)

router = APIRouter()


class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    query: str = Field(..., min_length=1, max_length=2000, description="查询文本")
    top_k: Optional[int] = Field(default=10, ge=1, le=50, description="返回结果数量")


class ChunkResult(BaseModel):
    """剧情片段检索结果"""
    content: str = Field(..., description="片段内容")
    chapter_number: int = Field(..., description="章节编号")
    chapter_title: Optional[str] = Field(None, description="章节标题")
    score: float = Field(..., description="相似度分数（越小越相似）")
    metadata: dict = Field(default_factory=dict, description="元数据")


class SummaryResult(BaseModel):
    """章节摘要检索结果"""
    chapter_number: int = Field(..., description="章节编号")
    title: str = Field(..., description="章节标题")
    summary: str = Field(..., description="章节摘要")
    score: float = Field(..., description="相似度分数（越小越相似）")


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""
    query: str = Field(..., description="原始查询文本")
    chunks: List[ChunkResult] = Field(default_factory=list, description="剧情片段结果")
    summaries: List[SummaryResult] = Field(default_factory=list, description="章节摘要结果")
    embedding_dimension: Optional[int] = Field(None, description="嵌入向量维度")
    message: Optional[str] = Field(None, description="提示信息")


@router.post(
    "/novels/{project_id}/rag/query",
    response_model=RAGQueryResponse,
    summary="RAG检索查询",
    description="对指定项目执行RAG检索，返回与查询文本最相关的剧情片段和章节摘要。"
)
async def query_rag(
    project_id: str,
    request: RAGQueryRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInDB = Depends(get_default_user),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    执行RAG检索查询

    Args:
        project_id: 项目ID
        request: 查询请求，包含查询文本和返回数量

    Returns:
        RAGQueryResponse: 包含剧情片段和章节摘要的检索结果

    Raises:
        HTTPException 400: 向量库未启用
        HTTPException 500: 嵌入模型未配置或服务错误
    """
    logger.info(
        "RAG查询请求: project_id=%s query='%s' top_k=%d",
        project_id,
        request.query[:50] + "..." if len(request.query) > 50 else request.query,
        request.top_k,
    )

    # 检查向量库是否可用
    if vector_store is None:
        logger.warning("RAG查询失败：向量库未启用")
        return RAGQueryResponse(
            query=request.query,
            chunks=[],
            summaries=[],
            message="向量库未启用。请在配置中开启向量库功能。",
        )

    # 生成查询向量
    embedding_service = EmbeddingService(session)
    try:
        query_embedding = await embedding_service.get_embedding(
            request.query,
            user_id=current_user.id,
        )
    except LLMConfigurationError as exc:
        logger.warning("RAG查询失败：嵌入模型未配置: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("生成查询向量失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成查询向量失败: {str(exc)}",
        ) from exc

    if not query_embedding:
        logger.warning("RAG查询失败：生成的查询向量为空")
        return RAGQueryResponse(
            query=request.query,
            chunks=[],
            summaries=[],
            message="生成查询向量失败，请检查嵌入模型配置。",
        )

    embedding_dimension = len(query_embedding)
    logger.info("查询向量生成成功: dimension=%d", embedding_dimension)

    # 执行向量检索
    try:
        # 并行查询剧情片段和章节摘要
        chunks = await vector_store.query_chunks(
            project_id=project_id,
            embedding=query_embedding,
            top_k=request.top_k,
        )

        summaries = await vector_store.query_summaries(
            project_id=project_id,
            embedding=query_embedding,
            top_k=request.top_k,
        )
    except Exception as exc:
        logger.error("向量检索失败: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量检索失败: {str(exc)}",
        ) from exc

    # 转换结果
    chunk_results = [
        ChunkResult(
            content=chunk.content,
            chapter_number=chunk.chapter_number,
            chapter_title=chunk.chapter_title,
            score=chunk.score,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]

    summary_results = [
        SummaryResult(
            chapter_number=summary.chapter_number,
            title=summary.title,
            summary=summary.summary,
            score=summary.score,
        )
        for summary in summaries
    ]

    logger.info(
        "RAG查询完成: project_id=%s chunks=%d summaries=%d",
        project_id,
        len(chunk_results),
        len(summary_results),
    )

    # 构建提示信息
    message = None
    if not chunk_results and not summary_results:
        message = "未找到相关内容。请确保已有章节被选中并完成向量化。"

    return RAGQueryResponse(
        query=request.query,
        chunks=chunk_results,
        summaries=summary_results,
        embedding_dimension=embedding_dimension,
        message=message,
    )
