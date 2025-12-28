"""
场景展开提示词模板

包含场景分析和画格内容分配的LLM提示词模板。
"""


# LLM提示词模板：场景分析
SCENE_ANALYSIS_PROMPT = """你是专业的漫画分镜师。请分析以下叙事场景，为漫画分镜提供指导。

## 场景内容
{scene_content}

## 场景摘要
{scene_summary}

## 上下文
- 前一场景: {previous_scene}
- 后一场景: {next_scene}
- 章节位置: {chapter_position}

请以JSON格式输出分析结果：
```json
{{
  "mood": "场景情感（calm/tension/action/emotional/mystery/comedy/dramatic/romantic/horror/flashback）",
  "importance": "重要程度（low/normal/high/critical）",
  "has_dialogue": true/false,
  "is_action": true/false,
  "is_climax": true/false,
  "key_moments": [
    {{
      "description": "关键时刻描述",
      "visual_focus": "视觉焦点",
      "emotion": "情感",
      "suggested_shot": "建议镜头（wide/medium/close-up/extreme close-up）"
    }}
  ],
  "characters_present": ["角色名"],
  "atmosphere": "整体氛围描述",
  "pacing_suggestion": "节奏建议（slow/normal/fast）",
  "recommended_panel_count": 4-8之间的数字
}}
```
"""


# LLM提示词模板：画格内容分配
PANEL_DISTRIBUTION_PROMPT = """你是专业的漫画分镜师。请将场景内容分配到指定的画格中。

## 场景信息
- 内容: {scene_content}
- 情感: {mood}
- 关键时刻: {key_moments}
- 角色: {characters}

## 页面模板
模板名称: {template_name}
模板特点: {template_description}

## 画格槽位
{panel_slots_description}

#############################################
## 【最重要】语言设置 - 违反将导致结果被拒绝
#############################################

**唯一允许使用的语言：{language_hint}**

### 绝对禁止的语言错误 ###
{forbidden_languages}

### 强制语言规则（必须100%遵守）###
1. dialogue（对话）: 只能使用{language_hint}，禁止任何其他语言
2. narration（旁白）: 只能使用{language_hint}，禁止任何其他语言
3. sound_effects（音效）: 只能使用{language_hint}的拟声词，禁止任何其他语言
4. sound_effect_details中的text: 只能使用{language_hint}，禁止任何其他语言

### 正确的{language_hint}音效词示例 ###
{sfx_examples}

#############################################

## 要求
1. 为每个画格分配具体内容
2. 遵循视觉叙事原则（建立->发展->高潮->反应）
3. 利用画格大小表达重要性
4. 注意镜头变化的节奏感
5. 对话要简短有力（每句不超过12字）
6. 根据说话内容和情绪选择合适的气泡类型
7. 为动作场景添加适当的音效

## 【重要】对话提取要求
漫画的核心是角色对话，请严格遵循以下规则：

1. **必须提取原文对话**: 仔细阅读场景内容，将原文中的对话分配到合适的画格
   - 原文中用引号（"" 或 「」）标注的内容是角色对话
   - 原文中的"说"、"道"、"问"等动词前后通常是对话内容
   - 不要遗漏任何重要对话

2. **对话分配原则**:
   - 每个有对话的画格只放1-2句话，保持简洁
   - 对话较长时，拆分到多个画格中
   - 确保对话的说话者(dialogue_speaker)正确对应

3. **对话必填检查**: 如果场景内容中包含对话，至少要有2-3个画格包含dialogue字段
   - 检查原文中的引号内容
   - 确保重要对话不被遗漏

4. **旁白使用**: 对于原文中的心理描写、环境描述，使用narration字段

## 【重要】镜头连贯性要求
为确保相邻画格之间的视觉连贯性，请遵循以下原则：

1. **渐进式镜头变化**: 避免突然的大跨度镜头跳跃
   - 推荐: 全景 -> 中景 -> 特写（逐步推进）
   - 避免: 大特写直接跳到全景（除非有意制造强烈对比）

2. **角色视觉锚定**: 当同一角色出现在连续画格中时
   - 保持角色的服装、发型、位置的视觉连贯
   - 在content_description中明确描述角色的关键视觉特征

3. **环境连续性**: 同一场景内的画格应保持环境一致
   - 在key_visual_elements中保留场景标志性元素
   - 确保光线和氛围的连贯

4. **镜头过渡逻辑**:
   - 全景(wide) -> 中景(medium): 从环境介绍过渡到人物聚焦
   - 中景(medium) -> 特写(close-up): 强调情感或细节
   - 特写(close-up) -> 中景/全景: 展示反应或揭示场景
   - 相同镜头连续: 保持节奏，用于对话场景

## 对话气泡类型说明
- normal: 普通对话（圆形边框）
- shout: 大喊/激动（锯齿边框）
- whisper: 低语/私语（虚线边框）
- thought: 内心独白/心理活动（云朵形状）
- narration: 旁白叙述（矩形方框）
- electronic: 电话/电子设备（波浪边框）

## 气泡位置说明
- top-right, top-left, top-center: 画面顶部
- middle-right, middle-left: 画面中部
- bottom-right, bottom-left, bottom-center: 画面底部

## 音效类型说明
- action: 动作音效
- impact: 撞击音效
- ambient: 环境音效
- emotional: 情感音效
- vocal: 人声音效

## 音效强度说明
- small: 次要音效，小字体
- medium: 中等音效，中等字体
- large: 主要音效，大字体，视觉冲击

请以JSON格式输出：
```json
{{
  "panels": [
    {{
      "slot_id": 1,
      "content_description": "这个画格展示什么内容（中文简述）",
      "prompt_en": "完整的英文AI绘图提示词，包含：风格、构图、角度、角色外观、动作、表情、环境、光线、氛围等。要求专业、详细、适合AI图像生成。示例：manga style, medium shot, eye level, young woman with long black hair speaking excitedly, open mouth, bright smile, sparkle eyes, speech bubble at top right, warm lighting, cozy cafe interior, detailed background",
      "negative_prompt": "负面提示词（英文），用于排除不想要的元素。示例：low quality, blurry, distorted face, extra limbs, bad anatomy, text, watermark",
      "narrative_purpose": "叙事目的",
      "characters": ["出场角色"],
      "character_emotions": {{"角色名": "情绪"}},
      "composition": "构图方式（wide shot/medium shot/close-up/extreme close-up）",
      "camera_angle": "镜头角度（eye level/low angle/high angle/dutch angle）",
      "dialogue": "对话内容（从原文提取，使用{language_hint}，不超过12字）",
      "dialogue_speaker": "说话者（必须是characters中的角色名）",
      "dialogue_bubble_type": "normal|shout|whisper|thought|narration|electronic",
      "dialogue_position": "top-right|top-left|top-center|bottom-right|bottom-left|bottom-center",
      "dialogue_emotion": "说话时的情绪",
      "narration": "旁白（心理描写或环境描述，使用{language_hint}，不超过20字）",
      "narration_position": "top|bottom",
      "sound_effects": ["音效文字（只能使用{language_hint}拟声词）"],
      "sound_effect_details": [
        {{
          "text": "音效文字（只能使用{language_hint}拟声词）",
          "type": "impact",
          "intensity": "large",
          "position": "画面中央"
        }}
      ],
      "key_visual_elements": ["关键视觉元素"],
      "atmosphere": "氛围",
      "lighting": "光线描述"
    }}
  ],
  "page_purpose": "这一页的整体叙事目的"
}}
```

## 【极重要】prompt_en 生成要求
prompt_en 是最关键的字段，必须是高质量的英文AI绘图提示词：

1. **必须包含的元素**（按顺序）：
   - 风格：manga style / anime style / comic style（根据场景情感选择最适合的风格）
   - 构图：wide shot, medium shot, close-up, extreme close-up
   - 角度：eye level, low angle, high angle, dutch angle
   - 角色描述：外观特征、服装、姿态、表情
   - 动作描述：如果有对话则包含 "speaking, open mouth" 等
   - 情绪视觉效果：sparkle eyes, sweat drops, anger vein 等漫画符号
   - 环境/背景：详细的场景描述
   - 光线氛围：warm lighting, dramatic shadows 等

2. **对话场景必须体现**：
   - 说话者的说话动作：speaking, open mouth, talking
   - 气泡类型视觉：speech bubble, thought bubble, shout bubble
   - 说话时的表情和情绪

3. **风格关键词要求**（必须包含在prompt_en开头）：
   - 平静/日常场景：manga style, clean line art, soft shading, warm tones
   - 动作/战斗场景：manga style, dynamic composition, speed lines, motion blur, high contrast
   - 情感/浪漫场景：manga style, soft focus, dreamy atmosphere, gentle lighting, sparkle effects
   - 紧张/悬疑场景：manga style, high contrast, dramatic shadows, tense atmosphere
   - 恐怖场景：manga style, dark shadows, ominous lighting, horror atmosphere
   - 搞笑场景：manga style, exaggerated expressions, comedic style, chibi elements

4. **质量要求**：
   - 使用专业的AI绘图术语
   - 描述要具体，避免模糊词汇
   - 长度适中（50-150个英文单词）

## 【极重要】negative_prompt 生成要求
negative_prompt 是防止生成质量问题的关键字段，必须根据场景智能生成：

1. **通用质量问题（所有场景必须包含）**：
   - low quality, blurry, pixelated, jpeg artifacts, watermark, signature

2. **AI常见缺陷（所有场景必须包含）**：
   - bad anatomy, wrong proportions, extra limbs, missing fingers, deformed hands
   - plastic skin, waxy appearance, uncanny valley, lifeless eyes

3. **场景特定的负面提示词**（根据场景类型添加）：

   **动作场景**应额外排除：
   - static pose, stiff movement, frozen action, no motion blur

   **情感/浪漫场景**应额外排除：
   - cold atmosphere, harsh lighting, aggressive expression

   **恐怖场景**应额外排除：
   - bright lighting, cheerful atmosphere, warm colors

   **搞笑场景**应额外排除：
   - serious expression, dark atmosphere, realistic style

   **日常场景**应额外排除：
   - dramatic lighting, intense expression, action poses

4. **风格一致性排除**：
   - 如果是黑白漫画风格，必须包含：color, colored, vibrant colors
   - 如果是彩色漫画风格，必须包含：black and white, monochrome, grayscale
   - 所有漫画风格必须排除：photorealistic, 3D render, CGI, hyper-realistic

5. **负面提示词长度**：30-80个英文单词，不要太短也不要太长

**重要提醒**：
1. 所有dialogue、narration、sound_effects字段必须使用{language_hint}，禁止使用其他语言！
2. dialogue字段应该从原文中提取角色的实际对话，不要遗漏！
3. prompt_en必须是高质量的英文提示词，直接用于AI图像生成！
4. negative_prompt必须根据场景情感智能生成，不要使用固定模板！
"""


__all__ = [
    "SCENE_ANALYSIS_PROMPT",
    "PANEL_DISTRIBUTION_PROMPT",
]
