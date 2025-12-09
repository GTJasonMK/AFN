"""
嵌入模型配置模型

支持远程 API（OpenAI 兼容）和本地 Ollama 两种提供方式。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class EmbeddingConfig(Base):
    """用户自定义的嵌入模型配置。支持多配置管理、测试和切换。"""

    __tablename__ = "embedding_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 配置基本信息
    config_name: Mapped[str] = mapped_column(String(100), nullable=False, default="默认嵌入配置")

    # 提供方类型: openai（远程API）或 ollama（本地）
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="openai")

    # API 配置（适用于 openai 提供方）
    api_base_url: Mapped[str | None] = mapped_column(Text())
    api_key: Mapped[str | None] = mapped_column(Text())

    # 模型配置
    model_name: Mapped[str | None] = mapped_column(Text())

    # 向量维度（可选，自动检测或手动指定）
    vector_size: Mapped[int | None] = mapped_column(Integer)

    # 配置状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 测试相关
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[str | None] = mapped_column(String(50))  # success, failed, pending
    test_message: Mapped[str | None] = mapped_column(Text())

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="embedding_configs")
