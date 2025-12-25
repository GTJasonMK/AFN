"""
API路由汇总（PyQt桌面版）

桌面版不包含认证路由，直接使用默认用户。
"""

from fastapi import APIRouter

from . import embedding_config, llm_config, novels, writer, settings, image_generation, queue, character_portrait, prompts, theme_config

api_router = APIRouter()

# 桌面版路由（无需认证）
api_router.include_router(novels.router, prefix="/api/novels")
api_router.include_router(writer.router, prefix="/api/writer")
api_router.include_router(llm_config.router)
api_router.include_router(embedding_config.router)
api_router.include_router(settings.router, prefix="/api/settings")
api_router.include_router(image_generation.router, prefix="/api")
api_router.include_router(queue.router)  # 队列管理（已包含/api/queue前缀）
api_router.include_router(character_portrait.router, prefix="/api")  # 角色立绘
api_router.include_router(prompts.router)  # 提示词管理（已包含/api/prompts前缀）
api_router.include_router(theme_config.router)  # 主题配置（已包含/api/theme-configs前缀）
