"""
配置服务基类

抽取配置服务通用逻辑（名称校验、加解密、URL规范化、验证状态重置等）。
"""

from typing import Optional, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..exceptions import ResourceNotFoundError, ConflictError
from ..utils.encryption import encrypt_api_key, decrypt_api_key


class BaseConfigService:
    """配置服务通用基类"""

    def __init__(self, session: AsyncSession, repo, config_label: str):
        self.session = session
        self.repo = repo
        self._config_label = config_label

    def _encrypt_key(self, api_key: Optional[str]) -> Optional[str]:
        """加密API密钥"""
        return encrypt_api_key(api_key, settings.secret_key)

    def _decrypt_key(self, encrypted_key: Optional[str]) -> Optional[str]:
        """解密API密钥"""
        return decrypt_api_key(encrypted_key, settings.secret_key)

    async def _get_config_or_404(self, config_id: int, user_id: int):
        """获取配置，不存在则抛出异常"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError(self._config_label, f"ID={config_id}")
        return config

    async def _ensure_unique_name(
        self,
        user_id: int,
        config_name: str,
        config_id: Optional[int] = None,
    ) -> None:
        """确保配置名称唯一"""
        existing = await self.repo.get_by_name(user_id, config_name)
        if not existing:
            return
        if config_id is None:
            raise ConflictError(f"配置名称 '{config_name}' 已存在")
        if existing.id != config_id:
            raise ConflictError(f"配置名称 '{config_name}' 已被其他配置使用")

    async def _is_first_config(self, user_id: int) -> bool:
        """判断用户是否尚无配置"""
        configs = await self.repo.list_by_user(user_id)
        return len(configs) == 0

    @staticmethod
    def _normalize_url_field(data: dict, field_name: str) -> None:
        """规范化URL字段"""
        if field_name in data and data[field_name] is not None:
            data[field_name] = str(data[field_name])

    @staticmethod
    def _reset_test_state(data: dict, fields: Iterable[str]) -> None:
        """根据字段变化重置测试状态"""
        if any(key in data for key in fields):
            data["is_verified"] = False
            data["test_status"] = None
            data["test_message"] = None
