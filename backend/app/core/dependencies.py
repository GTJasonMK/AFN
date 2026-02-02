"""
依赖注入模块（默认桌面版 / WebUI 可选登录）

默认行为：
- 桌面版/开发环境：使用固定的默认用户（desktop_user），无需登录认证。

可选行为（WebUI）：
- 当 `settings.auth_enabled=True` 时：要求登录（JWT），并启用多用户数据隔离（按 user_id）。
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..repositories.user_repository import UserRepository
from ..schemas.user import UserInDB
from ..core.config import settings

logger = logging.getLogger(__name__)

AUTH_COOKIE_NAME = "afn_access_token"


def _extract_bearer_token(authorization: str | None) -> str | None:
    """从 Authorization: Bearer <token> 中提取 token。"""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2:
        return None
    scheme, token = parts[0], parts[1]
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


async def get_default_user(
    session: AsyncSession = Depends(get_session),
    request: Request | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> UserInDB:
    """
    获取“当前用户”。

    - 当 auth_enabled=False：返回默认用户 desktop_user（与历史桌面版逻辑一致）。
    - 当 auth_enabled=True：从 Cookie 或 Authorization Bearer 读取 JWT，并解析为当前用户。

    Raises:
        HTTPException: 未登录/令牌无效/用户不存在时抛出 401；默认用户缺失时抛出 500
    """
    repo = UserRepository(session)

    if not getattr(settings, "auth_enabled", False):
        # 兼容旧行为：无登录时直接注入默认用户（username="desktop_user"）
        user = await repo.get_by_username("desktop_user")
        if not user:
            logger.error("默认用户 'desktop_user' 未找到，数据库可能未正确初始化")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="默认用户未初始化，请删除 storage/afn.db 后重启应用",
            )
        return UserInDB.model_validate(user)

    # 开启登录：必须提供 token
    token = _extract_bearer_token(authorization)
    if not token and request is not None:
        try:
            token = request.cookies.get(AUTH_COOKIE_NAME) or None
        except Exception:
            token = None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期，请先登录",
        )

    try:
        from jose import JWTError, jwt

        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
        user_id = int(sub)
    except HTTPException:
        raise
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录信息无效，请重新登录")
    except Exception as exc:
        # jose.JWTError / 过期等
        logger.debug("JWT 解析失败: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")

    user = await repo.get_by_id(user_id)
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用")

    return UserInDB.model_validate(user)


async def require_admin_user(
    current_user: UserInDB = Depends(get_default_user),
) -> UserInDB:
    """管理员权限校验：当前实现以 username == 'desktop_user' 作为管理员。"""
    if (current_user.username or "").strip() != "desktop_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限（desktop_user）",
        )
    return current_user


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
        service = VectorStoreService()
    except RuntimeError as exc:
        logger.warning("向量库初始化失败，RAG功能将被禁用: %s", exc)
        return None

    # VectorStoreService 内部可能捕获连接异常并将 _client 置空；
    # 这里统一将“不可用实例”视为初始化失败，兑现本依赖的返回契约（失败则返回 None）。
    if not getattr(service, "_client", None):
        logger.warning("向量库初始化失败（客户端不可用），RAG功能将被禁用")
        return None

    return service


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


async def get_coding_project_service(
    session: AsyncSession = Depends(get_session),
) -> "CodingProjectService":
    """
    获取CodingProjectService实例（依赖注入）

    统一Service获取方式，避免在每个路由函数中重复初始化。

    Returns:
        CodingProjectService实例
    """
    from ..services.coding import CodingProjectService
    return CodingProjectService(session)


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


async def get_conversation_service(
    session: AsyncSession = Depends(get_session),
) -> "ConversationService":
    """
    获取ConversationService实例（依赖注入）

    统一Service获取方式，避免在每个路由函数中重复初始化。

    Returns:
        ConversationService实例
    """
    from ..services.conversation_service import ConversationService
    return ConversationService(session)


async def get_coding_conversation_service(
    session: AsyncSession = Depends(get_session),
) -> "ConversationService":
    """
    获取 Coding 项目的 ConversationService 实例（依赖注入）

    Coding 项目与 Novel 项目对话表不同，需要显式指定 project_type="coding"。
    """
    from ..services.conversation_service import ConversationService
    return ConversationService(session, project_type="coding")


async def get_inspiration_service(
    session: AsyncSession = Depends(get_session),
    llm_service: "LLMService" = Depends(get_llm_service),
    prompt_service: "PromptService" = Depends(get_prompt_service),
) -> "InspirationService":
    """
    获取InspirationService实例（依赖注入）

    统一Service获取方式，封装灵感对话的业务逻辑。

    Returns:
        InspirationService实例
    """
    from ..services.inspiration_service import InspirationService
    return InspirationService(session, llm_service, prompt_service)


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


async def get_part_outline_service(
    session: AsyncSession = Depends(get_session),
    llm_service: "LLMService" = Depends(get_llm_service),
    prompt_service: "PromptService" = Depends(get_prompt_service),
    novel_service: "NovelService" = Depends(get_novel_service),
    vector_store: Optional["VectorStoreService"] = Depends(get_vector_store),
) -> "PartOutlineService":
    """
    获取PartOutlineService实例（依赖注入）

    统一Service获取方式，所有依赖通过参数注入，便于测试和解耦。

    Returns:
        PartOutlineService实例

    Example:
        ```python
        @router.post("/parts/generate")
        async def generate_parts(
            part_service: PartOutlineService = Depends(get_part_outline_service),
        ):
            return await part_service.generate_part_outlines(...)
        ```
    """
    from ..services.part_outline import PartOutlineService
    return PartOutlineService(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
        novel_service=novel_service,
        vector_store=vector_store,
    )


async def get_chapter_generation_service(
    session: AsyncSession = Depends(get_session),
    llm_service: "LLMService" = Depends(get_llm_service),
) -> "ChapterGenerationService":
    """
    获取ChapterGenerationService实例（依赖注入）

    统一Service获取方式，所有依赖通过参数注入。

    Returns:
        ChapterGenerationService实例
    """
    from ..services.chapter_generation import ChapterGenerationService
    return ChapterGenerationService(session, llm_service)


async def get_avatar_service(
    session: AsyncSession = Depends(get_session),
    llm_service: "LLMService" = Depends(get_llm_service),
    prompt_service: "PromptService" = Depends(get_prompt_service),
) -> "AvatarService":
    """
    获取AvatarService实例（依赖注入）

    统一Service获取方式，所有依赖通过参数注入。

    Returns:
        AvatarService实例

    Example:
        ```python
        @router.post("/avatar/generate")
        async def generate_avatar(
            avatar_service: AvatarService = Depends(get_avatar_service),
        ):
            return await avatar_service.generate_avatar(...)
        ```
    """
    from ..services.avatar_service import AvatarService
    return AvatarService(session, llm_service, prompt_service)


# ============================================================================
# 配置服务依赖注入
# ============================================================================

async def get_llm_config_service(
    session: AsyncSession = Depends(get_session),
) -> "LLMConfigService":
    """
    获取LLMConfigService实例（依赖注入）

    Returns:
        LLMConfigService实例
    """
    from ..services.llm_config_service import LLMConfigService
    return LLMConfigService(session)


async def get_embedding_config_service(
    session: AsyncSession = Depends(get_session),
) -> "EmbeddingConfigService":
    """
    获取EmbeddingConfigService实例（依赖注入）

    Returns:
        EmbeddingConfigService实例
    """
    from ..services.embedding_config_service import EmbeddingConfigService
    return EmbeddingConfigService(session)


async def get_image_config_service(
    session: AsyncSession = Depends(get_session),
) -> "ImageConfigService":
    """
    获取ImageConfigService实例（依赖注入）

    Returns:
        ImageConfigService实例
    """
    from ..services.image_generation import ImageConfigService
    return ImageConfigService(session)


async def get_import_analysis_service(
    session: AsyncSession = Depends(get_session),
    llm_service: "LLMService" = Depends(get_llm_service),
    prompt_service: "PromptService" = Depends(get_prompt_service),
) -> "ImportAnalysisService":
    """
    获取ImportAnalysisService实例（依赖注入）

    用于外部小说导入和分析功能。

    Returns:
        ImportAnalysisService实例
    """
    from ..services.import_analysis import ImportAnalysisService
    return ImportAnalysisService(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )


async def get_theme_config_service(
    session: AsyncSession = Depends(get_session),
) -> "ThemeConfigService":
    """
    获取ThemeConfigService实例（依赖注入）

    Returns:
        ThemeConfigService实例
    """
    from ..services.theme_config_service import ThemeConfigService
    return ThemeConfigService(session)
