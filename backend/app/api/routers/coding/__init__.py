"""
编程项目API路由

处理编程项目的CRUD、功能Prompt生成、内容管理等操作。
支持三层结构：系统(System) -> 模块(Module) -> 功能(Feature)
"""

from fastapi import APIRouter

from .projects import router as projects_router
from .feature_generation import router as feature_generation_router
from .hierarchy import router as hierarchy_router
from .rag import router as rag_router
from .inspiration import router as inspiration_router
from .optimization import router as optimization_router

router = APIRouter()

# 注册子路由
router.include_router(projects_router, tags=["coding-projects"])
router.include_router(hierarchy_router, tags=["coding-hierarchy"])
router.include_router(feature_generation_router, tags=["coding-features"])
router.include_router(rag_router, tags=["coding-rag"])
router.include_router(inspiration_router, tags=["coding-inspiration"])
router.include_router(optimization_router, tags=["coding-optimization"])
