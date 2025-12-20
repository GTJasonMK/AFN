"""
CRUD操作Mixin

提供漫画提示词的增删改查相关方法。
"""

import logging
from typing import Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    MangaPromptResult,
    MangaScene,
    SceneUpdateRequest,
    PanelInfo,
    LayoutInfo,
)
from ...models.novel import ChapterMangaPrompt, BlueprintCharacter
from ...repositories.chapter_repository import ChapterRepository

logger = logging.getLogger(__name__)


class CrudMixin:
    """CRUD操作相关方法的Mixin"""

    # 需要被主类提供的属性和方法
    session: AsyncSession
    chapter_repo: ChapterRepository
    _parse_dialogues: Any
    _parse_sound_effects: Any

    async def get_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[MangaPromptResult]:
        """
        获取已保存的漫画提示词

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            漫画提示词结果或None
        """
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter or not chapter.manga_prompt:
            return None

        mp = chapter.manga_prompt

        # 解析场景，处理panel_info
        scenes = []
        for scene_data in mp.scenes or []:
            # 如果有panel_info，转换为PanelInfo对象
            panel_info = None
            if scene_data.get("panel_info"):
                panel_info = PanelInfo(**scene_data["panel_info"])

            scene = MangaScene(
                scene_id=scene_data.get("scene_id", len(scenes) + 1),
                scene_summary=scene_data.get("scene_summary", ""),
                original_text=scene_data.get("original_text", ""),
                characters=scene_data.get("characters", []),
                # 对话和文字元素
                dialogues=self._parse_dialogues(scene_data.get("dialogues", [])),
                narration=scene_data.get("narration"),
                sound_effects=self._parse_sound_effects(
                    scene_data.get("sound_effects", [])
                ),
                # 核心提示词
                prompt_en=scene_data.get("prompt_en", ""),
                prompt_zh=scene_data.get("prompt_zh", ""),
                negative_prompt=scene_data.get("negative_prompt", ""),
                style_tags=scene_data.get("style_tags", []),
                composition=scene_data.get("composition", "medium shot"),
                emotion=scene_data.get("emotion", ""),
                lighting=scene_data.get("lighting", ""),
                panel_info=panel_info,
            )
            scenes.append(scene)

        # 解析排版信息
        layout_info = None
        if mp.layout_info:
            layout_info = LayoutInfo(**mp.layout_info)

        # 检查版本匹配情况
        version_mismatch_warning = None
        if mp.source_version_id is not None:
            if chapter.selected_version_id != mp.source_version_id:
                version_mismatch_warning = (
                    "注意：当前漫画提示词基于旧版本正文生成，"
                    "由于章节已切换到新版本，建议重新生成漫画提示词以确保内容一致性。"
                )
                logger.warning(
                    "章节 %d 的漫画提示词版本不匹配: 当前版本=%s, 提示词基于版本=%s",
                    chapter_number,
                    chapter.selected_version_id,
                    mp.source_version_id,
                )

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=mp.character_profiles or {},
            scenes=scenes,
            style_guide=mp.style_guide or "",
            total_scenes=len(scenes),
            layout_info=layout_info,
            version_mismatch_warning=version_mismatch_warning,
        )

    async def update_scene(
        self,
        project_id: str,
        chapter_number: int,
        scene_id: int,
        update: SceneUpdateRequest,
    ) -> MangaScene:
        """
        更新单个场景

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID
            update: 更新请求

        Returns:
            更新后的场景
        """
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter or not chapter.manga_prompt:
            raise ValueError("漫画提示词不存在")

        mp = chapter.manga_prompt
        scenes = mp.scenes or []

        # 查找并更新场景
        for i, scene in enumerate(scenes):
            if scene.get("scene_id") == scene_id:
                # 更新非None字段
                update_dict = update.model_dump(exclude_none=True)
                scene.update(update_dict)
                scenes[i] = scene

                # 保存更新
                mp.scenes = scenes
                await self.session.flush()

                return MangaScene(**scene)

        raise ValueError(f"场景 {scene_id} 不存在")

    async def delete_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
    ) -> bool:
        """
        删除章节的漫画提示词

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            是否删除成功
        """
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter or not chapter.manga_prompt:
            return False

        await self.session.delete(chapter.manga_prompt)
        await self.session.flush()
        return True

    async def _save_manga_prompt(
        self,
        chapter_id: int,
        result: MangaPromptResult,
        source_version_id: Optional[int] = None,
    ) -> None:
        """
        保存漫画提示词到数据库

        Args:
            chapter_id: 章节ID
            result: 生成结果
            source_version_id: 关联的正文版本ID（用于版本匹配检查）
        """
        # 检查是否已存在
        existing = await self.session.execute(
            select(ChapterMangaPrompt).where(
                ChapterMangaPrompt.chapter_id == chapter_id
            )
        )
        manga_prompt = existing.scalar_one_or_none()

        scenes_data = [scene.model_dump() for scene in result.scenes]
        layout_info_data = result.layout_info.model_dump() if result.layout_info else None

        if manga_prompt:
            # 更新现有记录
            manga_prompt.character_profiles = result.character_profiles
            manga_prompt.style_guide = result.style_guide
            manga_prompt.scenes = scenes_data
            manga_prompt.layout_info = layout_info_data
            manga_prompt.source_version_id = source_version_id  # 更新关联版本
            # 更新状态为completed
            manga_prompt.generation_status = "completed"
            manga_prompt.generation_progress = None
        else:
            # 创建新记录
            manga_prompt = ChapterMangaPrompt(
                chapter_id=chapter_id,
                character_profiles=result.character_profiles,
                style_guide=result.style_guide,
                scenes=scenes_data,
                layout_info=layout_info_data,
                source_version_id=source_version_id,
                generation_status="completed",
            )
            self.session.add(manga_prompt)

        await self.session.flush()

    async def _build_character_profiles(
        self,
        project_id: str,
    ) -> Dict[str, str]:
        """
        构建角色外观描述

        优先使用用户填写的外观描述，没有则留空（由LLM生成）

        Args:
            project_id: 项目ID

        Returns:
            角色外观字典
        """
        result = await self.session.execute(
            select(BlueprintCharacter).where(
                BlueprintCharacter.project_id == project_id
            )
        )
        characters = result.scalars().all()

        profiles = {}
        for char in characters:
            # 检查extra字段中是否有appearance
            appearance_desc = ""
            if char.extra and isinstance(char.extra, dict):
                appearance = char.extra.get("appearance", {})
                if appearance:
                    parts = []
                    if appearance.get("age"):
                        parts.append(appearance["age"])
                    if appearance.get("gender"):
                        parts.append(appearance["gender"])
                    if appearance.get("hair"):
                        parts.append(appearance["hair"])
                    if appearance.get("eyes"):
                        parts.append(appearance["eyes"])
                    if appearance.get("build"):
                        parts.append(appearance["build"])
                    if appearance.get("clothing"):
                        parts.append(f"wearing {appearance['clothing']}")
                    if appearance.get("features"):
                        parts.append(appearance["features"])
                    appearance_desc = ", ".join(parts)

            profiles[char.name] = appearance_desc

        return profiles
