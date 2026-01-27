"""
小说项目RAG入库管理路由

提供RAG完整性检查、手动入库、诊断等功能。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_llm_service,
    get_vector_store,
)
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService
from ....services.llm_service import LLMService
from ....services.novel_rag import (
    NovelDataType,
    NovelProjectIngestionService,
)
from ....core.constants import LLMConstants
from ..rag_helpers import run_completeness_check
from ..rag_schemas import CompletenessResponseBase, TypeDetailBase
from ..chapter_rag_helpers import (
    ensure_chapter_summary_and_analysis_data_safely,
    get_project_display_title,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 响应模型 ====================

class TypeDetail(TypeDetailBase):
    """单类型完整性详情"""
    new_count: int = Field(default=0, description="新增记录数")
    modified_count: int = Field(default=0, description="修改记录数")
    deleted_count: int = Field(default=0, description="删除记录数")
    has_changes: bool = Field(default=False, description="是否有变动")


class CompletenessResponse(CompletenessResponseBase):
    """完整性检查响应"""
    total_new: int = Field(description="总新增数")
    total_modified: int = Field(description="总修改数")
    total_deleted: int = Field(description="总删除数")
    types: Dict[str, TypeDetail] = Field(description="各类型详情")


class IngestionResultItem(BaseModel):
    """单类型入库结果"""
    data_type: str = Field(description="数据类型")
    display_name: str = Field(description="显示名称")
    success: bool = Field(description="是否成功")
    added_count: int = Field(default=0, description="新增数")
    updated_count: int = Field(default=0, description="更新数")
    skipped: bool = Field(default=False, description="是否跳过")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class FullIngestionResponse(BaseModel):
    """完整入库响应"""
    project_id: str = Field(description="项目ID")
    success: bool = Field(description="是否全部成功")
    is_complete_before: bool = Field(description="入库前是否已完整")
    total_added: int = Field(description="总新增数")
    total_updated: int = Field(description="总更新数")
    total_skipped: int = Field(description="总跳过数")
    results: Dict[str, IngestionResultItem] = Field(description="各类型结果")


class DiagnoseResponse(BaseModel):
    """诊断响应"""
    project_id: str = Field(description="项目ID")
    vector_store_enabled: bool = Field(description="向量库是否启用")
    embedding_service_enabled: bool = Field(description="嵌入服务是否启用")
    completeness: Optional[CompletenessResponse] = Field(default=None, description="完整性报告")
    data_type_list: List[Dict[str, str]] = Field(description="数据类型列表")


def _build_type_detail(type_name: str, detail: Dict[str, Any]) -> TypeDetail:
    """构建单类型完整性详情"""
    return TypeDetail(
        display_name=detail.get("display_name", type_name),
        db_count=detail.get("db_count", 0),
        vector_count=detail.get("vector_count", 0),
        complete=detail.get("complete", False),
        new_count=detail.get("new_count", 0),
        modified_count=detail.get("modified_count", 0),
        deleted_count=detail.get("deleted_count", 0),
        has_changes=detail.get("has_changes", False),
    )


# ==================== API端点 ====================

@router.get("/{project_id}/rag/completeness", response_model=CompletenessResponse)
async def check_rag_completeness(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    vector_store: Optional[Any] = Depends(get_vector_store),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> CompletenessResponse:
    """
    检查项目RAG入库完整性

    返回各数据类型的入库状态，包括：
    - 数据库记录数
    - 向量库记录数
    - 新增/修改/删除的记录数
    - 是否完整

    如果向量库未启用，所有类型将显示为不完整。
    """
    # 验证项目归属
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 检查向量库是否启用
    if not vector_store:
        logger.warning("项目 %s RAG检查: 向量库未启用", project_id)
        # 返回空的完整性报告
        return CompletenessResponse(
            project_id=project_id,
            complete=False,
            total_db_count=0,
            total_vector_count=0,
            total_new=0,
            total_modified=0,
            total_deleted=0,
            types={
                dt.value: TypeDetail(
                    display_name=NovelDataType.get_display_name(dt.value),
                    db_count=0,
                    vector_count=0,
                    complete=False,
                    new_count=0,
                    modified_count=0,
                    deleted_count=0,
                    has_changes=False,
                )
                for dt in NovelDataType.all_types()
            }
        )

    # 执行完整性检查
    report, types_detail = await run_completeness_check(
        project_id=project_id,
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=desktop_user.id,
        service_factory=NovelProjectIngestionService,
        build_detail=_build_type_detail,
        log_message=lambda rep: logger.info(
            "项目 %s RAG完整性检查: complete=%s db=%d vector=%d new=%d mod=%d del=%d",
            project_id, rep.complete,
            rep.total_db_count, rep.total_vector_count,
            rep.total_new, rep.total_modified, rep.total_deleted
        ),
    )

    return CompletenessResponse(
        project_id=project_id,
        complete=report.complete,
        total_db_count=report.total_db_count,
        total_vector_count=report.total_vector_count,
        total_new=report.total_new,
        total_modified=report.total_modified,
        total_deleted=report.total_deleted,
        types=types_detail,
    )


@router.post("/{project_id}/rag/ingest-all", response_model=FullIngestionResponse)
async def ingest_all_rag_data(
    project_id: str,
    force: bool = Query(False, description="强制全量重建（忽略已有数据）"),
    novel_service: NovelService = Depends(get_novel_service),
    vector_store: Optional[Any] = Depends(get_vector_store),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> FullIngestionResponse:
    """
    完整入库项目RAG数据

    流程：
    1. 对缺少摘要/分析数据的章节进行分析
    2. 更新角色状态和伏笔索引
    3. 将所有数据向量化入库

    Args:
        force: 是否强制全量重建
            - False（默认）: 智能模式，只入库不完整的类型
            - True: 强制模式，删除所有旧数据后全量重建

    返回各数据类型的入库结果。
    """
    from ....services.chapter_analysis_service import ChapterAnalysisService
    from ....services.incremental_indexer import IncrementalIndexer
    from ....repositories.chapter_outline_repository import ChapterOutlineRepository

    # 验证项目归属
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 检查向量库是否启用
    if not vector_store:
        logger.warning("项目 %s RAG入库: 向量库未启用", project_id)
        return FullIngestionResponse(
            project_id=project_id,
            success=False,
            is_complete_before=False,
            total_added=0,
            total_updated=0,
            total_skipped=0,
            results={
                dt.value: IngestionResultItem(
                    data_type=dt.value,
                    display_name=NovelDataType.get_display_name(dt.value),
                    success=False,
                    error_message="向量库未启用",
                )
                for dt in NovelDataType.all_types()
            }
        )

    # ===== 第一阶段：对所有已选择版本的章节进行分析 =====
    chapters_with_content = [
        ch for ch in project.chapters
        if ch.selected_version and ch.selected_version.content and ch.selected_version.content.strip()
    ]

    if chapters_with_content:
        logger.info("项目 %s RAG入库: 开始处理 %d 个章节的分析数据", project_id, len(chapters_with_content))

        analysis_service = ChapterAnalysisService(session)
        indexer = IncrementalIndexer(session)
        chapter_outline_repo = ChapterOutlineRepository(session)
        novel_title = get_project_display_title(project_id, project.title)

        for chapter in chapters_with_content:
            content = chapter.selected_version.content
            chapter_number = chapter.chapter_number

            # 获取章节标题
            outline = next(
                (item for item in project.outlines if item.chapter_number == chapter_number),
                None
            )
            chapter_title = outline.title if outline and outline.title else f"第{chapter_number}章"

            # 1-2. 生成摘要 + 章节分析（失败时章节分析降级为 None）
            analysis_data = await ensure_chapter_summary_and_analysis_data_safely(
                project_id=project_id,
                session=session,
                chapter=chapter,
                content=content,
                title=chapter_title,
                chapter_number=chapter_number,
                novel_title=novel_title,
                user_id=desktop_user.id,
                llm_service=llm_service,
                chapter_outline_repo=chapter_outline_repo,
                timeout=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
                analysis_service=analysis_service,
                log=logger,
            )

            # 3. 索引更新
            if analysis_data:
                await indexer.safe_index_chapter_analysis(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    analysis_data=analysis_data,
                    commit=False,
                )

        # 提交分析结果
        await session.commit()
        logger.info("项目 %s RAG入库: 章节分析完成", project_id)

    # ===== 第二阶段：向量化入库 =====
    service = NovelProjectIngestionService(
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=desktop_user.id
    )

    pre_report = await service.check_completeness(project_id)
    is_complete_before = pre_report.complete

    # 执行入库
    results = await service.ingest_full_project(project_id, force=force)

    # 统计结果
    total_added = 0
    total_updated = 0
    total_skipped = 0
    all_success = True
    results_detail = {}

    for type_name, result in results.items():
        total_added += result.added_count
        total_updated += result.updated_count
        if result.skipped_count > 0:
            total_skipped += 1

        if not result.success:
            all_success = False

        results_detail[type_name] = IngestionResultItem(
            data_type=type_name,
            display_name=NovelDataType.get_display_name(type_name),
            success=result.success,
            added_count=result.added_count,
            updated_count=result.updated_count,
            skipped=result.skipped_count > 0,
            error_message=result.error_message if not result.success else None,
        )

    # 补充未在results中的类型
    for dt in NovelDataType.all_types():
        if dt.value not in results_detail:
            results_detail[dt.value] = IngestionResultItem(
                data_type=dt.value,
                display_name=NovelDataType.get_display_name(dt.value),
                success=True,
                skipped=True,
            )

    logger.info(
        "项目 %s RAG入库完成: force=%s added=%d updated=%d skipped=%d",
        project_id, force, total_added, total_updated, total_skipped
    )

    return FullIngestionResponse(
        project_id=project_id,
        success=all_success,
        is_complete_before=is_complete_before,
        total_added=total_added,
        total_updated=total_updated,
        total_skipped=total_skipped,
        results=results_detail,
    )


@router.post("/{project_id}/rag/ingest", response_model=IngestionResultItem)
async def ingest_by_type(
    project_id: str,
    data_type: str = Query(..., description="数据类型"),
    novel_service: NovelService = Depends(get_novel_service),
    vector_store: Optional[Any] = Depends(get_vector_store),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> IngestionResultItem:
    """
    按类型入库RAG数据

    可选的数据类型：
    - inspiration: 灵感对话
    - synopsis: 故事概述
    - world_setting: 世界观设定
    - character: 角色设定
    - relationship: 角色关系
    - character_state: 角色状态
    - protagonist: 主角档案
    - part_outline: 分部大纲
    - chapter_outline: 章节大纲
    - chapter_content: 章节正文
    - chapter_summary: 章节摘要
    - foreshadowing: 伏笔记录
    """
    # 验证项目归属
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 验证数据类型
    try:
        novel_data_type = NovelDataType(data_type)
    except ValueError:
        return IngestionResultItem(
            data_type=data_type,
            display_name=data_type,
            success=False,
            error_message=f"无效的数据类型: {data_type}",
        )

    # 检查向量库是否启用
    if not vector_store:
        return IngestionResultItem(
            data_type=data_type,
            display_name=NovelDataType.get_display_name(data_type),
            success=False,
            error_message="向量库未启用",
        )

    # 执行入库
    service = NovelProjectIngestionService(
        session=session,
        vector_store=vector_store,
        llm_service=llm_service,
        user_id=desktop_user.id
    )

    result = await service.ingest_by_type(project_id, novel_data_type)

    logger.info(
        "项目 %s 入库类型 %s: success=%s added=%d",
        project_id, data_type, result.success, result.added_count
    )

    return IngestionResultItem(
        data_type=data_type,
        display_name=NovelDataType.get_display_name(data_type),
        success=result.success,
        added_count=result.added_count,
        updated_count=result.updated_count,
        error_message=result.error_message if not result.success else None,
    )


@router.get("/{project_id}/rag/diagnose", response_model=DiagnoseResponse)
async def diagnose_rag(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    vector_store: Optional[Any] = Depends(get_vector_store),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DiagnoseResponse:
    """
    RAG诊断

    返回详细的RAG系统状态：
    - 向量库是否启用
    - 嵌入服务是否启用
    - 完整性报告
    - 支持的数据类型列表
    """
    # 验证项目归属
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 检查服务状态
    vector_store_enabled = vector_store is not None
    embedding_service_enabled = llm_service is not None

    # 数据类型列表
    data_type_list = [
        {
            "value": dt.value,
            "display_name": NovelDataType.get_display_name(dt.value),
            "weight": str(NovelDataType.get_weight(dt.value)),
            "source_table": NovelDataType.get_source_table(dt.value),
        }
        for dt in NovelDataType.all_types()
    ]

    # 完整性检查（如果向量库启用）
    completeness = None
    if vector_store_enabled and embedding_service_enabled:
        report, types_detail = await run_completeness_check(
            project_id=project_id,
            session=session,
            vector_store=vector_store,
            llm_service=llm_service,
            user_id=desktop_user.id,
            service_factory=NovelProjectIngestionService,
            build_detail=_build_type_detail,
        )

        completeness = CompletenessResponse(
            project_id=project_id,
            complete=report.complete,
            total_db_count=report.total_db_count,
            total_vector_count=report.total_vector_count,
            total_new=report.total_new,
            total_modified=report.total_modified,
            total_deleted=report.total_deleted,
            types=types_detail,
        )

    logger.info(
        "项目 %s RAG诊断: vector=%s embedding=%s",
        project_id, vector_store_enabled, embedding_service_enabled
    )

    return DiagnoseResponse(
        project_id=project_id,
        vector_store_enabled=vector_store_enabled,
        embedding_service_enabled=embedding_service_enabled,
        completeness=completeness,
        data_type_list=data_type_list,
    )


__all__ = ["router"]
