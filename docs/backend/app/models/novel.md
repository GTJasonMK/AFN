
# backend/app/models/novel.py - 小说项目数据模型

## 文件概述

定义小说项目的完整数据模型，包含9个相互关联的表，覆盖从概念设计、蓝图规划、角色设定、章节大纲到正文创作的整个生命周期。这是整个系统最核心的数据结构。

**文件路径：** `backend/app/models/novel.py`  
**代码行数：** 235 行  
**复杂度：** ⭐⭐⭐⭐⭐ 非常复杂

## 数据模型架构

### 模型关系图

```
User
  ↓
NovelProject (项目主表)
  ├─→ NovelConversation (概念对话)
  ├─→ NovelBlueprint (蓝图信息)
  ├─→ BlueprintCharacter (角色设定)
  ├─→ BlueprintRelationship (角色关系)
  ├─→ PartOutline (部分大纲)
  ├─→ ChapterOutline (章节大纲)
  └─→ Chapter (章节)
       ├─→ ChapterVersion (章节版本)
       └─→ ChapterEvaluation (章节评估)
```

### 9个核心模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `NovelProject` | `novel_projects` | 项目主表 |
| `NovelConversation` | `novel_conversations` | 概念阶段对话 |
| `NovelBlueprint` | `novel_blueprints` | 蓝图主体信息 |
| `BlueprintCharacter` | `blueprint_characters` | 角色信息 |
| `BlueprintRelationship` | `blueprint_relationships` | 角色关系 |
| `ChapterOutline` | `chapter_outlines` | 章节大纲 |
| `Chapter` | `chapters` | 章节正文 |
| `ChapterVersion` | `chapter_versions` | 章节版本 |
| `ChapterEvaluation` | `chapter_evaluations` | 章节评估 |

## 模型详解

### 1. NovelProject - 项目主表

```python
class NovelProject(Base):
    """小说项目主表，仅存放轻量级元数据。"""
    
    __tablename__ = "novel_projects"
    
    # 主键和外键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # 基本信息
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    initial_prompt: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.DRAFT.value)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | UUID，项目唯一标识 |
| `user_id` | `Integer` | 所属用户ID |
| `title` | `String(255)` | 项目标题 |
| `initial_prompt` | `Text` | 初始创作想法 |
| `status` | `String(32)` | 项目状态（draft/blueprint_ready等） |

**关系映射：**
```python
owner: Mapped["User"] = relationship("User", back_populates="novel_projects")
blueprint: Mapped[Optional["NovelBlueprint"]] = relationship(back_populates="project", cascade="all, delete-orphan", uselist=False)
conversations: Mapped[list["NovelConversation"]] = relationship(back_populates="project", cascade="all, delete-orphan")
characters: Mapped[list["BlueprintCharacter"]] = relationship(back_populates="project", cascade="all, delete-orphan")
relationships_: Mapped[list["BlueprintRelationship"]] = relationship(back_populates="project", cascade="all, delete-orphan")
outlines: Mapped[list["ChapterOutline"]] = relationship(back_populates="project", cascade="all, delete-orphan")
chapters: Mapped[list["Chapter"]] = relationship(back_populates="project", cascade="all, delete-orphan")
part_outlines: Mapped[list["PartOutline"]] = relationship(back_populates="project", cascade="all, delete-orphan")
```

### 2. NovelConversation - 概念对话

```python
class NovelConversation(Base):
    """对话记录表，存储概念阶段的连续对话。"""
    
    __tablename__ = "novel_conversations"
    
    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**用途：** 存储概念设计阶段用户与AI的对话历史

**字段说明：**
- `seq`: 对话序号，确保顺序
- `role`: 角色（user/assistant/system）
- `content`: 对话内容
- `metadata_`: 附加元数据（tokens、模型等）

### 3. NovelBlueprint - 蓝图信息

```python
class NovelBlueprint(Base):
    """蓝图主体信息（标题、风格等）。"""
    
    __tablename__ = "novel_blueprints"
    
    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id", ondelete="CASCADE"), 
        primary_key=True
    )
    
    # 基本信息
    title: Mapped[Optional[str]] = mapped_column(String(255))
    target_audience: Mapped[Optional[str]] = mapped_column(String(255))
    genre: Mapped[Optional[str]] = mapped_column(String(128))
    style: Mapped[Optional[str]] = mapped_column(String(128))
    tone: Mapped[Optional[str]] = mapped_column(String(128))
    
    # 故事概要
    one_sentence_summary: Mapped[Optional[str]] = mapped_column(Text)
    full_synopsis: Mapped[Optional[str]] = mapped_column(LONG_TEXT_TYPE)
    
    # 世界观设定
    world_setting: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    
    # 大纲配置
    needs_part_outlines: Mapped[bool] = mapped_column(Boolean, default=False)
    total_chapters: Mapped[Optional[int]] = mapped_column(Integer)
    chapters_per_part: Mapped[int] = mapped_column(Integer, default=25)
```

**关系：** 一个项目对应一个蓝图（一对一）

**字段说明：**
- `genre`: 类型（玄幻、都市、科幻等）
- `style`: 风格（轻松、严肃等）
- `tone`: 语气（幽默、严谨等）
- `world_setting`: JSON格式的世界观设定
- `needs_part_outlines`: 是否需要分部大纲
- `chapters_per_part`: 每部分章节数

### 4. BlueprintCharacter - 角色信息

```python
class BlueprintCharacter(Base):
    """蓝图角色信息。"""
    
    __tablename__ = "blueprint_characters"
    
    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    identity: Mapped[Optional[str]] = mapped_column(String(255))
    personality: Mapped[Optional[str]] = mapped_column(Text)
    goals: Mapped[Optional[str]] = mapped_column(Text)
    abilities: Mapped[Optional[str]] = mapped_column(Text)
    relationship_to_protagonist: Mapped[Optional[str]] = mapped_column(Text)
    extra: Mapped[Optional[dict]] = mapped_column(JSON)
    position: Mapped[int] = mapped_column(Integer, default=0)
```

**用途：** 存储小说中的角色设定

**字段说明：**
- `name`: 角色名称
- `identity`: 身份（主角、配角等）
- `personality`: 性格特点
- `goals`: 目标动机
- `abilities`: 能力特长
- `relationship_to_protagonist`: 与主角的关系
- `position`: 排序位置

### 5. BlueprintRelationship - 角色关系

```python
class BlueprintRelationship(Base):
    """角色之间的关系。"""
    
    __tablename__ = "blueprint_relationships"
    
    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False)
    
    character_from: Mapped[str] = mapped_column(String(255), nullable=False)
    character_to: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
```

**用途：** 描述角色之间的关系网络

**示例：**
- character_from: "李明"
- character_to: "王芳"
- description: "师徒关系，李明是王芳的师父"

### 6. ChapterOutline - 章节大纲

```python
class ChapterOutline(Base):
    """章节纲要。"""
    
    __tablename__ = "chapter_outlines"
    __table_args__ = (
        UniqueConstraint('project_id', 'chapter_number', name='uq_project_chapter'),
    )
    
    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
```

**约束：** `(project_id, chapter_number)` 唯一，确保每个项目的章节号不重复

**字段说明：**
- `chapter_number`: 章节序号
- `title`: 章节标题
- `summary`: 章节摘要/大纲

### 7. Chapter - 章节正文

```python
class Chapter(Base):
    """章节正文状态，指向选中的版本。"""
    
    __tablename__ = "chapters"
    
    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id", ondelete="CASCADE"), nullable=False)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False)
    real_summary: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="not_generated")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    selected_version_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("chapter_versions.id", ondelete="SET NULL"), 
        nullable=True
    )
```

**设计理念：** 章节本身只是一个"指针"，指向选中的版本

**字段说明：**
- `real_summary`: 实际写出的内容摘要
- `status`: 状态（not_generated/generating/generated等）
- `word_count`: 字数统计
- `selected_version_id`: 当前选中的版本ID

**关系映射：**
```python
versions: Mapped[list["ChapterVersion"]] = relationship(
    "ChapterVersion",
    back_populates="chapter",
    cascade="all, delete-orphan",
    order_by="ChapterVersion.created_at"
)
selected_version: Mapped[Optional["ChapterVersion"]] = relationship(
    "ChapterVersion",
    foreign_keys=[selected_version_id],
    post_update=True,
)
evaluations: Mapped[list["ChapterEvaluation"]] = relationship(
    back_populates="chapter", 
    cascade="all, delete-orphan"
)
```

### 8. ChapterVersion - 章节版本

```python
class ChapterVersion(Base):
    """章节生成的不同版本文本。"""
    
    __tablename__ = "chapter_versions"
    
    id: Mapped[int] = mapped_column(BIGINT_PK_TYPE, primary_key=True, autoincrement=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    version_label: Mapped[Optional[str]] = mapped_column(String(64))
    provider: Mapped[Optional[str]] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(LONG_TEXT_TYPE, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**用途：** 存储AI生成的多个版本，用户可以选择最佳版本

**字段说明：**
- `version_label`: 版本标签（"版本1"、"版本2"）
- `provider`: 生成模型（"gpt-4"、"claude-3"）
- `content`: 章节正文内容
- `metadata_`: 生成参数、tokens等元数据

### 9. ChapterEvaluation - 章节评估

```python
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
```

**用途：** 记录AI或用户对章节的评估

**字段说明：**
- `version_id`: 评估的版本ID（可选）
- `decision`: 决策（accept/revise/reject）
- `feedback`: 评估反馈
- `score`: 评分

## 技术特性

### 1. 跨数据库兼容

```python
# 自定义列类型
BIGINT_PK_TYPE = BigInteger().with_variant(Integer, "sqlite")
LONG_TEXT_TYPE = Text().with_variant(LONGTEXT, "mysql")
```

**说明：**
- SQLite 使用 `Integer`，MySQL 使用 `BigInteger`
- SQLite 使用 `Text`，MySQL 使用 `LONGTEXT`

### 2. metadata 字段处理

```python
class _MetadataAccessor:
    """Descriptor 用于将 `metadata` 访问重定向到 `metadata_`"""
    
    def __get__(self, instance, owner):
        if instance is None:
            return Base.metadata
        return instance.metadata_
    
    def __set__(self, instance, value):
        instance.metadata_ = value
```

**原因：** `metadata` 是 SQLAlchemy 的保留属性，需要特殊处理

**使用：**
```python
conversation.metadata_ = {"tokens": 150}  # 直接赋值
print(conversation.metadata)  # 通过 descriptor 访问
```

### 3. 级联删除

