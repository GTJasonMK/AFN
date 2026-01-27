"""
Coding 文件相关路由：文件 Prompt 生成 API

拆分自 `backend/app/api/routers/coding/files.py`。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....db.session import get_session
from ....schemas.coding_files import GenerateFilePromptRequest, SaveFilePromptRequest
from ....schemas.user import UserInDB
from ....services.coding_files import FilePromptService
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.sse_helpers import create_sse_stream_response
from .files_dependencies import get_file_prompt_service

logger = logging.getLogger(__name__)
router = APIRouter()


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
        project_id,
        file_id,
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
        project_id,
        file_id,
    )

    event_generator = file_service.generate_prompt_stream(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        writing_notes=request.writing_notes if request else None,
        llm_service=llm_service,
        prompt_service=prompt_service,
        vector_store=vector_store,
    )
    return create_sse_stream_response(event_generator)


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


__all__ = ["router"]

