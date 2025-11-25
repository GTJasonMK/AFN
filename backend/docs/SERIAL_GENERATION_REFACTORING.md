# 串行生成改造总结文档

## 改造目标

将所有大纲生成（部分大纲、章节大纲）从一次性生成改为串行生成，确保：
- 小说前后连贯、逻辑一致
- 设定不冲突（角色能力、世界观规则）
- 剧情线索自然延续
- 角色发展符合前文设定
- 最大化利用已生成内容作为上下文

## 改造原则

1. **串行生成**：逐个或分批生成，每次生成都能看到前面已生成的实际内容
2. **上下文传递**：每次生成都将前面已生成的内容传递给LLM作为上下文
3. **批量优化**：章节大纲采用批量生成（每批5章），平衡生成速度和连贯性
4. **即时保存**：每个部分/批次生成后立即保存到数据库

## 改造内容

### 1. 提示词构建服务 (`backend/app/services/prompt_builder.py`)

#### 修改内容
- **`build_part_outline_prompt` 方法**：
  - 添加 `current_part_number` 参数：当前要生成的部分编号
  - 添加 `previous_parts` 参数：前面已生成的部分列表
  - 如果有前文部分，在提示词中展示所有已生成部分的详细信息

- **`build_part_chapters_prompt` 方法**：
  - 添加 `start_chapter` 参数：起始章节号（支持批量生成）
  - 添加 `num_chapters` 参数：要生成的章节数
  - 添加 `previous_chapters` 参数：前面已生成的章节列表
  - 如果有前文章节，在提示词中展示最近10章的详细信息

#### 改造前后对比

**改造前**：一次性生成所有部分/章节，LLM只能基于蓝图的总体规划
```python
# 一次性生成所有部分
prompt = build_part_outline_prompt(total_chapters, chapters_per_part, ...)
# 返回所有部分的JSON数组
```

**改造后**：逐个生成，每次都能看到前面实际生成的内容
```python
# 串行生成每个部分
for part_num in range(1, total_parts + 1):
    prompt = build_part_outline_prompt(
        current_part_number=part_num,
        previous_parts=already_generated_parts,  # 传入已生成部分
        ...
    )
    # 只返回当前部分的JSON对象
```

### 2. 部分大纲生成服务 (`backend/app/services/part_outline_service.py`)

#### 修改内容
- **`generate_part_outlines` 方法**：
  - 从一次性生成改为 for 循环串行生成
  - 每次生成一个部分，将前面已生成的部分传入上下文
  - 每个部分生成后立即保存到数据库

- **`generate_part_chapters` 方法**：
  - 从一次性生成改为 while 循环批量生成
  - 每批生成5章，将前面已生成的章节传入上下文
  - 每批生成后立即保存到数据库

- **新增辅助方法**：
  - `_parse_single_part_outline`：解析单个部分大纲的JSON
  - `_create_single_part_outline_model`：创建单个部分大纲模型
  - `_get_previous_chapters_for_context`：获取前面章节用于上下文

#### 改造前后对比

**改造前**：
```python
# 一次性生成所有部分
response = await llm_service.get_llm_response(...)
parts_data = result.get("parts", [])  # 返回所有部分的数组

# 批量保存
for part_data in parts_data:
    part_outline = create_model(part_data)
    await repo.add(part_outline)
```

**改造后**：
```python
# 串行生成每个部分
part_outlines = []
for current_part_num in range(1, total_parts + 1):
    # 构建提示词，包含前面已生成的部分
    user_prompt = build_part_outline_prompt(
        current_part_number=current_part_num,
        previous_parts=part_outlines,  # 传入前文
        ...
    )

    # 生成当前部分
    response = await llm_service.get_llm_response(...)
    part_data = parse_single_part_outline(response, current_part_num)

    # 立即保存
    part_outline = create_single_part_outline_model(project_id, part_data)
    await repo.add(part_outline)
    part_outlines.append(part_outline)
```

### 3. 短篇小说章节大纲生成路由 (`backend/app/api/routers/novels/outlines.py`)

#### 修改内容
- **`generate_chapter_outlines` 端点**：
  - 从一次性生成改为 while 循环批量生成
  - 每批生成5章，将前面已生成的章节传入上下文
  - 每批生成后立即保存到数据库

#### 改造前后对比

**改造前**：
```python
# 一次性生成所有章节
payload = {
    "novel_blueprint": blueprint_context,
    "wait_to_generate": {
        "start_chapter": 1,
        "num_chapters": total_chapters  # 一次性生成全部
    }
}
response = await llm_service.get_llm_response(...)
chapters_data = result.get("chapters", [])
```

**改造后**：
```python
# 串行批量生成
CHAPTERS_PER_BATCH = 5
current_chapter = 1

while current_chapter <= total_chapters:
    # 获取前面已生成的章节
    previous_chapters = [已生成的章节摘要]

    # 构建payload，包含前文
    payload = {
        "novel_blueprint": blueprint_context,
        "wait_to_generate": {
            "start_chapter": current_chapter,
            "num_chapters": batch_count
        },
        "previous_chapters": previous_chapters,  # 传入前文
        "context_note": "前面已生成X章，请确保连贯..."
    }

    # 生成当前批次
    response = await llm_service.get_llm_response(...)
    # 保存当前批次
    ...
    current_chapter = batch_end + 1
```

### 4. 增量生成章节大纲路由 (`backend/app/api/routers/writer/chapter_outlines.py`)

#### 修改内容
- **`generate_chapter_outlines_by_count` 端点**：
  - 从一次性生成改为批量串行生成
  - 每批生成5章，自动从数据库获取前面已生成的章节作为上下文
  - 每批生成后立即保存

- **`regenerate_chapter_outline` 端点**：
  - 添加前文章节上下文
  - 重新生成单章时也能参考前面章节

#### 改造前后对比

**改造前（增量生成）**：
```python
# 一次性生成请求的所有章节
payload = {
    "novel_blueprint": blueprint_dict,
    "wait_to_generate": {
        "start_chapter": start_chapter,
        "num_chapters": request.count  # 一次性生成
    }
}
```

**改造后（批量串行生成）**：
```python
# 分批生成
while current_chapter <= end_chapter:
    # 从数据库获取最新的前文章节
    fresh_outlines = await chapter_outline_repo.list_by_project(project_id)
    previous_chapters = [提取前文章节]

    # 构建payload，包含前文
    payload = {
        "novel_blueprint": blueprint_dict,
        "wait_to_generate": {
            "start_chapter": current_chapter,
            "num_chapters": batch_count
        },
        "previous_chapters": previous_chapters,  # 传入前文
        "context_note": "确保连贯..."
    }

    # 生成当前批次
    ...
    current_chapter = batch_end + 1
```

## 修改的文件列表

1. `backend/app/services/prompt_builder.py` - 提示词构建服务
2. `backend/app/services/part_outline_service.py` - 部分大纲服务
3. `backend/app/api/routers/novels/outlines.py` - 短篇章节大纲路由
4. `backend/app/api/routers/writer/chapter_outlines.py` - 增量章节大纲路由

## 关键参数

- **批量大小**：`CHAPTERS_PER_BATCH = 5`（每批生成5章）
- **上下文范围**：
  - 部分大纲：包含所有已生成部分的完整信息
  - 章节大纲：包含所有前文章节，提示词中展示最近10章详情

## 性能影响

### 改造前
- 部分大纲：1次LLM调用生成所有部分
- 章节大纲：1次LLM调用生成所有章节

### 改造后
- 部分大纲：N次LLM调用（N = 部分数量）
- 章节大纲：ceil(M/5)次LLM调用（M = 章节数量）

**示例**：
- 100章小说，4个部分：
  - 改造前：2次LLM调用（1次部分大纲 + 1次章节大纲）
  - 改造后：4次部分大纲 + 4次章节大纲（每部分25章，分5批）= 24次调用

**权衡**：虽然调用次数增加，但质量显著提升，避免了设定冲突和剧情断裂

## 质量提升

### 解决的问题

1. **设定遗忘**：LLM生成第3部分时不会忘记第1部分的世界观细节
2. **剧情线断裂**：每个部分都能承接前一部分的ending_hook
3. **角色发展矛盾**：角色能力和性格发展保持一致，不会出现倒退或突变
4. **细节记忆增强**：基于实际生成内容而非预期规划，细节更准确

### 新增的上下文信息

每次生成都包含：
- 前文的标题和摘要
- 关键事件列表
- 角色发展轨迹
- 主要冲突
- 前一部分的结尾钩子
- 明确的连贯性要求

## 测试建议

### 测试场景

1. **短篇小说测试**（20章）：
   - 创建项目并生成蓝图
   - 生成章节大纲
   - 验证：每批5章，共4批，每批都包含前文上下文

2. **长篇小说测试**（100章）：
   - 创建项目并生成蓝图
   - 生成部分大纲（4个部分）
   - 验证：串行生成，每个部分看到前面所有部分
   - 为每个部分生成章节大纲
   - 验证：每个部分的章节都能看到该部分前面的章节

3. **增量生成测试**：
   - 生成前10章
   - 再增量生成5章
   - 验证：新生成的章节能看到前10章的上下文

4. **重新生成测试**：
   - 重新生成第15章大纲
   - 验证：包含前14章的上下文

### 验证要点

- [ ] 日志中显示批次信息（第X批，共Y批）
- [ ] 日志中显示前文章节数量
- [ ] 生成的内容与前文保持连贯（手动检查）
- [ ] 数据库中章节顺序正确
- [ ] 没有章节编号重复或遗漏
- [ ] 生成时间合理（批量生成应该更慢，但可接受）

## 重新生成规则（串行生成原则）

串行生成不仅影响首次生成，也约束重新生成的行为。

### 核心原则

**重新生成某个大纲会影响后续所有依赖它的大纲，因此必须采取级联措施。**

### 部分大纲重新生成

#### 重新生成所有部分大纲
- **端点**：`POST /api/writer/novels/{id}/part-outlines/regenerate`
- **行为**：
  1. 删除所有已生成的章节大纲（因为章节大纲依赖部分大纲）
  2. 从头串行生成所有部分大纲
- **适用场景**：对整体结构不满意，需要完全重构

#### 重新生成最后一个部分大纲
- **端点**：`POST /api/writer/novels/{id}/part-outlines/regenerate-last`
- **行为**：
  1. 只删除最后一个部分对应的章节大纲
  2. 重新生成最后一个部分大纲（包含前面部分的上下文）
- **适用场景**：只对最后一部分不满意，想微调结尾
- **限制**：只能重新生成最后一个部分，无法重新生成中间部分

#### 重新生成指定部分大纲
- **端点**：`POST /api/writer/novels/{id}/part-outlines/{part_number}/regenerate`
- **行为**（取决于是否为最后一个部分）：
  - 如果是最后一个部分：
    1. 删除该部分对应的章节大纲
    2. 重新生成该部分大纲
  - 如果不是最后一个部分：
    1. 需要设置 `cascade_delete=True`，否则返回错误
    2. 删除该部分及之后的所有部分大纲
    3. 删除该部分及之后的所有章节大纲
    4. 重新生成指定部分大纲
- **适用场景**：对某个特定部分不满意，需要重新规划
- **警告**：重新生成非最后一个部分会丢失后续所有部分和章节大纲

### 章节大纲重新生成

#### 重新生成最后一章
- **端点**：`POST /api/writer/novels/{id}/chapter-outlines/{chapter_number}/regenerate`
- **行为**：直接重新生成，包含前面所有章节的上下文
- **限制**：默认只能重新生成最后一章

#### 重新生成非最后一章（级联删除模式）
- **端点**：同上，但需设置 `cascade_delete=True`
- **行为**：
  1. 删除该章节之后的所有章节大纲
  2. 重新生成指定章节（包含前面章节的上下文）
- **适用场景**：发现中间某章有问题，需要从该章开始重新规划
- **警告**：会丢失后续所有章节大纲，用户需要重新生成

### 错误示例

```python
# 错误：尝试重新生成非最后一章，不设置级联删除
POST /api/writer/novels/{id}/chapter-outlines/5/regenerate
Body: {"prompt": "优化提示词"}
# 响应：400 错误
# "串行生成原则：只能重新生成最后一章（当前最后一章为第20章）。
#  如需重新生成第5章，请设置cascade_delete=True以级联删除第5章之后的所有章节大纲。"
```

### 正确示例

```python
# 正确：重新生成最后一章
POST /api/writer/novels/{id}/chapter-outlines/20/regenerate
Body: {"prompt": "让这章结尾更有悬念"}
# 响应：200 成功

# 正确：重新生成中间章节（级联删除模式）
POST /api/writer/novels/{id}/chapter-outlines/5/regenerate
Body: {"prompt": "调整第5章的转折", "cascade_delete": true}
# 响应：200 成功，包含级联删除信息
# {
#   "message": "第5章大纲已重新生成",
#   "cascade_deleted": {
#     "count": 15,
#     "from_chapter": 6,
#     "to_chapter": 20,
#     "message": "根据串行生成原则，已删除第6-20章的大纲"
#   }
# }
```

### 修改的文件

1. `backend/app/repositories/chapter_repository.py`
   - 新增 `delete_from_chapter()` 方法：删除指定章节号及之后的大纲

2. `backend/app/api/routers/writer/part_outlines.py`
   - 修改 `regenerate_part_outlines`：重新生成所有部分时删除所有章节大纲
   - 新增 `regenerate_last_part_outline`：只重新生成最后一个部分

3. `backend/app/api/routers/writer/chapter_outlines.py`
   - 修改 `regenerate_chapter_outline`：添加串行生成原则检查和级联删除支持

4. `backend/app/schemas/novel.py`
   - 修改 `RegenerateChapterOutlineRequest`：添加 `cascade_delete` 字段

## 兼容性说明

### API 兼容性

原有API接口签名保持不变，新增以下接口：
- `POST /api/writer/novels/{id}/part-outlines/regenerate` - 重新生成所有部分大纲（**行为变更**：现在会删除所有章节大纲）
- `POST /api/writer/novels/{id}/part-outlines/regenerate-last` - **新增**：只重新生成最后一个部分大纲
- `POST /api/writer/novels/{id}/chapter-outlines/{chapter_number}/regenerate` - 重新生成单章（**行为变更**：默认只能重新生成最后一章，需要`cascade_delete`参数才能重新生成其他章节）

原有接口调用方式无需修改：
- `POST /api/writer/novels/{id}/parts/generate` - 部分大纲生成
- `POST /api/novels/{id}/chapter-outlines/generate` - 短篇章节大纲生成
- `POST /api/writer/novels/{id}/chapter-outlines/generate-by-count` - 增量生成

### 数据库兼容性

数据库Schema无变化，无需迁移。

### 前端兼容性

前端无需修改，行为变化：
- 生成时间可能变长（更多LLM调用）
- 进度更新更细粒度（每批次）
- 可考虑添加进度条显示当前批次

## 后续优化建议

1. **进度跟踪**：为批量生成添加实时进度反馈
2. **并发优化**：部分大纲可以考虑限制并发（如3个部分同时生成），但需确保按顺序等待前文
3. **缓存优化**：前文章节摘要可以缓存，避免每批都重新查询
4. **错误恢复**：如果某批生成失败，支持从失败处继续而非重新开始
5. **上下文裁剪**：当前文章节过多时，智能选择最相关的章节传入上下文

## 相关文档

- `backend/docs/PARALLEL_GENERATION_ANALYSIS.md` - 并行生成分析（改造前的分析）
- `backend/README.md` - 后端架构说明
- `CLAUDE.md` - 项目开发指南

## 改造完成日期

2025-11-23
