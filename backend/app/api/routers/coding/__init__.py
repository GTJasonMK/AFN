"""
编程项目API路由

处理编程项目的CRUD、架构设计、目录结构和文件Prompt生成等操作。
支持两层结构：系统(System) -> 模块(Module)
支持文件驱动：目录结构 -> 源文件 -> 文件Prompt
"""

from fastapi import APIRouter

from .projects import router as projects_router
from .hierarchy import router as hierarchy_router
from .rag import router as rag_router
from .inspiration import router as inspiration_router
from .files import router as files_router

router = APIRouter()

# 注册子路由
router.include_router(projects_router, tags=["coding-projects"])
router.include_router(hierarchy_router, tags=["coding-hierarchy"])
router.include_router(files_router, tags=["coding-files"])
router.include_router(rag_router, tags=["coding-rag"])
router.include_router(inspiration_router, tags=["coding-inspiration"])
