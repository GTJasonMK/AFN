from typing import Optional

from sqlalchemy import select, update

from .base import BaseRepository
from ..models import LLMConfig


class LLMConfigRepository(BaseRepository[LLMConfig]):
    """LLM配置仓储，支持多配置管理和切换。"""

    model = LLMConfig

    async def get_by_user(self, user_id: int) -> Optional[LLMConfig]:
        """获取用户的第一个配置（兼容旧代码）。"""
        result = await self.session.execute(select(LLMConfig).where(LLMConfig.user_id == user_id))
        return result.scalars().first()

    async def list_by_user(self, user_id: int) -> list[LLMConfig]:
        """获取用户的所有LLM配置，按创建时间排序。"""
        result = await self.session.execute(
            select(LLMConfig).where(LLMConfig.user_id == user_id).order_by(LLMConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_config(self, user_id: int) -> Optional[LLMConfig]:
        """获取用户当前激活的配置。"""
        result = await self.session.execute(
            select(LLMConfig).where(LLMConfig.user_id == user_id, LLMConfig.is_active == True)
        )
        return result.scalars().first()

    async def get_by_id(self, config_id: int, user_id: int) -> Optional[LLMConfig]:
        """通过ID获取配置，同时验证用户权限。"""
        result = await self.session.execute(
            select(LLMConfig).where(LLMConfig.id == config_id, LLMConfig.user_id == user_id)
        )
        return result.scalars().first()

    async def activate_config(self, config_id: int, user_id: int) -> None:
        """激活指定配置，同时取消该用户的其他配置的激活状态。"""
        # 先将该用户的所有配置设为未激活
        await self.session.execute(
            update(LLMConfig).where(LLMConfig.user_id == user_id).values(is_active=False)
        )
        # 再激活指定配置
        await self.session.execute(
            update(LLMConfig).where(LLMConfig.id == config_id, LLMConfig.user_id == user_id).values(is_active=True)
        )
        await self.session.flush()

    async def get_by_name(self, user_id: int, config_name: str) -> Optional[LLMConfig]:
        """通过配置名称获取配置。"""
        result = await self.session.execute(
            select(LLMConfig).where(LLMConfig.user_id == user_id, LLMConfig.config_name == config_name)
        )
        return result.scalars().first()
