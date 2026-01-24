"""
漫画提示词服务 V2

基于页面驱动的漫画分镜生成服务。

核心流程：
1. 信息提取 - 从章节内容提取结构化信息（角色、对话、事件、场景）
2. 页面规划 - 全局页面规划，确定页数和事件分配
3. 分镜设计 - 为每页设计详细分镜
4. 提示词构建 - 生成AI绘图提示词
"""

import logging
import time
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.services.image_generation.service import ImageGenerationService
from app.services.character_portrait_service import CharacterPortraitService
from app.repositories.chapter_repository import ChapterRepository
from app.repositories.manga_prompt_repository import MangaPromptRepository
from app.exceptions import GenerationCancelledError

from ..extraction import ChapterInfoExtractor, ChapterInfo
from ..planning import PagePlanner, PagePlanResult
from ..storyboard import StoryboardDesigner, StoryboardResult
from ..prompt_builder import PromptBuilder, MangaPromptResult, PagePromptGenerator

from .models import MangaStyle
from .checkpoint_manager import CheckpointManager
from .result_persistence import ResultPersistence

logger = logging.getLogger(__name__)


class MangaPromptServiceV2:
    """
    漫画提示词服务 V2

    基于页面驱动的4步流水线架构：
    提取 -> 规划 -> 分镜 -> 提示词
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

        # 核心流水线组件
        self._extractor = ChapterInfoExtractor(llm_service, prompt_service)
        self._planner = PagePlanner(llm_service, prompt_service)
        self._designer = StoryboardDesigner(llm_service, prompt_service)

        # 辅助组件
        self._checkpoint_manager = CheckpointManager(session, self.manga_prompt_repo)
        self._result_persistence = ResultPersistence(
            session, self.manga_prompt_repo, self.image_service
        )

        # 取消状态缓存（减少数据库查询）
        # 格式: {chapter_id: (is_cancelled, timestamp)}
        self._cancel_cache: Dict[int, tuple] = {}
        self._cancel_cache_ttl = 2.0  # 缓存有效期（秒）

    async def _check_cancelled(self, chapter_id: int) -> bool:
        """检查生成任务是否已被取消

        使用短期缓存减少数据库查询频率。

        Args:
            chapter_id: 章节ID

        Returns:
            是否已取消
        """
        current_time = time.time()

        # 检查缓存是否有效
        if chapter_id in self._cancel_cache:
            cached_result, cached_time = self._cancel_cache[chapter_id]
            if current_time - cached_time < self._cancel_cache_ttl:
                return cached_result

        # 缓存过期或不存在，查询数据库
        manga_prompt = await self.manga_prompt_repo.get_by_chapter_id(chapter_id)
        is_cancelled = manga_prompt and manga_prompt.generation_status == "cancelled"

        # 更新缓存
        self._cancel_cache[chapter_id] = (is_cancelled, current_time)

        return is_cancelled

    async def _raise_if_cancelled(self, chapter_id: int):
        """如果任务已取消则抛出异常

        Args:
            chapter_id: 章节ID

        Raises:
            GenerationCancelledError: 如果任务已取消
        """
        if await self._check_cancelled(chapter_id):
            raise GenerationCancelledError("漫画分镜生成")

    async def generate(
        self,
        project_id: str,
        chapter_number: int,
        chapter_content: str,
        style: str = MangaStyle.MANGA,
        min_pages: int = 8,
        max_pages: int = 15,
        user_id: Optional[int] = None,
        resume: bool = True,
        dialogue_language: str = "chinese",
        character_portraits: Optional[Dict[str, str]] = None,
        auto_generate_portraits: bool = False,
        start_from_stage: Optional[str] = None,
        auto_generate_page_images: bool = False,
        page_prompt_concurrency: int = 5,
    ) -> MangaPromptResult:
        """
        生成漫画分镜（支持细粒度断点续传）

        断点保存策略：
        - 信息提取阶段：每完成一个步骤（角色/对话/场景/物品）保存
        - 页面规划阶段：完成后保存
        - 分镜设计阶段：每完成一页保存

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            chapter_content: 章节内容
            style: 漫画风格
            min_pages: 最少页数
            max_pages: 最多页数
            user_id: 用户ID
            resume: 是否从断点恢复
            dialogue_language: 对话语言（chinese/japanese/english/korean）
            character_portraits: 角色立绘路径字典
            auto_generate_portraits: 是否自动生成缺失立绘
            start_from_stage: 指定从哪个阶段开始（extraction/planning/storyboard/prompt_building）
            auto_generate_page_images: 是否在分镜生成后自动生成所有整页图片
            page_prompt_concurrency: 整页提示词LLM生成的并发数（1-20）

        Returns:
            MangaPromptResult: 漫画提示词结果
        """
        logger.info(
            f"开始生成漫画分镜: 项目={project_id}, 章节={chapter_number}, "
            f"页数范围={min_pages}-{max_pages}, 语言={dialogue_language}"
        )

        # 清除取消状态缓存，确保使用最新的数据库状态
        # 这对于 cancelled 状态被 API router 重置的情况尤其重要
        self._cancel_cache.clear()

        # 获取章节信息
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        chapter_id = chapter.id if chapter else None
        source_version_id = chapter.selected_version_id if chapter else None

        # 检查断点
        checkpoint = None
        cp_data = {}
        if resume and chapter_id:
            checkpoint = await self._checkpoint_manager.get_checkpoint(
                project_id, chapter_number
            )
            if checkpoint:
                cp_data = checkpoint.get("checkpoint_data", {}) or {}
                logger.debug(
                    f"发现断点: status={checkpoint['status']}, "
                    f"已有数据: extraction_step1={bool(cp_data.get('extraction_step1'))}, "
                    f"chapter_info={bool(cp_data.get('chapter_info'))}, "
                    f"page_plan={bool(cp_data.get('page_plan'))}, "
                    f"designed_pages={len(cp_data.get('designed_pages', []))}"
                )

        # 如果用户指定了起始阶段，尝试从已完成的结果中恢复数据
        # 注意：即使有断点数据，也需要检查数据库中是否有完整结果（用于 page_prompt_building 等阶段）
        if start_from_stage and chapter_id:
            existing_manga = await self.manga_prompt_repo.get_by_chapter_id(chapter_id)
            if existing_manga:
                # 从 analysis_data 恢复数据（如果断点数据中没有）
                if existing_manga.analysis_data:
                    analysis = existing_manga.analysis_data
                    if not cp_data.get("chapter_info") and analysis.get("chapter_info"):
                        cp_data["chapter_info"] = analysis["chapter_info"]
                    if not cp_data.get("page_plan") and analysis.get("page_plan"):
                        cp_data["page_plan"] = analysis["page_plan"]
                # 如果已有完成的 storyboard 数据（从 panels 推断）
                if existing_manga.panels and existing_manga.scenes:
                    # 标记已有完整数据
                    cp_data["_has_completed_result"] = True
                logger.debug(
                    f"从已完成的结果恢复数据: "
                    f"chapter_info={bool(cp_data.get('chapter_info'))}, "
                    f"page_plan={bool(cp_data.get('page_plan'))}, "
                    f"has_completed_result={cp_data.get('_has_completed_result', False)}"
                )

        # 初始化变量
        chapter_info: Optional[ChapterInfo] = None
        page_plan: Optional[PagePlanResult] = None
        storyboard: Optional[StoryboardResult] = None
        final_portraits = dict(character_portraits) if character_portraits else {}

        # 判断起始阶段
        start_stage = self._determine_start_stage(cp_data, start_from_stage)
        logger.debug(f"用户指定阶段: {start_from_stage}, 实际起始阶段: {start_stage}")

        # 如果用户指定了起始阶段，验证前置数据是否存在
        if start_from_stage:
            validation_error = self._validate_start_stage(start_from_stage, cp_data)
            if validation_error:
                raise ValueError(validation_error)
            # 清理指定阶段之后的数据，强制重新生成
            cp_data = self._clear_data_from_stage(cp_data, start_from_stage)

            # 根据起始阶段清理相关图片
            # - extraction/planning/storyboard/prompt_building: 删除所有图片
            # - page_prompt_building: 只删除整页图片（panel图片保留）
            await self._result_persistence.cleanup_images_for_stage(
                project_id, chapter_number, start_from_stage
            )

        # ========== 特殊处理：仅重新生成整页提示词 ==========
        if start_stage == "page_prompt_building":
            logger.info("特殊阶段: 仅重新生成整页提示词")
            return await self._regenerate_page_prompts_only(
                project_id=project_id,
                chapter_number=chapter_number,
                chapter_id=chapter_id,
                style=style,
                character_portraits=character_portraits,
                source_version_id=source_version_id,
                user_id=user_id,
                page_prompt_concurrency=page_prompt_concurrency,
            )

        # 如果是从头开始，清理旧数据
        if start_stage == "extraction":
            await self._result_persistence.cleanup_old_data(
                project_id, chapter_number, chapter_id
            )

        # 定义断点保存回调（支持可选的 analysis_data）
        async def save_checkpoint_callback(
            status: str,
            progress: dict,
            data: dict,
            analysis_data: dict = None
        ):
            if chapter_id:
                # 先检查是否已取消
                await self._raise_if_cancelled(chapter_id)
                await self._checkpoint_manager.save_checkpoint(
                    chapter_id, status, progress, data, style, source_version_id,
                    analysis_data=analysis_data
                )

        # ========== 步骤1：信息提取（支持分步断点） ==========
        if start_stage == "extraction" or not cp_data.get("chapter_info"):
            logger.info("步骤1: 提取章节信息")

            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)

            # 立即保存初始状态，让轮询能看到"正在提取..."
            await save_checkpoint_callback(
                "extracting",
                {
                    "stage": "extracting",
                    "current": 0,
                    "total": 4,
                    "message": "正在提取章节信息..."
                },
                cp_data
            )

            # 定义提取步骤完成回调
            async def on_extraction_step_complete(step: int, extraction_data: dict):
                step_labels = {
                    1: "提取角色和事件",
                    2: "提取对话",
                    3: "提取场景",
                    4: "提取物品和摘要"
                }
                # 每一步完成时都构建并保存当前已提取的 analysis_data
                # 这样前端可以实时看到提取进度
                analysis_data_to_save = self._build_partial_analysis_data(extraction_data, step)
                await save_checkpoint_callback(
                    "extracting",
                    {
                        "stage": "extracting",
                        "current": step,
                        "total": 4,
                        "message": f"完成: {step_labels.get(step, '未知步骤')}"
                    },
                    extraction_data,
                    analysis_data=analysis_data_to_save
                )

            # 使用支持断点的提取方法
            chapter_info, cp_data = await self._extractor.extract_with_checkpoint(
                chapter_content=chapter_content,
                user_id=user_id,
                dialogue_language=dialogue_language,
                checkpoint_data=cp_data,
                on_step_complete=on_extraction_step_complete,
            )

            logger.info(
                f"提取完成: {len(chapter_info.events)} 事件, "
                f"{len(chapter_info.characters)} 角色, "
                f"{len(chapter_info.dialogues)} 对话"
            )

            # 自动生成立绘
            if auto_generate_portraits and chapter_info.characters and user_id:
                await self._auto_generate_portraits(
                    user_id, project_id, chapter_id, chapter_info,
                    style, source_version_id, final_portraits
                )
        else:
            # 从断点恢复 chapter_info
            chapter_info = ChapterInfo.from_dict(cp_data["chapter_info"])
            logger.debug("从断点恢复 chapter_info")

        # ========== 步骤2：页面规划 ==========
        if not cp_data.get("page_plan"):
            logger.info("步骤2: 全局页面规划")

            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)

            await save_checkpoint_callback(
                "planning",
                {"stage": "planning", "current": 1, "total": 4, "message": "正在进行页面规划..."},
                cp_data
            )

            page_plan = await self._planner.plan(
                chapter_info=chapter_info,
                min_pages=min_pages,
                max_pages=max_pages,
                user_id=user_id,
            )

            logger.info(
                f"规划完成: {page_plan.total_pages} 页"
            )

            # 保存断点（同时保存 analysis_data，包含 chapter_info 和 page_plan）
            cp_data["page_plan"] = page_plan.to_dict()
            analysis_data_with_plan = {
                "chapter_info": chapter_info.to_dict(),
                "page_plan": page_plan.to_dict()
            }
            await save_checkpoint_callback(
                "storyboard",
                {"stage": "storyboard", "current": 2, "total": 4,
                 "message": f"准备设计 {page_plan.total_pages} 页分镜..."},
                cp_data,
                analysis_data=analysis_data_with_plan
            )
        else:
            # 从断点恢复 page_plan
            page_plan = PagePlanResult.from_dict(cp_data["page_plan"])
            logger.debug(f"从断点恢复 page_plan: {page_plan.total_pages} 页")

        # ========== 步骤3：分镜设计（支持每页断点 + 增量保存） ==========
        # 检查是否需要从已完成结果恢复 storyboard（用于 prompt_building 阶段）
        need_storyboard_from_db = (
            start_from_stage == "prompt_building" and
            cp_data.get("_has_completed_result") and
            not cp_data.get("storyboard")
        )

        if need_storyboard_from_db:
            # 从数据库恢复 storyboard 数据
            logger.debug("从已完成结果恢复 storyboard 数据")
            existing_manga = await self.manga_prompt_repo.get_by_chapter_id(chapter_id)
            if existing_manga and existing_manga.panels and existing_manga.scenes:
                # 从 panels 和 scenes 重建 storyboard
                storyboard = self._rebuild_storyboard_from_db(existing_manga, page_plan)
                logger.debug(f"恢复 storyboard: {storyboard.total_pages} 页, {storyboard.total_panels} 格")
            else:
                # 没有足够的数据，需要重新设计
                need_storyboard_from_db = False
                logger.warning("无法从数据库恢复 storyboard，将重新设计")

        if not cp_data.get("storyboard") and not need_storyboard_from_db:
            logger.info("步骤3: 分镜设计")

            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)

            # 获取已设计的页面数据
            designed_pages_data = cp_data.get("designed_pages", [])

            # 准备提示词构建器（用于增量构建）
            character_profiles_for_builder = {}
            for name, char in chapter_info.characters.items():
                if char.appearance:
                    character_profiles_for_builder[name] = char.appearance

            incremental_builder = PromptBuilder(
                style=style,
                character_profiles=character_profiles_for_builder,
                character_portraits=final_portraits,
            )

            # 已完成的提示词页面（用于增量保存）
            completed_prompt_pages = cp_data.get("completed_prompt_pages", [])

            # 定义每页完成回调（增量构建提示词并保存）
            async def on_page_design_complete(page_number: int, all_pages_data: list):
                nonlocal completed_prompt_pages

                # 检查是否已取消
                if chapter_id:
                    await self._raise_if_cancelled(chapter_id)

                cp_data["designed_pages"] = all_pages_data
                completed = len(all_pages_data)
                total = page_plan.total_pages

                # 获取刚完成的页面分镜
                latest_page_data = all_pages_data[-1] if all_pages_data else None
                if latest_page_data:
                    # 立即为该页构建提示词
                    from ..storyboard import PageStoryboard
                    page_storyboard = PageStoryboard.from_dict(latest_page_data)
                    page_prompt = incremental_builder._build_page_prompts(
                        page_storyboard, chapter_info
                    )
                    completed_prompt_pages.append(page_prompt.to_dict())
                    cp_data["completed_prompt_pages"] = completed_prompt_pages

                    # 增量保存到数据库
                    await self._save_incremental_result(
                        project_id=project_id,
                        chapter_number=chapter_number,
                        style=style,
                        character_profiles=character_profiles_for_builder,
                        completed_pages=completed_prompt_pages,
                        total_pages=total,
                        chapter_info=chapter_info,
                        page_plan=page_plan,
                        is_complete=False,
                        source_version_id=source_version_id,
                        dialogue_language=dialogue_language,
                    )

                await save_checkpoint_callback(
                    "storyboard",
                    {
                        "stage": "storyboard",
                        "current": completed,
                        "total": total,
                        "message": f"已设计 {completed}/{total} 页 (第{page_number}页完成)"
                    },
                    cp_data
                )

            # 使用支持断点的设计方法
            storyboard, designed_pages_data = await self._designer.design_all_pages_with_checkpoint(
                page_plans=page_plan.pages,
                chapter_info=chapter_info,
                user_id=user_id,
                designed_pages_data=designed_pages_data,
                on_page_complete=on_page_design_complete,
            )

            logger.info(
                f"分镜设计完成: {storyboard.total_pages} 页, "
                f"{storyboard.total_panels} 格"
            )

            # 保存完整的分镜数据
            cp_data["storyboard"] = storyboard.to_dict()
            cp_data.pop("designed_pages", None)  # 清理中间数据
            cp_data.pop("completed_prompt_pages", None)  # 清理中间数据
        elif cp_data.get("storyboard"):
            # 从断点恢复 storyboard
            storyboard = StoryboardResult.from_dict(cp_data["storyboard"])
            logger.debug(f"从断点恢复 storyboard: {storyboard.total_pages} 页, {storyboard.total_panels} 格")
        # else: storyboard 已经在前面从数据库恢复了（need_storyboard_from_db=True）

        # ========== 步骤4：提示词构建（画格提示词 + LLM生成整页提示词） ==========
        logger.info("步骤4: 构建提示词")

        # 检查是否已取消
        if chapter_id:
            await self._raise_if_cancelled(chapter_id)

        # 确保 analysis_data 包含完整的 chapter_info 和 page_plan
        analysis_data_for_prompt = {
            "chapter_info": chapter_info.to_dict(),
            "page_plan": page_plan.to_dict()
        }

        await save_checkpoint_callback(
            "prompt_building",
            {"stage": "prompt_building", "current": 3, "total": 5, "message": "正在生成画格提示词..."},
            cp_data,
            analysis_data=analysis_data_for_prompt
        )

        # 收集角色外观描述
        character_profiles = {}
        for name, char in chapter_info.characters.items():
            if char.appearance:
                character_profiles[name] = char.appearance

        # 4.1 首先构建画格级提示词（不生成整页提示词）
        prompt_builder = PromptBuilder(
            style=style,
            character_profiles=character_profiles,
            character_portraits=final_portraits,
        )

        result = prompt_builder.build(
            storyboard=storyboard,
            chapter_info=chapter_info,
            chapter_number=chapter_number,
            build_page_prompts=False,  # 不使用规则生成整页提示词
            dialogue_language=dialogue_language,
        )

        logger.info(
            f"画格提示词构建完成: {result.total_pages} 页, "
            f"{result.total_panels} 格"
        )

        # 4.2 使用LLM生成整页提示词
        # 恢复已完成的整页提示词（用于断点恢复）
        completed_page_prompts_data = cp_data.get("completed_page_prompts", [])
        completed_page_prompts = []
        if completed_page_prompts_data:
            from ..prompt_builder import PagePrompt
            for pp_data in completed_page_prompts_data:
                try:
                    completed_page_prompts.append(PagePrompt.from_dict(pp_data))
                except Exception as e:
                    logger.warning(f"恢复整页提示词失败: {e}")

        await save_checkpoint_callback(
            "page_prompt_building",
            {"stage": "page_prompt_building", "stage_label": "整页提示词生成", "current": len(completed_page_prompts), "total": storyboard.total_pages, "message": "正在生成整页提示词..."},
            cp_data,
            analysis_data=analysis_data_for_prompt
        )

        page_prompt_generator = PagePromptGenerator(
            llm_service=self.llm_service,
            prompt_service=self.prompt_service,
            style=style,
            character_profiles=character_profiles,
            character_portraits=final_portraits,
        )

        # 定义整页提示词生成完成后的保存回调
        async def on_prompt_generated(page_number: int, page_prompt):
            # 保存到断点数据
            if "completed_page_prompts" not in cp_data:
                cp_data["completed_page_prompts"] = []
            # 检查是否已存在该页码的提示词（避免重复）
            existing_pages = {pp.get("page_number") for pp in cp_data["completed_page_prompts"]}
            if page_number not in existing_pages:
                cp_data["completed_page_prompts"].append(page_prompt.to_dict())

        # 定义整页提示词生成进度回调
        async def on_page_prompt_complete(page_number: int, completed: int, total: int):
            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)
            # 更新进度
            await save_checkpoint_callback(
                "page_prompt_building",
                {
                    "stage": "page_prompt_building",
                    "stage_label": "整页提示词生成",
                    "current": completed,
                    "total": total,
                    "message": f"整页提示词: {completed}/{total} 页 (第{page_number}页完成)"
                },
                cp_data,
                analysis_data=analysis_data_for_prompt
            )

        page_prompts = await page_prompt_generator.generate_page_prompts(
            storyboard=storyboard,
            chapter_info=chapter_info,
            user_id=user_id,
            max_concurrency=page_prompt_concurrency,
            on_page_complete=on_page_prompt_complete,
            completed_prompts=completed_page_prompts if completed_page_prompts else None,
            on_prompt_generated=on_prompt_generated,
        )

        # 将LLM生成的整页提示词添加到结果中
        result.page_prompts = page_prompts

        # 清理断点数据中的整页提示词（已全部完成）
        cp_data.pop("completed_page_prompts", None)

        logger.info(f"LLM整页提示词生成完成: {len(page_prompts)} 页")

        logger.info(
            f"提示词构建完成: {result.total_pages} 页, "
            f"{result.total_panels} 格"
        )

        # ========== 步骤5：保存结果 ==========
        logger.info("步骤5: 保存结果")
        await self._save_result(
            project_id, chapter_number, result,
            chapter_info=chapter_info,
            page_plan=page_plan,
            source_version_id=source_version_id,
        )

        logger.info(
            f"漫画分镜生成完成: {result.total_pages} 页, "
            f"{result.total_panels} 格"
        )

        # ========== 步骤6：自动生成整页图片（可选） ==========
        if auto_generate_page_images and user_id:
            logger.info("步骤6: 自动生成整页图片")

            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)

            await save_checkpoint_callback(
                "page_image_generation",
                {
                    "stage": "page_image_generation",
                    "current": 0,
                    "total": result.total_pages,
                    "message": "正在生成整页图片..."
                },
                cp_data
            )

            # 批量生成整页图片
            generated_count, failed_count = await self._generate_all_page_images(
                user_id=user_id,
                project_id=project_id,
                chapter_number=chapter_number,
                result=result,
                chapter_info=chapter_info,
                chapter_id=chapter_id,
                source_version_id=source_version_id,
                save_checkpoint_callback=save_checkpoint_callback,
                cp_data=cp_data,
            )

            logger.info(
                f"整页图片生成完成: 成功 {generated_count}, 失败 {failed_count}"
            )

        return result

    def _determine_start_stage(self, cp_data: dict, start_from_stage: Optional[str] = None) -> str:
        """根据断点数据和用户指定确定起始阶段

        Args:
            cp_data: 断点数据
            start_from_stage: 用户指定的起始阶段（可选）

        Returns:
            起始阶段名称
        """
        # 如果用户指定了起始阶段，直接使用
        if start_from_stage:
            valid_stages = ["extraction", "planning", "storyboard", "prompt_building", "page_prompt_building"]
            if start_from_stage in valid_stages:
                return start_from_stage
            logger.warning(f"无效的起始阶段: {start_from_stage}，将自动检测")

        # 自动检测起始阶段
        if cp_data.get("storyboard"):
            return "prompt_building"
        if cp_data.get("page_plan"):
            return "storyboard"
        if cp_data.get("chapter_info"):
            return "planning"
        if cp_data.get("extraction_step1"):
            # 有部分提取数据，继续提取
            return "extraction"
        return "extraction"

    def _validate_start_stage(self, start_from_stage: str, cp_data: dict) -> Optional[str]:
        """验证用户指定的起始阶段是否可行

        Args:
            start_from_stage: 用户指定的起始阶段
            cp_data: 断点数据（可能包含从已完成结果恢复的数据）

        Returns:
            错误信息（如果有），否则返回 None
        """
        # 检查是否有已完成的结果
        has_completed_result = cp_data.get("_has_completed_result", False)

        # extraction 阶段无需前置数据
        if start_from_stage == "extraction":
            return None

        # planning 阶段需要 chapter_info
        if start_from_stage == "planning":
            if not cp_data.get("chapter_info"):
                return "从规划阶段开始需要先完成信息提取。请先完整生成一次，或从提取阶段开始。"
            return None

        # storyboard 阶段需要 chapter_info 和 page_plan
        if start_from_stage == "storyboard":
            if not cp_data.get("chapter_info"):
                return "从分镜阶段开始需要先完成信息提取。请先完整生成一次，或从提取阶段开始。"
            if not cp_data.get("page_plan"):
                return "从分镜阶段开始需要先完成页面规划。请先完整生成一次，或从规划阶段开始。"
            return None

        # prompt_building 阶段需要 chapter_info、page_plan 和 storyboard
        if start_from_stage == "prompt_building":
            if not cp_data.get("chapter_info"):
                return "从提示词构建阶段开始需要先完成信息提取。"
            if not cp_data.get("page_plan"):
                return "从提示词构建阶段开始需要先完成页面规划。"
            # 如果有已完成的结果，可以直接使用（storyboard 数据在数据库中）
            if not has_completed_result and not cp_data.get("storyboard") and not cp_data.get("designed_pages"):
                return "从提示词构建阶段开始需要先完成分镜设计。"
            return None

        # page_prompt_building 阶段需要已完成的分镜结果（有 panels 数据）
        if start_from_stage == "page_prompt_building":
            if not has_completed_result:
                return "从整页提示词构建阶段开始需要先完整生成一次分镜提示词。"
            return None

        return f"无效的起始阶段: {start_from_stage}"

    def _clear_data_from_stage(self, cp_data: dict, start_from_stage: str) -> dict:
        """清理指定阶段及之后的数据，强制重新生成

        Args:
            cp_data: 断点数据
            start_from_stage: 用户指定的起始阶段

        Returns:
            清理后的断点数据
        """
        cp_data = dict(cp_data)  # 复制一份避免修改原数据

        if start_from_stage == "extraction":
            # 从提取开始，清理所有数据
            cp_data.pop("extraction_step1", None)
            cp_data.pop("extraction_step2", None)
            cp_data.pop("extraction_step3", None)
            cp_data.pop("extraction_step4", None)
            cp_data.pop("chapter_info", None)
            cp_data.pop("page_plan", None)
            cp_data.pop("designed_pages", None)
            cp_data.pop("storyboard", None)
            cp_data.pop("completed_prompt_pages", None)

        elif start_from_stage == "planning":
            # 从规划开始，保留 chapter_info，清理后续数据
            cp_data.pop("page_plan", None)
            cp_data.pop("designed_pages", None)
            cp_data.pop("storyboard", None)
            cp_data.pop("completed_prompt_pages", None)

        elif start_from_stage == "storyboard":
            # 从分镜开始，保留 chapter_info 和 page_plan，清理后续数据
            cp_data.pop("designed_pages", None)
            cp_data.pop("storyboard", None)
            cp_data.pop("completed_prompt_pages", None)

        elif start_from_stage == "prompt_building":
            # 从提示词构建开始，只清理提示词相关数据
            cp_data.pop("completed_prompt_pages", None)

        elif start_from_stage == "page_prompt_building":
            # 从整页提示词构建开始，不需要清理数据
            # 只需要重新生成 page_prompts 字段
            pass

        logger.debug(f"已清理 {start_from_stage} 阶段之后的数据")
        return cp_data

    def _build_partial_analysis_data(
        self,
        extraction_data: dict,
        completed_step: int,
    ) -> dict:
        """构建部分 analysis_data，用于实时更新详细信息Tab

        根据已完成的提取步骤，构建包含当前已提取数据的 chapter_info 字典。

        Args:
            extraction_data: 当前的断点数据
            completed_step: 刚完成的步骤号 (1-4)

        Returns:
            包含 chapter_info 的 analysis_data 字典
        """
        # 如果已经有完整的 chapter_info，直接使用
        if extraction_data.get("chapter_info"):
            return {"chapter_info": extraction_data["chapter_info"]}

        # 从各步骤数据中提取已有的信息
        step1_data = extraction_data.get("extraction_step1", {})
        step2_data = extraction_data.get("extraction_step2", {})
        step3_data = extraction_data.get("extraction_step3", {})
        step4_data = extraction_data.get("extraction_step4", {})

        # 构建部分 chapter_info
        partial_chapter_info = {
            "characters": step1_data.get("characters", {}),
            "events": step1_data.get("events", []),
            "climax_event_indices": step1_data.get("climax_event_indices", []),
            "dialogues": step2_data.get("dialogues", []),
            "scenes": step3_data.get("scenes", []),
            "items": step4_data.get("items", []),
            "chapter_summary": step4_data.get("chapter_summary", ""),
            "mood_progression": step4_data.get("mood_progression", []),
            "total_estimated_pages": step4_data.get("total_estimated_pages", 0),
        }

        return {"chapter_info": partial_chapter_info}

    def _build_analysis_data(
        self,
        chapter_info: Optional[ChapterInfo],
        page_plan: Optional[PagePlanResult],
    ) -> Optional[dict]:
        """构建 analysis_data 用于详细信息Tab展示"""
        if not chapter_info and not page_plan:
            return None

        analysis_data = {}
        if chapter_info:
            analysis_data["chapter_info"] = chapter_info.to_dict()
        if page_plan:
            analysis_data["page_plan"] = page_plan.to_dict()
        return analysis_data

    async def _get_chapter_or_warn(
        self,
        project_id: str,
        chapter_number: int,
    ):
        """获取章节，不存在则记录警告"""
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            logger.warning(f"未找到章节: {project_id}/{chapter_number}")
        return chapter

    async def _persist_result_data(
        self,
        chapter_id: int,
        result_data: dict,
        analysis_data: Optional[dict],
        source_version_id: Optional[int],
        is_complete: bool = True,
    ):
        """保存结果数据并提交事务"""
        await self.manga_prompt_repo.save_result(
            chapter_id=chapter_id,
            result_data=result_data,
            analysis_data=analysis_data,
            is_complete=is_complete,
            source_version_id=source_version_id,
        )
        await self.session.commit()

    def _rebuild_storyboard_from_db(
        self,
        manga_prompt,
        page_plan: PagePlanResult,
    ) -> StoryboardResult:
        """从数据库记录重建 StoryboardResult

        用于从已完成的结果恢复 storyboard 数据，以便重新构建提示词。

        Args:
            manga_prompt: 数据库中的 ChapterMangaPrompt 记录
            page_plan: 页面规划结果

        Returns:
            重建的 StoryboardResult
        """
        from ..storyboard import PageStoryboard, PanelDesign, PanelShape, ShotType, WidthRatio, AspectRatio, DialogueBubble

        pages = []
        pages_data = MangaPromptRepository.build_pages_from_scenes_panels(
            manga_prompt.scenes or [],
            manga_prompt.panels or [],
        )

        # 重建每页的 storyboard
        for page_data in pages_data:
            page_number = page_data.get("page_number", 0)
            page_panels = page_data.get("panels", [])

            # 重建 panel designs
            panel_designs = []
            for panel_data in page_panels:
                # 处理对话数据（完整恢复所有字段）
                dialogues_data = panel_data.get("dialogues", [])
                dialogues = []
                for d in dialogues_data:
                    if isinstance(d, dict):
                        dialogues.append(DialogueBubble(
                            speaker=d.get("speaker", ""),
                            content=d.get("content", ""),
                            is_internal=d.get("is_internal", False),
                            bubble_type=d.get("bubble_type", "normal"),
                        ))

                panel_design = PanelDesign(
                    panel_id=panel_data.get("panel_number", 1),
                    row_id=panel_data.get("row_id", 1),
                    row_span=panel_data.get("row_span", 1),
                    shape=PanelShape.from_string(panel_data.get("shape", "horizontal")),
                    shot_type=ShotType.from_string(panel_data.get("shot_type", "medium")),
                    width_ratio=WidthRatio.from_string(panel_data.get("width_ratio", "half")),
                    aspect_ratio=AspectRatio.from_string(panel_data.get("aspect_ratio", "4:3")),
                    visual_description=panel_data.get("prompt", ""),  # prompt 作为视觉描述
                    characters=panel_data.get("characters", []),
                    background=panel_data.get("background", ""),
                    atmosphere=panel_data.get("atmosphere", ""),
                    lighting=panel_data.get("lighting", ""),
                    character_actions=panel_data.get("character_actions", {}),
                    character_expressions=panel_data.get("character_expressions", {}),
                    dialogues=dialogues,
                    narration=panel_data.get("narration", ""),
                    narration_type=panel_data.get("narration_type", ""),
                    event_indices=panel_data.get("event_indices", []),
                )
                panel_designs.append(panel_design)

            # 重建 page storyboard
            page_sb = PageStoryboard(
                page_number=page_number,
                panels=panel_designs,
                layout_description=page_data.get("layout_description", ""),
                gutter_horizontal=page_data.get("gutter_horizontal", 8),
                gutter_vertical=page_data.get("gutter_vertical", 8),
            )
            pages.append(page_sb)

        # 按页码排序
        pages.sort(key=lambda p: p.page_number)

        return StoryboardResult(pages=pages)

    async def _auto_generate_portraits(
        self,
        user_id: int,
        project_id: str,
        chapter_id: Optional[int],
        chapter_info: ChapterInfo,
        style: str,
        source_version_id: Optional[int],
        final_portraits: Dict[str, str],
    ):
        """自动生成缺失的角色立绘"""
        logger.info("自动生成缺失的角色立绘")

        # 收集角色外观描述
        character_profiles = {}
        for name, char in chapter_info.characters.items():
            if char.appearance:
                character_profiles[name] = char.appearance

        if not character_profiles:
            return

        # 保存状态
        if chapter_id:
            await self._checkpoint_manager.save_checkpoint(
                chapter_id, "generating_portraits",
                {"stage": "generating_portraits", "current": 0,
                 "total": len(character_profiles),
                 "message": "正在为缺失立绘的角色生成立绘..."},
                {"chapter_info": chapter_info.to_dict()},
                style, source_version_id
            )

        # 调用立绘服务
        portrait_service = CharacterPortraitService(self.session)
        generated = await portrait_service.auto_generate_missing_portraits(
            user_id=user_id,
            project_id=project_id,
            character_profiles=character_profiles,
            style="anime",
            exclude_existing=True,
        )

        # 更新立绘映射
        # auto_generate_missing_portraits 返回 {"portraits": {...}, "failed_errors": [...]}
        if generated and generated.get("portraits"):
            from app.core.config import settings
            portraits_dict = generated["portraits"]
            for name, portrait in portraits_dict.items():
                if portrait.image_path:
                    final_portraits[name] = str(
                        settings.generated_images_dir / portrait.image_path
                    )
            logger.info(f"自动生成了 {len(portraits_dict)} 个角色的立绘")
            if generated.get("failed_errors"):
                logger.warning(f"部分立绘生成失败: {generated['failed_errors']}")
            await self.session.commit()

    async def _generate_all_page_images(
        self,
        user_id: int,
        project_id: str,
        chapter_number: int,
        result: "MangaPromptResult",
        chapter_info: "ChapterInfo",
        chapter_id: Optional[int],
        source_version_id: Optional[int],
        save_checkpoint_callback,
        cp_data: dict,
    ) -> tuple:
        """批量生成所有整页图片

        Args:
            user_id: 用户ID
            project_id: 项目ID
            chapter_number: 章节号
            result: 漫画提示词结果
            chapter_info: 章节信息
            chapter_id: 章节ID
            source_version_id: 源版本ID
            save_checkpoint_callback: 断点保存回调
            cp_data: 断点数据

        Returns:
            (generated_count, failed_count): 成功数和失败数的元组
        """
        from .page_prompt_builder import build_page_prompt_for_generation

        generated_count = 0
        failed_count = 0
        total_pages = result.total_pages
        page_prompts_map = {
            pp.page_number: pp for pp in (result.page_prompts or [])
        }

        # 收集角色立绘路径
        character_portraits = {}
        for name, char in chapter_info.characters.items():
            if hasattr(char, 'portrait_path') and char.portrait_path:
                character_portraits[name] = char.portrait_path

        for page in result.pages:
            page_number = page.page_number

            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)

            # 更新进度
            await save_checkpoint_callback(
                "page_image_generation",
                {
                    "stage": "page_image_generation",
                    "current": generated_count + failed_count,
                    "total": total_pages,
                    "message": f"正在生成第 {page_number} 页图片..."
                },
                cp_data
            )

            try:
                # 构建整页提示词（优先使用 LLM 结果）
                page_prompt = page_prompts_map.get(page_number)
                if page_prompt and page_prompt.full_page_prompt:
                    page_prompt_data = {
                        "full_page_prompt": page_prompt.full_page_prompt,
                        "negative_prompt": page_prompt.negative_prompt,
                        "aspect_ratio": page_prompt.aspect_ratio,
                        "reference_image_paths": page_prompt.reference_image_paths or [],
                        "layout_template": page_prompt.layout_template,
                        "layout_description": page_prompt.layout_description,
                        "panel_summaries": page_prompt.panel_summaries or [],
                    }
                else:
                    logger.warning(
                        "整页提示词缺失，回退使用规则拼装: page=%d",
                        page_number
                    )
                    page_prompt_data = build_page_prompt_for_generation(
                        page=page,
                        chapter_info=chapter_info,
                        style=result.style,
                        character_portraits=character_portraits,
                    )

                # 调用图片生成服务
                from app.services.image_generation.schemas import PageImageGenerationRequest
                gen_request = PageImageGenerationRequest(
                    full_page_prompt=page_prompt_data["full_page_prompt"],
                    negative_prompt=page_prompt_data.get("negative_prompt", ""),
                    layout_template=page_prompt_data.get("layout_template", ""),
                    layout_description=page_prompt_data.get("layout_description", ""),
                    ratio=page_prompt_data.get("aspect_ratio", "3:4"),
                    style=result.style,
                    chapter_version_id=source_version_id,
                    reference_image_paths=page_prompt_data.get("reference_image_paths", []),
                    panel_summaries=page_prompt_data.get("panel_summaries", []),
                    dialogue_language=result.dialogue_language or "chinese",
                )

                merged_request = await self.image_service.prepare_page_request(
                    project_id, gen_request
                )
                gen_result = await self.image_service.generate_page_image(
                    user_id=user_id,
                    project_id=project_id,
                    chapter_number=chapter_number,
                    page_number=page_number,
                    request=merged_request,
                )

                if gen_result.success:
                    generated_count += 1
                    logger.debug(f"第 {page_number} 页图片生成成功")
                else:
                    failed_count += 1
                    logger.warning(f"第 {page_number} 页图片生成失败: {gen_result.error_message}")

            except Exception as e:
                failed_count += 1
                logger.error(f"第 {page_number} 页图片生成异常: {e}")

        # 最终进度
        await save_checkpoint_callback(
            "completed",
            {
                "stage": "completed",
                "current": total_pages,
                "total": total_pages,
                "message": f"完成: {generated_count} 张图片"
            },
            cp_data
        )

        return generated_count, failed_count

    async def _save_incremental_result(
        self,
        project_id: str,
        chapter_number: int,
        style: str,
        character_profiles: Dict[str, str],
        completed_pages: list,
        total_pages: int,
        chapter_info: Optional[ChapterInfo] = None,
        page_plan: Optional[PagePlanResult] = None,
        is_complete: bool = False,
        source_version_id: Optional[int] = None,
        dialogue_language: str = "chinese",
    ):
        """增量保存生成结果（每完成一页就保存）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            style: 漫画风格
            character_profiles: 角色外观描述
            completed_pages: 已完成的页面提示词列表
            total_pages: 总页数
            chapter_info: 章节信息提取结果
            page_plan: 页面规划结果
            is_complete: 是否已全部完成
            source_version_id: 源章节版本ID（用于版本追踪）
            dialogue_language: 对话语言
        """
        # 获取章节
        chapter = await self._get_chapter_or_warn(project_id, chapter_number)
        if not chapter:
            return

        # 计算已完成的画格总数
        total_panels = sum(len(p.get("panels", [])) for p in completed_pages)

        # 构建部分结果数据
        result_data = {
            "chapter_number": chapter_number,
            "style": style,
            "pages": completed_pages,
            "total_pages": total_pages,
            "total_panels": total_panels,
            "character_profiles": character_profiles,
            "dialogue_language": dialogue_language,
            # 标记是否完成
            "is_complete": is_complete,
            "completed_pages_count": len(completed_pages),
        }

        # 构建分析数据（用于详细信息Tab展示）
        analysis_data = self._build_analysis_data(chapter_info, page_plan)

        # 保存到数据库（覆盖之前的部分结果）
        await self._persist_result_data(
            chapter.id,
            result_data,
            analysis_data,
            source_version_id,
            is_complete=is_complete,
        )
        logger.debug(f"增量保存: {len(completed_pages)}/{total_pages} 页")

    async def _save_result(
        self,
        project_id: str,
        chapter_number: int,
        result: MangaPromptResult,
        chapter_info: Optional[ChapterInfo] = None,
        page_plan: Optional[PagePlanResult] = None,
        source_version_id: Optional[int] = None,
    ):
        """保存生成结果

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            result: 漫画提示词结果
            chapter_info: 章节信息提取结果（用于详细信息Tab显示）
            page_plan: 页面规划结果（用于详细信息Tab显示）
            source_version_id: 源章节版本ID（用于版本追踪）
        """
        # 转换为数据库存储格式
        result_data = result.to_dict()

        # 标记为已完成
        result_data["is_complete"] = True
        result_data["completed_pages_count"] = result.total_pages

        # 获取章节
        chapter = await self._get_chapter_or_warn(project_id, chapter_number)
        if not chapter:
            return

        # 构建分析数据（用于详细信息Tab展示）
        analysis_data = self._build_analysis_data(chapter_info, page_plan)

        # 保存到数据库
        await self._persist_result_data(
            chapter.id,
            result_data,
            analysis_data,
            source_version_id,
            is_complete=True,
        )

    async def _regenerate_page_prompts_only(
        self,
        project_id: str,
        chapter_number: int,
        chapter_id: Optional[int],
        style: str,
        character_portraits: Optional[Dict[str, str]],
        source_version_id: Optional[int],
        user_id: Optional[int] = None,
        page_prompt_concurrency: int = 5,
    ) -> MangaPromptResult:
        """
        仅重新生成整页提示词（保留画格提示词不变）

        使用LLM重新生成整页提示词，保留已有的画格提示词。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            chapter_id: 章节ID
            style: 漫画风格
            character_portraits: 角色立绘路径字典
            source_version_id: 源版本ID
            user_id: 用户ID
            page_prompt_concurrency: 整页提示词LLM生成的并发数（1-20）

        Returns:
            MangaPromptResult: 更新后的漫画提示词结果
        """
        logger.info(f"仅重新生成整页提示词(LLM): project={project_id}, chapter={chapter_number}")

        # 1. 加载已有的漫画分镜数据
        chapter = await self.chapter_repo.get_by_project_and_number(project_id, chapter_number)
        if not chapter:
            raise ValueError(f"未找到章节: {project_id}/{chapter_number}")

        manga_prompt = await self.manga_prompt_repo.get_by_chapter_id(chapter.id)
        if not manga_prompt:
            raise ValueError("未找到已生成的漫画分镜数据，请先完整生成一次")

        # 2. 从 analysis_data 恢复 ChapterInfo 和 PagePlan
        analysis_data = manga_prompt.analysis_data or {}
        chapter_info_dict = analysis_data.get("chapter_info")
        page_plan_dict = analysis_data.get("page_plan")

        if not chapter_info_dict:
            raise ValueError("缺少章节信息数据，无法重新生成整页提示词")

        chapter_info = ChapterInfo.from_dict(chapter_info_dict)
        page_plan = PagePlanResult.from_dict(page_plan_dict) if page_plan_dict else None

        # 3. 从数据库重建 StoryboardResult
        storyboard = self._rebuild_storyboard_from_db(manga_prompt, page_plan)

        # 4. 收集角色外观描述
        character_profiles = {}
        for name, char in chapter_info.characters.items():
            if char.appearance:
                character_profiles[name] = char.appearance

        # 5. 使用 LLM 生成整页提示词
        final_portraits = dict(character_portraits) if character_portraits else {}

        page_prompt_generator = PagePromptGenerator(
            llm_service=self.llm_service,
            prompt_service=self.prompt_service,
            style=style,
            character_profiles=character_profiles,
            character_portraits=final_portraits,
        )

        # 定义进度回调（更新断点状态）
        total_pages = storyboard.total_pages

        async def on_page_prompt_complete(page_number: int, completed: int, total: int):
            # 检查是否已取消
            if chapter_id:
                await self._raise_if_cancelled(chapter_id)
            # 保存进度到断点
            await self._checkpoint_manager.save_checkpoint(
                chapter_id,
                "page_prompt_building",
                {
                    "stage": "page_prompt_building",
                    "stage_label": "整页提示词生成",
                    "current": completed,
                    "total": total,
                    "message": f"整页提示词: {completed}/{total} 页 (第{page_number}页完成)"
                },
                {},  # 不需要保存 checkpoint_data
                style,
                source_version_id,
                analysis_data=analysis_data,
            )

        # 保存初始进度
        await self._checkpoint_manager.save_checkpoint(
            chapter_id,
            "page_prompt_building",
            {
                "stage": "page_prompt_building",
                "stage_label": "整页提示词生成",
                "current": 0,
                "total": total_pages,
                "message": "正在生成整页提示词..."
            },
            {},
            style,
            source_version_id,
            analysis_data=analysis_data,
        )

        page_prompts = await page_prompt_generator.generate_page_prompts(
            storyboard=storyboard,
            chapter_info=chapter_info,
            user_id=user_id,
            max_concurrency=page_prompt_concurrency,
            on_page_complete=on_page_prompt_complete,
        )

        logger.info(f"LLM整页提示词重新生成完成: {len(page_prompts)} 页")

        # 6. 加载现有的 MangaPromptResult 并更新 page_prompts
        result_data = await self.manga_prompt_repo.get_result(chapter.id)
        if not result_data:
            raise ValueError("无法加载现有的漫画分镜结果")

        # 确保 chapter_number 在数据中
        result_data["chapter_number"] = chapter_number
        # 更新 page_prompts
        result_data["page_prompts"] = [pp.to_dict() for pp in page_prompts]

        # 7. 保存更新后的结果
        await self._persist_result_data(
            chapter.id,
            result_data,
            analysis_data,  # 保留原有的分析数据
            source_version_id,
            is_complete=True,
        )

        # 8. 返回完整的 MangaPromptResult
        return MangaPromptResult.from_dict(result_data)

    async def get_result(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[MangaPromptResult]:
        """获取已保存的生成结果"""
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            return None

        data = await self.manga_prompt_repo.get_result(chapter.id)
        if not data:
            return None

        # 确保 chapter_number 在数据中
        data["chapter_number"] = chapter_number

        return MangaPromptResult.from_dict(data)

    async def delete_result(
        self,
        project_id: str,
        chapter_number: int,
    ) -> bool:
        """删除生成结果"""
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            return False

        # Bug 27 修复: 同时删除已生成的图片
        image_service = ImageGenerationService(self.session)
        deleted_images = await image_service.delete_chapter_images(project_id, chapter_number)
        if deleted_images > 0:
            logger.info(
                "删除漫画分镜时同时清理了 %d 张图片: project=%s chapter=%d",
                deleted_images, project_id, chapter_number
            )

        await self.manga_prompt_repo.delete_result(chapter.id)
        await self.session.commit()
        return True


# 便捷函数
async def generate_manga_prompts(
    session: AsyncSession,
    llm_service: LLMService,
    project_id: str,
    chapter_number: int,
    chapter_content: str,
    style: str = MangaStyle.MANGA,
    min_pages: int = 8,
    max_pages: int = 15,
    user_id: Optional[int] = None,
    prompt_service: Optional[PromptService] = None,
) -> MangaPromptResult:
    """
    便捷函数：生成漫画分镜

    Args:
        session: 数据库会话
        llm_service: LLM服务
        project_id: 项目ID
        chapter_number: 章节号
        chapter_content: 章节内容
        style: 漫画风格
        min_pages: 最少页数
        max_pages: 最多页数
        user_id: 用户ID
        prompt_service: 提示词服务

    Returns:
        MangaPromptResult: 漫画提示词结果
    """
    service = MangaPromptServiceV2(session, llm_service, prompt_service)
    return await service.generate(
        project_id=project_id,
        chapter_number=chapter_number,
        chapter_content=chapter_content,
        style=style,
        min_pages=min_pages,
        max_pages=max_pages,
        user_id=user_id,
    )


__all__ = [
    "MangaPromptServiceV2",
    "generate_manga_prompts",
]
