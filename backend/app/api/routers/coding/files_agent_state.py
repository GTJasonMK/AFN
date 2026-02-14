"""
Coding 文件相关路由：目录规划 Agent 状态管理 API

拆分自 `backend/app/api/routers/coding/files.py`。
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_coding_project_service, get_default_user
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....repositories.coding_files_repository import CodingAgentStateRepository
from ....services.coding import CodingProjectService
from .files_dependencies import DIRECTORY_AGENT_TYPE

router = APIRouter()


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
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> AgentStateResponse:
    """
    获取目录规划Agent的状态

    用于检查是否有可恢复的暂停状态。
    """
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

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
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    暂停目录规划Agent

    保存当前状态以便后续恢复。
    """
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

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
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    清除目录规划Agent的状态

    用于放弃暂停的状态，重新开始。
    """
    await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    state_repo = CodingAgentStateRepository(session)
    deleted = await state_repo.delete_state(project_id, DIRECTORY_AGENT_TYPE)
    await session.commit()

    return {
        "success": True,
        "deleted": deleted > 0,
    }


__all__ = ["router"]
