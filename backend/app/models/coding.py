"""
Coding项目数据模型

独立的代码项目管理表结构，与小说项目完全分离。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base

# 自定义列类型：兼容跨数据库环境
BIGINT_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")
LONG_TEXT_TYPE = Text().with_variant(LONGTEXT, "mysql")


class CodingProject(Base):
    """代码项目主表"""

    __tablename__ = "coding_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    initial_prompt: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    owner: Mapped["User"] = relationship("User", back_populates="coding_projects")
    blueprint: Mapped[Optional["CodingBlueprint"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    conversations: Mapped[list["CodingConversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CodingConversation.seq"
    )
    systems: Mapped[list["CodingSystem"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CodingSystem.system_number"
    )
    modules: Mapped[list["CodingModule"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CodingModule.module_number"
    )
    # 目录结构和源文件（文件驱动Prompt系统）
    directory_nodes: Mapped[list["CodingDirectoryNode"]] = relationship(
        "CodingDirectoryNode",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="CodingDirectoryNode.path"
    )
    source_files: Mapped[list["CodingSourceFile"]] = relationship(
        "CodingSourceFile",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="CodingSourceFile.file_path"
    )


class CodingConversation(Base):
    """代码项目对话记录表，存储需求分析阶段的连续对话"""

    __tablename__ = "coding_conversations"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("coding_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[CodingProject] = relationship(back_populates="conversations")


class CodingBlueprint(Base):
    """代码项目架构蓝图"""

    __tablename__ = "coding_blueprints"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("coding_projects.id", ondelete="CASCADE"), primary_key=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255))
    target_audience: Mapped[Optional[str]] = mapped_column(String(255))
    project_type_desc: Mapped[Optional[str]] = mapped_column(String(128))
    tech_style: Mapped[Optional[str]] = mapped_column(String(128))
    project_tone: Mapped[Optional[str]] = mapped_column(String(128))
    one_sentence_summary: Mapped[Optional[str]] = mapped_column(Text)
    architecture_synopsis: Mapped[Optional[str]] = mapped_column(LONG_TEXT_TYPE)

    # 技术栈配置
    tech_stack: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # 架构设计辅助信息
    system_suggestions: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    core_requirements: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    technical_challenges: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    non_functional_requirements: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    risks: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    milestones: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # 模块依赖关系
    dependencies: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # 统计信息
    total_systems: Mapped[int] = mapped_column(Integer, default=0)
    total_modules: Mapped[int] = mapped_column(Integer, default=0)
    total_features: Mapped[int] = mapped_column(Integer, default=0)

    # 分阶段设计标志
    needs_phased_design: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[CodingProject] = relationship(back_populates="blueprint")


class CodingSystem(Base):
    """代码项目系统 - 顶层划分

    系统是项目的顶层划分，如"用户系统"、"订单系统"、"支付系统"等。
    每个系统包含多个模块。
    """

    __tablename__ = "coding_systems"
    __table_args__ = (
        UniqueConstraint('project_id', 'system_number', name='uq_coding_system_project_number'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("coding_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    system_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    responsibilities: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    tech_requirements: Mapped[Optional[str]] = mapped_column(Text)

    # 统计信息
    module_count: Mapped[int] = mapped_column(Integer, default=0)
    feature_count: Mapped[int] = mapped_column(Integer, default=0)

    # 生成状态
    generation_status: Mapped[str] = mapped_column(String(32), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[CodingProject] = relationship(back_populates="systems")


class CodingModule(Base):
    """代码项目模块 - 中层组织

    模块是系统内的功能模块，如用户系统下的"认证模块"、"权限模块"等。
    每个模块包含多个功能。
    """

    __tablename__ = "coding_modules"
    __table_args__ = (
        UniqueConstraint('project_id', 'module_number', name='uq_coding_module_project_number'),
        Index('idx_coding_module_system', 'project_id', 'system_number'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("coding_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    module_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    module_type: Mapped[Optional[str]] = mapped_column(String(64))  # service/repository/controller/utility/middleware
    description: Mapped[Optional[str]] = mapped_column(Text)
    interface: Mapped[Optional[str]] = mapped_column(Text)
    dependencies: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # 统计信息
    feature_count: Mapped[int] = mapped_column(Integer, default=0)

    # 生成状态
    generation_status: Mapped[str] = mapped_column(String(32), default="pending")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[CodingProject] = relationship(back_populates="modules")
