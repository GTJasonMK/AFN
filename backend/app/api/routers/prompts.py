"""
提示词管理API路由

提供提示词的查询、更新和恢复默认值功能。
"""

import logging
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core.dependencies import get_prompt_service
from ...exceptions import ResourceNotFoundError
from ...schemas.prompt import PromptRead, PromptUpdate
from ...services.prompt_service import PromptService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["Prompts"])


class ResetAllResponse(BaseModel):
    """恢复全部提示词的响应"""
    reset_count: int = Field(..., description="恢复的提示词数量")
    message: str = Field(..., description="操作结果消息")


# ========== 提示词管理API ==========


@router.get("", response_model=List[PromptRead])
async def list_prompts(
    service: PromptService = Depends(get_prompt_service),
) -> List[PromptRead]:
    """
    获取所有提示词列表。

    返回包含 title、description、is_modified 等元数据的完整提示词列表。
    """
    logger.info("查询提示词列表")
    return await service.list_prompts()


@router.get("/{name}", response_model=PromptRead)
async def get_prompt(
    name: str,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    """
    获取指定名称的提示词详情。

    Args:
        name: 提示词名称（如 inspiration, writing 等）
    """
    logger.info(f"查询提示词: {name}")
    result = await service.get_prompt_by_name(name)
    if not result:
        raise ResourceNotFoundError("提示词", name)
    return result


@router.put("/{name}", response_model=PromptRead)
async def update_prompt(
    name: str,
    payload: PromptUpdate,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    """
    更新提示词内容。

    用户编辑提示词后，内容会被保存并标记为已修改（is_modified=True）。
    已修改的提示词在系统更新时不会被覆盖。

    Args:
        name: 提示词名称
        payload: 包含新内容的请求体
    """
    logger.info(f"更新提示词: {name}")
    result = await service.update_prompt_content(name, payload.content)
    if not result:
        raise ResourceNotFoundError("提示词", name)
    return result


@router.post("/{name}/reset", response_model=PromptRead)
async def reset_prompt(
    name: str,
    service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    """
    恢复单个提示词到默认值。

    从原始提示词文件读取内容，覆盖当前数据库中的内容，
    并将 is_modified 标记设为 False。

    Args:
        name: 提示词名称
    """
    logger.info(f"恢复提示词默认值: {name}")
    result = await service.reset_prompt(name)
    if not result:
        raise ResourceNotFoundError("提示词", name)
    return result


@router.post("/reset-all", response_model=ResetAllResponse)
async def reset_all_prompts(
    service: PromptService = Depends(get_prompt_service),
) -> ResetAllResponse:
    """
    恢复所有提示词到默认值。

    遍历所有提示词文件，将数据库中的内容恢复为默认值，
    并将所有 is_modified 标记设为 False。
    """
    logger.info("恢复所有提示词默认值")
    reset_count = await service.reset_all_prompts()
    return ResetAllResponse(
        reset_count=reset_count,
        message=f"已恢复 {reset_count} 个提示词到默认值",
    )
