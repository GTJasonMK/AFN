"""
编程项目目录结构和文件Prompt模型

独立于功能大纲的文件级别Prompt生成系统。
基于模块生成目录结构，为每个源文件生成实现Prompt。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON, BigInteger, Boolean, DateTime, ForeignKey, Index,
    Integer, String, Text, func, UniqueConstraint
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base

# 自定义列类型：兼容跨数据库环境
BIGINT_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")
LONG_TEXT_TYPE = Text().with_variant(LONGTEXT, "mysql")


class CodingDirectoryNode(Base):
    """目录结构节点

    表示项目目录树中的一个节点，可以是目录或包（如Python的package）。
    采用parent_id方式存储层级关系。
    """

    __tablename__ = "coding_directory_nodes"
    __table_args__ = (
        UniqueConstraint('project_id', 'path', name='uq_coding_dir_project_path'),
        Index('idx_coding_dir_parent', 'project_id', 'parent_id'),
        Index('idx_coding_dir_module', 'project_id', 'module_number'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("coding_projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # 层级关系
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("coding_directory_nodes.id", ondelete="CASCADE"),
        nullable=True
    )

    # 节点信息
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 目录名
    path: Mapped[str] = mapped_column(String(1024), nullable=False)  # 完整路径 如 src/services/user
    node_type: Mapped[str] = mapped_column(String(32), default="directory")  # directory / package
    description: Mapped[Optional[str]] = mapped_column(Text)  # 目录说明

    # 排序字段
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 关联到模块（追踪哪个模块生成了这个目录）
    module_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 生成状态: pending -> generating -> completed / failed
    generation_status: Mapped[str] = mapped_column(String(32), default="pending")

    # 是否用户手动创建（区分AI生成和用户添加）
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    project: Mapped["CodingProject"] = relationship("CodingProject", back_populates="directory_nodes")
    parent: Mapped[Optional["CodingDirectoryNode"]] = relationship(
        "CodingDirectoryNode",
        remote_side=[id],
        back_populates="children"
    )
    children: Mapped[list["CodingDirectoryNode"]] = relationship(
        "CodingDirectoryNode",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    source_files: Mapped[list["CodingSourceFile"]] = relationship(
        back_populates="directory",
        cascade="all, delete-orphan"
    )


class CodingSourceFile(Base):
    """源文件

    表示项目中的一个源代码文件，可以生成对应的实现Prompt。
    """

    __tablename__ = "coding_source_files"
    __table_args__ = (
        UniqueConstraint('project_id', 'file_path', name='uq_coding_file_project_path'),
        Index('idx_coding_file_dir', 'directory_id'),
        Index('idx_coding_file_module', 'project_id', 'module_number'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("coding_projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    directory_id: Mapped[int] = mapped_column(
        ForeignKey("coding_directory_nodes.id", ondelete="CASCADE"),
        nullable=False
    )

    # 文件信息
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # 文件名 如 user_service.py
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # 完整路径
    file_type: Mapped[str] = mapped_column(String(64), default="source")  # source/config/test/doc
    language: Mapped[Optional[str]] = mapped_column(String(64))  # python/typescript/go等

    # 文件描述
    description: Mapped[Optional[str]] = mapped_column(Text)
    purpose: Mapped[Optional[str]] = mapped_column(Text)  # 文件用途说明

    # 依赖信息（JSON）
    imports: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # 导入的模块
    exports: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # 导出的接口
    dependencies: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # 依赖的其他文件

    # 关联到模块和系统
    module_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    system_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 优先级（用于排序生成顺序）
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # high/medium/low
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Prompt生成状态: not_generated -> generating -> generated / failed
    status: Mapped[str] = mapped_column(String(32), default="not_generated")

    # 当前选中的版本
    selected_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("coding_file_versions.id", ondelete="SET NULL"),
        nullable=True
    )

    # 审查Prompt
    review_prompt: Mapped[Optional[str]] = mapped_column(LONG_TEXT_TYPE, nullable=True)

    # 是否用户手动创建
    is_manual: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    project: Mapped["CodingProject"] = relationship("CodingProject", back_populates="source_files")
    directory: Mapped["CodingDirectoryNode"] = relationship(back_populates="source_files")
    versions: Mapped[list["CodingFileVersion"]] = relationship(
        "CodingFileVersion",
        back_populates="source_file",
        cascade="all, delete-orphan",
        order_by="CodingFileVersion.created_at",
        primaryjoin="CodingSourceFile.id == CodingFileVersion.file_id",
        foreign_keys="[CodingFileVersion.file_id]",
    )
    selected_version: Mapped[Optional["CodingFileVersion"]] = relationship(
        "CodingFileVersion",
        foreign_keys=[selected_version_id],
        primaryjoin="CodingSourceFile.selected_version_id == CodingFileVersion.id",
        post_update=True,
    )


class CodingAgentState(Base):
    """Agent规划状态

    保存Agent规划的中间状态，支持断点续传。
    """

    __tablename__ = "coding_agent_states"
    __table_args__ = (
        UniqueConstraint('project_id', 'agent_type', name='uq_coding_agent_state'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("coding_projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Agent类型: directory_planning / prompt_generation 等
    agent_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # 状态: running / paused / completed / failed
    status: Mapped[str] = mapped_column(String(32), default="running")

    # 当前阶段
    current_phase: Mapped[str] = mapped_column(String(64), default="analyzing")

    # 状态数据（JSON序列化的完整状态）
    state_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # 日志/输出记录
    output_log: Mapped[Optional[str]] = mapped_column(LONG_TEXT_TYPE)

    # 进度信息
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    progress_message: Mapped[Optional[str]] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 关系
    project: Mapped["CodingProject"] = relationship("CodingProject")


class CodingFileVersion(Base):
    """源文件Prompt版本

    存储每个源文件生成的Prompt的不同版本。
    """

    __tablename__ = "coding_file_versions"
    __table_args__ = (
        Index('idx_coding_file_version_created', 'file_id', 'created_at'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(
        ForeignKey("coding_source_files.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    version_label: Mapped[Optional[str]] = mapped_column(String(64))  # v1, v2, ...
    provider: Mapped[Optional[str]] = mapped_column(String(64))  # LLM提供商

    # Prompt内容
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)

    # 元数据
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 关系
    source_file: Mapped["CodingSourceFile"] = relationship(
        "CodingSourceFile",
        back_populates="versions",
        foreign_keys=[file_id],
    )
