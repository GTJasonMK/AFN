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
from ..prompt_builder import PromptBuilder, MangaPromptResult

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
            session, self.chapter_repo, self.manga_prompt_repo, self.image_service
        )

    async def _check_cancelled(self, chapter_id: int) -> bool:
        """检查生成任务是否已被取消

        Args:
            chapter_id: 章节ID

        Returns:
            是否已取消
        """
        manga_prompt = await self.manga_prompt_repo.get_by_chapter_id(chapter_id)
        if manga_prompt and manga_prompt.generation_status == "cancelled":
            return True
        return False

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

        Returns:
            MangaPromptResult: 漫画提示词结果
        """
        logger.info(
            f"开始生成漫画分镜: 项目={project_id}, 章节={chapter_number}, "
            f"页数范围={min_pages}-{max_pages}, 语言={dialogue_language}"
        )

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
                logger.info(
                    f"发现断点: status={checkpoint['status']}, "
                    f"已有数据: extraction_step1={bool(cp_data.get('extraction_step1'))}, "
                    f"chapter_info={bool(cp_data.get('chapter_info'))}, "
                    f"page_plan={bool(cp_data.get('page_plan'))}, "
                    f"designed_pages={len(cp_data.get('designed_pages', []))}"
                )

        # 如果用户指定了起始阶段，但没有断点数据，尝试从已完成的结果中恢复
        if start_from_stage and not cp_data and chapter_id:
            existing_manga = await self.manga_prompt_repo.get_by_chapter_id(chapter_id)
            if existing_manga and existing_manga.analysis_data:
                analysis = existing_manga.analysis_data
                if analysis.get("chapter_info"):
                    cp_data["chapter_info"] = analysis["chapter_info"]
                if analysis.get("page_plan"):
                    cp_data["page_plan"] = analysis["page_plan"]
                # 如果已有完成的 storyboard 数据（从 panels 推断）
                if existing_manga.panels and existing_manga.scenes:
                    # 标记已有完整数据
                    cp_data["_has_completed_result"] = True
                logger.info(
                    f"从已完成的结果恢复数据: "
                    f"chapter_info={bool(cp_data.get('chapter_info'))}, "
                    f"page_plan={bool(cp_data.get('page_plan'))}"
                )

        # 初始化变量
        chapter_info: Optional[ChapterInfo] = None
        page_plan: Optional[PagePlanResult] = None
        storyboard: Optional[StoryboardResult] = None
        final_portraits = dict(character_portraits) if character_portraits else {}

        # 判断起始阶段
        start_stage = self._determine_start_stage(cp_data, start_from_stage)
        logger.info(f"起始阶段: {start_stage}")

        # 如果用户指定了起始阶段，验证前置数据是否存在
        if start_from_stage:
            validation_error = self._validate_start_stage(start_from_stage, cp_data)
            if validation_error:
                raise ValueError(validation_error)
            # 清理指定阶段之后的数据，强制重新生成
            cp_data = self._clear_data_from_stage(cp_data, start_from_stage)

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
                # 第4步完成时，同时保存 analysis_data
                analysis_data_to_save = None
                if step == 4 and extraction_data.get("chapter_info"):
                    analysis_data_to_save = {
                        "chapter_info": extraction_data["chapter_info"]
                    }
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
            logger.info("从断点恢复 chapter_info")

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
            logger.info(f"从断点恢复 page_plan: {page_plan.total_pages} 页")

        # ========== 步骤3：分镜设计（支持每页断点 + 增量保存） ==========
        # 检查是否需要从已完成结果恢复 storyboard（用于 prompt_building 阶段）
        need_storyboard_from_db = (
            start_from_stage == "prompt_building" and
            cp_data.get("_has_completed_result") and
            not cp_data.get("storyboard")
        )

        if need_storyboard_from_db:
            # 从数据库恢复 storyboard 数据
            logger.info("从已完成结果恢复 storyboard 数据")
            existing_manga = await self.manga_prompt_repo.get_by_chapter_id(chapter_id)
            if existing_manga and existing_manga.panels and existing_manga.scenes:
                # 从 panels 和 scenes 重建 storyboard
                storyboard = self._rebuild_storyboard_from_db(existing_manga, page_plan)
                logger.info(f"恢复 storyboard: {storyboard.total_pages} 页, {storyboard.total_panels} 格")
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
            logger.info(f"从断点恢复 storyboard: {storyboard.total_pages} 页, {storyboard.total_panels} 格")
        # else: storyboard 已经在前面从数据库恢复了（need_storyboard_from_db=True）

        # ========== 步骤4：提示词构建（无LLM调用，不需要断点） ==========
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
            {"stage": "prompt_building", "current": 3, "total": 4, "message": "正在生成提示词..."},
            cp_data,
            analysis_data=analysis_data_for_prompt
        )

        # 收集角色外观描述
        character_profiles = {}
        for name, char in chapter_info.characters.items():
            if char.appearance:
                character_profiles[name] = char.appearance

        # 构建提示词
        prompt_builder = PromptBuilder(
            style=style,
            character_profiles=character_profiles,
            character_portraits=final_portraits,
        )

        result = prompt_builder.build(
            storyboard=storyboard,
            chapter_info=chapter_info,
            chapter_number=chapter_number,
        )

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
            valid_stages = ["extraction", "planning", "storyboard", "prompt_building"]
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

        logger.info(f"已清理 {start_from_stage} 阶段之后的数据")
        return cp_data

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
        from ..storyboard import PageStoryboard, PanelStoryboard

        # 按页码分组 panels
        panels_by_page = {}
        for panel in manga_prompt.panels or []:
            page_num = panel.get("page_number", 1)
            if page_num not in panels_by_page:
                panels_by_page[page_num] = []
            panels_by_page[page_num].append(panel)

        # 重建每页的 storyboard
        pages = []
        for scene in manga_prompt.scenes or []:
            page_number = scene.get("page_number", 0)
            page_panels = panels_by_page.get(page_number, [])

            # 重建 panel storyboards
            panel_storyboards = []
            for panel_data in page_panels:
                panel_sb = PanelStoryboard(
                    panel_id=panel_data.get("panel_id", ""),
                    position=panel_data.get("position", {}),
                    aspect_ratio=panel_data.get("aspect_ratio", "16:9"),
                    visual_description=panel_data.get("visual_description", ""),
                    characters=panel_data.get("characters", []),
                    action_description=panel_data.get("action_description", ""),
                    emotion_focus=panel_data.get("emotion_focus", ""),
                    camera_angle=panel_data.get("camera_angle", ""),
                    composition=panel_data.get("composition", ""),
                    lighting=panel_data.get("lighting", ""),
                    atmosphere=panel_data.get("atmosphere", ""),
                    key_visual_elements=panel_data.get("key_visual_elements", []),
                    dialogues=panel_data.get("dialogues", []),
                    narration=panel_data.get("narration", ""),
                    narration_position=panel_data.get("narration_position", ""),
                    sound_effects=panel_data.get("sound_effects", []),
                    is_key_panel=panel_data.get("is_key_panel", False),
                )
                panel_storyboards.append(panel_sb)

            # 重建 page storyboard
            page_sb = PageStoryboard(
                page_number=page_number,
                layout_type=scene.get("layout_type", "standard"),
                layout_description=scene.get("layout_description", ""),
                reading_flow=scene.get("reading_flow", "right_to_left"),
                panels=panel_storyboards,
                gutter_horizontal=scene.get("gutter_horizontal", 8),
                gutter_vertical=scene.get("gutter_vertical", 8),
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
        """
        # 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            logger.warning(f"未找到章节: {project_id}/{chapter_number}")
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
            "dialogue_language": "chinese",
            # 标记是否完成
            "is_complete": is_complete,
            "completed_pages_count": len(completed_pages),
        }

        # 构建分析数据（用于详细信息Tab展示）
        analysis_data = None
        if chapter_info or page_plan:
            analysis_data = {}
            if chapter_info:
                analysis_data["chapter_info"] = chapter_info.to_dict()
            if page_plan:
                analysis_data["page_plan"] = page_plan.to_dict()

        # 保存到数据库（覆盖之前的部分结果）
        await self.manga_prompt_repo.save_result(
            chapter_id=chapter.id,
            result_data=result_data,
            analysis_data=analysis_data,
            is_complete=is_complete,
            source_version_id=source_version_id,
        )

        await self.session.commit()
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
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            logger.warning(f"未找到章节: {project_id}/{chapter_number}")
            return

        # 构建分析数据（用于详细信息Tab展示）
        analysis_data = None
        if chapter_info or page_plan:
            analysis_data = {}
            if chapter_info:
                analysis_data["chapter_info"] = chapter_info.to_dict()
            if page_plan:
                analysis_data["page_plan"] = page_plan.to_dict()

        # 保存到数据库
        await self.manga_prompt_repo.save_result(
            chapter_id=chapter.id,
            result_data=result_data,
            analysis_data=analysis_data,
            source_version_id=source_version_id,
        )

        await self.session.commit()

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
