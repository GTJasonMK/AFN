"""FastAPI 应用入口（PyQt桌面版），负责装配路由、依赖与生命周期管理。

此版本不包含管理后台功能，专为PyQt桌面应用设计。
"""

import logging
from logging.config import dictConfig
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .db.init_db import init_db
from .services.prompt_service import PromptService
from .db.session import AsyncSessionLocal
from .exceptions import ArborisException

# 重要：必须先配置 logging，再导入 api_router
# 否则 router 模块中的 logger 会在配置完成前被创建，导致日志无法正常输出
dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": "storage/debug.log",
                "mode": "a",
                "formatter": "default",
                "encoding": "utf-8",
            }
        },
        "loggers": {
            "backend": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "backend.app": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "backend.api": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "backend.services": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.api.routers": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "app.services": {
                "level": settings.logging_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # 禁用 SQLAlchemy SQL 日志，避免淹没业务日志
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console", "file"],
        },
    }
)

# 在 logging 配置完成后导入 api_router，确保所有 router 模块的 logger 都能正确配置
from .api.routers import api_router

# 创建模块级别的 logger 并写入启动测试日志
logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("Arboris-Novel PyQt版 后端服务启动，logging 配置已完成")
logger.info("日志级别: %s", settings.logging_level)
logger.info("日志文件: backend/storage/debug.log")
logger.info("=" * 80)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库，并预热提示词缓存"""
    await init_db()
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()
    yield


app = FastAPI(
    title=f"{settings.app_name} - PyQt Desktop Edition",
    debug=settings.debug,
    version="1.0.0-pyqt",
    lifespan=lifespan,
)

# 全局异常处理器：捕获所有Arboris业务异常并转换为HTTP响应
@app.exception_handler(ArborisException)
async def arboris_exception_handler(request: Request, exc: ArborisException):
    """
    统一处理所有Arboris业务异常

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
