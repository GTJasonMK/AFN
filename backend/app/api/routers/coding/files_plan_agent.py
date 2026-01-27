"""
Coding 文件相关路由：目录规划 Agent API（ReAct）

拆分自 `backend/app/api/routers/coding/files.py`。
"""

import logging
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user, get_llm_service, get_prompt_service
from ....db.session import AsyncSessionLocal, get_session
from ....schemas.user import UserInDB
from ....services.coding_files import DirectoryStructureService
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.sse_helpers import create_sse_response, sse_event
from .files_planning_context import load_directory_planning_context
from .files_plan_v2 import _error_generator

logger = logging.getLogger(__name__)
router = APIRouter()


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

    context = await load_directory_planning_context(session, project_id, desktop_user.id)
    if not context.modules:
        return create_sse_response(_error_generator("项目没有模块，无法生成目录结构"))

    from ....services.coding_files.directory_agent import run_directory_planning_agent

    async def event_generator():
        # 运行Agent
        final_state = None

        async for event in run_directory_planning_agent(
            project_id=project_id,
            project_data=context.project_data,
            blueprint_data=context.blueprint_data,
            systems=context.systems,
            modules=context.modules,
            llm_service=llm_service,
            prompt_service=prompt_service,
            user_id=desktop_user.id,
        ):
            event_type = event.get("event", "")
            event_data = event.get("data", {})

            # 调试日志：记录所有转发的事件
            if event_type == "structure_update":
                logger.info(
                    "[SSE转发] structure_update事件: dirs=%d, files=%d",
                    len(event_data.get("directories", [])),
                    len(event_data.get("files", [])),
                )

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

                    yield sse_event(
                        "saved",
                        {
                            "directories_created": dirs_created,
                            "files_created": files_created,
                        },
                    )

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
    from ....schemas.coding_files import LLMDirectoryNode, LLMDirectoryStructureOutput, LLMSourceFile

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


__all__ = ["router"]

