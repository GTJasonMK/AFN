"""
文件驱动Prompt生成路由

处理编程项目的目录结构管理、源文件管理和文件Prompt生成。
"""

import logging
from typing import List, Optional, Dict, Any, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....db.session import get_session, AsyncSessionLocal
from ....exceptions import ResourceNotFoundError
from ....schemas.user import UserInDB
from ....schemas.coding_files import (
    DirectoryNodeCreate,
    DirectoryNodeUpdate,
    DirectoryNodeResponse,
    DirectoryTreeResponse,
    GenerateDirectoryStructureRequest,
    GenerateDirectoryStructureResponse,
    SourceFileCreate,
    SourceFileUpdate,
    SourceFileResponse,
    SourceFileDetail,
    SourceFileListResponse,
    FileVersionResponse,
    FileVersionListResponse,
    GenerateFilePromptRequest,
    SaveFilePromptRequest,
    SelectFileVersionRequest,
    GenerateReviewPromptRequest,
    SaveReviewPromptRequest,
)
from ....services.coding_files import (
    DirectoryStructureService,
    FilePromptService,
    PlannedDirectory,
)
from ....services.coding_files.directory_generator import (
    DirectoryTreeBuilder,
    BruteForceOutput,
)
from ....services.coding_files.architect import (
    ArchitecturePattern,
    ProjectProfiler,
    ArchitectureDecisionMaker,
    ArchitectureBasedGenerator,
    QualityEvaluator,
    RefinementAgent,
)
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.sse_helpers import sse_event, create_sse_response
from ....repositories.coding_files_repository import CodingAgentStateRepository

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 依赖注入 ====================

async def get_directory_service(
    session: AsyncSession = Depends(get_session),
) -> DirectoryStructureService:
    """获取目录结构服务"""
    return DirectoryStructureService(session)


async def get_file_prompt_service(
    session: AsyncSession = Depends(get_session),
) -> FilePromptService:
    """获取文件Prompt服务"""
    return FilePromptService(session)


# ==================== 目录结构API ====================

@router.get("/coding/{project_id}/directories/tree")
async def get_directory_tree(
    project_id: str,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DirectoryTreeResponse:
    """
    获取项目的完整目录树

    返回项目的所有目录和文件，按树形结构组织。
    """
    return await directory_service.get_directory_tree(project_id, desktop_user.id)


@router.post("/coding/{project_id}/directories/generate")
async def generate_directory_structure(
    project_id: str,
    request: GenerateDirectoryStructureRequest,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GenerateDirectoryStructureResponse:
    """
    为指定模块生成目录结构

    根据模块信息和功能列表，使用LLM生成合理的目录结构和源文件列表。
    """
    logger.info(
        "收到目录结构生成请求: project_id=%s module_number=%d",
        project_id, request.module_number
    )

    # 获取模块名称
    from ....repositories.coding_repository import CodingModuleRepository
    module_repo = CodingModuleRepository(session)
    module = await module_repo.get_by_project_and_number(project_id, request.module_number)
    if not module:
        raise ResourceNotFoundError("模块", str(request.module_number))

    dirs_created, files_created, root_path = await directory_service.generate_for_module(
        project_id=project_id,
        user_id=desktop_user.id,
        module_number=request.module_number,
        preference=request.preference,
        clear_existing=request.clear_existing,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    await session.commit()

    logger.info(
        "目录结构生成完成: project_id=%s module=%d dirs=%d files=%d",
        project_id, request.module_number, dirs_created, files_created
    )

    return GenerateDirectoryStructureResponse(
        module_number=request.module_number,
        module_name=module.name,
        directories_created=dirs_created,
        files_created=files_created,
        root_path=root_path,
        ai_message=f"已为模块「{module.name}」生成{dirs_created}个目录和{files_created}个源文件",
    )


# ==================== Agent状态管理API ====================
# 注意：这些路由必须在 /directories/{node_id} 之前定义，否则会被误匹配

DIRECTORY_AGENT_TYPE = "directory_planning_v2"


class AgentStateResponse(BaseModel):
    """Agent状态响应"""
    has_paused_state: bool = Field(description="是否有暂停的状态")
    current_phase: Optional[str] = Field(None, description="当前阶段")
    total_directories: int = Field(0, description="已生成的目录数")
    total_files: int = Field(0, description="已生成的文件数")
    progress_percent: int = Field(0, description="进度百分比")
    progress_message: Optional[str] = Field(None, description="进度消息")
    paused_at: Optional[str] = Field(None, description="暂停时间")


class PauseAgentRequest(BaseModel):
    """暂停Agent请求"""
    reason: str = Field("用户手动停止", description="暂停原因")


@router.get("/coding/{project_id}/directories/agent-state")
async def get_directory_agent_state(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> AgentStateResponse:
    """
    获取目录规划Agent的状态

    用于检查是否有可恢复的暂停状态。
    """
    state_repo = CodingAgentStateRepository(session)
    state = await state_repo.get_paused(project_id, DIRECTORY_AGENT_TYPE)

    if not state:
        return AgentStateResponse(has_paused_state=False)

    state_data = state.state_data or {}
    return AgentStateResponse(
        has_paused_state=True,
        current_phase=state.current_phase,
        total_directories=state_data.get("total_directories", 0),
        total_files=state_data.get("total_files", 0),
        progress_percent=state.progress_percent,
        progress_message=state.progress_message,
        paused_at=state.updated_at.isoformat() if state.updated_at else None,
    )


@router.post("/coding/{project_id}/directories/pause-agent")
async def pause_directory_agent(
    project_id: str,
    request: PauseAgentRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    暂停目录规划Agent

    保存当前状态以便后续恢复。
    """
    state_repo = CodingAgentStateRepository(session)

    # 获取当前运行中的状态
    state = await state_repo.get_by_project_and_type(project_id, DIRECTORY_AGENT_TYPE)
    if not state:
        return {
            "success": False,
            "message": "没有运行中的Agent",
        }

    # 更新为暂停状态
    state.status = "paused"
    state.progress_message = request.reason
    await session.commit()

    state_data = state.state_data or {}
    return {
        "success": True,
        "total_directories": state_data.get("total_directories", 0),
        "total_files": state_data.get("total_files", 0),
        "current_phase": state.current_phase,
    }


@router.delete("/coding/{project_id}/directories/agent-state")
async def clear_directory_agent_state(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    清除目录规划Agent的状态

    用于放弃暂停的状态，重新开始。
    """
    state_repo = CodingAgentStateRepository(session)
    deleted = await state_repo.delete_state(project_id, DIRECTORY_AGENT_TYPE)
    await session.commit()

    return {
        "success": True,
        "deleted": deleted > 0,
    }


# ==================== 目录CRUD API ====================

@router.post("/coding/{project_id}/directories")
async def create_directory(
    project_id: str,
    request: DirectoryNodeCreate,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DirectoryNodeResponse:
    """
    手动创建目录

    在指定父目录下创建新目录，parent_id为空则创建根目录。
    """
    node = await directory_service.create_directory(
        project_id=project_id,
        user_id=desktop_user.id,
        name=request.name,
        parent_id=request.parent_id,
        node_type=request.node_type.value,
        description=request.description,
    )
    await session.commit()

    return DirectoryNodeResponse(
        id=node.id,
        project_id=node.project_id,
        parent_id=node.parent_id,
        name=node.name,
        path=node.path,
        node_type=node.node_type,
        description=node.description,
        sort_order=node.sort_order,
        module_number=node.module_number,
        generation_status=node.generation_status,
        is_manual=node.is_manual,
        file_count=0,
        children=[],
    )


@router.patch("/coding/{project_id}/directories/{node_id}")
async def update_directory(
    project_id: str,
    node_id: int,
    request: DirectoryNodeUpdate,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> DirectoryNodeResponse:
    """
    更新目录

    修改目录名称、描述或排序顺序。
    """
    node = await directory_service.update_directory(
        project_id=project_id,
        user_id=desktop_user.id,
        node_id=node_id,
        name=request.name,
        description=request.description,
        sort_order=request.sort_order,
    )
    await session.commit()

    return DirectoryNodeResponse(
        id=node.id,
        project_id=node.project_id,
        parent_id=node.parent_id,
        name=node.name,
        path=node.path,
        node_type=node.node_type,
        description=node.description,
        sort_order=node.sort_order,
        module_number=node.module_number,
        generation_status=node.generation_status,
        is_manual=node.is_manual,
        file_count=0,
        children=[],
    )


@router.delete("/coding/{project_id}/directories/{node_id}")
async def delete_directory(
    project_id: str,
    node_id: int,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    删除目录

    级联删除所有子目录和文件。
    """
    await directory_service.delete_directory(
        project_id=project_id,
        user_id=desktop_user.id,
        node_id=node_id,
    )
    await session.commit()

    return {"success": True, "message": "目录已删除"}


class RepairDirectoriesResponse(BaseModel):
    """修复目录关系响应"""
    success: bool
    total_directories: int = Field(description="总目录数")
    fixed_directories: int = Field(description="修复的目录数")
    created_parents: int = Field(description="创建的缺失父目录数")
    message: str


@router.post("/coding/{project_id}/directories/repair")
async def repair_directory_relationships(
    project_id: str,
    directory_service: DirectoryStructureService = Depends(get_directory_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> RepairDirectoriesResponse:
    """
    修复目录的parent_id关系

    遍历项目所有目录，根据路径重建正确的父子关系。
    用于修复之前由于bug导致的parent_id全为NULL的问题。
    """
    logger.info("收到目录关系修复请求: project_id=%s", project_id)

    stats = await directory_service.repair_parent_relationships(
        project_id=project_id,
        user_id=desktop_user.id,
    )
    await session.commit()

    message = f"修复完成：检查了{stats['total_directories']}个目录，修复了{stats['fixed_directories']}个关系"
    if stats['created_parents'] > 0:
        message += f"，创建了{stats['created_parents']}个缺失的父目录"

    logger.info(
        "目录关系修复完成: project_id=%s total=%d fixed=%d created=%d",
        project_id,
        stats['total_directories'],
        stats['fixed_directories'],
        stats['created_parents'],
    )

    return RepairDirectoriesResponse(
        success=True,
        total_directories=stats['total_directories'],
        fixed_directories=stats['fixed_directories'],
        created_parents=stats['created_parents'],
        message=message,
    )


# ==================== 源文件API ====================

@router.get("/coding/{project_id}/files")
async def list_files(
    project_id: str,
    module_number: Optional[int] = None,
    directory_id: Optional[int] = None,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileListResponse:
    """
    获取源文件列表

    可按模块或目录筛选。
    """
    files = await file_service.list_files(
        project_id=project_id,
        user_id=desktop_user.id,
        module_number=module_number,
        directory_id=directory_id,
    )

    return SourceFileListResponse(files=files, total=len(files))


@router.get("/coding/{project_id}/files/{file_id}")
async def get_file(
    project_id: str,
    file_id: int,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileDetail:
    """
    获取源文件详情

    包含文件信息和当前选中版本的内容。
    """
    return await file_service.get_file(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
    )


@router.post("/coding/{project_id}/files")
async def create_file(
    project_id: str,
    request: SourceFileCreate,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileResponse:
    """
    手动创建源文件
    """
    file = await file_service.create_file(
        project_id=project_id,
        user_id=desktop_user.id,
        directory_id=request.directory_id,
        filename=request.filename,
        file_type=request.file_type.value,
        language=request.language,
        description=request.description,
        purpose=request.purpose,
        priority=request.priority.value,
    )
    await session.commit()

    return SourceFileResponse(
        id=file.id,
        project_id=file.project_id,
        directory_id=file.directory_id,
        filename=file.filename,
        file_path=file.file_path,
        file_type=file.file_type,
        language=file.language,
        description=file.description,
        purpose=file.purpose,
        imports=[],
        exports=[],
        dependencies=[],
        module_number=file.module_number,
        system_number=file.system_number,
        priority=file.priority,
        sort_order=file.sort_order,
        status=file.status,
        is_manual=file.is_manual,
        has_content=False,
        selected_version_id=None,
        version_count=0,
    )


@router.patch("/coding/{project_id}/files/{file_id}")
async def update_file(
    project_id: str,
    file_id: int,
    request: SourceFileUpdate,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> SourceFileResponse:
    """
    更新源文件信息
    """
    file = await file_service.update_file(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        filename=request.filename,
        description=request.description,
        purpose=request.purpose,
        priority=request.priority.value if request.priority else None,
        sort_order=request.sort_order,
    )
    await session.commit()

    # 重新获取完整信息
    return await file_service._serialize_file(file)


@router.delete("/coding/{project_id}/files/{file_id}")
async def delete_file(
    project_id: str,
    file_id: int,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    删除源文件
    """
    await file_service.delete_file(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
    )
    await session.commit()

    return {"success": True, "message": "文件已删除"}


# ==================== 文件Prompt生成API ====================

@router.post("/coding/{project_id}/files/{file_id}/generate")
async def generate_file_prompt(
    project_id: str,
    file_id: int,
    request: Optional[GenerateFilePromptRequest] = None,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    vector_store=Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    生成文件Prompt（同步模式）

    使用RAG检索相关上下文，生成更精准的实现Prompt。
    """
    logger.info(
        "收到文件Prompt生成请求: project_id=%s file_id=%d",
        project_id, file_id
    )

    version = await file_service.generate_prompt(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        writing_notes=request.writing_notes if request else None,
        llm_service=llm_service,
        prompt_service=prompt_service,
        vector_store=vector_store,
    )
    await session.commit()

    return {
        "success": True,
        "file_id": file_id,
        "version_id": version.id,
        "content": version.content,
    }


@router.post("/coding/{project_id}/files/{file_id}/generate-stream")
async def generate_file_prompt_stream(
    project_id: str,
    file_id: int,
    request: Optional[GenerateFilePromptRequest] = None,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    vector_store=Depends(get_vector_store),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    生成文件Prompt（SSE流式模式）

    使用RAG检索相关上下文，流式生成实现Prompt。

    事件类型：
    - progress: 进度信息 {"stage": "...", "message": "..."}
    - token: 流式内容 {"token": "..."}
    - complete: 完成 {"file_id": N, "version_id": N, "content": "...", "version_count": N}
    - error: 错误 {"message": "..."}
    """
    logger.info(
        "收到文件Prompt生成请求（SSE模式）: project_id=%s file_id=%d",
        project_id, file_id
    )

    async def event_generator():
        async for event in file_service.generate_prompt_stream(
            project_id=project_id,
            user_id=desktop_user.id,
            file_id=file_id,
            writing_notes=request.writing_notes if request else None,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
        ):
            yield sse_event(event["event"], event["data"])

    return create_sse_response(event_generator())


@router.post("/coding/{project_id}/files/{file_id}/save")
async def save_file_content(
    project_id: str,
    file_id: int,
    request: SaveFilePromptRequest,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    保存文件Prompt内容

    创建新版本并选中。
    """
    version = await file_service.save_content(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        content=request.content,
        version_label=request.version_label,
    )
    await session.commit()

    return {
        "success": True,
        "version_id": version.id,
        "word_count": len(request.content),
    }


# ==================== 审查Prompt生成API ====================

@router.post("/coding/{project_id}/files/{file_id}/generate-review")
async def generate_review_prompt(
    project_id: str,
    file_id: int,
    request: Optional[GenerateReviewPromptRequest] = None,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    vector_store=Depends(get_vector_store),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    生成文件审查Prompt（同步模式）

    基于文件的实现Prompt，生成代码审查和测试指南。
    """
    logger.info(
        "收到文件审查Prompt生成请求: project_id=%s file_id=%d",
        project_id, file_id
    )

    content = await file_service.generate_review_prompt(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        writing_notes=request.writing_notes if request else None,
        llm_service=llm_service,
        prompt_service=prompt_service,
        vector_store=vector_store,
    )
    await session.commit()

    return {
        "success": True,
        "file_id": file_id,
        "content": content,
    }


@router.post("/coding/{project_id}/files/{file_id}/generate-review-stream")
async def generate_review_prompt_stream(
    project_id: str,
    file_id: int,
    request: Optional[GenerateReviewPromptRequest] = None,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    vector_store=Depends(get_vector_store),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    生成文件审查Prompt（SSE流式模式）

    事件类型：
    - progress: 进度信息 {"stage": "...", "message": "..."}
    - token: 流式内容 {"token": "..."}
    - complete: 完成 {"file_id": N, "content": "..."}
    - error: 错误 {"message": "..."}
    """
    logger.info(
        "收到文件审查Prompt生成请求（SSE模式）: project_id=%s file_id=%d",
        project_id, file_id
    )

    async def event_generator():
        async for event in file_service.generate_review_prompt_stream(
            project_id=project_id,
            user_id=desktop_user.id,
            file_id=file_id,
            writing_notes=request.writing_notes if request else None,
            llm_service=llm_service,
            prompt_service=prompt_service,
            vector_store=vector_store,
        ):
            yield sse_event(event["event"], event["data"])

    return create_sse_response(event_generator())


@router.post("/coding/{project_id}/files/{file_id}/save-review")
async def save_review_prompt(
    project_id: str,
    file_id: int,
    request: SaveReviewPromptRequest,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    保存文件审查Prompt内容
    """
    content = await file_service.save_review_prompt(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        content=request.content,
    )
    await session.commit()

    return {
        "success": True,
        "file_id": file_id,
        "word_count": len(content),
    }


# ==================== 版本管理API ====================

@router.get("/coding/{project_id}/files/{file_id}/versions")
async def get_file_versions(
    project_id: str,
    file_id: int,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> FileVersionListResponse:
    """
    获取文件的所有版本
    """
    versions = await file_service.get_versions(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
    )

    # 获取当前选中的版本ID
    file = await file_service.file_repo.get_by_id(file_id)
    selected_version_id = file.selected_version_id if file else None

    return FileVersionListResponse(
        versions=versions,
        selected_version_id=selected_version_id,
    )


@router.post("/coding/{project_id}/files/{file_id}/select-version")
async def select_file_version(
    project_id: str,
    file_id: int,
    request: SelectFileVersionRequest,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    选择文件版本
    """
    file = await file_service.select_version(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        version_id=request.version_id,
    )
    await session.commit()

    return {
        "success": True,
        "selected_version_id": file.selected_version_id,
    }


# ==================== 目录生成API（三阶段架构） ====================

class PlanDirectoryV2Request(BaseModel):
    """目录规划请求（三阶段架构）"""
    preference: Optional[str] = Field(None, description="规划偏好说明")
    architecture_pattern: Optional[str] = Field(
        None,
        description="架构模式：layered(分层架构), feature_based(功能模块架构), simple(简单架构)"
    )
    run_refinement: bool = Field(True, description="是否运行质量评估和精化阶段")
    clear_existing: bool = Field(False, description="是否清除现有目录结构")


@router.post("/coding/{project_id}/directories/plan-v2")
async def plan_directory_structure_v2(
    project_id: str,
    request: Optional[PlanDirectoryV2Request] = None,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    三阶段目录结构规划（SSE流式模式）

    阶段一（项目画像）：
    - 收集项目信息，构建项目画像
    - 分析技术栈、模块依赖、项目复杂度
    - 推荐适合的架构模式

    阶段二（架构决策）：
    - 选择架构模式（可由用户指定或系统推荐）
    - 生成层级定义和模块放置计划
    - 确定命名约定和共享模块策略

    阶段三（生成与精化）：
    - 按架构决策生成目录结构
    - 质量评估：覆盖率、内聚性、耦合度、可理解性
    - 精化Agent：自动修复不达标的问题

    事件类型：
    - progress: 进度更新
    - profile_built: 项目画像构建完成
    - decision_made: 架构决策完成
    - quality_evaluated: 质量评估完成
    - structure: 生成的结构数据
    - complete: 规划完成
    - error: 发生错误
    """
    logger.info(
        "收到目录规划请求: project_id=%s, pattern=%s",
        project_id,
        request.architecture_pattern if request else "auto",
    )

    # 获取项目信息
    from ....services.coding import CodingProjectService
    from ....repositories.coding_repository import (
        CodingModuleRepository,
        CodingSystemRepository,
    )
    from ....serializers.coding_serializer import CodingSerializer

    project_service = CodingProjectService(session)
    project = await project_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取蓝图信息
    blueprint_schema = CodingSerializer.build_blueprint_schema(project)

    # 获取系统信息
    system_repo = CodingSystemRepository(session)
    systems = await system_repo.get_by_project_ordered(project_id)

    # 获取模块信息
    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    if not modules:
        return create_sse_response(_error_generator("项目没有模块，无法生成目录结构"))

    # 构建模块数据
    module_dicts = [
        {
            "module_number": m.module_number,
            "system_number": m.system_number,
            "name": m.name,
            "module_type": m.module_type,
            "description": m.description,
            "interface": m.interface,
            "dependencies": m.dependencies or [],
        }
        for m in modules
    ]

    # 构建项目数据
    project_data = {
        "id": project.id,
        "title": project.title,
        "initial_prompt": project.initial_prompt,
        "status": project.status,
    }

    # 构建蓝图数据
    blueprint_data = {}
    if blueprint_schema:
        nfr = blueprint_schema.non_functional_requirements
        nfr_dict = nfr.model_dump() if hasattr(nfr, 'model_dump') else (nfr if isinstance(nfr, dict) else {}) if nfr else {}

        blueprint_data = {
            "title": blueprint_schema.title,
            "target_audience": blueprint_schema.target_audience,
            "project_type_desc": blueprint_schema.project_type_desc,
            "tech_style": blueprint_schema.tech_style,
            "project_tone": blueprint_schema.project_tone,
            "one_sentence_summary": blueprint_schema.one_sentence_summary,
            "architecture_synopsis": blueprint_schema.architecture_synopsis,
            "tech_stack": blueprint_schema.tech_stack.model_dump() if blueprint_schema.tech_stack else {},
            "system_suggestions": [s.model_dump() if hasattr(s, 'model_dump') else s for s in (blueprint_schema.system_suggestions or [])],
            "core_requirements": [r.model_dump() if hasattr(r, 'model_dump') else r for r in (blueprint_schema.core_requirements or [])],
            "technical_challenges": [c.model_dump() if hasattr(c, 'model_dump') else c for c in (blueprint_schema.technical_challenges or [])],
            "non_functional_requirements": nfr_dict,
            "risks": [r.model_dump() if hasattr(r, 'model_dump') else r for r in (blueprint_schema.risks or [])],
            "milestones": [m.model_dump() if hasattr(m, 'model_dump') else m for m in (blueprint_schema.milestones or [])],
            "dependencies": [d.model_dump() if hasattr(d, 'model_dump') else d for d in (blueprint_schema.dependencies or [])],
        }

    # 构建系统数据
    system_dicts = [
        {
            "system_number": s.system_number,
            "name": s.name,
            "description": s.description,
            "responsibilities": s.responsibilities or [],
            "tech_requirements": s.tech_requirements,
            "module_count": s.module_count,
            "feature_count": s.feature_count,
        }
        for s in systems
    ]

    async def event_generator():
        async with AsyncSessionLocal() as inner_session:
            inner_state_repo = CodingAgentStateRepository(inner_session)
            inner_directory_service = DirectoryStructureService(inner_session)

            async for event in _three_phase_pipeline(
                project_id=project_id,
                user_id=desktop_user.id,
                project_data=project_data,
                blueprint_data=blueprint_data,
                systems=system_dicts,
                modules=module_dicts,
                architecture_pattern=request.architecture_pattern if request else None,
                run_refinement=request.run_refinement if request else True,
                clear_existing=request.clear_existing if request else False,
                inner_session=inner_session,
                inner_state_repo=inner_state_repo,
                inner_directory_service=inner_directory_service,
                llm_service=llm_service,
                prompt_service=prompt_service,
            ):
                yield event

    return create_sse_response(event_generator())


async def _error_generator(message: str):
    """错误事件生成器"""
    yield sse_event("error", {"message": message})


async def _three_phase_pipeline(
    project_id: str,
    user_id: int,
    project_data: dict,
    blueprint_data: dict,
    systems: list,
    modules: list,
    architecture_pattern: Optional[str],
    run_refinement: bool,
    clear_existing: bool,
    inner_session,
    inner_state_repo,
    inner_directory_service,
    llm_service=None,
    prompt_service=None,
):
    """
    三阶段目录结构生成流水线

    阶段一：ProjectProfiler - 项目画像构建
    阶段二：ArchitectureDecisionMaker - 架构决策
    阶段三：ArchitectureBasedGenerator + QualityEvaluator + RefinementAgent - 生成与精化

    Yields:
        SSE事件
    """
    try:
        # ============ 阶段一：项目画像构建 ============
        yield sse_event("progress", {
            "stage": "phase1",
            "phase": "profiling",
            "message": "正在分析项目特征...",
        })

        # 保存运行状态
        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="phase1_profiling",
            state_data={"started": True},
            progress_percent=10,
            progress_message="正在构建项目画像...",
            status="running",
        )
        await inner_session.commit()

        # 构建模块依赖
        module_dependencies = []
        for m in modules:
            deps = m.get("dependencies", [])
            if deps:
                for dep in deps:
                    module_dependencies.append({
                        "from_module": m.get("name", ""),
                        "to_module": dep,
                    })

        # 创建项目画像
        profiler = ProjectProfiler(
            project_id=project_id,
            project_data=project_data,
            blueprint_data=blueprint_data,
            systems=systems,
            modules=modules,
            module_dependencies=module_dependencies,
        )
        profile = profiler.build_profile()

        yield sse_event("profile_built", {
            "project_name": profile.project_name,
            "total_modules": profile.total_modules,
            "total_systems": profile.total_systems,
            "complexity_score": profile.complexity_score,
            "recommended_pattern": profile.recommended_pattern.value if profile.recommended_pattern else None,
            "recommendation_reason": profile.recommendation_reason,
        })

        yield sse_event("progress", {
            "stage": "phase1_complete",
            "message": f"项目画像构建完成: {profile.total_modules}个模块, 复杂度{profile.complexity_score:.2f}",
        })

        # ============ 阶段二：架构决策 ============
        yield sse_event("progress", {
            "stage": "phase2",
            "phase": "decision",
            "message": "正在制定架构决策...",
        })

        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="phase2_decision",
            state_data={"profile_built": True},
            progress_percent=30,
            progress_message="正在制定架构决策...",
            status="running",
        )
        await inner_session.commit()

        # 解析用户指定的架构模式
        user_pattern = None
        if architecture_pattern:
            try:
                user_pattern = ArchitecturePattern(architecture_pattern)
            except ValueError:
                logger.warning("无效的架构模式: %s, 将使用推荐模式", architecture_pattern)

        # 创建架构决策
        decision_maker = ArchitectureDecisionMaker(
            profile=profile,
            user_preference=user_pattern,
        )
        decision = decision_maker.make_decision()

        yield sse_event("decision_made", {
            "pattern": decision.pattern.value,
            "pattern_rationale": decision.pattern_rationale,
            "layers": [
                {"name": l.name, "path": l.path, "description": l.description}
                for l in decision.layers
            ],
            "module_placements_count": len(decision.module_placements),
            "naming_convention": decision.naming_convention,
        })

        yield sse_event("progress", {
            "stage": "phase2_complete",
            "message": f"架构决策完成: 选择{decision.pattern.value}模式",
        })

        # ============ 阶段三：目录结构生成 ============
        yield sse_event("progress", {
            "stage": "phase3",
            "phase": "generating",
            "message": f"正在按{decision.pattern.value}架构生成目录结构...",
        })

        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="phase3_generating",
            state_data={
                "profile": profile.to_dict(),
                "decision": decision.to_dict(),
            },
            progress_percent=50,
            progress_message="正在生成目录结构...",
            status="running",
        )
        await inner_session.commit()

        # 生成目录结构
        generator = ArchitectureBasedGenerator(
            profile=profile,
            decision=decision,
            llm_service=llm_service,
            prompt_service=prompt_service,
            user_id=user_id,
        )

        # 使用流式生成
        output = None
        async for event in generator.generate_stream():
            event_type = event.get("event", "")
            event_data = event.get("data", {})

            if event_type == "structure":
                # 构建BruteForceOutput
                from ....services.coding_files.directory_generator.schemas import (
                    DirectorySpec,
                    FileSpec,
                )
                output = BruteForceOutput(
                    root_path=decision.root_path,
                    directories=[
                        DirectorySpec(**d) for d in event_data.get("directories", [])
                    ],
                    files=[
                        FileSpec(**f) for f in event_data.get("files", [])
                    ],
                    shared_modules=event_data.get("shared_modules", []),
                    architecture_notes=event_data.get("architecture_notes", ""),
                )
            elif event_type == "complete":
                yield sse_event("progress", {
                    "stage": "phase3_generated",
                    "message": f"目录结构生成完成: {event_data.get('total_directories', 0)}个目录, {event_data.get('total_files', 0)}个文件",
                    "total_directories": event_data.get("total_directories", 0),
                    "total_files": event_data.get("total_files", 0),
                })
            else:
                # 转发其他事件
                yield sse_event(event_type, event_data)

        if output is None:
            # 如果流式生成没有产出，使用同步生成
            output = generator.generate()

        # ============ 阶段三b：质量评估与精化 ============
        if run_refinement:
            yield sse_event("progress", {
                "stage": "phase3b",
                "phase": "evaluating",
                "message": "正在评估目录结构质量...",
            })

            await inner_state_repo.save_state(
                project_id=project_id,
                agent_type=DIRECTORY_AGENT_TYPE,
                current_phase="phase3b_evaluating",
                state_data={
                    "output": output.model_dump(),
                },
                progress_percent=70,
                progress_message="正在评估和精化...",
                status="running",
            )
            await inner_session.commit()

            # 质量评估
            evaluator = QualityEvaluator(
                profile=profile,
                decision=decision,
                output=output,
            )
            initial_metrics = evaluator.evaluate()

            yield sse_event("quality_evaluated", {
                "overall_score": initial_metrics.overall_score,
                "grade": initial_metrics.get_grade(),
                "module_coverage": initial_metrics.module_coverage,
                "file_completeness": initial_metrics.file_completeness,
                "pattern_adherence": initial_metrics.pattern_adherence,
                "issues_count": len(initial_metrics.issues),
            })

            # 如果质量不达标，运行精化Agent
            if initial_metrics.overall_score < 0.8:
                yield sse_event("progress", {
                    "stage": "phase3b",
                    "phase": "refining",
                    "message": f"质量评分{initial_metrics.overall_score:.2f}，开始精化...",
                })

                refiner = RefinementAgent(
                    profile=profile,
                    decision=decision,
                    output=output,
                )

                async for event in refiner.refine_stream():
                    event_type = event.get("event", "")
                    event_data = event.get("data", {})
                    yield sse_event(event_type, event_data)

                # 获取精化后的输出
                output = refiner.output
                summary = refiner.get_refinement_summary()

                yield sse_event("progress", {
                    "stage": "phase3b_complete",
                    "message": f"精化完成: {summary['rounds']}轮, 评分提升{summary['improvement']:.2f}",
                    "refinement_rounds": summary["rounds"],
                    "initial_score": summary["initial_score"],
                    "final_score": summary["final_score"],
                })
            else:
                yield sse_event("progress", {
                    "stage": "phase3b_complete",
                    "message": f"质量评分{initial_metrics.overall_score:.2f}达标，无需精化",
                })

        # ============ 保存到数据库 ============
        yield sse_event("progress", {
            "stage": "saving",
            "message": "正在保存目录结构到数据库...",
        })

        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="saving",
            state_data={
                "output": output.model_dump(),
            },
            progress_percent=90,
            progress_message="正在保存到数据库...",
            status="running",
        )
        await inner_session.commit()

        # 使用TreeBuilder构建目录树
        tree_builder = DirectoryTreeBuilder()
        root_dirs, all_files = tree_builder.build(output)

        # 如果需要清除现有结构
        if clear_existing:
            await inner_directory_service.clear_project_structure(project_id, user_id)
            await inner_session.flush()

        # 转换为LLM输出格式并保存
        from ....schemas.coding_files import LLMDirectoryStructureOutput, LLMDirectoryNode, LLMSourceFile

        def convert_planned_directory(planned_dir) -> LLMDirectoryNode:
            """转换PlannedDirectory为LLMDirectoryNode"""
            return LLMDirectoryNode(
                name=planned_dir.name,
                path=planned_dir.path,
                node_type=planned_dir.node_type,
                description=planned_dir.description,
                module_number=planned_dir.module_number,
                files=[
                    LLMSourceFile(
                        filename=f.filename,
                        file_type=f.file_type,
                        language=f.language,
                        description=f.description,
                        purpose=f.purpose,
                        priority=f.priority,
                        module_number=f.module_number,
                    )
                    for f in planned_dir.files
                ],
                children=[convert_planned_directory(c) for c in planned_dir.children],
            )

        llm_output = LLMDirectoryStructureOutput(
            root_path=output.root_path,
            directories=[convert_planned_directory(d) for d in root_dirs],
            summary=output.architecture_notes,
        )

        # 保存到数据库
        dirs_created, files_created = await inner_directory_service._save_structure(
            project_id=project_id,
            module_number=0,  # 项目级别
            structure=llm_output,
        )

        # 清除Agent状态（成功完成）
        await inner_state_repo.delete_state(project_id, DIRECTORY_AGENT_TYPE)
        await inner_session.commit()

        logger.info(
            "三阶段目录结构生成完成: project_id=%s, dirs=%d, files=%d",
            project_id, dirs_created, files_created
        )

        # 最终质量评估
        final_evaluator = QualityEvaluator(
            profile=profile,
            decision=decision,
            output=output,
        )
        final_metrics = final_evaluator.evaluate()

        # 发送完成事件
        yield sse_event("structure", {
            "directories": [d.model_dump() for d in output.directories],
            "files": [f.model_dump() for f in output.files],
            "shared_modules": output.shared_modules,
            "architecture_notes": output.architecture_notes,
        })

        yield sse_event("complete", {
            "success": True,
            "directories_created": dirs_created,
            "files_created": files_created,
            "total_modules": len(modules),
            "architecture_pattern": decision.pattern.value,
            "quality_score": final_metrics.overall_score,
            "quality_grade": final_metrics.get_grade(),
            "message": f"目录结构生成完成: {dirs_created}个目录, {files_created}个文件, 质量等级{final_metrics.get_grade()}",
        })

    except Exception as e:
        logger.error("三阶段目录生成失败: %s", e, exc_info=True)
        # 保存错误状态（可以恢复）
        try:
            await inner_state_repo.save_state(
                project_id=project_id,
                agent_type=DIRECTORY_AGENT_TYPE,
                current_phase="error",
                state_data={"error": str(e)},
                progress_percent=0,
                progress_message=f"发生错误: {str(e)[:100]}",
                status="paused",
            )
            await inner_session.commit()
        except Exception:
            pass

        yield sse_event("error", {"message": str(e)})


# ==================== 目录规划Agent API ====================

class PlanDirectoryAgentRequest(BaseModel):
    """目录规划Agent请求"""
    clear_existing: bool = Field(False, description="是否清除现有目录结构")


@router.post("/coding/{project_id}/directories/plan-agent")
async def plan_directory_with_agent(
    project_id: str,
    request: Optional[PlanDirectoryAgentRequest] = None,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    使用ReAct Agent进行目录规划（SSE流式模式）

    Agent会通过思考-行动-观察循环，智能地规划目录结构：
    1. 获取项目信息，了解整体情况
    2. 分析模块依赖，确定架构方案
    3. 逐步创建目录和文件，详细说明每个文件的功能和依赖
    4. 验证完整性，确保所有模块都被覆盖

    事件类型：
    - agent_start: Agent启动
    - iteration_start: 迭代开始
    - thinking: Agent思考过程
    - action: Agent选择的工具和参数
    - observation: 工具执行结果
    - progress: 进度更新
    - planning_complete: 规划完成
    - final_state: 最终的目录结构
    - error: 发生错误
    - warning: 警告信息
    """
    logger.info("收到Agent目录规划请求: project_id=%s", project_id)

    # 获取项目信息
    from ....services.coding import CodingProjectService
    from ....repositories.coding_repository import (
        CodingModuleRepository,
        CodingSystemRepository,
    )
    from ....serializers.coding_serializer import CodingSerializer
    from ....services.coding_files.directory_agent import run_directory_planning_agent

    project_service = CodingProjectService(session)
    project = await project_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取蓝图信息
    blueprint_schema = CodingSerializer.build_blueprint_schema(project)

    # 获取系统信息
    system_repo = CodingSystemRepository(session)
    systems = await system_repo.get_by_project_ordered(project_id)

    # 获取模块信息
    module_repo = CodingModuleRepository(session)
    modules = await module_repo.get_by_project_ordered(project_id)

    if not modules:
        return create_sse_response(_error_generator("项目没有模块，无法生成目录结构"))

    # 构建模块数据
    module_dicts = [
        {
            "module_number": m.module_number,
            "system_number": m.system_number,
            "name": m.name,
            "module_type": m.module_type,
            "description": m.description,
            "interface": m.interface,
            "dependencies": m.dependencies or [],
        }
        for m in modules
    ]

    # 构建项目数据
    project_data = {
        "id": project.id,
        "title": project.title,
        "initial_prompt": project.initial_prompt,
        "status": project.status,
    }

    # 构建蓝图数据
    blueprint_data = {}
    if blueprint_schema:
        nfr = blueprint_schema.non_functional_requirements
        nfr_dict = nfr.model_dump() if hasattr(nfr, 'model_dump') else (nfr if isinstance(nfr, dict) else {}) if nfr else {}

        blueprint_data = {
            "title": blueprint_schema.title,
            "target_audience": blueprint_schema.target_audience,
            "project_type_desc": blueprint_schema.project_type_desc,
            "tech_style": blueprint_schema.tech_style,
            "project_tone": blueprint_schema.project_tone,
            "one_sentence_summary": blueprint_schema.one_sentence_summary,
            "architecture_synopsis": blueprint_schema.architecture_synopsis,
            "tech_stack": blueprint_schema.tech_stack.model_dump() if blueprint_schema.tech_stack else {},
            "system_suggestions": [s.model_dump() if hasattr(s, 'model_dump') else s for s in (blueprint_schema.system_suggestions or [])],
            "core_requirements": [r.model_dump() if hasattr(r, 'model_dump') else r for r in (blueprint_schema.core_requirements or [])],
            "technical_challenges": [c.model_dump() if hasattr(c, 'model_dump') else c for c in (blueprint_schema.technical_challenges or [])],
            "non_functional_requirements": nfr_dict,
            "risks": [r.model_dump() if hasattr(r, 'model_dump') else r for r in (blueprint_schema.risks or [])],
            "milestones": [m.model_dump() if hasattr(m, 'model_dump') else m for m in (blueprint_schema.milestones or [])],
            "dependencies": [d.model_dump() if hasattr(d, 'model_dump') else d for d in (blueprint_schema.dependencies or [])],
        }

    # 构建系统数据
    system_dicts = [
        {
            "system_number": s.system_number,
            "name": s.name,
            "description": s.description,
            "responsibilities": s.responsibilities or [],
            "tech_requirements": s.tech_requirements,
            "module_count": s.module_count,
            "feature_count": s.feature_count,
        }
        for s in systems
    ]

    async def event_generator():
        # 运行Agent
        final_state = None

        async for event in run_directory_planning_agent(
            project_id=project_id,
            project_data=project_data,
            blueprint_data=blueprint_data,
            systems=system_dicts,
            modules=module_dicts,
            llm_service=llm_service,
            prompt_service=prompt_service,
            user_id=desktop_user.id,
        ):
            event_type = event.get("event", "")
            event_data = event.get("data", {})

            # 调试日志：记录所有转发的事件
            if event_type == "structure_update":
                logger.info("[SSE转发] structure_update事件: dirs=%d, files=%d",
                           len(event_data.get("directories", [])),
                           len(event_data.get("files", [])))

            # 保存最终状态
            if event_type == "final_state":
                final_state = event_data

            # 转发事件
            yield sse_event(event_type, event_data)

        # 如果有最终状态，保存到数据库
        if final_state and (not request or request.clear_existing):
            try:
                async with AsyncSessionLocal() as save_session:
                    directory_service = DirectoryStructureService(save_session)

                    # 清除现有结构
                    if request and request.clear_existing:
                        await directory_service.clear_project_structure(project_id, desktop_user.id)
                        await save_session.flush()

                    # 保存Agent生成的结构
                    dirs_created, files_created = await _save_agent_result(
                        directory_service,
                        project_id,
                        final_state,
                    )
                    await save_session.commit()

                    yield sse_event("saved", {
                        "directories_created": dirs_created,
                        "files_created": files_created,
                    })

            except Exception as e:
                logger.error("保存Agent结果失败: %s", e, exc_info=True)
                yield sse_event("error", {"message": f"保存结果失败: {e}"})

    return create_sse_response(event_generator())


async def _save_agent_result(
    directory_service: DirectoryStructureService,
    project_id: str,
    final_state: Dict[str, Any],
) -> Tuple[int, int]:
    """
    保存Agent生成的结果到数据库

    Args:
        directory_service: 目录服务
        project_id: 项目ID
        final_state: Agent的最终状态

    Returns:
        (创建的目录数, 创建的文件数)
    """
    from ....schemas.coding_files import LLMDirectoryStructureOutput, LLMDirectoryNode, LLMSourceFile

    directories = final_state.get("directories", [])
    files = final_state.get("files", [])

    # 按路径组织文件
    files_by_dir = {}
    for f in files:
        dir_path = "/".join(f["path"].split("/")[:-1])
        if dir_path not in files_by_dir:
            files_by_dir[dir_path] = []
        files_by_dir[dir_path].append(f)

    # 构建目录树
    def build_directory_node(dir_info: Dict) -> LLMDirectoryNode:
        path = dir_info["path"]
        dir_files = files_by_dir.get(path, [])

        return LLMDirectoryNode(
            name=path.split("/")[-1],
            path=path,
            node_type="directory",
            description=dir_info.get("description", ""),
            module_number=0,
            files=[
                LLMSourceFile(
                    filename=f["filename"],
                    file_type=f.get("file_type", "source"),
                    language=f.get("language", "python"),
                    description=f.get("description", ""),
                    purpose=f.get("purpose", ""),
                    priority=f.get("priority", "medium"),
                    module_number=f.get("module_number", 0),
                )
                for f in dir_files
            ],
            children=[],
        )

    # 找出顶层目录
    root_dirs = []
    for d in directories:
        path = d["path"]
        # 检查是否是顶层目录（路径中只有一级或两级）
        depth = path.count("/")
        if depth <= 1:
            root_dirs.append(build_directory_node(d))

    llm_output = LLMDirectoryStructureOutput(
        root_path="src",
        directories=root_dirs,
        summary="由Agent自动规划生成",
    )

    # 保存到数据库
    dirs_created, files_created = await directory_service._save_structure(
        project_id=project_id,
        module_number=0,
        structure=llm_output,
    )

    return dirs_created, files_created

