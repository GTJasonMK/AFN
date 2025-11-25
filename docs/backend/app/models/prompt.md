
# backend/app/models/prompt.py - 提示词模型

## 文件概述

定义提示词（Prompt）的数据模型，用于存储和管理 AI 对话中使用的各种提示词模板。提示词是指导 AI 生成内容的核心，包括概念设计、大纲生成、章节写作等不同场景的模板。

**文件路径：** `backend/app/models/prompt.py`  
**代码行数：** 25 行  
**复杂度：** ⭐ 简单

## 数据模型定义

### Prompt 类

```python
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

class Prompt(Base):
    """提示词表，支持后台 CRUD 操作。"""
    
    __tablename__ = "prompts"
    
    # 主键
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(String(255))
    
    # 时间戳
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now()
    )
```

## 字段详解

### 主键

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | `Integer` | 主键，自增 | 提示词唯一标识符 |

### 基本信息

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `name` | `String(100)` | 唯一，非空，索引 | 提示词名称（标识符） |
| `title` | `String(255)` | 可选 | 提示词标题（显示名称） |
| `content` | `Text` | 非空 | 提示词内容（模板文本） |
| `tags` | `String(255)` | 可选 | 标签（逗号分隔） |

**字段说明：**

**name：**
- 提示词的唯一标识符
- 通常使用英文命名
- 例如：`concept`、`outline`、`writing`

**title：**
- 提示词的显示标题
- 用于前端展示
- 例如："概念设计"、"大纲生成"

**content：**
- 提示词的完整内容
- 使用 Markdown 格式
- 支持占位符（如 `{title}`、`{genre}`）

**tags：**
- 提示词的分类标签
- 逗号分隔多个标签
- 例如："创作,大纲"

### 时间戳

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `created_at` | `DateTime(TZ)` | 非空 | 创建时间 |
| `updated_at` | `DateTime(TZ)` | 非空 | 最后更新时间 |

**自动管理：**
- `created_at`：创建时自动设置
- `updated_at`：每次更新时自动更新

## 数据库表结构

### 表定义

```sql
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    title VARCHAR(255),
    content TEXT NOT NULL,
    tags VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_prompts_name ON prompts(name);
```

### 索引

| 索引名 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| `PRIMARY` | `id` | 主键 | 唯一标识 |
| `ix_prompts_name` | `name` | 唯一索引 | 快速查找 |

## 默认提示词

应用初始化时会自动加载 `backend/prompts/` 目录下的提示词文件：

### 提示词文件列表

| 文件名 | name | 用途 |
|--------|------|------|
| `concept.md` | concept | 概念设计阶段的对话引导 |
| `evaluation.md` | evaluation | 章节内容评估 |
| `extraction.md` | extraction | 从对话中提取信息 |
| `outline.md` | outline | 生成章节大纲 |
| `part_outline.md` | part_outline | 生成部分大纲 |
| `screenwriting.md` | screenwriting | 剧本式写作 |
| `writing.md` | writing | 章节正文写作 |

### 加载流程

```python
# backend/app/db/init_db.py

async def _ensure_default_prompts(session: AsyncSession) -> None:
    """加载默认提示词"""
    prompts_dir = Path(__file__).resolve().parents[2] / "prompts"
    
    # 获取已存在的提示词
    result = await session.execute(select(Prompt.name))
    existing_names = set(result.scalars().all())
    
    # 遍历 .md 文件
    for prompt_file in sorted(prompts_dir.glob("*.md")):
        name = prompt_file.stem  # 文件名（不含扩展名）
        if name in existing_names:
            continue
        
        # 读取文件内容
        content = prompt_file.read_text(encoding="utf-8")
        
        # 创建提示词记录
        session.add(Prompt(name=name, content=content))
```

## 使用示例

### 1. 创建提示词

```python
from backend.app.models.prompt import Prompt
from sqlalchemy.ext.asyncio import AsyncSession

async def create_prompt(
    session: AsyncSession,
    name: str,
    content: str,
    title: str = None,
    tags: str = None
) -> Prompt:
    """创建新提示词"""
    prompt = Prompt(
        name=name,
        title=title,
        content=content,
        tags=tags
    )
    session.add(prompt)
    await session.commit()
    await session.refresh(prompt)
    return prompt
```

**示例：**
```python
prompt = await create_prompt(
    session,
    name="custom_writing",
    title="自定义写作模板",
    content="你是一位专业的小说作家...",
    tags="创作,写作"
)
```

### 2. 查询提示词

```python
from sqlalchemy import select

async def get_prompt_by_name(
    session: AsyncSession, 
    name: str
) -> Optional[Prompt]:
    """根据名称查询提示词"""
    result = await session.execute(
        select(Prompt).where(Prompt.name == name)
    )
    return result.scalar_one_or_none()

async def list_all_prompts(session: AsyncSession) -> list[Prompt]:
    """获取所有提示词"""
    result = await session.execute(
        select(Prompt).order_by(Prompt.name)
    )
    return result.scalars().all()

async def search_prompts_by_tag(
    session: AsyncSession, 
    tag: str
) -> list[Prompt]:
    """根据标签搜索提示词"""
    result = await session.execute(
        select(Prompt).where(Prompt.tags.like(f"%{tag}%"))
    )
    return result.scalars().all()
```

### 3. 更新提示词

```python
async def update_prompt(
    session: AsyncSession,
    prompt_id: int,
    **updates
) -> Prompt:
    """更新提示词"""
    prompt = await session.get(Prompt, prompt_id)
    
    for key, value in updates.items():
        if hasattr(prompt, key) and key != 'id':
            setattr(prompt, key, value)
    
    await session.commit()
    await session.refresh(prompt)
    return prompt
```

**示例：**
```python
prompt = await update_prompt(
    session,
    prompt_id=1,
    content="更新后的提示词内容",
    tags="创作,大纲,更新"
)
```

### 4. 删除提示词

```python
async def delete_prompt(session: AsyncSession, prompt_id: int):
    """删除提示词"""
    prompt = await session.get(Prompt, prompt_id)
    await session.delete(prompt)
    await session.commit()
```

## 提示词模板格式

### 基本结构

```markdown
# 角色定义
你是一位{角色描述}...

# 任务说明
请根据以下信息{任务描述}...

# 输入信息
- 标题：{title}
- 类型：{genre}
- 风格：{style}

# 输出要求
1. {要求1}
2. {要求2}

# 示例
{示例内容}
```

### 占位符使用

提示词中可以使用占位符，在实际使用时替换：

```python
# 提示词内容
content = """
请为小说《{title}》生成第{chapter_number}章的内容。

类型：{genre}
风格：{style}
章节大纲：{outline}
"""

# 使用时替换占位符
filled_prompt = content.format(
    title="修仙传",
    chapter_number=1,
    genre="玄幻",
    style="轻松",
    outline="主角进入宗门..."
)
```

## 提示词服务

### PromptService 类

```python
# backend/app/services/prompt_service.py

class PromptService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, str] = {}
    
    async def preload(self):
        """预加载所有提示词到缓存"""
        result = await self.session.execute(select(Prompt))
        prompts = result.scalars().all()
        
        for prompt in prompts:
            self._cache[prompt.name] = prompt.content
    
    def get(self, name: str, **kwargs) -> str:
        """获取提示词并填充占位符"""
        template = self._cache.get(name, "")
        return template.format(**kwargs)
```

### 使用提示词服务

```python
from backend.app.services.prompt_service import PromptService

# 初始化服务
prompt_service = PromptService(session)
await prompt_service.preload()

# 获取提示词
writing_prompt = prompt_service.get(
    "writing",
    title="修仙传",
    chapter_number=1,
    outline="主角进入宗门..."
)

# 调用 LLM
response = await llm_service.chat(writing_prompt)
```

## 实际提示词示例

### 1. 概念设计提示词（concept.md）

```markdown
# 角色
你是一位经验丰富的小说策划师。

# 任务
协助用户从初步想法发展出完整的小说概念。

# 对话流程
1. 询问小说的核心idea
2. 探讨类型、风格、受众
3. 讨论主要角色和故事线
4. 确定世界观设定

# 输出
最终输出一份包含以下要素的蓝图：
- 标题
- 目标受众
- 类型和风格
- 一句话概要
- 完整梗概
```

### 2. 写作提示词（writing.md）

```markdown
# 角色
你是一位专业小说作家。

# 任务
根据提供的章节大纲，创作完整的章节内容。

# 输入信息
- 小说标题：{title}
- 类型：{genre}
- 风格：{style}
- 章节号：{chapter_number}
- 章节大纲：{outline}
- 前文摘要：{context}

# 写作要求
1. 保持风格一致
2. 字数控制在 {word_count} 字左右
3. 注意情节连贯性
4. 人物性格要鲜明

# 输出格式
纯文本，不要添加额外说明。
```

### 3. 评估提示词（evaluation.md）

```markdown
# 角色
你是一位资深小说编辑。

# 任务
评估章节内容的质量，提供修改建议。

# 评估维度
1. 情节完整性（1-10分）
2. 文字流畅度（1-10分）
3. 人物刻画（1-10分）
4. 氛围营造（1-10分）

# 输出格式
{
  "scores": {
    "plot": 8,
    "writing": 9,
    "character": 7,
    "atmosphere": 8
  },
  "feedback": "具体评价和建议...",
  "decision": "accept/revise/reject"
}
```

## 提示词管理API

虽然当前版本可能没有完整的管理界面，但可以通过服务层管理提示词：

```python
class PromptService:
    async def create(self, data: PromptCreate) -> Prompt:
        """创建提示词"""
        pass
    
    async def update(self, prompt_id: int, data: PromptUpdate) -> Prompt:
        """更新提示词"""
        pass
    
    async def delete(self, prompt_id: int):
        """删除提示词"""
        pass
    
    async def list_all(self) -> list[Prompt]:
        """列出所有提示词"""
        pass
    
    async def get_by_name(self, name: str) -> Prompt:
        """根据名称获取"""
        pass
```

## 相关文件

### 服务层
- [`backend/app/services/prompt_service.py`](../services/prompt_service.md) - 提示词服务
- [`backend/app/services/llm_service.py`](../services/llm_service.md) - LLM 调用服务

### 提示词文件
- `backend/prompts/concept.md` - 概念设计
- `backend/prompts/outline.md` - 大纲生成
- `backend/prompts/writing.md` - 章节写作
- `backend/prompts/evaluation.md` - 内容评估
- `backend/prompts/extraction.md` - 信息提取
- `backend/prompts/part_outline.md` - 部分大纲
- `backend/prompts/screenwriting.md` - 剧本写作

### 数据库
- [`backend/app/db/init_db.py`](../db/init_db.md) - 加载默认提示词

## 