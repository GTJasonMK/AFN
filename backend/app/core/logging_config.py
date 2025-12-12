"""
日志配置模块

提供统一的日志配置，支持控制台输出和文件输出。
必须在导入其他模块之前调用 setup_logging()。
"""

import sys
import logging
import traceback
from logging.config import dictConfig

from .config import settings


def get_logging_config() -> dict:
    """
    获取日志配置字典

    Returns:
        日志配置字典，可直接传递给 dictConfig
    """
    return {
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
                "stream": "ext://sys.stdout",
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
            "app.utils": {
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


def setup_logging() -> None:
    """
    配置日志系统

    必须在导入其他模块之前调用，否则这些模块中的 logger
    会在配置完成前被创建，导致日志无法正常输出。
    """
    dictConfig(get_logging_config())


def setup_exception_hook() -> None:
    """
    设置全局异常钩子，捕获未处理的异常并记录到日志
    """
    original_hook = sys.excepthook

    def exception_hook(exc_type, exc_value, exc_traceback):
        # 记录到日志
        logger = logging.getLogger(__name__)
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"未捕获的异常导致程序崩溃:\n{error_msg}")

        # 确保日志被写入
        for handler in logging.root.handlers:
            handler.flush()

        # 调用原始钩子
        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook


def log_startup_info() -> None:
    """
    输出启动信息到日志
    """
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("AFN (Agents for Novel) 后端服务启动，logging 配置已完成")
    logger.info("日志级别: %s", settings.logging_level)
    logger.info("日志文件: backend/storage/debug.log")
    logger.info("=" * 80)
