"""
编程项目RAG路由

处理编程项目的向量入库和检索操作。
支持10种数据类型的入库和按类型过滤的检索。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_coding_project_service,
    get_vector_store,
)
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.llm_service import LLMService
from ....services.coding import CodingProjectService
from ....services.vector_store_service import VectorStoreService
from ....services.coding_rag import (
    CodingProjectIngestionService,
    CodingDataType,
    CompletenessReport,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_default_source(data_type: Optional[str], chapter_number: int) -> str:
    """
    根据数据类型生成默认来源显示

    当chunk的chapter_title为空时，根据data_type生成合适的默认来源。

    Args:
        data_type: 数据类型标识
        chapter_number: 章节/序号

    Returns:
        来源显示字符串
    """
    if not data_type:
        return f"未知来源 {chapter_number}"

    type_display_map = {
        "inspiration": f"对话轮次{chapter_number}",
        "architecture": f"架构设计{chapter_number}",
        "tech_stack": f"技术栈{chapter_number}",
        "requirement": f"核心需求{chapter_number}",
        "challenge": f"技术挑战{chapter_number}",
        "system": f"系统{chapter_number}",
        "module": f"模块{chapter_number}",
        "feature_outline": f"功能大纲{chapter_number}",
        "dependency": f"模块依赖{chapter_number}",
        "feature_prompt": f"功能{chapter_number}",
    }

    return type_display_map.get(data_type, f"功能 {chapter_number}")


class ReindexResponse(BaseModel):
    """重新入库响应"""
    success: bool
    indexed_count: int
    message: str


class FullIngestionRequest(BaseModel):
    """完整入库请求"""
    force: bool = Field(default=False, description="是否强制全量入库（默认只入库不完整的类型）")


class FullIngestionResponse(BaseModel):
    """完整入库响应"""
    success: bool
    is_complete: bool = False  # 入库前是否已经完整
    total_items: int
    added: int
    skipped: int = 0  # 跳过的类型数
    failed: int
    details: Dict[str, Any]


class TypeCompletenessDetail(BaseModel):
    """类型完整性详情"""
    db_count: int
    vector_count: int
    complete: bool
    missing: int
    display_name: str


class CompletenessResponse(BaseModel):
    """完整性检查响应"""
    project_id: str
    complete: bool
    total_db_count: int
    total_vector_count: int
    types: Dict[str, TypeCompletenessDetail]


class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    query: str = Field(..., min_length=1, description="查询内容")
    top_k: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    data_types: Optional[List[str]] = Field(default=None, description="限定数据类型（可选）")
    use_type_weights: bool = Field(default=True, description="是否使用类型权重")


class RAGChunk(BaseModel):
    """RAG检索结果片段"""
    content: str
    chapter_number: int
    source: str
    score: float
    data_type: Optional[str] = None


class RAGSummary(BaseModel):
    """RAG检索结果摘要"""
    chapter_number: int
    title: str
    summary: str
    score: float


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""
    chunks: List[RAGChunk]
    summaries: List[RAGSummary]


# ==================== 诊断端点 ====================

@router.get("/coding/{project_id}/rag/diagnose")
async def diagnose_rag_data(
    project_id: str,
    user: UserInDB = Depends(get_default_user),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    诊断RAG数据状态 - 用于排查问题

    返回项目的RAG数据详细信息，包括有无data_type字段的记录数。
    """
    if vector_store is None or not vector_store._client:
        return {"error": "向量库未启用"}

    # 验证项目
    project = await coding_project_service.get_project_schema(project_id, user.id)
    if not project:
        return {"error": "项目不存在"}

    await vector_store.ensure_schema()

    diagnosis = {
        "project_id": project_id,
        "total_chunks": 0,
        "chunks_with_data_type": 0,
        "chunks_without_data_type": 0,
        "data_type_distribution": {},
        "sample_without_data_type": [],
        "sample_with_data_type": [],
    }

    try:
        # 总数
        sql = "SELECT COUNT(*) as cnt FROM rag_chunks WHERE project_id = :project_id"
        result = await vector_store._client.execute(sql, {"project_id": project_id})
        for row in vector_store._iter_rows(result):
            diagnosis["total_chunks"] = row.get("cnt", 0)
            break

        # 有data_type的数量
        sql = """
        SELECT COUNT(*) as cnt FROM rag_chunks
        WHERE project_id = :project_id
        AND json_extract(metadata, '$.data_type') IS NOT NULL
        AND json_extract(metadata, '$.data_type') != ''
        """
        result = await vector_store._client.execute(sql, {"project_id": project_id})
        for row in vector_store._iter_rows(result):
            diagnosis["chunks_with_data_type"] = row.get("cnt", 0)
            break

        # 没有data_type的数量
        diagnosis["chunks_without_data_type"] = diagnosis["total_chunks"] - diagnosis["chunks_with_data_type"]

        # data_type分布
        sql = """
        SELECT json_extract(metadata, '$.data_type') as dtype, COUNT(*) as cnt
        FROM rag_chunks
        WHERE project_id = :project_id
        GROUP BY dtype
        """
        result = await vector_store._client.execute(sql, {"project_id": project_id})
        for row in vector_store._iter_rows(result):
            dtype = row.get("dtype") or "(无)"
            diagnosis["data_type_distribution"][dtype] = row.get("cnt", 0)

        # 采样没有data_type的记录
        sql = """
        SELECT id, chapter_number, chapter_title, SUBSTR(content, 1, 100) as content_preview,
               metadata
        FROM rag_chunks
        WHERE project_id = :project_id
        AND (json_extract(metadata, '$.data_type') IS NULL OR json_extract(metadata, '$.data_type') = '')
        LIMIT 3
        """
        result = await vector_store._client.execute(sql, {"project_id": project_id})
        for row in vector_store._iter_rows(result):
            diagnosis["sample_without_data_type"].append({
                "id": row.get("id", "")[:50],
                "chapter_number": row.get("chapter_number"),
                "chapter_title": row.get("chapter_title"),
                "content_preview": row.get("content_preview"),
            })

        # 采样有data_type的记录
        sql = """
        SELECT id, chapter_number, chapter_title, SUBSTR(content, 1, 100) as content_preview,
               json_extract(metadata, '$.data_type') as dtype
        FROM rag_chunks
        WHERE project_id = :project_id
        AND json_extract(metadata, '$.data_type') IS NOT NULL
        AND json_extract(metadata, '$.data_type') != ''
        LIMIT 3
        """
        result = await vector_store._client.execute(sql, {"project_id": project_id})
        for row in vector_store._iter_rows(result):
            diagnosis["sample_with_data_type"].append({
                "id": row.get("id", "")[:50],
                "chapter_number": row.get("chapter_number"),
                "chapter_title": row.get("chapter_title"),
                "data_type": row.get("dtype"),
                "content_preview": row.get("content_preview"),
            })

    except Exception as e:
        diagnosis["error"] = str(e)

    return diagnosis


# ==================== 完整性检查 ====================

@router.get("/coding/{project_id}/rag/completeness", response_model=CompletenessResponse)
async def check_rag_completeness(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    检查编程项目的RAG入库完整性

    对比数据库记录数和向量库记录数，返回各类型的完整性状态。
    """
    # 检查向量库是否启用
    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="向量库未启用，请在设置中配置嵌入服务"
        )

    # 获取项目数据
    project = await coding_project_service.get_project_schema(project_id, user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 创建入库服务并检查完整性
    ingestion_service = CodingProjectIngestionService(
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=user.id
    )

    report = await ingestion_service.check_completeness(project_id)

    logger.info(
        "RAG完整性检查: project=%s complete=%s db_total=%d vector_total=%d "
        "new=%d modified=%d deleted=%d",
        project_id, report.complete,
        report.total_db_count, report.total_vector_count,
        report.total_new, report.total_modified, report.total_deleted
    )

    # 转换为响应格式
    types_detail = {}
    for type_name, detail in report.type_details.items():
        types_detail[type_name] = TypeCompletenessDetail(
            db_count=detail["db_count"],
            vector_count=detail["vector_count"],
            complete=detail["complete"],
            missing=detail["missing"],
            display_name=detail["display_name"]
        )

    return CompletenessResponse(
        project_id=project_id,
        complete=report.complete,
        total_db_count=report.total_db_count,
        total_vector_count=report.total_vector_count,
        types=types_detail
    )


# ==================== 完整入库 ====================

@router.post("/coding/{project_id}/rag/ingest-all", response_model=FullIngestionResponse)
async def ingest_all_rag_data(
    project_id: str,
    request: Optional[FullIngestionRequest] = None,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    将编程项目的所有数据入库到向量数据库

    智能入库模式（默认）：先检查完整性，只入库不完整的类型。
    强制模式（force=True）：遍历10种数据类型，全部重新入库。
    """
    # 检查向量库是否启用
    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="向量库未启用，请在设置中配置嵌入服务"
        )

    # 获取项目数据
    project = await coding_project_service.get_project_schema(project_id, user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 创建入库服务
    ingestion_service = CodingProjectIngestionService(
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=user.id
    )

    # 提取force参数（默认False，智能入库模式）
    force = request.force if request else False

    logger.info(
        "=== RAG入库API调用 === project=%s force=%s request=%s",
        project_id, force, request
    )

    # 执行入库（智能模式会先检查完整性，只入库不完整的类型）
    results = await ingestion_service.ingest_full_project(project_id, force=force)

    # 如果结果为空，说明已经完整，无需入库
    if not results:
        logger.info("项目 %s RAG数据已完整，无需入库", project_id)
        return FullIngestionResponse(
            success=True,
            is_complete=True,
            total_items=0,
            added=0,
            skipped=10,  # 10种类型全部跳过
            failed=0,
            details={}
        )

    # 统计结果
    total_items = 0
    added = 0
    skipped = 0
    failed = 0
    details = {}

    for type_name, result in results.items():
        # 检查是否是跳过的类型（skipped_count > 0）
        if result.skipped_count > 0:
            skipped += 1
            details[type_name] = {
                "success": True,
                "skipped": True,
                "display_name": CodingDataType.get_display_name(type_name)
            }
        else:
            total_items += result.total_records
            added += result.added_count
            failed += result.failed_count
            details[type_name] = {
                "success": result.success,
                "total_records": result.total_records,
                "added_count": result.added_count,
                "failed_count": result.failed_count,
                "error_message": result.error_message,
                "display_name": CodingDataType.get_display_name(type_name)
            }

    logger.info(
        "智能入库完成: project=%s total=%d added=%d skipped=%d failed=%d",
        project_id, total_items, added, skipped, failed
    )

    return FullIngestionResponse(
        success=failed == 0,
        is_complete=False,
        total_items=total_items,
        added=added,
        skipped=skipped,
        failed=failed,
        details=details
    )


@router.post("/coding/{project_id}/rag/reindex", response_model=ReindexResponse)
async def reindex_coding_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserInDB = Depends(get_default_user),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    将编程项目的文件Prompt入库到向量数据库

    使用CodingProjectIngestionService进行入库，与ingest_all_rag_data保持一致。
    这是一个幂等操作，会增量更新索引。
    """
    # 检查向量库是否启用
    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="向量库未启用，请在设置中配置嵌入服务"
        )

    # 验证项目归属
    await coding_project_service.ensure_project_owner(project_id, user.id)

    # 使用CodingProjectIngestionService进行入库（与ingest_all_rag_data一致）
    ingestion_service = CodingProjectIngestionService(
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=user.id
    )

    try:
        result = await ingestion_service.ingest_by_type(
            project_id=project_id,
            data_type=CodingDataType.FILE_PROMPT
        )

        if result.success:
            if result.total_records == 0:
                message = "项目暂无已生成的文件Prompt内容"
            else:
                message = f"成功入库 {result.added_count} 个文件Prompt片段"
            return ReindexResponse(
                success=True,
                indexed_count=result.added_count,
                message=message
            )
        else:
            return ReindexResponse(
                success=False,
                indexed_count=0,
                message=f"入库失败: {result.error_message}"
            )

    except Exception as e:
        logger.error(
            "文件Prompt入库失败: project=%s error=%s",
            project_id, str(e)
        )
        return ReindexResponse(
            success=False,
            indexed_count=0,
            message=f"入库失败: {str(e)}"
        )


@router.post("/coding/{project_id}/rag/query", response_model=RAGQueryResponse)
async def query_coding_rag(
    project_id: str,
    request: RAGQueryRequest,
    user: UserInDB = Depends(get_default_user),
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    vector_store: Optional[VectorStoreService] = Depends(get_vector_store),
):
    """
    检索编程项目的RAG上下文

    根据查询内容从向量数据库中检索相关的功能Prompt片段。
    """
    # 检查向量库是否启用
    if vector_store is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="向量库未启用，请在设置中配置嵌入服务"
        )

    # 验证项目存在
    project = await coding_project_service.get_project_schema(project_id, user.id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )

    # 生成查询向量
    query_embedding = await llm_service.get_embedding(
        request.query,
        user_id=user.id
    )
    if not query_embedding:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成查询向量失败，请检查嵌入服务配置"
        )

    # 检索片段
    # 如果指定了类型过滤，需要over-fetch以确保过滤后仍有足够数量
    fetch_multiplier = 3 if request.data_types else 1
    fetch_top_k = request.top_k * fetch_multiplier

    chunks = await vector_store.query_chunks(
        project_id=project_id,
        embedding=query_embedding,
        top_k=fetch_top_k
    )

    # 调试日志：记录检索到的原始数据
    logger.info(
        "RAG查询: project=%s query='%s' 检索到 %d 个chunks (请求 %d)",
        project_id, request.query[:50], len(chunks), fetch_top_k
    )
    for i, chunk in enumerate(chunks[:3]):  # 只记录前3个
        meta = chunk.metadata or {}
        logger.info(
            "  chunk[%d]: chapter_title='%s' chapter_number=%d data_type='%s' meta_keys=%s",
            i,
            chunk.chapter_title or "(空)",
            chunk.chapter_number,
            meta.get("data_type", "(无)"),
            list(meta.keys())
        )

    # 检索摘要
    summaries = await vector_store.query_summaries(
        project_id=project_id,
        embedding=query_embedding,
        top_k=min(request.top_k, 5)  # 摘要数量限制
    )

    # 转换结果，包含data_type信息
    chunk_results = []
    for chunk in chunks:
        # 从metadata中获取data_type
        data_type = chunk.metadata.get("data_type") if chunk.metadata else None

        # 如果指定了类型过滤，跳过不匹配的结果
        if request.data_types and data_type not in request.data_types:
            continue

        # 应用类型权重（如果启用）
        weighted_score = chunk.score
        if request.use_type_weights and data_type:
            weight = CodingDataType.get_weight(data_type)
            # 权重越高，分数越低（距离越近）
            weighted_score = chunk.score / weight if weight > 0 else chunk.score

        # 根据数据类型生成默认来源（当chapter_title为空时）
        source = chunk.chapter_title
        if not source:
            source = _get_default_source(data_type, chunk.chapter_number)

        chunk_results.append(RAGChunk(
            content=chunk.content,
            chapter_number=chunk.chapter_number,
            source=source,
            score=weighted_score,
            data_type=data_type
        ))

    # 按加权分数重新排序
    if request.use_type_weights:
        chunk_results.sort(key=lambda x: x.score)

    # 限制返回数量
    chunk_results = chunk_results[:request.top_k]

    summary_results = [
        RAGSummary(
            chapter_number=s.chapter_number,
            title=s.title,
            summary=s.summary,
            score=s.score
        )
        for s in summaries
    ]

    return RAGQueryResponse(
        chunks=chunk_results,
        summaries=summary_results
    )


__all__ = ["router"]
