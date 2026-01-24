"""
信息提取模块提示词

定义从章节内容中提取结构化信息的 LLM 提示词模板。

注意：此文件作为内置备用提示词。
用户可编辑的版本位于 backend/prompts/manga_chapter_extraction.md
ChapterInfoExtractor 会优先从 PromptService 加载，找不到时使用此处定义。

分步提取策略：
为避免单次LLM调用输出过大导致JSON被截断，将提取任务分为4个步骤：
1. 步骤1：提取角色 + 基础事件
2. 步骤2：提取对话信息
3. 步骤3：提取场景信息
4. 步骤4：提取物品 + 摘要信息
"""

# 提示词名称（用于从 PromptService 加载）
PROMPT_NAME = "manga_chapter_extraction"

# 分步提取提示词名称
PROMPT_NAME_STEP1 = "manga_extraction_step1"
PROMPT_NAME_STEP2 = "manga_extraction_step2"
PROMPT_NAME_STEP3 = "manga_extraction_step3"
PROMPT_NAME_STEP4 = "manga_extraction_step4"

from ..prompts_shared import EVENT_FIELDS_BASE

# 对话字段说明（主模板与分步模板共用）
DIALOGUE_FIELDS_BASE = """- index: 对话序号（从0开始）
- speaker: 说话人名字（必须是已识别角色之一）
- content: 对话内容（保留原文）
- emotion: 情绪（neutral/happy/sad/angry/surprised/fearful/disgusted/contemptuous/excited/calm/nervous/determined）
- target: 对话对象（如有明确对象）
- event_index: 所属事件索引（对应events中的index）
- is_internal: 是否是内心独白（心想、暗道、心中想等 → true；说出来的话 → false）
- bubble_type: 气泡类型（thought用于内心想法；normal/shout/whisper用于说出的话）
"""

# 场景字段说明（主模板与分步模板共用）
SCENE_FIELDS_BASE = """- index: 场景序号（从0开始）
- location: 地点描述
- time_of_day: 时间（morning/afternoon/evening/night/dawn/dusk）
- atmosphere: 氛围描述
- weather: 天气（如有描述）
- lighting: 光线（natural/dim/bright/dramatic/soft）
- indoor_outdoor: 室内还是室外（indoor/outdoor）
- description: 场景的详细描述
- event_indices: 该场景包含的事件索引列表
"""

# 章节信息提取提示词模板
CHAPTER_INFO_EXTRACTION_PROMPT = (
"""你是专业的漫画编剧助手。请从以下章节内容中提取结构化信息，用于后续的漫画分镜设计。

## 章节内容
{content}

## 提取要求

请仔细阅读章节内容，提取以下五类信息：

### 1. 角色信息 (characters)
为每个出场角色提取：
- name: 角色名
- appearance: 外观描述（详细描述发型、服装、体型、年龄特征等）
- personality: 性格特点（简短描述）
- role: 角色定位（protagonist=主角 / antagonist=反派 / supporting=重要配角 / minor=次要角色 / background=背景角色）
- gender: 性别（male/female/unknown）
- age_description: 年龄描述（如"青年"、"中年"、"少女"等）
- relationships: 与其他角色的关系，格式为 {{"角色名": "关系描述"}}

### 2. 对话信息 (dialogues)
按顺序提取所有对话和内心独白：
""" + DIALOGUE_FIELDS_BASE + """

**重要：对话和想法必须正确区分，这直接影响漫画中气泡的绘制方式（对话用普通气泡，想法用云朵气泡）。**

### 3. 场景信息 (scenes)
识别不同的场景/地点：
""" + SCENE_FIELDS_BASE + """

### 4. 事件信息 (events)
按时间顺序提取关键事件：
""" + EVENT_FIELDS_BASE + """- scene_index: 所属场景索引
- importance: 重要程度（low/normal/high/critical）
- dialogue_indices: 关联的对话索引列表
- action_description: 动作描述
- visual_focus: 视觉焦点描述
- emotion_tone: 情绪基调
- is_climax: 是否是高潮/关键时刻（true/false）

### 5. 物品信息 (items)
识别故事中的重要物品/道具：
- name: 物品名
- description: 描述
- importance: 重要程度（prop=普通道具/key_item=关键物品/mcguffin=麦格芬/情节推动物）
- first_appearance_event: 首次出现的事件索引
- visual_features: 视觉特征

## 输出格式

请以 JSON 格式输出，确保格式正确可解析：

```json
{{
  "characters": {{
    "角色名1": {{
      "name": "角色名1",
      "appearance": "详细外观描述...",
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
      "participants": ["角色名1", "角色名2"],
      "scene_index": 0,
      "importance": "normal",
      "dialogue_indices": [0, 1],
      "action_description": "动作描述",
      "visual_focus": "视觉焦点",
      "emotion_tone": "紧张",
      "is_climax": false
    }}
  ],
  "items": [
    {{
      "name": "物品名",
      "description": "物品描述",
      "importance": "prop",
      "first_appearance_event": 0,
      "visual_features": "视觉特征"
    }}
  ],
  "chapter_summary": "章节内容的简短摘要（2-3句话）",
  "mood_progression": ["开始时的情绪", "中间的情绪变化", "结束时的情绪"],
  "climax_event_indices": [5, 6],
  "total_estimated_pages": 10
}}
```

## 重要提示

1. **外观描述**：角色的 appearance 字段需足够详细，包含发色、发型、眼睛颜色、服装风格、体型、年龄外观等信息
2. **事件粒度**：事件应该是可以在漫画中可视化呈现的最小单元，不要过于宏观或过于琐碎
3. **对话完整性**：提取所有对话，包括内心独白，保持原文不要改写
4. **场景连续性**：注意场景之间的转换，不要遗漏过渡场景
5. **高潮识别**：准确识别章节中的高潮/关键事件，这些事件后续会得到更多画面
6. **物品识别**：只提取对剧情有影响的物品，背景装饰物不需要提取
7. **预估页数**：根据事件数量和复杂度，估计这章内容适合用多少页漫画来呈现（通常5-15页）

请确保输出的 JSON 格式正确，所有字段都有值（可以为空字符串或空列表，但不要省略字段）。
"""
)

# 系统提示词（用于设置 LLM 的角色）
EXTRACTION_SYSTEM_PROMPT = """你是一位专业的漫画编剧和分镜师助手。你的任务是分析小说章节内容，提取出用于漫画创作的结构化信息。

你需要：
1. 准确理解故事内容和人物关系
2. 识别适合可视化呈现的关键事件和场景
3. 为每个角色生成详细的外观描述（用于AI绘图）
4. 把握故事节奏，识别高潮和转折点
5. 以结构化的 JSON 格式输出结果

请始终确保输出的 JSON 格式正确，可以被程序解析。
"""

# ============================================================
# 分步提取提示词
# ============================================================

# 步骤1：提取角色和事件
STEP1_CHARACTERS_EVENTS_PROMPT = (
"""请从以下章节内容中提取角色信息和事件信息。

## 章节内容
{content}

## 提取要求

### 1. 角色信息 (characters)
为每个出场角色提取：
- name: 角色名
- appearance: 外观描述（详细描述发型、服装、体型、年龄特征）
- personality: 性格特点（简短）
- role: protagonist/antagonist/supporting/minor/background
- gender: male/female/unknown
- age_description: 年龄描述

### 2. 事件信息 (events)
按时间顺序提取关键事件：
""" + EVENT_FIELDS_BASE + """- importance: low/normal/high/critical
- is_climax: 是否是高潮点（true/false）

## 输出格式

```json
{{
  "characters": {{
    "角色名": {{
      "name": "角色名",
      "appearance": "外观描述...",
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
"""
)

# 步骤2：提取对话和旁白
STEP2_DIALOGUES_PROMPT = (
"""请从以下章节内容中提取所有对话和旁白信息。

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

## 提取要求

### 一、对话和想法提取

提取所有对话和内心独白：
""" + DIALOGUE_FIELDS_BASE + """

**重要区分：**
- **对话(dialogue)**: 角色说出来的话，用普通对话气泡
- **想法(thought)**: 角色内心独白，用云朵气泡（is_internal=true, bubble_type="thought"）

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
      "speaker": "角色名",
      "content": "对话内容",
      "emotion": "neutral",
      "target": "对话对象",
      "event_index": 0,
      "is_internal": false,
      "bubble_type": "normal"
    }}
  ],
  "narrations": [
    {{
      "index": 0,
      "content": "旁白内容",
      "narration_type": "scene",
      "event_index": 0,
      "position": "top"
    }}
  ]
}}
```

请确保JSON格式正确。只输出JSON，不要其他文字。
"""
)

# 步骤3：提取场景
STEP3_SCENES_PROMPT = (
"""请从以下章节内容中提取场景信息。

## 章节内容
{content}

## 已识别的事件
{events_json}

## 提取要求

识别不同的场景/地点：
""" + SCENE_FIELDS_BASE + """

## 输出格式

```json
{{
  "scenes": [
    {{
      "index": 0,
      "location": "地点",
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
"""
)

# 步骤4：提取物品和摘要
STEP4_ITEMS_SUMMARY_PROMPT = """请从以下章节内容中提取物品信息和章节摘要。

## 章节内容
{content}

## 已识别的事件数量
{event_count}

## 提取要求

### 1. 物品信息 (items)
只提取对剧情有影响的物品：
- name: 物品名
- description: 描述
- importance: prop/key_item/mcguffin
- first_appearance_event: 首次出现的事件索引
- visual_features: 视觉特征

### 2. 章节摘要
- chapter_summary: 章节内容摘要（2-3句话）
- mood_progression: 情绪变化轨迹（如["平静", "紧张", "高潮", "释然"]）
- total_estimated_pages: 预估漫画页数（5-15页）

## 输出格式

```json
{{
  "items": [
    {{
      "name": "物品名",
      "description": "描述",
      "importance": "prop",
      "first_appearance_event": 0,
      "visual_features": "视觉特征"
    }}
  ],
  "chapter_summary": "章节摘要...",
  "mood_progression": ["开始情绪", "中间情绪", "结束情绪"],
  "total_estimated_pages": 10
}}
```

请确保JSON格式正确。只输出JSON，不要其他文字。
"""

# 分步提取的系统提示词
STEP_EXTRACTION_SYSTEM_PROMPT = """你是一位专业的漫画编剧助手。你的任务是从小说章节中提取结构化信息，用于漫画分镜设计。

重要要求：
1. 严格按照指定格式输出JSON
2. 不要输出任何额外的解释或文字
3. 确保JSON格式正确，可以被程序解析
4. 所有字段都需要填写（可以为空字符串或空列表，但不要省略）
5. **字符串值中不要使用双引号**：如需引用词语，请用单引号或中文引号代替
   - 错误: "wearing a \"casual\" outfit"
   - 正确: "wearing a 'casual' outfit" 或 "wearing a casual outfit"
"""

__all__ = [
    "PROMPT_NAME",
    "PROMPT_NAME_STEP1",
    "PROMPT_NAME_STEP2",
    "PROMPT_NAME_STEP3",
    "PROMPT_NAME_STEP4",
    "CHAPTER_INFO_EXTRACTION_PROMPT",
    "EXTRACTION_SYSTEM_PROMPT",
    "STEP1_CHARACTERS_EVENTS_PROMPT",
    "STEP2_DIALOGUES_PROMPT",
    "STEP3_SCENES_PROMPT",
    "STEP4_ITEMS_SUMMARY_PROMPT",
    "STEP_EXTRACTION_SYSTEM_PROMPT",
]
