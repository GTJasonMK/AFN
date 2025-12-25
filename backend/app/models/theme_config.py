"""
用户自定义主题配置模型

支持两级主题结构：
- 顶级主题：浅色(light)、深色(dark)
- 子主题：每个顶级下可有多个自定义配置
"""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON

from ..db.base import Base


class ThemeConfig(Base):
    """用户自定义主题配置

    每个用户可以在浅色和深色两个顶级主题下各创建多个子主题。
    每个顶级主题下只能有一个激活的子主题。
    """

    __tablename__ = "theme_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 配置基本信息
    config_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="默认主题"
    )
    parent_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # "light" 或 "dark"

    # 激活状态（每个parent_mode下只能有一个激活的配置）
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    # ==================== 颜色配置（JSON存储）====================
    # 主色调组
    primary_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 强调色组
    accent_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 语义色组（success, error, warning, info）
    semantic_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 文字色组
    text_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 背景色组
    background_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 边框与特效组
    border_effects: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 按钮文字色组
    button_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # ==================== 排版配置（JSON存储）====================
    # 字体配置（字体族、大小、粗细、行高、字间距）
    typography: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # ==================== 设计系统配置（JSON存储）====================
    # 圆角配置
    border_radius: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 间距配置
    spacing: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 动画配置
    animation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 按钮尺寸配置
    button_sizes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="theme_configs")
