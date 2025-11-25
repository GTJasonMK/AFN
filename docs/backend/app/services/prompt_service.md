
# Prompt Service - 提示词服务

## 文件概述

**文件路径**: `backend/app/services/prompt_service.py`  
**代码行数**: 96行  
**核心职责**: 提示词管理服务，提供高性能的提示词缓存、CRUD操作和预加载机制

## 核心功能

### 1. 提示词缓存机制

使用模块级别的缓存字典，避免频繁查询数据库：

```python
_CACHE: Dict[str, PromptRead] = {}      # 全局缓存
_LOCK = asyncio.Lock()                   # 并发锁
_LOADED = False                          # 缓存状态标志
```

**缓存特点**：
- 全局共享，所有请求复用
- 线程安全（使用asyncio.Lock）
- 懒加载 + 预加载双模式
- 自动更新（增删改操作同步更新缓存）

### 2. 预加载提示词

应用启动时预加载所有提示词到内存：

```python
async def preload(self) -> None:
    """预加载所有提示词到缓存"""
    global _CACHE, _LOADED
    prompts = await self.repo.list_all()
    async with _LOCK:
        _CACHE = {item.name: PromptRead.model_validate(item) for item in prompts}
        _LOADED = True
```

**调用位置**：
```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时预热提示词缓存"""
    await init_db()
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()  # 预加载提示词
    yield
```

**优势**：
- 应用启动后提示词访问几乎无延迟
- 减少数据库查询压力
- 适合提示词数量有限的场景

### 3. 获取提示词内容

主要方法，支持懒加载和缓存命中：

```python
async def get_prompt(self, name: str) -> Optional[str]
```

**执行流程**：
```python
# 1. 检查缓存
async with _LOCK:
    if not _LOADED:
        # 首次访问，懒加载所有提示词
        prompts = await self.repo.list_all()
        _CACHE.update({item.name: PromptRead.model_validate(item) for item in prompts})
        _LOADED = True
    
    cached = _CACHE.get(name)

if cached:
    return cached.content  # 缓存命中，直接返回

# 2. 缓存未命中，查询数据库
prompt = await self.repo.get_by_name(name)
if not prompt:
    return None

# 3. 更新缓存
prompt_read = PromptRead.model_validate(prompt)
async with _LOCK:
    _CACHE[name] = prompt_read

return prompt_read.content
```

**使用示例**：
```python
# 获取写作提示词
writing_prompt = await prompt_service.get_prompt("writing")
if not writing_prompt:
    raise HTTPException(status_code=500, detail="未配置写作提示词")

# 获取大纲提示词
outline_prompt = await prompt_service.get_prompt("outline")

# 获取提取提示词（摘要生成）
extraction_prompt = await prompt_service.get_prompt("extraction")
```

### 4. 提示词CRUD操作

#### 列出所有提示词

```python
async def list_prompts(self) -> list[PromptRead]
```

**使用示例**：
```python
prompts = await prompt_service.list_prompts()
for prompt in prompts:
    print(f"{prompt.name}: {prompt.description}")
    print(f"标签: {prompt.tags}")
```

#### 获取单个提示词

```python
async def get_prompt_by_id(self, prompt_id: int) -> Optional[PromptRead]
```

**使用示例**：
```python
prompt = await prompt_service.get_prompt_by_id(1)
if prompt:
    print(f"名称: {prompt.name}")
    print(f"内容: {prompt.content}")
```

#### 创建提示词

```python
async def create_prompt(self, payload: PromptCreate) -> PromptRead
```

**自动更新缓存**：
```python
prompt_read = PromptRead.model_validate(prompt)
async with _LOCK:
    _CACHE[prompt_read.name] = prompt_read  # 立即加入缓存
    global _LOADED
    _LOADED = True
return prompt_read
```

**使用示例**：
```python
from backend.app.schemas.prompt import PromptCreate

new_prompt = await prompt_service.create_prompt(
    PromptCreate(
        name="custom_writing",
        description="自定义写作风格提示词",
        content="你是一个专业的小说作家，擅长...",
        tags=["写作", "自定义"]
    )
)

# 创建后立即可用
content = await prompt_service.get_prompt("custom_writing")
```

#### 更新提示词

```python
async def update_prompt(
    self, 
    prompt_id: int, 
    payload: PromptUpdate
) -> Optional[PromptRead]
```

**自动更新缓存**：
```python
prompt_read = PromptRead.model_validate(instance)
async with _LOCK:
    _CACHE[prompt_read.name] = prompt_read  # 更新缓存
return prompt_read
```

**使用示例**：
```python
from backend.app.schemas.prompt import PromptUpdate

updated = await prompt_service.update_prompt(
    prompt_id=1,
    payload=PromptUpdate(
        content="更新后的提示词内容...",
        description="新的描述",
        tags=["写作", "v2"]
    )
)

# 更新后立即生效
new_content = await prompt_service.get_prompt(updated.name)
```

#### 删除提示词

```python
async def delete_prompt(self, prompt_id: int) -> bool
```

**自动清理缓存**：
```python
await self.repo.delete(instance)
await self.session.commit()
async with _LOCK:
    _CACHE.pop(instance.name, None)  # 从缓存移除
return True
```

**使用示例**：
```python
success = await prompt_service.delete_prompt(prompt_id=5)
if success:
    print("提示词已删除")
```

### 5. 标签处理

提示词支持多标签分类，存储时自动转换：

```python
# 创建时：List[str] -> str
data = payload.model_dump()
tags = data.get("tags")
if tags is not None:
    data["tags"] = ",".join(tags)  # ["写作", "小说"] -> "写作,小说"

# 更新时：List[str] -> str
if "tags" in update_data and update_data["tags"] is not None:
    update_data["tags"] = ",".join(update_data["tags"])
```

**Schema定义**（自动转换）：
```python
# backend/app/schemas/prompt.py
class PromptRead(BaseModel):
    name: str
    description: Optional[str]
    content: str
    tags: List[str] = []  # 数据库存储为逗号分隔，读取时自动分割
```

## 系统提示词

### 内置提示词列表

项目预定义了以下提示词（存储在 `backend/prompts/` 目录）：

```python
# backend/prompts/
concept.md       # 概念生成提示词
evaluation.md    # 章节评价提示词
extraction.md    # 摘要提取提示词
outline.md       # 章节大纲生成提示词
part_outline.md  # 部分大纲生成提示词（长篇小说）
screenwriting.md # 分镜生成提示词
writing.md       # 章节写作提示词
```

### 提示词数据库初始化

在应用首次启动时，从Markdown文件导入到数据库：

```python
# backend/app/db/init_db.py
async def init_db():
    """初始化数据库，导入提示词"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        prompt_repo = PromptRepository(session)
        existing_count = await prompt_repo.count()
        
        if existing_count == 0:
            # 从backend/prompts目录导入
            prompts_dir = Path(__file__).parent.parent / "prompts"
            for md_file in prompts_dir.glob("*.md"):
                name = md_file.stem
                content = md_file.read_text(encoding="utf-8")
                prompt = Prompt(
                    name=name,
                    description=f"{name}提示词",
                    content=content
                )
                session.add(prompt)
            await session.commit()
```

### 常用提示词名称

```python
# 写作相关
"writing"         # 章节内容生成
"outline"         # 章节大纲生成
"part_outline"    # 部分大纲生成
"screenwriting"   # 分镜脚本生成

# 分析相关
"extraction"      # 章节摘要提取
"evaluation"      # 章节评价
"concept"         # 概念生成
```

## 性能优化

### 缓存命中率

通过预加载机制，缓存命中率接近100%：

```python
# 应用启动时
await prompt_service.preload()  # 加载所有提示词

# 后续请求
content = await prompt_service.get_prompt("writing")  # 缓存命中，<1ms
```

### 并发安全

使用asyncio.Lock确保并发环境下的数据一致性：

```python
async with _LOCK:
    # 关键区域：读写缓存
    _CACHE[name] = prompt_read
```

### 内存占用

提示词通常为文本数据，内存占用极小：

```python
# 假设100个提示词，每个平均5KB
# 总内存占用 ≈ 100 * 5KB = 500KB
```

## 使用场景

### 1. 章节生成时获取提示词

```python
# backend/app/api/routers/writer.py
async def generate_chapter(...):
    prompt_service = PromptService(session)
    
    # 获取写作提示词
    system_prompt = await prompt_service.get_prompt("writing")
    if not system_prompt:
        raise HTTPException(status_code=500, detail="未配置写作提示词")
    
    # 调用LLM
    response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[...]
    )
```

### 2. 大纲生成时获取提示词

```python
async def generate_outline(...):
    prompt_service = PromptService(session)
    
    # 获取大纲提示词
    system_prompt = await prompt_service.get_prompt("outline")
    
    # 生成大纲
    response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[...]
    )
```

### 3. 章节摘要生成

```python
async def get_summary(...):
    prompt_service = PromptService(session)
    
    # 获取提取提示词
    system_prompt = await prompt_service.get_prompt("extraction")
    
    # 生成摘要
    summary = await llm_service.get_summary(
        chapter_content=content,
        system_prompt=system_prompt
    )
```

## 依赖关系

### 内部依赖
- [`PromptRepository`](backend/app/repositories/prompt_repository.py) - 数据库操作
- [`Prompt`](backend/app/models/prompt.py) - 数据模型

### Schema定义
- [`PromptCreate`](backend/app/schemas/prompt.py) - 创建Schema
- [`PromptUpdate`](backend/app/schemas/prompt.py) - 更新Schema
- [`PromptRead`](backend/app/schemas/prompt.py) - 读取Schema

### 调用方
- [`LLMService`](backend/app/services/llm_service.py) - 获取摘要提示词
- [`writer.py`](backend/app/api/routers/writer.py) - 章节生成
- [`novels.py`](backend/app/api/routers/novels.py) - 大纲生成

## 最佳实践

### 1. 应用启动时预加载

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        prompt_service = PromptService(session)
        await prompt_service.preload()  # 必须
    yield
```

### 2. 检查提示词是否存在

```python
system_prompt = await prompt_service.get_prompt("writing")
if not system_prompt:
    raise HTTPException(status_code=500, detail="未配置写作提示词")
```

### 3. 自定义提示词

```python
# 为特殊需求创建自定义提示词
custom_prompt = await prompt_service.create_prompt(
    PromptCreate(
        name="mystery_writing",
        description="悬疑小说写作提示词",
        content="你是一个擅长悬疑推理的作家...",
        tags=["写作", "悬疑"]
    )
)

# 使用自定义提示词
content = await prompt_service.get_prompt("mystery_writing")
```

### 4. 提示词版本管理

```python
# 通过标签管理版本
await prompt_service.create_prompt(
    PromptCreate(
        name="writing_v2",
        description="写作提示词v2",
        content="改进后的提示词...",
        tags=["写作", "v2", "最新"]
    )
)
```

## 相关文件

- **数据模型**: [`backend/app/models/prompt.py`](backend/app/models/prompt.py)
- **仓储层**: [`backend/app/repositories/prompt_repository.py`](backend/app/repositories/prompt_repository.py)
- **Schema**: [`backend/app/schemas/prompt.py`](backend/app/schemas/prompt.py)
- **提示词文件**: `backend/prompts/*.md`
- **初始化**: [`backend/app/db/init_db.py`](backend/app/db/init_db.py)
