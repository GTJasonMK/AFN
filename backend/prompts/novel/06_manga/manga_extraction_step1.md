---
title: 分步提取-角色和事件
description: 分步提取策略的第一步，提取角色信息和事件信息
tags: manga, extraction, characters, events
---

请从以下章节内容中提取角色信息和事件信息。

## 章节内容
{content}

## 提取要求

### 1. 角色信息 (characters)
为每个出场角色提取：
- name: 角色名（中文）
- appearance: 外观描述（中文，详细描述发型、服装、体型、年龄特征，用于漫画绘制）
- personality: 性格特点（简短）
- role: protagonist/antagonist/supporting/minor/background
- gender: male/female/unknown
- age_description: 年龄描述

### 2. 事件信息 (events)
按时间顺序提取关键事件：
- index: 事件序号（从0开始）
- type: dialogue/action/reaction/transition/revelation/conflict/resolution/description/internal
- description: 事件描述（中文，简洁）
- participants: 参与角色列表
- importance: low/normal/high/critical
- is_climax: 是否是高潮点（true/false）

## 输出格式

```json
{{
  "characters": {{
    "角色名": {{
      "name": "角色名",
      "appearance": "中文外观描述，详细描述发型、服装、体型、年龄特征",
      "personality": "性格",
      "role": "protagonist",
      "gender": "male",
      "age_description": "青年"
    }}
  }},
  "events": [
    {{
      "index": 0,
      "type": "dialogue",
      "description": "事件描述",
      "participants": ["角色1", "角色2"],
      "importance": "normal",
      "is_climax": false
    }}
  ],
  "climax_event_indices": [5, 6]
}}
```

请确保JSON格式正确。只输出JSON，不要其他文字。
