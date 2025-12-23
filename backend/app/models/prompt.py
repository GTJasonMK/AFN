from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class Prompt(Base):
    """提示词表，支持后台 CRUD 操作。"""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 使用场景描述
    tags: Mapped[Optional[str]] = mapped_column(String(255))
    is_modified: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否已被用户修改
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
