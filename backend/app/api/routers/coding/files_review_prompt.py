"""
Coding 文件相关路由：审查 Prompt 生成 API

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
from ....schemas.coding_files import GenerateReviewPromptRequest, SaveReviewPromptRequest
from ....schemas.user import UserInDB
from ....services.coding_files import FilePromptService
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.sse_helpers import create_sse_stream_response
from .files_dependencies import get_file_prompt_service

logger = logging.getLogger(__name__)
router = APIRouter()


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
        project_id,
        file_id,
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
        project_id,
        file_id,
    )

    event_generator = file_service.generate_review_prompt_stream(
        project_id=project_id,
        user_id=desktop_user.id,
        file_id=file_id,
        writing_notes=request.writing_notes if request else None,
        llm_service=llm_service,
        prompt_service=prompt_service,
        vector_store=vector_store,
    )
    return create_sse_stream_response(event_generator)


@router.post("/coding/{project_id}/files/{file_id}/save-review")
async def save_review_prompt(
    project_id: str,
    file_id: int,
    request: SaveReviewPromptRequest,
    file_service: FilePromptService = Depends(get_file_prompt_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """保存文件审查Prompt内容"""
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


__all__ = ["router"]

