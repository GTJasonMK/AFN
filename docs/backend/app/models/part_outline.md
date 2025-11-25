# backend/app/models/part_outline.py - 部分大纲模型

## 文件概述

定义小说部分大纲（Part Outline）的数据模型，用于长篇小说的分层大纲结构。将整部小说分成多个部分，每个部分包含若干章节，便于管理超长篇幅的作品。

**文件路径：** `backend/app/models/part_outline.py`  
**代码行数：** 49 行  
**复杂度：** ⭐⭐⭐ 中等

## 数据模型定义

### PartOutline 类

```python
class PartOutline(Base):
    """小说部分大纲表（用于长篇小说的分层大纲结构）"""
    
    __tablename__ = "part_outlines"
    
    # 主键和外键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id", ondelete="CASCADE"), 
        nullable=False
    )
    part_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 部分信息
    title: Mapped[Optional[str]] = mapped_column(String(255))
    start_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    end_chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    theme: Mapped[Optional[str]] = mapped_column(String(500))
    
    # JSON字段存储复杂数据
    key_events: Mapped[Optional[list]] = mapped_column(JSON)
    character_arcs: Mapped[Optional[dict]] = mapped_column(JSON)
    conflicts: Mapped[Optional[list]] = mapped_column(JSON)
    ending_hook: Mapped[Optional[str]] = mapped_column(Text)
    
    # 状态和时间戳
    generation_status: Mapped[str] = mapped_column(String(50), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

## 字段详解

### 基础字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `String(36)` | UUID，部分大纲唯一标识 |
| `project_id` | `String(36)` | 所属项目ID |
| `part_number` | `Integer` | 部分序号（第1部、第2部） |

### 部分信息

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | `String(255)` | 部分标题 |
| `start_chapter` | `Integer` | 起始章节号 |
| `end_chapter` | `Integer` | 结束章节号 |
| `summary` | `Text` | 部分摘要 |
| `theme` | `String(500)` | 部分主题 |

### JSON复杂数据

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `key_events` | `JSON (list)` | 关键事件列表 | `["主角突破境界", "与反派初次交锋"]` |
| `character_arcs` | `JSON (dict)` | 角色成长弧线 | `{"李明": "从懦弱到勇敢", "王芳": "从自私到无私"}` |
| `conflicts` | `JSON (list)` | 主要冲突列表 | `["正邪对决", "内心挣扎"]` |
| `ending_hook` | `Text` | 与下一部分的衔接点 | "主角发现了神秘线索..." |

### 状态字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `generation_status` | `String(50)` | "pending" | 生成状态 |
| `progress` | `Integer` | 0 | 进度（0-100） |

**状态值：**
- `pending`: 待生成
- `generating`: 生成中
- `completed`: 已完成
- `failed`: 生成失败

## 使用场景

### 1. 长篇小说结构

**问题：** 小说超过100章时，大纲难以管理

**解决方案：** 使用部分大纲分层管理

```
小说项目（500章）
├── 第一部：初入江湖（1-100章）
├── 第二部：修炼历程（101-200章）
├── 第三部：成长蜕变（201-300章）
├── 第四部：巅峰对决（301-400章）
└── 第五部：终极篇章（401-500章）
```

### 2. 数据示例

```python
part_outline = PartOutline(
    id="uuid-1234",
    project_id="novel-uuid",
    part_number=1,
    title="第一部：初入江湖",
    start_chapter=1,
    end_chapter=100,
    summary="主角从普通人成长为修炼者的过程",
    theme="成长与探索",
    key_events=[
        "主角获得奇遇",
        "拜入门派",
        "初次遇到反派",
        "学会第一个功法"
    ],
    character_arcs={
        "李明（主角）": "从懦弱新手成长为自信修炼者",
        "张师傅": "从严师形象转变为亦师亦友",
        "林雪": "从陌生人到好友"
    },
    conflicts=[
        "主角与世俗观念的冲突",
        "门派内部的竞争",
        "与邪派弟子的对抗"
    ],
    ending_hook="主角发现师傅隐藏的秘密，为第二部埋下伏笔",
    generation_status="completed",
    progress=100
)
```

## 使用示例

### 1. 创建部分大纲

```python
from backend.app.models.part_outline import PartOutline
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

async def create_part_outline(
    session: AsyncSession,
    project_id: str,
    part_number: int,
    start_chapter: int,
    end_chapter: int
) -> PartOutline:
    """创建新的部分大纲"""
    part = PartOutline(
        id=str(uuid.uuid4()),
        project_id=project_id,
        part_number=part_number,
        title=f"第{part_number}部",
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        generation_status="pending",
        progress=0
    )
    session.add(part)
    await session.commit()
    await session.refresh(part)
    return part
```

### 2. 查询项目的所有部分

```python
from sqlalchemy import select

async def list_part_outlines(
    session: AsyncSession,
    project_id: str
) -> list[PartOutline]:
    """查询项目的所有部分大纲"""
    result = await session.execute(
        select(PartOutline)
        .where(PartOutline.project_id == project_id)
        .order_by(PartOutline.part_number)
    )
    return result.scalars().all()
```

### 3. 更新部分大纲内容

```python
async def update_part_content(
    session: AsyncSession,
    part_id: str,
    **updates
) -> PartOutline:
    """更新部分大纲内容"""
    part = await session.get(PartOutline, part_id)
    
    for key, value in updates.items():
        if hasattr(part, key):
            setattr(part, key, value)
    
    await session.commit()
    await session.refresh(part)
    return part
```

**使用示例：**
```python
await update_part_content(
    session,
    part_id="uuid-1234",
    summary="更新后的摘要",
    key_events=["事件1", "事件2", "事件3"],
    character_arcs={"李明": "成长描述"},
    progress=50,
    generation_status="generating"
)
```

### 4. 生成部分大纲

```python
async def generate_part_outline(
    session: AsyncSession,
    part_id: str,
    llm_service: LLMService
) -> PartOutline:
    """使用AI生成部分大纲"""
    part = await session.get(PartOutline, part_id)
    
    # 更新状态
    part.generation_status = "generating"
    part.progress = 10
    await session.commit()
    
    try:
        # 调用LLM生成
        prompt = f"""
        为第{part.part_number}部（第{part.start_chapter}-{part.end_chapter}章）
        生成详细的部分大纲...
        """
        
        response = await llm_service.chat(prompt)
        
        # 解析响应并更新
        part.summary = response.get("summary")
        part.key_events = response.get("key_events", [])
        part.character_arcs = response.get("character_arcs", {})
        part.conflicts = response.get("conflicts", [])
        part.ending_hook = response.get("ending_hook")
        part.generation_status = "completed"
        part.progress = 100
        
    except Exception as e:
        part.generation_status = "failed"
        part.progress = 0
    
    await session.commit()
    await session.refresh(part)
    return part
```

## 数据库表结构

### 表定义

```sql
CREATE TABLE part_outlines (
    id VARCHAR(36) PRIMARY KEY,
    project_id VARCHAR(36) NOT NULL,
    part_number INTEGER NOT NULL,
    title VARCHAR(255),
    start_chapter INTEGER NOT NULL,
    end_chapter INTEGER NOT NULL,
    summary TEXT,
    theme VARCHAR(500),
    key_events JSON,
    character_arcs JSON,
    conflicts JSON,
    ending_hook TEXT,
    generation_status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES novel_projects(id) ON DELETE CASCADE
);

CREATE INDEX ix_part_outlines_project_id ON part_outlines(project_id);
CREATE INDEX ix_part_outlines_part_number ON part_outlines(part_number);
```

## 与NovelProject的关系

```python
# NovelProject中的关系定义
class NovelProject(Base):
    part_outlines: Mapped[list["PartOutline"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="PartOutline.part_number"
    )
```

**关系类型：** 一对多（One-to-Many）

```
NovelProject (1) ←──────→ (N) PartOutline
```

## 业务逻辑

### 1. 自动分部

```python
async def auto_create_parts(
    session: AsyncSession,
    project_id: str,
    total_chapters: int,
    chapters_per_part: int = 100
) -> list[PartOutline]:
    """自动创建部分大纲"""
    parts = []
    part_number = 1
    
    for start in range(1, total_chapters + 1, chapters_per_part):
        end = min(start + chapters_per_part - 1, total_chapters)
        
        part = PartOutline(
            id=str(uuid.uuid4()),
            project_id=project_id,
            part_number=part_number,
            title=f"第{part_number}部",
            start_chapter=start,
            end_chapter=end
        )
        session.add(part)
        parts.append(part)
        part_number += 1
    
    await session.commit()
    return parts
```

### 2. 验证章节范围

```python
def validate_chapter_range(parts: list[PartOutline]) -> bool:
    """验证部分大纲的章节范围是否连续"""
    sorted_parts = sorted(parts, key=lambda p: p.part_number)
    
    for i in range(len(sorted_parts) - 1):
        current = sorted_parts[i]
        next_part = sorted_parts[i + 1]
        
        # 检查是否连续
        if current.end_chapter + 1 != next_part.start_chapter:
            return False
    
    return True
```

### 3. 获取章节所属部分

```python
async def get_part_by_chapter(
    session: AsyncSession,
    project_id: str,
    chapter_number: int
) -> Optional[PartOutline]:
    """根据章节号获取所属部分"""
    result = await session.execute(
        select(PartOutline)
        .where(
            PartOutline.project_id == project_id,
            PartOutline.start_chapter <= chapter_number,
            PartOutline.end_chapter >= chapter_number
        )
    )
    return result.scalar_one_or_none()
```

## 相关文件

### 数据模型
- [`backend/app/models/novel.py`](novel.md) - 小说项目模型
- [`backend/app/models/user.py`](user.md) - 用户模型

### 服务层
- `backend/app/services/part_outline_service.py` - 部分大纲服务

### API路由
- `backend/app/api/routers/novels.py` - 包含部分大纲相关接口

## 注意事项

### 1. 章节范围验证

⚠️ **确保章节范围不重叠**

```python
# ❌ 错误：范围重叠
Part 1: chapters 1-100
Part 2: chapters 95-200  # 与Part 1重叠

# ✅ 正确：连续不重叠
Part 1: chapters 1-100
Part 2: chapters 101-200
```

### 2. JSON字段处理

```python
# ✅ 正确：确保JSON字段类型
part.key_events = ["事件1", "事件2"]  # list
part.character_arcs = {"角色": "描述"}  # dict
part.conflicts = ["冲突1"]  # list

# ❌ 错误：类型不匹配
part.key_events = "事件1,事件2"  # 应该是list
```

### 3. 状态管理

```python
# 状态转换流程
pending → generating → completed/failed

# ✅ 正确的状态更新
part.generation_status = "generating"
part.progress = 10
# ...执行生成...
part.generation_status = "completed"
part.progress = 100
```

## 总结

`PartOutline` 模型是长篇小说管理的关键组件：

**核心价值：**
1. ✅ 分层管理长篇小说结构
2. ✅ 存储部分级别的大纲信息
3. ✅ 支持复杂的JSON数据结构
4. ✅ 跟踪生成状态和进度

**适用场景：**
- 超过100章的长篇小说
- 需要分部创作的作品
- 复杂的多线叙事结构

---

**文档版本：** v1.0.0  
**最后更新：** 2025-11-06