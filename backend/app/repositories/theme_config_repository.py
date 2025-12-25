"""
主题配置仓储

支持两级主题结构：每个parent_mode下可有多个子主题，但只能激活一个。
"""

from typing import Optional

from sqlalchemy import case, select, update

from .base import BaseRepository
from ..models import ThemeConfig


class ThemeConfigRepository(BaseRepository[ThemeConfig]):
    """主题配置仓储，支持多配置管理和切换。"""

    model = ThemeConfig

    async def list_by_user(self, user_id: int) -> list[ThemeConfig]:
        """获取用户的所有主题配置。"""
        result = await self.session.execute(
            select(ThemeConfig)
            .where(ThemeConfig.user_id == user_id)
            .order_by(ThemeConfig.parent_mode, ThemeConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_mode(self, user_id: int, parent_mode: str) -> list[ThemeConfig]:
        """获取用户指定模式下的所有主题配置。"""
        result = await self.session.execute(
            select(ThemeConfig)
            .where(ThemeConfig.user_id == user_id, ThemeConfig.parent_mode == parent_mode)
            .order_by(ThemeConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_config(self, user_id: int, parent_mode: str) -> Optional[ThemeConfig]:
        """获取用户指定模式下当前激活的配置。"""
        result = await self.session.execute(
            select(ThemeConfig).where(
                ThemeConfig.user_id == user_id,
                ThemeConfig.parent_mode == parent_mode,
                ThemeConfig.is_active == True,
            )
        )
        return result.scalars().first()

    async def get_by_id(self, config_id: int, user_id: int) -> Optional[ThemeConfig]:
        """通过ID获取配置，同时验证用户权限。"""
        result = await self.session.execute(
            select(ThemeConfig).where(ThemeConfig.id == config_id, ThemeConfig.user_id == user_id)
        )
        return result.scalars().first()

    async def activate_config(self, config_id: int, user_id: int, parent_mode: str) -> None:
        """激活指定配置，同时取消该用户同模式下其他配置的激活状态。

        使用单条UPDATE语句的CASE表达式实现原子操作，避免竞态条件。
        """
        await self.session.execute(
            update(ThemeConfig)
            .where(ThemeConfig.user_id == user_id, ThemeConfig.parent_mode == parent_mode)
            .values(
                is_active=case(
                    (ThemeConfig.id == config_id, True),
                    else_=False,
                )
            )
        )
        await self.session.flush()

    async def get_by_name(
        self, user_id: int, config_name: str, parent_mode: str
    ) -> Optional[ThemeConfig]:
        """通过配置名称获取配置（同模式下名称唯一）。"""
        result = await self.session.execute(
            select(ThemeConfig).where(
                ThemeConfig.user_id == user_id,
                ThemeConfig.config_name == config_name,
                ThemeConfig.parent_mode == parent_mode,
            )
        )
        return result.scalars().first()

    async def count_by_mode(self, user_id: int, parent_mode: str) -> int:
        """统计用户指定模式下的配置数量。"""
        result = await self.session.execute(
            select(ThemeConfig).where(
                ThemeConfig.user_id == user_id, ThemeConfig.parent_mode == parent_mode
            )
        )
        return len(result.scalars().all())
