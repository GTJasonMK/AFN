"""
漫画提示词服务 V2

基于专业漫画分镜理念重新设计的服务。

核心流程：
1. 提取场景 - 从章节内容中识别关键叙事场景
2. 展开场景 - 将每个场景展开为页面+画格
3. 生成提示词 - 为每个画格生成专属提示词
4. 保存结果 - 存储生成结果供后续使用

设计原则：
- 简洁：减少不必要的抽象层
- 清晰：流程直观易懂
- 专业：基于真实漫画分镜实践
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService
from app.services.llm_wrappers import call_llm, LLMProfile
from app.services.prompt_service import PromptService
from app.services.image_generation.service import ImageGenerationService
from app.utils.json_utils import parse_llm_json_safe
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.manga_prompt_repository import MangaPromptRepository

from .page_templates import (
    PageTemplate,
    SceneMood,
    SceneExpansion,
    PagePlan,
    PanelContent,
    ALL_TEMPLATES,
    recommend_template,
)
from .scene_expansion_service import SceneExpansionService
from .panel_prompt_builder import PanelPromptBuilder, PanelPrompt

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================

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
    ):
        self.chapter_number = chapter_number
        self.style = style
        self.scenes = scenes
        self.panel_prompts = panel_prompts
        self.character_profiles = character_profiles
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
                            "template_id": page.template.id,
                            "template_name": page.template.name_zh,
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
                    # 参考图（用于 img2img）
                    "reference_image_paths": p.reference_image_paths or [],
                }
                for p in self.panel_prompts
            ],
            "created_at": self.created_at.isoformat(),
        }


# ============================================================
# 场景提取提示词
# ============================================================

SCENE_EXTRACTION_PROMPT = """你是专业的漫画分镜师。请从以下章节内容中识别关键叙事场景。

## 章节内容
{content}

## 要求
1. 识别 {min_scenes}-{max_scenes} 个关键场景
2. 每个场景应该是一个独立的叙事单元（可以展开为1-2页漫画）
3. 注意场景的情感变化和节奏
4. 标注每个场景的重要性

## 语言设置（极其重要，必须严格遵守）
目标语言: {dialogue_language}

**重要约束**：
- 场景内容(content)字段：保留原文用于上下文理解
- 角色外观描述(character_profiles)：必须使用英文（用于AI绘图）
- 此阶段无需生成对话，对话将在后续阶段根据目标语言生成

## 输出格式
```json
{{
  "scenes": [
    {{
      "scene_id": 1,
      "summary": "场景简要描述（20字内）",
      "content": "场景对应的原文内容（可以是摘要）",
      "characters": ["出场角色"],
      "mood": "情感类型（calm/tension/action/emotional/mystery/comedy/dramatic/romantic/horror/flashback）",
      "importance": "重要程度（low/normal/high/critical）",
      "has_dialogue": true/false,
      "is_action": true/false
    }}
  ],
  "character_profiles": {{
    "角色名": "外观描述（用于AI绘图，英文）"
  }}
}}
```
"""

# 语言提示映射
LANGUAGE_HINTS = {
    "chinese": "中文",
    "japanese": "日语",
    "english": "英文",
    "korean": "韩语",
}


# ============================================================
# 主服务类
# ============================================================

class MangaPromptServiceV2:
    """
    漫画提示词服务 V2

    简洁版本，基于新的页面模板架构
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: Optional[PromptService] = None,
    ):
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service

        # 数据访问层
        self.chapter_repo = ChapterRepository(session)
        self.manga_prompt_repo = MangaPromptRepository(session)

        # 图片服务（用于清理旧图片）
        self.image_service = ImageGenerationService(session)

        # 子服务
        self.expansion_service = SceneExpansionService(llm_service)

    async def generate(
        self,
        project_id: str,
        chapter_number: int,
        chapter_content: str,
        style: str = MangaStyle.MANGA,
        min_scenes: int = 5,
        max_scenes: int = 15,
        user_id: Optional[int] = None,
        resume: bool = True,  # 是否从断点恢复
        dialogue_language: str = "chinese",  # 对话/音效语言
        character_portraits: Optional[Dict[str, str]] = None,  # 角色立绘路径
    ) -> MangaGenerationResult:
        """
        生成漫画分镜（支持断点续传）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            chapter_content: 章节内容
            style: 漫画风格
            min_scenes: 最少场景数
            max_scenes: 最多场景数
            user_id: 用户ID
            resume: 是否从断点恢复（默认True）
            dialogue_language: 对话/音效语言（chinese/japanese/english/korean）
            character_portraits: 角色立绘路径字典 {角色名: 立绘图片路径}

        Returns:
            漫画生成结果
        """
        logger.info(f"开始生成漫画分镜: 项目={project_id}, 章节={chapter_number}, 语言={dialogue_language}")

        # 获取章节ID（用于保存断点）
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        chapter_id = chapter.id if chapter else None
        source_version_id = chapter.selected_version_id if chapter else None

        # 检查断点
        checkpoint = None
        if resume and chapter_id:
            checkpoint = await self.manga_prompt_repo.get_checkpoint(
                project_id, chapter_number
            )
            if checkpoint:
                logger.info(f"发现断点: status={checkpoint['status']}, "
                          f"progress={checkpoint.get('progress')}")

        # 初始化变量
        scenes_data = None
        character_profiles = {}
        expansions = []
        start_scene_index = 0

        # 从断点恢复
        if checkpoint and checkpoint.get("checkpoint_data"):
            cp_data = checkpoint["checkpoint_data"]
            scenes_data = cp_data.get("scenes_data")
            character_profiles = cp_data.get("character_profiles", {})
            # 恢复已完成的展开
            completed_expansions_data = cp_data.get("completed_expansions", [])
            start_scene_index = cp_data.get("current_scene_index", 0)

            if completed_expansions_data:
                # 反序列化已完成的展开
                expansions = self._deserialize_expansions(completed_expansions_data)
                logger.info(f"从断点恢复: 已完成 {len(expansions)} 个场景展开")

        # 步骤1：提取场景（如果没有从断点恢复）
        if scenes_data is None:
            logger.info("步骤1: 提取场景")

            # 清理旧数据：重新生成时删除之前的图片和分镜数据
            # 这确保了数据一致性，避免旧的 panel_id 与新的不匹配
            await self._cleanup_old_data(project_id, chapter_number, chapter_id)

            # 保存状态：正在提取场景
            if chapter_id:
                await self._save_checkpoint(
                    chapter_id, "extracting",
                    {"stage": "extracting", "current": 0, "total": 0, "message": "正在提取场景..."},
                    {}, style, source_version_id
                )

            scenes_data, character_profiles = await self._extract_scenes(
                content=chapter_content,
                min_scenes=min_scenes,
                max_scenes=max_scenes,
                user_id=user_id,
                dialogue_language=dialogue_language,
            )
            logger.info(f"提取到 {len(scenes_data)} 个场景")

            # 保存断点：场景提取完成
            if chapter_id:
                await self._save_checkpoint(
                    chapter_id, "expanding",
                    {"stage": "expanding", "current": 0, "total": len(scenes_data),
                     "message": f"准备展开 {len(scenes_data)} 个场景"},
                    {"scenes_data": scenes_data, "character_profiles": character_profiles,
                     "completed_expansions": [], "current_scene_index": 0},
                    style, source_version_id
                )
        else:
            logger.info(f"从断点恢复: 跳过场景提取，共 {len(scenes_data)} 个场景")

        # 步骤2：展开场景为页面+画格
        logger.info(f"步骤2: 展开场景 (从第 {start_scene_index + 1} 个开始)")
        new_expansions = await self._expand_scenes_with_checkpoint(
            scenes_data=scenes_data,
            start_index=start_scene_index,
            chapter_id=chapter_id,
            character_profiles=character_profiles,
            style=style,
            source_version_id=source_version_id,
            existing_expansions=expansions,
            user_id=user_id,
            dialogue_language=dialogue_language,
        )
        expansions = new_expansions

        total_pages = sum(len(e.pages) for e in expansions)
        total_panels = sum(e.get_total_panels() for e in expansions)
        logger.info(f"展开为 {total_pages} 页, {total_panels} 格")

        # 步骤3：为每个画格生成提示词
        logger.info("步骤3: 生成画格提示词")

        # 保存断点状态：正在构建提示词（场景展开已完成）
        if chapter_id:
            await self._save_checkpoint(
                chapter_id, "prompt_building",
                {"stage": "prompt_building", "current": 0, "total": total_panels,
                 "message": f"正在为 {total_panels} 个画格生成提示词..."},
                {"scenes_data": scenes_data,
                 "character_profiles": character_profiles,
                 "completed_expansions": self._serialize_expansions_minimal(expansions),
                 "current_scene_index": len(scenes_data)},  # 所有场景已完成
                style, source_version_id,
            )

        prompt_builder = PanelPromptBuilder(
            style=style,
            character_profiles=character_profiles,
            dialogue_language=dialogue_language,
            character_portraits=character_portraits,
        )
        panel_prompts = []
        for expansion in expansions:
            prompts = prompt_builder.build_panel_prompts(expansion)
            panel_prompts.extend(prompts)
        logger.info(f"生成 {len(panel_prompts)} 个画格提示词")

        # 构建结果
        result = MangaGenerationResult(
            chapter_number=chapter_number,
            style=style,
            scenes=expansions,
            panel_prompts=panel_prompts,
            character_profiles=character_profiles,
        )

        # 步骤4：保存结果
        logger.info("步骤4: 保存结果")
        await self._save_result(project_id, chapter_number, result)

        logger.info(
            f"漫画分镜生成完成: {result.get_total_pages()}页, "
            f"{result.get_total_panels()}格"
        )

        return result

    async def _save_checkpoint(
        self,
        chapter_id: int,
        status: str,
        progress: dict,
        checkpoint_data: dict,
        style: str,
        source_version_id: Optional[int],
    ):
        """保存断点并提交事务"""
        await self.manga_prompt_repo.save_checkpoint(
            chapter_id=chapter_id,
            status=status,
            progress=progress,
            checkpoint_data=checkpoint_data,
            style=style,
            source_version_id=source_version_id,
        )
        await self.session.commit()

    async def _cleanup_old_data(
        self,
        project_id: str,
        chapter_number: int,
        chapter_id: Optional[int],
    ):
        """
        清理旧的分镜数据和相关图片

        在重新生成分镜时调用，确保数据一致性：
        1. 删除该章节的所有生成图片（文件和数据库记录）
        2. 清除旧的分镜提示词数据

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            chapter_id: 章节数据库ID
        """
        # 1. 删除该章节的所有生成图片
        deleted_images = await self.image_service.delete_chapter_images(
            project_id, chapter_number
        )
        if deleted_images > 0:
            logger.info(
                f"清理旧数据: 删除了 {deleted_images} 张图片 "
                f"(project={project_id}, chapter={chapter_number})"
            )

        # 2. 删除旧的分镜提示词数据（如果存在）
        if chapter_id:
            deleted = await self.manga_prompt_repo.delete_by_chapter_id(chapter_id)
            if deleted:
                logger.info(
                    f"清理旧数据: 删除了旧的分镜提示词 "
                    f"(project={project_id}, chapter={chapter_number})"
                )

        # 提交清理操作
        await self.session.commit()

    async def _expand_scenes_with_checkpoint(
        self,
        scenes_data: List[Dict[str, Any]],
        start_index: int,
        chapter_id: Optional[int],
        character_profiles: dict,
        style: str,
        source_version_id: Optional[int],
        existing_expansions: List[SceneExpansion],
        user_id: Optional[int],
        dialogue_language: str = "chinese",
    ) -> List[SceneExpansion]:
        """
        展开场景并在每个场景完成后保存断点
        """
        expansions = list(existing_expansions)
        total_scenes = len(scenes_data)

        for i in range(start_index, total_scenes):
            scene = scenes_data[i]

            # 获取上下文
            prev_summary = scenes_data[i - 1].get("summary") if i > 0 else None
            next_summary = scenes_data[i + 1].get("summary") if i < len(scenes_data) - 1 else None

            # 判断章节位置
            if i == 0:
                position = "beginning"
            elif i == len(scenes_data) - 1:
                position = "ending"
            elif scene.get("importance") == "critical":
                position = "climax"
            elif i >= len(scenes_data) * 0.7:
                position = "climax"
            else:
                position = "middle"

            logger.info(f"展开场景 {i + 1}/{total_scenes}")

            expansion = await self.expansion_service.expand_scene(
                scene_id=scene.get("scene_id", i + 1),
                scene_summary=scene.get("summary", ""),
                scene_content=scene.get("content", ""),
                characters=scene.get("characters", []),
                previous_scene=prev_summary,
                next_scene=next_summary,
                chapter_position=position,
                user_id=user_id,
                dialogue_language=dialogue_language,
            )

            expansions.append(expansion)

            # 每个场景完成后保存断点（优化内存：精简已完成的数据）
            if chapter_id:
                # 精简 scenes_data：已完成的场景只保留 summary
                optimized_scenes = self._optimize_scenes_for_checkpoint(
                    scenes_data, i + 1
                )
                await self._save_checkpoint(
                    chapter_id, "expanding",
                    {"stage": "expanding", "current": i + 1, "total": total_scenes,
                     "message": f"已展开 {i + 1}/{total_scenes} 个场景"},
                    {"scenes_data": optimized_scenes,
                     "character_profiles": character_profiles,
                     "completed_expansions": self._serialize_expansions_minimal(expansions),
                     "current_scene_index": i + 1},
                    style, source_version_id,
                )

        return expansions

    def _optimize_scenes_for_checkpoint(
        self,
        scenes_data: List[Dict[str, Any]],
        current_index: int,
    ) -> List[Dict[str, Any]]:
        """
        优化 scenes_data 以减少断点存储大小

        已完成的场景只保留 summary（用于上下文）
        当前和未来的场景保留完整数据
        """
        result = []
        for i, scene in enumerate(scenes_data):
            if i < current_index:
                # 已完成的场景：只保留 summary
                result.append({"summary": scene.get("summary", "")})
            else:
                # 当前和未来的场景：保留完整数据
                result.append(scene)
        return result

    def _serialize_expansions_minimal(self, expansions: List[SceneExpansion]) -> List[dict]:
        """
        最小化序列化展开结果（省略不需要的字段）

        省略的字段（SceneExpansion级别）：
        - original_text: 后续步骤不需要
        - scene_summary: 后续步骤不需要
        - importance: 后续步骤不需要

        保留的字段（PanelContent级别）：
        - 所有字段都保留，因为 build_panel_prompts 需要使用
        - 注意：is_key_panel 来自 PanelSlot（模板），不在 PanelContent 中
        """
        result = []
        for exp in expansions:
            result.append({
                "scene_id": exp.scene_id,
                "mood": exp.mood.value,
                "pages": [
                    {
                        "page_number": page.page_number,
                        "template_id": page.template.id,
                        "panels": [
                            {
                                "slot_id": panel.slot_id,
                                "content_description": panel.content_description,
                                "narrative_purpose": panel.narrative_purpose,
                                "characters": panel.characters,
                                "character_emotions": panel.character_emotions,
                                "composition": panel.composition,
                                "camera_angle": panel.camera_angle,
                                # 文字元素 - 基础字段
                                "dialogue": panel.dialogue,
                                "dialogue_speaker": panel.dialogue_speaker,
                                "narration": panel.narration,
                                "sound_effects": panel.sound_effects,
                                # 文字元素 - 扩展字段
                                "dialogue_bubble_type": panel.dialogue_bubble_type,
                                "dialogue_position": panel.dialogue_position,
                                "dialogue_emotion": panel.dialogue_emotion,
                                "narration_position": panel.narration_position,
                                "sound_effect_details": panel.sound_effect_details,
                                # 视觉指导
                                "key_visual_elements": panel.key_visual_elements,
                                "atmosphere": panel.atmosphere,
                                "lighting": panel.lighting,
                            }
                            for panel in page.panels
                        ]
                    }
                    for page in exp.pages
                ]
            })
        return result

    def _deserialize_expansions(self, data: List[dict]) -> List[SceneExpansion]:
        """
        从存储的字典列表反序列化展开结果

        注意：断点存储使用精简格式，SceneExpansion 级别的部分字段使用默认值
        """
        from .page_templates import get_template, PanelContent, PagePlan

        result = []
        for exp_data in data:
            pages = []
            for page_data in exp_data.get("pages", []):
                template = get_template(page_data["template_id"])
                panels = [
                    PanelContent(
                        slot_id=p["slot_id"],
                        content_description=p.get("content_description", ""),
                        narrative_purpose=p.get("narrative_purpose", ""),
                        characters=p.get("characters", []),
                        character_emotions=p.get("character_emotions", {}),
                        composition=p.get("composition", "medium shot"),
                        camera_angle=p.get("camera_angle", "eye level"),
                        # 文字元素 - 基础字段
                        dialogue=p.get("dialogue"),
                        dialogue_speaker=p.get("dialogue_speaker"),
                        narration=p.get("narration"),
                        sound_effects=p.get("sound_effects", []),
                        # 文字元素 - 扩展字段
                        dialogue_bubble_type=p.get("dialogue_bubble_type", "normal"),
                        dialogue_position=p.get("dialogue_position", "top-right"),
                        dialogue_emotion=p.get("dialogue_emotion", ""),
                        narration_position=p.get("narration_position", "top"),
                        sound_effect_details=p.get("sound_effect_details", []),
                        # 视觉指导
                        key_visual_elements=p.get("key_visual_elements", []),
                        atmosphere=p.get("atmosphere", ""),
                        lighting=p.get("lighting", ""),
                    )
                    for p in page_data.get("panels", [])
                ]
                pages.append(PagePlan(
                    page_number=page_data["page_number"],
                    template=template,
                    panels=panels,
                ))

            result.append(SceneExpansion(
                scene_id=exp_data["scene_id"],
                scene_summary=exp_data.get("scene_summary", ""),  # 精简格式可能没有
                original_text=exp_data.get("original_text", ""),  # 精简格式可能没有
                pages=pages,
                mood=SceneMood(exp_data.get("mood", "calm")),
                importance=exp_data.get("importance", "normal"),  # 精简格式可能没有
            ))
        return result

    async def _extract_scenes(
        self,
        content: str,
        min_scenes: int,
        max_scenes: int,
        user_id: Optional[int],
        dialogue_language: str = "chinese",
    ) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        从章节内容中提取场景

        Returns:
            (场景列表, 角色外观字典)
        """
        prompt = SCENE_EXTRACTION_PROMPT.format(
            content=content[:8000],  # 限制长度
            min_scenes=min_scenes,
            max_scenes=max_scenes,
            dialogue_language=dialogue_language,
        )

        response = await call_llm(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt="你是专业的漫画分镜师，擅长将文字叙事转化为视觉场景。",
            user_content=prompt,
            user_id=user_id,
        )

        data = parse_llm_json_safe(response)

        if not data or "scenes" not in data:
            logger.warning("场景提取失败，使用默认分割")
            return self._fallback_scene_extraction(content, min_scenes), {}

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

    def _fallback_scene_extraction(
        self,
        content: str,
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """
        回退的场景提取（简单分段）
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

    async def _save_result(
        self,
        project_id: str,
        chapter_number: int,
        result: MangaGenerationResult,
    ):
        """
        保存生成结果到数据库

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            result: 漫画生成结果
        """
        # 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            logger.warning(f"章节不存在: project={project_id}, chapter={chapter_number}")
            return

        # 将结果转为可存储的格式
        data = result.to_dict()

        # 获取当前选中的版本ID
        source_version_id = chapter.selected_version_id

        # 使用upsert保存
        await self.manga_prompt_repo.upsert(
            chapter_id=chapter.id,
            style=result.style,
            total_pages=result.get_total_pages(),
            total_panels=result.get_total_panels(),
            character_profiles=result.character_profiles,
            scenes=data["scenes"],
            panels=data["panels"],
            source_version_id=source_version_id,
        )

        logger.info(
            f"保存漫画分镜结果: project={project_id}, chapter={chapter_number}, "
            f"pages={result.get_total_pages()}, panels={result.get_total_panels()}"
        )

    async def get_result(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取已保存的生成结果

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            漫画分镜数据字典，不存在或未完成返回None
        """
        manga_prompt = await self.manga_prompt_repo.get_by_project_and_chapter(
            project_id, chapter_number
        )

        if not manga_prompt:
            return None

        # 确保是已完成的结果（有panels数据且状态为completed）
        # 如果只有断点数据但没有panels，不认为是完成的结果
        if not manga_prompt.panels or manga_prompt.generation_status != "completed":
            return None

        # 转换为API响应格式
        return {
            "chapter_number": chapter_number,
            "style": manga_prompt.style,
            "character_profiles": manga_prompt.character_profiles or {},
            "total_pages": manga_prompt.total_pages,
            "total_panels": manga_prompt.total_panels,
            "scenes": manga_prompt.scenes or [],
            "panels": manga_prompt.panels or [],
            "created_at": manga_prompt.created_at.isoformat() if manga_prompt.created_at else None,
        }

    async def delete_result(
        self,
        project_id: str,
        chapter_number: int,
    ) -> bool:
        """
        删除生成结果

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            是否删除成功
        """
        # 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            return False

        # 删除漫画提示词
        deleted = await self.manga_prompt_repo.delete_by_chapter_id(chapter.id)

        if deleted:
            logger.info(f"删除漫画分镜: project={project_id}, chapter={chapter_number}")

        return deleted


# ============================================================
# 便捷函数
# ============================================================

async def generate_manga_prompts(
    session: AsyncSession,
    llm_service: LLMService,
    project_id: str,
    chapter_number: int,
    chapter_content: str,
    style: str = MangaStyle.MANGA,
    user_id: Optional[int] = None,
) -> MangaGenerationResult:
    """
    便捷函数：生成漫画分镜

    Args:
        session: 数据库会话
        llm_service: LLM服务
        project_id: 项目ID
        chapter_number: 章节号
        chapter_content: 章节内容
        style: 漫画风格
        user_id: 用户ID

    Returns:
        漫画生成结果
    """
    service = MangaPromptServiceV2(session, llm_service)
    return await service.generate(
        project_id=project_id,
        chapter_number=chapter_number,
        chapter_content=chapter_content,
        style=style,
        user_id=user_id,
    )
