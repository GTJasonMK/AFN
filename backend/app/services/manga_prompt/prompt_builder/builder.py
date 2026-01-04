"""
提示词构建器

基于分镜设计结果生成最终的AI绘图提示词。
"""

import logging
from typing import Dict, List, Optional

from ..storyboard import StoryboardResult, PageStoryboard, PanelDesign
from ..extraction import ChapterInfo
from .models import PanelPrompt, PagePromptResult, MangaPromptResult

logger = logging.getLogger(__name__)


# 画格大小到宽高比的映射
SIZE_TO_ASPECT_RATIO = {
    "small": "4:3",
    "medium": "4:3",
    "large": "16:9",
    "half": "2:1",
    "full": "2:3",
    "spread": "4:3",
}

# 画格形状到宽高比的修正
SHAPE_ASPECT_RATIO_OVERRIDE = {
    "square": "1:1",
    "vertical": "3:4",
    "horizontal": "16:9",
}

# 风格前缀映射
STYLE_PREFIXES = {
    "manga": "manga style, black and white, screentone, Japanese comic,",
    "anime": "anime style, vibrant colors, Japanese animation,",
    "comic": "western comic style, bold lines, dynamic,",
    "webtoon": "webtoon style, vertical scroll, Korean comic,",
}

# 默认负面提示词
DEFAULT_NEGATIVE_PROMPT = (
    "text, watermark, signature, blurry, low quality, "
    "deformed, ugly, bad anatomy, extra limbs, "
    "realistic photo, 3d render"
)


class PromptBuilder:
    """
    提示词构建器

    将分镜设计转换为AI图像生成提示词
    """

    def __init__(
        self,
        style: str = "manga",
        character_profiles: Optional[Dict[str, str]] = None,
        dialogue_language: str = "chinese",
        character_portraits: Optional[Dict[str, str]] = None,
    ):
        """
        初始化构建器

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            character_profiles: 角色外观描述字典 {角色名: 外观描述}
            dialogue_language: 对话语言
            character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}
        """
        self.style = style
        self.character_profiles = character_profiles or {}
        self.dialogue_language = dialogue_language
        self.character_portraits = character_portraits or {}
        self.style_prefix = STYLE_PREFIXES.get(style, STYLE_PREFIXES["manga"])

    def build(
        self,
        storyboard: StoryboardResult,
        chapter_info: ChapterInfo,
        chapter_number: int = 1,
    ) -> MangaPromptResult:
        """
        构建完整的漫画提示词结果

        Args:
            storyboard: 分镜设计结果
            chapter_info: 章节信息
            chapter_number: 章节号

        Returns:
            MangaPromptResult: 完整提示词结果
        """
        pages = []
        total_panels = 0

        for page_storyboard in storyboard.pages:
            page_result = self._build_page_prompts(page_storyboard, chapter_info)
            pages.append(page_result)
            total_panels += len(page_result.panels)

        # 收集角色外观
        character_profiles = {}
        for name, char_info in chapter_info.characters.items():
            if char_info.appearance:
                character_profiles[name] = char_info.appearance

        return MangaPromptResult(
            chapter_number=chapter_number,
            style=self.style,
            pages=pages,
            total_pages=len(pages),
            total_panels=total_panels,
            character_profiles=character_profiles,
            dialogue_language=self.dialogue_language,
        )

    def _build_page_prompts(
        self,
        page: PageStoryboard,
        chapter_info: ChapterInfo,
    ) -> PagePromptResult:
        """构建单页的提示词"""
        panels = []

        for panel in page.panels:
            prompt = self._build_panel_prompt(
                panel=panel,
                page_number=page.page_number,
                chapter_info=chapter_info,
            )
            panels.append(prompt)

        return PagePromptResult(
            page_number=page.page_number,
            panels=panels,
            layout_description=page.layout_description,
            reading_flow=page.reading_flow,
        )

    def _build_panel_prompt(
        self,
        panel: PanelDesign,
        page_number: int,
        chapter_info: ChapterInfo,
    ) -> PanelPrompt:
        """构建单个画格的提示词"""
        # 确定宽高比
        aspect_ratio = self._get_aspect_ratio(panel)

        # 构建英文提示词
        prompt_en = self._build_english_prompt(panel, chapter_info)

        # 构建中文描述
        prompt_zh = self._build_chinese_description(panel)

        # 获取角色立绘路径
        reference_paths = self._get_reference_paths(panel.characters)

        # 转换对话和音效为字典格式
        dialogues = [d.to_dict() for d in panel.dialogues]
        sound_effects = [s.to_dict() for s in panel.sound_effects]

        return PanelPrompt(
            panel_id=f"page{page_number}_panel{panel.panel_id}",
            page_number=page_number,
            panel_number=panel.panel_id,
            size=panel.size.value,
            shape=panel.shape.value,
            shot_type=panel.shot_type.value,
            aspect_ratio=aspect_ratio,
            prompt_en=prompt_en,
            prompt_zh=prompt_zh,
            negative_prompt=DEFAULT_NEGATIVE_PROMPT,
            dialogues=dialogues,
            narration=panel.narration,
            sound_effects=sound_effects,
            characters=panel.characters,
            character_actions=panel.character_actions,
            character_expressions=panel.character_expressions,
            focus_point=panel.focus_point,
            lighting=panel.lighting,
            atmosphere=panel.atmosphere,
            background=panel.background,
            motion_lines=panel.motion_lines,
            impact_effects=panel.impact_effects,
            is_key_panel=panel.is_key_panel,
            reference_image_paths=reference_paths,
        )

    def _get_aspect_ratio(self, panel: PanelDesign) -> str:
        """获取画格的宽高比"""
        # 形状优先
        shape_value = panel.shape.value
        if shape_value in SHAPE_ASPECT_RATIO_OVERRIDE:
            return SHAPE_ASPECT_RATIO_OVERRIDE[shape_value]

        # 否则基于大小
        size_value = panel.size.value
        return SIZE_TO_ASPECT_RATIO.get(size_value, "4:3")

    def _build_english_prompt(
        self,
        panel: PanelDesign,
        chapter_info: ChapterInfo,
    ) -> str:
        """构建英文提示词"""
        parts = [self.style_prefix]

        # 优先使用LLM生成的英文描述
        if panel.visual_description_en:
            parts.append(panel.visual_description_en)
        else:
            # 回退：基于中文描述构建
            parts.append(f"scene depicting: {panel.visual_description[:100]}")

        # 添加镜头类型
        shot_descriptions = {
            "establishing": "wide establishing shot showing the environment,",
            "long": "long shot showing full figure and surroundings,",
            "medium": "medium shot showing upper body,",
            "close_up": "close-up shot focusing on face,",
            "extreme_close_up": "extreme close-up on eyes or details,",
            "over_shoulder": "over-the-shoulder shot,",
            "pov": "first-person point of view,",
            "bird_eye": "bird's eye view from above,",
            "worm_eye": "low angle looking up,",
        }
        shot_desc = shot_descriptions.get(panel.shot_type.value, "")
        if shot_desc:
            parts.append(shot_desc)

        # 添加角色描述
        for char_name in panel.characters[:2]:  # 最多2个角色
            char_info = chapter_info.characters.get(char_name)
            if char_info and char_info.appearance:
                parts.append(f"{char_name}: {char_info.appearance[:100]},")
            elif char_name in self.character_profiles:
                parts.append(f"{char_name}: {self.character_profiles[char_name][:100]},")

        # 添加角色表情
        for char_name, expression in panel.character_expressions.items():
            if expression:
                parts.append(f"{char_name} with {expression} expression,")

        # 添加角色动作
        for char_name, action in panel.character_actions.items():
            if action:
                parts.append(f"{char_name} {action},")

        # 添加氛围和光线
        if panel.atmosphere:
            parts.append(f"{panel.atmosphere} atmosphere,")
        if panel.lighting:
            parts.append(f"{panel.lighting} lighting,")

        # 添加背景
        if panel.background:
            parts.append(f"background: {panel.background},")

        # 添加视觉焦点
        if panel.focus_point:
            parts.append(f"focus on {panel.focus_point},")

        # 添加视觉效果
        if panel.motion_lines:
            parts.append("motion lines, speed lines,")
        if panel.impact_effects:
            parts.append("impact effect, action lines,")

        # 添加质量标签
        parts.append("high quality, detailed, masterpiece")

        return " ".join(parts)

    def _build_chinese_description(self, panel: PanelDesign) -> str:
        """构建中文描述"""
        parts = []

        # 镜头类型
        shot_names = {
            "establishing": "全景",
            "long": "远景",
            "medium": "中景",
            "close_up": "近景",
            "extreme_close_up": "特写",
            "over_shoulder": "过肩",
            "pov": "主观",
            "bird_eye": "俯视",
            "worm_eye": "仰视",
        }
        shot_name = shot_names.get(panel.shot_type.value, "中景")
        parts.append(f"[{shot_name}]")

        # 画面描述
        if panel.visual_description:
            parts.append(panel.visual_description)

        # 角色
        if panel.characters:
            parts.append(f"角色: {', '.join(panel.characters)}")

        # 焦点
        if panel.focus_point:
            parts.append(f"焦点: {panel.focus_point}")

        return " | ".join(parts)

    def _get_reference_paths(
        self,
        characters: List[str],
    ) -> Optional[List[str]]:
        """获取角色立绘路径"""
        if not characters or not self.character_portraits:
            return None

        paths = []
        for char in characters:
            if char in self.character_portraits:
                paths.append(self.character_portraits[char])

        return paths if paths else None


__all__ = [
    "PromptBuilder",
]
