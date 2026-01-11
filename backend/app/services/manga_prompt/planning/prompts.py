"""
页面规划模块提示词

定义全局页面规划的 LLM 提示词模板。
简化版：专注于简单的页面分配。
"""

# 提示词名称（用于从 PromptService 加载）
PROMPT_NAME = "manga_page_planning"

# 页面规划提示词模板
PAGE_PLANNING_PROMPT = """你是漫画分镜师，请根据章节信息规划页面结构。

## 章节信息

### 章节摘要
{chapter_summary}

### 事件列表
{events_json}

### 场景列表
{scenes_json}

### 角色列表
{characters_json}

## 规划要求

1. **页面数量**: 规划 {min_pages}-{max_pages} 页
2. **事件分配**: 每页包含 1-3 个相关事件
3. **分镜数量**: 每页建议 3-6 个画格

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
      "notes": "建立场景氛围"
    }}
  ]
}}
```

请确保：
1. 所有事件都被分配到某个页面
2. 事件按时间顺序分配
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
