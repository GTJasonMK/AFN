"""
场景提取提示词模板

包含场景提取相关的提示词和语言配置。
"""


# 场景提取提示词模板
SCENE_EXTRACTION_PROMPT = """你是专业的漫画分镜师。请从以下章节内容中识别关键叙事场景。

## 章节内容
{content}

## 要求
1. 识别 {min_scenes}-{max_scenes} 个关键场景
2. 每个场景应该是一个独立的叙事单元（可以展开为1-2页漫画）
3. 注意场景的情感变化和节奏
4. 标注每个场景的重要性

## 语言设置（极其重要，必须严格遵守）
目标语言: {dialogue_language}

**重要约束**：
- 场景内容(content)字段：保留原文用于上下文理解
- 角色外观描述(character_profiles)：必须使用英文（用于AI绘图）
- 此阶段无需生成对话，对话将在后续阶段根据目标语言生成

## 角色外观描述要求（极其重要）
character_profiles 必须包含本章节中出现的**所有角色**的外观描述，包括：
- 主要角色（主角、重要配角）
- 次要角色（路人、店员、士兵、侍女等）
- 群体角色（如"士兵A"、"村民B"等需要分别描述）

每个角色的外观描述必须包含：
- 性别、大致年龄
- 发型、发色
- 服装特征
- 体型特征（如适用）
- 任何显著的视觉特征（如伤疤、饰品等）

示例：
```json
"character_profiles": {{
  "李明": "young man in his 20s, short black hair, wearing modern casual clothes, slim build",
  "王大妈": "elderly woman in her 60s, gray hair in a bun, wearing traditional Chinese dress, kind face",
  "店员": "young woman, brown ponytail, wearing cafe uniform with apron, friendly appearance",
  "士兵A": "muscular man, short military haircut, wearing armor, stern expression",
  "士兵B": "thin young man, helmet covering hair, wearing armor, nervous expression"
}}
```

## 输出格式
```json
{{
  "scenes": [
    {{
      "scene_id": 1,
      "summary": "场景简要描述（20字内）",
      "content": "场景对应的原文内容（可以是摘要）",
      "characters": ["出场角色"],
      "mood": "情感类型（calm/tension/action/emotional/mystery/comedy/dramatic/romantic/horror/flashback）",
      "importance": "重要程度（low/normal/high/critical）",
      "has_dialogue": true/false,
      "is_action": true/false
    }}
  ],
  "character_profiles": {{
    "角色名": "外观描述（用于AI绘图，英文，包含性别、年龄、发型、服装、体型等）"
  }}
}}
```
"""


# 语言提示映射
LANGUAGE_HINTS = {
    "chinese": "中文",
    "japanese": "日语",
    "english": "英文",
    "korean": "韩语",
}


__all__ = [
    "SCENE_EXTRACTION_PROMPT",
    "LANGUAGE_HINTS",
]
