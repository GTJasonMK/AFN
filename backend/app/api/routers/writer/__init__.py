"""
写作相关路由模块

拆分后的路由结构：
- chapter_generation.py: 章节生成和重试
- chapter_management.py: 章节管理（选择、评价、编辑、删除）
- chapter_outlines.py: 章节大纲管理
- part_outlines.py: 部分大纲管理（长篇小说）
- rag_query.py: RAG检索查询（测试向量检索效果）
- content_optimization.py: 正文优化（段落分析、连贯性检查）
- manga_prompt_v2.py: 漫画提示词生成（基于专业漫画分镜架构）
"""

from fastapi import APIRouter

from .chapter_generation import router as chapter_generation_router
from .chapter_management import router as chapter_management_router
from .chapter_outlines import router as chapter_outlines_router
from .part_outlines import router as part_outlines_router
from .rag_query import router as rag_query_router
from .content_optimization import router as content_optimization_router
from .manga_prompt_v2 import router as manga_prompt_router

# 创建writer总路由器（prefix在主路由器中设置）
router = APIRouter(tags=["Writer"])

# 挂载所有子路由
router.include_router(chapter_generation_router)
router.include_router(chapter_management_router)
router.include_router(chapter_outlines_router)
router.include_router(part_outlines_router)
router.include_router(rag_query_router)
router.include_router(content_optimization_router)
router.include_router(manga_prompt_router)

__all__ = ["router"]
