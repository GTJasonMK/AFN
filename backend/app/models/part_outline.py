from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class PartOutline(Base):
    """小说部分大纲表（用于长篇小说的分层大纲结构）"""

    __tablename__ = "part_outlines"
    __table_args__ = (
        # 复合唯一约束：同一项目内part_number唯一，同时作为高效查询索引
        UniqueConstraint('project_id', 'part_number', name='uq_part_outline_project_part'),
        # 复合索引：优化按项目+状态查询（如获取待处理的部分）
        Index('ix_part_outline_project_status', 'project_id', 'generation_status'),
    )

    # 基础字段
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # 部分信息
    title: Mapped[Optional[str]] = mapped_column(String(255))
    start_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    end_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    theme: Mapped[Optional[str]] = mapped_column(String(500))

    # JSON字段存储复杂数据
    key_events: Mapped[Optional[list]] = mapped_column(JSON)  # 关键事件列表
    character_arcs: Mapped[Optional[dict]] = mapped_column(JSON)  # 角色成长弧线 {角色名: 成长描述}
    conflicts: Mapped[Optional[list]] = mapped_column(JSON)  # 主要冲突列表
    ending_hook: Mapped[Optional[str]] = mapped_column(Text)  # 与下一部分的衔接点

    # 状态和时间戳
    generation_status: Mapped[str] = mapped_column(String(50), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    project: Mapped[NovelProject] = relationship(back_populates="part_outlines")

    def __repr__(self):
        return f"<PartOutline {self.part_number}: {self.title}>"