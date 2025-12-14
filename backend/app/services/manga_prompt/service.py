"""
漫画提示词服务

主服务入口，协调工作流执行并提供对外接口。
"""

import logging
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    MangaPromptRequest,
    MangaPromptResult,
    MangaScene,
    MangaStyle,
    SceneUpdateRequest,
)
from ...models.novel import Chapter, ChapterMangaPrompt, BlueprintCharacter
from ...repositories.chapter_repository import ChapterRepository
from ...utils.json_utils import parse_llm_json_safe

logger = logging.getLogger(__name__)


class MangaPromptService:
    """漫画提示词服务"""

    def __init__(
        self,
        session: AsyncSession,
        llm_service,
        prompt_service=None,
    ):
        """
        初始化服务

        Args:
            session: 数据库会话
            llm_service: LLM服务
            prompt_service: 提示词服务
        """
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.chapter_repo = ChapterRepository(session)

    async def generate_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
        request: MangaPromptRequest,
        user_id: str,
    ) -> MangaPromptResult:
        """
        生成章节的漫画提示词

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            request: 生成请求
            user_id: 用户ID

        Returns:
            漫画提示词结果
        """
        # 获取章节内容
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter or not chapter.selected_version:
            raise ValueError(f"章节 {chapter_number} 不存在或未生成内容")

        content = chapter.selected_version.content

        # 获取角色信息
        character_profiles = await self._build_character_profiles(project_id)

        # 构建提示词并调用LLM
        system_prompt, user_prompt = await self._build_prompts(
            content=content,
            character_profiles=character_profiles,
            style=request.style,
            scene_count=request.scene_count,
        )

        # 调用LLM生成
        llm_response = await self.llm_service.get_llm_response(
            system_prompt,
            [{"role": "user", "content": user_prompt}],
            temperature=0.7,
            response_format="json_object",
            user_id=int(user_id) if user_id else None,
        )

        # 解析响应
        result = self._parse_llm_response(
            llm_response,
            chapter_number=chapter_number,
            style=request.style,
        )

        # 保存到数据库
        await self._save_manga_prompt(chapter.id, result)

        return result

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
        scenes = [MangaScene(**scene) for scene in (mp.scenes or [])]

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=mp.character_profiles or {},
            scenes=scenes,
            style_guide=mp.style_guide or "",
            total_scenes=len(scenes),
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
        from sqlalchemy import select

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

    async def _build_prompts(
        self,
        content: str,
        character_profiles: Dict[str, str],
        style: MangaStyle,
        scene_count: Optional[int],
    ) -> tuple[str, str]:
        """
        构建LLM提示词

        Args:
            content: 章节内容
            character_profiles: 角色外观描述
            style: 漫画风格
            scene_count: 目标场景数，为None时由LLM自动决定

        Returns:
            (system_prompt, user_prompt)
        """
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

        # 风格映射
        style_map = {
            MangaStyle.MANGA: "Japanese manga style, black and white ink drawing, dynamic lines, screentones",
            MangaStyle.ANIME: "Anime style, vibrant colors, clean lines, expressive eyes",
            MangaStyle.COMIC: "Western comic book style, bold colors, dramatic shadows, detailed backgrounds",
            MangaStyle.WEBTOON: "Korean webtoon style, soft colors, clean digital art, vertical scroll format",
        }

        # 根据是否指定场景数构建不同的提示
        if scene_count is not None:
            scene_instruction = f"请将以下小说章节内容转化为 {scene_count} 个漫画场景的文生图提示词。"
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
你是专业的漫画分镜师和AI提示词工程师。你擅长将小说内容转化为视觉化的漫画场景描述。

# 任务
将小说章节内容转化为一系列漫画画面的文生图提示词。每个提示词应该能够让AI图像生成模型创建出视觉上连贯、叙事清晰的漫画画面。

# 输出格式
请输出一个JSON对象，包含以下字段：

```json
{
  "character_profiles": {
    "角色名": "详细的英文外观描述，包括年龄、性别、发色、瞳色、体型、服装等特征"
  },
  "style_guide": "整体风格描述（英文），如 'manga style, detailed backgrounds, dramatic lighting'",
  "scenes": [
    {
      "scene_id": 1,
      "scene_summary": "中文场景简述",
      "original_text": "对应的原文片段（截取关键句子）",
      "characters": ["出场角色名列表"],
      "prompt_en": "完整的英文提示词，包含角色描述、动作、表情、环境、光线、构图等",
      "prompt_zh": "中文说明（帮助用户理解这个场景）",
      "negative_prompt": "负面提示词（避免生成的内容）",
      "style_tags": ["manga", "dramatic lighting"],
      "composition": "medium shot / close-up / wide shot 等",
      "emotion": "场景的情感基调",
      "lighting": "光线描述"
    }
  ]
}
```

# 重要要求
1. **提示词必须是英文**（用于AI图像生成）
2. **不要在提示词中包含对话文字**（文字容易生成错误）
3. **角色外观描述必须在所有场景中保持一致**（使用character_profiles中的描述）
4. **每个场景应该是视觉上有意义的关键画面**
5. **包含构图、光线、情感等视觉元素的描述**
6. **场景按照故事时间线顺序排列**"""

    def _parse_llm_response(
        self,
        response: str,
        chapter_number: int,
        style: MangaStyle,
    ) -> MangaPromptResult:
        """
        解析LLM响应

        Args:
            response: LLM响应文本
            chapter_number: 章节号
            style: 漫画风格

        Returns:
            解析后的结果
        """
        data = parse_llm_json_safe(response)

        if not data:
            logger.error("无法解析LLM响应: %s", response[:500])
            raise ValueError("LLM响应解析失败")

        # 解析角色外观
        character_profiles = data.get("character_profiles", {})

        # 解析场景
        scenes = []
        for scene_data in data.get("scenes", []):
            try:
                scene = MangaScene(
                    scene_id=scene_data.get("scene_id", len(scenes) + 1),
                    scene_summary=scene_data.get("scene_summary", ""),
                    original_text=scene_data.get("original_text", ""),
                    characters=scene_data.get("characters", []),
                    prompt_en=scene_data.get("prompt_en", ""),
                    prompt_zh=scene_data.get("prompt_zh", ""),
                    negative_prompt=scene_data.get("negative_prompt", ""),
                    style_tags=scene_data.get("style_tags", []),
                    composition=scene_data.get("composition", "medium shot"),
                    emotion=scene_data.get("emotion", ""),
                    lighting=scene_data.get("lighting", ""),
                )
                scenes.append(scene)
            except Exception as e:
                logger.warning("解析场景失败: %s, 错误: %s", scene_data, e)

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=character_profiles,
            scenes=scenes,
            style_guide=data.get("style_guide", ""),
            total_scenes=len(scenes),
            style=style,
        )

    async def _save_manga_prompt(
        self,
        chapter_id: int,
        result: MangaPromptResult,
    ) -> None:
        """
        保存漫画提示词到数据库

        Args:
            chapter_id: 章节ID
            result: 生成结果
        """
        from sqlalchemy import select

        # 检查是否已存在
        existing = await self.session.execute(
            select(ChapterMangaPrompt).where(
                ChapterMangaPrompt.chapter_id == chapter_id
            )
        )
        manga_prompt = existing.scalar_one_or_none()

        scenes_data = [scene.model_dump() for scene in result.scenes]

        if manga_prompt:
            # 更新现有记录
            manga_prompt.character_profiles = result.character_profiles
            manga_prompt.style_guide = result.style_guide
            manga_prompt.scenes = scenes_data
        else:
            # 创建新记录
            manga_prompt = ChapterMangaPrompt(
                chapter_id=chapter_id,
                character_profiles=result.character_profiles,
                style_guide=result.style_guide,
                scenes=scenes_data,
            )
            self.session.add(manga_prompt)

        await self.session.flush()
