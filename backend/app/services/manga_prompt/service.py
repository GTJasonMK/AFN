"""
漫画提示词服务

主服务入口，协调工作流执行并提供对外接口。
新流程：先生成排版 -> 再基于排版生成提示词 -> 最后组装结果
"""

import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    MangaPromptRequest,
    MangaPromptResult,
    MangaScene,
    MangaStyle,
    SceneUpdateRequest,
    PanelInfo,
    LayoutInfo,
    DialogueLanguage,
    DialogueItem,
    SoundEffectItem,
)
from .layout_schemas import (
    LayoutType,
    PageSize,
    LayoutGenerationRequest,
)
from .layout_service import LayoutService
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
        self.layout_service = LayoutService(session, llm_service, prompt_service)

    async def generate_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
        request: MangaPromptRequest,
        user_id: str,
    ) -> MangaPromptResult:
        """
        生成章节的漫画提示词（带排版）

        新流程：
        1. 获取章节内容
        2. 快速提取场景概要
        3. 调用LayoutService生成排版
        4. 基于排版信息生成详细提示词
        5. 组装最终结果

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

        # 步骤1: 快速提取场景概要
        logger.info("步骤1: 提取场景概要")
        scene_summaries = await self._extract_scene_summaries(
            content=content,
            scene_count=request.scene_count,
            user_id=user_id,
        )

        # 步骤2: 生成排版方案
        logger.info("步骤2: 生成排版方案，共 %d 个场景", len(scene_summaries))
        layout_request = LayoutGenerationRequest(
            layout_type=self._get_layout_type(request.style),
            page_size=PageSize.A4,
            panels_per_page=6,
            reading_direction="ltr",
        )

        layout_result = await self.layout_service.generate_layout(
            chapter_content=content[:2000],  # 内容概要
            scene_summaries=scene_summaries,
            request=layout_request,
            user_id=user_id,
        )

        # 步骤3: 基于排版生成详细提示词
        logger.info("步骤3: 基于排版生成详细提示词")
        system_prompt, user_prompt = await self._build_prompts_with_layout(
            content=content,
            character_profiles=character_profiles,
            style=request.style,
            scene_summaries=scene_summaries,
            layout_result=layout_result,
            dialogue_language=request.dialogue_language,
            include_dialogue=request.include_dialogue,
            include_sound_effects=request.include_sound_effects,
        )

        # 调用LLM生成
        # 注意: 某些模型(如Gemini)可能不支持response_format参数，所以不强制要求JSON格式
        # JSON解析工具会自动从响应中提取JSON内容
        llm_response = await self.llm_service.get_llm_response(
            system_prompt,
            [{"role": "user", "content": user_prompt}],
            temperature=0.7,
            response_format=None,  # 不强制JSON格式，兼容更多模型
            user_id=int(user_id) if user_id else None,
        )

        # 解析响应并附加排版信息
        result = self._parse_llm_response_with_layout(
            llm_response,
            chapter_number=chapter_number,
            style=request.style,
            layout_result=layout_result,
        )

        # 保存到数据库
        await self._save_manga_prompt(chapter.id, result)

        return result

    async def _extract_scene_summaries(
        self,
        content: str,
        scene_count: Optional[int],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        快速提取场景概要

        Args:
            content: 章节内容
            scene_count: 目标场景数
            user_id: 用户ID

        Returns:
            场景概要列表
        """
        scene_hint = f"分割成 {scene_count} 个场景" if scene_count else "分割成5-15个场景"

        system_prompt = """你是专业的漫画分镜师。请快速将小说章节内容分割成漫画场景。
只需要返回场景的简要信息，不需要生成详细提示词。

输出JSON格式：
{
  "scenes": [
    {
      "scene_id": 1,
      "summary": "场景的一句话描述",
      "emotion": "情感基调（如：紧张、温馨、悲伤）",
      "characters": ["出场角色列表"],
      "scene_type": "场景类型：对话/动作/环境/特写/转场"
    }
  ]
}"""

        user_prompt = f"""请将以下章节内容{scene_hint}：

{content}

要求：
1. 选择视觉上有意义的关键画面
2. 按故事时间线顺序
3. 识别每个场景的情感和类型"""

        response = await self.llm_service.get_llm_response(
            system_prompt,
            [{"role": "user", "content": user_prompt}],
            temperature=0.5,
            response_format="json_object",
            user_id=int(user_id) if user_id else None,
        )

        data = parse_llm_json_safe(response)
        if not data or "scenes" not in data:
            # 返回默认场景列表
            return [{"scene_id": i + 1, "summary": f"场景{i + 1}", "emotion": "", "characters": [], "scene_type": "对话"} for i in range(8)]

        return data["scenes"]

    def _get_layout_type(self, style: MangaStyle) -> LayoutType:
        """根据漫画风格获取排版类型"""
        mapping = {
            MangaStyle.MANGA: LayoutType.TRADITIONAL_MANGA,
            MangaStyle.ANIME: LayoutType.TRADITIONAL_MANGA,
            MangaStyle.COMIC: LayoutType.COMIC,
            MangaStyle.WEBTOON: LayoutType.WEBTOON,
        }
        return mapping.get(style, LayoutType.TRADITIONAL_MANGA)

    async def _build_prompts_with_layout(
        self,
        content: str,
        character_profiles: Dict[str, str],
        style: MangaStyle,
        scene_summaries: List[Dict[str, Any]],
        layout_result,
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
            guide_lines.append("- 对话气泡类型: normal(普通)/shout(大喊)/whisper(低语)/thought(内心独白)/narration(旁白)/electronic(电子声音)")
            guide_lines.append("- 气泡位置: top-left/top-center/top-right/middle-left/middle-right/bottom-left/bottom-center/bottom-right")
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
            guide_lines.append("- 音效类型: action(动作)/impact(撞击)/ambient(环境)/emotional(情感)/vocal(人声)")
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
                guide_lines.append(f"- 音效示例（{dialogue_language}）: {sfx_hints[dialogue_language]}")
        else:
            guide_lines.append("- 不需要生成音效文字，sound_effects数组留空")

        return "\n".join(guide_lines)

    def _build_layout_guide(
        self,
        scene_summaries: List[Dict[str, Any]],
        layout_result,
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
                aspect_ratio = self.layout_service.get_panel_aspect_ratio(layout, scene_id)

                guide_lines.append(
                    f"- 场景{scene_id}: 页{page.page_number}, "
                    f"重要性={importance}, 构图={composition}, "
                    f"推荐比例={aspect_ratio}"
                )

        return "\n".join(guide_lines)

    def _parse_llm_response_with_layout(
        self,
        response: str,
        chapter_number: int,
        style: MangaStyle,
        layout_result,
    ) -> MangaPromptResult:
        """
        解析LLM响应并附加排版信息

        Args:
            response: LLM响应文本
            chapter_number: 章节号
            style: 漫画风格
            layout_result: 排版结果

        Returns:
            解析后的结果
        """
        data = parse_llm_json_safe(response)

        if not data:
            # 记录更详细的错误信息用于调试
            logger.error("LLM响应解析失败，原始响应长度: %d", len(response) if response else 0)
            logger.error("LLM响应前1000字符: %s", response[:1000] if response else "(空)")
            logger.error("LLM响应后500字符: %s", response[-500:] if response and len(response) > 500 else "(短)")
            raise ValueError(f"LLM响应解析失败，请检查后端日志获取详细信息")

        # 解析角色外观
        character_profiles = data.get("character_profiles", {})

        # 构建场景到格子的映射
        panel_map = {}
        if layout_result and layout_result.success:
            layout = layout_result.layout
            for page in layout.pages:
                for panel in page.panels:
                    panel_map[panel.scene_id] = {
                        "panel_id": panel.panel_id,
                        "page_number": page.page_number,
                        "importance": panel.importance.value,
                        "x": panel.x,
                        "y": panel.y,
                        "width": panel.width,
                        "height": panel.height,
                        "aspect_ratio": self.layout_service.get_panel_aspect_ratio(
                            layout, panel.scene_id
                        ) or "1:1",
                        "camera_angle": panel.camera_angle,
                    }

        # 解析场景
        scenes = []
        for scene_data in data.get("scenes", []):
            try:
                scene_id = scene_data.get("scene_id", len(scenes) + 1)

                # 附加排版信息
                panel_info = None
                if scene_id in panel_map:
                    panel_info = PanelInfo(**panel_map[scene_id])

                scene = MangaScene(
                    scene_id=scene_id,
                    scene_summary=scene_data.get("scene_summary", ""),
                    original_text=scene_data.get("original_text", ""),
                    characters=scene_data.get("characters", []),
                    # 对话和文字元素
                    dialogues=self._parse_dialogues(scene_data.get("dialogues", [])),
                    narration=scene_data.get("narration"),
                    sound_effects=self._parse_sound_effects(scene_data.get("sound_effects", [])),
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
            except Exception as e:
                logger.warning("解析场景失败: %s, 错误: %s", scene_data, e)

        # 构建排版信息摘要
        layout_info = None
        if layout_result and layout_result.success:
            layout = layout_result.layout
            layout_info = LayoutInfo(
                layout_type=layout.layout_type.value,
                page_size=layout.page_size.value,
                reading_direction=layout.reading_direction,
                total_pages=layout.total_pages,
                total_panels=layout.total_panels,
            )

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=character_profiles,
            scenes=scenes,
            style_guide=data.get("style_guide", ""),
            total_scenes=len(scenes),
            style=style,
            layout_info=layout_info,
        )

    def _parse_dialogues(self, dialogues_data: List[Dict[str, Any]]) -> List[DialogueItem]:
        """
        解析对话数据

        Args:
            dialogues_data: 对话数据列表

        Returns:
            DialogueItem列表
        """
        result = []
        for d in dialogues_data:
            try:
                item = DialogueItem(
                    speaker=d.get("speaker", ""),
                    text=d.get("text", ""),
                    bubble_type=d.get("bubble_type", "normal"),
                    position=d.get("position", "top-right"),
                )
                result.append(item)
            except Exception as e:
                logger.warning("解析对话失败: %s, 错误: %s", d, e)
        return result

    def _parse_sound_effects(self, sfx_data: List[Dict[str, Any]]) -> List[SoundEffectItem]:
        """
        解析音效数据

        Args:
            sfx_data: 音效数据列表

        Returns:
            SoundEffectItem列表
        """
        result = []
        for s in sfx_data:
            try:
                item = SoundEffectItem(
                    text=s.get("text", ""),
                    type=s.get("type", "action"),
                    intensity=s.get("intensity", "medium"),
                )
                result.append(item)
            except Exception as e:
                logger.warning("解析音效失败: %s, 错误: %s", s, e)
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

        # 解析场景，处理panel_info
        scenes = []
        for scene_data in (mp.scenes or []):
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
                sound_effects=self._parse_sound_effects(scene_data.get("sound_effects", [])),
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

        return MangaPromptResult(
            chapter_number=chapter_number,
            character_profiles=mp.character_profiles or {},
            scenes=scenes,
            style_guide=mp.style_guide or "",
            total_scenes=len(scenes),
            layout_info=layout_info,
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
        layout_info_data = result.layout_info.model_dump() if result.layout_info else None

        if manga_prompt:
            # 更新现有记录
            manga_prompt.character_profiles = result.character_profiles
            manga_prompt.style_guide = result.style_guide
            manga_prompt.scenes = scenes_data
            manga_prompt.layout_info = layout_info_data
        else:
            # 创建新记录
            manga_prompt = ChapterMangaPrompt(
                chapter_id=chapter_id,
                character_profiles=result.character_profiles,
                style_guide=result.style_guide,
                scenes=scenes_data,
                layout_info=layout_info_data,
            )
            self.session.add(manga_prompt)

        await self.session.flush()
