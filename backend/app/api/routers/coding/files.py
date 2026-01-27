"""
文件驱动 Prompt 生成路由（聚合入口）

说明：
- 原 `coding/files.py` 体量过大，已按职责拆分到 `coding/files_*.py`。
- 本文件仅负责聚合子路由，保持 `from .files import router` 的导入方式不变。
"""

from fastapi import APIRouter

from .files_agent_state import router as agent_state_router
from .files_directory_crud import router as directory_crud_router
from .files_directory_structure import router as directory_structure_router
from .files_plan_agent import router as plan_agent_router
from .files_plan_v2 import router as plan_v2_router
from .files_prompt_generation import router as prompt_generation_router
from .files_review_prompt import router as review_prompt_router
from .files_source_files import router as source_files_router
from .files_versions import router as versions_router

router = APIRouter()

# 注意：为避免静态路径被动态参数路由误匹配，先注册静态目录相关路由，再注册 /directories/{node_id} 等动态路由。
router.include_router(directory_structure_router)
router.include_router(agent_state_router)
router.include_router(plan_v2_router)
router.include_router(plan_agent_router)
router.include_router(directory_crud_router)

router.include_router(source_files_router)
router.include_router(prompt_generation_router)
router.include_router(review_prompt_router)
router.include_router(versions_router)

__all__ = ["router"]

