
# Chapter Ingest Service - 章节向量入库服务

## 文件概述

**文件路径**: `backend/app/services/chapter_ingest_service.py`  
**代码行数**: 262行  
**核心职责**: 章节向量入库服务，负责在章节确认后切分文本、生成向量嵌入并写入向量库，为RAG检索提供数据支持

## 核心功能

### 1. 章节向量化入库

主要方法，将章节内容和摘要向量化并存储：

```python
async def ingest_chapter(
    self,
    *,
    project_id: str,
    chapter_number: int,
    title: str,
    content: str,
    summary: Optional[str],
    user_id: int,
) -> None
```

**功能说明**：
- 切分章节内容为多个片段（chunks）
- 为每个片段生成向量嵌入
- 将片段和向量存入向量库
- 为章节摘要生成向量并存储

**使用示例**：
```python
from backend.app.services.chapter_ingest_service import ChapterIngestionService

# 初始化服务
ingest_service = ChapterIngestionService(
    llm_service=llm_service,
    vector_store=vector_store
)

# 用户选择章节版本后，向量化该章节
await ingest_service.ingest_chapter(
    project_id=project_id,
    chapter_number=1,
    title="第一章：穿越",
    content=selected_version.content,
    summary=chapter.real_summary,
    user_id=user_id
)
```

**工作流程**：
```python
# 1. 切分章节内容
chunks = self._split_into_chunks(content)  # 按配置大小切分

# 2. 删除旧数据（如果存在）
await self._vector_store.delete_by_chapters(project_id, [chapter_number])

# 3. 为每个片段生成向量
for index, chunk_text in enumerate(chunks):
    embedding = await self._llm_service.get_embedding(chunk_text, user_id=user_id)
    chunk_records.append({
        "id": f"{project_id}:{chapter_number}:{index}",
        "project_id": project_id,
        "chapter_number": chapter_number,
        "chunk_index": index,
        "chapter_title": title,
        "content": chunk_text,
        "embedding": embedding,
        "metadata": {"length": len(chunk_text)}
    })

# 4. 批量写入向量库
await self._vector_store.upsert_chunks(records=chunk_records)

# 5. 处理章节摘要
if summary:
    summary_embedding = await self._llm_service.get_embedding(summary, user_id=user_id)
    await self._vector_store.upsert_summaries(records=[{
        "id": f"{project_id}:{chapter_number}:summary",
        "project_id": project_id,
        "chapter_number": chapter_number,
        "title": title,
        "summary": summary,
        "embedding": summary_embedding
    }])
```

### 2. 文本切分策略

#### LangChain切分器（首选）

使用LangChain的RecursiveCharacterTextSplitter：

```python
def _init_text_splitter(self) -> Optional["RecursiveCharacterTextSplitter"]:
    """初始化LangChain文本切分器"""
    chunk_size = settings.vector_chunk_size      # 默认500
    overlap = settings.vector_chunk_overlap      # 默认50
    
    separators = [
        "\n\n",        # 段落分隔
        "\n",          # 行分隔
        "。", "！", "？",  # 中文标点
        "!", "?", "；", ";",  # 英文标点
        "，", ",",     # 逗号
        " ",           # 空格
    ]
    
    splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        keep_separator=False,
        strip_whitespace=True,
    )
    
    return splitter
```

**优势**：
- 智能分隔：优先在自然断点切分
- 保留上下文：通过overlap保持连贯性
- 灵活配置：可调整chunk大小和重叠度

**使用示例**：
```python
# 配置切分参数
VECTOR_CHUNK_SIZE=500      # 每个片段500字
VECTOR_CHUNK_OVERLAP=50    # 相邻片段重叠50字

# 切分效果
content = "第一章内容..." * 1000  # 假设5000字
chunks = text_splitter.split_text(content)
# 结果：约10个片段，每个500字左右，相邻片段有50字重叠
```

#### 内置切分器（后备方案）

当LangChain未安装时，使用内置切分算法：

```python
def _legacy_split(self, text: str) -> List[str]:
    """内置切分策略，作为LangChain缺失时的后备方案"""
    chunk_size = settings.vector_chunk_size
    overlap = settings.vector_chunk_overlap
    
    chunks = []
    start = 0
    total_length = len(text)
    
    while start < total_length:
        end = min(total_length, start + chunk_size)
        segment = text[start:end]
        
        # 寻找自然分割点
        split_offset = self._find_split_offset(segment)
        if split_offset is not None:
            end = start + split_offset
            segment = text[start:end]
        
        chunks.append(segment.strip())
        
        if end >= total_length:
            break
        start = max(0, end - overlap)
    
    return chunks
```

**自然分割点查找**：
```python
@staticmethod
def _find_split_offset(segment: str) -> Optional[int]:
    """在片段内部寻找更自然的分割点"""
    candidates = {}
    
    # 优先：段落分隔
    newline_pos = segment.rfind("\n\n")
    if newline_pos == -1:
        newline_pos = segment.rfind("\n")
    if newline_pos > 0:
        candidates["newline"] = newline_pos
    
    # 其次：标点符号
    punctuation_marks = ["。", "！", "？", "!", "?", ".", ";", "；"]
    for mark in punctuation_marks:
        idx = segment.rfind(mark)
        if idx > 0:
            candidates.setdefault("punctuation", idx + len(mark))
    
    # 选择最接近末尾但不过短的分割点
    if candidates:
        best_offset = max(candidates.values())
        if best_offset >= len(segment) * 0.4:  # 至少占40%
            return best_offset
    
    return None
```

### 3. 删除章节向量

```python
async def delete_chapters(
    self, 
    project_id: str, 
    chapter_numbers: Sequence[int]
) -> None:
    """从向量库中删除指定章节的所有片段与摘要"""
```

**使用场景**：
1. 章节重新生成前清理旧数据
2. 用户删除章节时清理向量数据

**使用示例**：
```python
# 删除单个章节
await ingest_service.delete_chapters(
    project_id=project_id,
    chapter_numbers=[5]
)

# 批量删除章节
await ingest_service.delete_chapters(
    project_id=project_id,
    chapter_numbers=[5, 6, 7, 8, 9, 10]
)
```

## 完整工作流程

### 章节生成后的向量化流程

```python
async def on_chapter_version_selected(
    project_id: str,
    chapter: Chapter,
    selected_version: ChapterVersion,
    user_id: int
):
    """用户选择章节版本后的处理流程"""
    
    # 1. 更新章节状态
    chapter.selected_version_id = selected_version.id
    chapter.status = ChapterGenerationStatus.SUCCESSFUL.value
    await session.commit()
    
    # 2. 生成章节摘要（如果没有）
    if not chapter.real_summary:
        summary = await llm_service.get_summary(
            chapter_content=selected_version.content,
            user_id=user_id
        )
        chapter.real_summary = summary
        await session.commit()
    
    # 3. 向量化章节内容
    ingest_service = ChapterIngestionService(
        llm_service=llm_service,
        vector_store=vector_store
    )
    
    await ingest_service.ingest_chapter(
        project_id=project_id,
        chapter_number=chapter.chapter_number,
        title=chapter.outline.title if chapter.outline else f"第{chapter.chapter_number}章",
        content=selected_version.content,
        summary=chapter.real_summary,
        user_id=user_id
    )
    
    logger.info(
        "章节 %d 向量化完成: project=%s",
        chapter.chapter_number,
        project_id
    )
```

### 章节重新生成的流程

```python
async def regenerate_chapter(
    project_id: str,
    chapter_number: int,
    user_id: int
):
    """重新生成章节"""
    
    # 1. 删除旧的向量数据
    ingest_service = ChapterIngestionService(
        llm_service=llm_service,
        vector_store=vector_store
    )
    
    await ingest_service.delete_chapters(
        project_id=project_id,
        chapter_numbers=[chapter_number]
    )
    
    # 2. 生成新章节
    new_content = await generate_chapter_content(
        project_id=project_id,
        chapter_number=chapter_number,
        user_id=user_id
    )
    
    # 3. 用户选择版本后，再次向量化
    # （参考上面的 on_chapter_version_selected 流程）
```

## 配置项

### 切分参数配置

```python
# .env 或 settings
VECTOR_CHUNK_SIZE=500          # 每个片段的字符数
VECTOR_CHUNK_OVERLAP=50        # 相邻片段的重叠字符数
```

**推荐配置**：
```python
# 短章节（1000-3000字）
VECTOR_CHUNK_SIZE=300
VECTOR_CHUNK_OVERLAP=30

# 中等章节（3000-6000字）
VECTOR_CHUNK_SIZE=500
VECTOR_CHUNK_OVERLAP=50

# 长章节（6000字以上）
VECTOR_CHUNK_SIZE=800
VECTOR_CHUNK_OVERLAP=80
```

### 向量库配置

```python
VECTOR_STORE_ENABLED=true      # 启用向量库
VECTOR_DB_URL=file:storage/vector.db
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
```

## 性能优化

### 1. 容错设计

向量库未启用时静默跳过：
```python
if not settings.vector_store_enabled:
    logger.debug("向量库未启用，跳过章节向量写入")
    return
```

### 2. 批量写入

所有片段一次性写入，减少网络开销：
```python
# 收集所有片段
chunk_records = []
for index, chunk_text in enumerate(chunks):
    embedding = await self._llm_service.get_embedding(...)
    chunk_records.append({...})

# 批量写入
await self._vector_store.upsert_chunks(records=chunk_records)
```

### 3. 并发向量生成

可以并发生成多个片段的向量：
```python
# 串行（当前实现）
for chunk in chunks:
    embedding = await llm_service.get_embedding(chunk)

# 并发优化（可选）
import asyncio
tasks = [
    llm_service.get_embedding(chunk, user_id=user_id)
    for chunk in chunks
]
embeddings = await asyncio.gather(*tasks)
```

## 依赖关系

### 内部依赖
- [`LLMService`](backend/app/services/llm_service.py) - 生成向量嵌入
- [`VectorStoreService`](backend/app/services/vector_store_service.py) - 存储向量数据
- [`settings`](backend/app/core/config.py) - 读取配置

### 外部依赖
- `langchain-text-splitters` - 文本切分（可选）

### 调用方
- [`writer.py`](backend/app/api/routers/writer.py) - 章节生成后入库

## 最佳实践

### 1. 章节选择后立即入库

```python
# 好的做法：选择版本后立即向量化
await novel_service.select_chapter_version(chapter, version_index)
await ingest_service.ingest_chapter(...)

# 不推荐：延迟入库（影响后续章节的RAG检索）
```

### 2. 重新生成前清理旧数据

```python
# 好的做法：先删除再生成
await ingest_service.delete_chapters(project_id, [chapter_number])
# 生成新章节...
await ingest_service.ingest_chapter(...)

# 不推荐：直接覆盖（可能导致向量ID冲突）
```

### 3. 调整切分参数

```python
# 根据章节平均长度调整
avg_chapter_length = 5000  # 平均5000字

if avg_chapter_length < 3000:
    chunk_size = 300
elif avg_chapter_length > 8000:
    chunk_size = 800
else:
    chunk_size = 500
```

### 4. 监控向量生成失败

```python
# 记录失败的片段
failed_chunks = []
for index, chunk_text in enumerate(chunks):
    embedding = await llm_service.get_embedding(chunk_text, user_id=user_id)
    if not embedding:
        