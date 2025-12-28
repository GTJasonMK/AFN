"""
用户自定义主题配置模型

支持两级主题结构：
- 顶级主题：浅色(light)、深色(dark)
- 子主题：每个顶级下可有多个自定义配置

配置结构 V2（面向组件）：
- tokens: 设计令牌（颜色、字体、间距等基础变量）
- components: 组件配置（按钮、卡片、输入框等具体样式）
- effects: 效果配置（透明度、动画等）
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

    配置版本：
    - V1（旧版）：面向常量的配置（primary_colors, text_colors等）
    - V2（新版）：面向组件的配置（token_*, comp_*, effects）

    系统同时支持两种格式，优先使用V2格式。
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

    # 配置格式版本：1 = 旧版（面向常量），2 = 新版（面向组件）
    config_version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )

    # ==================== V1: 旧版配置（面向常量，保留兼容）====================
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
    # 字体配置
    typography: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 圆角配置
    border_radius: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 间距配置
    spacing: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 动画配置
    animation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 按钮尺寸配置
    button_sizes: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # ==================== V2: 新版配置（面向组件）====================
    # 设计令牌 - 颜色
    token_colors: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 设计令牌 - 排版
    token_typography: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 设计令牌 - 间距
    token_spacing: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 设计令牌 - 圆角
    token_radius: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 组件配置 - 按钮（含 primary, secondary, ghost, danger 变体）
    comp_button: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 卡片
    comp_card: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 输入框
    comp_input: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 侧边栏（含透明效果）
    comp_sidebar: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 顶部栏（含透明效果）
    comp_header: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 对话框（含透明效果）
    comp_dialog: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 滚动条
    comp_scrollbar: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 工具提示
    comp_tooltip: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 标签页
    comp_tabs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 文本样式
    comp_text: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # 组件配置 - 语义反馈（success/error/warning/info）
    comp_semantic: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 效果配置（透明度、动画等全局效果）
    effects: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="theme_configs")
