---
title: 分步提取-场景
description: 分步提取策略的第三步，提取场景信息
tags: manga, extraction, scenes
---

请从以下章节内容中提取场景信息。

## 章节内容
{content}

## 已识别的事件
{events_json}

## 提取要求

识别不同的场景/地点：
- index: 场景序号（从0开始）
- location: 地点描述（中文）
- location_en: 地点描述（英文，用于绘图）
- time_of_day: morning/afternoon/evening/night/dawn/dusk
- atmosphere: 氛围描述
- weather: 天气描述（可选）
- lighting: natural/dim/bright/dramatic/soft
- indoor_outdoor: indoor/outdoor
- description: 场景的详细描述
- event_indices: 该场景包含的事件索引列表

## 输出格式

```json
{{
  "scenes": [
    {{
      "index": 0,
      "location": "地点",
      "location_en": "Location in English",
      "time_of_day": "day",
      "atmosphere": "氛围",
      "weather": null,
      "lighting": "natural",
      "indoor_outdoor": "indoor",
      "description": "场景描述",
      "event_indices": [0, 1, 2]
    }}
  ]
}}
```

请确保所有事件都被分配到场景中。只输出JSON，不要其他文字。
