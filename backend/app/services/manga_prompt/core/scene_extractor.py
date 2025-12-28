"""
场景提取器

从章节内容中提取关键叙事场景。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from app.services.llm_wrappers import call_llm, LLMProfile
from app.utils.json_utils import parse_llm_json_safe

from .prompts import SCENE_EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class SceneExtractor:
    """
    场景提取器

    从章节内容中提取关键叙事场景
    """

    def __init__(self, llm_service, prompt_service=None):
        """
        初始化提取器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def extract_scenes(
        self,
        content: str,
        min_scenes: int,
        max_scenes: int,
        user_id: Optional[int],
        dialogue_language: str = "chinese",
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        从章节内容中提取场景

        Args:
            content: 章节内容
            min_scenes: 最少场景数
            max_scenes: 最多场景数
            user_id: 用户ID
            dialogue_language: 对话语言

        Returns:
            (场景列表, 角色外观字典)
        """
        prompt = SCENE_EXTRACTION_PROMPT.format(
            content=content[:8000],  # 限制长度
            min_scenes=min_scenes,
            max_scenes=max_scenes,
            dialogue_language=dialogue_language,
        )

        # 尝试从提示词服务获取系统提示词，否则使用默认值
        system_prompt = None
        if self.prompt_service:
            try:
                system_prompt = await self.prompt_service.get_prompt("manga_prompt")
            except Exception as e:
                logger.warning(f"无法加载 manga_prompt 提示词: {e}")

        if not system_prompt:
            system_prompt = "你是专业的漫画分镜师，擅长将文字叙事转化为视觉场景。"

        response = await call_llm(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=system_prompt,
            user_content=prompt,
            user_id=user_id,
        )

        data = parse_llm_json_safe(response)

        if not data or "scenes" not in data:
            logger.warning("场景提取失败，使用默认分割")
            return self.fallback_scene_extraction(content, min_scenes), {}

        scenes = data.get("scenes", [])
        character_profiles = data.get("character_profiles", {})

        # 确保每个场景有必要字段
        for i, scene in enumerate(scenes):
            scene.setdefault("scene_id", i + 1)
            scene.setdefault("mood", "calm")
            scene.setdefault("importance", "normal")
            scene.setdefault("has_dialogue", False)
            scene.setdefault("is_action", False)

        return scenes, character_profiles

    def fallback_scene_extraction(
        self,
        content: str,
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """
        回退的场景提取（简单分段）

        Args:
            content: 章节内容
            target_count: 目标场景数

        Returns:
            场景列表
        """
        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        # 合并成目标数量的场景
        scenes = []
        chunk_size = max(1, len(paragraphs) // target_count)

        for i in range(0, len(paragraphs), chunk_size):
            chunk = paragraphs[i:i + chunk_size]
            scene_content = '\n'.join(chunk)

            scenes.append({
                "scene_id": len(scenes) + 1,
                "summary": scene_content[:50] + "...",
                "content": scene_content,
                "characters": [],
                "mood": "calm",
                "importance": "normal",
                "has_dialogue": '"' in scene_content or '"' in scene_content,
                "is_action": False,
            })

            if len(scenes) >= target_count:
                break

        return scenes


__all__ = [
    "SceneExtractor",
]
