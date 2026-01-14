---
title: 分步提取-物品和摘要
description: 分步提取策略的第四步，提取物品信息和章节摘要
tags: manga, extraction, items, summary
---
请从以下章节内容中提取物品信息和章节摘要。

## 章节内容

{content}

## 已识别的事件数量

{event_count}

## 提取要求

### 1. 物品信息 (items)

只提取对剧情有影响的物品：

- name: 物品名（中文）
- description: 描述（中文）
- description_en: 描述（英文，用于绘图）
- importance: prop/key_item/mcguffin
- first_appearance_event: 首次出现的事件索引
- visual_features: 视觉特征（英文）

### 2. 章节摘要

- chapter_summary: 章节内容摘要（2-3句话，中文）
- mood_progression: 情绪变化轨迹（如["平静", "紧张", "高潮", "释然"]）
- total_estimated_pages: 预估漫画页数（5-15页）

## 输出格式

```json
{{
  "items": [
    {{
      "name": "物品名",
      "description": "描述",
      "description_en": "Description",
      "importance": "prop",
      "first_appearance_event": 0,
      "visual_features": "Visual features"
    }}
  ],
  "chapter_summary": "章节摘要...",
  "mood_progression": ["开始情绪", "中间情绪", "结束情绪"],
  "total_estimated_pages": 10
}}
```

请确保JSON格式正确。只输出JSON，不要其他文字。
