# 提示词构建审查报告

**审查日期**: 2025-12-30
**审查人**: Claude Code
**审查范围**: AFN项目所有生成阶段的提示词构建与信息利用

---

## 1. 灵感对话(Inspiration)阶段

### README中的描述
- 使用 "inspiration" 提示词
- SSE流式交互进行多轮对话
- 追踪对话状态和完成度
- UI控件动态调整（字数滑块、结束按钮等）

### 实际实现

**提示词加载** (`backend/app/services/inspiration_service.py:36-47`):
```python
system_prompt = await self.prompt_service.get_prompt("inspiration")
```

**提示词输入信息**:
- 对话历史（格式化为 "用户: xxx" / "助手: xxx"）
- 用户当前输入
- 不包含项目元数据（如标题等）

**提示词位置**: `backend/prompts/01_inspiration/inspiration.md`

**提示词核心内容**:
- 角色定义："文思"AI助手
- 内部检查清单：火花、类型、主角、核心冲突、世界观、结构、基调、预期读者、篇幅、独特卖点
- 输出JSON格式：`dialogue_content`, `ui_control`, `conversation_state`
- 动态UI控制：字数滑块、结束对话按钮等

### 审查结论
**符合度: 完全符合**
实际实现与文档描述一致。提示词通过 `PromptService.get_prompt("inspiration")` 加载，支持用户自定义修改。

---

## 2. 蓝图生成(Blueprint)阶段

### README中的描述
- 基于灵感对话生成完整小说蓝图
- 包含角色设定、世界观、情节主线等

### 实际实现

**提示词加载** (`backend/app/api/routers/novels/blueprints.py:91`):
```python
system_prompt = await prompt_service.get_prompt("screenwriting")
```

**提示词输入信息**:
- 格式化的对话历史（"用户: xxx\n助手: xxx"）
- 章节数配置
- force_regenerate 和 allow_incomplete 标志

**提示词位置**: `backend/prompts/06_manga/screenwriting.md`

**提示词核心内容**:
- 生成完整JSON蓝图结构
- 包含：title, genre, style, tone, synopsis, total_chapters, characters, world_building, plot_outline
- 此阶段 `chapter_outline` 为空数组（后续生成）

### 审查发现
**注意事项**:
1. 提示词名称为 "screenwriting"（编剧），位于 `06_manga` 目录下，但实际用于蓝图生成
2. 建议将其移至 `02_blueprint` 目录或重命名为 "blueprint" 以保持一致性

### 审查结论
**符合度: 基本符合（有组织建议）**
功能正确，但提示词命名和位置存在组织问题。

---

## 3. 分部大纲(Part Outline)阶段

### README中的描述
- 仅对长篇小说(>=50章)生成
- 将全书分为多个部分，每部分包含故事阶段和转折点

### 实际实现

**提示词加载**: 通过 `PromptService.get_prompt("part_outline")`

**提示词位置**: `backend/prompts/03_outline/part_outline.md`

**提示词输入信息**:
- `novel_blueprint`: 完整蓝图JSON
- `total_chapters`: 总章节数
- `chapters_per_part`: 每部分章节数（默认约10-15章）

**提示词核心内容**:
- 输入：蓝图 + 总章数 + 每部章数
- 输出：parts数组，每部分包含 part_number, title, chapters_range, story_phase, turning_point, summary

### 审查结论
**符合度: 完全符合**
实际实现与文档描述一致。

---

## 4. 章节大纲(Chapter Outline)阶段

### README中的描述
- 根据蓝图和已有章节生成详细大纲
- 支持RAG检索相关已完成章节
- 批量生成（一次生成多章）

### 实际实现

**提示词加载**: 通过 `PromptService.get_prompt("outline")`

**提示词位置**: `backend/prompts/03_outline/outline.md`

**提示词输入信息**:
- `novel_blueprint`: 蓝图JSON
- `wait_to_generate`: 待生成章节号列表（如 "第5章-第8章"）
- `previous_chapters`: 前序章节摘要
- `relevant_completed_chapters`: RAG检索的相关章节（可选）

**提示词核心内容**:
- 输出：chapters数组，每章包含 chapter_number, title, summary
- 要求：承上启下、伏笔设置、节奏控制

### 审查结论
**符合度: 完全符合**
支持批量生成和RAG增强。

---

## 5. 章节生成(Chapter Generation)阶段

### README中的描述
- 使用 "writing" 提示词
- 分层RAG上下文构建
- 4段式提示词结构

### 实际实现

**提示词加载** (`backend/app/services/chapter_generation/prompt_builder.py:28`):
```python
async def _load_prompt(self, name: str) -> str:
    content = await self.prompt_service.get_prompt(name)
```

**提示词位置**: `backend/prompts/04_writing/writing.md`

**提示词构建器** (`ChapterPromptBuilder.build_writing_prompt`):

**4段式提示词结构**:
1. **核心设定区**: 人名约束、世界观规则、情节走向、大纲遵循
2. **当前任务区**: 章节大纲（title, summary）、写作笔记
3. **场景状态区**: 前章尾部摘录（200-500字）、前章结束时的场景状态（可选）
4. **关键参考区**: RAG检索的相关内容（passages, summaries）

**RAG上下文构建** (`SmartContextBuilder.build_generation_context`):

分3层构建：
- **must_have层**: story_basics, character_names, current_outline, prev_ending_state
- **important层**: involved_characters, relationships, high_priority_foreshadowing, prev_character_states, relevant_summaries
- **reference层**: world_setting, full_synopsis, relevant_passages, other_foreshadowing

### 审查结论
**符合度: 完全符合**
实际实现高度符合文档描述，RAG系统设计精细。

---

## 6. 漫画分镜(Manga Prompt)4步流水线

### README/ARCHITECTURE中的描述
4步流水线：
1. 章节信息提取 (Extraction)
2. 页面规划 (Page Planning)
3. 分镜设计 (Storyboard Design)
4. 提示词构建 (Prompt Building)

### 实际实现

**服务入口** (`backend/app/services/manga_prompt/core/service.py`):

```python
class MangaPromptServiceV2:
    # 核心流水线组件
    self._extractor = ChapterInfoExtractor(llm_service, prompt_service)
    self._planner = PagePlanner(llm_service, prompt_service)
    self._designer = StoryboardDesigner(llm_service, prompt_service)
```

**步骤1: 信息提取**
- 提示词名称: `manga_chapter_extraction`
- 提示词位置: `backend/prompts/06_manga/manga_chapter_extraction.md`
- 输入: 章节内容
- 输出: characters, dialogues, scenes, events, items（包含英文描述用于AI绘图）

**步骤2: 页面规划**
- 提示词名称: `manga_page_planning`
- 提示词位置: `backend/prompts/06_manga/manga_page_planning.md`
- 输入: chapter_summary, events_json, scenes_json, characters_json, climax_indices, min_pages, max_pages
- 输出: pages数组（每页包含event_indices, pacing, role, suggested_panel_count）

**步骤3: 分镜设计**
- 提示词名称: `manga_storyboard_design`
- 提示词位置: `backend/prompts/06_manga/manga_storyboard_design.md`
- 输入: page_number, page_role, events_json, dialogues_json, characters_json, previous_panel
- 输出: panels数组（每格包含shot_type, visual_description_en, dialogues, sound_effects等）

**步骤4: 提示词构建**
- 非LLM步骤，程序化构建
- 位置: `backend/app/services/manga_prompt/prompt_builder/builder.py`
- 功能: 将分镜设计结果转换为AI绘图提示词

**额外提示词文件**:
- `manga_layout.md`: 专业漫画布局规划（含格间过渡、间白策略、"间"运用）
- `manga_prompt.md`: 通用漫画提示词生成（含气泡系统、音效系统、构图变化要求）

### 审查结论
**符合度: 完全符合**
4步流水线设计精细，每步都有独立提示词，支持断点续传。

---

## 7. 正文优化(Content Optimization)阶段

### README/ARCHITECTURE中的描述
- 基于ReAct循环的Agent模式
- 6个检查维度: coherence, character, foreshadow, timeline, style, scene
- 支持RAG检索和索引查询

### 实际实现

**服务入口** (`backend/app/services/content_optimization/service.py`)

**Agent实现** (`backend/app/services/content_optimization/agent.py:308-370`):
```python
async def _build_system_prompt(self, dimensions: List[str]) -> str:
    # 尝试从外部模板加载
    if self.prompt_service:
        template = await self.prompt_service.get_prompt("content_optimization_agent")
```

**提示词位置**: `backend/prompts/05_analysis/content_optimization_agent.md`

**Agent工具集**:
- `analyze_paragraph`: 分析段落内容
- `rag_retrieve`: RAG检索历史内容
- `get_character_state`: 查询角色状态索引
- `check_foreshadowing`: 检查伏笔
- `generate_suggestion`: 生成修改建议
- `next_paragraph`: 移动到下一段
- `finish_analysis`: 完成当前段落
- `complete_workflow`: 完成整个分析

**工作流程**:
1. 段落分割
2. Agent循环（思考 -> 工具调用 -> 观察）
3. 支持Review模式（暂停等待用户确认）

### 审查结论
**符合度: 完全符合**
ReAct Agent模式实现完整，支持多维度检查和用户交互。

---

## 8. 章节评审(Chapter Evaluation)阶段

### README/ARCHITECTURE中的描述
- 多版本评估和选择
- 6个评估维度
- 支持RAG增强

### 实际实现

**服务入口** (`backend/app/services/chapter_evaluation_service.py`)

**提示词加载**: 外部传入 `evaluator_prompt`（通常通过 `PromptService.get_prompt("evaluation")` 获取）

**提示词位置**: `backend/prompts/05_analysis/evaluation.md`

**提示词输入信息**:
```python
payload = {
    "novel_blueprint": blueprint_dict,
    "completed_chapters": context.completed_chapters,
    "content_to_evaluate": {
        "chapter_number": chapter_number,
        "versions": versions_to_evaluate,
    },
    "relevant_context": {  # RAG增强
        "relevant_chunks": ...,
        "relevant_summaries": ...,
    }
}
```

**6个评估维度**:
1. 情节连贯性 (plot coherence)
2. 文学质量 (literary quality)
3. 角色一致性 (character consistency)
4. 世界观契合度 (world fit)
5. 伏笔处理 (foreshadowing)
6. 叙事节奏 (narrative rhythm)

**输出格式**:
- `best_choice`: 最佳版本ID
- `reason_for_choice`: 选择理由
- `evaluation`: 每个版本的详细评估

### 审查结论
**符合度: 完全符合**
评估系统完整，支持RAG增强和多维度评分。

---

## 总结

### 整体评估
| 阶段 | 符合度 | 备注 |
|------|--------|------|
| 灵感对话 | 完全符合 | - |
| 蓝图生成 | 基本符合 | 提示词命名/位置可优化 |
| 分部大纲 | 完全符合 | - |
| 章节大纲 | 完全符合 | - |
| 章节生成 | 完全符合 | RAG系统设计精细 |
| 漫画分镜 | 完全符合 | 4步流水线完整 |
| 正文优化 | 完全符合 | ReAct Agent实现完整 |
| 章节评审 | 完全符合 | - |

### 发现的问题

1. **蓝图生成提示词命名不一致**
   - 当前: `screenwriting` 位于 `06_manga/`
   - 建议: 重命名为 `blueprint` 并移至 `02_blueprint/`

2. **提示词加载机制健壮**
   - 所有服务均通过 `PromptService` 加载提示词
   - 支持用户自定义修改
   - 有内置备用提示词

### 优势亮点

1. **分层RAG上下文**: 章节生成的3层上下文设计（must_have, important, reference）确保关键信息不丢失
2. **4步漫画流水线**: 从信息提取到提示词构建的完整流程，支持断点续传
3. **ReAct Agent模式**: 正文优化采用自主决策的Agent架构，灵活应对不同场景
4. **统一提示词管理**: `PromptService` + `_registry.yaml` 实现集中管理和用户自定义

---

**报告完成**
