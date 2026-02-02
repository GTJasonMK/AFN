"""FastAPI 应用入口（PyQt 桌面版）。

职责：
- 配置日志系统（必须早于 router 导入）
- 装配路由、全局异常处理器与中间件
- 生命周期：初始化数据库、预热提示词缓存、（可选）预加载本地嵌入模型
"""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .core.config import settings
from .core.logging_config import log_startup_info, setup_exception_hook, setup_logging
from .db.init_db import init_db
from .db.session import AsyncSessionLocal, engine
from .exceptions import AFNException
from .services.prompt_service import PromptService


# 重要：必须先配置 logging，再导入 api_router
# 否则 router 模块中的 logger 会在配置完成前被创建，导致日志无法按域路由到各自文件
setup_logging()
setup_exception_hook()

from .api.routers import api_router

log_startup_info()
logger = logging.getLogger(__name__)


async def _preload_embedding_model_if_needed(session: AsyncSession) -> None:
    """如果激活的嵌入配置为本地模型，则在启动时触发异步预加载（非阻塞）。"""
    try:
        from .repositories.embedding_config_repository import EmbeddingConfigRepository
        from .repositories.user_repository import UserRepository

        user = await UserRepository(session).get_by_username("desktop_user")
        if not user:
            return

        active_config = await EmbeddingConfigRepository(session).get_active_config(user.id)
        if not active_config:
            return

        provider = (active_config.provider or "").lower()
        if provider != "local":
            return

        model_name = (active_config.model_name or "").strip()
        if not model_name:
            logger.info(
                "嵌入模型预加载跳过：provider=local 但未配置 model_name（仅影响启动预热；首次使用将按需加载）。"
                "如需启动预热，请在「设置 - 嵌入模型」中填写模型名称，例如：BAAI/bge-base-zh-v1.5"
            )
            return

        # 仅在确认需要预加载时才导入 embedding_service（避免不必要的启动开销）
        from .services.embedding_service import embedding_preloader

        await embedding_preloader.start_preload(model_name)
    except Exception as exc:
        logger.warning("嵌入模型预加载初始化失败，将在首次使用时按需加载: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库并预热缓存；关闭时清理资源。"""
    await init_db()

    async with AsyncSessionLocal() as session:
        await PromptService(session).preload()
        await _preload_embedding_model_if_needed(session)

    yield

    # 关闭阶段：清理 HTTP 客户端连接池
    from .services.image_generation.service import HTTPClientManager

    await HTTPClientManager.close_client()


app = FastAPI(
    title=f"{settings.app_name} - PyQt Desktop Edition",
    debug=settings.debug,
    version="1.0.0-pyqt",
    lifespan=lifespan,
)


@app.exception_handler(AFNException)
async def afn_exception_handler(request: Request, exc: AFNException):
    """统一处理 AFN 业务异常（用户看到 message，日志保留 detail）。"""
    logger.error(
        "业务异常 [%s %s]: %s (状态码=%d)",
        request.method,
        request.url.path,
        exc.detail,
        exc.status_code,
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕获所有未处理异常，避免服务崩溃，并返回标准 500 响应。"""
    logger.critical(
        "未捕获异常 [%s %s]: %s\n%s",
        request.method,
        request.url.path,
        str(exc),
        traceback.format_exc(),
    )
    for handler in logging.root.handlers:
        handler.flush()
    return JSONResponse(status_code=500, content={"detail": f"服务器内部错误: {type(exc).__name__}: {exc}"})


# CORS 配置：桌面版仅允许本地访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """健康检查接口，返回应用状态。"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0-pyqt",
        "edition": "Desktop (PyQt)",
    }


@app.get("/api/db-health", tags=["Health"])
async def db_health_check():
    """数据库健康检查。"""
    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: sync_conn.execute(select(1)))
        return {"status": "ok"}
    except Exception as exc:
        logger.error("数据库健康检查失败: %s", exc, exc_info=True)
        return {"status": "error", "detail": str(exc)}
