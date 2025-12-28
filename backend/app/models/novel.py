from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.state_machine import ProjectStatus
from ..db.base import Base

# 自定义列类型：兼容跨数据库环境
BIGINT_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")
LONG_TEXT_TYPE = Text().with_variant(LONGTEXT, "mysql")


class _MetadataAccessor:
    """Descriptor 用于将 `metadata` 访问重定向到 `metadata_`，且保持 Base.metadata 可用。"""

    def __get__(self, instance, owner):
        if instance is None:
            return Base.metadata
        return instance.metadata_

    def __set__(self, instance, value):
        instance.metadata_ = value


class NovelProject(Base):
    """小说项目主表，仅存放轻量级元数据。"""

    __tablename__ = "novel_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    initial_prompt: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.DRAFT.value)

    # 导入分析相关字段
    is_imported: Mapped[bool] = mapped_column(Boolean, default=False, doc="是否为外部导入项目")
    import_analysis_status: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, doc="导入分析状态: pending/analyzing/completed/failed"
    )
    import_analysis_progress: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, doc="分析进度信息"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner: Mapped["User"] = relationship("User", back_populates="novel_projects")
    blueprint: Mapped[Optional["NovelBlueprint"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", uselist=False
    )
    conversations: Mapped[list["NovelConversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="NovelConversation.seq"
    )
    characters: Mapped[list["BlueprintCharacter"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="BlueprintCharacter.position"
    )
    relationships_: Mapped[list["BlueprintRelationship"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="BlueprintRelationship.position"
    )
    outlines: Mapped[list["ChapterOutline"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ChapterOutline.chapter_number"
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Chapter.chapter_number"
    )
    part_outlines: Mapped[list["PartOutline"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="PartOutline.part_number"
    )
    character_portraits: Mapped[list["CharacterPortrait"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="CharacterPortrait.created_at"
    )


class NovelConversation(Base):
    """对话记录表，存储概念阶段的连续对话。"""

    __tablename__ = "novel_conversations"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    metadata = _MetadataAccessor()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[NovelProject] = relationship(back_populates="conversations")


class NovelBlueprint(Base):
    """蓝图主体信息（标题、风格等）。"""

    __tablename__ = "novel_blueprints"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id", ondelete="CASCADE"), primary_key=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(255))
    target_audience: Mapped[Optional[str]] = mapped_column(String(255))
    genre: Mapped[Optional[str]] = mapped_column(String(128))
    style: Mapped[Optional[str]] = mapped_column(String(128))
    tone: Mapped[Optional[str]] = mapped_column(String(128))
    one_sentence_summary: Mapped[Optional[str]] = mapped_column(Text)
    full_synopsis: Mapped[Optional[str]] = mapped_column(LONG_TEXT_TYPE)
    world_setting: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    needs_part_outlines: Mapped[bool] = mapped_column(Boolean, default=False)
    total_chapters: Mapped[Optional[int]] = mapped_column(Integer)
    chapters_per_part: Mapped[int] = mapped_column(Integer, default=25)

    # 小说头像（SVG格式，由LLM生成的小动物图标）
    avatar_svg: Mapped[Optional[str]] = mapped_column(Text)
    avatar_animal: Mapped[Optional[str]] = mapped_column(String(64))  # 动物类型，如"fox", "owl"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[NovelProject] = relationship(back_populates="blueprint")


class BlueprintCharacter(Base):
    """蓝图角色信息。"""

    __tablename__ = "blueprint_characters"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identity: Mapped[Optional[str]] = mapped_column(String(255))
    personality: Mapped[Optional[str]] = mapped_column(Text)
    goals: Mapped[Optional[str]] = mapped_column(Text)
    abilities: Mapped[Optional[str]] = mapped_column(Text)
    relationship_to_protagonist: Mapped[Optional[str]] = mapped_column(Text)
    extra: Mapped[Optional[dict]] = mapped_column(JSON)
    position: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[NovelProject] = relationship(back_populates="characters")


class BlueprintRelationship(Base):
    """角色之间的关系。"""

    __tablename__ = "blueprint_relationships"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    character_from: Mapped[str] = mapped_column(String(255), nullable=False)
    character_to: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)

    project: Mapped[NovelProject] = relationship(back_populates="relationships_")


class ChapterOutline(Base):
    """章节纲要。"""

    __tablename__ = "chapter_outlines"
    __table_args__ = (
        UniqueConstraint('project_id', 'chapter_number', name='uq_project_chapter'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)

    project: Mapped[NovelProject] = relationship(back_populates="outlines")


class Chapter(Base):
    """章节正文状态，指向选中的版本。"""

    __tablename__ = "chapters"
    __table_args__ = (
        # 复合唯一约束：同一项目内chapter_number唯一，同时作为高效查询索引
        UniqueConstraint('project_id', 'chapter_number', name='uq_chapter_project_number'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    real_summary: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="not_generated")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    selected_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chapter_versions.id", ondelete="SET NULL"), nullable=True
    )

    # 章节分析数据 - 预处理结果存储
    analysis_data: Mapped[Optional[dict]] = mapped_column(JSON)
    """
    {
        "metadata": {
            "characters": ["角色名列表"],
            "locations": ["地点列表"],
            "items": ["物品列表"],
            "tags": ["战斗", "对话"],
            "tone": "情感基调",
            "timeline_marker": "时间标记"
        },
        "summaries": {
            "compressed": "100字压缩摘要",
            "one_line": "30字一句话摘要",
            "keywords": ["关键词"]
        },
        "character_states": {
            "角色名": {
                "location": "当前位置",
                "status": "状态描述",
                "changes": ["本章变化"]
            }
        },
        "foreshadowing": {
            "planted": [{"description": "...", "priority": "high"}],
            "resolved": [{"id": "...", "resolution": "..."}],
            "tensions": ["未解悬念"]
        },
        "key_events": [
            {"type": "battle", "description": "...", "importance": "high"}
        ]
    }
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project: Mapped[NovelProject] = relationship(back_populates="chapters")
    versions: Mapped[list["ChapterVersion"]] = relationship(
        "ChapterVersion",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ChapterVersion.created_at",
        primaryjoin="Chapter.id == ChapterVersion.chapter_id",
        foreign_keys="[ChapterVersion.chapter_id]",
    )
    selected_version: Mapped[Optional["ChapterVersion"]] = relationship(
        "ChapterVersion",
        foreign_keys=[selected_version_id],
        primaryjoin="Chapter.selected_version_id == ChapterVersion.id",
        post_update=True,
    )
    evaluations: Mapped[list["ChapterEvaluation"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", order_by="ChapterEvaluation.created_at"
    )
    manga_prompt: Mapped[Optional["ChapterMangaPrompt"]] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", uselist=False
    )


class ChapterVersion(Base):
    """章节生成的不同版本文本。"""

    __tablename__ = "chapter_versions"
    __table_args__ = (
        # 复合索引：用于快速查询章节的最新版本（按创建时间倒序）
        Index('idx_chapter_version_chapter_created', 'chapter_id', 'created_at'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    version_label: Mapped[Optional[str]] = mapped_column(String(64))
    provider: Mapped[Optional[str]] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    metadata = _MetadataAccessor()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    chapter: Mapped[Chapter] = relationship(
        "Chapter",
        back_populates="versions",
        foreign_keys=[chapter_id],
    )
    evaluations: Mapped[list["ChapterEvaluation"]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )


class ChapterEvaluation(Base):
    """章节评估记录。"""

    __tablename__ = "chapter_evaluations"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chapter_versions.id", ondelete="CASCADE"))
    decision: Mapped[Optional[str]] = mapped_column(String(32))
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    score: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    chapter: Mapped[Chapter] = relationship(back_populates="evaluations")
    version: Mapped[Optional[ChapterVersion]] = relationship(back_populates="evaluations")


class CharacterStateIndex(Base):
    """角色状态索引表

    存储每个章节结束时各角色的状态快照，用于RAG检索和状态追踪。
    支持按角色名、章节号、项目ID进行高效查询。
    """

    __tablename__ = "character_state_index"
    __table_args__ = (
        UniqueConstraint("project_id", "chapter_number", "character_name", name="uq_char_state_project_chapter_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    character_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # 状态信息
    location: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[Optional[str]] = mapped_column(Text)
    changes: Mapped[Optional[list]] = mapped_column(JSON)  # 本章发生的变化列表

    # 额外元数据
    emotional_state: Mapped[Optional[str]] = mapped_column(String(64))  # 情绪状态
    relationships_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)  # 关系快照

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ForeshadowingIndex(Base):
    """伏笔索引表

    追踪小说中埋下的伏笔及其回收状态。
    支持按项目、状态、优先级进行查询，用于智能提醒伏笔回收。
    """

    __tablename__ = "foreshadowing_index"
    __table_args__ = (
        # 复合索引：用于快速查询项目的待回收伏笔
        Index('idx_foreshadowing_project_status', 'project_id', 'status'),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False, index=True)

    # 伏笔基本信息
    description: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[Optional[str]] = mapped_column(Text)  # 原文引用
    category: Mapped[str] = mapped_column(String(64), default="plot_twist")  # character_secret/plot_twist/item_mystery/world_rule
    priority: Mapped[str] = mapped_column(String(16), default="medium", index=True)  # high/medium/low

    # 时间线信息
    planted_chapter: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 埋下伏笔的章节
    resolved_chapter: Mapped[Optional[int]] = mapped_column(Integer)  # 回收伏笔的章节
    suggested_resolve_chapter: Mapped[Optional[int]] = mapped_column(Integer)  # 建议回收的章节

    # 状态
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)  # pending/resolved/abandoned
    resolution: Mapped[Optional[str]] = mapped_column(Text)  # 回收方式描述

    # 关联实体
    related_entities: Mapped[Optional[list]] = mapped_column(JSON)  # 关联的角色/物品/地点

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ChapterMangaPrompt(Base):
    """章节漫画提示词

    存储将章节内容转化为专业漫画分镜的完整数据。
    基于专业漫画分镜架构：场景 -> 页面 -> 画格 -> 提示词

    V2架构核心概念：
    - scenes: 叙事场景列表，每个场景包含页面信息
    - panels: 画格提示词列表，每个画格有独立的AI绘图提示词
    - 页面模板系统：8种专业布局适配不同场景情感
    """

    __tablename__ = "chapter_manga_prompts"

    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # 关联的正文版本ID（记录漫画提示词基于哪个版本生成）
    source_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chapter_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # 漫画风格：manga/anime/comic/webtoon
    style: Mapped[str] = mapped_column(String(32), default="manga")

    # 生成状态（用于断点续传）
    # pending: 未开始, extracting: 提取场景中, expanding: 展开场景中,
    # prompting: 生成提示词中, completed: 完成, failed: 失败
    generation_status: Mapped[str] = mapped_column(String(32), default="pending")

    # 生成进度（JSON格式）
    # 格式: {"stage": "expanding", "current": 5, "total": 10, "message": "展开场景 5/10"}
    generation_progress: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    # 断点数据（JSON格式，用于恢复生成）
    # 格式: {
    #   "scenes_data": [...],  # 提取的场景列表
    #   "character_profiles": {...},  # 角色外观
    #   "completed_expansions": [...],  # 已完成展开的场景
    #   "current_scene_index": 5  # 当前处理的场景索引
    # }
    checkpoint_data: Mapped[Optional[dict]] = mapped_column(JSON, default=None)

    # 统计信息
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    total_panels: Mapped[int] = mapped_column(Integer, default=0)

    # 角色外观配置（JSON字典，确保角色在所有画面中外观一致）
    # 格式: {"角色名": "详细的英文外观描述"}
    character_profiles: Mapped[dict] = mapped_column(JSON, default=dict)

    # 场景列表（JSON数组）- V2格式
    # 每个场景包含: scene_id, scene_summary, mood, importance, pages[]
    # pages数组: page_number, template_id, template_name, panel_count
    scenes: Mapped[list] = mapped_column(JSON, default=list)

    # 画格提示词列表（JSON数组）- V2新增
    # 每个画格包含: panel_id, scene_id, page_number, slot_id, aspect_ratio,
    # composition, camera_angle, prompt_en, prompt_zh, negative_prompt,
    # dialogue, dialogue_speaker, narration, sound_effects, characters, is_key_panel
    panels: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chapter: Mapped["Chapter"] = relationship(back_populates="manga_prompt")
