import logging
import os
import re
import secrets
from typing import Dict, Optional, Tuple

from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ..core.config import settings
from ..core.security import hash_password, verify_password
from ..models import (
    Prompt,
    User,
    CharacterPortrait,
    EmbeddingConfig,
    GeneratedImage,
    ImageGenerationConfig,
    LLMConfig,
    NovelConversation,
    NovelBlueprint,
    BlueprintCharacter,
    BlueprintRelationship,
    ChapterOutline,
    Chapter,
    ChapterMangaPrompt,
    ChapterVersion,
    ChapterEvaluation,
    CharacterStateIndex,
    ForeshadowingIndex,
    NovelProject,
    PartOutline,
    # Coding models
    CodingProject,
    CodingBlueprint,
    CodingSystem,
    CodingModule,
    CodingConversation,
    # Coding files models
    CodingDirectoryNode,
    CodingSourceFile,
    CodingFileVersion,
    CodingAgentState,
)
from .base import Base
from .session import AsyncSessionLocal, engine
from ..utils.prompt_include import resolve_prompt_includes

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

    # ---- 第二步：确保默认桌面用户存在并具备管理员权限 ----
    async with AsyncSessionLocal() as session:
        auth_enabled = bool(getattr(settings, "auth_enabled", False))
        normalized_env = (getattr(settings, "environment", "") or "").strip().lower()
        is_production = normalized_env in {"production", "prod"}
        bootstrap_password_env = (os.environ.get("AFN_INITIAL_ADMIN_PASSWORD") or "").strip()
        bootstrap_notice: str | None = None

        # 检查是否存在默认桌面用户
        desktop_user_result = await session.execute(
            select(User).where(User.username == "desktop_user")
        )
        desktop_user = desktop_user_result.scalars().first()
        if not desktop_user:
            logger.info("正在创建默认桌面用户 ...")
            if auth_enabled:
                if bootstrap_password_env:
                    initial_password = bootstrap_password_env
                elif is_production:
                    raise RuntimeError(
                        "已启用登录认证（AFN_AUTH_ENABLED=true），但未设置初始管理员密码。"
                        "请在 backend/.env 中配置 AFN_INITIAL_ADMIN_PASSWORD 后重启。"
                    )
                else:
                    initial_password = secrets.token_urlsafe(18)
                    bootstrap_notice = (
                        "[AuthBootstrap] 已生成初始管理员密码（仅显示一次）：\n"
                        f"  username=desktop_user\n"
                        f"  password={initial_password}\n"
                        "请立即登录后在「设置-账号」修改密码。"
                    )
            else:
                # 桌面版默认不走登录流程，密码主要用于占位；开启登录后会在启动阶段强制重置默认密码。
                initial_password = "desktop"

            desktop_user = User(
                username="desktop_user",
                hashed_password=hash_password(initial_password),
                is_admin=True,
            )

            session.add(desktop_user)
            try:
                await session.commit()
                logger.info("默认桌面用户创建完成：desktop_user")
                if bootstrap_notice:
                    # 首次创建管理员时立刻输出密码，避免后续初始化失败导致“密码丢失”。
                    print(bootstrap_notice, flush=True)
                    bootstrap_notice = None
            except IntegrityError:
                await session.rollback()
                logger.exception("默认桌面用户创建失败，可能是并发启动导致")
                desktop_user = None
        elif not bool(getattr(desktop_user, "is_admin", False)):
            desktop_user.is_admin = True
            logger.info("已将默认桌面用户提升为管理员：desktop_user")

        # ---- 登录模式安全收敛：禁止默认弱口令（desktop_user / desktop） ----
        if auth_enabled and desktop_user is not None:
            has_default_password = False
            try:
                has_default_password = verify_password("desktop", desktop_user.hashed_password)
            except Exception:
                has_default_password = False

            if has_default_password:
                # 若存在其他启用的管理员，则直接禁用默认用户，避免弱口令遗留。
                other_admin_result = await session.execute(
                    select(User.id)
                    .where(
                        User.is_admin.is_(True),
                        User.is_active.is_(True),
                        User.username != "desktop_user",
                    )
                    .limit(1)
                )
                other_admin_exists = other_admin_result.scalars().first() is not None

                if other_admin_exists:
                    desktop_user.is_active = False
                    logger.warning(
                        "检测到启用登录模式下仍存在默认弱口令账户 desktop_user / desktop；"
                        "由于已有其他管理员，已自动禁用 desktop_user。"
                        "如需保留该账号，请在管理后台重置其密码后再启用。"
                    )
                else:
                    # 无其他管理员时必须保证能登录：优先使用环境变量，否则生产环境拒绝启动，开发环境生成随机密码并提示。
                    desktop_user.is_active = True
                    if bootstrap_password_env:
                        desktop_user.hashed_password = hash_password(bootstrap_password_env)
                        logger.warning(
                            "检测到 desktop_user 仍使用默认弱口令，已按 AFN_INITIAL_ADMIN_PASSWORD 自动重置密码。"
                        )
                    elif is_production:
                        raise RuntimeError(
                            "已启用登录认证（AFN_AUTH_ENABLED=true），但检测到默认管理员 desktop_user 仍为默认弱口令。"
                            "请在 backend/.env 中配置 AFN_INITIAL_ADMIN_PASSWORD 后重启（用于重置默认密码）。"
                        )
                    else:
                        new_password = secrets.token_urlsafe(18)
                        desktop_user.hashed_password = hash_password(new_password)
                        bootstrap_notice = (
                            "[AuthBootstrap] 检测到默认弱口令，已自动重置初始管理员密码（仅显示一次）：\n"
                            f"  username=desktop_user\n"
                            f"  password={new_password}\n"
                            "请立即登录后在「设置-账号」修改密码。"
                        )
                        await session.commit()
                        print(bootstrap_notice, flush=True)
                        bootstrap_notice = None

            # 兜底：避免出现“启用登录但无启用管理员”的死锁状态
            active_admin_result = await session.execute(
                select(User.id)
                .where(User.is_admin.is_(True), User.is_active.is_(True))
                .limit(1)
            )
            has_active_admin = active_admin_result.scalars().first() is not None
            if not has_active_admin:
                desktop_user.is_admin = True
                desktop_user.is_active = True

                if bootstrap_password_env:
                    desktop_user.hashed_password = hash_password(bootstrap_password_env)
                    logger.warning(
                        "检测到当前无启用管理员账户，已将 desktop_user 恢复为管理员并按 AFN_INITIAL_ADMIN_PASSWORD 重置密码。"
                    )
                elif is_production:
                    raise RuntimeError(
                        "已启用登录认证（AFN_AUTH_ENABLED=true），但当前不存在启用的管理员账户。"
                        "请在 backend/.env 中配置 AFN_INITIAL_ADMIN_PASSWORD 后重启。"
                    )
                else:
                    new_password = secrets.token_urlsafe(18)
                    desktop_user.hashed_password = hash_password(new_password)
                    bootstrap_notice = (
                        "[AuthBootstrap] 检测到当前无启用管理员账户，已恢复 desktop_user 并生成新密码（仅显示一次）：\n"
                        f"  username=desktop_user\n"
                        f"  password={new_password}\n"
                        "请立即登录后在「设置-账号」修改密码。"
                    )
                    await session.commit()
                    print(bootstrap_notice, flush=True)
                    bootstrap_notice = None

        # 确保拿到 desktop_user 的 id（避免并发启动导致 commit 失败后对象无 id）
        if desktop_user is None or getattr(desktop_user, "id", None) is None:
            desktop_user_result = await session.execute(select(User).where(User.username == "desktop_user"))
            desktop_user = desktop_user_result.scalars().first()
        if not desktop_user or getattr(desktop_user, "id", None) is None:
            raise RuntimeError("默认桌面用户初始化失败，无法继续数据库迁移")

        # ---- 第二步半：多用户系统迁移（补齐 user_id 并回填历史数据） ----
        await _ensure_user_scoped_user_id_columns(session, int(desktop_user.id))

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

    支持两种目录结构：
    1. 新结构：使用_registry.yaml注册表，按分类目录组织
    2. 旧结构：所有.md文件平铺在prompts根目录（向后兼容）

    策略：
    - 新提示词：插入数据库（包含元数据）
    - 已存在且未修改的提示词：如果文件内容不同，更新数据库
    - 已存在且已修改的提示词：只更新元数据（title、description、tags），保留用户修改的content
    """
    from ..services.prompt_service import get_prompt_cache, get_prompt_registry

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

    # 尝试使用注册表
    registry = get_prompt_registry(prompts_dir)
    if registry.is_registry_available():
        # 新结构：遍历注册表中的所有提示词
        for name in registry.get_all_names():
            registry_path = registry.get_path(name)
            if not registry_path:
                continue

            prompt_file = prompts_dir / registry_path
            if not prompt_file.is_file():
                logger.warning(f"注册表中的提示词文件不存在: {registry_path}")
                continue

            file_content = prompt_file.read_text(encoding="utf-8")
            metadata, body_content = _parse_yaml_frontmatter(file_content)
            body_content = resolve_prompt_includes(
                body_content,
                current_file=prompt_file,
                prompts_dir=prompts_dir,
            )

            # 从注册表补充元数据
            reg_meta = registry.get_meta(name)
            if reg_meta:
                if not metadata["title"]:
                    metadata["title"] = reg_meta.get("title")
                if not metadata["description"]:
                    metadata["description"] = reg_meta.get("description")

            updated_count += await _sync_single_prompt(
                session, name, metadata, body_content, existing_prompts
            )
    else:
        # 旧结构：遍历子目录和根目录
        # 先遍历子目录
        for subdir in prompts_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('_'):
                for prompt_file in sorted(subdir.glob("*.md")):
                    name = prompt_file.stem
                    file_content = prompt_file.read_text(encoding="utf-8")
                    metadata, body_content = _parse_yaml_frontmatter(file_content)
                    body_content = resolve_prompt_includes(
                        body_content,
                        current_file=prompt_file,
                        prompts_dir=prompts_dir,
                    )
                    updated_count += await _sync_single_prompt(
                        session, name, metadata, body_content, existing_prompts
                    )

        # 再遍历根目录（兼容旧的平铺结构）
        for prompt_file in sorted(prompts_dir.glob("*.md")):
            name = prompt_file.stem
            file_content = prompt_file.read_text(encoding="utf-8")
            metadata, body_content = _parse_yaml_frontmatter(file_content)
            body_content = resolve_prompt_includes(
                body_content,
                current_file=prompt_file,
                prompts_dir=prompts_dir,
            )
            updated_count += await _sync_single_prompt(
                session, name, metadata, body_content, existing_prompts
            )

    # 如果有更新，使全局缓存失效
    if updated_count > 0:
        await get_prompt_cache().invalidate()
        logger.info(f"已更新 {updated_count} 个提示词，缓存已失效")


async def _sync_single_prompt(
    session: AsyncSession,
    name: str,
    metadata: Dict[str, Optional[str]],
    body_content: str,
    existing_prompts: Dict[str, Prompt]
) -> int:
    """
    同步单个提示词到数据库

    Returns:
        1 如果有更新，0 如果无变化
    """
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

        return 1 if needs_update else 0
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
        return 1


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
        (
            "users",
            "is_admin",
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"
        ),
        # 角色立绘：次要角色和自动生成标记
        (
            "character_portraits",
            "is_secondary",
            "ALTER TABLE character_portraits ADD COLUMN is_secondary BOOLEAN NOT NULL DEFAULT 0"
        ),
        (
            "character_portraits",
            "auto_generated",
            "ALTER TABLE character_portraits ADD COLUMN auto_generated BOOLEAN NOT NULL DEFAULT 0"
        ),
        # 漫画分镜：分析数据（角色、事件、场景、情绪曲线、页面规划等）
        (
            "chapter_manga_prompts",
            "analysis_data",
            "ALTER TABLE chapter_manga_prompts ADD COLUMN analysis_data JSON DEFAULT NULL"
        ),
        # 图片类型：区分单画格(panel)和整页漫画(page)
        (
            "generated_images",
            "image_type",
            "ALTER TABLE generated_images ADD COLUMN image_type VARCHAR(20) DEFAULT 'panel' NOT NULL"
        ),
        # 整页提示词列表：存储整页漫画生成所需的提示词
        (
            "chapter_manga_prompts",
            "page_prompts",
            "ALTER TABLE chapter_manga_prompts ADD COLUMN page_prompts JSON DEFAULT '[]'"
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


async def _ensure_user_scoped_user_id_columns(session: AsyncSession, desktop_user_id: int) -> None:
    """补齐多用户系统所需的 user_id 列，并为历史数据回填默认用户。

    背景：
    - 旧版本的 SQLite DB 中通常没有 user_id 字段；
    - SQLAlchemy 的 create_all 不会修改已有表结构，导致上线后插入/查询报错；
    - 这里采用“最小可用迁移”：添加列（如缺失）+ 回填已有行 user_id + 创建索引。
    """
    try:
        backend_name = make_url(settings.sqlalchemy_database_uri).get_backend_name()
    except Exception:
        backend_name = "sqlite"

    targets: list[tuple[str, str]] = [
        ("novel_projects", "user_id"),
        ("coding_projects", "user_id"),
        ("llm_configs", "user_id"),
        ("embedding_configs", "user_id"),
        ("image_generation_configs", "user_id"),
        ("theme_configs", "user_id"),
    ]

    async def sqlite_table_columns(table_name: str) -> list[str]:
        result = await session.execute(text(f"PRAGMA table_info({table_name})"))
        rows = result.fetchall()
        if not rows:
            return []
        return [row[1] for row in rows]

    async def mysql_table_exists(table_name: str) -> bool:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name"
            ),
            {"table_name": table_name},
        )
        return int(result.scalar() or 0) > 0

    async def mysql_column_exists(table_name: str, column_name: str) -> bool:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name AND COLUMN_NAME = :column_name"
            ),
            {"table_name": table_name, "column_name": column_name},
        )
        return int(result.scalar() or 0) > 0

    async def mysql_index_exists(table_name: str, index_name: str) -> bool:
        result = await session.execute(
            text(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name AND INDEX_NAME = :index_name"
            ),
            {"table_name": table_name, "index_name": index_name},
        )
        return int(result.scalar() or 0) > 0

    for table_name, column_name in targets:
        try:
            if backend_name == "sqlite":
                columns = await sqlite_table_columns(table_name)
                if not columns:
                    continue

                if column_name not in columns:
                    await session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER"))
                    logger.info("数据库迁移: 已添加列 %s.%s（多用户隔离）", table_name, column_name)

                await session.execute(
                    text(
                        f"UPDATE {table_name} "
                        f"SET {column_name} = :user_id "
                        f"WHERE {column_name} IS NULL OR {column_name} = 0"
                    ),
                    {"user_id": desktop_user_id},
                )

                index_name = f"ix_{table_name}_{column_name}"
                await session.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"))
            else:
                if not await mysql_table_exists(table_name):
                    continue

                if not await mysql_column_exists(table_name, column_name):
                    await session.execute(text(f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` INT NULL"))
                    logger.info("数据库迁移: 已添加列 %s.%s（多用户隔离）", table_name, column_name)

                await session.execute(
                    text(
                        f"UPDATE `{table_name}` "
                        f"SET `{column_name}` = :user_id "
                        f"WHERE `{column_name}` IS NULL OR `{column_name}` = 0"
                    ),
                    {"user_id": desktop_user_id},
                )

                index_name = f"ix_{table_name}_{column_name}"
                if not await mysql_index_exists(table_name, index_name):
                    await session.execute(text(f"CREATE INDEX `{index_name}` ON `{table_name}` (`{column_name}`)"))
        except Exception as exc:
            logger.warning("多用户隔离迁移跳过 %s.%s: %s", table_name, column_name, exc)
