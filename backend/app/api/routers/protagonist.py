"""主角档案管理路由

处理主角档案的CRUD、属性操作、同步、历史查询等功能。
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import get_default_user
from ...db.session import get_session
from ...models.novel import NovelProject, Chapter
from ...repositories.novel_repository import NovelRepository
from ...repositories.chapter_repository import ChapterRepository
from ...schemas.protagonist import (
    ProtagonistProfileCreate,
    ProtagonistProfileResponse,
    ProtagonistProfileSummary,
    AttributeAddRequest,
    AttributeModifyRequest,
    AttributeDeleteRequest,
    AttributeChangeResponse,
    ChangeHistoryQuery,
    BehaviorRecordResponse,
    BehaviorRecordQuery,
    DeletionMarkResponse,
    DeletionMarkQuery,
    SyncRequest,
    SyncResult,
    ImplicitStatsQuery,
    ImplicitStatsResponse,
    ImplicitCheckRequest,
    ImplicitCheckResponse,
    AttributeCategory,
)
from ...schemas.user import UserInDB
from ...services.protagonist_profile import (
    ProtagonistProfileService,
    ProtagonistAnalysisService,
    ImplicitAttributeTracker,
    DeletionProtectionService,
    ProtagonistSyncService,
)
from ...services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter()


# ============== 依赖注入辅助函数 ==============

async def get_profile_service(
    session: AsyncSession = Depends(get_session),
) -> ProtagonistProfileService:
    """获取主角档案服务"""
    return ProtagonistProfileService(session)


async def get_implicit_tracker(
    session: AsyncSession = Depends(get_session),
) -> ImplicitAttributeTracker:
    """获取隐性属性追踪器"""
    return ImplicitAttributeTracker(session)


async def get_deletion_protection(
    session: AsyncSession = Depends(get_session),
) -> DeletionProtectionService:
    """获取删除保护服务"""
    return DeletionProtectionService(session)


async def get_analysis_service(
    session: AsyncSession = Depends(get_session),
) -> ProtagonistAnalysisService:
    """获取分析服务"""
    from app.services.prompt_service import PromptService
    llm_service = LLMService(session)
    prompt_service = PromptService(session)
    return ProtagonistAnalysisService(session, llm_service, prompt_service)


async def get_sync_service(
    session: AsyncSession = Depends(get_session),
) -> ProtagonistSyncService:
    """获取同步服务"""
    from app.services.prompt_service import PromptService
    profile_service = ProtagonistProfileService(session)
    llm_service = LLMService(session)
    prompt_service = PromptService(session)
    analysis_service = ProtagonistAnalysisService(session, llm_service, prompt_service)
    implicit_tracker = ImplicitAttributeTracker(session)
    deletion_protection = DeletionProtectionService(session)

    return ProtagonistSyncService(
        session=session,
        profile_service=profile_service,
        analysis_service=analysis_service,
        implicit_tracker=implicit_tracker,
        deletion_protection=deletion_protection
    )


async def verify_project_exists(
    project_id: str,
    session: AsyncSession = Depends(get_session),
) -> NovelProject:
    """验证项目存在"""
    repo = NovelRepository(session)
    project = await repo.get(id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    return project


# ============== 档案CRUD ==============

@router.get("/{project_id}/protagonist-profiles", response_model=List[ProtagonistProfileSummary])
async def list_protagonist_profiles(
    project_id: str = Path(..., description="项目ID"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
) -> List[ProtagonistProfileSummary]:
    """获取项目下所有主角档案列表"""
    profiles = await profile_service.get_all_profiles(project_id)

    summaries = []
    for profile in profiles:
        summaries.append(ProtagonistProfileSummary(
            id=profile.id,
            character_name=profile.character_name,
            last_synced_chapter=profile.last_synced_chapter,
            attribute_counts={
                "explicit": len(profile.explicit_attributes or {}),
                "implicit": len(profile.implicit_attributes or {}),
                "social": len(profile.social_attributes or {}),
            },
            created_at=profile.created_at,
        ))

    return summaries


@router.post("/{project_id}/protagonist-profiles", response_model=ProtagonistProfileResponse)
async def create_protagonist_profile(
    project_id: str = Path(..., description="项目ID"),
    data: ProtagonistProfileCreate = Body(...),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    session: AsyncSession = Depends(get_session),
) -> ProtagonistProfileResponse:
    """创建主角档案"""
    try:
        profile = await profile_service.create_profile(
            project_id=project_id,
            character_name=data.character_name,
            initial_attributes=data
        )
        await session.commit()
        return ProtagonistProfileResponse.model_validate(profile)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/protagonist-profiles/{name}", response_model=ProtagonistProfileResponse)
async def get_protagonist_profile(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
) -> ProtagonistProfileResponse:
    """获取单个主角档案详情"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")
    return ProtagonistProfileResponse.model_validate(profile)


@router.delete("/{project_id}/protagonist-profiles/{name}")
async def delete_protagonist_profile(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """删除主角档案"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    await profile_service.delete_profile(profile.id)
    await session.commit()
    return {"success": True, "message": f"已删除角色 {name} 的档案"}


# ============== 属性操作 ==============

@router.post("/{project_id}/protagonist-profiles/{name}/attributes", response_model=AttributeChangeResponse)
async def add_attribute(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    data: AttributeAddRequest = Body(...),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    session: AsyncSession = Depends(get_session),
) -> AttributeChangeResponse:
    """添加属性"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    try:
        change = await profile_service.add_attribute(
            profile_id=profile.id,
            category=data.category.value,
            key=data.key,
            value=data.value,
            event_cause=data.event_cause,
            evidence=data.evidence,
            chapter_number=data.chapter_number
        )
        await session.commit()
        return AttributeChangeResponse.model_validate(change)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{project_id}/protagonist-profiles/{name}/attributes/{category}/{key}", response_model=AttributeChangeResponse)
async def modify_attribute(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    category: AttributeCategory = Path(..., description="属性类别"),
    key: str = Path(..., description="属性键名"),
    data: AttributeModifyRequest = Body(...),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    session: AsyncSession = Depends(get_session),
) -> AttributeChangeResponse:
    """修改属性"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    try:
        change = await profile_service.modify_attribute(
            profile_id=profile.id,
            category=category.value,
            key=key,
            new_value=data.new_value,
            event_cause=data.event_cause,
            evidence=data.evidence,
            chapter_number=data.chapter_number
        )
        await session.commit()
        return AttributeChangeResponse.model_validate(change)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}/protagonist-profiles/{name}/attributes/{category}/{key}", response_model=DeletionMarkResponse)
async def request_attribute_deletion(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    category: AttributeCategory = Path(..., description="属性类别"),
    key: str = Path(..., description="属性键名"),
    data: AttributeDeleteRequest = Body(...),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    deletion_protection: DeletionProtectionService = Depends(get_deletion_protection),
    session: AsyncSession = Depends(get_session),
) -> DeletionMarkResponse:
    """请求删除属性（标记删除）"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    mark = await deletion_protection.add_mark(
        profile_id=profile.id,
        category=category.value,
        key=key,
        reason=data.reason,
        evidence=data.evidence,
        chapter_number=data.chapter_number
    )
    await session.commit()
    return DeletionMarkResponse.model_validate(mark)


# ============== 章节同步 ==============

@router.post("/{project_id}/protagonist-profiles/{name}/sync", response_model=SyncResult)
async def sync_from_chapter(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    data: SyncRequest = Body(...),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    sync_service: ProtagonistSyncService = Depends(get_sync_service),
    desktop_user: UserInDB = Depends(get_default_user),
    session: AsyncSession = Depends(get_session),
) -> SyncResult:
    """从章节同步更新档案"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    # 获取章节内容
    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get(project_id=project_id, chapter_number=data.chapter_number)
    if not chapter or not chapter.selected_version_id:
        raise HTTPException(
            status_code=404,
            detail=f"第 {data.chapter_number} 章不存在或未生成内容"
        )

    # 获取选中版本的内容
    from ...repositories.chapter_version_repository import ChapterVersionRepository
    version_repo = ChapterVersionRepository(session)
    version = await version_repo.get(id=chapter.selected_version_id)
    if not version or not version.content:
        raise HTTPException(
            status_code=404,
            detail=f"第 {data.chapter_number} 章内容为空"
        )

    result = await sync_service.sync_from_chapter(
        profile_id=profile.id,
        chapter_number=data.chapter_number,
        chapter_content=version.content,
        user_id=desktop_user.id
    )
    await session.commit()
    return result


# ============== 历史查询 ==============

@router.get("/{project_id}/protagonist-profiles/{name}/history", response_model=List[AttributeChangeResponse])
async def get_change_history(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    start_chapter: Optional[int] = Query(None, description="起始章节", ge=1),
    end_chapter: Optional[int] = Query(None, description="结束章节", ge=1),
    category: Optional[AttributeCategory] = Query(None, description="属性类别"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
) -> List[AttributeChangeResponse]:
    """获取属性变更历史"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    changes = await profile_service.get_change_history(
        profile_id=profile.id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        category=category.value if category else None
    )

    return [AttributeChangeResponse.model_validate(c) for c in changes]


@router.get("/{project_id}/protagonist-profiles/{name}/behaviors", response_model=List[BehaviorRecordResponse])
async def get_behavior_records(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    chapter: Optional[int] = Query(None, description="指定章节", ge=1),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    implicit_tracker: ImplicitAttributeTracker = Depends(get_implicit_tracker),
) -> List[BehaviorRecordResponse]:
    """获取行为记录"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    if chapter:
        records = await implicit_tracker.get_behaviors_by_chapter(profile.id, chapter)
    else:
        records = await implicit_tracker.get_recent_behaviors(profile.id, limit)

    return [BehaviorRecordResponse.model_validate(r) for r in records]


# ============== 删除标记管理 ==============

@router.get("/{project_id}/protagonist-profiles/{name}/deletion-marks", response_model=List[DeletionMarkResponse])
async def get_deletion_marks(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    category: Optional[AttributeCategory] = Query(None, description="属性类别"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    deletion_protection: DeletionProtectionService = Depends(get_deletion_protection),
) -> List[DeletionMarkResponse]:
    """获取删除标记"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    marks = await deletion_protection.get_marks(
        profile_id=profile.id,
        category=category.value if category else None
    )

    return [DeletionMarkResponse.model_validate(m) for m in marks]


@router.post("/{project_id}/protagonist-profiles/{name}/deletion-marks/{category}/{key}/execute")
async def execute_deletion(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    category: AttributeCategory = Path(..., description="属性类别"),
    key: str = Path(..., description="属性键名"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    deletion_protection: DeletionProtectionService = Depends(get_deletion_protection),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """手动执行删除（需满足5次标记条件）"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    # 检查是否达到阈值
    ready, count = await deletion_protection.check_ready_for_deletion(
        profile.id, category.value, key
    )

    if not ready:
        raise HTTPException(
            status_code=400,
            detail=f"未达到删除阈值，当前连续标记次数: {count}/5"
        )

    # 执行删除
    try:
        await profile_service.delete_attribute(
            profile_id=profile.id,
            category=category.value,
            key=key,
            event_cause=f"手动执行删除（连续{count}次标记）",
            evidence="用户手动确认删除",
            chapter_number=profile.last_synced_chapter
        )
        await deletion_protection.mark_as_executed(profile.id, category.value, key)
        await session.commit()
        return {"success": True, "message": f"已删除属性 {category.value}.{key}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{project_id}/protagonist-profiles/{name}/deletion-marks/{category}/{key}/reset")
async def reset_deletion_marks(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    category: AttributeCategory = Path(..., description="属性类别"),
    key: str = Path(..., description="属性键名"),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    deletion_protection: DeletionProtectionService = Depends(get_deletion_protection),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """重置删除标记"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    reset = await deletion_protection.reset_marks(profile.id, category.value, key)
    await session.commit()

    if reset:
        return {"success": True, "message": f"已重置属性 {category.value}.{key} 的删除标记"}
    else:
        return {"success": False, "message": "没有可重置的删除标记"}


# ============== 隐性属性分析 ==============

@router.get("/{project_id}/protagonist-profiles/{name}/implicit-stats", response_model=ImplicitStatsResponse)
async def get_implicit_stats(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    attribute_key: str = Query(..., description="属性键名"),
    window: int = Query(10, description="统计窗口大小", ge=1, le=50),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    implicit_tracker: ImplicitAttributeTracker = Depends(get_implicit_tracker),
) -> ImplicitStatsResponse:
    """获取隐性属性的符合/不符合统计"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    stats = await implicit_tracker.get_non_conform_stats(
        profile_id=profile.id,
        attribute_key=attribute_key,
        window_chapters=window
    )

    threshold_reached = await implicit_tracker.check_update_threshold(
        profile_id=profile.id,
        attribute_key=attribute_key,
        window_chapters=window
    )

    return ImplicitStatsResponse(
        attribute_key=attribute_key,
        total=stats["total"],
        conform_count=stats["conform_count"],
        non_conform_count=stats["non_conform_count"],
        conform_rate=stats["conform_rate"],
        threshold_reached=threshold_reached
    )


@router.post("/{project_id}/protagonist-profiles/{name}/implicit-check", response_model=ImplicitCheckResponse)
async def check_implicit_update(
    project_id: str = Path(..., description="项目ID"),
    name: str = Path(..., description="角色名称"),
    data: ImplicitCheckRequest = Body(...),
    _: NovelProject = Depends(verify_project_exists),
    profile_service: ProtagonistProfileService = Depends(get_profile_service),
    implicit_tracker: ImplicitAttributeTracker = Depends(get_implicit_tracker),
    analysis_service: ProtagonistAnalysisService = Depends(get_analysis_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ImplicitCheckResponse:
    """检查是否需要更新某个隐性属性（LLM建议）"""
    profile = await profile_service.get_profile(project_id, name)
    if not profile:
        raise HTTPException(status_code=404, detail=f"角色 {name} 的档案不存在")

    # 检查属性是否存在
    implicit_attrs = profile.implicit_attributes or {}
    if data.attribute_key not in implicit_attrs:
        raise HTTPException(
            status_code=404,
            detail=f"隐性属性 {data.attribute_key} 不存在"
        )

    current_value = implicit_attrs[data.attribute_key]

    # 获取统计和证据
    stats = await implicit_tracker.get_non_conform_stats(
        profile_id=profile.id,
        attribute_key=data.attribute_key
    )

    evidence = await implicit_tracker.get_behavior_evidence(
        profile_id=profile.id,
        attribute_key=data.attribute_key
    )

    # 请求LLM决策
    decision = await analysis_service.decide_implicit_update(
        attribute_key=data.attribute_key,
        current_value=current_value,
        behavior_records=evidence,
        non_conform_count=stats["non_conform_count"],
        user_id=desktop_user.id
    )

    return ImplicitCheckResponse(
        attribute_key=data.attribute_key,
        current_value=current_value,
        decision=decision.decision,
        reasoning=decision.reasoning,
        suggested_new_value=decision.new_value,
        evidence_summary=decision.evidence_summary
    )
