"""主角档案系统数据模型

包含主角档案、属性变更历史、行为记录、删除标记等四个模型，
用于追踪主角的属性变化和行为模式。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .novel import BIGINT_PK_TYPE


class ProtagonistProfile(Base):
    """主角档案主表

    存储主角的三类属性（显性、隐性、社会），内部结构由LLM自主决定。
    每个项目可以有多个主角档案，通过character_name区分。
    """

    __tablename__ = "protagonist_profiles"
    __table_args__ = (
        UniqueConstraint("project_id", "character_name", name="uq_protagonist_project_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    character_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # 三类属性 (JSON字段，内部结构由LLM自主决定)
    explicit_attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # 结构由LLM决定，示例: {"外貌": "黑发红眼", "装备": ["长剑", "皮甲"], ...}

    implicit_attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # 结构由LLM决定，示例: {"性格特点": ["谨慎", "重情义"], "行为习惯": [...], ...}

    social_attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # 结构由LLM决定，示例: {"师徒关系": {...}, "门派地位": "外门弟子", ...}

    # 同步状态
    last_synced_chapter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # 关系
    attribute_changes: Mapped[list["ProtagonistAttributeChange"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProtagonistAttributeChange.chapter_number"
    )
    behavior_records: Mapped[list["ProtagonistBehaviorRecord"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProtagonistBehaviorRecord.chapter_number"
    )
    deletion_marks: Mapped[list["ProtagonistDeletionMark"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
        order_by="ProtagonistDeletionMark.chapter_number"
    )


class ProtagonistAttributeChange(Base):
    """属性变更历史表（含证据溯源）

    记录主角属性的每一次变化，包括添加、修改、删除操作。
    每条记录必须包含原文引用作为证据，确保可溯源性。
    """

    __tablename__ = "protagonist_attribute_changes"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("protagonist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 变更信息
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    attribute_category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # explicit/implicit/social
    attribute_key: Mapped[str] = mapped_column(String(128), nullable=False)
    # 属性键名，如 "外貌"、"性格特点"
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    # add/modify/delete

    # 值变化（JSON序列化存储）
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 变更描述
    change_description: Mapped[str] = mapped_column(Text, nullable=False)
    event_cause: Mapped[str] = mapped_column(Text, nullable=False)
    # 触发事件描述

    # 证据溯源（关键字段）
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    # 原文引用，证明变更的真实依据

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 关系
    profile: Mapped["ProtagonistProfile"] = relationship(back_populates="attribute_changes")


class ProtagonistBehaviorRecord(Base):
    """行为记录表（用于隐性属性分析）

    记录主角在每章中的行为和对话，用于分析隐性属性的一致性。
    通过二元分类（符合/不符合）追踪属性与实际行为的匹配度。
    """

    __tablename__ = "protagonist_behavior_records"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("protagonist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 行为信息
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    behavior_description: Mapped[str] = mapped_column(Text, nullable=False)
    # 行为/对话描述

    # 证据溯源（关键字段）
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    # 原文摘录，作为行为依据

    # 行为标签
    behavior_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # 行为标签列表，如 ["勇敢", "保护欲", "正义感"]

    # 分类结果
    classification_results: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # 结构: {"谨慎": "conform", "冲动": "non-conform", ...}

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 关系
    profile: Mapped["ProtagonistProfile"] = relationship(back_populates="behavior_records")


class ProtagonistDeletionMark(Base):
    """删除标记表（保护机制）

    实现删除保护机制：需要连续5次标记才能实际删除属性。
    如果属性在此期间被引用或使用，连续计数会被重置。
    """

    __tablename__ = "protagonist_deletion_marks"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "attribute_category", "attribute_key",
            name="uq_deletion_mark_profile_category_key"
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("protagonist_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 目标属性
    attribute_category: Mapped[str] = mapped_column(String(32), nullable=False)
    # explicit/implicit/social
    attribute_key: Mapped[str] = mapped_column(String(128), nullable=False)
    # 要删除的属性键名

    # 标记信息
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # 首次标记的章节
    mark_reason: Mapped[str] = mapped_column(Text, nullable=False)
    # 标记原因

    # 证据溯源（关键字段）
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    # 支持删除的原文证据

    # 保护机制
    consecutive_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # 连续标记次数
    last_marked_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    # 最后一次标记的章节
    is_executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 是否已执行删除

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # 关系
    profile: Mapped["ProtagonistProfile"] = relationship(back_populates="deletion_marks")
