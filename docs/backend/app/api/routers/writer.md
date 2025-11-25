
# backend/app/api/routers/writer.py - 章节写作核心API

## 文件概述

提供小说章节写作的完整功能API，包括章节生成、版本管理、评估、编辑、大纲管理和部分大纲（长篇小说分层）等核心功能。这是系统最复杂和最重要的API文件。

**文件路径：** `backend/app/api/routers/writer.py`  
**代码行数：** 1538 行  
**复杂度：** ⭐⭐⭐⭐⭐ 极其复杂

## 核心功能模块

### 1. 章节生成
- 多版本并行生成
- RAG检索上下文增强
- 分层摘要构建
- 并发控制与优化

### 2. 版本管理
- 版本选择
- 版本重试
- 摘要自动生成
- 向量库同步

### 3. 章节评估
- AI多维度评审
- 版本对比分析

### 4. 章节编辑
- 内容直接编辑
- 摘要重新生成
- 向量库更新

### 5. 大纲灵活管理
- 增量生成
- 删除最新N章
- 单章重新生成

### 6. 部分大纲（长篇小说）
- 分层大纲生成
- 批量并发生成
- 中断恢复机制
- 进度跟踪

## API端点总览

| 方法 | 路径 | 功能 | 复杂度 |
|------|------|------|--------|
| POST | `/api/writer/novels/{project_id}/chapters/generate` | 生成章节 | ⭐⭐⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapters/select` | 选择版本 | ⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapters/retry-version` | 重试版本 | ⭐⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapters/evaluate` | 评估章节 | ⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapters/edit` | 编辑章节 | ⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapters/delete` | 删除章节 | ⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapters/update-outline` | 更新大纲 | ⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapter-outlines/generate-count` | 增量生成大纲 | ⭐⭐⭐⭐ |
| DELETE | `/api/writer/novels/{project_id}/chapter-outlines/delete-latest` | 删除最新大纲 | ⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/chapter-outlines/{chapter_number}/regenerate` | 重新生成单章 | ⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/parts/generate` | 生成部分大纲 | ⭐⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/parts/{part_number}/chapters` | 生成部分章节 | ⭐⭐⭐⭐ |
| POST | `/api/writer/novels/{project_id}/parts/batch-generate` | 批量生成 | ⭐⭐⭐⭐⭐ |
| GET | `/api/writer/novels/{project_id}/parts/progress` | 查询进度 | ⭐⭐ |

## 核心功能详解

### 1. 章节生成（最核心）

```python
@router.post("/novels/{project_id}/chapters/generate", response_model=NovelProjectSchema)
async def generate_chapter(
    project_id: str,
    request: GenerateChapterRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
```

**功能：** 为指定章节生成多个版本的内容，使用RAG检索增强上下文

#### 阶段1：前情摘要构建

**分层摘要策略：**
```python
def _build_layered_summary(completed_chapters: List[Dict], current_chapter_number: int) -> str:
    """
    构建分层摘要：
    - 最近10章：完整摘要（每章50-100字）
    - 其余章节：超简摘要（每章1句话，约20字）
    
    平衡完整性与token消耗
    """
    recent_threshold = max(1, current_chapter_number - 10)
    
    for ch in completed_chapters:
        chapter_num = ch['chapter_number']
        if chapter_num >= recent_threshold:
            # 最近10章：完整摘要
            recent_summaries.append(f"- 第{chapter_num}章《{title}》：{summary}")
        else:
            # 早期章节：只保留第一句话
            brief = summary.split('。')[0]
            old_summaries.append(f"- 第{chapter_num}章：{brief}")
```

**为什么使用分层摘要？**
- 完整摘要：保证最近情节的连贯性
- 超简摘要：控制总token数，避免超出限制
- 动态调整：根据当前章节号自动选择范围

#### 阶段2：RAG上下文检索

```python
# 初始化向量检索服务
vector_store = VectorStoreService() if settings.vector_store_enabled else None
context_service = ChapterContextService(llm_service, vector_store)

# 构建检索查询
query_parts = [outline_title, outline_summary]
if request.writing_notes:
    query_parts.append(request.writing_notes)
rag_query = "\n".join(query_parts)

# 执行检索
rag_context = await context_service.retrieve_for_generation(
    project_id=project_id,
    query_text=rag_query,
    user_id=desktop_user.id,
)

# 提取检索结果
rag_chunks_text = "\n\n".join(rag_context.chunk_texts())
rag_summaries_text = "\n".join(rag_context.summary_lines())
```

**RAG检索增强的作用：**
- **剧情一致性**：检索相关章节，避免前后矛盾
- **角色连贯**：获取角色之前的行为和对话
- **世界观统一**：确保设定不冲突

#### 阶段3：构建写作提示词

```python
# 组装提示词各部分
prompt_sections = [
    ("[世界蓝图](JSON)", blueprint_text),
    ("[前情摘要]", completed_section),      # 分层摘要
    ("[上一章摘要]", previous_summary_text),
    ("[上一章结尾]", previous_tail_excerpt),
    ("[检索到的剧情上下文](Markdown)", rag_chunks_text),
    ("[检索到的章节摘要]", rag_summaries_text),
    ("[当前章节目标]", f"标题：{outline_title}\n摘要：{outline_summary}\n写作要求：{writing_notes}"),
]

prompt_input = "\n\n".join(f"{title}\n{content}" for title, content in prompt_sections)
```

#### 阶段4：多版本并行生成

**版本数量配置：**
```python
async def _resolve_version_count(session: AsyncSession) -> int:
    # 优先级1：数据库配置
    record = await repo.get_by_key("writer.chapter_versions")
    if record:
        return int(record.value)
    
    # 优先级2：环境变量
    env_value = os.getenv("WRITER_CHAPTER_VERSION_COUNT")
    if env_value:
        return int(env_value)
    
    # 优先级3：默认值
    return 3
```

**并行生成策略：**
```python
async def _generate_single_version(idx: int) -> Dict:
    """生成单个版本"""
    response = await llm_service.get_llm_response(
        system_prompt=writer_prompt,
        conversation_history=[{"role": "user", "content": prompt_input}],
        temperature=0.75,  # 平衡创意性与一致性
        user_id=desktop_user.id,
        timeout=600.0,
        skip_usage_tracking=skip_usage_tracking,  # 并行模式
        cached_config=llm_config,                  # 缓存配置
    )
    return json.loads(unwrap_markdown_json(remove_think_tags(response)))

if settings.writer_parallel_generation:
    # 并行模式：使用信号量控制并发
    semaphore = asyncio.Semaphore(settings.writer_max_parallel_requests)
    
    async def _generate_with_semaphore(idx: int):
        async with semaphore:
            return await _generate_single_version(idx)
    
    # 禁用autoflush，避免并发冲突
    with session.no_autoflush:
        tasks = [_generate_with_semaphore(idx) for idx in range(version_count)]
        raw_versions = await asyncio.gather(*tasks, return_exceptions=True)
else:
    # 串行模式（向后兼容）
    raw_versions = [await _generate_single_version(idx) for idx in range(version_count)]
```

**并行优化要点：**
1. **Semaphore控制**：限制最大并发数（默认3）
2. **缓存LLM配置**：避免并发数据库查询
3. **禁用autoflush**：防止session冲突
4. **异常处理**：使用`return_exceptions=True`捕获单个失败

#### 阶段5：版本保存与状态更新

```python
# 保存所有版本
await novel_service.replace_chapter_versions(chapter, contents, metadata)

# 更新使用统计（并行模式下统一更新）
if skip_usage_tracking:
    successful_count = sum(1 for v in raw_versions if not v.get("content", "").startswith("生成失败:"))
    for _ in range(successful_count):
        await usage_service.increment("api_request_count")

# 清除缓存，返回最新数据
session.expire_all()
return await novel_service.get_project_schema(project_id, desktop_user.id)
```

### 2. 版本选择与向量库同步

```python
@router.post("/novels/{project_id}/chapters/select", response_model=NovelProjectSchema)
async def select_chapter_version(
    project_id: str,
    request: SelectVersionRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
```

**核心流程：**

#### 2.1 选择版本
```python
selected = await novel_service.select_chapter_version(chapter, request.version_index)
```

#### 2.2 生成摘要
```python
if selected and selected.content:
    try:
        summary = await llm_service.get_summary(
            selected.content,
            temperature=0.15,  # 低温度确保摘要稳定
            user_id=desktop_user.id,
            timeout=180.0,
        )
        chapter.real_summary = remove_think_tags(summary)
        await session.commit()
    except Exception as exc:
        