"""管理员仪表盘路由。"""

from __future__ import annotations

from datetime import date as date_cls, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import require_admin_user
from ...db.session import get_session
from ...models.coding import CodingProject
from ...models.embedding_config import EmbeddingConfig
from ...models.image_config import ImageGenerationConfig
from ...models.llm_config import LLMConfig
from ...models.novel import NovelProject
from ...models.theme_config import ThemeConfig
from ...models.user import User
from ...schemas.user import UserInDB
from .admin_utils import collect_count_map, collect_latest_map, normalize_datetime

router = APIRouter(prefix="/api/admin/dashboard", tags=["Admin Dashboard"])


class AdminStatusCount(BaseModel):
    """状态统计项。"""

    status: str
    count: int


class AdminOverviewSummary(BaseModel):
    """管理总览核心统计。"""

    total_users: int = 0
    active_users: int = 0
    recently_active_users: int = 0
    total_novel_projects: int = 0
    total_coding_projects: int = 0
    total_projects: int = 0
    total_llm_configs: int = 0
    total_embedding_configs: int = 0
    total_image_configs: int = 0
    total_theme_configs: int = 0


class AdminOverviewResponse(BaseModel):
    """管理员总览响应。"""

    summary: AdminOverviewSummary
    novel_status_distribution: list[AdminStatusCount]
    coding_status_distribution: list[AdminStatusCount]
    generated_at: datetime


class AdminProjectSummary(BaseModel):
    """项目总览统计。"""

    total_novel_projects: int = 0
    total_coding_projects: int = 0
    total_projects: int = 0


class AdminRecentProjectItem(BaseModel):
    """最近项目记录。"""

    kind: str
    project_id: str
    title: str
    status: str
    user_id: int
    username: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminTopProjectUser(BaseModel):
    """项目最多用户排行项。"""

    user_id: int
    username: str
    novel_projects: int = 0
    coding_projects: int = 0
    total_projects: int = 0
    last_project_updated_at: datetime | None = None


class AdminProjectsResponse(BaseModel):
    """项目页响应。"""

    summary: AdminProjectSummary
    recent_projects: list[AdminRecentProjectItem]
    top_users: list[AdminTopProjectUser]
    novel_status_distribution: list[AdminStatusCount]
    coding_status_distribution: list[AdminStatusCount]
    generated_at: datetime


class AdminConfigTypeSummary(BaseModel):
    """单类配置统计。"""

    config_type: str
    total: int = 0
    active: int = 0


class AdminConfigsSummary(BaseModel):
    """配置页汇总统计。"""

    total_configs: int = 0
    total_active_configs: int = 0
    by_type: list[AdminConfigTypeSummary]


class AdminTopConfigUser(BaseModel):
    """配置最多用户排行项。"""

    user_id: int
    username: str
    llm_configs: int = 0
    embedding_configs: int = 0
    image_configs: int = 0
    theme_configs: int = 0
    total_configs: int = 0


class AdminActiveConfigItem(BaseModel):
    """当前激活配置记录。"""

    config_type: str
    config_id: int
    config_name: str
    user_id: int
    username: str
    updated_at: datetime | None = None
    test_status: str | None = None


class AdminConfigTestStatusCount(BaseModel):
    """配置测试状态聚合项。"""

    status: str
    count: int


class AdminConfigsResponse(BaseModel):
    """配置页响应。"""

    summary: AdminConfigsSummary
    top_users: list[AdminTopConfigUser]
    active_configs: list[AdminActiveConfigItem]
    test_status_distribution: list[AdminConfigTestStatusCount]
    generated_at: datetime


class AdminTrendPoint(BaseModel):
    """趋势数据点。"""

    date: str
    value: int


class AdminTrendSeries(BaseModel):
    """趋势序列。"""

    key: str
    label: str
    points: list[AdminTrendPoint]


class AdminDashboardTrendsResponse(BaseModel):
    """管理员趋势响应。"""

    days: int
    series: list[AdminTrendSeries]
    generated_at: datetime


def _normalize_test_status(value: str | None) -> str:
    """统一测试状态，兼容空值。"""
    normalized = str(value or "").strip().lower()
    if normalized in {"success", "failed", "pending"}:
        return normalized
    return "untested"


def _normalize_date_bucket(value: object) -> str | None:
    """统一日期分组值，兼容多数据库返回类型。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date_cls):
        return value.isoformat()

    text = str(value).strip()
    if not text:
        return None
    return text[:10]


def _build_day_labels(days: int, now_utc: datetime) -> list[str]:
    """生成最近 N 天（含今天）的日期标签。"""
    today = now_utc.date()
    start_day = today - timedelta(days=days - 1)
    return [
        (start_day + timedelta(days=offset)).isoformat()
        for offset in range(days)
    ]


async def _count_table(session: AsyncSession, model: type) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar() or 0)


async def _count_active_table(session: AsyncSession, model: type) -> int:
    is_active_col = getattr(model, "is_active", None)
    if is_active_col is None:
        return 0
    result = await session.execute(select(func.count()).select_from(model).where(is_active_col.is_(True)))
    return int(result.scalar() or 0)


async def _collect_status_distribution(session: AsyncSession, model: type) -> list[AdminStatusCount]:
    status_col = getattr(model, "status", None)
    if status_col is None:
        return []

    result = await session.execute(
        select(status_col, func.count()).group_by(status_col)
    )

    rows = [
        AdminStatusCount(status=str(status_value or "UNKNOWN"), count=int(count_value or 0))
        for status_value, count_value in result.all()
    ]
    rows.sort(key=lambda item: item.count, reverse=True)
    return rows


async def _collect_test_status_map(session: AsyncSession, model: type) -> dict[str, int]:
    status_col = getattr(model, "test_status", None)
    id_col = getattr(model, "id", None)
    if status_col is None or id_col is None:
        return {}

    result = await session.execute(select(status_col, func.count(id_col)).group_by(status_col))

    data: dict[str, int] = {}
    for raw_status, count_value in result.all():
        status_key = _normalize_test_status(raw_status)
        data[status_key] = data.get(status_key, 0) + int(count_value or 0)
    return data


async def _collect_daily_count_map(
    session: AsyncSession,
    model: type,
    dt_field: str,
    start_at: datetime,
    valid_days: set[str],
) -> dict[str, int]:
    """按天聚合计数。"""
    dt_col = getattr(model, dt_field, None)
    if dt_col is None:
        return {}

    day_col = func.date(dt_col)
    result = await session.execute(
        select(day_col, func.count())
        .where(dt_col >= start_at)
        .group_by(day_col)
        .order_by(day_col)
    )

    data: dict[str, int] = {}
    for day_value, count_value in result.all():
        day_key = _normalize_date_bucket(day_value)
        if day_key is None or day_key not in valid_days:
            continue
        data[day_key] = int(count_value or 0)
    return data


@router.get("/overview", response_model=AdminOverviewResponse)
async def get_overview(
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminOverviewResponse:
    """获取管理员总览数据。"""
    total_users = await _count_table(session, User)

    active_users_result = await session.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    active_users = int(active_users_result.scalar() or 0)

    total_novel_projects = await _count_table(session, NovelProject)
    total_coding_projects = await _count_table(session, CodingProject)
    total_llm_configs = await _count_table(session, LLMConfig)
    total_embedding_configs = await _count_table(session, EmbeddingConfig)
    total_image_configs = await _count_table(session, ImageGenerationConfig)
    total_theme_configs = await _count_table(session, ThemeConfig)

    user_latest_result = await session.execute(
        select(User.id, User.updated_at)
    )
    user_latest_map = {
        int(user_id): normalize_datetime(updated_at)
        for user_id, updated_at in user_latest_result.all()
        if user_id is not None
    }

    novel_latest = await collect_latest_map(session, NovelProject)
    coding_latest = await collect_latest_map(session, CodingProject)
    llm_latest = await collect_latest_map(session, LLMConfig)
    embedding_latest = await collect_latest_map(session, EmbeddingConfig)
    image_latest = await collect_latest_map(session, ImageGenerationConfig)
    theme_latest = await collect_latest_map(session, ThemeConfig)

    now_utc = datetime.now(timezone.utc)
    recent_threshold = now_utc - timedelta(days=7)

    recently_active_users = 0
    for user_id in user_latest_map.keys():
        candidates = [
            user_latest_map.get(user_id),
            novel_latest.get(user_id),
            coding_latest.get(user_id),
            llm_latest.get(user_id),
            embedding_latest.get(user_id),
            image_latest.get(user_id),
            theme_latest.get(user_id),
        ]
        valid_candidates = [dt for dt in candidates if dt is not None]
        if not valid_candidates:
            continue
        if max(valid_candidates) >= recent_threshold:
            recently_active_users += 1

    summary = AdminOverviewSummary(
        total_users=total_users,
        active_users=active_users,
        recently_active_users=recently_active_users,
        total_novel_projects=total_novel_projects,
        total_coding_projects=total_coding_projects,
        total_projects=total_novel_projects + total_coding_projects,
        total_llm_configs=total_llm_configs,
        total_embedding_configs=total_embedding_configs,
        total_image_configs=total_image_configs,
        total_theme_configs=total_theme_configs,
    )

    return AdminOverviewResponse(
        summary=summary,
        novel_status_distribution=await _collect_status_distribution(session, NovelProject),
        coding_status_distribution=await _collect_status_distribution(session, CodingProject),
        generated_at=now_utc,
    )


@router.get("/trends", response_model=AdminDashboardTrendsResponse)
async def get_trends(
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
    days: int = Query(default=21, ge=7, le=90),
) -> AdminDashboardTrendsResponse:
    """获取管理员趋势数据。"""
    now_utc = datetime.now(timezone.utc)
    labels = _build_day_labels(days, now_utc)
    valid_days = set(labels)

    start_day = date_cls.fromisoformat(labels[0])
    start_at = datetime.combine(start_day, datetime.min.time(), tzinfo=timezone.utc)

    user_new_map = await _collect_daily_count_map(session, User, "created_at", start_at, valid_days)
    novel_new_map = await _collect_daily_count_map(session, NovelProject, "created_at", start_at, valid_days)
    coding_new_map = await _collect_daily_count_map(session, CodingProject, "created_at", start_at, valid_days)
    llm_new_map = await _collect_daily_count_map(session, LLMConfig, "created_at", start_at, valid_days)
    embedding_new_map = await _collect_daily_count_map(session, EmbeddingConfig, "created_at", start_at, valid_days)
    image_new_map = await _collect_daily_count_map(session, ImageGenerationConfig, "created_at", start_at, valid_days)
    theme_new_map = await _collect_daily_count_map(session, ThemeConfig, "created_at", start_at, valid_days)

    def _merge_day_maps(*maps: dict[str, int]) -> dict[str, int]:
        merged = {day: 0 for day in labels}
        for data_map in maps:
            for day, count_value in data_map.items():
                if day not in merged:
                    continue
                merged[day] += int(count_value or 0)
        return merged

    def _build_series(key: str, label: str, data_map: dict[str, int]) -> AdminTrendSeries:
        return AdminTrendSeries(
            key=key,
            label=label,
            points=[
                AdminTrendPoint(date=day, value=int(data_map.get(day, 0)))
                for day in labels
            ],
        )

    total_project_map = _merge_day_maps(novel_new_map, coding_new_map)
    total_config_map = _merge_day_maps(llm_new_map, embedding_new_map, image_new_map, theme_new_map)

    series = [
        _build_series("new_users", "新用户", user_new_map),
        _build_series("new_novel_projects", "新建小说项目", novel_new_map),
        _build_series("new_coding_projects", "新建Prompt项目", coding_new_map),
        _build_series("new_projects", "新建项目总量", total_project_map),
        _build_series("new_llm_configs", "新建LLM配置", llm_new_map),
        _build_series("new_embedding_configs", "新建嵌入配置", embedding_new_map),
        _build_series("new_image_configs", "新建图片配置", image_new_map),
        _build_series("new_theme_configs", "新建主题配置", theme_new_map),
        _build_series("new_configs", "新建配置总量", total_config_map),
    ]

    return AdminDashboardTrendsResponse(
        days=days,
        series=series,
        generated_at=now_utc,
    )


@router.get("/projects", response_model=AdminProjectsResponse)
async def get_projects(
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=40, ge=10, le=200),
) -> AdminProjectsResponse:
    """获取项目页数据。"""
    novel_total = await _count_table(session, NovelProject)
    coding_total = await _count_table(session, CodingProject)

    novel_rows = await session.execute(
        select(
            NovelProject.id,
            NovelProject.title,
            NovelProject.status,
            NovelProject.user_id,
            User.username,
            NovelProject.created_at,
            NovelProject.updated_at,
        )
        .join(User, User.id == NovelProject.user_id)
        .order_by(NovelProject.updated_at.desc())
        .limit(limit)
    )

    coding_rows = await session.execute(
        select(
            CodingProject.id,
            CodingProject.title,
            CodingProject.status,
            CodingProject.user_id,
            User.username,
            CodingProject.created_at,
            CodingProject.updated_at,
        )
        .join(User, User.id == CodingProject.user_id)
        .order_by(CodingProject.updated_at.desc())
        .limit(limit)
    )

    combined: list[AdminRecentProjectItem] = []

    for project_id, title, status_value, user_id, username, created_at, updated_at in novel_rows.all():
        combined.append(
            AdminRecentProjectItem(
                kind="novel",
                project_id=str(project_id),
                title=str(title or "未命名小说"),
                status=str(status_value or "UNKNOWN"),
                user_id=int(user_id),
                username=str(username or f"user_{user_id}"),
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    for project_id, title, status_value, user_id, username, created_at, updated_at in coding_rows.all():
        combined.append(
            AdminRecentProjectItem(
                kind="coding",
                project_id=str(project_id),
                title=str(title or "未命名项目"),
                status=str(status_value or "UNKNOWN"),
                user_id=int(user_id),
                username=str(username or f"user_{user_id}"),
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    combined.sort(
        key=lambda item: (
            normalize_datetime(item.updated_at) or normalize_datetime(item.created_at) or datetime.min.replace(tzinfo=timezone.utc)
        ),
        reverse=True,
    )

    user_lookup_result = await session.execute(select(User.id, User.username))
    user_lookup = {
        int(user_id): str(username or f"user_{user_id}")
        for user_id, username in user_lookup_result.all()
        if user_id is not None
    }

    novel_counts = await collect_count_map(session, NovelProject)
    coding_counts = await collect_count_map(session, CodingProject)
    novel_latest = await collect_latest_map(session, NovelProject)
    coding_latest = await collect_latest_map(session, CodingProject)

    top_users: list[AdminTopProjectUser] = []
    for user_id, username in user_lookup.items():
        novel_projects = int(novel_counts.get(user_id, 0))
        coding_projects = int(coding_counts.get(user_id, 0))
        total_projects = novel_projects + coding_projects
        if total_projects <= 0:
            continue

        last_candidates = [novel_latest.get(user_id), coding_latest.get(user_id)]
        valid_candidates = [dt for dt in last_candidates if dt is not None]
        last_updated = max(valid_candidates) if valid_candidates else None

        top_users.append(
            AdminTopProjectUser(
                user_id=user_id,
                username=username,
                novel_projects=novel_projects,
                coding_projects=coding_projects,
                total_projects=total_projects,
                last_project_updated_at=last_updated,
            )
        )

    top_users.sort(
        key=lambda item: (
            item.total_projects,
            normalize_datetime(item.last_project_updated_at) or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )

    return AdminProjectsResponse(
        summary=AdminProjectSummary(
            total_novel_projects=novel_total,
            total_coding_projects=coding_total,
            total_projects=novel_total + coding_total,
        ),
        recent_projects=combined[:limit],
        top_users=top_users[:20],
        novel_status_distribution=await _collect_status_distribution(session, NovelProject),
        coding_status_distribution=await _collect_status_distribution(session, CodingProject),
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/configs", response_model=AdminConfigsResponse)
async def get_configs(
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=20, le=400),
) -> AdminConfigsResponse:
    """获取配置页数据。"""
    llm_total = await _count_table(session, LLMConfig)
    embedding_total = await _count_table(session, EmbeddingConfig)
    image_total = await _count_table(session, ImageGenerationConfig)
    theme_total = await _count_table(session, ThemeConfig)

    llm_active = await _count_active_table(session, LLMConfig)
    embedding_active = await _count_active_table(session, EmbeddingConfig)
    image_active = await _count_active_table(session, ImageGenerationConfig)
    theme_active = await _count_active_table(session, ThemeConfig)

    llm_counts = await collect_count_map(session, LLMConfig)
    embedding_counts = await collect_count_map(session, EmbeddingConfig)
    image_counts = await collect_count_map(session, ImageGenerationConfig)
    theme_counts = await collect_count_map(session, ThemeConfig)

    user_lookup_result = await session.execute(select(User.id, User.username))
    user_lookup = {
        int(user_id): str(username or f"user_{user_id}")
        for user_id, username in user_lookup_result.all()
        if user_id is not None
    }

    top_users: list[AdminTopConfigUser] = []
    for user_id, username in user_lookup.items():
        llm_count = int(llm_counts.get(user_id, 0))
        embedding_count = int(embedding_counts.get(user_id, 0))
        image_count = int(image_counts.get(user_id, 0))
        theme_count = int(theme_counts.get(user_id, 0))
        total_count = llm_count + embedding_count + image_count + theme_count

        if total_count <= 0:
            continue

        top_users.append(
            AdminTopConfigUser(
                user_id=user_id,
                username=username,
                llm_configs=llm_count,
                embedding_configs=embedding_count,
                image_configs=image_count,
                theme_configs=theme_count,
                total_configs=total_count,
            )
        )

    top_users.sort(key=lambda item: item.total_configs, reverse=True)

    active_items: list[AdminActiveConfigItem] = []

    llm_rows = await session.execute(
        select(
            LLMConfig.id,
            LLMConfig.config_name,
            LLMConfig.user_id,
            User.username,
            LLMConfig.updated_at,
            LLMConfig.test_status,
        )
        .join(User, User.id == LLMConfig.user_id)
        .where(LLMConfig.is_active.is_(True))
        .order_by(LLMConfig.updated_at.desc())
        .limit(limit)
    )

    for config_id, config_name, user_id, username, updated_at, test_status in llm_rows.all():
        active_items.append(
            AdminActiveConfigItem(
                config_type="llm",
                config_id=int(config_id),
                config_name=str(config_name or "默认配置"),
                user_id=int(user_id),
                username=str(username or f"user_{user_id}"),
                updated_at=updated_at,
                test_status=test_status,
            )
        )

    embedding_rows = await session.execute(
        select(
            EmbeddingConfig.id,
            EmbeddingConfig.config_name,
            EmbeddingConfig.user_id,
            User.username,
            EmbeddingConfig.updated_at,
            EmbeddingConfig.test_status,
        )
        .join(User, User.id == EmbeddingConfig.user_id)
        .where(EmbeddingConfig.is_active.is_(True))
        .order_by(EmbeddingConfig.updated_at.desc())
        .limit(limit)
    )

    for config_id, config_name, user_id, username, updated_at, test_status in embedding_rows.all():
        active_items.append(
            AdminActiveConfigItem(
                config_type="embedding",
                config_id=int(config_id),
                config_name=str(config_name or "默认配置"),
                user_id=int(user_id),
                username=str(username or f"user_{user_id}"),
                updated_at=updated_at,
                test_status=test_status,
            )
        )

    image_rows = await session.execute(
        select(
            ImageGenerationConfig.id,
            ImageGenerationConfig.config_name,
            ImageGenerationConfig.user_id,
            User.username,
            ImageGenerationConfig.updated_at,
            ImageGenerationConfig.test_status,
        )
        .join(User, User.id == ImageGenerationConfig.user_id)
        .where(ImageGenerationConfig.is_active.is_(True))
        .order_by(ImageGenerationConfig.updated_at.desc())
        .limit(limit)
    )

    for config_id, config_name, user_id, username, updated_at, test_status in image_rows.all():
        active_items.append(
            AdminActiveConfigItem(
                config_type="image",
                config_id=int(config_id),
                config_name=str(config_name or "默认配置"),
                user_id=int(user_id),
                username=str(username or f"user_{user_id}"),
                updated_at=updated_at,
                test_status=test_status,
            )
        )

    theme_rows = await session.execute(
        select(
            ThemeConfig.id,
            ThemeConfig.config_name,
            ThemeConfig.user_id,
            User.username,
            ThemeConfig.updated_at,
        )
        .join(User, User.id == ThemeConfig.user_id)
        .where(ThemeConfig.is_active.is_(True))
        .order_by(ThemeConfig.updated_at.desc())
        .limit(limit)
    )

    for config_id, config_name, user_id, username, updated_at in theme_rows.all():
        active_items.append(
            AdminActiveConfigItem(
                config_type="theme",
                config_id=int(config_id),
                config_name=str(config_name or "默认主题"),
                user_id=int(user_id),
                username=str(username or f"user_{user_id}"),
                updated_at=updated_at,
                test_status=None,
            )
        )

    active_items.sort(
        key=lambda item: normalize_datetime(item.updated_at) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    by_type = [
        AdminConfigTypeSummary(config_type="llm", total=llm_total, active=llm_active),
        AdminConfigTypeSummary(config_type="embedding", total=embedding_total, active=embedding_active),
        AdminConfigTypeSummary(config_type="image", total=image_total, active=image_active),
        AdminConfigTypeSummary(config_type="theme", total=theme_total, active=theme_active),
    ]

    summary = AdminConfigsSummary(
        total_configs=llm_total + embedding_total + image_total + theme_total,
        total_active_configs=llm_active + embedding_active + image_active + theme_active,
        by_type=by_type,
    )

    llm_status_map = await _collect_test_status_map(session, LLMConfig)
    embedding_status_map = await _collect_test_status_map(session, EmbeddingConfig)
    image_status_map = await _collect_test_status_map(session, ImageGenerationConfig)

    test_status_distribution: list[AdminConfigTestStatusCount] = []
    for status_key in ("success", "failed", "pending", "untested"):
        total_count = int(llm_status_map.get(status_key, 0))
        total_count += int(embedding_status_map.get(status_key, 0))
        total_count += int(image_status_map.get(status_key, 0))
        test_status_distribution.append(
            AdminConfigTestStatusCount(status=status_key, count=total_count)
        )

    return AdminConfigsResponse(
        summary=summary,
        top_users=top_users[:20],
        active_configs=active_items[:limit],
        test_status_distribution=test_status_distribution,
        generated_at=datetime.now(timezone.utc),
    )
