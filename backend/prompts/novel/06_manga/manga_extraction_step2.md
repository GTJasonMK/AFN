---
title: 分步提取-对话和旁白
description: 分步提取策略的第二步，提取对话、想法和旁白信息
tags: manga, extraction, dialogues, narrations
---

请从以下章节内容中提取所有对话和旁白信息。

## 章节内容
{content}

## 已识别的角色（含详细信息）
{characters_json}

**角色信息说明**：
- name: 角色名字
- appearance: 外观描述（用于识别角色）
- personality: 性格特点（用于判断说话风格）
- role: 角色定位（protagonist/antagonist/supporting/minor/background）
- gender: 性别

请根据角色的性格特点和说话风格，准确匹配对话的说话人。

## 已识别的事件
{events_json}

**事件字段说明**：
- index: 事件索引（用于关联对话的event_index）
- description: 事件描述（用于判断对话发生的上下文）
- participants: 参与角色列表（对话的说话人通常是参与者之一）
- type: 事件类型（dialogue对话/action动作/conflict冲突等）

**关联对话到事件的方法**：
1. 根据对话内容在原文中的位置，找到最接近的事件
2. 对话的说话人通常是该事件的参与者之一
3. 如果无法确定，选择最相关的事件索引

## 提取要求

### 一、对话和想法提取

**核心原则：精选关键对话，每个气泡不超过30字！**

漫画是视觉媒体，对话应该精简。遵循"Show don't tell"原则：能用画面表达的不用对话。

**应该提取的对话：**
- 推动情节的关键对话（转折点、决定性时刻）
- 塑造角色性格的对话
- 无法用画面表达的具体信息（名字、数字、计划）

**应该省略的对话：**
- 画面已经表达的内容（角色在哭，不需要说"我好难过"）
- 过渡性寒暄（"你好"、"再见"、"嗯"、"啊"）
- 冗长的解释性对话（应精简或改用旁白）

**字段说明：**
- index: 对话序号（从0开始）
- speaker: 说话人名字（必须是已识别角色之一）
- content: 对话内容（**不超过30字**，过长需精简）
- emotion: neutral/happy/sad/angry/surprised/fearful/excited/calm/nervous/determined
- target: 对话对象（可为null）
- event_index: 所属事件索引
- is_internal: 是否是内心独白（true/false）
- bubble_type: thought/normal/shout/whisper

**对话与想法的区分：**
- **对话(dialogue)**: 角色说出来的话，用普通对话气泡
- **想法(thought)**: 角色内心独白，用云朵气泡（is_internal=true, bubble_type="thought"）

**想法提取原则：**
- 只提取**关键的内心转折**，不是所有心理活动都需要
- 应该提取：重要决定、情感爆发、关键领悟
- 不要提取：琐碎的心理活动、与画面重复的情绪

**视角转换规则：**
- **对话**：保持原文不变
- **想法**：必须转换为第一人称！
  - "她觉得自己很累" → "我好累"
  - "他认为这是个陷阱" → "这是个陷阱"
  - 去掉"心想"、"暗道"等引导词

### 二、旁白提取

**核心原则：旁白必须是原文中的原句或基于原文的简洁概括，禁止凭空编造！**

只提取以下四种类型的旁白：
- index: 旁白序号（从0开始）
- content: 旁白内容（尽量使用原文原句）
- narration_type: 旁白类型（只有四种）
  - time: 时间跳转/标记，如"三天后..."、"那是周三下午三点"
  - exposition: 背景说明，如"这座城市已沦陷三年"、"十二年来，她从未..."
  - character_intro: 人物首次出场介绍，如"林晓雨，32岁，某公司高管"
  - transition: 场景转换连接，如"与此同时，在另一边..."
- event_index: 所属事件索引
- position: 建议位置 top/bottom

**不要提取的内容：**
- 场景描述 → 通过画面表现，不需要旁白
- 心理描写 → 已通过thought提取，不要重复

**提取标准：**
1. 优先使用原文中的句子
2. 人物介绍可以基于原文信息简洁概括
3. 宁可少提取，也不要编造

## 输出格式

```json
{{
  "dialogues": [
    {{
      "index": 0,
      "speaker": "林晓雨",
      "content": "你好，请问有什么事？",
      "emotion": "neutral",
      "target": "陌生人",
      "event_index": 0,
      "is_internal": false,
      "bubble_type": "normal"
    }},
    {{
      "index": 1,
      "speaker": "林晓雨",
      "content": "我不认识这个人...",
      "emotion": "fearful",
      "target": null,
      "event_index": 0,
      "is_internal": true,
      "bubble_type": "thought"
    }}
  ],
  "narrations": [
    {{
      "index": 0,
      "content": "那是周三下午三点二十分",
      "narration_type": "time",
      "event_index": 0,
      "position": "top"
    }}
  ]
}}
```

注意：想法(thought)的content使用第一人称"我"，而不是"她/他"。

请确保JSON格式正确。只输出JSON，不要其他文字。
