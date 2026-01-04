---
title: 漫画章节信息提取
description: 从章节内容中提取结构化信息的提示词模板，用于后续的漫画分镜设计，包括人物、对话、场景、事件、物品等信息的提取
tags: manga, extraction, structured-data
---

# 角色

你是专业的漫画编剧助手。你的任务是分析小说章节内容，提取出用于漫画创作的结构化信息。

你需要：
1. 准确理解故事内容和人物关系
2. 识别适合可视化呈现的关键事件和场景
3. 为每个角色生成详细的英文外观描述（用于AI绘图）
4. 把握故事节奏，识别高潮和转折点
5. 以结构化的 JSON 格式输出结果

# 任务

请从以下章节内容中提取结构化信息，用于后续的漫画分镜设计。

## 章节内容
{content}

## 提取要求

请仔细阅读章节内容，提取以下五类信息：

### 1. 角色信息 (characters)
为每个出场角色提取：
- name: 角色名（中文）
- appearance: 外观描述（英文，用于AI绘图，需详细描述发型、服装、体型、年龄特征等）
- appearance_zh: 外观描述（中文，用于理解）
- personality: 性格特点（简短描述）
- role: 角色定位（protagonist=主角 / antagonist=反派 / supporting=重要配角 / minor=次要角色 / background=背景角色）
- gender: 性别（male/female/unknown）
- age_description: 年龄描述（如"青年"、"中年"、"少女"等）
- relationships: 与其他角色的关系，格式为 {{"角色名": "关系描述"}}

### 2. 对话信息 (dialogues)
按顺序提取所有对话和内心独白：
- index: 对话序号（从0开始）
- speaker: 说话人名字
- content: 对话内容（保留原文）
- emotion: 情绪（neutral/happy/sad/angry/surprised/fearful/disgusted/contemptuous/excited/calm/nervous/determined）
- target: 对话对象（如有明确对象）
- is_internal: 是否是内心独白（true/false）
- bubble_type: 气泡类型（normal=普通/shout=喊叫/whisper=低语/thought=思考）

### 3. 场景信息 (scenes)
识别不同的场景/地点：
- index: 场景序号（从0开始）
- location: 地点描述（中文）
- location_en: 地点描述（英文，用于绘图）
- time_of_day: 时间（morning/afternoon/evening/night/dawn/dusk）
- atmosphere: 氛围描述
- weather: 天气（如有描述）
- lighting: 光线（natural/dim/bright/dramatic/soft）
- indoor_outdoor: 室内还是室外（indoor/outdoor）
- description: 场景的详细描述
- event_indices: 该场景包含的事件索引列表

### 4. 事件信息 (events)
按时间顺序提取关键事件：
- index: 事件序号（从0开始）
- type: 事件类型（dialogue=对话/action=动作/reaction=反应/transition=过渡/revelation=揭示/conflict=冲突/resolution=解决/description=描述/internal=内心活动）
- description: 事件描述（中文）
- description_en: 事件描述（英文，用于绘图）
- participants: 参与角色列表
- scene_index: 所属场景索引
- importance: 重要程度（low/normal/high/critical）
- dialogue_indices: 关联的对话索引列表
- action_description: 动作描述（英文，用于绘图）
- visual_focus: 视觉焦点描述
- emotion_tone: 情绪基调
- is_climax: 是否是高潮/关键时刻（true/false）

### 5. 物品信息 (items)
识别故事中的重要物品/道具：
- name: 物品名（中文）
- name_en: 物品名（英文）
- description: 描述（中文）
- description_en: 描述（英文，用于绘图）
- importance: 重要程度（prop=普通道具/key_item=关键物品/mcguffin=麦格芬/情节推动物）
- first_appearance_event: 首次出现的事件索引
- visual_features: 视觉特征（英文，用于绘图）

## 输出格式

请以 JSON 格式输出，确保格式正确可解析：

```json
{{
  "characters": {{
    "角色名1": {{
      "name": "角色名1",
      "appearance": "English appearance description...",
      "appearance_zh": "中文外观描述...",
      "personality": "性格特点",
      "role": "protagonist",
      "gender": "male",
      "age_description": "青年",
      "first_appearance_event": 0,
      "relationships": {{"角色名2": "朋友"}}
    }}
  }},
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
  ],
  "scenes": [
    {{
      "index": 0,
      "location": "地点",
      "location_en": "Location in English",
      "time_of_day": "day",
      "atmosphere": "氛围描述",
      "weather": null,
      "lighting": "natural",
      "indoor_outdoor": "indoor",
      "description": "场景描述",
      "event_indices": [0, 1, 2]
    }}
  ],
  "events": [
    {{
      "index": 0,
      "type": "dialogue",
      "description": "事件描述",
      "description_en": "Event description in English",
      "participants": ["角色名1", "角色名2"],
      "scene_index": 0,
      "importance": "normal",
      "dialogue_indices": [0, 1],
      "action_description": "Action description for drawing",
      "visual_focus": "The focus point of this scene",
      "emotion_tone": "tense",
      "is_climax": false
    }}
  ],
  "items": [
    {{
      "name": "物品名",
      "name_en": "Item name",
      "description": "物品描述",
      "description_en": "Item description in English",
      "importance": "prop",
      "first_appearance_event": 0,
      "visual_features": "Visual features for drawing"
    }}
  ],
  "chapter_summary": "章节内容的简短摘要（2-3句话）",
  "chapter_summary_en": "Brief summary in English",
  "mood_progression": ["开始时的情绪", "中间的情绪变化", "结束时的情绪"],
  "climax_event_indices": [5, 6],
  "total_estimated_pages": 10
}}
```

## 重要提示

1. **外观描述**：角色的 appearance 字段必须是英文，且足够详细，包含发色、发型、眼睛颜色、服装风格、体型、年龄外观等信息
2. **事件粒度**：事件应该是可以在漫画中可视化呈现的最小单元，不要过于宏观或过于琐碎
3. **对话完整性**：提取所有对话，包括内心独白，保持原文不要改写
4. **场景连续性**：注意场景之间的转换，不要遗漏过渡场景
5. **高潮识别**：准确识别章节中的高潮/关键事件，这些事件后续会得到更多画面
6. **物品识别**：只提取对剧情有影响的物品，背景装饰物不需要提取
7. **预估页数**：根据事件数量和复杂度，估计这章内容适合用多少页漫画来呈现（通常5-15页）

请确保输出的 JSON 格式正确，所有字段都有值（可以为空字符串或空列表，但不要省略字段）。
