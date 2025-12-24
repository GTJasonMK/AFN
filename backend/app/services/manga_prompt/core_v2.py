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
from app.services.character_portrait_service import CharacterPortraitService
from app.utils.json_utils import parse_llm_json_safe
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.manga_prompt_repository import MangaPromptRepository
from app.repositories.character_portrait_repository import CharacterPortraitRepository

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

## 角色外观描述要求（极其重要）
character_profiles 必须包含本章节中出现的**所有角色**的外观描述，包括：
- 主要角色（主角、重要配角）
- 次要角色（路人、店员、士兵、侍女等）
- 群体角色（如"士兵A"、"村民B"等需要分别描述）

每个角色的外观描述必须包含：
- 性别、大致年龄
- 发型、发色
- 服装特征
- 体型特征（如适用）
- 任何显著的视觉特征（如伤疤、饰品等）

示例：
```json
"character_profiles": {{
  "李明": "young man in his 20s, short black hair, wearing modern casual clothes, slim build",
  "王大妈": "elderly woman in her 60s, gray hair in a bun, wearing traditional Chinese dress, kind face",
  "店员": "young woman, brown ponytail, wearing cafe uniform with apron, friendly appearance",
  "士兵A": "muscular man, short military haircut, wearing armor, stern expression",
  "士兵B": "thin young man, helmet covering hair, wearing armor, nervous expression"
}}
```

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
    "角色名": "外观描述（用于AI绘图，英文，包含性别、年龄、发型、服装、体型等）"
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

        # 子服务（传递 prompt_service 以支持可配置提示词）
        self.expansion_service = SceneExpansionService(llm_service, prompt_service)

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
        auto_generate_portraits: bool = False,  # 是否自动生成缺失的立绘
        use_dynamic_layout: bool = True,  # 是否使用LLM动态布局
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
            auto_generate_portraits: 是否自动为缺失立绘的角色生成立绘
            use_dynamic_layout: 是否使用LLM动态布局（True=动态布局，False=硬编码模板）

        Returns:
            漫画生成结果
        """
        logger.info(f"开始生成漫画分镜: 项目={project_id}, 章节={chapter_number}, "
                   f"语言={dialogue_language}, 动态布局={use_dynamic_layout}")

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

        # 初始化角色立绘（可能会在后续步骤中更新）
        final_character_portraits = dict(character_portraits) if character_portraits else {}

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

                # 恢复布局历史以保持页面布局连续性
                if expansions:
                    self.expansion_service.restore_previous_pages_from_expansions(expansions)

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

            # 步骤1.5：自动生成缺失立绘（如果启用）
            if auto_generate_portraits and character_profiles and user_id:
                logger.info("步骤1.5: 自动生成缺失的角色立绘")

                # 保存状态：正在生成立绘
                if chapter_id:
                    await self._save_checkpoint(
                        chapter_id, "generating_portraits",
                        {"stage": "generating_portraits", "current": 0, "total": len(character_profiles),
                         "message": "正在为缺失立绘的角色生成立绘..."},
                        {"scenes_data": scenes_data, "character_profiles": character_profiles},
                        style, source_version_id
                    )

                # 调用角色立绘服务自动生成缺失立绘
                portrait_service = CharacterPortraitService(self.session)
                generated_portraits = await portrait_service.auto_generate_missing_portraits(
                    user_id=user_id,
                    project_id=project_id,
                    character_profiles=character_profiles,
                    style="anime",  # 使用anime风格，与漫画风格最匹配
                    exclude_existing=True,
                )

                # 更新角色立绘映射
                if generated_portraits:
                    from app.core.config import settings
                    for name, portrait in generated_portraits.items():
                        if portrait.image_path:
                            # 使用完整路径
                            final_character_portraits[name] = str(
                                settings.generated_images_dir / portrait.image_path
                            )
                    logger.info(f"自动生成了 {len(generated_portraits)} 个角色的立绘")

                    # 提交立绘生成的事务
                    await self.session.commit()

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
            use_dynamic_layout=use_dynamic_layout,
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
            character_portraits=final_character_portraits,
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
            dialogue_language=dialogue_language,  # 传递语言设置
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
        use_dynamic_layout: bool = True,
    ) -> List[SceneExpansion]:
        """
        展开场景并在每个场景完成后保存断点

        Args:
            scenes_data: 场景数据列表
            start_index: 开始索引
            chapter_id: 章节ID
            character_profiles: 角色描述
            style: 漫画风格
            source_version_id: 来源版本ID
            existing_expansions: 已完成的展开结果
            user_id: 用户ID
            dialogue_language: 对话/音效语言
            use_dynamic_layout: 是否使用LLM动态布局
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
                use_dynamic_layout=use_dynamic_layout,
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

        对于动态生成的模板（ID以llm_dynamic_开头），额外保存槽位信息以便恢复
        """
        result = []
        for exp in expansions:
            result.append({
                "scene_id": exp.scene_id,
                "mood": exp.mood.value,
                "pages": [
                    self._serialize_page_plan(page)
                    for page in exp.pages
                ]
            })
        return result

    def _serialize_page_plan(self, page) -> dict:
        """序列化单个页面规划"""
        template_id = page.template.id if page.template else "unknown"

        page_data = {
            "page_number": page.page_number,
            "template_id": template_id,
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
                    # LLM生成的提示词（必须保留，否则恢复后会触发回退逻辑）
                    "prompt_en": panel.prompt_en,
                    "negative_prompt": panel.negative_prompt,
                }
                for panel in page.panels
            ]
        }

        # 对于动态模板，保存完整的槽位信息以便精确恢复
        if template_id.startswith("llm_dynamic_") and page.template:
            page_data["template_slots"] = [
                {
                    "slot_id": slot.slot_id,
                    "x": slot.x,
                    "y": slot.y,
                    "width": slot.width,
                    "height": slot.height,
                    "shape": slot.shape.value if hasattr(slot.shape, 'value') else str(slot.shape),
                    "purpose": slot.purpose.value if hasattr(slot.purpose, 'value') else str(slot.purpose),
                    "suggested_composition": slot.suggested_composition,
                    "suggested_angle": slot.suggested_angle,
                    "is_key_panel": slot.is_key_panel,
                }
                for slot in page.template.panel_slots
            ]
            # 保存模板名称
            page_data["template_name_zh"] = page.template.name_zh

        return page_data

    def _deserialize_expansions(self, data: List[dict]) -> List[SceneExpansion]:
        """
        从存储的字典列表反序列化展开结果

        注意：断点存储使用精简格式，SceneExpansion 级别的部分字段使用默认值
        对于动态生成的模板（ID以llm_dynamic_开头），优先使用保存的槽位信息恢复
        """
        from .page_templates import (
            get_template, PanelContent, PagePlan, PageTemplate, PanelSlot,
            PanelPurpose, PanelShape, SceneMood, TEMPLATE_STANDARD_THREE_TIER
        )

        result = []
        for exp_data in data:
            pages = []
            for page_data in exp_data.get("pages", []):
                template_id = page_data.get("template_id", "")
                template = get_template(template_id)

                # 如果找不到模板（可能是动态生成的模板），尝试从保存的数据恢复
                if template is None:
                    template = self._restore_template_from_page_data(
                        page_data, template_id, PanelSlot, PanelPurpose, PanelShape,
                        PageTemplate, SceneMood, TEMPLATE_STANDARD_THREE_TIER
                    )

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
                        # LLM生成的提示词（从断点恢复时需要）
                        prompt_en=p.get("prompt_en", ""),
                        negative_prompt=p.get("negative_prompt", ""),
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

    def _restore_template_from_page_data(
        self,
        page_data: dict,
        template_id: str,
        PanelSlot,
        PanelPurpose,
        PanelShape,
        PageTemplate,
        SceneMood,
        TEMPLATE_STANDARD_THREE_TIER,
    ):
        """
        从页面数据恢复模板

        优先使用保存的 template_slots 信息，否则从面板数据推断
        """
        # 优先使用保存的槽位信息（动态模板）
        template_slots = page_data.get("template_slots")
        if template_slots:
            logger.debug(f"使用保存的槽位信息恢复模板 {template_id}")
            panel_slots = []
            for slot_data in template_slots:
                # 解析枚举值
                try:
                    purpose = PanelPurpose(slot_data.get("purpose", "action"))
                except ValueError:
                    purpose = PanelPurpose.ACTION

                try:
                    shape = PanelShape(slot_data.get("shape", "rectangle"))
                except ValueError:
                    shape = PanelShape.RECTANGLE

                slot = PanelSlot(
                    slot_id=slot_data.get("slot_id", 1),
                    x=slot_data.get("x", 0),
                    y=slot_data.get("y", 0),
                    width=slot_data.get("width", 1.0),
                    height=slot_data.get("height", 0.5),
                    shape=shape,
                    purpose=purpose,
                    suggested_composition=slot_data.get("suggested_composition", "medium shot"),
                    suggested_angle=slot_data.get("suggested_angle", "eye level"),
                    is_key_panel=slot_data.get("is_key_panel", False),
                )
                panel_slots.append(slot)

            return PageTemplate(
                id=template_id,
                name="Restored Dynamic Template",
                name_zh=page_data.get("template_name_zh", "恢复的动态模板"),
                description="从断点数据精确恢复的动态模板",
                suitable_moods=[SceneMood.CALM],
                panel_slots=panel_slots,
            )

        # 回退：从面板数据推断槽位
        panels_data = page_data.get("panels", [])
        if panels_data:
            logger.debug(f"模板 {template_id} 不在注册表中，从面板数据推断槽位")
            panel_slots = []
            for idx, p in enumerate(panels_data):
                slot = PanelSlot(
                    slot_id=p.get("slot_id", idx + 1),
                    x=0,
                    y=idx * (1.0 / len(panels_data)),
                    width=1.0,
                    height=1.0 / len(panels_data),
                    purpose=PanelPurpose.ACTION,
                    suggested_composition=p.get("composition", "medium shot"),
                    suggested_angle=p.get("camera_angle", "eye level"),
                )
                panel_slots.append(slot)

            return PageTemplate(
                id=template_id or f"restored_{page_data.get('page_number', 1)}",
                name="Restored Template",
                name_zh="恢复的模板",
                description="从断点数据恢复的临时模板",
                suitable_moods=[SceneMood.CALM],
                panel_slots=panel_slots,
            )

        # 最后回退：使用标准模板
        return TEMPLATE_STANDARD_THREE_TIER

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
    prompt_service: Optional[PromptService] = None,
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
        prompt_service: 提示词服务（可选，用于加载可配置提示词）

    Returns:
        漫画生成结果
    """
    service = MangaPromptServiceV2(session, llm_service, prompt_service)
    return await service.generate(
        project_id=project_id,
        chapter_number=chapter_number,
        chapter_content=chapter_content,
        style=style,
        user_id=user_id,
    )
