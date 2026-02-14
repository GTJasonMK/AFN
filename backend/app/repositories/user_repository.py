"""用户数据访问层"""

from typing import Optional

from sqlalchemy import select

from .base import BaseRepository
from ..models.user import User


class UserRepository(BaseRepository[User]):
    """用户Repository，封装用户相关的数据库操作"""

    model = User

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            用户实例，不存在返回None
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            用户实例，不存在返回None
        """
        return await self.get(id=user_id)

    async def get_any_user(self) -> Optional[User]:
        """
        获取任意一个用户（用于桌面版fallback）

        Returns:
            用户实例，不存在返回None
        """
        result = await self.session.execute(select(User).limit(1))
        return result.scalars().first()

    async def username_exists(self, username: str) -> bool:
        """
        检查用户名是否已存在

        Args:
            username: 用户名

        Returns:
            是否存在
        """
        user = await self.get_by_username(username)
        return user is not None

    async def create_user(
        self,
        username: str,
        hashed_password: str,
        is_active: bool = True,
        is_admin: bool = False
    ) -> User:
        """
        创建新用户

        Args:
            username: 用户名
            hashed_password: 哈希后的密码
            is_active: 是否激活
            is_admin: 是否管理员

        Returns:
            创建的用户实例
        """
        user = User(
            username=username,
            hashed_password=hashed_password,
            is_active=is_active,
            is_admin=is_admin
        )
        return await self.add(user)
