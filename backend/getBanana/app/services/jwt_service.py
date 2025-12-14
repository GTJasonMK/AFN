"""
JWT 服务
- 从 Google 获取 xsrfToken
- 生成 Gemini Business JWT
"""
import asyncio
import logging
from typing import Optional, Tuple

import httpx

from app.config import config_manager
from app.models.account import Account
from app.utils.crypto import decode_xsrf_token, create_jwt_token
from app.services.account_manager import (
    account_manager,
    AccountAuthError,
    AccountRateLimitError,
    AccountRequestError,
    CooldownReason
)

logger = logging.getLogger(__name__)

# API endpoints
GETOXSRF_URL = "https://business.gemini.google/auth/getoxsrf"

# HTTP 客户端
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """获取 HTTP 客户端（单例）"""
    global _http_client
    if _http_client is None:
        proxy = config_manager.config.proxy or None
        _http_client = httpx.AsyncClient(
            timeout=30.0,
            verify=False,
            proxy=proxy if proxy else None
        )
    return _http_client


async def close_http_client():
    """关闭 HTTP 客户端"""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None


class JWTService:
    """
    JWT 服务

    负责：
    1. 从 Google 获取 xsrfToken 和 keyId
    2. 使用 xsrfToken 生成 JWT
    3. JWT 缓存和刷新
    """

    def __init__(self):
        self._lock = asyncio.Lock()

    async def get_jwt_for_account(
        self,
        account: Account,
        force_refresh: bool = False
    ) -> Tuple[str, float]:
        """
        获取账号的 JWT

        Args:
            account: 账号
            force_refresh: 是否强制刷新

        Returns:
            (jwt_token, expires_at)
        """
        async with self._lock:
            # 检查缓存的 JWT 是否有效
            if not force_refresh and account.state.is_jwt_valid():
                return account.state.jwt, account.state.jwt_expires_at

            # 需要获取新的 JWT
            jwt, expires_at = await self._fetch_new_jwt(account)

            # 更新账号状态
            account_manager.update_account_state(
                account.index,
                jwt=jwt,
                jwt_expires_at=expires_at
            )

            return jwt, expires_at

    async def _fetch_new_jwt(self, account: Account) -> Tuple[str, float]:
        """
        从 Google 获取新的 JWT

        流程：
        1. 请求 /auth/getoxsrf 获取 xsrfToken 和 keyId
        2. 使用 xsrfToken 作为 HMAC 密钥生成 JWT
        """
        client = await get_http_client()

        # 构建请求
        url = f"{GETOXSRF_URL}?csesidx={account.csesidx}"
        headers = {
            "accept": "*/*",
            "user-agent": account.user_agent,
            "cookie": f"__Secure-C_SES={account.secure_c_ses}; __Host-C_OSES={account.host_c_oses}"
        }

        try:
            response = await client.get(url, headers=headers)
        except httpx.RequestError as e:
            logger.error(f"获取 JWT 请求失败: {e}")
            raise AccountRequestError(f"请求失败: {e}")

        # 处理响应
        if response.status_code == 401:
            raise AccountAuthError("认证失败，Cookie 可能已过期")
        elif response.status_code == 429:
            raise AccountRateLimitError("触发限额")
        elif response.status_code != 200:
            raise AccountRequestError(f"请求失败: {response.status_code}")

        # 解析响应（Google 安全前缀）
        text = response.text
        if text.startswith(")]}'\n") or text.startswith(")]}'"):
            text = text[4:].strip()

        try:
            import json
            data = json.loads(text)
        except Exception as e:
            raise AccountAuthError(f"解析响应失败: {e}")

        key_id = data.get("keyId")
        xsrf_token = data.get("xsrfToken")

        if not key_id or not xsrf_token:
            raise AccountAuthError(f"响应缺少 keyId 或 xsrfToken")

        # 生成 JWT
        key_bytes = decode_xsrf_token(xsrf_token)
        jwt, expires_at = create_jwt_token(key_bytes, key_id, account.csesidx)

        logger.debug(f"账号 {account.index} JWT 获取成功，key_id: {key_id}")

        return jwt, expires_at

    async def ensure_jwt(self, account: Account) -> str:
        """
        确保账号有有效的 JWT

        如果 JWT 即将过期（30秒内），自动刷新
        """
        jwt, _ = await self.get_jwt_for_account(account)
        return jwt


# 全局 JWT 服务实例
jwt_service = JWTService()
