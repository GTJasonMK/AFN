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

提取所有对话和内心独白：
- index: 对话序号（从0开始）
- speaker: 说话人名字（必须是已识别角色之一）
- content: 对话/想法内容（见下方视角规则）
- emotion: neutral/happy/sad/angry/surprised/fearful/excited/calm/nervous/determined
- target: 对话对象
- event_index: 所属事件索引（对应events中的index）
- is_internal: 是否是内心独白（心想、暗道、心中想等 → true；说出来的话 → false）
- bubble_type: thought用于内心想法；normal/shout/whisper用于说出的话

**重要区分：**
- **对话(dialogue)**: 角色说出来的话，用普通对话气泡
- **想法(thought)**: 角色内心独白，用云朵气泡（is_internal=true, bubble_type="thought"）

**视角转换规则（非常重要）：**
- **对话**：保持原文不变（角色说出来的话本来就是第一人称或对话形式）
- **想法/内心独白**：必须转换为第一人称视角！
  - 原文中小说常用第三人称描写角色内心，如"她觉得自己很累"、"他认为这是个陷阱"
  - 提取时必须转换为角色自己的视角：
    - "她觉得自己很累" → "我好累"
    - "他认为这是个陷阱" → "这是个陷阱"
    - "林晓雨心想，她已经累了" → "我已经累了"
    - "她不认识这个女人" → "我不认识这个女人"
    - "她从来不哭" → "我从来不哭"
  - 想法气泡应该是角色内心的声音，读者看到的应该是"我..."而不是"她/他..."
  - 去掉"心想"、"暗道"、"想到"等引导词，直接写内心话语

### 二、旁白提取

提取叙述性文字（旁白），这些是作者的叙述，不是角色说的话或想的事：
- index: 旁白序号（从0开始）
- content: 旁白内容
- narration_type: 旁白类型
  - scene: 场景描述，如"夜晚，城市灯火阑珊"
  - time: 时间跳转，如"三天后..."、"第二天清晨"
  - inner: 深度心理描写（作者对角色心理的描述，非角色直接想法）
  - exposition: 背景说明，如"这座城市已沦陷三年"
- event_index: 所属事件索引
- position: 建议位置 top/bottom

**重要区分：**
- **旁白(narration)**: 作者的叙述文字，用方框旁白框
- **想法(thought)**: 角色的内心独白，用云朵气泡

例如：
- "他心想：这下完了" → 想法（角色直接的内心话语）
- "他的内心充满了绝望，仿佛世界末日来临" → 旁白/inner（作者对心理的描述）
- "夜幕降临，街道上空无一人" → 旁白/scene（场景描述）

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
      "content": "夜幕降临，城市的霓虹灯渐次亮起",
      "narration_type": "scene",
      "event_index": 0,
      "position": "top"
    }}
  ]
}}
```

注意：想法(thought)的content使用第一人称"我"，而不是"她/他"。

请确保JSON格式正确。只输出JSON，不要其他文字。
