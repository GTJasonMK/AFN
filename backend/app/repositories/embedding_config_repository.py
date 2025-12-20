"""
嵌入模型配置仓储

提供嵌入模型配置的数据访问层。
"""

from typing import Optional

from sqlalchemy import case, select, update

from .base import BaseRepository
from ..models import EmbeddingConfig


class EmbeddingConfigRepository(BaseRepository[EmbeddingConfig]):
    """嵌入模型配置仓储，支持多配置管理和切换。"""

    model = EmbeddingConfig

    # list_by_user 继承自 BaseRepository，按 created_at 降序排列

    async def get_active_config(self, user_id: int) -> Optional[EmbeddingConfig]:
        """获取用户当前激活的配置。"""
        result = await self.session.execute(
            select(EmbeddingConfig).where(EmbeddingConfig.user_id == user_id, EmbeddingConfig.is_active == True)
        )
        return result.scalars().first()

    async def get_by_id(self, config_id: int, user_id: int) -> Optional[EmbeddingConfig]:
        """通过ID获取配置，同时验证用户权限。"""
        result = await self.session.execute(
            select(EmbeddingConfig).where(EmbeddingConfig.id == config_id, EmbeddingConfig.user_id == user_id)
        )
        return result.scalars().first()

    async def activate_config(self, config_id: int, user_id: int) -> None:
        """激活指定配置，同时取消该用户的其他配置的激活状态。

        使用单条UPDATE语句的CASE表达式实现原子操作，避免竞态条件。
        """
        await self.session.execute(
            update(EmbeddingConfig)
            .where(EmbeddingConfig.user_id == user_id)
            .values(
                is_active=case(
                    (EmbeddingConfig.id == config_id, True),
                    else_=False,
                )
            )
        )
        await self.session.flush()

    async def get_by_name(self, user_id: int, config_name: str) -> Optional[EmbeddingConfig]:
        """通过配置名称获取配置。"""
        result = await self.session.execute(
            select(EmbeddingConfig).where(EmbeddingConfig.user_id == user_id, EmbeddingConfig.config_name == config_name)
        )
        return result.scalars().first()
