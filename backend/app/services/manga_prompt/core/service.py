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

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.image_generation.service import ImageGenerationService
from app.services.character_portrait_service import CharacterPortraitService
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.manga_prompt_repository import MangaPromptRepository

from ..page_templates import SceneExpansion
from ..scene_expansion import SceneExpansionService
from ..panel_prompt import PanelPromptBuilder

from .models import MangaStyle, MangaGenerationResult
from .scene_extractor import SceneExtractor
from .checkpoint_manager import CheckpointManager
from .result_persistence import ResultPersistence

logger = logging.getLogger(__name__)


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
        self.expansion_service = SceneExpansionService(llm_service, prompt_service)

        # 子组件
        self._scene_extractor = SceneExtractor(llm_service, prompt_service)
        self._checkpoint_manager = CheckpointManager(session, self.manga_prompt_repo)
        self._result_persistence = ResultPersistence(
            session, self.chapter_repo, self.manga_prompt_repo, self.image_service
        )

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
            checkpoint = await self._checkpoint_manager.get_checkpoint(
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
                expansions = self._checkpoint_manager.deserialize_expansions(completed_expansions_data)
                logger.info(f"从断点恢复: 已完成 {len(expansions)} 个场景展开")

                # 恢复布局历史以保持页面布局连续性
                if expansions:
                    self.expansion_service.restore_previous_pages_from_expansions(expansions)

        # 步骤1：提取场景（如果没有从断点恢复）
        if scenes_data is None:
            logger.info("步骤1: 提取场景")

            # 清理旧数据
            await self._result_persistence.cleanup_old_data(project_id, chapter_number, chapter_id)

            # 保存状态：正在提取场景
            if chapter_id:
                await self._checkpoint_manager.save_checkpoint(
                    chapter_id, "extracting",
                    {"stage": "extracting", "current": 0, "total": 0, "message": "正在提取场景..."},
                    {}, style, source_version_id
                )

            scenes_data, character_profiles = await self._scene_extractor.extract_scenes(
                content=chapter_content,
                min_scenes=min_scenes,
                max_scenes=max_scenes,
                user_id=user_id,
                dialogue_language=dialogue_language,
            )
            logger.info(f"提取到 {len(scenes_data)} 个场景")

            # 步骤1.5：自动生成缺失立绘（如果启用）
            if auto_generate_portraits and character_profiles and user_id:
                await self._auto_generate_portraits(
                    user_id, project_id, chapter_id, character_profiles,
                    scenes_data, style, source_version_id, final_character_portraits
                )

            # 保存断点：场景提取完成
            if chapter_id:
                await self._checkpoint_manager.save_checkpoint(
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

        # 保存断点状态
        if chapter_id:
            await self._checkpoint_manager.save_checkpoint(
                chapter_id, "prompt_building",
                {"stage": "prompt_building", "current": 0, "total": total_panels,
                 "message": f"正在为 {total_panels} 个画格生成提示词..."},
                {"scenes_data": scenes_data,
                 "character_profiles": character_profiles,
                 "completed_expansions": self._checkpoint_manager.serialize_expansions_minimal(expansions),
                 "current_scene_index": len(scenes_data)},
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
            dialogue_language=dialogue_language,
        )

        # 步骤4：保存结果
        logger.info("步骤4: 保存结果")
        await self._result_persistence.save_result(project_id, chapter_number, result)

        logger.info(
            f"漫画分镜生成完成: {result.get_total_pages()}页, "
            f"{result.get_total_panels()}格"
        )

        return result

    async def _auto_generate_portraits(
        self,
        user_id: int,
        project_id: str,
        chapter_id: Optional[int],
        character_profiles: Dict[str, str],
        scenes_data: List[Dict[str, Any]],
        style: str,
        source_version_id: Optional[int],
        final_character_portraits: Dict[str, str],
    ):
        """自动生成缺失的角色立绘"""
        logger.info("步骤1.5: 自动生成缺失的角色立绘")

        # 保存状态：正在生成立绘
        if chapter_id:
            await self._checkpoint_manager.save_checkpoint(
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
            style="anime",
            exclude_existing=True,
        )

        # 更新角色立绘映射
        if generated_portraits:
            from app.core.config import settings
            for name, portrait in generated_portraits.items():
                if portrait.image_path:
                    final_character_portraits[name] = str(
                        settings.generated_images_dir / portrait.image_path
                    )
            logger.info(f"自动生成了 {len(generated_portraits)} 个角色的立绘")
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
        """展开场景并在每个场景完成后保存断点"""
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

            # 每个场景完成后保存断点
            if chapter_id:
                optimized_scenes = self._checkpoint_manager.optimize_scenes_for_checkpoint(
                    scenes_data, i + 1
                )
                await self._checkpoint_manager.save_checkpoint(
                    chapter_id, "expanding",
                    {"stage": "expanding", "current": i + 1, "total": total_scenes,
                     "message": f"已展开 {i + 1}/{total_scenes} 个场景"},
                    {"scenes_data": optimized_scenes,
                     "character_profiles": character_profiles,
                     "completed_expansions": self._checkpoint_manager.serialize_expansions_minimal(expansions),
                     "current_scene_index": i + 1},
                    style, source_version_id,
                )

        return expansions

    # 向后兼容的方法代理
    async def _save_checkpoint(self, *args, **kwargs):
        """向后兼容：代理到 CheckpointManager"""
        return await self._checkpoint_manager.save_checkpoint(*args, **kwargs)

    async def _cleanup_old_data(self, *args, **kwargs):
        """向后兼容：代理到 ResultPersistence"""
        return await self._result_persistence.cleanup_old_data(*args, **kwargs)

    async def _extract_scenes(self, *args, **kwargs):
        """向后兼容：代理到 SceneExtractor"""
        return await self._scene_extractor.extract_scenes(*args, **kwargs)

    def _fallback_scene_extraction(self, *args, **kwargs):
        """向后兼容：代理到 SceneExtractor"""
        return self._scene_extractor.fallback_scene_extraction(*args, **kwargs)

    async def _save_result(self, *args, **kwargs):
        """向后兼容：代理到 ResultPersistence"""
        return await self._result_persistence.save_result(*args, **kwargs)

    async def get_result(self, project_id: str, chapter_number: int):
        """获取已保存的生成结果"""
        return await self._result_persistence.get_result(project_id, chapter_number)

    async def delete_result(self, project_id: str, chapter_number: int) -> bool:
        """删除生成结果"""
        return await self._result_persistence.delete_result(project_id, chapter_number)

    def _optimize_scenes_for_checkpoint(self, *args, **kwargs):
        """向后兼容：代理到 CheckpointManager"""
        return self._checkpoint_manager.optimize_scenes_for_checkpoint(*args, **kwargs)

    def _serialize_expansions_minimal(self, *args, **kwargs):
        """向后兼容：代理到 CheckpointManager"""
        return self._checkpoint_manager.serialize_expansions_minimal(*args, **kwargs)

    def _serialize_page_plan(self, *args, **kwargs):
        """向后兼容：代理到 CheckpointManager"""
        return self._checkpoint_manager._serialize_page_plan(*args, **kwargs)

    def _deserialize_expansions(self, *args, **kwargs):
        """向后兼容：代理到 CheckpointManager"""
        return self._checkpoint_manager.deserialize_expansions(*args, **kwargs)

    def _restore_template_from_page_data(self, *args, **kwargs):
        """向后兼容：代理到 CheckpointManager"""
        return self._checkpoint_manager._restore_template_from_page_data(*args, **kwargs)


# 便捷函数
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


__all__ = [
    "MangaPromptServiceV2",
    "generate_manga_prompts",
]
