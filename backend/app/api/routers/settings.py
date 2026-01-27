"""
高级配置管理路由（聚合入口）

说明：
- 具体的配置读写/导入导出逻辑已按主题拆分到 `settings_*.py`；
- 本文件仅负责聚合各子路由，保持对外 `settings.router` 的 import 路径不变。
"""

from fastapi import APIRouter

from .settings_advanced import router as advanced_router
from .settings_all import router as all_router
from .settings_max_tokens import router as max_tokens_router
from .settings_queue import router as queue_router
from .settings_temperature import router as temperature_router

router = APIRouter()
router.include_router(advanced_router)
router.include_router(max_tokens_router)
router.include_router(temperature_router)
router.include_router(queue_router)
router.include_router(all_router)

__all__ = ["router"]

