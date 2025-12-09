# RAG系统优化计划

> 版本: 1.1
> 创建日期: 2025-12-08
> 更新日期: 2025-12-08
> 状态: **已实现**
> 目标: 最大化利用项目现有数据资源，提升章节生成的上下文质量和故事连贯性

---

## 实现状态

### Phase 1: 基础优化 (已完成)

| 模块 | 文件 | 状态 |
|------|------|------|
| RAG模块目录 | `backend/app/services/rag/__init__.py` | 已完成 |
| 查询构建器 | `backend/app/services/rag/query_builder.py` | 已完成 |
| 时序检索器 | `backend/app/services/rag/temporal_retriever.py` | 已完成 |
| 上下文构建器 | `backend/app/services/rag/context_builder.py` | 已完成 |
| 上下文压缩器 | `backend/app/services/rag/context_compressor.py` | 已完成 |
| 增强上下文服务 | `backend/app/services/chapter_context_service.py` | 已完成 |
| 章节生成集成 | `backend/app/api/routers/writer/chapter_generation.py` | 已完成 |

### Phase 2: 结构化索引 (已完成)

| 模块 | 文件 | 状态 |
|------|------|------|
| 角色状态索引模型 | `backend/app/models/novel.py` (CharacterStateIndex) | 已完成 |
| 伏笔索引模型 | `backend/app/models/novel.py` (ForeshadowingIndex) | 已完成 |
| 增量索引器 | `backend/app/services/incremental_indexer.py` | 已完成 |
| 伏笔服务 | `backend/app/services/foreshadowing_service.py` | 已完成 |
| 数据库表导出 | `backend/app/models/__init__.py` | 已完成 |
| 章节管理集成 | `backend/app/api/routers/writer/chapter_management.py` | 已完成 |

---

## 目录

1. [现状分析](#1-现状分析)
2. [核心问题诊断](#2-核心问题诊断)
3. [优化目标](#3-优化目标)
4. [数据资源盘点](#4-数据资源盘点)
5. [优化方案详解](#5-优化方案详解)
6. [实施路线图](#6-实施路线图)
7. [技术实现细节](#7-技术实现细节)
8. [评估指标](#8-评估指标)
9. [风险与缓解](#9-风险与缓解)

---

## 1. 现状分析

### 1.1 当前RAG架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      章节生成请求                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  查询构建 (chapter_generation.py)                               │
│  query = 章节标题 + 章节摘要 + 写作要点                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  向量检索 (chapter_context_service.py)                          │
│  - top_k_chunks = 5                                             │
│  - top_k_summaries = 3                                          │
│  - 使用cosine相似度                                             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  上下文构建 (chapter_generation_service.py)                     │
│  - 检索到的chunks (截断至500字)                                 │
│  - 检索到的summaries (截断至300字)                              │
│  - 前一章analysis_data                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  提示词组装 → LLM调用 → 章节生成                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 当前数据流

```
章节选择版本
    │
    ├──→ chapter_ingest_service.py
    │         │
    │         ├──→ 文本切分 (chunk_size=480, overlap=120)
    │         ├──→ 生成chunk embeddings
    │         └──→ 写入 rag_chunks 表
    │
    └──→ chapter_analysis_service.py
              │
              ├──→ LLM分析章节内容
              └──→ 写入 Chapter.analysis_data
                       │
                       ├── metadata (characters, locations, items, tags, tone)
                       ├── summaries (compressed, one_line, keywords)
                       ├── character_states (位置、状态、变化)
                       ├── foreshadowing (planted, resolved, tensions)
                       └── key_events (type, description, importance)
```

### 1.3 现有问题汇总

| 问题类别 | 具体问题 | 影响程度 |
|----------|----------|----------|
| 查询构建 | 仅使用标题+摘要，缺乏语义扩展 | 高 |
| 查询构建 | 未提取涉及角色进行针对性检索 | 高 |
| 检索策略 | 纯向量检索，无混合检索 | 中 |
| 检索策略 | 固定top_k，不考虑章节复杂度 | 中 |
| 检索策略 | 无时序感知，可能检索到无关章节 | 高 |
| 数据利用 | analysis_data未充分利用 | 高 |
| 数据利用 | 蓝图角色信息未参与检索 | 高 |
| 数据利用 | 伏笔追踪系统与RAG割裂 | 高 |
| 上下文构建 | 内容截断可能丢失关键信息 | 中 |
| 上下文构建 | 缺乏上下文优先级排序 | 中 |
| 数据同步 | 编辑后向量数据不自动更新 | 中 |

---

## 2. 核心问题诊断

### 2.1 问题一：查询语义贫乏

**现状代码** (`chapter_generation.py:85-93`):
```python
query_parts = []
if outline.get('title'):
    query_parts.append(f"章节标题: {outline['title']}")
if outline.get('summary'):
    query_parts.append(f"章节摘要: {outline['summary']}")
if outline.get('writing_notes'):
    query_parts.append(f"写作要点: {outline['writing_notes']}")
query = "\n".join(query_parts)
```

**问题分析**:
- 查询仅包含当前章节的静态信息
- 未利用蓝图中的角色名称进行匹配
- 未考虑需要回收的伏笔
- 未考虑前一章的结束状态

### 2.2 问题二：结构化数据未参与检索

**现有的analysis_data结构**:
```json
{
  "metadata": {
    "characters": ["李明", "王芳"],
    "locations": ["青云山"],
    "items": ["玄铁剑"]
  },
  "character_states": {
    "李明": {
      "location": "山顶",
      "status": "受伤",
      "changes": ["获得秘籍"]
    }
  },
  "foreshadowing": {
    "planted": [{"description": "神秘老人的预言", "priority": "high"}],
    "tensions": ["身世之谜未解"]
  }
}
```

**问题分析**:
- 这些宝贵的结构化数据仅用于展示，未参与检索
- 无法基于角色名查找该角色的历史状态
- 无法追踪特定伏笔的埋设和回收

### 2.3 问题三：检索缺乏时序意识

**现状**:
- 向量检索仅基于语义相似度
- 第100章生成时可能检索到第5章的内容（语义相似但时间久远）
- 未优先返回临近章节的相关内容

### 2.4 问题四：蓝图数据利用不足

**蓝图中可用的信息**:
- `BlueprintCharacter`: 所有角色的名称、身份、性格、目标、能力
- `BlueprintRelationship`: 角色之间的关系
- `world_setting`: 世界观规则、地点、派系

**现状**:
- 这些信息仅在初次生成时使用
- 未与RAG检索联动
- 无法验证生成内容是否符合既定设定

---

## 3. 优化目标

### 3.1 核心目标

1. **连贯性提升**: 确保生成章节与前文保持人物、情节、设定的一致性
2. **伏笔管理**: 自动追踪埋设的伏笔，在合适时机提醒回收
3. **角色一致性**: 保证角色名称、性格、位置状态的连续性
4. **检索精准度**: 提高检索结果与当前章节的相关性

### 3.2 量化指标

| 指标 | 当前估计 | 目标值 |
|------|----------|--------|
| 角色名称一致性 | 85% | 99% |
| 伏笔回收提醒率 | 0% | 80% |
| 检索相关性(主观评分) | 6/10 | 8/10 |
| 上下文利用率 | 40% | 85% |

---

## 4. 数据资源盘点

### 4.1 可用于RAG的现有数据

#### 4.1.1 蓝图层数据

| 数据源 | 表/字段 | 可用信息 | 利用方式 |
|--------|---------|----------|----------|
| NovelBlueprint | title, genre, style, tone | 作品元信息 | 生成风格约束 |
| NovelBlueprint | full_synopsis | 完整故事大纲 | 情节方向验证 |
| NovelBlueprint | world_setting | 世界观JSON | 设定一致性检查 |
| BlueprintCharacter | name, identity, personality, goals | 角色设定 | 角色行为验证 |
| BlueprintRelationship | character_from, character_to, description | 人物关系 | 互动合理性 |
| ChapterOutline | title, summary | 章节大纲 | 情节指导 |
| PartOutline | theme, key_events, character_arcs | 部分规划 | 长篇结构参考 |

#### 4.1.2 章节层数据

| 数据源 | 表/字段 | 可用信息 | 利用方式 |
|--------|---------|----------|----------|
| Chapter | real_summary | 实际章节摘要 | RAG检索 |
| Chapter | analysis_data.metadata | 角色/地点/物品列表 | 实体检索 |
| Chapter | analysis_data.character_states | 角色状态快照 | 状态连续性 |
| Chapter | analysis_data.foreshadowing | 伏笔追踪 | 伏笔管理 |
| Chapter | analysis_data.key_events | 关键事件 | 情节参考 |
| ChapterVersion | content | 章节正文 | 向量化源 |

#### 4.1.3 向量存储数据

| 表 | 存储内容 | 检索用途 |
|----|----------|----------|
| rag_chunks | 章节文本片段向量 | 语义相似内容 |
| rag_summaries | 章节摘要向量 | 快速章节定位 |

### 4.2 数据关联图

```
NovelProject
    │
    ├── NovelBlueprint (1:1)
    │       ├── world_setting (JSON)
    │       ├── BlueprintCharacter (1:N) ──────────────────┐
    │       └── BlueprintRelationship (1:N)                │
    │                                                      │
    ├── PartOutline (1:N) [长篇]                           │
    │       └── character_arcs, key_events                 │
    │                                                      │
    ├── ChapterOutline (1:N)                               │
    │       └── title, summary                             │
    │                                                      │
    └── Chapter (1:N)                                      │
            ├── real_summary                               │
            ├── analysis_data ─────────────────────────────┤
            │       ├── metadata.characters ───────────────┼─→ 角色匹配
            │       ├── character_states ──────────────────┼─→ 状态追踪
            │       ├── foreshadowing ─────────────────────┼─→ 伏笔管理
            │       └── key_events                         │
            │                                              │
            └── ChapterVersion (1:N)                       │
                    └── content ──→ rag_chunks             │
                                   rag_summaries           │
                                          │                │
                                          ▼                ▼
                              ┌─────────────────────────────────┐
                              │     增强型RAG检索系统           │
                              │  (利用结构化+向量化数据)        │
                              └─────────────────────────────────┘
```

---

## 5. 优化方案详解

### 5.1 方案一：增强型查询构建

#### 5.1.1 多维查询扩展

**原理**: 将单一查询扩展为多个维度的子查询，分别检索后合并结果。

```python
class EnhancedQueryBuilder:
    """增强型查询构建器"""

    def build_queries(
        self,
        outline: dict,
        blueprint: NovelBlueprint,
        prev_chapter_analysis: Optional[ChapterAnalysisData],
        pending_foreshadowing: List[dict]
    ) -> dict:
        """
        构建多维查询

        Returns:
            {
                "main_query": str,           # 主查询(章节内容相关)
                "character_queries": list,   # 角色相关查询
                "foreshadow_queries": list,  # 伏笔相关查询
                "location_query": str,       # 场景相关查询
            }
        """
        queries = {}

        # 1. 主查询：章节核心内容
        queries["main_query"] = self._build_main_query(outline)

        # 2. 角色查询：提取涉及角色，查找其历史
        involved_characters = self._extract_characters(
            outline, blueprint.characters
        )
        queries["character_queries"] = [
            f"角色 {char.name} 的行动和状态变化"
            for char in involved_characters
        ]

        # 3. 伏笔查询：查找需要回收的伏笔相关内容
        queries["foreshadow_queries"] = [
            f"伏笔: {fs['description']}"
            for fs in pending_foreshadowing
            if self._should_resolve_in_chapter(fs, outline)
        ]

        # 4. 场景查询：如果有明确场景，查找该场景的历史
        if location := self._extract_location(outline):
            queries["location_query"] = f"场景 {location} 中发生的事件"

        return queries

    def _extract_characters(
        self,
        outline: dict,
        blueprint_characters: List[BlueprintCharacter]
    ) -> List[BlueprintCharacter]:
        """从大纲中提取涉及的角色"""
        text = f"{outline.get('title', '')} {outline.get('summary', '')}"
        involved = []
        for char in blueprint_characters:
            if char.name in text:
                involved.append(char)
        return involved
```

#### 5.1.2 实体识别增强

```python
class EntityAwareQueryEnhancer:
    """基于实体的查询增强器"""

    def enhance_query(
        self,
        base_query: str,
        blueprint: NovelBlueprint,
        chapter_number: int
    ) -> str:
        """
        使用蓝图信息增强查询
        """
        enhancements = []

        # 提取查询中提到的角色
        for char in blueprint.characters:
            if char.name in base_query:
                # 添加角色的关键属性作为查询扩展
                enhancements.append(f"[角色:{char.name}|{char.identity}]")

        # 提取地点
        if blueprint.world_setting:
            locations = blueprint.world_setting.get('key_locations', [])
            for loc in locations:
                if loc['name'] in base_query:
                    enhancements.append(f"[地点:{loc['name']}]")

        if enhancements:
            return f"{base_query}\n关联实体: {' '.join(enhancements)}"
        return base_query
```

### 5.2 方案二：结构化数据索引

#### 5.2.1 角色状态索引

**目标**: 快速查询任意角色在任意章节的状态。

```python
# 新增表结构
class CharacterStateIndex(Base):
    """角色状态索引表 - 支持快速角色状态查询"""
    __tablename__ = "character_state_index"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    project_id = Column(String(36), ForeignKey("novels.id"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    character_name = Column(String(255), nullable=False, index=True)
    location = Column(String(255))
    status = Column(Text)
    changes = Column(JSON)  # List[str]
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_char_state_project_char', 'project_id', 'character_name'),
        Index('idx_char_state_project_chapter', 'project_id', 'chapter_number'),
    )
```

**查询示例**:
```python
async def get_character_history(
    self,
    project_id: str,
    character_name: str,
    before_chapter: int,
    limit: int = 5
) -> List[CharacterStateIndex]:
    """获取角色在指定章节之前的状态历史"""
    query = select(CharacterStateIndex).where(
        CharacterStateIndex.project_id == project_id,
        CharacterStateIndex.character_name == character_name,
        CharacterStateIndex.chapter_number < before_chapter
    ).order_by(
        CharacterStateIndex.chapter_number.desc()
    ).limit(limit)

    result = await session.execute(query)
    return result.scalars().all()
```

#### 5.2.2 伏笔追踪索引

**目标**: 管理伏笔的埋设、状态和回收。

```python
class ForeshadowingIndex(Base):
    """伏笔追踪索引表"""
    __tablename__ = "foreshadowing_index"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("novels.id"), nullable=False)

    # 埋设信息
    planted_chapter = Column(Integer, nullable=False)  # 埋设章节
    description = Column(Text, nullable=False)         # 伏笔描述
    original_text = Column(Text)                       # 原文片段
    category = Column(String(64))  # character_secret/plot_twist/item_mystery/world_rule
    priority = Column(String(16), default='medium')    # high/medium/low
    related_entities = Column(JSON)                    # 关联角色/物品

    # 回收信息
    status = Column(String(32), default='pending')     # pending/resolved/abandoned
    resolved_chapter = Column(Integer)                 # 回收章节
    resolution = Column(Text)                          # 回收方式

    # 提醒设置
    remind_after_chapter = Column(Integer)             # 建议回收章节(可选)
    remind_priority = Column(Integer, default=0)       # 提醒优先级

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_foreshadow_project_status', 'project_id', 'status'),
        Index('idx_foreshadow_project_planted', 'project_id', 'planted_chapter'),
    )
```

**伏笔服务**:
```python
class ForeshadowingService:
    """伏笔管理服务"""

    async def get_pending_foreshadowing(
        self,
        project_id: str,
        current_chapter: int,
        include_overdue: bool = True
    ) -> List[ForeshadowingIndex]:
        """
        获取待回收的伏笔

        Args:
            project_id: 项目ID
            current_chapter: 当前章节号
            include_overdue: 是否包含过期未回收的伏笔
        """
        conditions = [
            ForeshadowingIndex.project_id == project_id,
            ForeshadowingIndex.status == 'pending'
        ]

        if include_overdue:
            # 包含所有pending状态的伏笔
            pass
        else:
            # 只包含建议在当前或之前回收的
            conditions.append(
                or_(
                    ForeshadowingIndex.remind_after_chapter <= current_chapter,
                    ForeshadowingIndex.remind_after_chapter.is_(None)
                )
            )

        query = select(ForeshadowingIndex).where(*conditions).order_by(
            ForeshadowingIndex.priority.desc(),
            ForeshadowingIndex.planted_chapter.asc()
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def suggest_resolution_chapters(
        self,
        project_id: str,
        total_chapters: int
    ) -> Dict[str, int]:
        """
        根据故事结构建议伏笔回收章节

        Returns:
            {foreshadowing_id: suggested_chapter}
        """
        pending = await self.get_pending_foreshadowing(project_id, total_chapters)
        suggestions = {}

        for fs in pending:
            planted = fs.planted_chapter
            priority = fs.priority

            # 根据优先级和故事进度建议回收时机
            if priority == 'high':
                # 高优先级伏笔应在3-10章内回收
                suggested = min(planted + 5, int(total_chapters * 0.8))
            elif priority == 'medium':
                # 中优先级可以在中后期回收
                suggested = min(planted + 15, int(total_chapters * 0.9))
            else:
                # 低优先级可以在结尾前回收
                suggested = int(total_chapters * 0.95)

            suggestions[fs.id] = suggested

        return suggestions
```

### 5.3 方案三：时序感知检索

#### 5.3.1 时序权重算法

```python
class TemporalAwareRetriever:
    """时序感知检索器"""

    def __init__(
        self,
        recency_weight: float = 0.3,  # 时序权重
        similarity_weight: float = 0.7  # 相似度权重
    ):
        self.recency_weight = recency_weight
        self.similarity_weight = similarity_weight

    def compute_final_score(
        self,
        similarity_score: float,
        source_chapter: int,
        target_chapter: int,
        total_chapters: int
    ) -> float:
        """
        计算综合得分 = 相似度得分 * 相似度权重 + 时序得分 * 时序权重

        时序得分计算:
        - 相邻章节得分最高
        - 距离越远得分越低
        - 使用指数衰减
        """
        # 计算章节距离(归一化)
        distance = abs(target_chapter - source_chapter)
        max_distance = total_chapters
        normalized_distance = distance / max_distance

        # 指数衰减: 距离为0时得分1，距离增加时快速衰减
        recency_score = math.exp(-3 * normalized_distance)

        # 综合得分
        final_score = (
            similarity_score * self.similarity_weight +
            recency_score * self.recency_weight
        )

        return final_score

    async def retrieve_with_temporal_awareness(
        self,
        query_embedding: List[float],
        project_id: str,
        target_chapter: int,
        total_chapters: int,
        top_k: int = 10
    ) -> List[RetrievedChunk]:
        """
        带时序感知的检索
        """
        # 1. 先检索更多候选(2倍top_k)
        candidates = await self.vector_store.search_chunks(
            query_embedding, project_id, top_k=top_k * 2
        )

        # 2. 重新计算综合得分
        scored_candidates = []
        for chunk in candidates:
            final_score = self.compute_final_score(
                similarity_score=chunk.score,
                source_chapter=chunk.chapter_number,
                target_chapter=target_chapter,
                total_chapters=total_chapters
            )
            scored_candidates.append((chunk, final_score))

        # 3. 按综合得分排序，取top_k
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        return [chunk for chunk, score in scored_candidates[:top_k]]
```

#### 5.3.2 临近章节优先策略

```python
class NearbyChapterPrioritizer:
    """临近章节优先器"""

    def prioritize_nearby_chapters(
        self,
        retrieved_chunks: List[RetrievedChunk],
        target_chapter: int,
        nearby_bonus: float = 0.2,
        nearby_range: int = 5
    ) -> List[RetrievedChunk]:
        """
        为临近章节的检索结果加分

        Args:
            nearby_bonus: 临近章节的额外加分
            nearby_range: 定义"临近"的章节范围
        """
        boosted = []
        for chunk in retrieved_chunks:
            distance = abs(chunk.chapter_number - target_chapter)
            if distance <= nearby_range:
                # 临近章节加分，越近加分越多
                bonus = nearby_bonus * (1 - distance / nearby_range)
                new_score = min(chunk.score + bonus, 1.0)
                chunk.score = new_score
            boosted.append(chunk)

        # 重新排序
        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted
```

### 5.4 方案四：混合检索策略

#### 5.4.1 向量+关键词混合

```python
class HybridRetriever:
    """混合检索器：向量检索 + BM25关键词检索"""

    def __init__(
        self,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4
    ):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        project_id: str,
        top_k: int = 10
    ) -> List[RetrievedChunk]:
        """
        混合检索
        """
        # 1. 向量检索
        vector_results = await self.vector_store.search_chunks(
            query_embedding, project_id, top_k=top_k * 2
        )

        # 2. 关键词检索(使用SQLite FTS或简单LIKE)
        keyword_results = await self.keyword_search(
            query, project_id, top_k=top_k * 2
        )

        # 3. 融合结果(Reciprocal Rank Fusion)
        return self._rrf_fusion(
            vector_results,
            keyword_results,
            top_k
        )

    def _rrf_fusion(
        self,
        vector_results: List[RetrievedChunk],
        keyword_results: List[RetrievedChunk],
        top_k: int,
        k: int = 60  # RRF常数
    ) -> List[RetrievedChunk]:
        """
        Reciprocal Rank Fusion算法

        RRF_score = sum(1 / (k + rank_i))
        """
        scores = {}
        chunk_map = {}

        # 向量结果打分
        for rank, chunk in enumerate(vector_results):
            chunk_id = f"{chunk.chapter_number}:{chunk.metadata.get('chunk_index', 0)}"
            scores[chunk_id] = scores.get(chunk_id, 0) + self.vector_weight / (k + rank)
            chunk_map[chunk_id] = chunk

        # 关键词结果打分
        for rank, chunk in enumerate(keyword_results):
            chunk_id = f"{chunk.chapter_number}:{chunk.metadata.get('chunk_index', 0)}"
            scores[chunk_id] = scores.get(chunk_id, 0) + self.keyword_weight / (k + rank)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = chunk

        # 排序并返回top_k
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [chunk_map[cid] for cid in sorted_ids[:top_k]]

    async def keyword_search(
        self,
        query: str,
        project_id: str,
        top_k: int
    ) -> List[RetrievedChunk]:
        """
        关键词检索实现
        """
        # 提取关键词(简单分词)
        keywords = self._extract_keywords(query)

        # 构建SQL查询
        conditions = [f"content LIKE '%{kw}%'" for kw in keywords[:5]]
        where_clause = " OR ".join(conditions)

        sql = f"""
            SELECT id, project_id, chapter_number, chunk_index,
                   chapter_title, content, metadata
            FROM rag_chunks
            WHERE project_id = ? AND ({where_clause})
            LIMIT ?
        """

        # 执行查询并转换为RetrievedChunk
        # ...
```

### 5.5 方案五：上下文智能构建

#### 5.5.1 分层上下文结构

```python
class SmartContextBuilder:
    """智能上下文构建器"""

    def build_generation_context(
        self,
        project_id: str,
        chapter_number: int,
        outline: dict,
        blueprint: NovelBlueprint,
        rag_context: ChapterRAGContext,
        prev_analysis: Optional[ChapterAnalysisData],
        pending_foreshadowing: List[ForeshadowingIndex]
    ) -> GenerationContext:
        """
        构建分层上下文

        层级结构:
        1. 必需层(Must-have): 必须包含，影响正确性
        2. 重要层(Important): 强烈建议包含，影响连贯性
        3. 参考层(Reference): 可选包含，提升丰富度
        """
        context = GenerationContext()

        # === 必需层 ===
        context.must_have = {
            # 蓝图核心信息
            "blueprint_summary": blueprint.one_sentence_summary,
            "genre": blueprint.genre,
            "tone": blueprint.tone,

            # 角色名称列表(防止改名)
            "character_names": [c.name for c in blueprint.characters],

            # 当前章节大纲
            "current_outline": outline,

            # 前一章结尾状态(如有)
            "prev_ending_state": self._get_prev_ending_state(prev_analysis),
        }

        # === 重要层 ===
        context.important = {
            # 涉及角色的详细信息
            "involved_characters": self._get_involved_characters(
                outline, blueprint.characters
            ),

            # 涉及角色的关系
            "character_relationships": self._get_relevant_relationships(
                outline, blueprint.relationships
            ),

            # 待回收的高优先级伏笔
            "high_priority_foreshadowing": [
                fs for fs in pending_foreshadowing
                if fs.priority == 'high'
            ],

            # 前一章角色状态
            "prev_character_states": prev_analysis.character_states if prev_analysis else {},

            # RAG检索的最相关摘要
            "relevant_summaries": rag_context.summaries[:3],
        }

        # === 参考层 ===
        context.reference = {
            # 世界观设定
            "world_setting": blueprint.world_setting,

            # RAG检索的文本片段
            "relevant_chunks": rag_context.chunks[:5],

            # 中低优先级伏笔
            "other_foreshadowing": [
                fs for fs in pending_foreshadowing
                if fs.priority != 'high'
            ],

            # 关键事件历史
            "key_events_history": self._get_key_events_history(project_id, chapter_number),
        }

        return context

    def _get_prev_ending_state(
        self,
        prev_analysis: Optional[ChapterAnalysisData]
    ) -> dict:
        """提取前一章的结尾状态"""
        if not prev_analysis:
            return {}

        return {
            "last_location": self._extract_last_location(prev_analysis),
            "character_positions": {
                name: state.location
                for name, state in prev_analysis.character_states.items()
            },
            "unresolved_tensions": prev_analysis.foreshadowing.tensions if prev_analysis.foreshadowing else [],
        }
```

#### 5.5.2 上下文压缩与优先级

```python
class ContextCompressor:
    """上下文压缩器"""

    def __init__(self, max_context_tokens: int = 4000):
        self.max_tokens = max_context_tokens

    def compress_context(
        self,
        context: GenerationContext,
        token_counter: Callable[[str], int]
    ) -> str:
        """
        智能压缩上下文，确保不超过token限制

        优先级: must_have > important > reference
        """
        result_parts = []
        current_tokens = 0

        # 1. 必需层：全部包含
        must_have_text = self._format_must_have(context.must_have)
        must_have_tokens = token_counter(must_have_text)
        if must_have_tokens > self.max_tokens * 0.5:
            # 必需层太大，需要精简
            must_have_text = self._compress_must_have(
                context.must_have,
                int(self.max_tokens * 0.5),
                token_counter
            )
        result_parts.append(must_have_text)
        current_tokens += token_counter(must_have_text)

        # 2. 重要层：尽量包含
        remaining_tokens = self.max_tokens - current_tokens
        if remaining_tokens > 500:
            important_text = self._format_important(
                context.important,
                max_tokens=int(remaining_tokens * 0.7),
                token_counter=token_counter
            )
            result_parts.append(important_text)
            current_tokens += token_counter(important_text)

        # 3. 参考层：按需包含
        remaining_tokens = self.max_tokens - current_tokens
        if remaining_tokens > 300:
            reference_text = self._format_reference(
                context.reference,
                max_tokens=remaining_tokens,
                token_counter=token_counter
            )
            result_parts.append(reference_text)

        return "\n\n".join(result_parts)
```

### 5.6 方案六：数据同步机制

#### 5.6.1 自动向量更新

```python
class ChapterUpdateHandler:
    """章节更新处理器"""

    async def on_chapter_content_changed(
        self,
        project_id: str,
        chapter_number: int,
        new_content: str
    ):
        """
        章节内容变更时的处理
        """
        # 1. 删除旧的向量数据
        await self.vector_store.delete_chapter_chunks(project_id, chapter_number)

        # 2. 重新入库
        await self.ingest_service.ingest_chapter(
            project_id=project_id,
            chapter_number=chapter_number,
            content=new_content,
            title=await self._get_chapter_title(project_id, chapter_number)
        )

        # 3. 重新分析(可选，异步执行)
        asyncio.create_task(
            self.analysis_service.analyze_chapter(
                content=new_content,
                title=await self._get_chapter_title(project_id, chapter_number),
                chapter_number=chapter_number,
                novel_title=await self._get_novel_title(project_id)
            )
        )

    async def on_chapter_version_selected(
        self,
        project_id: str,
        chapter_number: int,
        version_id: int
    ):
        """
        版本选择时的处理
        """
        # 获取版本内容
        version = await self.get_version(version_id)

        # 触发内容变更处理
        await self.on_chapter_content_changed(
            project_id, chapter_number, version.content
        )
```

#### 5.6.2 增量索引更新

```python
class IncrementalIndexer:
    """增量索引器"""

    async def update_character_state_index(
        self,
        project_id: str,
        chapter_number: int,
        analysis_data: ChapterAnalysisData
    ):
        """
        更新角色状态索引
        """
        # 删除该章节的旧索引
        await self.session.execute(
            delete(CharacterStateIndex).where(
                CharacterStateIndex.project_id == project_id,
                CharacterStateIndex.chapter_number == chapter_number
            )
        )

        # 插入新索引
        for char_name, state in analysis_data.character_states.items():
            index_entry = CharacterStateIndex(
                project_id=project_id,
                chapter_number=chapter_number,
                character_name=char_name,
                location=state.location,
                status=state.status,
                changes=state.changes
            )
            self.session.add(index_entry)

        await self.session.flush()

    async def update_foreshadowing_index(
        self,
        project_id: str,
        chapter_number: int,
        foreshadowing_data: ForeshadowingData
    ):
        """
        更新伏笔索引
        """
        # 处理新埋设的伏笔
        for planted in foreshadowing_data.planted:
            existing = await self._find_similar_foreshadowing(
                project_id, planted.description
            )

            if not existing:
                # 新伏笔，创建索引
                new_fs = ForeshadowingIndex(
                    project_id=project_id,
                    planted_chapter=chapter_number,
                    description=planted.description,
                    original_text=planted.original_text,
                    category=planted.category,
                    priority=planted.priority,
                    related_entities=planted.related_entities,
                    status='pending'
                )
                self.session.add(new_fs)

        # 处理回收的伏笔
        for resolved in foreshadowing_data.resolved:
            if fs_id := resolved.get('id'):
                await self.session.execute(
                    update(ForeshadowingIndex).where(
                        ForeshadowingIndex.id == fs_id
                    ).values(
                        status='resolved',
                        resolved_chapter=chapter_number,
                        resolution=resolved.get('resolution')
                    )
                )

        await self.session.flush()
```

---

## 6. 实施路线图

### 6.1 阶段划分

```
Phase 1: 基础优化 (1-2周)
├── 查询增强
├── 时序感知
└── 上下文优先级

Phase 2: 结构化索引 (2-3周)
├── 角色状态索引
├── 伏笔追踪索引
└── 索引自动更新

Phase 3: 高级检索 (2-3周)
├── 混合检索
├── 实体感知检索
└── 上下文压缩

Phase 4: 智能管理 (1-2周)
├── 伏笔回收建议
├── 一致性检查
└── 质量评估
```

### 6.2 Phase 1: 基础优化

**目标**: 在不改变数据结构的情况下提升检索质量

**任务清单**:

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 1.1 实现EnhancedQueryBuilder | P0 | 4h | - |
| 1.2 实现TemporalAwareRetriever | P0 | 4h | - |
| 1.3 实现SmartContextBuilder | P0 | 6h | 1.1 |
| 1.4 修改chapter_generation.py使用新组件 | P0 | 4h | 1.1-1.3 |
| 1.5 测试与调优 | P0 | 4h | 1.4 |

**交付物**:
- `services/enhanced_query_builder.py`
- `services/temporal_retriever.py`
- `services/smart_context_builder.py`
- 修改后的`chapter_generation.py`

### 6.3 Phase 2: 结构化索引

**目标**: 建立角色状态和伏笔追踪的索引系统

**任务清单**:

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 2.1 创建CharacterStateIndex模型 | P0 | 2h | - |
| 2.2 创建ForeshadowingIndex模型 | P0 | 2h | - |
| 2.3 数据库迁移 | P0 | 1h | 2.1, 2.2 |
| 2.4 实现IncrementalIndexer | P0 | 6h | 2.3 |
| 2.5 修改chapter_analysis_service集成索引 | P0 | 4h | 2.4 |
| 2.6 实现ForeshadowingService | P1 | 6h | 2.3 |
| 2.7 历史数据迁移脚本 | P1 | 4h | 2.4 |
| 2.8 测试 | P0 | 4h | 2.5, 2.6 |

**交付物**:
- `models/character_state_index.py`
- `models/foreshadowing_index.py`
- `services/incremental_indexer.py`
- `services/foreshadowing_service.py`
- 数据库迁移文件

### 6.4 Phase 3: 高级检索

**目标**: 实现混合检索和实体感知检索

**任务清单**:

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 3.1 实现HybridRetriever | P1 | 8h | Phase 1 |
| 3.2 实现EntityAwareQueryEnhancer | P1 | 6h | Phase 2 |
| 3.3 实现ContextCompressor | P1 | 6h | - |
| 3.4 集成到chapter_context_service | P1 | 4h | 3.1-3.3 |
| 3.5 性能优化 | P2 | 4h | 3.4 |
| 3.6 测试 | P1 | 4h | 3.4 |

**交付物**:
- `services/hybrid_retriever.py`
- `services/entity_query_enhancer.py`
- `services/context_compressor.py`

### 6.5 Phase 4: 智能管理

**目标**: 提供伏笔回收建议和一致性检查

**任务清单**:

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 4.1 实现伏笔回收建议算法 | P2 | 6h | Phase 2 |
| 4.2 实现一致性检查器 | P2 | 8h | Phase 2 |
| 4.3 前端伏笔管理界面 | P2 | 8h | 4.1 |
| 4.4 前端一致性提示 | P2 | 4h | 4.2 |
| 4.5 测试与文档 | P2 | 4h | 4.1-4.4 |

**交付物**:
- 伏笔管理API
- 一致性检查API
- 前端伏笔管理组件

---

## 7. 技术实现细节

### 7.1 目录结构

```
backend/app/
├── models/
│   ├── novel.py                    # 现有模型
│   ├── character_state_index.py    # [新增] 角色状态索引
│   └── foreshadowing_index.py      # [新增] 伏笔索引
│
├── services/
│   ├── chapter_context_service.py  # [修改] 集成新检索器
│   ├── chapter_ingest_service.py   # 现有
│   ├── chapter_analysis_service.py # [修改] 集成索引更新
│   ├── vector_store_service.py     # 现有
│   │
│   ├── rag/                        # [新增] RAG增强模块
│   │   ├── __init__.py
│   │   ├── query_builder.py        # 查询构建器
│   │   ├── temporal_retriever.py   # 时序检索器
│   │   ├── hybrid_retriever.py     # 混合检索器
│   │   ├── context_builder.py      # 上下文构建器
│   │   └── context_compressor.py   # 上下文压缩器
│   │
│   ├── indexing/                   # [新增] 索引模块
│   │   ├── __init__.py
│   │   ├── character_state_indexer.py
│   │   └── foreshadowing_indexer.py
│   │
│   └── consistency/                # [新增] 一致性检查模块
│       ├── __init__.py
│       ├── character_checker.py
│       └── plot_checker.py
│
└── api/routers/
    ├── writer/
    │   └── chapter_generation.py   # [修改] 使用新RAG系统
    └── rag/                        # [新增] RAG管理API
        ├── __init__.py
        └── foreshadowing.py        # 伏笔管理API
```

### 7.2 配置更新

```python
# core/config.py 新增配置

class Settings:
    # ... 现有配置 ...

    # RAG增强配置
    rag_temporal_weight: float = 0.3          # 时序权重
    rag_similarity_weight: float = 0.7        # 相似度权重
    rag_nearby_chapter_range: int = 5         # 临近章节范围
    rag_nearby_bonus: float = 0.2             # 临近章节加分

    # 混合检索配置
    rag_hybrid_enabled: bool = True           # 启用混合检索
    rag_vector_weight: float = 0.6            # 向量检索权重
    rag_keyword_weight: float = 0.4           # 关键词检索权重

    # 上下文配置
    rag_max_context_tokens: int = 4000        # 最大上下文token数
    rag_must_have_ratio: float = 0.4          # 必需层占比
    rag_important_ratio: float = 0.4          # 重要层占比
    rag_reference_ratio: float = 0.2          # 参考层占比

    # 伏笔追踪配置
    foreshadowing_remind_default_chapters: int = 10  # 默认提醒章节间隔
    foreshadowing_high_priority_chapters: int = 5    # 高优先级提醒间隔
```

### 7.3 API设计

#### 7.3.1 伏笔管理API

```python
# api/routers/rag/foreshadowing.py

@router.get("/novels/{project_id}/foreshadowing")
async def list_foreshadowing(
    project_id: str,
    status: Optional[str] = Query(None, enum=['pending', 'resolved', 'abandoned']),
    priority: Optional[str] = Query(None, enum=['high', 'medium', 'low']),
    service: ForeshadowingService = Depends(get_foreshadowing_service)
) -> List[ForeshadowingSchema]:
    """获取项目的伏笔列表"""
    pass

@router.get("/novels/{project_id}/foreshadowing/pending")
async def get_pending_foreshadowing(
    project_id: str,
    current_chapter: int,
    include_suggestions: bool = Query(True),
    service: ForeshadowingService = Depends(get_foreshadowing_service)
) -> PendingForeshadowingResponse:
    """获取待回收的伏笔及回收建议"""
    pass

@router.patch("/novels/{project_id}/foreshadowing/{fs_id}")
async def update_foreshadowing(
    project_id: str,
    fs_id: str,
    update_data: ForeshadowingUpdate,
    service: ForeshadowingService = Depends(get_foreshadowing_service)
) -> ForeshadowingSchema:
    """更新伏笔状态（手动标记回收/放弃）"""
    pass
```

#### 7.3.2 角色状态API

```python
# api/routers/rag/character_state.py

@router.get("/novels/{project_id}/characters/{character_name}/history")
async def get_character_history(
    project_id: str,
    character_name: str,
    before_chapter: Optional[int] = None,
    limit: int = Query(10, le=50),
    service: CharacterStateService = Depends(get_character_state_service)
) -> List[CharacterStateSchema]:
    """获取角色的状态历史"""
    pass

@router.get("/novels/{project_id}/chapters/{chapter_number}/character-states")
async def get_chapter_character_states(
    project_id: str,
    chapter_number: int,
    service: CharacterStateService = Depends(get_character_state_service)
) -> Dict[str, CharacterStateSchema]:
    """获取指定章节的所有角色状态"""
    pass
```

### 7.4 数据库迁移

```python
# alembic/versions/xxx_add_rag_indexes.py

def upgrade():
    # 创建角色状态索引表
    op.create_table(
        'character_state_index',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('novels.id'), nullable=False),
        sa.Column('chapter_number', sa.Integer(), nullable=False),
        sa.Column('character_name', sa.String(255), nullable=False),
        sa.Column('location', sa.String(255)),
        sa.Column('status', sa.Text()),
        sa.Column('changes', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_char_state_project_char', 'character_state_index',
                    ['project_id', 'character_name'])
    op.create_index('idx_char_state_project_chapter', 'character_state_index',
                    ['project_id', 'chapter_number'])

    # 创建伏笔索引表
    op.create_table(
        'foreshadowing_index',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('novels.id'), nullable=False),
        sa.Column('planted_chapter', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('original_text', sa.Text()),
        sa.Column('category', sa.String(64)),
        sa.Column('priority', sa.String(16), server_default='medium'),
        sa.Column('related_entities', sa.JSON()),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('resolved_chapter', sa.Integer()),
        sa.Column('resolution', sa.Text()),
        sa.Column('remind_after_chapter', sa.Integer()),
        sa.Column('remind_priority', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_foreshadow_project_status', 'foreshadowing_index',
                    ['project_id', 'status'])
    op.create_index('idx_foreshadow_project_planted', 'foreshadowing_index',
                    ['project_id', 'planted_chapter'])

def downgrade():
    op.drop_table('foreshadowing_index')
    op.drop_table('character_state_index')
```

---

## 8. 评估指标

### 8.1 定量指标

| 指标 | 测量方法 | 基线 | 目标 |
|------|----------|------|------|
| 角色名称一致性 | 生成内容中角色名与蓝图匹配率 | 85% | 99% |
| 伏笔回收率 | 已回收伏笔/应回收伏笔 | N/A | 80% |
| 检索Recall@10 | 人工标注相关内容的召回率 | 60% | 85% |
| 检索Precision@5 | Top5结果的准确率 | 50% | 75% |
| 上下文利用率 | 生成内容引用上下文的比例 | 40% | 70% |
| 生成延迟 | 单章节生成时间 | 30s | <35s |

### 8.2 定性指标

| 指标 | 评估方法 |
|------|----------|
| 故事连贯性 | 人工阅读评分(1-10) |
| 角色行为合理性 | 人工评估是否符合人设 |
| 情节自然度 | 人工评估情节过渡是否自然 |
| 伏笔回收质量 | 人工评估回收方式是否合理 |

### 8.3 测试用例

```python
# tests/test_rag_optimization.py

class TestEnhancedQueryBuilder:
    """查询构建器测试"""

    def test_character_extraction(self):
        """测试从大纲中提取角色"""
        pass

    def test_foreshadow_query_generation(self):
        """测试伏笔相关查询生成"""
        pass

class TestTemporalRetriever:
    """时序检索器测试"""

    def test_nearby_chapter_bonus(self):
        """测试临近章节加分"""
        pass

    def test_temporal_score_computation(self):
        """测试时序得分计算"""
        pass

class TestForeshadowingService:
    """伏笔服务测试"""

    def test_pending_foreshadowing_retrieval(self):
        """测试获取待回收伏笔"""
        pass

    def test_resolution_suggestion(self):
        """测试回收建议生成"""
        pass

class TestIntegration:
    """集成测试"""

    async def test_full_generation_pipeline(self):
        """测试完整生成流程"""
        pass

    async def test_character_consistency(self):
        """测试角色一致性"""
        pass
```

---

## 9. 风险与缓解

### 9.1 技术风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 混合检索增加延迟 | 中 | 中 | 异步并行检索；结果缓存 |
| 索引数据不一致 | 中 | 高 | 事务保证；定期校验脚本 |
| 上下文过长导致成本增加 | 高 | 中 | 智能压缩；配置限制 |
| 伏笔自动识别准确率低 | 中 | 中 | 人工确认机制；阈值调整 |

### 9.2 兼容性风险

| 风险 | 缓解措施 |
|------|----------|
| 现有数据迁移 | 提供迁移脚本；支持增量迁移 |
| API变更 | 保持向后兼容；版本化API |
| 配置变更 | 提供默认值；平滑升级 |

### 9.3 回滚计划

```python
# 每个Phase都支持独立回滚

# Phase 1 回滚:
# - 恢复chapter_generation.py到旧版本
# - 新增的service文件不影响现有功能

# Phase 2 回滚:
# - 执行 alembic downgrade -1
# - 删除索引相关service

# Phase 3 回滚:
# - 配置rag_hybrid_enabled=False
# - 恢复chapter_context_service.py

# Phase 4 回滚:
# - 移除前端伏笔管理组件
# - 禁用相关API路由
```

---

## 附录A: 现有数据资源完整清单

### A.1 蓝图数据

| 字段 | 类型 | 用途 |
|------|------|------|
| title | str | 小说标题 |
| genre | str | 题材类别 |
| style | str | 写作风格 |
| tone | str | 叙事基调 |
| one_sentence_summary | str | 一句话总结 |
| full_synopsis | str | 完整大纲 |
| world_setting | JSON | 世界观设定 |
| total_chapters | int | 总章节数 |

### A.2 角色数据

| 字段 | 类型 | 用途 |
|------|------|------|
| name | str | 角色名(核心) |
| identity | str | 身份职位 |
| personality | str | 性格描述 |
| goals | str | 目标动机 |
| abilities | str | 能力技能 |
| relationship_to_protagonist | str | 与主角关系 |

### A.3 章节分析数据

| 字段路径 | 类型 | 用途 |
|----------|------|------|
| metadata.characters | List[str] | 出场角色 |
| metadata.locations | List[str] | 场景地点 |
| metadata.items | List[str] | 重要物品 |
| metadata.tags | List[str] | 章节标签 |
| metadata.tone | str | 情感基调 |
| metadata.timeline_marker | str | 时间标记 |
| summaries.compressed | str | 压缩摘要 |
| summaries.one_line | str | 一句话摘要 |
| summaries.keywords | List[str] | 关键词 |
| character_states.{name}.location | str | 角色位置 |
| character_states.{name}.status | str | 角色状态 |
| character_states.{name}.changes | List[str] | 本章变化 |
| foreshadowing.planted | List[dict] | 埋设伏笔 |
| foreshadowing.resolved | List[dict] | 回收伏笔 |
| foreshadowing.tensions | List[str] | 未解悬念 |
| key_events | List[dict] | 关键事件 |

---

## 附录B: 参考资料

1. [LangChain RAG最佳实践](https://python.langchain.com/docs/use_cases/question_answering/)
2. [向量检索优化技术](https://www.pinecone.io/learn/vector-search/)
3. [Reciprocal Rank Fusion算法](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
4. [小说写作AI辅助研究](https://arxiv.org/abs/2305.14752)

---

*文档版本历史*:
- v1.0 (2025-12-08): 初始版本
