# Chapter Context Service - 章节上下文服务

## 文件概述

**文件路径**: `backend/app/services/chapter_context_service.py`  
**代码行数**: 109行  
**核心职责**: 章节上下文组装服务，负责调用向量库检索上下文，并对结果进行格式化，为RAG（检索增强生成）提供支持

## 核心功能

### 1. RAG上下文检索

主要方法，根据查询文本检索相关的章节片段和摘要：

```python
async def retrieve_for_generation(
    self,
    *,
    project_id: str,
    query_text: str,
    user_id: int,
    top_k_chunks: Optional[int] = None,
    top_k_summaries: Optional[int] = None,
) -> ChapterRAGContext
```

**功能说明**：
- 将查询文本转换为向量
- 从向量库检索相关章节片段
- 从向量库检索相关章节摘要
- 返回格式化的上下文对象

**使用示例**：
```python
from backend.app.services.chapter_context_service import ChapterContextService
from backend.app.services.llm_service import LLMService
from backend.app.services.vector_store_service import VectorStoreService

# 初始化服务
llm_service = LLMService(session)
vector_store = VectorStoreService()
context_service = ChapterContextService(
    llm_service=llm_service,
    vector_store=vector_store
)

# 构建查询（基于章节大纲）
query_text = f"{outline.title}\n{outline.summary}"

# 检索上下文
rag_context = await context_service.retrieve_for_generation(
    project_id=project_id,
    query_text=query_text,
    user_id=user_id,
    top_k_chunks=5,        # 返回5个最相关片段
    top_k_summaries=10      # 返回10个最相关摘要
)

# 使用检索结果
print(f"检索到 {len(rag_context.chunks)} 个相关片段")
print(f"检索到 {len(rag_context.summaries)} 个相关摘要")
```

**容错处理**：
```python
# 向量库未启用时返回空结果
if not settings.vector_store_enabled or not self._vector_store:
    logger.debug("向量库未启用，跳过检索")
    return ChapterRAGContext(query=query, chunks=[], summaries=[])

# 向量生成失败时返回空结果
embedding = await self._llm_service.get_embedding(query, user_id=user_id)
if not embedding:
    logger.warning("查询向量生成失败")
    return ChapterRAGContext(query=query, chunks=[], summaries=[])
```

### 2. 上下文数据结构

**ChapterRAGContext** 封装了检索结果：

```python
@dataclass
class ChapterRAGContext:
    """封装检索得到的上下文结果"""
    query: str                          # 标准化后的查询文本
    chunks: List[RetrievedChunk]        # 检索到的章节片段
    summaries: List[RetrievedSummary]   # 检索到的章节摘要
```

**使用示例**：
```python
# 获取格式化的片段文本
chunk_texts = rag_context.chunk_texts()
for text in chunk_texts:
    print(text)
# 输出：
# ### Chunk 1(来源：第3章)
# 主角在山洞中发现了古老的传承...

# 获取格式化的摘要列表
summary_lines = rag_context.summary_lines()
for line in summary_lines:
    print(line)
# 输出：
# - 第3章 - 奇遇:主角意外获得修炼功法
# - 第5章 - 初战:首次与敌人交手
```

### 3. 格式化方法

#### chunk_texts() - 片段格式化

将检索到的章节片段转换为Markdown格式：

```python
def chunk_texts(self) -> List[str]:
    """将检索到的chunk转换成带序号的Markdown段落"""
    lines = []
    for idx, chunk in enumerate(self.chunks, start=1):
        title = chunk.chapter_title or f"第{chunk.chapter_number}章"
        lines.append(
            f"### Chunk {idx}(来源：{title})\n{chunk.content.strip()}"
        )
    return lines
```

**输出格式**：
```markdown
### Chunk 1(来源：第1章)
程序员张三坐在电脑前，突然一道雷电劈中了他的电脑...

### Chunk 2(来源：第3章)
醒来后，张三发现自己穿越到了一个陌生的修仙世界...

### Chunk 3(来源：第5章)
在师傅的指导下，张三开始学习基础的修炼功法...
```

#### summary_lines() - 摘要格式化

整理章节摘要为列表格式：

```python
def summary_lines(self) -> List[str]:
    """整理章节摘要，方便直接插入Prompt"""
    lines = []
    for summary in self.summaries:
        lines.append(
            f"- 第{summary.chapter_number}章 - {summary.title}:{summary.summary.strip()}"
        )
    return lines
```

**输出格式**：
```
- 第1章 - 穿越:程序员张三意外穿越到修仙世界
- 第2章 - 初遇:结识了修仙门派的长老李四
- 第3章 - 拜师:成为李四的弟子，开始修炼
- 第5章 - 突破:成功突破到炼气期
- 第8章 - 试炼:参加门派试炼，展现实力
```

### 4. 查询文本标准化

[`_normalize()`](backend/app/services/chapter_context_service.py:100) 统一压缩空白字符：

```python
@staticmethod
def _normalize(text: str) -> str:
    """统一压缩空白字符，避免影响检索效果"""
    return " ".join(text.split())
```

**处理效果**：
```python
# 原始文本（包含多余空白）
text = "第五章\n\n  主角  突破   \n炼气期"

# 标准化后
normalized = ChapterContextService._normalize(text)
# 结果："第五章 主角 突破 炼气期"
```

## 完整使用流程

### 典型的RAG生成流程

```python
async def generate_chapter_with_rag(
    project_id: str,
    chapter_number: int,
    user_id: int
):
    """使用RAG增强生成章节"""
    
    # 1. 获取章节大纲
    outline = await novel_service.get_outline(project_id, chapter_number)
    
    # 2. 构建查询文本
    query_text = f"{outline.title}\n{outline.summary}"
    
    # 3. 检索上下文
    context_service = ChapterContextService(
        llm_service=llm_service,
        vector_store=vector_store
    )
    
    rag_context = await context_service.retrieve_for_generation(
        project_id=project_id,
        query_text=query_text,
        user_id=user_id,
        top_k_chunks=5,
        top_k_summaries=10
    )
    
    # 4. 构建上下文提示
    context_prompt = ""
    
    # 添加相关片段
    if rag_context.chunks:
        chunk_texts = rag_context.chunk_texts()
        context_prompt += "## 相关剧情片段\n\n"
        context_prompt += "\n\n".join(chunk_texts)
        context_prompt += "\n\n"
    
    # 添加相关摘要
    if rag_context.summaries:
        summary_lines = rag_context.summary_lines()
        context_prompt += "## 相关章节摘要\n\n"
        context_prompt += "\n".join(summary_lines)
        context_prompt += "\n\n"
    
    # 5. 调用LLM生成
    writing_prompt = await prompt_service.get_prompt("writing")
    user_message = f"""{context_prompt}

请基于以上上下文信息，生成第{chapter_number}章的内容。

## 章节信息
标题：{outline.title}
大纲：{outline.summary}

## 要求
1. 保持与已有剧情的连贯性
2. 符合角色设定和性格
3. 推进主线剧情
"""
    
    response = await llm_service.get_llm_response(
        system_prompt=writing_prompt,
        conversation_history=[
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        user_id=user_id
    )
    
    return response
```

## 依赖关系

### 内部依赖
- [`LLMService`](backend/app/services/llm_service.py) - 生成查询向量
- [`VectorStoreService`](backend/app/services/vector_store_service.py) - 执行向量检索
- [`settings`](backend/app/core/config.py) - 读取配置（是否启用向量库）

### 数据结构
- [`RetrievedChunk`](backend/app/services/vector_store_service.py) - 检索到的片段
- [`RetrievedSummary`](backend/app/services/vector_store_service.py) - 检索到的摘要

### 调用方
- [`writer.py`](backend/app/api/routers/writer.py) - 章节生成API

## 配置项

```python
# .env 或 settings
VECTOR_STORE_ENABLED=true              # 启用向量库
EMBEDDING_PROVIDER=openai              # openai 或 ollama
EMBEDDING_MODEL=text-embedding-3-small # 向量模型
VECTOR_TOP_K_CHUNKS=5                  # 默认检索片段数
VECTOR_TOP_K_SUMMARIES=10              # 默认检索摘要数
```

## 性能特点

### 1. 懒初始化

向量库可选，未启用时不会报错：
```python
if not settings.vector_store_enabled or not self._vector_store:
    return ChapterRAGContext(query=query, chunks=[], summaries=[])
```

### 2. 容错设计

向量生成失败时返回空上下文，不影响生成流程：
```python
if not embedding:
    logger.warning("查询向量生成失败")
    return ChapterRAGContext(query=query, chunks=[], summaries=[])
```

### 3. 并发友好

检索操作是异步的，不会阻塞其他请求。

## 最佳实践

### 1. 查询文本构建

```python
# 好的做法：结合标题和摘要
query_text = f"{outline.title}\n{outline.summary}"

# 不推荐：仅使用标题（信息不足）
query_text = outline.title
```

### 2. Top-K参数调整

```python
# 长章节：增加检索数量
rag_context = await context_service.retrieve_for_generation(
    project_id=project_id,
    query_text=query_text,
    user_id=user_id,
    top_k_chunks=10,       # 更多片段
    top_k_summaries=15      # 更多摘要
)

# 短章节：减少检索数量
rag_context = await context_service.retrieve_for_generation(
    project_id=project_id,
    query_text=query_text,
    user_id=user_id,
    top_k_chunks=3,
    top_k_summaries=5
)
```

### 3. 上下文使用

```python
# 检查是否有检索结果
if rag_context.chunks or rag_context.summaries:
    # 构建增强上下文
    context_prompt = build_context(rag_context)
else:
    # 无检索结果时使用基础提示
    context_prompt = "请基于章节大纲自由创作"
```

## 相关文件

- **LLM服务**: [`backend/app/services/llm_service.py`](backend/app/services/llm_service.py)
- **向量库服务**: [`backend/app/services/vector_store_service.py`](backend/app/services/vector_store_service.py)
- **写作API**: [`backend/app/api/routers/writer.py`](backend/app/api/routers/writer.py)
- **配置**: [`backend/app/core/config.py`](backend/app/core/config.py)