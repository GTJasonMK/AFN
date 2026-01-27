from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .mixins import ActivationStatusMixin, TestStatusMixin, TimestampsMixin


class LLMConfig(Base, ActivationStatusMixin, TestStatusMixin, TimestampsMixin):
    """用户自定义的 LLM 接入配置。支持多配置管理、测试和切换。"""

    __tablename__ = "llm_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 配置基本信息
    config_name: Mapped[str] = mapped_column(String(100), nullable=False, default="默认配置")
    llm_provider_url: Mapped[str | None] = mapped_column(Text())
    llm_provider_api_key: Mapped[str | None] = mapped_column(Text())
    llm_provider_model: Mapped[str | None] = mapped_column(Text())

    user: Mapped["User"] = relationship("User", back_populates="llm_configs")

