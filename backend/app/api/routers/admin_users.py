"""管理员用户管理与监控路由。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.dependencies import require_admin_user
from ...core.security import hash_password
from ...db.session import get_session
from ...models.coding import CodingProject
from ...models.embedding_config import EmbeddingConfig
from ...models.image_config import ImageGenerationConfig
from ...models.llm_config import LLMConfig
from ...models.novel import NovelProject
from ...models.theme_config import ThemeConfig
from ...models.user import User
from ...repositories.user_repository import UserRepository
from ...schemas.user import UserInDB
from .admin_utils import collect_count_map, collect_latest_map, normalize_datetime

router = APIRouter(prefix="/api/admin/users", tags=["Admin Users"])
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


class AdminUserItem(BaseModel):
    """管理员视角的用户信息。"""

    id: int
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminUsersListResponse(BaseModel):
    """用户列表响应。"""

    users: list[AdminUserItem]


class AdminUserMetrics(BaseModel):
    """用户监控指标。"""

    novel_projects: int = 0
    coding_projects: int = 0
    total_projects: int = 0
    llm_configs: int = 0
    embedding_configs: int = 0
    image_configs: int = 0
    theme_configs: int = 0
    last_activity_at: datetime | None = None
    recently_active: bool = False


class AdminUserMonitorItem(AdminUserItem):
    """带监控指标的用户信息。"""

    metrics: AdminUserMetrics


class AdminUsersMonitorSummary(BaseModel):
    """管理员监控总览。"""

    total_users: int = 0
    active_users: int = 0
    inactive_users: int = 0
    admin_users: int = 0
    recently_active_users: int = 0
    total_novel_projects: int = 0
    total_coding_projects: int = 0
    total_projects: int = 0
    total_llm_configs: int = 0
    total_embedding_configs: int = 0
    total_image_configs: int = 0
    total_theme_configs: int = 0


class AdminUsersMonitorResponse(BaseModel):
    """用户监控面板响应。"""

    summary: AdminUsersMonitorSummary
    users: list[AdminUserMonitorItem]


class AdminUserCreateRequest(BaseModel):
    """创建用户请求。"""

    username: str = Field(min_length=3, max_length=32, description="用户名")
    password: str = Field(min_length=6, max_length=128, description="初始密码")
    is_active: bool = Field(default=True, description="是否启用")
    is_admin: bool = Field(default=False, description="是否管理员")


class AdminUserCreateResponse(BaseModel):
    """创建用户响应。"""

    success: bool = True
    user: AdminUserItem


class AdminUserStatusUpdateRequest(BaseModel):
    """更新用户启停用状态请求。"""

    is_active: bool = Field(description="是否启用")


class AdminUserStatusUpdateResponse(BaseModel):
    """更新用户状态响应。"""

    success: bool = True
    user: AdminUserItem


class AdminUserRoleUpdateRequest(BaseModel):
    """更新用户管理员角色请求。"""

    is_admin: bool = Field(description="是否管理员")


class AdminUserRoleUpdateResponse(BaseModel):
    """更新用户角色响应。"""

    success: bool = True
    user: AdminUserItem


class AdminUserResetPasswordRequest(BaseModel):
    """重置密码请求。"""

    new_password: str = Field(min_length=6, max_length=128, description="新密码")


class AdminUserResetPasswordResponse(BaseModel):
    """重置密码响应。"""

    success: bool = True


def _to_user_item(user: UserInDB) -> AdminUserItem:
    username = (user.username or "").strip()
    return AdminUserItem(
        id=user.id,
        username=username,
        is_active=user.is_active,
        is_admin=bool(getattr(user, "is_admin", False)),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

async def _load_user_or_404(repo: UserRepository, user_id: int):
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


async def _count_admin_users(session: AsyncSession) -> int:
    """统计管理员总数。"""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.is_admin.is_(True))
    )
    return int(result.scalar() or 0)


async def _count_active_admin_users(session: AsyncSession) -> int:
    """统计启用状态的管理员数量。"""
    result = await session.execute(
        select(func.count()).select_from(User).where(User.is_admin.is_(True), User.is_active.is_(True))
    )
    return int(result.scalar() or 0)


@router.get("", response_model=AdminUsersListResponse)
async def list_users(
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUsersListResponse:
    """列出所有用户。"""
    repo = UserRepository(session)
    users = await repo.list_all()
    rows = sorted((UserInDB.model_validate(item) for item in users), key=lambda item: item.id)
    return AdminUsersListResponse(users=[_to_user_item(item) for item in rows])


@router.get("/monitor", response_model=AdminUsersMonitorResponse)
async def monitor_users(
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUsersMonitorResponse:
    """获取管理员用户监控面板数据。"""
    repo = UserRepository(session)
    users = await repo.list_all()
    rows = sorted((UserInDB.model_validate(item) for item in users), key=lambda item: item.id)

    novel_counts = await collect_count_map(session, NovelProject)
    coding_counts = await collect_count_map(session, CodingProject)
    llm_counts = await collect_count_map(session, LLMConfig)
    embedding_counts = await collect_count_map(session, EmbeddingConfig)
    image_counts = await collect_count_map(session, ImageGenerationConfig)
    theme_counts = await collect_count_map(session, ThemeConfig)

    novel_latest = await collect_latest_map(session, NovelProject)
    coding_latest = await collect_latest_map(session, CodingProject)
    llm_latest = await collect_latest_map(session, LLMConfig)
    embedding_latest = await collect_latest_map(session, EmbeddingConfig)
    image_latest = await collect_latest_map(session, ImageGenerationConfig)
    theme_latest = await collect_latest_map(session, ThemeConfig)

    now_utc = datetime.now(timezone.utc)
    recent_threshold = now_utc - timedelta(days=7)

    user_rows: list[AdminUserMonitorItem] = []
    recently_active_users = 0

    for user in rows:
        user_id = int(user.id)
        username = (user.username or "").strip()

        novel_projects = int(novel_counts.get(user_id, 0))
        coding_projects = int(coding_counts.get(user_id, 0))
        llm_configs = int(llm_counts.get(user_id, 0))
        embedding_configs = int(embedding_counts.get(user_id, 0))
        image_configs = int(image_counts.get(user_id, 0))
        theme_configs = int(theme_counts.get(user_id, 0))

        last_candidates = [
            normalize_datetime(user.updated_at),
            novel_latest.get(user_id),
            coding_latest.get(user_id),
            llm_latest.get(user_id),
            embedding_latest.get(user_id),
            image_latest.get(user_id),
            theme_latest.get(user_id),
        ]
        valid_candidates = [dt for dt in last_candidates if dt is not None]
        last_activity_at = max(valid_candidates) if valid_candidates else None
        recently_active = bool(last_activity_at and last_activity_at >= recent_threshold)
        if recently_active:
            recently_active_users += 1

        metrics = AdminUserMetrics(
            novel_projects=novel_projects,
            coding_projects=coding_projects,
            total_projects=novel_projects + coding_projects,
            llm_configs=llm_configs,
            embedding_configs=embedding_configs,
            image_configs=image_configs,
            theme_configs=theme_configs,
            last_activity_at=last_activity_at,
            recently_active=recently_active,
        )

        user_rows.append(
            AdminUserMonitorItem(
                id=user_id,
                username=username,
                is_active=bool(user.is_active),
                is_admin=bool(getattr(user, "is_admin", False)),
                created_at=user.created_at,
                updated_at=user.updated_at,
                metrics=metrics,
            )
        )

    total_users = len(user_rows)
    active_users = sum(1 for item in user_rows if item.is_active)
    admin_users = sum(1 for item in user_rows if item.is_admin)

    summary = AdminUsersMonitorSummary(
        total_users=total_users,
        active_users=active_users,
        inactive_users=total_users - active_users,
        admin_users=admin_users,
        recently_active_users=recently_active_users,
        total_novel_projects=sum(novel_counts.values()),
        total_coding_projects=sum(coding_counts.values()),
        total_projects=sum(novel_counts.values()) + sum(coding_counts.values()),
        total_llm_configs=sum(llm_counts.values()),
        total_embedding_configs=sum(embedding_counts.values()),
        total_image_configs=sum(image_counts.values()),
        total_theme_configs=sum(theme_counts.values()),
    )

    return AdminUsersMonitorResponse(summary=summary, users=user_rows)


@router.post("", response_model=AdminUserCreateResponse)
async def create_user(
    payload: AdminUserCreateRequest,
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUserCreateResponse:
    """创建新用户。"""
    username = payload.username.strip()
    if not _USERNAME_RE.match(username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名格式不正确（3-32，字母数字及 _ . -）",
        )

    repo = UserRepository(session)
    if await repo.username_exists(username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user = await repo.create_user(
        username=username,
        hashed_password=hash_password(payload.password),
        is_active=payload.is_active,
        is_admin=payload.is_admin,
    )
    await session.commit()
    user_in_db = UserInDB.model_validate(user)
    return AdminUserCreateResponse(user=_to_user_item(user_in_db))


@router.patch("/{user_id}/status", response_model=AdminUserStatusUpdateResponse)
async def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdateRequest,
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUserStatusUpdateResponse:
    """启用或禁用用户。"""
    repo = UserRepository(session)
    user = await _load_user_or_404(repo, user_id)

    if user.is_admin and user.is_active and not payload.is_active:
        active_admin_count = await _count_active_admin_users(session)
        if active_admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要保留一个启用状态的管理员账户")

    user.is_active = payload.is_active
    await session.commit()
    user_in_db = UserInDB.model_validate(user)
    return AdminUserStatusUpdateResponse(user=_to_user_item(user_in_db))


@router.patch("/{user_id}/role", response_model=AdminUserRoleUpdateResponse)
async def update_user_role(
    user_id: int,
    payload: AdminUserRoleUpdateRequest,
    current_admin: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUserRoleUpdateResponse:
    """授予或撤销管理员角色。"""
    repo = UserRepository(session)
    user = await _load_user_or_404(repo, user_id)

    if user.is_admin and not payload.is_admin:
        admin_count = await _count_admin_users(session)
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要保留一个管理员账户")

        if user.is_active:
            active_admin_count = await _count_active_admin_users(session)
            if active_admin_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="至少需要保留一个启用状态的管理员账户")

        if int(current_admin.id) == int(user.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能撤销当前登录管理员自己的权限")

    user.is_admin = payload.is_admin
    await session.commit()
    user_in_db = UserInDB.model_validate(user)
    return AdminUserRoleUpdateResponse(user=_to_user_item(user_in_db))


@router.post("/{user_id}/reset-password", response_model=AdminUserResetPasswordResponse)
async def reset_user_password(
    user_id: int,
    payload: AdminUserResetPasswordRequest,
    _: UserInDB = Depends(require_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUserResetPasswordResponse:
    """重置用户密码。"""
    repo = UserRepository(session)
    user = await _load_user_or_404(repo, user_id)
    user.hashed_password = hash_password(payload.new_password)
    await session.commit()
    return AdminUserResetPasswordResponse()
