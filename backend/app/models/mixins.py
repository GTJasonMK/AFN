"""
SQLAlchemy 模型通用字段 Mixin

目标：收敛多个“配置模型”重复的状态/测试/时间戳字段定义，避免并行维护漂移。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column


class ActivationStatusMixin:
    """配置状态字段（是否激活/是否已验证）"""

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TestStatusMixin:
    """配置测试字段（最后测试时间/状态/消息）"""

    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[str | None] = mapped_column(String(50))  # success, failed, pending
    test_message: Mapped[str | None] = mapped_column(Text())


class TimestampsMixin:
    """通用时间戳字段（创建/更新时间）"""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

