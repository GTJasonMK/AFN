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


# 风格前缀映射（中文）
STYLE_PREFIXES = {
    "manga": "漫画风格, 黑白漫画, 网点纸, 日式漫画,",
    "anime": "动漫风格, 鲜艳色彩, 日本动画,",
    "comic": "美漫风格, 粗线条, 动感,",
    "webtoon": "条漫风格, 竖向滚动, 韩国漫画,",
}

# 默认负面提示词（中文）
DEFAULT_NEGATIVE_PROMPT = (
    "水印, 签名, 模糊, 低质量, "
    "变形, 丑陋, 解剖错误, 多余肢体, "
    "真实照片, 3D渲染"
)


class PromptBuilder:
    """
    提示词构建器

    将分镜设计转换为AI图像生成提示词（中文）
    """

    def __init__(
        self,
        style: str = "manga",
        character_profiles: Optional[Dict[str, str]] = None,
        character_portraits: Optional[Dict[str, str]] = None,
    ):
        """
        初始化构建器

        Args:
            style: 漫画风格 (manga/anime/comic/webtoon)
            character_profiles: 角色外观描述字典 {角色名: 外观描述}
            character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}
        """
        self.style = style
        self.character_profiles = character_profiles or {}
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
            dialogue_language="chinese",
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
            gutter_horizontal=page.gutter_horizontal,
            gutter_vertical=page.gutter_vertical,
        )

    def _build_panel_prompt(
        self,
        panel: PanelDesign,
        page_number: int,
        chapter_info: ChapterInfo,
    ) -> PanelPrompt:
        """构建单个画格的提示词"""
        # 构建中文提示词
        prompt = self._build_prompt(panel, chapter_info)

        # 获取角色立绘路径
        reference_paths = self._get_reference_paths(panel.characters)

        # 转换对话为字典格式
        dialogues = [d.to_dict() for d in panel.dialogues]

        return PanelPrompt(
            panel_id=f"page{page_number}_panel{panel.panel_id}",
            page_number=page_number,
            panel_number=panel.panel_id,
            shape=panel.shape.value,
            shot_type=panel.shot_type.value,
            row_id=panel.row_id,
            row_span=panel.row_span,
            width_ratio=panel.width_ratio.value,
            aspect_ratio=panel.aspect_ratio.value,
            prompt=prompt,
            negative_prompt=DEFAULT_NEGATIVE_PROMPT,
            dialogues=dialogues,
            characters=panel.characters,
            reference_image_paths=reference_paths,
        )

    def _build_prompt(
        self,
        panel: PanelDesign,
        chapter_info: ChapterInfo,
    ) -> str:
        """构建中文提示词"""
        parts = [self.style_prefix]

        # 镜头类型
        shot_names = {
            "long": "远景镜头, 展示全身和环境,",
            "medium": "中景镜头, 展示上半身,",
            "close_up": "近景特写, 聚焦面部,",
        }
        shot_desc = shot_names.get(panel.shot_type.value, "中景镜头,")
        parts.append(shot_desc)

        # 画面描述
        if panel.visual_description:
            parts.append(panel.visual_description)

        # 背景/场景
        if panel.background:
            parts.append(f"背景: {panel.background},")

        # 氛围
        if panel.atmosphere:
            parts.append(f"{panel.atmosphere}氛围,")

        # 光线
        if panel.lighting:
            parts.append(f"{panel.lighting}光线,")

        # 角色描述（最多3个角色）
        for char_name in panel.characters[:3]:
            char_info = chapter_info.characters.get(char_name)
            if char_info and char_info.appearance:
                parts.append(f"{char_name}: {char_info.appearance[:200]},")
            elif char_name in self.character_profiles:
                parts.append(f"{char_name}: {self.character_profiles[char_name][:200]},")

        # 角色动作
        for char_name, action in panel.character_actions.items():
            if action:
                parts.append(f"{char_name}{action},")

        # 角色表情
        for char_name, expression in panel.character_expressions.items():
            if expression:
                parts.append(f"{char_name}{expression}表情,")

        # 对话内容
        dialogue_entries = []
        for bubble in panel.dialogues:
            content = bubble.content.strip()
            if not content:
                continue
            speaker = bubble.speaker.strip() if bubble.speaker else ""
            label = f"{speaker}: {content}" if speaker else content
            dialogue_entries.append(label)
        if dialogue_entries:
            dialogue_text = " | ".join(dialogue_entries[:3])
            parts.append(f'对话气泡: "{dialogue_text}"')

        # 质量标签（只有有对话时才添加对话气泡关键词）
        if dialogue_entries:
            parts.append("漫画分格, 对话气泡, 高质量, 精细, 杰作")
        else:
            parts.append("漫画分格, 高质量, 精细, 杰作")

        return " ".join(parts)

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
