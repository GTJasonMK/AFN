
# Part Outline Service - 部分大纲服务

## 文件概述

**文件路径**: `backend/app/services/part_outline_service.py`  
**代码行数**: 747行  
**核心职责**: 长篇小说的分层大纲管理服务，支持部分大纲生成、章节大纲展开、生成状态管理、取消机制等功能

## 核心概念

### 分层大纲架构

对于超过50章的长篇小说，使用两层大纲结构：

```
项目蓝图
  ├─ 部分大纲1 (第1-25章)
  │   ├─ 第1章大纲
  │   ├─ 第2章大纲
  │   └─ ...
  ├─ 部分大纲2 (第26-50章)
  │   └─ ...
  └─ 部分大纲3 (第51-75章)
      └─ ...
```

**优势**：
1. **降低复杂度**：将100章拆分为4个部分，每次处理25章
2. **提高质量**：LLM可以更专注于每个部分的细节
3. **增量生成**：支持逐步生成，避免一次性生成过多内容
4. **灵活调整**：可以单独重新生成某个部分

## 核心功能

### 1. 生成部分大纲（大纲的大纲）

```python
async def generate_part_outlines(
    self,
    project_id: str,
    user_id: int,
    total_chapters: int,
    chapters_per_part: int = 25,
    optimization_prompt: Optional[str] = None,
    skip_status_update: bool = False,
) -> PartOutlineGenerationProgress
```

**功能说明**：
- 根据总章节数自动计算需要几个部分
- 调用LLM生成每个部分的高层概要
- 自动创建 `PartOutline` 数据库记录
- 更新项目状态为 `part_outlines_ready`

**使用示例**：
```python
part_outline_service = PartOutlineService(session)

# 为100章小说生成部分大纲
result = await part_outline_service.generate_part_outlines(
    project_id=project_id,
    user_id=user_id,
    total_chapters=100,
    chapters_per_part=25,  # 每部分25章，共4个部分
    optimization_prompt="注重角色成长和情感线"
)

print(f"生成了 {result.total_parts} 个部分")
for part in result.parts:
    print(f"第{part.part_number}部分: {part.title}")
    print(f"章节范围: {part.start_chapter}-{part.end_chapter}")
    print(f"主题: {part.theme}")
```

**生成的部分大纲结构**：
```python
{
    "parts": [
        {
            "part_number": 1,
            "title": "初入江湖",
            "start_chapter": 1,
            "end_chapter": 25,
            "summary": "主角从平凡少年成长为初窥武道门径的修炼者...",
            "theme": "成长与启蒙",
            "key_events": [
                "获得传承",
                "结识师傅",
                "初次战斗"
            ],
            "character_arcs": {
                "张三": "从懦弱到勇敢",
                "李四": "从傲慢到尊重"
            },
            "conflicts": [
                "主角与恶霸的矛盾",
                "修炼资源的争夺"
            ],
            "ending_hook": "主角发现师傅隐藏的秘密"
        },
        // 更多部分...
    ]
}
```

**优化提示词的作用**：
```python
# 基础生成（无优化提示）
await generate_part_outlines(
    total_chapters=100,
    chapters_per_part=25
)

# 带优化提示（引导AI生成更符合预期的大纲）
await generate_part_outlines(
    total_chapters=100,
    chapters_per_part=25,
    optimization_prompt="""
    请注意以下优化方向：
    1. 加强主角与反派的对抗线
    2. 每个部分至少有一个情感高潮
    3. 角色成长要循序渐进，不要跳跃式
    4. 世界观逐步展开，不要一次性抛出所有设定
    """
)
```

### 2. 生成部分的详细章节大纲

```python
async def generate_part_chapters(
    self,
    project_id: str,
    user_id: int,
    part_number: int,
    regenerate: bool = False,
) -> List[ChapterOutlineSchema]
```

**功能说明**：
- 将部分大纲展开为详细的章节大纲
- 考虑上下文（前一部分的结尾、下一部分的开始）
- 支持重新生成
- 自动更新生成状态

**使用示例**：
```python
# 生成第1部分的章节大纲
chapters = await part_outline_service.generate_part_chapters(
    project_id=project_id,
    user_id=user_id,
    part_number=1,
    regenerate=False  # 如果已存在则跳过
)

print(f"生成了 {len(chapters)} 个章节大纲")
for chapter in chapters:
    print(f"第{chapter.chapter_number}章: {chapter.title}")
    print(f"摘要: {chapter.summary[:50]}...")
```

**生成流程**：
```python
# 1. 获取部分大纲信息
part_outline = await repo.get_by_part_number(project_id, part_number)

# 2. 构建上下文
# - 当前部分的主题、关键事件、冲突
# - 前一部分的结尾钩子（承接）
# - 下一部分的摘要（铺垫）

# 3. 调用LLM生成章节大纲
response = await llm_service.get_llm_response(
    system_prompt=screenwriting_prompt,
    conversation_history=[{"role": "user", "content": user_prompt}],
    temperature=0.3
)

# 4. 解析并存储章节大纲
for chapter_data in result["chapter_outline"]:
    outline = ChapterOutline(
        project_id=project_id,
        chapter_number=chapter_data["chapter_number"],
        title=chapter_data["title"],
        summary=chapter_data["summary"]
    )
    session.add(outline)
```

### 3. 批量生成章节大纲

```python
async def batch_generate_chapters(
    self,
    project_id: str,
    user_id: int,
    part_numbers: Optional[List[int]] = None,
    max_concurrent: int = 3,
) -> PartOutlineGenerationProgress
```

**功能说明**：
- 串行生成多个部分的章节大纲（避免session并发问题）
- 支持指定部分列表或自动生成所有待生成部分
- 返回生成进度和结果

**使用示例**：
```python
# 生成所有待生成的部分
progress = await part_outline_service.batch_generate_chapters(
    project_id=project_id,
    user_id=user_id,
    part_numbers=None,  # None表示自动选择pending状态的部分
    max_concurrent=3
)

print(f"完成: {progress.completed_parts}/{progress.total_parts}")
print(f"状态: {progress.status}")

# 生成指定的部分
progress = await part_outline_service.batch_generate_chapters(
    project_id=project_id,
    user_id=user_id,
    part_numbers=[1, 2, 3],  # 仅生成前3个部分
)
```

### 4. 取消生成机制

#### 请求取消

```python
async def cancel_part_generation(
    self,
    project_id: str,
    part_number: int,
    user_id: int,
) -> bool
```

**使用示例**：
```python
# 用户点击取消按钮
success = await part_outline_service.cancel_part_generation(
    project_id=project_id,
    part_number=2,
    user_id=user_id
)

if success:
    print("取消请求已发送")
else:
    print("该部分当前不在生成中，无法取消")
```

#### 检查取消状态

```python
async def _check_if_cancelled(self, part_outline: PartOutline) -> bool:
    """检查是否被请求取消，如果是则抛出异常"""
    await self.session.refresh(part_outline)
    
    if part_outline.generation_status == "cancelling":
        raise GenerationCancelledException(
            f"第 {part_outline.part_number} 部分的生成已被取消"
        )
    
    return False
```

**在生成流程中的检查点**：
```python
async def generate_part_chapters(...):
    try:
        # 检查点1：开始生成前
        await self._check_if_cancelled(part_outline)
        
        # 构建提示词
        user_prompt = await self._build_part_chapters_prompt(...)
        
        # 检查点2：LLM调用前
        await self._check_if_cancelled(part_outline)
        
        # 调用LLM（耗时操作）
        response = await llm_service.get_llm_response(...)
        
        # 检查点3：LLM调用后
        await self._check_if_cancelled(part_outline)
        
        # 解析和存储
        ...
        
    except GenerationCancelledException:
        # 取消异常，让finally块处理状态更新
        pass
    finally:
        # 确保状态总是会更新
        if generation_successful:
            await repo.update_status(part_outline, "completed", 100)
        elif part_outline.generation_status == "cancelling":
            await repo.update_status(part_outline, "cancelled", progress)
        else:
            await repo.update_status(part_outline, "failed", 0)
```

### 5. 超时清理机制

```python
async def cleanup_stale_generating_status(
    self,
    project_id: str,
    timeout_minutes: int = 15,
) -> int
```

**功能说明**：
- 清理超过指定时间未更新的"generating"状态
- 防止意外中断导致状态永久卡住
- 建议在项目加载时调用

**使用示例**：
```python
# 在获取项目详情时清理超时状态
project = await novel_service.get_project_schema(project_id, user_id)

# 清理超过15分钟未更新的generating状态
cleaned = await part_outline_service.cleanup_stale_generating_status(
    project_id=project_id,
    timeout_minutes=15
)

if cleaned > 0:
    logger.info(f"清理了 {cleaned} 个超时状态")
```

## 生成状态管理

### 状态流转

```python
pending -> generating -> completed
                      -> cancelled
                      -> failed
         -> cancelling -> cancelled
```

**状态说明**：
- `pending` - 待生成
- `generating` - 生成中
- `cancelling` - 取消中（过渡状态）
- `completed` - 已完成
- `cancelled` - 已取消
- `failed` - 生成失败

### 状态更新

```python
async def update_status(
    self,
    part_outline: PartOutline,
    status: str,
    progress: int
) -> None:
    """更新部分大纲的生成状态"""
    part_outline.generation_status = status
    part_outline.progress = progress
    await self.session.commit()
```

**使用示例**：
```python
# 开始生成
await repo.update_status(part_outline, "generating", 0)

# 更新进度
await repo.update_status(part_outline, "generating", 50)

# 完成生成
await repo.update_status(part_outline, "completed", 100)

# 生成失败
await repo.update_status(part_outline, "failed", 0)
```

## 提示词构建

### 部分大纲提示词

[`_build_part_outline_prompt()`](backend/app/services/part_outline_service.py:541) 构建生成部分大纲的提示词：

```python
def _build_part_outline_prompt(
    self,
    total_chapters: int,
    chapters_per_part: int,
    total_parts: int,
    world_setting: Dict,
    characters: List[Dict],
    full_synopsis: str,
    optimization_prompt: Optional[str] = None,
) -> str
```

**提示词结构**：
```
## 小说基本信息
- 总章节数
- 每部分章节数
- 需要生成的部分数

## 世界观设定
{世界观JSON}

## 角色档案
{角色列表JSON}

## 主要剧情
{完整概要}

## 优化方向（可选）
{用户的优化提示}

## 输出要求
- 生成N个部分的大纲
- 每个部分包含：标题、章节范围、摘要、主题、关键事件、角色成长、冲突、结尾钩子
- 