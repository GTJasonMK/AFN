import logging
import os
import re
from typing import Dict, Optional, Tuple

from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..core.config import settings
from ..core.security import hash_password
from ..models import Prompt, User
from .base import Base
from .session import AsyncSessionLocal, engine

logger = logging.getLogger(__name__)


def _parse_yaml_frontmatter(content: str) -> Tuple[Dict[str, Optional[str]], str]:
    """
    解析Markdown文件的YAML前置元数据。

    Args:
        content: 完整的文件内容

    Returns:
        (metadata, body) 元组，metadata包含title、description、tags
    """
    metadata: Dict[str, Optional[str]] = {
        "title": None,
        "description": None,
        "tags": None,
    }

    # 匹配 YAML 前置元数据块
    # 格式：---\n...\n---
    frontmatter_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
    match = frontmatter_pattern.match(content)

    if not match:
        # 没有前置元数据，返回原始内容
        return metadata, content

    yaml_block = match.group(1)
    body = content[match.end():]

    # 简单解析YAML（不引入pyyaml依赖）
    for line in yaml_block.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 解析 key: value 格式
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            # 移除引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            if key in metadata:
                metadata[key] = value if value else None

    return metadata, body


async def init_db() -> None:
    """初始化数据库结构并确保默认桌面用户存在（PyQt版）。"""

    await _ensure_database_exists()

    # ---- 第一步：创建所有表结构 ----
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表结构已初始化")

    # ---- 第一步半：执行数据库迁移（添加缺失的列） ----
    await _run_migrations()

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
    - 新提示词：插入数据库（包含元数据）
    - 已存在且未修改的提示词：如果文件内容不同，更新数据库
    - 已存在且已修改的提示词：只更新元数据（title、description、tags），保留用户修改的content
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

        # 解析YAML前置元数据
        metadata, body_content = _parse_yaml_frontmatter(file_content)

        if name in existing_prompts:
            # 已存在：检查是否需要更新
            existing = existing_prompts[name]
            needs_update = False

            # 更新元数据（无论用户是否修改过content）
            if existing.title != metadata["title"]:
                existing.title = metadata["title"]
                needs_update = True
            if existing.description != metadata["description"]:
                existing.description = metadata["description"]
                needs_update = True
            if existing.tags != metadata["tags"]:
                existing.tags = metadata["tags"]
                needs_update = True

            # 只有用户未修改时才更新content
            if not existing.is_modified and existing.content != body_content:
                existing.content = body_content
                needs_update = True
                logger.info(f"提示词 '{name}' 内容已从文件同步更新")

            if needs_update:
                updated_count += 1
        else:
            # 新提示词：插入（包含元数据）
            session.add(Prompt(
                name=name,
                title=metadata["title"],
                description=metadata["description"],
                tags=metadata["tags"],
                content=body_content,
                is_modified=False,
            ))
            logger.info(f"提示词 '{name}' 已从文件加载")

    # 如果有更新，使全局缓存失效
    if updated_count > 0:
        await get_prompt_cache().invalidate()
        logger.info(f"已更新 {updated_count} 个提示词，缓存已失效")


async def _run_migrations() -> None:
    """
    执行数据库迁移，添加缺失的列。

    对于SQLite，使用ALTER TABLE ADD COLUMN来添加新列。
    如果列已存在，会捕获异常并跳过。
    """
    migrations = [
        # 格式: (表名, 列名, 列定义SQL)
        (
            "chapter_manga_prompts",
            "source_version_id",
            "ALTER TABLE chapter_manga_prompts ADD COLUMN source_version_id INTEGER REFERENCES chapter_versions(id) ON DELETE SET NULL"
        ),
        (
            "generated_images",
            "chapter_version_id",
            "ALTER TABLE generated_images ADD COLUMN chapter_version_id VARCHAR(36) REFERENCES chapter_versions(id) ON DELETE SET NULL"
        ),
        # 断点续传支持：添加生成状态和进度字段
        (
            "chapter_manga_prompts",
            "generation_status",
            "ALTER TABLE chapter_manga_prompts ADD COLUMN generation_status VARCHAR(32) DEFAULT 'completed'"
        ),
        (
            "chapter_manga_prompts",
            "generation_progress",
            "ALTER TABLE chapter_manga_prompts ADD COLUMN generation_progress JSON DEFAULT NULL"
        ),
        # 画格ID：精确匹配图片属于哪个画格
        (
            "generated_images",
            "panel_id",
            "ALTER TABLE generated_images ADD COLUMN panel_id VARCHAR(100)"
        ),
        # 提示词管理：添加description和is_modified字段
        (
            "prompts",
            "description",
            "ALTER TABLE prompts ADD COLUMN description TEXT"
        ),
        (
            "prompts",
            "is_modified",
            "ALTER TABLE prompts ADD COLUMN is_modified BOOLEAN DEFAULT 0"
        ),
    ]

    async with engine.begin() as conn:
        for table_name, column_name, alter_sql in migrations:
            try:
                # 检查列是否已存在（SQLite特有方式）
                result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in result.fetchall()]

                if column_name not in columns:
                    await conn.execute(text(alter_sql))
                    logger.info(f"数据库迁移: 已添加列 {table_name}.{column_name}")
                else:
                    logger.debug(f"数据库迁移: 列 {table_name}.{column_name} 已存在，跳过")

            except OperationalError as e:
                # 表可能不存在（首次运行），或其他问题
                logger.debug(f"数据库迁移跳过 {table_name}.{column_name}: {e}")
