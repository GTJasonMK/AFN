"""
页面规划模块提示词

定义全局页面规划的 LLM 提示词模板。
简化版：专注于简单的页面分配。
"""

from ..prompts_shared import EVENT_FIELDS_BASE

# 提示词名称（用于从 PromptService 加载）
PROMPT_NAME = "manga_page_planning"

# 页面规划提示词模板
PAGE_PLANNING_PROMPT = """你是漫画分镜师，请根据章节信息规划页面结构。

## 章节信息

### 章节摘要
{chapter_summary}

### 事件列表（含复杂度信息）
{events_json}

**事件字段说明**：
""" + EVENT_FIELDS_BASE + """- importance: 重要程度（critical关键/high高/normal普通/low低）
- dialogue_count: 关联对话数量
- is_climax: 是否是高潮场景

### 场景列表
{scenes_json}

### 角色列表
{characters_json}

### 高潮事件索引
{climax_indices}

## 规划要求

1. **页面数量**: 规划 {min_pages}-{max_pages} 页

2. **事件复杂度考量**:
   - **高潮/关键事件** (is_climax=true 或 importance=critical/high): 单独分配1页或更多
   - **动作/冲突事件** (type=action/conflict): 需要更多画格，建议 4-6 格
   - **对话密集事件** (dialogue_count>=3): 需要更多空间放对话气泡
   - **普通/低重要度事件**: 可以合并，每页 2-3 个

3. **分镜数量建议**:
   - 高潮场景: 5-6 格（大场面）
   - 动作场景: 4-5 格
   - 对话场景: 3-4 格
   - 过渡场景: 2-3 格

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
      "key_characters": ["李明"],
      "has_dialogue": true,
      "has_action": false,
      "suggested_panel_count": 4,
      "page_importance": "normal",
      "notes": "建立场景氛围"
    }}
  ]
}}
```

**page_importance 说明**: critical(高潮页)/high(重要)/normal(普通)/low(过渡)

请确保：
1. 所有事件都被分配到某个页面
2. 事件按时间顺序分配
3. 高潮事件获得足够的页面空间
"""

# 系统提示词
PLANNING_SYSTEM_PROMPT = """你是漫画分镜规划师，负责将章节内容分配到各个页面。

你的任务：
1. 合理分配事件到各个页面
2. 建议每页的分镜数量
3. 以 JSON 格式输出规划结果

请确保输出的 JSON 格式正确。
"""

__all__ = [
    "PROMPT_NAME",
    "PAGE_PLANNING_PROMPT",
    "PLANNING_SYSTEM_PROMPT",
]
