
# Vector Store Service - 向量检索服务

## 文件概述

**文件路径**: `backend/app/services/vector_store_service.py`  
**代码行数**: 544行  
**核心职责**: 基于libsql的向量存储与检索服务，为RAG（检索增强生成）功能提供章节内容和摘要的向量化存储与相似度搜索

## 核心功能

### 1. 向量检索

#### 检索剧情片段

```python
async def query_chunks(
    self,
    *,
    project_id: str,
    embedding: Sequence[float],
    top_k: Optional[int] = None,
) -> List[RetrievedChunk]
```

**功能说明**：
- 根据查询向量检索最相似的章节片段
- 使用余弦相似度计算
- 支持项目级别的数据隔离
- 结果按相似度排序

**使用示例**：
```python
vector_service = VectorStoreService()

# 生成查询向量
query_text = "主角遇到了什么困难？"
query_embedding = await llm_service.get_embedding(query_text)

# 检索相关片段
chunks = await vector_service.query_chunks(
    project_id=project_id,
    embedding=query_embedding,
    top_k=5  # 返回前5个最相关的片段
)

# 使用检索结果
for chunk in chunks:
    print(f"章节{chunk.chapter_number}: {chunk.chapter_title}")
    print(f"相似度: {chunk.score:.4f}")
    print(f"内容: {chunk.content[:100]}...")
    print(f"元数据: {chunk.metadata}")
```

**返回数据结构**：
```python
@dataclass
class RetrievedChunk:
    content: str                      # 片段内容
    chapter_number: int               # 章节编号
    chapter_title: Optional[str]      # 章节标题
    score: float                      # 相似度分数（余弦距离）
    metadata: Dict[str, Any]          # 额外元数据
```

#### 检索章节摘要

```python
async def query_summaries(
    self,
    *,
    project_id: str,
    embedding: Sequence[float],
    top_k: Optional[int] = None,
) -> List[RetrievedSummary]
```

**使用场景**：
- 快速了解相关章节概要
- 构建章节上下文摘要
- 避免加载完整章节内容

**使用示例**：
```python
# 检索相关章节摘要
summaries = await vector_service.query_summaries(
    project_id=project_id,
    embedding=query_embedding,
    top_k=10
)

# 构建上下文摘要
context = "以下是相关章节的摘要：\n\n"
for summary in summaries:
    context += f"第{summary.chapter_number}章《{summary.title}》\n"
    context += f"{summary.summary}\n\n"
```

**返回数据结构**：
```python
@dataclass
class RetrievedSummary:
    chapter_number: int    # 章节编号
    title: str             # 章节标题
    summary: str           # 章节摘要
    score: float           # 相似度分数
```

### 2. 向量存储

#### 批量写入章节片段

```python
async def upsert_chunks(
    self,
    *,
    records: Iterable[Dict[str, Any]],
) -> None
```

**记录格式**：
```python
records = [
    {
        "id": f"{project_id}:chunk:{chapter_number}:{chunk_index}",
        "project_id": project_id,
        "chapter_number": 1,
        "chunk_index": 0,
        "chapter_title": "第一章",
        "content": "章节片段内容...",
        "embedding": [0.1, 0.2, 0.3, ...],  # 向量数组
        "metadata": {"word_count": 500}
    },
    # 更多片段...
]
```

**使用示例**：
```python
# 章节向量化后批量写入
chunks_to_store = []
for idx, chunk_text in enumerate(chapter_chunks):
    embedding = await llm_service.get_embedding(chunk_text)
    chunks_to_store.append({
        "id": f"{project_id}:chunk:{chapter_num}:{idx}",
        "project_id": project_id,
        "chapter_number": chapter_num,
        "chunk_index": idx,
        "chapter_title": chapter_title,
        "content": chunk_text,
        "embedding": embedding,
        "metadata": {"word_count": len(chunk_text)}
    })

await vector_service.upsert_chunks(records=chunks_to_store)
```

#### 批量写入章节摘要

```python
async def upsert_summaries(
    self,
    *,
    records: Iterable[Dict[str, Any]],
) -> None
```

**记录格式**：
```python
records = [
    {
        "id": f"{project_id}:summary:{chapter_number}",
        "project_id": project_id,
        "chapter_number": 1,
        "title": "第一章：开篇",
        "summary": "章节摘要内容...",
        "embedding": [0.1, 0.2, 0.3, ...]
    },
    # 更多摘要...
]
```

**使用示例**：
```python
# 生成并存储章节摘要
summaries_to_store = []
for chapter in chapters:
    # 生成摘要
    summary_text = await llm_service.get_summary(chapter.content)
    
    # 生成摘要向量
    summary_embedding = await llm_service.get_embedding(summary_text)
    
    summaries_to_store.append({
        "id": f"{project_id}:summary:{chapter.chapter_number}",
        "project_id": project_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "summary": summary_text,
        "embedding": summary_embedding
    })

await vector_service.upsert_summaries(records=summaries_to_store)
```

### 3. 数据管理

#### 删除章节向量

```python
async def delete_by_chapters(
    self, 
    project_id: str, 
    chapter_numbers: Sequence[int]
) -> None
```

**功能说明**：
- 同时删除片段和摘要表中的数据
- 支持批量删除多个章节
- 用于章节重新生成或删除场景

**使用示例**：
```python
# 删除第5-10章的所有向量数据
await vector_service.delete_by_chapters(
    project_id=project_id,
    chapter_numbers=[5, 6, 7, 8, 9, 10]
)

# 重新生成这些章节后，再次写入新的向量
```

### 4. 初始化与配置

#### 表结构初始化

```python
async def ensure_schema(self) -> None
```

**创建的表结构**：

```sql
-- 章节片段表
CREATE TABLE IF NOT EXISTS rag_chunks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    chapter_title TEXT,
    content TEXT NOT NULL,
    embedding BLOB NOT NULL,           -- F32 向量
    metadata TEXT,                      -- JSON字符串
    created_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_project
ON rag_chunks(project_id, chapter_number);

-- 章节摘要表
CREATE TABLE IF NOT EXISTS rag_summaries (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    chapter_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    embedding BLOB NOT NULL,           -- F32 向量
    created_at INTEGER DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_rag_summaries_project
ON rag_summaries(project_id, chapter_number);
```

**自动调用时机**：
- 第一次查询时
- 第一次写入时
- 服务初始化后的第一次操作

### 5. 相似度计算

#### 数据库层计算（首选）

使用libsql的向量扩展函数：
```sql
SELECT 
    content,
    chapter_number,
    vector_distance_cosine(embedding, :query) AS distance
FROM rag_chunks
WHERE project_id = :project_id
ORDER BY distance ASC
LIMIT :limit
```

#### Python层计算（降级方案）

当数据库不支持向量函数时，自动降级到应用层计算：

```python
@staticmethod
def _cosine_distance(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """计算余弦距离（1 - similarity）"""
    if not vec_a or not vec_b:
        return 1.0
    
    # 点积
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    
    # 范数
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    
    if norm_a == 0 or norm_b == 0:
        return 1.0
    
    # 余弦相似度
    similarity = dot / (norm_a * norm_b)
    
    # 转换为距离（越小越相似）
    return 1.0 - similarity
```

**降级处理流程**：
```python
try:
    # 尝试使用数据库向量函数
    result = await self._client.execute(sql_with_vector_function)
except Exception as exc:
    if "no such function: vector_distance_cosine" in str(exc).lower():
        # 降级到Python实现
        logger.warning("向量库缺少函数，回退至应用层计算")
        return await self._query_chunks_with_python_similarity(...)
```

### 6. 向量编码

#### Float32二进制编码

```python
@staticmethod
def _to_f32_blob(embedding: Sequence[float]) -> bytes:
    """将向量浮点列表编码为float32二进制"""
    return array("f", embedding).tobytes()
```

**使用示例**：
```python
embedding = [0.1, 0.2, 0.3, 0.4]
blob = VectorStoreService._to_f32_blob(embedding)
# blob 是紧凑的二进制表示，适合数据库存储
```

#### Float32二进制解码

```python
@staticmethod
def _from_f32_blob(blob: Any) -> List[float]:
    """将数据库BLOB解码为浮点列表"""
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    data = array("f")
    data.frombytes(bytes(blob))
    return list(data)
```

## 配置与环境

### 必需配置

```python
# .env 或 settings
VECTOR_STORE_ENABLED=true                    # 启用向量库
VECTOR_DB_URL=file:storage/vector.db         # 本地文件
# 或
VECTOR_DB_URL=libsql://xxx.turso.io          # 远程Turso

VECTOR_DB_AUTH_TOKEN=your_token              # 远程数据库认证令牌（可选）
```

### 检索参数配置

```python
# settings.py
VECTOR_TOP_K_CHUNKS=5      # 默认返回5个最相关片段
VECTOR_TOP_K_SUMMARIES=10  # 默认返回10个最相关摘要
```

### 禁用向量库

```python
VECTOR_STORE_ENABLED=false
```

当禁用时，服务会静默跳过所有操作：
```python
if not self._client:
    return []  # 返回空结果，不抛出错误
```

## 工作流程

### 完整的RAG流程

```python
# 1. 章节生成时向量化
async def ingest_chapter(project_id: str, chapter: Chapter):
    """将章节内容向量化并存储"""
    
    # 分块（每500字一块）
    chunks = split_text(chapter.content, chunk_size=500)
    
    # 生成片段向量
    chunk_records = []
    for idx, chunk_text in enumerate(chunks):
        embedding = await llm_service.get_embedding(chunk_text)
        chunk_records.append({
            "id": f"{project_id}:chunk:{chapter.chapter_number}:{idx}",
            "project_id": project_id,
            "chapter_number": chapter.chapter_number,
            "chunk_index": idx,
            "chapter_title": chapter.title,
            "content": chunk_text,
            "embedding": embedding,
            "metadata": {}
        })
    
    await vector_service.upsert_chunks(records=chunk_records)
    
    # 生成摘要向量
    summary = await llm_service.get_summary(chapter.content)
    summary_embedding = await llm_service.get_embedding(summary)
    
    await vector_service.upsert_summaries(records=[{
        "id": f"{project_id}:summary:{chapter.chapter_number}",
        "project_id": project_id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "summary": summary,
        "embedding": summary_embedding
    }])

# 2. 生成新章节时检索上下文
async def generate_with_rag(project_id: str, chapter_number: int):
    """使用RAG增强生成"""
    
    # 构建查询
    outline = await get_chapter_outline(project_id, chapter_number)
    query_text = f"{outline.title}\n{outline.summary}"
    
    # 生成查询向量
    query_embedding = await llm_service.get_embedding(query_text)
    
    # 检索相关内容
    relevant_chunks = await vector_service.query_chunks(
        project_id=project_id,
        embedding=query_embedding,
        top_k=5
    )
    
    relevant_summaries = await vector_service.query_summaries(
        project_id=project_id,
        embedding=query_embedding,
        top_k=10
    )
    
    # 构建上下文
    context = build_context(relevant_chunks, relevant_summaries)
    
    # 调用LLM生成
    response = await llm_service.get_llm_response(
        system_prompt=writing_prompt,
        conversation_history=[
            {"role": "user", "content": f"上下文：\n{context}\n\n请基于以上上下文生成第{chapter_number}章"}
        ]
    )
    
    return response
```

## 技术细节

### 数据隔离

