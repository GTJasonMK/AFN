"""
提示词构建器

基于分镜设计结果生成最终的AI绘图提示词。
"""

import logging
from typing import Dict, List, Optional

from ..storyboard import StoryboardResult, PageStoryboard, PanelDesign
from ..extraction import ChapterInfo
from .models import PanelPrompt, PagePrompt, PagePromptResult, MangaPromptResult

logger = logging.getLogger(__name__)


# 风格模板（用户可基于这些模板自定义）
STYLE_TEMPLATES = {
    "manga": "漫画风格, 黑白漫画, 网点纸, 日式漫画, 精细线条, 高对比度",
    "anime": "动漫风格, 鲜艳色彩, 日本动画, 柔和阴影, 大眼睛",
    "comic": "美漫风格, 粗线条, 动感, 强烈阴影, 肌肉感",
    "webtoon": "条漫风格, 全彩, 韩国漫画, 柔和渐变, 现代感",
}

# 默认负面提示词（中文，自然语言）
DEFAULT_NEGATIVE_PROMPT = (
    "禁止：模糊低质量、变形扭曲、多余肢体、真实照片风格、3D渲染、水印签名"
)


def _resolve_panel_value(panel, attr: str, default):
    """读取画格字段，兼容枚举与直接字符串"""
    value = getattr(panel, attr, default)
    if value is None:
        return default
    return getattr(value, "value", value)


def _resolve_panel_int(panel, attr: str, default: int) -> int:
    """读取画格整数字段，兼容字符串与缺省值"""
    value = _resolve_panel_value(panel, attr, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_layout_template(panels: List) -> str:
    """构建布局模板名称（兼容不同面板对象）"""
    if not panels:
        return "empty"

    rows = {}
    for panel in panels:
        row_id = _resolve_panel_int(panel, "row_id", 1)
        rows[row_id] = rows.get(row_id, 0) + 1

    row_count = len(rows)
    panel_counts = [str(rows[r]) for r in sorted(rows.keys())]
    return f"{row_count}row_{'x'.join(panel_counts)}"


def build_panel_summary(panel) -> dict:
    """构建画格简要信息（兼容 PanelDesign/PanelPrompt）"""
    summary = {
        "panel_id": _resolve_panel_value(panel, "panel_id", ""),
        "row_id": _resolve_panel_int(panel, "row_id", 1),
        "row_span": _resolve_panel_int(panel, "row_span", 1),
        "width_ratio": _resolve_panel_value(panel, "width_ratio", "half"),
        "aspect_ratio": _resolve_panel_value(panel, "aspect_ratio", "4:3"),
    }

    shot_map = {"long": "远景", "medium": "中景", "close_up": "特写", "extreme_close_up": "超特写"}
    shot_raw = _resolve_panel_value(panel, "shot_type", "medium")
    summary["shot_type"] = shot_map.get(shot_raw, "中景")

    visual_text = getattr(panel, "visual_description", "") or getattr(panel, "prompt", "")
    summary["visual"] = visual_text[:100] if visual_text else ""

    characters = getattr(panel, "characters", None) or []
    summary["characters"] = characters[:3]

    dialogues_data = getattr(panel, "dialogues", None) or []
    if dialogues_data:
        dialogues = []
        for dialogue in dialogues_data[:2]:
            if isinstance(dialogue, dict):
                speaker = dialogue.get("speaker") or "角色"
                content = dialogue.get("content") or ""
                is_internal = dialogue.get("is_internal", False)
                bubble_type = dialogue.get("bubble_type") or "normal"
            else:
                speaker = dialogue.speaker if getattr(dialogue, "speaker", None) else "角色"
                content = getattr(dialogue, "content", "") or ""
                is_internal = getattr(dialogue, "is_internal", False)
                bubble_type = getattr(dialogue, "bubble_type", "normal")

            content = content[:30] if len(content) > 30 else content

            if is_internal or bubble_type == "thought":
                dialogues.append(f'{speaker}(想法): ({content})')
            elif bubble_type == "shout":
                dialogues.append(f'{speaker}(喊): "{content}"')
            elif bubble_type == "whisper":
                dialogues.append(f'{speaker}(低语): "{content}"')
            else:
                dialogues.append(f'{speaker}: "{content}"')
        summary["dialogues"] = dialogues

    narration = getattr(panel, "narration", "") or ""
    if narration:
        narration_text = narration[:50] if len(narration) > 50 else narration
        summary["narration"] = narration_text
        summary["narration_type"] = getattr(panel, "narration_type", "") or "scene"

    background = getattr(panel, "background", "") or ""
    if background:
        summary["background"] = background

    atmosphere = getattr(panel, "atmosphere", "") or ""
    if atmosphere:
        summary["atmosphere"] = atmosphere

    return summary


def build_panel_summaries(panels: List) -> List[dict]:
    """批量生成画格摘要列表"""
    return [build_panel_summary(panel) for panel in panels]


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
            style: 漫画风格，可以是预设key(manga/anime/comic/webtoon)或自定义描述字符串
            character_profiles: 角色外观描述字典 {角色名: 外观描述}
            character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}
        """
        self.style = style
        self.character_profiles = character_profiles or {}
        self.character_portraits = character_portraits or {}
        # 如果是预设key则使用模板，否则直接使用自定义字符串
        self.style_prefix = STYLE_TEMPLATES.get(style, style)

    def build(
        self,
        storyboard: StoryboardResult,
        chapter_info: ChapterInfo,
        chapter_number: int = 1,
        build_page_prompts: bool = True,
        dialogue_language: str = "chinese",
    ) -> MangaPromptResult:
        """
        构建完整的漫画提示词结果

        Args:
            storyboard: 分镜设计结果
            chapter_info: 章节信息
            chapter_number: 章节号
            build_page_prompts: 是否同时构建整页提示词（默认True）
            dialogue_language: 对话语言（chinese/japanese/english/korean）

        Returns:
            MangaPromptResult: 完整提示词结果
        """
        pages = []
        page_prompts = []
        total_panels = 0

        for page_storyboard in storyboard.pages:
            # 构建画格级提示词
            page_result = self._build_page_prompts(page_storyboard, chapter_info)
            pages.append(page_result)
            total_panels += len(page_result.panels)

            # 构建整页级提示词
            if build_page_prompts:
                page_prompt = self.build_page_prompt(page_storyboard, chapter_info)
                page_prompts.append(page_prompt)

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
            dialogue_language=dialogue_language,
            page_prompts=page_prompts,
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
        """
        构建中文提示词

        注意：visual_description 已经是 LLM 生成的完整画面描述，包含了场景、角色、
        动作、表情、背景、氛围等信息。这里只需要：
        1. 添加风格前缀（由用户选择）
        2. 使用 visual_description 作为主体
        3. 添加对话气泡/旁白的结构化描述（确保 AI 绘图模型知道要画气泡）
        4. 添加角色外观描述（用于角色一致性参考）
        5. 添加质量标签
        """
        parts = []

        # 1. 风格前缀
        parts.append(self.style_prefix)

        # 2. 画面描述（LLM 生成的完整描述）
        if panel.visual_description:
            parts.append(panel.visual_description)

        # 3. 对话气泡和旁白（结构化描述，确保 AI 知道要画气泡）
        has_bubbles = False

        # 对话和想法内容 - 区分气泡类型
        dialogue_entries = []  # 普通对话
        thought_entries = []   # 内心想法
        shout_entries = []     # 喊叫
        whisper_entries = []   # 低语

        for bubble in panel.dialogues:
            content = bubble.content.strip()
            if not content:
                continue
            speaker = bubble.speaker.strip() if bubble.speaker else ""
            label = f"{speaker}: {content}" if speaker else content

            # 根据类型分类
            if bubble.is_internal or bubble.bubble_type == "thought":
                thought_entries.append(label)
            elif bubble.bubble_type == "shout":
                shout_entries.append(label)
            elif bubble.bubble_type == "whisper":
                whisper_entries.append(label)
            else:
                dialogue_entries.append(label)

        # 添加不同类型的气泡描述
        if thought_entries:
            thought_text = " | ".join(thought_entries[:2])
            parts.append(f'想法气泡(云朵状): "{thought_text}"')
            has_bubbles = True
        if dialogue_entries:
            dialogue_text = " | ".join(dialogue_entries[:2])
            parts.append(f'对话气泡: "{dialogue_text}"')
            has_bubbles = True
        if shout_entries:
            shout_text = " | ".join(shout_entries[:2])
            parts.append(f'喊叫气泡(锯齿状): "{shout_text}"')
            has_bubbles = True
        if whisper_entries:
            whisper_text = " | ".join(whisper_entries[:2])
            parts.append(f'低语气泡(虚线): "{whisper_text}"')
            has_bubbles = True

        # 旁白框（方框样式，与对话气泡不同）
        if panel.narration:
            narration_text = panel.narration[:80] if len(panel.narration) > 80 else panel.narration
            # 根据旁白类型选择不同描述
            narration_type_map = {
                "scene": "场景旁白框",
                "time": "时间旁白框",
                "inner": "内心旁白框",
                "exposition": "说明旁白框",
            }
            narration_label = narration_type_map.get(panel.narration_type, "旁白框")
            parts.append(f'{narration_label}(方框): "{narration_text}"')
            has_bubbles = True

        # 4. 角色外观描述（用于角色一致性参考，只添加一次）
        for char_name in panel.characters[:3]:
            char_info = chapter_info.characters.get(char_name)
            if char_info and char_info.appearance:
                parts.append(f"{char_name}: {char_info.appearance[:150]}")
            elif char_name in self.character_profiles:
                parts.append(f"{char_name}: {self.character_profiles[char_name][:150]}")

        # 5. 质量标签
        if has_bubbles:
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

    # ==================== 页面级提示词构建方法 ====================

    def build_page_prompt(
        self,
        page: PageStoryboard,
        chapter_info: ChapterInfo,
    ) -> PagePrompt:
        """
        构建整页漫画的提示词

        将页面的布局结构和所有panel内容整合为一个AI可理解的prompt，
        用于生成带分格布局的整页漫画图片。

        Args:
            page: 页面分镜设计
            chapter_info: 章节信息

        Returns:
            PagePrompt: 整页提示词结果
        """
        # 1. 分析页面布局，生成布局模板和描述
        layout_template, layout_desc = self._analyze_page_layout(page)

        # 2. 为每个panel生成完整提示词
        panel_prompts = []
        all_characters = set()

        for panel in page.panels:
            # 复用现有方法生成panel提示词
            panel_prompt = self._build_panel_prompt(panel, page.page_number, chapter_info)
            panel_prompts.append(panel_prompt)

            # 收集所有角色
            all_characters.update(panel.characters)

        # 生成panel简要描述（用于整页prompt）
        panel_summaries = build_panel_summaries(page.panels)

        # 3. 组合成整页提示词
        full_prompt = self._compose_full_page_prompt(
            layout_desc=layout_desc,
            panel_summaries=panel_summaries,
            page=page,
        )

        # 4. 获取所有角色的立绘路径
        reference_paths = self._get_reference_paths(list(all_characters))

        return PagePrompt(
            page_number=page.page_number,
            layout_template=layout_template,
            layout_description=layout_desc,
            panel_summaries=panel_summaries,
            full_page_prompt=full_prompt,
            negative_prompt=self._get_page_negative_prompt(),
            aspect_ratio="3:4",  # 标准漫画页面比例
            panels=panel_prompts,
            reference_image_paths=reference_paths,
        )

    def _analyze_page_layout(self, page: PageStoryboard) -> tuple:
        """
        分析页面布局，返回(模板名称, 布局描述)

        Args:
            page: 页面分镜设计

        Returns:
            (layout_template, layout_description)
        """
        panels = page.panels
        if not panels:
            return "empty", "Empty page"

        # 按 row_id 分组
        rows = {}
        for p in panels:
            rid = p.row_id
            if rid not in rows:
                rows[rid] = []
            rows[rid].append(p)

        row_count = len(rows)

        # 生成布局描述
        desc_parts = [
            f"漫画页面布局, {row_count}行结构, 黑色画格边框, 画格间留白{page.gutter_horizontal}px"
        ]

        for row_id in sorted(rows.keys()):
            row_panels = rows[row_id]
            panel_descs = []
            for p in row_panels:
                width_map = {
                    "full": "100%",
                    "two_thirds": "2/3",
                    "half": "1/2",
                    "third": "1/3"
                }
                width_key = _resolve_panel_value(p, "width_ratio", "half")
                width = width_map.get(width_key, "1/2")
                ratio = _resolve_panel_value(p, "aspect_ratio", "4:3")
                span = f"跨{p.row_span}行" if p.row_span > 1 else ""
                panel_descs.append(f"画格({width}, {ratio}{span})")
            desc_parts.append(f"第{row_id}行: {' + '.join(panel_descs)}")

        # 生成模板名称 (如 "3row_1x2x1")
        template_name = build_layout_template(panels)

        return template_name, "\n".join(desc_parts)

    def _build_panel_summary_for_page(
        self,
        panel: PanelDesign,
        chapter_info: ChapterInfo,
    ) -> dict:
        """
        为整页prompt构建单个panel的简要描述

        Args:
            panel: 画格分镜设计
            chapter_info: 章节信息

        Returns:
            dict: panel简要信息
        """
        return build_panel_summary(panel)

    def _compose_full_page_prompt(
        self,
        layout_desc: str,
        panel_summaries: List[dict],
        page: PageStoryboard,
    ) -> str:
        """
        组合成完整的页面提示词

        Args:
            layout_desc: 布局描述
            panel_summaries: 所有panel的简要信息
            page: 页面分镜设计

        Returns:
            str: 完整的页面级提示词
        """
        parts = []

        # 风格前缀
        parts.append(f"{self.style_prefix} 专业漫画页面, 完整分格布局, 带画格边框")

        # 布局描述
        parts.append(f"\n[页面结构]\n{layout_desc}")

        # 每个画格的内容
        parts.append("\n[画格内容]")
        for i, summary in enumerate(panel_summaries, 1):
            row_id = summary.get('row_id', 1)
            width = summary.get('width_ratio', 'half')
            ratio = summary.get('aspect_ratio', '4:3')
            shot = summary.get('shot_type', '中景')
            visual = summary.get('visual', '')

            panel_desc = f"\n画格{i} (第{row_id}行, {width}, {ratio}):"
            panel_desc += f"\n  {shot}, {visual}" if visual else f"\n  {shot}"

            # 角色
            characters = summary.get('characters', [])
            if characters:
                panel_desc += f"\n  角色: {', '.join(characters)}"

            # 对话
            dialogues = summary.get('dialogues', [])
            for d in dialogues:
                panel_desc += f"\n  对话气泡: {d}"

            # 旁白（方框样式）
            narration = summary.get('narration', '')
            if narration:
                narration_type = summary.get('narration_type', 'scene')
                type_label = {
                    "scene": "场景",
                    "time": "时间",
                    "inner": "内心",
                    "exposition": "说明",
                }.get(narration_type, "")
                panel_desc += f"\n  旁白框({type_label}): \"{narration}\""

            # 背景
            background = summary.get('background', '')
            if background:
                panel_desc += f"\n  背景: {background}"

            # 氛围
            atmosphere = summary.get('atmosphere', '')
            if atmosphere:
                panel_desc += f"\n  氛围: {atmosphere}"

            parts.append(panel_desc)

        # 必须包含的元素
        parts.append("\n[必须包含]")
        parts.append("画格边框, 画格间白色间隙, 对话气泡含文字, 专业漫画质量, 高清细节")

        return "\n".join(parts)

    def _get_page_negative_prompt(self) -> str:
        """获取页面级负面提示词"""
        return (
            "禁止：模糊低质量、变形扭曲、多余肢体、"
            "画格间黑色间隙、内容被裁剪截断、对话气泡不完整、"
            "真实照片风格、3D渲染、水印签名"
        )


__all__ = [
    "PromptBuilder",
    "build_layout_template",
    "build_panel_summary",
    "build_panel_summaries",
]
