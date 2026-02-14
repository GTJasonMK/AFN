"""
提示词管理API路由

提供提示词的查询、更新、恢复默认值和注册表管理功能。
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ...core.dependencies import get_default_user, get_prompt_service, require_admin_user
from ...exceptions import ResourceNotFoundError
from ...schemas.prompt import PromptRead, PromptUpdate
from ...services.prompt_service import PromptService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["Prompts"], dependencies=[Depends(get_default_user)])


class ResetAllResponse(BaseModel):
    """恢复全部提示词的响应"""
    reset_count: int = Field(..., description="恢复的提示词数量")
    message: str = Field(..., description="操作结果消息")


class RegistrySummaryResponse(BaseModel):
    """注册表摘要响应"""
    available: bool = Field(..., description="注册表是否可用")
    total: Optional[int] = Field(None, description="提示词总数")
    by_category: Optional[Dict[str, int]] = Field(None, description="按分类统计")
    by_status: Optional[Dict[str, int]] = Field(None, description="按状态统计")
    categories: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="分类定义")


class ValidationResponse(BaseModel):
    """验证结果响应"""
    valid: bool = Field(..., description="是否验证通过")
    errors: List[str] = Field(default_factory=list, description="错误列表")


class PromptMetaResponse(BaseModel):
    """提示词元数据响应"""
    name: str = Field(..., description="提示词名称")
    path: Optional[str] = Field(None, description="文件路径")
    title: Optional[str] = Field(None, description="标题")
    category: Optional[str] = Field(None, description="分类")
    status: Optional[str] = Field(None, description="状态")
    description: Optional[str] = Field(None, description="描述")
    dependencies: List[str] = Field(default_factory=list, description="依赖列表")
    used_by: List[str] = Field(default_factory=list, description="使用此提示词的服务")


class DependencyGraphResponse(BaseModel):
    """依赖关系图响应"""
    graph: Dict[str, List[str]] = Field(..., description="依赖关系图")


# ========== 提示词管理API ==========


@router.get("", response_model=List[PromptRead])
async def list_prompts(
    service: PromptService = Depends(get_prompt_service),
) -> List[PromptRead]:
    """
    获取所有提示词列表。

    返回包含 title、description、is_modified 等元数据的完整提示词列表。
    """
    logger.debug("查询提示词列表")
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
    logger.debug(f"查询提示词: {name}")
    result = await service.get_prompt_by_name(name)
    if not result:
        raise ResourceNotFoundError("提示词", name)
    return result


@router.put("/{name}", response_model=PromptRead, dependencies=[Depends(require_admin_user)])
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


@router.post("/{name}/reset", response_model=PromptRead, dependencies=[Depends(require_admin_user)])
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


@router.post("/reset-all", response_model=ResetAllResponse, dependencies=[Depends(require_admin_user)])
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


# ========== 注册表管理API ==========


@router.get("/registry/summary", response_model=RegistrySummaryResponse)
async def get_registry_summary(
    service: PromptService = Depends(get_prompt_service),
) -> RegistrySummaryResponse:
    """
    获取注册表摘要信息。

    返回提示词的统计信息，包括按分类和状态的数量分布。
    """
    summary = service.get_registry_summary()
    return RegistrySummaryResponse(**summary)


@router.get("/registry/validate", response_model=ValidationResponse)
async def validate_registry(
    service: PromptService = Depends(get_prompt_service),
) -> ValidationResponse:
    """
    验证注册表完整性。

    检查：
    1. 注册表中的文件是否都存在
    2. 依赖的提示词是否都已注册
    """
    errors = service.validate_registry()
    return ValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
    )


@router.get("/registry/categories", response_model=Dict[str, Dict[str, Any]])
async def list_categories(
    service: PromptService = Depends(get_prompt_service),
) -> Dict[str, Dict[str, Any]]:
    """
    获取所有分类定义。

    返回分类的标签、颜色和排序等信息。
    """
    return service.get_all_categories()


@router.get("/registry/dependency-graph", response_model=DependencyGraphResponse)
async def get_dependency_graph(
    service: PromptService = Depends(get_prompt_service),
) -> DependencyGraphResponse:
    """
    获取提示词依赖关系图。

    返回所有提示词之间的依赖关系。
    """
    return DependencyGraphResponse(graph=service.get_dependency_graph())


@router.get("/by-category/{category}", response_model=List[str])
async def list_prompts_by_category(
    category: str,
    service: PromptService = Depends(get_prompt_service),
) -> List[str]:
    """
    按分类获取提示词列表。

    Args:
        category: 分类名（inspiration, blueprint, outline, writing, analysis, manga, protagonist）
    """
    return service.get_prompts_by_category(category)


@router.get("/by-status/{status}", response_model=List[str])
async def list_prompts_by_status(
    status: str,
    service: PromptService = Depends(get_prompt_service),
) -> List[str]:
    """
    按状态获取提示词列表。

    Args:
        status: 状态（active, experimental, unused, deprecated）
    """
    return service.get_prompts_by_status(status)


@router.get("/{name}/meta", response_model=PromptMetaResponse)
async def get_prompt_meta(
    name: str,
    service: PromptService = Depends(get_prompt_service),
) -> PromptMetaResponse:
    """
    获取提示词的注册表元数据。

    返回提示词的路径、分类、状态、依赖关系等信息。

    Args:
        name: 提示词名称
    """
    meta = service.get_prompt_meta(name)
    if not meta:
        raise ResourceNotFoundError("提示词元数据", name)

    return PromptMetaResponse(
        name=name,
        path=meta.get("path"),
        title=meta.get("title"),
        category=meta.get("category"),
        status=meta.get("status"),
        description=meta.get("description"),
        dependencies=meta.get("dependencies", []),
        used_by=meta.get("used_by", []),
    )


@router.get("/{name}/dependencies", response_model=List[str])
async def get_prompt_dependencies(
    name: str,
    service: PromptService = Depends(get_prompt_service),
) -> List[str]:
    """
    获取提示词的依赖列表。

    Args:
        name: 提示词名称
    """
    return service.get_prompt_dependencies(name)


@router.get("/{name}/reverse-dependencies", response_model=List[str])
async def get_prompt_reverse_dependencies(
    name: str,
    service: PromptService = Depends(get_prompt_service),
) -> List[str]:
    """
    获取依赖此提示词的其他提示词列表。

    Args:
        name: 提示词名称
    """
    return service.get_reverse_dependencies(name)

