import logging
import os

from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..core.config import settings
from ..core.security import hash_password
from ..models import Prompt, User
from .base import Base
from .session import AsyncSessionLocal, engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """初始化数据库结构并确保默认桌面用户存在（PyQt版）。"""

    await _ensure_database_exists()

    # ---- 第一步：创建所有表结构 ----
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表结构已初始化")

    # ---- 第二步：确保默认桌面用户存在（PyQt版无需管理员） ----
    async with AsyncSessionLocal() as session:
        # 检查是否存在默认桌面用户
        desktop_user_exists = await session.execute(
            select(User).where(User.username == "desktop_user")
        )
        if not desktop_user_exists.scalars().first():
            logger.info("正在创建默认桌面用户 ...")
            desktop_user = User(
                username="desktop_user",
                hashed_password=hash_password("desktop"),  # 密码无关紧要，不会用到
            )

            session.add(desktop_user)
            try:
                await session.commit()
                logger.info("默认桌面用户创建完成：desktop_user")
            except IntegrityError:
                await session.rollback()
                logger.exception("默认桌面用户创建失败，可能是并发启动导致")

        # ---- 第三步：加载默认 Prompts ----
        await _ensure_default_prompts(session)

        await session.commit()
        logger.info("PyQt桌面版数据库初始化完成")


async def _ensure_database_exists() -> None:
    """在首次连接前确认数据库存在，针对不同驱动做最小化准备工作。"""
    url = make_url(settings.sqlalchemy_database_uri)

    if url.get_backend_name() == "sqlite":
        # SQLite 采用文件数据库，确保父目录存在即可，无需额外建库语句
        db_path = Path(url.database or "").expanduser()
        if not db_path.is_absolute():
            project_root = Path(__file__).resolve().parents[2]
            db_path = (project_root / db_path).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return

    database = (url.database or "").strip("/")
    if not database:
        return

    admin_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=None,
        query=url.query,
    )

    admin_engine = create_async_engine(
        admin_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    async with admin_engine.begin() as conn:
        await conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database}`"))
    await admin_engine.dispose()


async def _ensure_default_prompts(session: AsyncSession) -> None:
    """
    确保默认提示词存在，并同步文件更新到数据库。

    策略：
    - 新提示词：插入数据库
    - 已存在的提示词：如果文件内容不同，更新数据库
    """
    from ..services.prompt_service import get_prompt_cache

    # 优先使用环境变量指定的路径（打包环境），否则使用相对路径（开发环境）
    prompts_dir_env = os.environ.get('PROMPTS_DIR')
    if prompts_dir_env:
        prompts_dir = Path(prompts_dir_env)
    else:
        prompts_dir = Path(__file__).resolve().parents[2] / "prompts"

    if not prompts_dir.is_dir():
        logger.warning(f"提示词目录不存在: {prompts_dir}")
        return

    # 获取数据库中现有的提示词（包括内容，用于比对）
    result = await session.execute(select(Prompt))
    existing_prompts = {p.name: p for p in result.scalars().all()}

    updated_count = 0
    for prompt_file in sorted(prompts_dir.glob("*.md")):
        name = prompt_file.stem
        file_content = prompt_file.read_text(encoding="utf-8")

        if name in existing_prompts:
            # 已存在：检查内容是否需要更新
            existing = existing_prompts[name]
            if existing.content != file_content:
                existing.content = file_content
                updated_count += 1
                logger.info(f"提示词 '{name}' 已从文件同步更新")
        else:
            # 新提示词：插入
            session.add(Prompt(name=name, content=file_content))
            logger.info(f"提示词 '{name}' 已从文件加载")

    # 如果有更新，使全局缓存失效
    if updated_count > 0:
        await get_prompt_cache().invalidate()
        logger.info(f"已更新 {updated_count} 个提示词，缓存已失效")
