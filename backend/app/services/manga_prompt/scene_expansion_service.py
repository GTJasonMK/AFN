"""
场景展开服务

将叙事场景展开为专业漫画分镜（页面+画格）。
这是实现真正漫画效果的核心服务。

核心流程：
1. 分析场景的情感、重要性、内容类型
2. 选择合适的页面模板
3. 将场景内容分配到各个画格
4. 生成画格级别的内容描述
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .page_templates import (
    PageTemplate,
    PanelSlot,
    PanelContent,
    PagePlan,
    SceneExpansion,
    SceneMood,
    PanelPurpose,
    ALL_TEMPLATES,
    recommend_template,
    get_template,
)
from app.utils.json_utils import parse_llm_json_safe

logger = logging.getLogger(__name__)

# 语言提示映射
LANGUAGE_HINTS = {
    "chinese": "中文",
    "japanese": "日语",
    "english": "英文",
    "korean": "韩语",
}

# 各语言的音效示例
SOUND_EFFECT_EXAMPLES = {
    "chinese": "砰、嗖、咚、哗、轰、咚咚（心跳）、沙沙",
    "japanese": "ドン、シュッ、バン、ザザ、ゴゴゴ、ドキドキ（心跳）、サラサラ",
    "english": "BANG, WHOOSH, THUD, SPLASH, BOOM, THUMP THUMP (heartbeat), RUSTLE",
    "korean": "쾅, 슉, 쿵, 철퍼덕, 콰광, 두근두근 (심장), 사각사각",
}


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

## 语言设置（极其重要，必须严格遵守！）
**目标语言：{language_hint}**

### 强制语言规则 ###
1. dialogue（对话）: 必须且只能使用{language_hint}
2. narration（旁白）: 必须且只能使用{language_hint}
3. sound_effects（音效）: 必须且只能使用{language_hint}
4. **严禁混用其他语言！即使原文是其他语言，也必须翻译为{language_hint}**

### 音效示例（{language_hint}）###
{sfx_examples}

## 要求
1. 为每个画格分配具体内容
2. 遵循视觉叙事原则（建立->发展->高潮->反应）
3. 利用画格大小表达重要性
4. 注意镜头变化的节奏感
5. 对话要简短有力（每句不超过12字）
6. 根据说话内容和情绪选择合适的气泡类型
7. 为动作场景添加适当的音效

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
      "content_description": "这个画格展示什么内容",
      "narrative_purpose": "叙事目的",
      "characters": ["出场角色"],
      "character_emotions": {{"角色名": "情绪"}},
      "composition": "构图方式",
      "camera_angle": "镜头角度",
      "dialogue": "对话内容（必须使用{language_hint}，可选，不超过12字）",
      "dialogue_speaker": "说话者",
      "dialogue_bubble_type": "normal|shout|whisper|thought|narration|electronic",
      "dialogue_position": "top-right|top-left|...",
      "dialogue_emotion": "说话时的情绪",
      "narration": "旁白（必须使用{language_hint}，可选，不超过20字）",
      "narration_position": "top|bottom",
      "sound_effects": ["音效文字（必须使用{language_hint}）"],
      "sound_effect_details": [
        {{
          "text": "音效文字（必须使用{language_hint}）",
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

**再次强调：所有dialogue、narration、sound_effects字段必须使用{language_hint}，禁止使用其他语言！**
"""


class SceneExpansionService:
    """
    场景展开服务

    将单个叙事场景展开为专业漫画分镜
    """

    def __init__(self, llm_service=None):
        """
        初始化服务

        Args:
            llm_service: LLM服务实例（用于智能分析）
        """
        self.llm_service = llm_service

    async def expand_scene(
        self,
        scene_id: int,
        scene_summary: str,
        scene_content: str,
        characters: List[str],
        previous_scene: Optional[str] = None,
        next_scene: Optional[str] = None,
        chapter_position: str = "middle",  # beginning/middle/climax/ending
        user_id: Optional[int] = None,
        dialogue_language: str = "chinese",  # 对话/音效语言
    ) -> SceneExpansion:
        """
        将场景展开为漫画分镜

        Args:
            scene_id: 场景ID
            scene_summary: 场景摘要
            scene_content: 场景原文内容
            characters: 出场角色列表
            previous_scene: 前一场景摘要
            next_scene: 后一场景摘要
            chapter_position: 在章节中的位置
            user_id: 用户ID
            dialogue_language: 对话/音效语言（chinese/japanese/english/korean）

        Returns:
            场景展开结果
        """
        logger.info(f"展开场景 {scene_id}: {scene_summary[:30]}...")

        # 步骤1：分析场景
        analysis = await self._analyze_scene(
            scene_content=scene_content,
            scene_summary=scene_summary,
            previous_scene=previous_scene,
            next_scene=next_scene,
            chapter_position=chapter_position,
            user_id=user_id,
        )

        # 步骤2：选择页面模板
        template = self._select_template(analysis)
        logger.info(f"选择模板: {template.name_zh}")

        # 步骤3：分配画格内容
        page_plan = await self._distribute_content(
            scene_content=scene_content,
            scene_summary=scene_summary,
            analysis=analysis,
            template=template,
            characters=characters,
            user_id=user_id,
            dialogue_language=dialogue_language,
        )

        # 步骤4：构建展开结果
        expansion = SceneExpansion(
            scene_id=scene_id,
            scene_summary=scene_summary,
            original_text=scene_content,
            pages=[page_plan],
            mood=self._parse_mood(analysis.get("mood", "calm")),
            importance=analysis.get("importance", "normal"),
        )

        logger.info(
            f"场景 {scene_id} 展开完成: "
            f"{len(expansion.pages)} 页, {expansion.get_total_panels()} 格"
        )

        return expansion

    async def expand_scenes_batch(
        self,
        scenes: List[Dict[str, Any]],
        user_id: Optional[int] = None,
    ) -> List[SceneExpansion]:
        """
        批量展开多个场景

        Args:
            scenes: 场景列表，每个包含 scene_id, summary, content, characters
            user_id: 用户ID

        Returns:
            场景展开结果列表
        """
        expansions = []

        for i, scene in enumerate(scenes):
            # 获取上下文
            previous_scene = scenes[i - 1].get("summary") if i > 0 else None
            next_scene = scenes[i + 1].get("summary") if i < len(scenes) - 1 else None

            # 判断章节位置
            if i == 0:
                position = "beginning"
            elif i == len(scenes) - 1:
                position = "ending"
            elif i >= len(scenes) * 0.7:
                position = "climax"
            else:
                position = "middle"

            expansion = await self.expand_scene(
                scene_id=scene.get("scene_id", i + 1),
                scene_summary=scene.get("summary", ""),
                scene_content=scene.get("content", scene.get("original_text", "")),
                characters=scene.get("characters", []),
                previous_scene=previous_scene,
                next_scene=next_scene,
                chapter_position=position,
                user_id=user_id,
            )

            expansions.append(expansion)

        return expansions

    async def _analyze_scene(
        self,
        scene_content: str,
        scene_summary: str,
        previous_scene: Optional[str],
        next_scene: Optional[str],
        chapter_position: str,
        user_id: Optional[int],
    ) -> Dict[str, Any]:
        """
        分析场景特性

        使用LLM分析场景的情感、重要性、关键时刻等
        """
        if self.llm_service:
            # 使用LLM分析
            prompt = SCENE_ANALYSIS_PROMPT.format(
                scene_content=scene_content[:2000],
                scene_summary=scene_summary,
                previous_scene=previous_scene or "（无）",
                next_scene=next_scene or "（无）",
                chapter_position=chapter_position,
            )

            try:
                from app.services.llm_wrappers import call_llm, LLMProfile

                response = await call_llm(
                    self.llm_service,
                    LLMProfile.ANALYTICAL,
                    system_prompt="你是专业的漫画分镜师，擅长分析叙事场景并转化为视觉表现。",
                    user_content=prompt,
                    user_id=user_id,
                )

                analysis = parse_llm_json_safe(response)
                if analysis:
                    return analysis

            except Exception as e:
                logger.warning(f"LLM场景分析失败: {e}，使用规则分析")

        # 回退到规则分析
        return self._analyze_scene_by_rules(
            scene_content, scene_summary, chapter_position
        )

    def _analyze_scene_by_rules(
        self,
        scene_content: str,
        scene_summary: str,
        chapter_position: str,
    ) -> Dict[str, Any]:
        """
        基于规则的场景分析（LLM不可用时的回退）
        """
        content_lower = scene_content.lower()
        summary_lower = scene_summary.lower()
        combined = content_lower + summary_lower

        # 情感检测
        mood = "calm"
        if any(word in combined for word in ["战斗", "打", "攻击", "冲", "fight", "attack"]):
            mood = "action"
        elif any(word in combined for word in ["紧张", "对峙", "威胁", "危险"]):
            mood = "tension"
        elif any(word in combined for word in ["哭", "泪", "悲伤", "痛苦", "感动"]):
            mood = "emotional"
        elif any(word in combined for word in ["笑", "搞笑", "有趣", "开心"]):
            mood = "comedy"
        elif any(word in combined for word in ["神秘", "奇怪", "疑惑", "秘密"]):
            mood = "mystery"
        elif any(word in combined for word in ["回忆", "过去", "曾经", "记得"]):
            mood = "flashback"
        elif any(word in combined for word in ["爱", "喜欢", "心动", "浪漫"]):
            mood = "romantic"
        elif any(word in combined for word in ["恐怖", "害怕", "阴森", "黑暗"]):
            mood = "horror"

        # 重要性判断
        importance = "normal"
        if chapter_position == "climax":
            importance = "high"
        elif chapter_position in ["beginning", "ending"]:
            importance = "normal"
        if any(word in combined for word in ["关键", "重要", "转折", "决定"]):
            importance = "high"

        # 对话检测
        has_dialogue = '"' in scene_content or '"' in scene_content or "说" in scene_content

        # 动作检测
        is_action = mood == "action" or any(
            word in combined for word in ["跑", "跳", "飞", "冲", "打"]
        )

        # 高潮检测
        is_climax = chapter_position == "climax" or importance == "critical"

        return {
            "mood": mood,
            "importance": importance,
            "has_dialogue": has_dialogue,
            "is_action": is_action,
            "is_climax": is_climax,
            "key_moments": [],
            "characters_present": [],
            "atmosphere": "",
            "pacing_suggestion": "fast" if is_action else "normal",
            "recommended_panel_count": 6 if is_action else 5,
        }

    def _select_template(self, analysis: Dict[str, Any]) -> PageTemplate:
        """
        根据分析结果选择页面模板
        """
        # 解析 mood，处理 LLM 可能返回的复合值如 "calm/dramatic"
        mood_str = analysis.get("mood", "calm")
        mood = self._parse_mood(mood_str)

        is_climax = analysis.get("is_climax", False)
        has_dialogue = analysis.get("has_dialogue", False)
        is_action = analysis.get("is_action", False)

        return recommend_template(
            mood=mood,
            is_climax=is_climax,
            has_dialogue=has_dialogue,
            is_action=is_action,
        )

    def _parse_mood(self, mood_str: str) -> SceneMood:
        """
        解析 mood 字符串，处理复合值和无效值
        """
        if not mood_str:
            return SceneMood.CALM

        # 处理复合值如 "calm/dramatic"
        candidates = mood_str.replace("/", ",").replace("|", ",").split(",")

        for candidate in candidates:
            candidate = candidate.strip().lower()
            try:
                return SceneMood(candidate)
            except ValueError:
                continue

        # 如果都无效，返回默认值
        return SceneMood.CALM

    async def _distribute_content(
        self,
        scene_content: str,
        scene_summary: str,
        analysis: Dict[str, Any],
        template: PageTemplate,
        characters: List[str],
        user_id: Optional[int],
        dialogue_language: str = "chinese",
    ) -> PagePlan:
        """
        将场景内容分配到画格中
        """
        if self.llm_service:
            # 使用LLM分配
            panel_slots_desc = self._format_panel_slots(template)
            key_moments = analysis.get("key_moments", [])

            # 获取语言相关信息
            language_hint = LANGUAGE_HINTS.get(dialogue_language, "中文")
            sfx_examples = SOUND_EFFECT_EXAMPLES.get(dialogue_language, SOUND_EFFECT_EXAMPLES["chinese"])

            prompt = PANEL_DISTRIBUTION_PROMPT.format(
                scene_content=scene_content[:2000],
                mood=analysis.get("mood", "calm"),
                key_moments=str(key_moments) if key_moments else "（自动识别）",
                characters=", ".join(characters) if characters else "（自动识别）",
                template_name=template.name_zh,
                template_description=template.description,
                panel_slots_description=panel_slots_desc,
                language_hint=language_hint,
                sfx_examples=sfx_examples,
            )

            try:
                from app.services.llm_wrappers import call_llm, LLMProfile

                response = await call_llm(
                    self.llm_service,
                    LLMProfile.MANGA,
                    system_prompt="你是专业的漫画分镜师，擅长将叙事内容转化为视觉画面。",
                    user_content=prompt,
                    user_id=user_id,
                )

                result = parse_llm_json_safe(response)
                if result and "panels" in result:
                    panels = self._parse_panel_contents(result["panels"], template)
                    return PagePlan(
                        page_number=1,
                        template=template,
                        panels=panels,
                        page_purpose=result.get("page_purpose", scene_summary),
                    )

            except Exception as e:
                logger.warning(f"LLM内容分配失败: {e}，使用规则分配")

        # 回退到规则分配
        return self._distribute_by_rules(
            scene_content, scene_summary, analysis, template, characters
        )

    def _format_panel_slots(self, template: PageTemplate) -> str:
        """格式化画格槽位描述"""
        lines = []
        for slot in template.panel_slots:
            size_desc = "大格" if slot.is_key_panel else "标准格"
            lines.append(
                f"- 槽位{slot.slot_id}: {size_desc}, "
                f"用途={slot.purpose.value}, "
                f"建议构图={slot.suggested_composition}, "
                f"建议角度={slot.suggested_angle}"
            )
        return "\n".join(lines)

    def _parse_panel_contents(
        self,
        panels_data: List[Dict[str, Any]],
        template: PageTemplate,
    ) -> List[PanelContent]:
        """解析LLM返回的画格内容"""
        panels = []
        template_slot_ids = {s.slot_id for s in template.panel_slots}

        for panel_data in panels_data:
            slot_id = panel_data.get("slot_id")
            if slot_id not in template_slot_ids:
                continue

            panel = PanelContent(
                slot_id=slot_id,
                content_description=panel_data.get("content_description", ""),
                narrative_purpose=panel_data.get("narrative_purpose", ""),
                characters=panel_data.get("characters", []),
                character_emotions=panel_data.get("character_emotions", {}),
                composition=panel_data.get("composition", "medium shot"),
                camera_angle=panel_data.get("camera_angle", "eye level"),
                # 文字元素 - 基础字段
                dialogue=panel_data.get("dialogue"),
                dialogue_speaker=panel_data.get("dialogue_speaker"),
                narration=panel_data.get("narration"),
                sound_effects=panel_data.get("sound_effects", []),
                # 文字元素 - 扩展字段（新增）
                dialogue_bubble_type=panel_data.get("dialogue_bubble_type", "normal"),
                dialogue_position=panel_data.get("dialogue_position", "top-right"),
                dialogue_emotion=panel_data.get("dialogue_emotion", ""),
                narration_position=panel_data.get("narration_position", "top"),
                sound_effect_details=panel_data.get("sound_effect_details", []),
                # 视觉指导
                key_visual_elements=panel_data.get("key_visual_elements", []),
                atmosphere=panel_data.get("atmosphere", ""),
                lighting=panel_data.get("lighting", ""),
            )
            panels.append(panel)

        # 确保所有槽位都有内容
        existing_ids = {p.slot_id for p in panels}
        for slot in template.panel_slots:
            if slot.slot_id not in existing_ids:
                panels.append(
                    PanelContent(
                        slot_id=slot.slot_id,
                        content_description="场景延续",
                        narrative_purpose=slot.purpose.value,
                        composition=slot.suggested_composition,
                        camera_angle=slot.suggested_angle,
                    )
                )

        # 按slot_id排序
        panels.sort(key=lambda p: p.slot_id)
        return panels

    def _distribute_by_rules(
        self,
        scene_content: str,
        scene_summary: str,
        analysis: Dict[str, Any],
        template: PageTemplate,
        characters: List[str],
    ) -> PagePlan:
        """
        基于规则的内容分配（LLM不可用时的回退）
        """
        panels = []

        for slot in template.panel_slots:
            # 根据画格用途生成内容
            content_desc, narrative_purpose = self._generate_panel_content_by_purpose(
                slot.purpose,
                scene_summary,
                characters,
            )

            panel = PanelContent(
                slot_id=slot.slot_id,
                content_description=content_desc,
                narrative_purpose=narrative_purpose,
                characters=characters[:2] if characters else [],
                composition=slot.suggested_composition,
                camera_angle=slot.suggested_angle,
                atmosphere=analysis.get("atmosphere", ""),
            )
            panels.append(panel)

        return PagePlan(
            page_number=1,
            template=template,
            panels=panels,
            page_purpose=scene_summary,
        )

    def _generate_panel_content_by_purpose(
        self,
        purpose: PanelPurpose,
        scene_summary: str,
        characters: List[str],
    ) -> Tuple[str, str]:
        """根据画格用途生成内容描述"""
        char_str = characters[0] if characters else "角色"

        content_map = {
            PanelPurpose.ESTABLISHING: (
                f"场景全景：{scene_summary[:20]}的环境",
                "建立场景环境和氛围"
            ),
            PanelPurpose.ACTION: (
                f"{char_str}的动作",
                "展示关键动作"
            ),
            PanelPurpose.REACTION: (
                f"{char_str}的反应表情",
                "展示角色对事件的反应"
            ),
            PanelPurpose.CLOSEUP: (
                f"{char_str}的面部特写",
                "聚焦角色情感"
            ),
            PanelPurpose.DETAIL: (
                "关键细节特写",
                "突出重要道具或细节"
            ),
            PanelPurpose.EMOTION: (
                f"{char_str}的情感表达",
                "深入展示角色内心"
            ),
            PanelPurpose.TRANSITION: (
                "过渡画面",
                "连接前后场景"
            ),
            PanelPurpose.EMPHASIS: (
                scene_summary[:30],
                "场景高潮或关键时刻"
            ),
        }

        return content_map.get(
            purpose,
            (scene_summary[:30], "叙事推进")
        )


# 便捷函数
async def expand_scene_to_manga(
    scene_id: int,
    scene_summary: str,
    scene_content: str,
    characters: List[str],
    llm_service=None,
    user_id: Optional[int] = None,
) -> SceneExpansion:
    """
    便捷函数：将场景展开为漫画分镜

    Args:
        scene_id: 场景ID
        scene_summary: 场景摘要
        scene_content: 场景内容
        characters: 角色列表
        llm_service: LLM服务
        user_id: 用户ID

    Returns:
        场景展开结果
    """
    service = SceneExpansionService(llm_service)
    return await service.expand_scene(
        scene_id=scene_id,
        scene_summary=scene_summary,
        scene_content=scene_content,
        characters=characters,
        user_id=user_id,
    )
