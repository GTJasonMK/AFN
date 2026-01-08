"""FastAPI 应用入口（PyQt桌面版），负责装配路由、依赖与生命周期管理。

此版本不包含管理后台功能，专为PyQt桌面应用设计。
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging_config import setup_logging, setup_exception_hook, log_startup_info
from .db.init_db import init_db
from .services.prompt_service import PromptService
from .db.session import AsyncSessionLocal
from .exceptions import AFNException


# 重要：必须先配置 logging，再导入 api_router
# 否则 router 模块中的 logger 会在配置完成前被创建，导致日志无法正常输出
setup_logging()
setup_exception_hook()

# 在 logging 配置完成后导入 api_router，确保所有 router 模块的 logger 都能正确配置
from .api.routers import api_router

# 输出启动信息
log_startup_info()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库，并预热提示词缓存和嵌入模型；关闭时清理资源"""
    # 启动阶段
    await init_db()

    # 预热提示词缓存
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()

    # 异步预加载本地嵌入模型（非阻塞）
    await _preload_embedding_model_if_needed()

    yield
    # 关闭阶段：清理HTTP客户端连接池
    from .services.image_generation.service import HTTPClientManager
    await HTTPClientManager.close_client()


async def _preload_embedding_model_if_needed():
    """
    如果配置了本地嵌入模型，则启动异步预加载

    这是一个非阻塞操作，预加载在后台进行，不会延迟应用启动。
    """
    from .services.embedding_service import embedding_preloader
    from .repositories.embedding_config_repository import EmbeddingConfigRepository
    from .models import User

    try:
        async with AsyncSessionLocal() as session:
            # 获取默认用户
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.username == "desktop_user")
            )
            user = result.scalars().first()
            if not user:
                logger.debug("预加载嵌入模型：未找到默认用户，跳过")
                return

            # 获取激活的嵌入配置
            embedding_repo = EmbeddingConfigRepository(session)
            config = await embedding_repo.get_active_config(user.id)

            if not config:
                logger.debug("预加载嵌入模型：未配置嵌入模型，跳过")
                return

            # 只预加载本地模型
            if config.provider != "local":
                logger.debug("预加载嵌入模型：当前配置非本地模型（%s），跳过", config.provider)
                return

            model_name = config.model_name or "BAAI/bge-base-zh-v1.5"
            logger.info("触发嵌入模型异步预加载: %s", model_name)
            await embedding_preloader.start_preload(model_name)

    except Exception as e:
        logger.warning("预加载嵌入模型检查失败: %s", e)


app = FastAPI(
    title=f"{settings.app_name} - PyQt Desktop Edition",
    debug=settings.debug,
    version="1.0.0-pyqt",
    lifespan=lifespan,
)

# 全局异常处理器：捕获所有AFN业务异常并转换为HTTP响应
@app.exception_handler(AFNException)
async def afn_exception_handler(request: Request, exc: AFNException):
    """
    统一处理所有AFN业务异常

    将业务异常转换为标准的HTTP响应格式。
    日志中会记录详细错误信息（detail），用户只看到友好的message。
    """
    logger.error(
        "业务异常 [%s %s]: %s (状态码: %d)",
        request.method,
        request.url.path,
        exc.detail,
        exc.status_code
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


# 全局异常处理器：捕获所有未处理的异常
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    捕获所有未处理的异常，防止服务崩溃
    """
    import traceback
    error_traceback = traceback.format_exc()
    logger.critical(
        "未捕获的异常 [%s %s]: %s\n%s",
        request.method,
        request.url.path,
        str(exc),
        error_traceback
    )
    # 确保日志被写入
    for handler in logging.root.handlers:
        handler.flush()

    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {type(exc).__name__}: {str(exc)}"}
    )

# CORS 配置，桌面版允许本地访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# 健康检查接口（用于应用自检）
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
