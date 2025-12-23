"""
角色立绘仓储

负责角色立绘的数据访问操作。
"""

from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.character_portrait import CharacterPortrait


class CharacterPortraitRepository(BaseRepository[CharacterPortrait]):
    """角色立绘仓储"""

    model = CharacterPortrait

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, portrait_id: str) -> Optional[CharacterPortrait]:
        """根据ID获取立绘"""
        return await self.get(id=portrait_id)

    async def get_by_project(self, project_id: str) -> List[CharacterPortrait]:
        """获取项目的所有立绘"""
        result = await self.session.execute(
            select(CharacterPortrait)
            .where(CharacterPortrait.project_id == project_id)
            .order_by(CharacterPortrait.character_name, CharacterPortrait.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_character(
        self,
        project_id: str,
        character_name: str,
    ) -> List[CharacterPortrait]:
        """获取某个角色的所有立绘"""
        result = await self.session.execute(
            select(CharacterPortrait)
            .where(
                CharacterPortrait.project_id == project_id,
                CharacterPortrait.character_name == character_name,
            )
            .order_by(CharacterPortrait.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_by_character(
        self,
        project_id: str,
        character_name: str,
    ) -> Optional[CharacterPortrait]:
        """获取角色当前激活的立绘"""
        result = await self.session.execute(
            select(CharacterPortrait)
            .where(
                CharacterPortrait.project_id == project_id,
                CharacterPortrait.character_name == character_name,
                CharacterPortrait.is_active == True,
            )
            .order_by(CharacterPortrait.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_all_active_by_project(
        self,
        project_id: str,
    ) -> List[CharacterPortrait]:
        """获取项目中所有角色的激活立绘"""
        result = await self.session.execute(
            select(CharacterPortrait)
            .where(
                CharacterPortrait.project_id == project_id,
                CharacterPortrait.is_active == True,
            )
            .order_by(CharacterPortrait.character_name)
        )
        return list(result.scalars().all())

    async def set_active(
        self,
        portrait_id: str,
    ) -> Optional[CharacterPortrait]:
        """设置立绘为激活状态，同时取消同一角色的其他立绘激活状态"""
        # 先获取要激活的立绘
        portrait = await self.get_by_id(portrait_id)
        if not portrait:
            return None

        # 取消同一角色的其他立绘激活状态
        await self.session.execute(
            update(CharacterPortrait)
            .where(
                CharacterPortrait.project_id == portrait.project_id,
                CharacterPortrait.character_name == portrait.character_name,
                CharacterPortrait.id != portrait_id,
            )
            .values(is_active=False)
        )

        # 激活指定立绘
        portrait.is_active = True
        await self.session.flush()

        return portrait

    async def deactivate(self, portrait_id: str) -> bool:
        """取消立绘激活状态"""
        portrait = await self.get_by_id(portrait_id)
        if not portrait:
            return False

        portrait.is_active = False
        await self.session.flush()
        return True

    async def delete_by_id(self, portrait_id: str) -> bool:
        """根据ID删除立绘记录（不删除文件）"""
        portrait = await self.get_by_id(portrait_id)
        if not portrait:
            return False

        await self.delete(portrait)
        return True

    async def delete_by_character(
        self,
        project_id: str,
        character_name: str,
    ) -> int:
        """删除某个角色的所有立绘记录"""
        portraits = await self.get_by_character(project_id, character_name)
        count = 0
        for portrait in portraits:
            await self.delete(portrait)
            count += 1
        return count

    async def get_active_portraits_map(
        self,
        project_id: str,
    ) -> dict:
        """获取项目中所有角色的激活立绘映射

        Returns:
            dict: {角色名: 图片路径}，用于漫画生成时的img2img引用
        """
        portraits = await self.get_all_active_by_project(project_id)
        return {
            portrait.character_name: portrait.image_path
            for portrait in portraits
            if portrait.image_path
        }
