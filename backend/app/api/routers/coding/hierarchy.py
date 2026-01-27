"""
编程项目两层结构管理路由（聚合入口）

说明：
- 原 `hierarchy.py` 体量较大，已按职责拆分为 `hierarchy_*.py`；
- 本文件仅负责聚合子路由，保持 `backend.app.api.routers.coding.hierarchy:router` 的 import 路径不变。
"""

from fastapi import APIRouter

from .hierarchy_dependencies import router as dependencies_router
from .hierarchy_generation import router as generation_router
from .hierarchy_modules import router as modules_router
from .hierarchy_systems import router as systems_router

router = APIRouter()
router.include_router(systems_router)
router.include_router(modules_router)
router.include_router(generation_router)
router.include_router(dependencies_router)

__all__ = ["router"]

