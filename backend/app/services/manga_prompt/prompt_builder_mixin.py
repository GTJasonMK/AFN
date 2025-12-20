"""
提示词构建Mixin

提供LLM提示词构建相关的方法。
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING

from .schemas import MangaStyle, DialogueLanguage

if TYPE_CHECKING:
    from .layout_schemas import LayoutGenerationResult

logger = logging.getLogger(__name__)


class PromptBuilderMixin:
    """提示词构建相关方法的Mixin"""

    # 需要被主类提供的属性和方法
    prompt_service: Any
    layout_service: Any
    _truncate_content: Any
    CONTENT_LIMIT_FULL_PROMPT: int

    async def _build_prompts_with_layout(
        self,
        content: str,
        character_profiles: Dict[str, str],
        style: MangaStyle,
        scene_summaries: List[Dict[str, Any]],
        layout_result: "LayoutGenerationResult",
        dialogue_language: DialogueLanguage = DialogueLanguage.CHINESE,
        include_dialogue: bool = True,
        include_sound_effects: bool = True,
    ) -> tuple[str, str]:
        """
        构建包含排版信息的LLM提示词

        Args:
            content: 章节内容
            character_profiles: 角色外观描述
            style: 漫画风格
            scene_summaries: 场景概要
            layout_result: 排版结果
            dialogue_language: 对话语言
            include_dialogue: 是否包含对话气泡
            include_sound_effects: 是否包含音效文字

        Returns:
            (system_prompt, user_prompt)
        """
        # 使用统一的内容截断方法
        content = self._truncate_content(content, self.CONTENT_LIMIT_FULL_PROMPT)

        # 从提示词服务获取模板
        if self.prompt_service:
            template = await self.prompt_service.get_prompt("manga_prompt")
        else:
            template = self._get_default_template()

        system_prompt = template

        # 构建角色信息
        char_info = ""
        for name, appearance in character_profiles.items():
            if appearance:
                char_info += f"- {name}: {appearance}\n"
            else:
                char_info += f"- {name}: (需要你生成外观描述)\n"

        # 风格映射（强调线稿风格，避免厚涂/塑料感）
        style_map = {
            MangaStyle.MANGA: "Japanese manga style, clean bold outlines, ink drawing, screentone shading, black and white, high contrast, pen and ink illustration",
            MangaStyle.ANIME: "Anime style, clean line art, cel shading, flat colors, vibrant, expressive eyes",
            MangaStyle.COMIC: "Western comic book style, strong black outlines, flat colors, graphic novel art, bold shadows",
            MangaStyle.WEBTOON: "Korean webtoon style, clean digital lines, soft cel shading, minimal rendering, vertical scroll format",
        }

        # 语言映射
        language_map = {
            DialogueLanguage.CHINESE: "chinese",
            DialogueLanguage.JAPANESE: "japanese",
            DialogueLanguage.ENGLISH: "english",
            DialogueLanguage.KOREAN: "korean",
            DialogueLanguage.NONE: "none",
        }
        dialogue_lang = language_map.get(dialogue_language, "chinese")

        # 构建排版指导信息
        layout_guide = self._build_layout_guide(scene_summaries, layout_result)

        # 构建对话和音效指导
        dialogue_guide = self._build_dialogue_guide(
            dialogue_language=dialogue_lang,
            include_dialogue=include_dialogue,
            include_sound_effects=include_sound_effects,
        )

        user_prompt = f"""请为以下章节内容生成漫画场景的文生图提示词。

## 章节内容
{content}

## 角色信息
{char_info if char_info else "(无已知角色信息，请根据内容自行识别和描述)"}

## 目标风格
{style_map.get(style, style_map[MangaStyle.MANGA])}

## 排版指导
{layout_guide}

## 对话和文字设置
{dialogue_guide}

## 输出要求
请严格按照JSON格式输出，包含character_profiles、style_guide和scenes数组。
每个场景的composition必须与排版指导中的建议一致。
每个场景必须包含dialogues（对话气泡列表）、narration（旁白）、sound_effects（音效列表）字段。
"""

        return system_prompt, user_prompt

    def _build_dialogue_guide(
        self,
        dialogue_language: str,
        include_dialogue: bool,
        include_sound_effects: bool,
    ) -> str:
        """
        构建对话和音效指导文本

        Args:
            dialogue_language: 对话语言
            include_dialogue: 是否包含对话
            include_sound_effects: 是否包含音效

        Returns:
            对话指导文本
        """
        guide_lines = []

        # 对话设置
        if include_dialogue and dialogue_language != "none":
            guide_lines.append(f"- 对话语言: {dialogue_language}")
            guide_lines.append("- 请从原文中提取角色对话，生成对话气泡")
            guide_lines.append(
                "- 对话气泡类型: normal(普通)/shout(大喊)/whisper(低语)/"
                "thought(内心独白)/narration(旁白)/electronic(电子声音)"
            )
            guide_lines.append(
                "- 气泡位置: top-left/top-center/top-right/middle-left/"
                "middle-right/bottom-left/bottom-center/bottom-right"
            )
            guide_lines.append("- 对话内容要简短（控制在15字以内）")

            # 语言特定提示
            lang_hints = {
                "chinese": "对话使用中文，如「你好」「怎么回事？」",
                "japanese": "对话使用日文，如「こんにちは」「何だと？」",
                "english": "对话使用英文，如 \"Hello\" \"What's going on?\"",
                "korean": "对话使用韩文，如 \"안녕하세요\" \"무슨 일이야?\"",
            }
            if dialogue_language in lang_hints:
                guide_lines.append(f"- {lang_hints[dialogue_language]}")
        else:
            guide_lines.append("- 不需要生成对话气泡，dialogues数组留空")

        # 音效设置
        if include_sound_effects:
            guide_lines.append("- 请根据场景动作生成音效文字")
            guide_lines.append(
                "- 音效类型: action(动作)/impact(撞击)/ambient(环境)/"
                "emotional(情感)/vocal(人声)"
            )
            guide_lines.append("- 音效强度: small(小)/medium(中)/large(大)")
            guide_lines.append("- 音效文字要简短（控制在4字以内）")

            # 语言特定音效示例
            sfx_hints = {
                "chinese": "如：砰、嗖、咚咚、哗啦",
                "japanese": "如：ドン、シュッ、ドキドキ、ザァァ",
                "english": "如：BANG、SWOOSH、THUMP、SPLASH",
                "korean": "如：쾅、휙、두근두근、철썩",
            }
            if dialogue_language in sfx_hints:
                guide_lines.append(
                    f"- 音效示例（{dialogue_language}）: {sfx_hints[dialogue_language]}"
                )
        else:
            guide_lines.append("- 不需要生成音效文字，sound_effects数组留空")

        return "\n".join(guide_lines)

    def _build_layout_guide(
        self,
        scene_summaries: List[Dict[str, Any]],
        layout_result: Optional["LayoutGenerationResult"],
    ) -> str:
        """构建排版指导文本"""
        if not layout_result or not layout_result.success:
            return "（排版自动分配，请根据场景重要性自行决定构图）"

        layout = layout_result.layout
        guide_lines = []

        guide_lines.append(f"排版类型: {layout.layout_type.value}")
        guide_lines.append(f"总页数: {layout.total_pages}")
        guide_lines.append(f"总格数: {layout.total_panels}")
        guide_lines.append("")
        guide_lines.append("各场景排版要求：")

        for page in layout.pages:
            for panel in page.panels:
                scene_id = panel.scene_id
                importance = panel.importance.value
                composition = panel.composition.value

                # 根据格子尺寸推荐构图
                aspect_ratio = self.layout_service.get_panel_aspect_ratio(
                    layout, scene_id
                )

                guide_lines.append(
                    f"- 场景{scene_id}: 页{page.page_number}, "
                    f"重要性={importance}, 构图={composition}, "
                    f"推荐比例={aspect_ratio}"
                )

        return "\n".join(guide_lines)

    async def _build_prompts(
        self,
        content: str,
        character_profiles: Dict[str, str],
        style: MangaStyle,
        scene_count: Optional[int],
    ) -> tuple[str, str]:
        """
        构建LLM提示词（不含排版信息的简化版本）

        Args:
            content: 章节内容
            character_profiles: 角色外观描述
            style: 漫画风格
            scene_count: 目标场景数，为None时由LLM自动决定

        Returns:
            (system_prompt, user_prompt)
        """
        # 使用统一的内容截断方法
        content = self._truncate_content(content, self.CONTENT_LIMIT_FULL_PROMPT)

        # 从提示词服务获取模板
        if self.prompt_service:
            template = await self.prompt_service.get_prompt("manga_prompt")
        else:
            template = self._get_default_template()

        system_prompt = template

        # 构建角色信息
        char_info = ""
        for name, appearance in character_profiles.items():
            if appearance:
                char_info += f"- {name}: {appearance}\n"
            else:
                char_info += f"- {name}: (需要你生成外观描述)\n"

        # 风格映射（强调线稿风格，避免厚涂/塑料感）
        style_map = {
            MangaStyle.MANGA: "Japanese manga style, clean bold outlines, ink drawing, screentone shading, black and white, high contrast, pen and ink illustration",
            MangaStyle.ANIME: "Anime style, clean line art, cel shading, flat colors, vibrant, expressive eyes",
            MangaStyle.COMIC: "Western comic book style, strong black outlines, flat colors, graphic novel art, bold shadows",
            MangaStyle.WEBTOON: "Korean webtoon style, clean digital lines, soft cel shading, minimal rendering, vertical scroll format",
        }

        # 根据是否指定场景数构建不同的提示
        if scene_count is not None:
            scene_instruction = (
                f"请将以下小说章节内容转化为 {scene_count} 个漫画场景的文生图提示词。"
            )
        else:
            scene_instruction = """请将以下小说章节内容转化为漫画场景的文生图提示词。
场景数量由你根据章节内容的长度、情节复杂度和关键画面数量自行决定（通常在5-15个之间）。
选择能够完整呈现故事、且每个场景都有视觉意义的关键画面。"""

        user_prompt = f"""{scene_instruction}

## 章节内容
{content}

## 角色信息
{char_info if char_info else "(无已知角色信息，请根据内容自行识别和描述)"}

## 目标风格
{style_map.get(style, style_map[MangaStyle.MANGA])}

## 输出要求
请严格按照JSON格式输出，包含character_profiles、style_guide和scenes数组。
"""

        return system_prompt, user_prompt

    def _get_default_template(self) -> str:
        """获取默认提示词模板"""
        return """# 角色
你是漫画分镜师和AI提示词工程师。

# 任务
将小说内容转化为漫画场景的文生图提示词。

# 输出要求
直接输出JSON，不要有任何其他文字。prompt_en必须是英文，限制在100词以内。

```json
{
  "character_profiles": {"角色名": "英文外观描述(50词内)"},
  "style_guide": "manga style",
  "scenes": [
    {
      "scene_id": 1,
      "scene_summary": "中文简述(20字内)",
      "characters": ["角色名"],
      "prompt_en": "英文提示词(100词内)",
      "composition": "medium shot",
      "emotion": "情感"
    }
  ]
}
```

# 重要
1. prompt_en必须是英文
2. 不要在提示词中包含对话文字
3. 每个场景限制在100词以内"""
