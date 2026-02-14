from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class User(Base):
    """用户主表，记录账号及权限信息。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # 关系映射
    novel_projects: Mapped[list["NovelProject"]] = relationship("NovelProject", back_populates="owner")
    coding_projects: Mapped[list["CodingProject"]] = relationship("CodingProject", back_populates="owner")
    llm_configs: Mapped[list["LLMConfig"]] = relationship("LLMConfig", back_populates="user", cascade="all, delete-orphan")
    embedding_configs: Mapped[list["EmbeddingConfig"]] = relationship("EmbeddingConfig", back_populates="user", cascade="all, delete-orphan")
    image_configs: Mapped[list["ImageGenerationConfig"]] = relationship("ImageGenerationConfig", back_populates="user", cascade="all, delete-orphan")
    theme_configs: Mapped[list["ThemeConfig"]] = relationship("ThemeConfig", back_populates="user", cascade="all, delete-orphan")
