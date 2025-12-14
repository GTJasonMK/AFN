"""
Gemini Business API 代理服务

主入口文件
- FastAPI 应用初始化
- 中间件配置
- 生命周期管理
"""
import logging
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse

from app.config import config_manager, STATIC_DIR, IMAGES_DIR
from app.api import api_router
from app.services.account_manager import account_manager
from app.services.conversation_manager import conversation_manager
from app.services.token_manager import token_manager
from app.services.jwt_service import close_http_client
from app.services.image_service import image_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("正在启动 Gemini Business API 代理服务...")

    # 加载配置
    config_manager.load_config()
    logger.info(f"配置已加载: {len(config_manager.config.accounts)} 个账号")

    # 加载账号
    account_manager.load_accounts()
    total, available = account_manager.get_account_count()
    logger.info(f"账号状态: {available}/{total} 可用")

    # 加载 API Token（兼容旧配置中的静态 token）
    token_manager.load(config_manager.config.api_tokens)
    token_stats = token_manager.get_stats()
    logger.info(f"API Token: {token_stats.enabled_tokens}/{token_stats.total_tokens} 可用")

    # 加载会话
    conversation_manager.load_conversations()

    # 根据现有会话分布初始化轮训索引（确保负载均衡）
    account_usage = conversation_manager.get_account_usage()
    account_manager.initialize_round_robin(account_usage)

    # 启动定时清理任务
    cleanup_task = asyncio.create_task(periodic_cleanup())

    logger.info("服务启动完成")

    yield

    # 关闭时
    logger.info("正在关闭服务...")

    # 取消清理任务
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # 关闭HTTP客户端
    await close_http_client()

    logger.info("服务已关闭")


async def periodic_cleanup():
    """定时清理任务"""
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时执行一次

            # 清理过期会话
            conversation_manager.cleanup_expired(max_age_seconds=86400)

            # 清理图片缓存
            image_service.cleanup_cache()

            # 清理旧图片（保留24小时）
            image_service.cleanup_old_images(max_age_hours=24)

            logger.info("定时清理完成")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"定时清理失败: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="Gemini Business API Proxy",
    description="Google Gemini Business API 代理服务，提供 OpenAI 兼容接口",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    logger.debug(f"{request.method} {request.url.path}")
    response = await call_next(request)

    # 注意：/v1/chat/completions 的 token 消耗在 chat.py 中记录
    # 这里只记录其他 /v1/ API 的调用次数（不含 token 消耗）
    if request.url.path.startswith("/v1/") and not request.url.path.endswith("/chat/completions"):
        if response.status_code == 200:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_token = auth_header[7:]
                # 只记录请求次数，不记录 token 消耗
                token_manager.record_usage(api_token, 0)

    return response


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.exception(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": {"message": str(exc), "type": "server_error"}}
    )


# 注册API路由
app.include_router(api_router)

# 挂载静态文件目录
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 挂载图片目录（用于直接访问图片）
if IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="images")


# 聊天页面
@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """聊天页面"""
    chat_file = STATIC_DIR / "chat.html"
    if chat_file.exists():
        return HTMLResponse(content=chat_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Chat page not found</h1>", status_code=404)


# 根路径
@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径 - 返回管理界面或欢迎信息"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gemini Business API Proxy</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #1a73e8; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 4px; }
            code { background: #e8e8e8; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>Gemini Business API Proxy</h1>
        <p>OpenAI 兼容的 Google Gemini Business API 代理服务</p>

        <h2>API 端点</h2>
        <div class="endpoint">
            <strong>POST</strong> <code>/v1/chat/completions</code> - 聊天补全
        </div>
        <div class="endpoint">
            <strong>GET</strong> <code>/v1/models</code> - 模型列表
        </div>
        <div class="endpoint">
            <strong>POST</strong> <code>/v1/files</code> - 文件上传
        </div>
        <div class="endpoint">
            <strong>GET</strong> <code>/api/admin/status</code> - 系统状态
        </div>

        <h2>文档</h2>
        <p>查看 <a href="/docs">API 文档</a> 获取详细信息</p>
    </body>
    </html>
    """)


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    total, available = account_manager.get_account_count()
    return {
        "status": "healthy" if available > 0 else "degraded",
        "accounts": {"total": total, "available": available}
    }


def main():
    """主函数"""
    config = config_manager.config

    host = config.host if hasattr(config, 'host') else "0.0.0.0"
    port = config.port if hasattr(config, 'port') else 8000

    logger.info(f"启动服务: http://{host}:{port}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
