"""
分镜设计模块提示词

定义分镜设计的 LLM 提示词模板。
包含排版信息和画面细节。
"""

# 提示词名称（用于从 PromptService 加载）
PROMPT_NAME = "manga_storyboard_design"

# 分镜设计提示词模板
STORYBOARD_DESIGN_PROMPT = """你是漫画分镜师，请为章节内容设计分镜布局。

## 排版规则

### 画格形状
- **horizontal**: 横向画格
- **vertical**: 纵向画格
- **square**: 正方形画格

### 宽度占比 (width_ratio) - 必须根据内容选择！
- **full**: 占整行宽度 - 用于：重要高潮、震撼场景、环境建立、章节开场/结尾
- **two_thirds**: 占2/3行宽度 - 用于：主要角色动作、重要对话、关键反应
- **half**: 占半行宽度（最常用）- 用于：对话双方、动作序列、一般叙事
- **third**: 占1/3行宽度 - 仅用于：快速特写、细节强调、过渡镜头

**布局多样性硬性要求（必须遵守！）**：
- 禁止：整页全部使用 third 宽度（会导致5-6个窄条，非常难看）
- 禁止：整页全部使用相同宽度（除非是full独占）
- 要求：每页必须有至少2种不同的 width_ratio
- 建议：重要内容用 full 或 two_thirds，普通内容用 half，仅快速过渡用 third

### 宽高比 (aspect_ratio)
- **16:9**: 宽屏，适合远景、场景展示
- **4:3**: 标准，适合中景、对话
- **1:1**: 正方形，适合特写、表情
- **3:4**: 竖向，适合人物全身
- **9:16**: 超竖向，适合纵向动作

### 行布局系统 (row_id + row_span)
- **row_id**: 画格起始行号（从1开始）
- **row_span**: 画格跨越的行数（默认1，最大3）
- 同一行的画格并排显示，宽度之和必须等于100%

### 跨行布局规则
- 一个画格可以跨越多行（row_span > 1）
- **核心规则**：同一"列区域"内，画格的 row_span 之和必须相等
- 示例：左边A跨2行，右边B+C各占1行
  ```
  ┌─────────┬─────────┐
  │         │    B    │  B: row_id=1, row_span=1
  │    A    ├─────────┤
  │         │    C    │  C: row_id=2, row_span=1
  └─────────┴─────────┘
  A: row_id=1, row_span=2, width_ratio=half
  B: row_id=1, row_span=1, width_ratio=half
  C: row_id=2, row_span=1, width_ratio=half
  左侧 row_span 总和 = 2，右侧 row_span 总和 = 1+1 = 2（必须相等）
  ```

### 高度对齐规则
- **同一行的画格高度必须一致**（前端会自动拉伸对齐）
- 同一行的画格应使用**相同或相近的宽高比**，确保视觉协调
- 跨行画格的高度 = 跨越行数 × 单行高度 + 间隙
- 推荐搭配：
  - 横向行：都用 16:9 或 4:3（宽屏/标准）
  - 竖向行：都用 3:4 或 9:16（竖屏）
  - 混合行：用 1:1（正方形）作为过渡
- 避免同一行出现极端差异（如 16:9 和 9:16 并排）

### 间隙说明
- 画格之间有间隙（gutter），前端默认为 8px
- 计算布局时需考虑间隙占用的空间
- 间隙由前端统一处理，LLM只需关注 width_ratio 和 row_span

### 排版原则
- 每页 3-6 个画格，分为 2-4 行
- 画格排版要紧凑饱满，充分利用页面空间
- **重要规则**：同一行(row_id相同)的画格宽度占比之和必须等于100%
  - full = 100%（独占一行）
  - half + half = 100%（两个半宽并排）
  - third + two_thirds = 100%（1/3 + 2/3并排）
  - two_thirds + third = 100%（2/3 + 1/3并排）
- **多样性规则**：
  - 每页必须包含至少2种不同的 width_ratio
  - 禁止一页全部使用 third（会产生难看的窄条布局）
  - 推荐组合：full + half、half + half、two_thirds + third
- 合理搭配不同尺寸的画格，体现叙事节奏
- 适当使用跨行布局增加视觉冲击力

## 页面信息

第 {page_number} 页 / 共 {total_pages} 页

### 场景环境
{scene_context}

### 包含的事件
{events_json}

### 相关对话
{dialogues_json}

### 出场角色
{characters_json}

### 建议分镜数量
{suggested_panel_count} 格

### 上一页最后一格
{previous_panel}

## 设计要求

1. **分镜数量**: {min_panels}-{max_panels} 格
2. **排版饱满**: 合理分配画格尺寸，让页面布局紧凑有层次
3. **画面细节**: 每个画格需要包含完整的画面信息

## 输出格式

```json
{{
  "page_number": {page_number},
  "panels": [
    {{
      "panel_id": 1,
      "row_id": 1,
      "row_span": 1,
      "shape": "horizontal",
      "width_ratio": "full",
      "aspect_ratio": "16:9",
      "shot_type": "long",
      "visual_description": "中文画面描述",
      "characters": ["角色1"],
      "background": "背景描述",
      "atmosphere": "氛围",
      "lighting": "光线",
      "character_actions": {{"角色1": "动作"}},
      "character_expressions": {{"角色1": "表情"}},
      "dialogues": [{{"speaker": "角色1", "content": "对话"}}],
      "event_indices": [0]
    }},
    {{
      "panel_id": 2,
      "row_id": 2,
      "row_span": 2,
      "shape": "vertical",
      "width_ratio": "half",
      "aspect_ratio": "3:4",
      "shot_type": "medium",
      "visual_description": "跨两行的大画面，展示人物全身",
      "characters": ["角色1"],
      "background": "室内场景",
      "atmosphere": "紧张",
      "lighting": "侧光",
      "character_actions": {{"角色1": "站立"}},
      "character_expressions": {{"角色1": "严肃"}},
      "dialogues": [],
      "event_indices": [0]
    }},
    {{
      "panel_id": 3,
      "row_id": 2,
      "row_span": 1,
      "shape": "square",
      "width_ratio": "half",
      "aspect_ratio": "1:1",
      "shot_type": "close_up",
      "visual_description": "特写画面",
      "characters": ["角色2"],
      "background": "",
      "atmosphere": "紧张",
      "lighting": "聚光",
      "character_actions": {{}},
      "character_expressions": {{"角色2": "惊讶"}},
      "dialogues": [],
      "event_indices": [0]
    }},
    {{
      "panel_id": 4,
      "row_id": 3,
      "row_span": 1,
      "shape": "horizontal",
      "width_ratio": "half",
      "aspect_ratio": "4:3",
      "shot_type": "medium",
      "visual_description": "人物中景对话",
      "characters": ["角色2"],
      "background": "室内",
      "atmosphere": "平静",
      "lighting": "自然光",
      "character_actions": {{"角色2": "转身"}},
      "character_expressions": {{"角色2": "微笑"}},
      "dialogues": [{{"speaker": "角色2", "content": "对话内容"}}],
      "event_indices": [1]
    }}
  ],
  "layout_description": "第一行：1格占整行；第二三行：左侧2格跨两行(row_span=2)，右侧3格和4格各占一行(row_span=1+1=2，与左侧对齐)"
}}
```

请确保：
1. JSON 格式正确
2. **同一 row_id 的画格宽度之和必须等于100%**（full=100%, half+half=100%, third+two_thirds=100%）
3. **跨行布局时，同一列区域的 row_span 之和必须相等**
4. **同一 row_id 的画格使用相同或相近的宽高比**（避免16:9和9:16同行）
5. aspect_ratio 与 shape 匹配（横向用16:9或4:3，竖向用3:4或9:16，正方形用1:1）
6. row_id 从1开始递增，row_span 默认为1（不跨行时可省略）
7. **布局多样性**：每页必须使用至少2种不同的 width_ratio，禁止全部使用 third
"""

# 系统提示词
STORYBOARD_SYSTEM_PROMPT = """你是专业漫画分镜师，负责将故事内容转换为视觉冲击力强的分镜布局。

你的任务：
1. 将故事事件分解为画格
2. **根据内容重要性**分配画格尺寸（重要内容用大格，过渡用小格）
3. 编写详细的画面描述
4. 以 JSON 格式输出结果

**核心原则：内容决定尺寸**
- 震撼场景、高潮时刻 → full 宽度（独占一行）
- 重要对话、关键动作 → two_thirds 或 half 宽度
- 普通叙事、对话双方 → half 宽度（最常用）
- 快速特写、过渡镜头 → third 宽度（仅用于小格）

**布局多样性（必须遵守！）**：
- 禁止：整页全部使用 third 宽度（会产生5-6个窄条，极其难看）
- 禁止：整页全部使用相同 width_ratio（除非是 full 独占）
- 要求：每页必须使用至少2种不同的 width_ratio
- 推荐：full+half、half+half、two_thirds+third 的组合

行布局系统：
- **row_id**: 画格起始行号（从1开始）
- **row_span**: 画格跨越的行数（默认1，最大3）
- **宽度规则**：同一行(row_id相同)的画格宽度之和必须等于100%
- **高度规则**：同一行的画格高度一致，应使用相同或相近的宽高比
- **跨行规则**：同一"列区域"内，画格的 row_span 之和必须相等

跨行布局示例：
```
┌─────────┬─────────┐
│         │    B    │  B: row_id=1, row_span=1
│    A    ├─────────┤  A: row_id=1, row_span=2
│         │    C    │  C: row_id=2, row_span=1
└─────────┴─────────┘
左侧 A 的 row_span=2
右侧 B+C 的 row_span=1+1=2（必须相等）
```

同一行宽高比搭配建议：
- 横向行：都用 16:9 或 4:3（场景展示、对话）
- 竖向行：都用 3:4 或 9:16（人物全身、纵向动作）
- 混合行：用 1:1 正方形作为过渡（特写表情）
- 禁止：16:9 和 9:16 同一行（高度差异过大）

常见布局模板（根据内容选择）：
- 开场页：full(场景) + half+half(角色)
- 对话页：half+half(对话双方) × 2-3行
- 动作页：full(主动作) + third+two_thirds(反应)
- 高潮页：full(震撼画面) + two_thirds+third(特写)
- 过渡页：half+half + third+two_thirds

请确保输出的 JSON 格式正确，且满足布局多样性要求。
"""

__all__ = [
    "PROMPT_NAME",
    "STORYBOARD_DESIGN_PROMPT",
    "STORYBOARD_SYSTEM_PROMPT",
]
