"""
写作相关路由模块

拆分后的路由结构：
- chapter_generation.py: 章节生成和重试
- chapter_management.py: 章节管理（选择、评价、编辑、删除）
- chapter_outlines.py: 章节大纲管理
- part_outlines.py: 部分大纲管理（长篇小说）
"""

from fastapi import APIRouter

from .chapter_generation import router as chapter_generation_router
from .chapter_management import router as chapter_management_router
from .chapter_outlines import router as chapter_outlines_router
from .part_outlines import router as part_outlines_router

# 创建writer总路由器（prefix在主路由器中设置）
router = APIRouter(tags=["Writer"])

# 挂载所有子路由
router.include_router(chapter_generation_router)
router.include_router(chapter_management_router)
router.include_router(chapter_outlines_router)
router.include_router(part_outlines_router)

__all__ = ["router"]
