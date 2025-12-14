"""
API路由汇总（PyQt桌面版）

桌面版不包含认证路由，直接使用默认用户。
"""

from fastapi import APIRouter

from . import embedding_config, llm_config, novels, writer, settings, image_generation

api_router = APIRouter()

# 桌面版路由（无需认证）
api_router.include_router(novels.router, prefix="/api/novels")
api_router.include_router(writer.router, prefix="/api/writer")
api_router.include_router(llm_config.router)
api_router.include_router(embedding_config.router)
api_router.include_router(settings.router, prefix="/api/settings")
api_router.include_router(image_generation.router, prefix="/api")
