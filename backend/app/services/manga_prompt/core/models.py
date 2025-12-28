"""
漫画提示词数据结构

包含漫画风格、生成结果等核心数据结构。
"""

from datetime import datetime
from typing import List, Dict, Any

from ..page_templates import SceneExpansion
from ..panel_prompt import PanelPrompt


class MangaStyle:
    """漫画风格"""
    MANGA = "manga"
    ANIME = "anime"
    COMIC = "comic"
    WEBTOON = "webtoon"


class MangaGenerationResult:
    """
    漫画生成结果

    包含完整的漫画分镜数据
    """

    def __init__(
        self,
        chapter_number: int,
        style: str,
        scenes: List[SceneExpansion],
        panel_prompts: List[PanelPrompt],
        character_profiles: Dict[str, str],
        dialogue_language: str = "chinese",  # 对话/音效语言
    ):
        self.chapter_number = chapter_number
        self.style = style
        self.scenes = scenes
        self.panel_prompts = panel_prompts
        self.character_profiles = character_profiles
        self.dialogue_language = dialogue_language
        self.created_at = datetime.now()

    def get_total_pages(self) -> int:
        """获取总页数"""
        return sum(len(s.pages) for s in self.scenes)

    def get_total_panels(self) -> int:
        """获取总画格数"""
        return len(self.panel_prompts)

    def get_panels_by_scene(self, scene_id: int) -> List[PanelPrompt]:
        """获取指定场景的画格"""
        return [p for p in self.panel_prompts if p.scene_id == scene_id]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于API响应和存储）"""
        return {
            "chapter_number": self.chapter_number,
            "style": self.style,
            "dialogue_language": self.dialogue_language,  # 添加语言字段
            "character_profiles": self.character_profiles,
            "total_pages": self.get_total_pages(),
            "total_panels": self.get_total_panels(),
            "scenes": [
                {
                    "scene_id": scene.scene_id,
                    "scene_summary": scene.scene_summary,
                    "mood": scene.mood.value,
                    "importance": scene.importance,
                    "pages": [
                        {
                            "page_number": page.page_number,
                            "template_id": page.template.id if page.template else "unknown",
                            "template_name": page.template.name_zh if page.template else "未知模板",
                            "panel_count": len(page.panels),
                        }
                        for page in scene.pages
                    ],
                }
                for scene in self.scenes
            ],
            "panels": [
                {
                    "panel_id": p.panel_id,
                    "scene_id": p.scene_id,
                    "page_number": p.page_number,
                    "slot_id": p.slot_id,
                    "aspect_ratio": p.aspect_ratio,
                    "composition": p.composition,
                    "camera_angle": p.camera_angle,
                    "prompt_en": p.prompt_en,
                    "prompt_zh": p.prompt_zh,
                    "negative_prompt": p.negative_prompt,
                    # 文字元素 - 基础字段
                    "dialogue": p.dialogue,
                    "dialogue_speaker": p.dialogue_speaker,
                    "narration": p.narration,
                    "sound_effects": p.sound_effects,
                    # 文字元素 - 扩展字段
                    "dialogue_bubble_type": p.dialogue_bubble_type,
                    "dialogue_position": p.dialogue_position,
                    "dialogue_emotion": p.dialogue_emotion,
                    "narration_position": p.narration_position,
                    "sound_effect_details": p.sound_effect_details,
                    # 视觉信息
                    "characters": p.characters,
                    "is_key_panel": p.is_key_panel,
                    # 视觉氛围信息
                    "lighting": p.lighting,
                    "atmosphere": p.atmosphere,
                    "key_visual_elements": p.key_visual_elements,
                    # 参考图（用于 img2img）
                    "reference_image_paths": p.reference_image_paths or [],
                    # 语言设置（用于图片生成时的语言约束）
                    "dialogue_language": self.dialogue_language,
                }
                for p in self.panel_prompts
            ],
            "created_at": self.created_at.isoformat(),
        }


__all__ = [
    "MangaStyle",
    "MangaGenerationResult",
]
