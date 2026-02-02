"""
API路由汇总（桌面版 / WebUI）

说明：
- 默认桌面版不要求登录，直接注入默认用户（desktop_user）。
- 当启用 settings.auth_enabled=True 时，WebUI 将启用登录与多用户数据隔离（按 user_id）。
"""

from fastapi import APIRouter

from . import auth, embedding_config, llm_config, novels, writer, settings, image_generation, queue, character_portrait, prompts, theme_config, coding

api_router = APIRouter()

# 桌面版路由（无需认证）
api_router.include_router(auth.router)
api_router.include_router(novels.router, prefix="/api/novels")
api_router.include_router(writer.router, prefix="/api/writer")
api_router.include_router(coding.router, prefix="/api")  # 编程项目路由（路由内部已包含/coding/前缀）
api_router.include_router(llm_config.router)
api_router.include_router(embedding_config.router)
api_router.include_router(settings.router, prefix="/api/settings")
api_router.include_router(image_generation.router, prefix="/api")
api_router.include_router(queue.router)  # 队列管理（已包含/api/queue前缀）
api_router.include_router(character_portrait.router, prefix="/api")  # 角色立绘
api_router.include_router(prompts.router)  # 提示词管理（已包含/api/prompts前缀）
api_router.include_router(theme_config.router)  # 主题配置（已包含/api/theme-configs前缀）
