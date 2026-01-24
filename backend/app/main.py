import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.logging_config import setup_logging, setup_exception_hook, log_startup_info
from .db.init_db import init_db
from .services.prompt_service import PromptService
from .db.session import AsyncSessionLocal, engine
from .exceptions import AFNException
from .models import User  # Import User model
from sqlalchemy import select

# ... (setup_logging calls) ...

setup_logging()
setup_exception_hook()

from .api.routers import api_router
log_startup_info()
logger = logging.getLogger(__name__)

async def ensure_default_user_exists():
    """Ensures the default 'desktop_user' exists on startup."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == "desktop_user"))
        if not result.scalars().first():
            logger.warning("Default user 'desktop_user' not found. Creating it now.")
            from .repositories.user_repository import UserRepository
            repo = UserRepository(session)
            await repo.create_default_user()
            await session.commit()
            logger.info("Default user 'desktop_user' created.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await init_db()
    await ensure_default_user_exists() # Ensure user exists
    
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()
        
    await _preload_embedding_model_if_needed()

    yield
    # ... (cleanup)
    from .services.image_generation.service import HTTPClientManager
    await HTTPClientManager.close_client()
    
# ... (_preload_embedding_model_if_needed function)
async def _preload_embedding_model_if_needed():
    # ... same as before
    pass

app = FastAPI(
    title=f"{settings.app_name} - PyQt Desktop Edition",
    debug=settings.debug,
    version="1.0.0-pyqt",
    lifespan=lifespan,
)

# ... (exception handlers)
@app.exception_handler(AFNException)
async def afn_exception_handler(request: Request, exc: AFNException):
    logger.error("...")
    return JSONResponse(...)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # ...
    return JSONResponse(...)
    
# ... (CORS middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Health checks
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check():
    """健康检查接口，返回应用状态。"""
    return {"status": "healthy", "app": settings.app_name}

@app.get("/api/db-health", tags=["Health"])
async def db_health_check():
    """数据库健康检查"""
    try:
        async with engine.connect() as conn:
            await conn.run_sync(lambda sync_conn: sync_conn.execute(select(1)))
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"DB Health Check failed: {e}")
        return {"status": "error", "detail": str(e)}