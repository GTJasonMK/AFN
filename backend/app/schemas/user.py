from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserInDB(BaseModel):
    """桌面版用户数据模型（简化版，仅包含必要字段）"""

    id: int = Field(..., description="用户主键")
    username: str = Field(..., description="用户名")
    hashed_password: str = Field(..., description="哈希后的密码")
    is_active: bool = Field(default=True, description="是否激活")
    is_admin: bool = Field(default=False, description="是否管理员")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")

    class Config:
        from_attributes = True
