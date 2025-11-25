
# backend/app/api/routers/novels.py - 小说项目管理API

## 文件概述

提供小说项目的完整生命周期管理API，包括项目创建、蓝图生成、对话交互、章节大纲管理和内容导出等核心功能。这是系统最重要的API路由文件之一。

**文件路径：** `backend/app/api/routers/novels.py`  
**代码行数：** 936 行  
**复杂度：** ⭐⭐⭐⭐⭐ 非常复杂

## 核心功能模块

### 1. 项目基础管理
- 创建项目
- 列表查询
- 详情获取
- 更新/删除

### 2. 概念对话（AI交互）
- 与AI进行创意对话
- 收集小说创意信息
- 构建蓝图筹备材料

### 3. 蓝图生成与优化
- 自动生成小说蓝图
- 蓝图优化迭代
- 局部字段更新

### 4. 章节大纲管理
- 短篇小说大纲生成
- 长篇小说分层大纲

### 5. 内容导出
- TXT格式导出
- Markdown格式导出

## API端点总览

| 方法 | 路径 | 功能 | 复杂度 |
|------|------|------|--------|
| POST | `/api/novels` | 创建项目 | ⭐ |
| GET | `/api/novels` | 项目列表 | ⭐ |
| GET | `/api/novels/{project_id}` | 项目详情 | ⭐ |
| DELETE | `/api/novels` | 批量删除 | ⭐⭐ |
| GET | `/api/novels/{project_id}/sections/{section}` | 获取区段数据 | ⭐⭐ |
| GET | `/api/novels/{project_id}/chapters/{chapter_number}` | 获取章节 | ⭐⭐ |
| POST | `/api/novels/{project_id}/concept/converse` | 概念对话 | ⭐⭐⭐⭐ |
| POST | `/api/novels/{project_id}/blueprint/generate` | 生成蓝图 | ⭐⭐⭐⭐⭐ |
| POST | `/api/novels/{project_id}/blueprint/save` | 保存蓝图 | ⭐⭐ |
| POST | `/api/novels/{project_id}/blueprint/refine` | 优化蓝图 | ⭐⭐⭐⭐ |
| PATCH | `/api/novels/{project_id}` | 更新项目 | ⭐⭐ |
| PATCH | `/api/novels/{project_id}/blueprint` | 局部更新蓝图 | ⭐⭐ |
| POST | `/api/novels/{project_id}/chapter-outlines/generate` | 生成章节大纲 | ⭐⭐⭐⭐ |
| GET | `/api/novels/{project_id}/export` | 导出章节 | ⭐⭐⭐ |

## 详细接口说明

### 1. 创建项目

```python
@router.post("", response_model=NovelProjectSchema, status_code=status.HTTP_201_CREATED)
async def create_novel(
    title: str = Body(...),
    initial_prompt: str = Body(...),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> NovelProjectSchema:
```

**功能：** 为当前用户创建一个新的小说项目

**请求示例：**
```json
{
  "title": "魔法世界的冒险",
  "initial_prompt": "我想写一个关于魔法学院的青春冒险故事"
}
```

**响应：** 完整的项目Schema，包含项目ID、状态等信息

### 2. 概念对话

```python
@router.post("/{project_id}/concept/converse", response_model=ConverseResponse)
async def converse_with_concept(
    project_id: str,
    request: ConverseRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ConverseResponse:
```

**功能：** 与概念设计师（LLM）进行对话，引导蓝图筹备

**工作流程：**
1. 加载历史对话记录
2. 构建系统提示词（concept.md + JSON格式要求）
3. 调用LLM生成响应
4. 解析JSON响应
5. 保存对话记录
6. 检查是否完成（is_complete）

**请求示例：**
```json
{
  "user_input": {
    "type": "text_input",
    "value": "主角是一个16岁的少年，有强大的魔法天赋但不自知"
  }
}
```

**响应示例：**
```json
{
  "ai_message": "很好！让我们继续深入主角设定...",
  "ui_control": {
    "type": "single_choice",
    "options": [
      {"id": "option_1", "label": "选择魔法类型"},
      {"id": "option_2", "label": "设定成长路线"}
    ]
  },
  "conversation_state": {
    "protagonist_defined": true,
    "chapter_count": 80
  },
  "is_complete": false,
  "ready_for_blueprint": false
}
```

**关键逻辑：**
```python
# JSON响应指令
JSON_RESPONSE_INSTRUCTION = """
IMPORTANT: 你的回复必须是合法的 JSON 对象，并严格包含以下字段：
{
  "ai_message": "string",
  "ui_control": {...},
  "conversation_state": {},
  "is_complete": false
}

当「内部信息清单」中的所有项目都已完成，准备结束对话时，
`is_complete` 必须设置为 `true`
"""

# 当对话完成时，标记可以生成蓝图
if parsed.get("is_complete"):
    parsed["ready_for_blueprint"] = True
```

### 3. 生成蓝图（核心功能）

```python
@router.post("/{project_id}/blueprint/generate", response_model=BlueprintGenerationResponse)
async def generate_blueprint(
    project_id: str,
    force_regenerate: bool = False,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> BlueprintGenerationResponse:
```

**功能：** 根据完整对话生成可执行的小说蓝图

**核心流程：**

#### 阶段1：对话历史提取
```python
# 提取对话历史
history_records = await novel_service.list_conversations(project_id)

# 格式化为LLM可理解的格式
formatted_history = []
for record in history_records:
    if record.role == "user":
        user_value = data.get("value", data)
        formatted_history.append({"role": "user", "content": user_value})
    elif record.role == "assistant":
        ai_message = data.get("ai_message")
        formatted_history.append({"role": "assistant", "content": ai_message})
```

#### 阶段2：调用LLM生成蓝图
```python
# 使用 screenwriting 提示词
system_prompt = await prompt_service.get_prompt("screenwriting")

# 对于大型小说，蓝图JSON可能很大
blueprint_raw = await llm_service.get_llm_response(
    system_prompt=system_prompt,
    conversation_history=formatted_history,
    temperature=0.3,
    user_id=desktop_user.id,
    timeout=480.0,
    max_tokens=8192,  # Gemini 2.5 Flash的最大输出限制
)
```

#### 阶段3：数据校验与降级

**total_chapters 校验逻辑（三层降级）：**

```python
if total_chapters <= 0:
    # 优先级1：从conversation_state提取
    for record in reversed(history_records):
        conversation_state = data.get("conversation_state", {})
        chapter_count = conversation_state.get("chapter_count")
        if 5 <= chapter_count <= 10000:
            extracted_chapters = chapter_count
            break
    
    # 优先级2：正则匹配用户输入
    if not extracted_chapters:
        patterns = [
            r'(?:设置|章节数)[\s:：]*?(\d+)\s*(?:章|$)',
            r'(?:写|创作)[\s]*(\d+)\s*章',
        ]
        # ... 正则匹配逻辑
    
    # 优先级3：对话轮次推断
    if not extracted_chapters:
        conversation_rounds = len(history_records) // 2
        if conversation_rounds <= 5:
            default_chapters = 30   # 简单短篇
        elif conversation_rounds <= 10:
            default_chapters = 80   # 中等复杂度
        else:
            default_chapters = 150  # 复杂史诗
```

#### 阶段4：状态转换

```python
# 新流程：蓝图生成阶段不包含章节大纲
# 统一设置为 blueprint_ready
if project.status != ProjectStatus.BLUEPRINT_READY.value:
    await novel_service.transition_project_status(
        project, 
        ProjectStatus.BLUEPRINT_READY.value
    )
```

#### 阶段5：清理旧数据（重新生成时）

```python
# 确保数据一致性：PartOutline、ChapterOutline 和 Chapter 同步删除

# 1. 删除所有部分大纲
if project.part_outlines:
    await session.execute(
        delete(PartOutline).where(PartOutline.project_id == project_id)
    )

# 2. 删除所有章节和章节大纲
if project.chapters:
    chapter_numbers = [ch.chapter_number for ch in project.chapters]
    await novel_service.delete_chapters(project_id, chapter_numbers)
    
    # 3. 同步清理向量库
    if vector_store:
        await ingestion_service.delete_chapters(project_id, chapter_numbers)

# 4. 删除所有章节大纲（防御性删除）
await session.execute(
    delete(ChapterOutline).where(ChapterOutline.project_id == project_id)
)
```

**重要约束：**
```python
# 强制工作流分离：蓝图生成阶段不包含章节大纲
if blueprint.chapter_outline:
    logger.warning(
        "蓝图生成时包含了章节大纲，违反工作流设计，已强制清空"
    )
    blueprint.chapter_outline = []
```

### 4. 优化蓝图

```python
@router.post("/{project_id}/blueprint/refine", response_model=BlueprintGenerationResponse)
async def refine_blueprint(
    project_id: str,
    request: BlueprintRefineRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> BlueprintGenerationResponse:
```

**功能：** 基于用户的优化指令，迭代改进现有蓝图

**请求示例：**
```json
{
  "refinement_instruction": "增强主角的成长弧线，添加更多内心挣扎的描写"
}
```

**优化提示词增强：**
```python
system_prompt += """
## 蓝图优化任务

### 优化要求：
1. **保持现有设定的连贯性**：除非用户明确要求修改
2. **针对性改进**：重点优化用户指出的方面
3. 