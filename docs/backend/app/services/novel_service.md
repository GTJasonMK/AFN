
# Novel Service - 小说项目服务

## 文件概述

**文件路径**: `backend/app/services/novel_service.py`  
**代码行数**: 781行  
**核心职责**: 小说项目的核心业务逻辑服务，提供项目管理、蓝图管理、章节管理、版本控制、状态机转换等完整功能

## 核心功能

### 1. 状态机管理

使用状态机模式安全地管理项目状态转换：

```python
async def transition_project_status(
    self,
    project: NovelProject,
    new_status: str,
    force: bool = False
) -> None:
    """
    安全地转换项目状态
    
    Args:
        project: 项目实例
        new_status: 目标状态
        force: 是否强制转换（跳过验证）
    
    Raises:
        InvalidStateTransitionError: 非法状态转换
    """
```

**状态转换流程**：
```python
# 正常流程
created → blueprint_generated → chapter_outlines_ready → writing → completed

# 分部分大纲流程（长篇小说）
created → blueprint_generated → part_outlines_ready → chapter_outlines_ready → writing → completed

# 使用示例
novel_service = NovelService(session)
project = await novel_service.ensure_project_owner(project_id, user_id)

# 生成蓝图后更新状态
await novel_service.transition_project_status(
    project, 
    ProjectStatus.BLUEPRINT_GENERATED.value
)

# 强制转换（跳过验证）
await novel_service.transition_project_status(
    project,
    ProjectStatus.WRITING.value,
    force=True
)
```

### 2. 项目管理

#### 创建项目

```python
async def create_project(
    self, 
    user_id: int, 
    title: str, 
    initial_prompt: str
) -> NovelProject
```

**使用示例**：
```python
project = await novel_service.create_project(
    user_id=1,
    title="修仙传奇",
    initial_prompt="一个现代程序员穿越到修仙世界的故事"
)
# 自动创建关联的NovelBlueprint记录
```

#### 权限验证

```python
async def ensure_project_owner(
    self, 
    project_id: str, 
    user_id: int
) -> NovelProject:
    """验证用户是否为项目所有者"""
```

**使用示例**：
```python
try:
    project = await novel_service.ensure_project_owner(project_id, user_id)
    # 继续业务逻辑
except HTTPException as e:
    # 404: 项目不存在
    # 403: 无权访问
    pass
```

#### 项目列表

```python
async def list_projects_for_user(
    self, 
    user_id: int
) -> List[NovelProjectSummary]
```

返回项目摘要列表，包含：
- 基本信息（ID、标题、类型）
- 进度统计（已完成章节数/总章节数）
- 最后编辑时间
- **项目状态**

**使用示例**：
```python
summaries = await novel_service.list_projects_for_user(user_id=1)
for summary in summaries:
    print(f"{summary.title}: {summary.completed_chapters}/{summary.total_chapters} 章")
    print(f"状态: {summary.status}")
```

#### 批量删除项目

```python
async def delete_projects(
    self, 
    project_ids: List[str], 
    user_id: int
) -> None
```

**使用示例**：
```python
await novel_service.delete_projects(
    project_ids=["uuid-1", "uuid-2", "uuid-3"],
    user_id=1
)
await session.commit()
```

### 3. 蓝图管理

#### 完整替换蓝图

```python
async def replace_blueprint(
    self, 
    project_id: str, 
    blueprint: Blueprint
) -> None
```

**操作内容**：
1. 更新 `NovelBlueprint` 主表字段
2. 删除并重建 `BlueprintCharacter` 表
3. 删除并重建 `BlueprintRelationship` 表
4. 删除并重建 `ChapterOutline` 表

**使用示例**：
```python
blueprint = Blueprint(
    title="修仙传奇",
    target_audience="18-35岁玄幻小说爱好者",
    genre="修仙",
    style="轻松幽默",
    tone="积极向上",
    one_sentence_summary="程序员穿越修仙世界，用代码思维修炼成仙",
    full_synopsis="主角张三是一名程序员...",
    world_setting={"时代背景": "修仙世界", "修炼体系": "..."},
    characters=[
        {
            "name": "张三",
            "identity": "穿越者，程序员",
            "personality": "理性、好奇、幽默",
            "goals": "成为修仙界最强者",
            "abilities": "编程思维、快速学习"
        }
    ],
    relationships=[
        {
            "character_from": "张三",
            "character_to": "李四",
            "description": "师徒关系"
        }
    ],
    chapter_outline=[
        {
            "chapter_number": 1,
            "title": "穿越",
            "summary": "程序员张三意外穿越到修仙世界"
        }
    ],
    needs_part_outlines=False,
    total_chapters=100,
    chapters_per_part=25
)

await novel_service.replace_blueprint(project_id, blueprint)
```

#### 部分更新蓝图

```python
async def patch_blueprint(
    self, 
    project_id: str, 
    patch: Dict
) -> None
```

**支持的字段**：
- `one_sentence_summary` - 一句话概括
- `full_synopsis` - 完整概要
- `world_setting` - 世界观设定（增量更新）
- `characters` - 角色列表（完全替换）
- `relationships` - 关系列表（完全替换）
- `chapter_outline` - 章节大纲（完全替换）

**使用示例**：
```python
# 仅更新概要
await novel_service.patch_blueprint(
    project_id,
    {
        "one_sentence_summary": "新的一句话概括",
        "full_synopsis": "更新后的完整概要"
    }
)

# 更新世界观（增量）
await novel_service.patch_blueprint(
    project_id,
    {
        "world_setting": {
            "新增设定": "新内容"
        }
    }
)

# 更新角色列表（完全替换）
await novel_service.patch_blueprint(
    project_id,
    {
        "characters": [
            {"name": "新角色", "identity": "主角"}
        ]
    }
)
```

### 4. 对话管理

#### 追加对话记录

```python
async def append_conversation(
    self, 
    project_id: str, 
    role: str, 
    content: str, 
    metadata: Optional[Dict] = None
) -> None
```

**使用示例**：
```python
# 记录用户输入
await novel_service.append_conversation(
    project_id=project_id,
    role="user",
    content="请生成第一章的内容"
)

# 记录AI响应
await novel_service.append_conversation(
    project_id=project_id,
    role="assistant",
    content="第一章内容...",
    metadata={"model": "gpt-4", "tokens": 2000}
)
```

#### 获取对话历史

```python
async def list_conversations(
    self, 
    project_id: str
) -> List[NovelConversation]
```

**使用示例**：
```python
conversations = await novel_service.list_conversations(project_id)
for conv in conversations:
    print(f"[{conv.role}] {conv.content[:50]}...")
```

### 5. 章节与版本管理

#### 获取或创建章节

```python
async def get_or_create_chapter(
    self, 
    project_id: str, 
    chapter_number: int
) -> Chapter
```

**使用示例**：
```python
# 如果章节不存在则自动创建
chapter = await novel_service.get_or_create_chapter(
    project_id=project_id,
    chapter_number=1
)
```

#### 替换章节版本

```python
async def replace_chapter_versions(
    self, 
    chapter: Chapter, 
    contents: List[str], 
    metadata: Optional[List[Dict]] = None
) -> List[ChapterVersion]
```

**功能说明**：
- 删除章节的所有旧版本
- 批量创建新版本
- 自动标记版本号（v1, v2, v3...）
- 更新章节状态为 `WAITING_FOR_CONFIRM`
- 支持内容标准化处理

**使用示例**：
```python
# 并行生成3个版本
contents = [
    "第一章版本1的内容...",
    "第一章版本2的内容...",
    "第一章版本3的内容..."
]

metadata = [
    {"temperature": 0.7, "model": "gpt-4"},
    {"temperature": 0.8, "model": "gpt-4"},
    {"temperature": 0.9, "model": "gpt-4"}
]

versions = await novel_service.replace_chapter_versions(
    chapter=chapter,
    contents=contents,
    metadata=metadata
)
```

**内容标准化处理**：

[`_normalize_version_content()`](backend/app/services/novel_service.py:22) 函数处理LLM返回的多种格式：

```python
# 支持的内容格式：
# 1. 纯字符串
content = "第一章内容..."

# 2. JSON字符串
content = '{"content": "第一章内容..."}'

# 3. 嵌套字典
content = {
    "chapter_content": "第一章内容...",
    "metadata": {...}
}

# 4. 列表形式
content = ["段落1", "段落2", "段落3"]

# 所有格式都会被标准化为纯字符串
normalized = _normalize_version_content(raw_content, metadata)
```

#### 选择章节版本

```python
async def select_chapter_version(
    self, 
    chapter: Chapter, 
    version_index: int
) -> ChapterVersion
```

**使用示例**：
```python
# 用户选择第2个版本（索引1）
selected = await novel_service.select_chapter_version(
    chapter=chapter,
    version_index=1
)

# 章节状态自动更新为SUCCESSFUL
# selected_version_id指向该版本
# word_count自动计算
```

#### 添加章节评价

```python
async def add_chapter_evaluation(
    self, 
    chapter: Chapter, 
    version: Optional[ChapterVersion], 
    feedback: str, 
    decision: Optional[str] = None
) -> None
```

**使用示例**：
```python
# 用户对版本的评价
await novel_service.add_chapter_evaluation(
    chapter=chapter,
    version=selected_version,
    feedback="节奏太快，需要更多细节描写",
    decision="retry"
)

# 章节状态回到WAITING_FOR_CONFIRM
```

#### 删除章节

```python
async def delete_chapters(
    self, 
    project_id: str, 
    chapter_numbers: Iterable[int]
) -> None
```

**同时删除**：
- `Chapter` 记录（级联删除版本和评价）
- `ChapterOutline` 记录

**使用示例**：
```python
# 删除第5-10章
await novel_service.delete_chapters(
    project_id=project_id,
    chapter_numbers=[5, 6, 7, 8, 9, 10]
)
```

### 6. 数据序列化

#### 完整项目序列化

```python
async def get_project_schema(
    self, 
    project_id: str, 
    user_id: int
) -> NovelProjectSchema
```

返回包含所有关联数据的完整项目信息：
- 基本信息
- 对话历史
- 完整蓝图（包括角色、关系、章节大纲、部分大纲）
- 所有章节（包括版本和评价）

**使用示例**：
```python
schema = await novel_service.get_project_schema(project_id, user_id)

# 访问蓝图
print(schema.blueprint.title)
print(schema.blueprint.characters)

# 访问章节
for chapter in schema.chapters:
    print(f"第{chapter.chapter_number}章: {chapter.title}")
    if chapter.content:
        print(f"已选择版本，字数: {chapter.word_count}")
    if chapter.versions:
        print(f"共有 {len(chapter.versions)} 个版本")
```

#### 按区域获取数据

```python
async def get_section_data(
    self,
    project_id: str,
    user_id: int,
    section: NovelSectionType,
) -> NovelSectionResponse
```

**支持的区域**：
- `OVERVIEW` - 项目概览
- `WORLD_SETTING` - 世界观设定
- `CHARACTERS` - 角色列表
- `RELATIONSHIPS` - 关系列表
- `CHAPTER_OUTLINE` - 章节大纲（含部分大纲）
- `CHAPTERS` - 章节列表（不含完整内容）

**使用示例**：
```python
# 获取项目概览
overview = await novel_service.get_section_data(
    project_id, user_id, NovelSectionType.OVERVIEW
)
print(overview.data["title"])
print(overview.data["status"])

# 获取角色列表
characters = await novel_service.get_section_data(
    project_id, user_id, NovelSectionType.CHARACTERS
)
for char in characters.data["characters"]:
    