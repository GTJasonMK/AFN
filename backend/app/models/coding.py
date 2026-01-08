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
    features: Mapped[list["CodingFeature"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CodingFeature.feature_number"
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


class CodingFeature(Base):
    """代码项目功能 - 最终产物

    功能是模块内的具体功能点，如认证模块下的"登录功能"、"注册功能"等。
    每个功能可以生成对应的实现Prompt。
    """

    __tablename__ = "coding_features"
    __table_args__ = (
        UniqueConstraint('project_id', 'feature_number', name='uq_coding_feature_project_number'),
        Index('idx_coding_feature_module', 'project_id', 'module_number'),
        Index('idx_coding_feature_system', 'project_id', 'system_number'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("coding_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_number: Mapped[int] = mapped_column(Integer, nullable=False)
    module_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    inputs: Mapped[Optional[str]] = mapped_column(Text)
    outputs: Mapped[Optional[str]] = mapped_column(Text)
    implementation_notes: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(16), default="medium")

    # 生成状态
    status: Mapped[str] = mapped_column(String(32), default="not_generated")

    # 生成的实现内容（多版本支持）
    selected_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("coding_feature_versions.id", ondelete="SET NULL"), nullable=True
    )

    # 审查Prompt
    review_prompt: Mapped[Optional[str]] = mapped_column(LONG_TEXT_TYPE, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[CodingProject] = relationship(back_populates="features")
    versions: Mapped[list["CodingFeatureVersion"]] = relationship(
        "CodingFeatureVersion",
        back_populates="feature",
        cascade="all, delete-orphan",
        order_by="CodingFeatureVersion.created_at",
        primaryjoin="CodingFeature.id == CodingFeatureVersion.feature_id",
        foreign_keys="[CodingFeatureVersion.feature_id]",
    )
    selected_version: Mapped[Optional["CodingFeatureVersion"]] = relationship(
        "CodingFeatureVersion",
        foreign_keys=[selected_version_id],
        primaryjoin="CodingFeature.selected_version_id == CodingFeatureVersion.id",
        post_update=True,
    )


class CodingFeatureVersion(Base):
    """代码功能生成的不同版本"""

    __tablename__ = "coding_feature_versions"
    __table_args__ = (
        Index('idx_coding_feature_version_created', 'feature_id', 'created_at'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("coding_features.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label: Mapped[Optional[str]] = mapped_column(String(64))
    provider: Mapped[Optional[str]] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    feature: Mapped[CodingFeature] = relationship(
        "CodingFeature",
        back_populates="versions",
        foreign_keys=[feature_id],
    )
