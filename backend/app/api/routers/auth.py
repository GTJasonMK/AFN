"""
认证与用户系统路由（WebUI 可选）

设计目标：
- 当 settings.auth_enabled=False：保持历史行为（不要求登录，直接注入 desktop_user）。
- 当 settings.auth_enabled=True：启用多用户登录与数据隔离（按 user_id）。

说明：
- 采用 JWT（python-jose）作为访问令牌。
- 默认通过 HttpOnly Cookie 承载 token，便于文件下载/iframe/SSE 等同源请求自动携带；
  同时兼容 Authorization: Bearer <token>（由 dependencies.get_default_user 解析）。
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import AUTH_COOKIE_NAME, get_default_user
from ...core.security import hash_password, verify_password
from ...db.session import get_session
from ...repositories.user_repository import UserRepository
from ...schemas.user import UserInDB

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


class AuthStatusResponse(BaseModel):
    auth_enabled: bool = Field(description="是否启用登录")
    auth_allow_registration: bool = Field(description="是否允许自助注册")


class UserPublic(BaseModel):
    id: int
    username: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, description="用户名（3-32，字母数字及 _ . -）")
    password: str = Field(min_length=6, max_length=128, description="密码（至少6位）")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AuthOkResponse(BaseModel):
    success: bool = True
    user: UserPublic


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


def _issue_token(user_id: int, username: str) -> str:
    """签发 JWT 访问令牌。"""
    from jose import jwt

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def _set_auth_cookie(response: Response, token: str, *, secure: bool) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
    )


def _to_public(user: UserInDB) -> UserPublic:
    return UserPublic(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    """获取当前认证开关状态（公开接口，用于 WebUI 决定是否展示登录页）。"""
    return AuthStatusResponse(
        auth_enabled=bool(getattr(settings, "auth_enabled", False)),
        auth_allow_registration=bool(getattr(settings, "auth_allow_registration", True)),
    )


@router.get("/me", response_model=UserPublic)
async def me(
    current_user: UserInDB = Depends(get_default_user),
) -> UserPublic:
    """获取当前登录用户。"""
    return _to_public(current_user)


@router.post("/register", response_model=AuthOkResponse)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthOkResponse:
    """自助注册（仅在启用登录且允许注册时可用）。"""
    if not getattr(settings, "auth_enabled", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未启用登录，无需注册")
    if not getattr(settings, "auth_allow_registration", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前已关闭自助注册")

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
        is_active=True,
    )
    await session.commit()

    token = _issue_token(user.id, user.username)
    _set_auth_cookie(response, token, secure=request.url.scheme == "https")
    return AuthOkResponse(user=UserPublic(id=user.id, username=user.username, is_active=user.is_active))


@router.post("/login", response_model=AuthOkResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> AuthOkResponse:
    """登录并下发 Cookie token。"""
    if not getattr(settings, "auth_enabled", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未启用登录")

    username = payload.username.strip()
    repo = UserRepository(session)
    user = await repo.get_by_username(username)
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = _issue_token(user.id, user.username)
    _set_auth_cookie(response, token, secure=request.url.scheme == "https")
    return AuthOkResponse(user=UserPublic(id=user.id, username=user.username, is_active=user.is_active))


@router.post("/logout")
async def logout(response: Response) -> dict:
    """退出登录（清除 Cookie）。"""
    _clear_auth_cookie(response)
    return {"success": True}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserInDB = Depends(get_default_user),
) -> dict:
    """修改当前用户密码。"""
    repo = UserRepository(session)
    user = await repo.get_by_id(current_user.id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if not verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确")

    user.hashed_password = hash_password(payload.new_password)
    await session.commit()
    return {"success": True}

