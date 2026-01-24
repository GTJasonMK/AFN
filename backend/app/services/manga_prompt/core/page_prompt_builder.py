"""
整页提示词构建器

为整页图片生成构建提示词，整合页面内所有画格的信息。
"""

from typing import Dict, List, Optional, Any

from ..prompt_builder.builder import build_layout_template, build_panel_summaries


def build_page_prompt_for_generation(
    page: Any,
    chapter_info: Any,
    style: str = "manga",
    character_portraits: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    为整页图片生成构建提示词

    Args:
        page: PagePrompt 对象，包含页面的所有画格信息
        chapter_info: ChapterInfo 对象，包含角色和场景信息
        style: 漫画风格
        character_portraits: 角色立绘路径字典

    Returns:
        包含 full_page_prompt, negative_prompt, aspect_ratio, reference_image_paths 的字典
    """
    character_portraits = character_portraits or {}

    panels = page.panels if hasattr(page, 'panels') else []

    # 构建布局模板名，如 "3row_1x2x1"
    layout_template = build_layout_template(panels)
    if layout_template == "empty":
        layout_template = "1row_1"

    # 构建提示词
    lines = []

    # 基础风格描述（支持预设key或自定义字符串）
    style_templates = {
        "manga": "manga style, professional manga page, black and white manga, panel layout",
        "anime": "anime style, professional anime page, colorful anime, panel layout",
        "comic": "comic book style, professional comic page, western comic, panel layout",
        "webtoon": "webtoon style, vertical scroll comic, korean webtoon, full color",
    }
    # 如果是预设key则使用模板，否则直接使用自定义字符串
    style_desc = style_templates.get(style, style)
    lines.append(style_desc)
    lines.append("")

    # 页面结构
    page_number = page.page_number if hasattr(page, 'page_number') else 1
    mood = page.mood if hasattr(page, 'mood') else ""
    layout_description = page.layout_description if hasattr(page, 'layout_description') else ""

    if mood:
        lines.append(f"[Page Mood: {mood}]")

    if layout_description:
        lines.append(f"[Layout: {layout_description}]")
    else:
        lines.append(f"[Layout Template: {layout_template}]")

    lines.append("")
    lines.append("[Panel Contents]")

    # 各画格内容
    reference_image_paths = []
    for i, panel in enumerate(panels, 1):
        row_id = panel.row_id if hasattr(panel, 'row_id') else 1
        width_ratio = panel.width_ratio if hasattr(panel, 'width_ratio') else "half"
        aspect_ratio = panel.aspect_ratio if hasattr(panel, 'aspect_ratio') else "1:1"
        prompt = panel.prompt if hasattr(panel, 'prompt') else ""

        # 画格位置和尺寸
        panel_line = f"Panel {i} (Row {row_id}, {width_ratio}, {aspect_ratio}):"
        lines.append(panel_line)

        # 画格内容描述
        if prompt:
            # 截取前150字符
            short_prompt = prompt[:150] + '...' if len(prompt) > 150 else prompt
            lines.append(f"  {short_prompt}")

        # 对话/旁白
        dialogues = panel.dialogues if hasattr(panel, 'dialogues') else []
        for dialogue in dialogues[:2]:  # 最多2条对话
            if isinstance(dialogue, dict):
                content = dialogue.get('content', '')[:50]
                speaker = dialogue.get('speaker', '')
                if content:
                    lines.append(f"  [Dialogue ({speaker}): \"{content}...\"]" if len(content) >= 50 else f"  [Dialogue ({speaker}): \"{content}\"]")

        narration = panel.narration if hasattr(panel, 'narration') else ""
        if narration:
            lines.append(f"  [Narration: \"{narration[:50]}...\"]" if len(narration) > 50 else f"  [Narration: \"{narration}\"]")

        # 收集角色立绘
        characters = panel.characters if hasattr(panel, 'characters') else []
        for char_name in characters:
            if char_name in character_portraits:
                path = character_portraits[char_name]
                if path and path not in reference_image_paths:
                    reference_image_paths.append(path)

        # 也检查 reference_image_paths 字段
        panel_refs = panel.reference_image_paths if hasattr(panel, 'reference_image_paths') else []
        for path in panel_refs:
            if path and path not in reference_image_paths:
                reference_image_paths.append(path)

        lines.append("")

    # 必须包含的元素
    lines.append("[Required Elements]")
    lines.append("- Clear panel borders with black lines")
    lines.append("- White gutters between panels")
    lines.append("- Speech bubbles with text (if dialogue exists)")
    lines.append("- Manga-style visual flow")

    full_page_prompt = "\n".join(lines)

    panel_summaries = build_panel_summaries(panels)

    # 负面提示词（中文）
    negative_prompt = (
        "禁止：模糊低质量、变形扭曲、多余肢体、"
        "画格间黑色间隙、内容被裁剪、水印签名"
    )

    return {
        "full_page_prompt": full_page_prompt,
        "negative_prompt": negative_prompt,
        "aspect_ratio": "3:4",  # 漫画页标准比例
        "reference_image_paths": reference_image_paths,
        "layout_template": layout_template,
        "layout_description": layout_description,
        "panel_summaries": panel_summaries,
    }
