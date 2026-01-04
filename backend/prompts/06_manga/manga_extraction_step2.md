---
title: 分步提取-对话
description: 分步提取策略的第二步，提取对话信息
tags: manga, extraction, dialogues
---

请从以下章节内容中提取所有对话信息。

## 章节内容
{content}

## 已识别的角色
{characters_json}

## 已识别的事件
{events_json}

## 提取要求

提取所有对话和内心独白：
- index: 对话序号（从0开始）
- speaker: 说话人名字（必须是已识别角色之一）
- content: 对话内容（保留原文）
- emotion: neutral/happy/sad/angry/surprised/fearful/excited/calm/nervous/determined
- target: 对话对象
- event_index: 所属事件索引（对应events中的index）
- is_internal: 是否是内心独白
- bubble_type: normal/shout/whisper/thought

## 输出格式

```json
{{
  "dialogues": [
    {{
      "index": 0,
      "speaker": "角色名",
      "content": "对话内容",
      "emotion": "neutral",
      "target": "对话对象",
      "event_index": 0,
      "is_internal": false,
      "bubble_type": "normal"
    }}
  ]
}}
```

请确保JSON格式正确。只输出JSON，不要其他文字。
