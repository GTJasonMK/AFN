"""
依赖注入模块（PyQt桌面版 - 无需认证）

桌面版使用固定的默认用户，无需登录认证。
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..repositories.user_repository import UserRepository
from ..schemas.user import UserInDB
from ..core.config import settings

logger = logging.getLogger(__name__)


async def get_default_user(
    session: AsyncSession = Depends(get_session),
) -> UserInDB:
    """
    获取默认用户（桌面版专用）

    桌面版自动使用默认用户，无需登录认证。
    默认用户在数据库初始化时自动创建。

    Raises:
        HTTPException: 当默认用户不存在时抛出500错误
    """
    repo = UserRepository(session)

    # 尝试获取默认用户（username="desktop_user"）
    user = await repo.get_by_username("desktop_user")

    if not user:
        # 默认用户不存在，立即失败
        # 不应该回退到获取任意用户，这会导致数据混乱
        logger.error("默认用户 'desktop_user' 未找到，数据库可能未正确初始化")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="默认用户未初始化，请删除 backend/storage/arboris.db 后重启应用"
        )

    return UserInDB.model_validate(user)


async def get_vector_store() -> Optional["VectorStoreService"]:
    """
    获取向量库服务实例（依赖注入）

    自动处理向量库初始化失败的情况，避免代码重复。

    Returns:
        VectorStoreService实例，如果未启用或初始化失败则返回None

    Example:
        ```python
        @router.post("/chapters/generate")
        async def generate_chapter(
            vector_store: Optional[VectorStoreService] = Depends(get_vector_store)
        ):
            if vector_store:
                # 使用RAG检索
                context = await vector_store.query_chunks(...)
        ```
    """
    from ..services.vector_store_service import VectorStoreService

    if not settings.vector_store_enabled:
        logger.debug("向量库未启用，RAG功能将被禁用")
        return None

    try:
        return VectorStoreService()
    except RuntimeError as exc:
        logger.warning("向量库初始化失败，RAG功能将被禁用: %s", exc)
        return None


async def get_novel_service(
    session: AsyncSession = Depends(get_session),
) -> "NovelService":
    """
    获取NovelService实例（依赖注入）

    统一Service获取方式，避免在每个路由函数中重复初始化。

    Returns:
        NovelService实例

    Example:
        ```python
        @router.get("/{project_id}")
        async def get_novel(
            project_id: str,
            novel_service: NovelService = Depends(get_novel_service),
        ):
            return await novel_service.get_project_schema(project_id, user_id)
        ```
    """
    from ..services.novel_service import NovelService
    return NovelService(session)


async def get_llm_service(
    session: AsyncSession = Depends(get_session),
) -> "LLMService":
    """
    获取LLMService实例（依赖注入）

    统一Service获取方式，避免在每个路由函数中重复初始化。

    Returns:
        LLMService实例

    Example:
        ```python
        @router.post("/generate")
        async def generate_content(
            llm_service: LLMService = Depends(get_llm_service),
        ):
            response = await llm_service.get_llm_response(...)
        ```
    """
    from ..services.llm_service import LLMService
    return LLMService(session)


async def get_prompt_service(
    session: AsyncSession = Depends(get_session),
) -> "PromptService":
    """
    获取PromptService实例（依赖注入）

    统一Service获取方式，避免在每个路由函数中重复初始化。

    Returns:
        PromptService实例

    Example:
        ```python
        @router.post("/execute")
        async def execute_prompt(
            prompt_service: PromptService = Depends(get_prompt_service),
        ):
            prompt = await prompt_service.get_prompt("writing")
        ```
    """
    from ..services.prompt_service import PromptService
    return PromptService(session)


async def get_vector_ingestion_service(
    llm_service: "LLMService" = Depends(get_llm_service),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> Optional["ChapterIngestionService"]:
    """
    获取向量入库服务实例（依赖注入）

    统一向量库初始化逻辑，自动处理初始化失败的情况，避免代码重复。
    如果向量库未启用或初始化失败，返回None。

    Returns:
        ChapterIngestionService实例，如果未启用或初始化失败则返回None

    Example:
        ```python
        @router.post("/chapters/generate")
        async def generate_chapter(
            ingestion_service: Optional[ChapterIngestionService] = Depends(get_vector_ingestion_service)
        ):
            if ingestion_service:
                # 向量化章节内容
                await ingestion_service.ingest_chapter(...)
        ```
    """
    from ..services.chapter_ingest_service import ChapterIngestionService

    # 依赖get_vector_store，避免重复初始化逻辑
    if vector_store is None:
        return None

    return ChapterIngestionService(
        llm_service=llm_service,
        vector_store=vector_store
    )

