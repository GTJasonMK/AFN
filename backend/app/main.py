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
    """应用生命周期管理：启动时初始化数据库，并预热提示词缓存；关闭时清理资源"""
    # 启动阶段
    await init_db()
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()
    yield
    # 关闭阶段：清理HTTP客户端连接池
    from .services.image_generation.service import HTTPClientManager
    await HTTPClientManager.close_client()


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
