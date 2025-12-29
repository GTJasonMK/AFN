"""
页面规划模块提示词

定义全局页面规划的 LLM 提示词模板。
"""

# 提示词名称（用于从 PromptService 加载）
PROMPT_NAME = "manga_page_planning"

# 页面规划提示词模板
PAGE_PLANNING_PROMPT = """你是专业的漫画分镜师。请根据以下章节信息规划整章的页面结构。

## 章节信息

### 章节摘要
{chapter_summary}

### 事件列表
{events_json}

### 场景列表
{scenes_json}

### 角色列表
{characters_json}

### 高潮事件索引
{climax_indices}

## 规划要求

1. **页面数量**: 规划 {min_pages}-{max_pages} 页
2. **内容分配**:
   - 每页应包含 1-3 个相关事件
   - 高潮事件应使用更大的页面空间（1-2个事件/页）
   - 过渡事件可以合并（2-3个事件/页）
3. **节奏控制**:
   - 开场(opening): 建立场景和角色，节奏较慢
   - 铺垫(setup): 展开剧情，中等节奏
   - 上升(rising): 推进冲突，节奏加快
   - 高潮(climax): 情感/动作爆发，需要更多画面空间
   - 下降(falling): 冲突后的过渡
   - 收尾(resolution): 章节结束，可快可慢
4. **分镜数量建议**:
   - 慢节奏页面: 3-4 格
   - 中等节奏页面: 4-5 格
   - 快节奏页面: 5-6 格
   - 爆发页面: 3-4 格（大格为主）

## 输出格式

请以 JSON 格式输出：

```json
{{
  "total_pages": 10,
  "pages": [
    {{
      "page_number": 1,
      "event_indices": [0, 1],
      "content_summary": "开场，主角登场",
      "content_summary_en": "Opening, protagonist appears",
      "pacing": "slow",
      "role": "opening",
      "key_characters": ["李明"],
      "has_dialogue": true,
      "has_action": false,
      "suggested_panel_count": 4,
      "notes": "建立场景氛围"
    }}
  ],
  "pacing_notes": "整体节奏说明",
  "climax_pages": [6, 7]
}}
```

## 字段说明

- **pacing**: slow/medium/fast/explosive
- **role**: opening/setup/rising/climax/falling/resolution/transition
- **suggested_panel_count**: 建议的分镜数量（3-7）
- **climax_pages**: 高潮所在的页码列表

请确保：
1. 所有事件都被分配到某个页面
2. 事件按时间顺序分配
3. 高潮事件获得足够的页面空间
4. 页面之间的节奏有变化
"""

# 系统提示词
PLANNING_SYSTEM_PROMPT = """你是一位专业的漫画分镜规划师。你的任务是根据章节内容规划漫画的页面结构。

你需要：
1. 理解章节的整体叙事节奏
2. 识别高潮和关键转折点
3. 合理分配内容到各个页面
4. 确保页面之间的节奏变化自然
5. 以结构化的 JSON 格式输出规划结果

请始终确保输出的 JSON 格式正确，可以被程序解析。
"""

__all__ = [
    "PROMPT_NAME",
    "PAGE_PLANNING_PROMPT",
    "PLANNING_SYSTEM_PROMPT",
]
