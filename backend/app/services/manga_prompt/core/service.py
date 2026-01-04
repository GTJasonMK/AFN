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

        # 初始化变量
        chapter_info: Optional[ChapterInfo] = None
        page_plan: Optional[PagePlanResult] = None
        storyboard: Optional[StoryboardResult] = None
        final_portraits = dict(character_portraits) if character_portraits else {}

        # 判断起始阶段
        start_stage = self._determine_start_stage(cp_data)
        logger.info(f"起始阶段: {start_stage}")

        # 如果是从头开始，清理旧数据
        if start_stage == "extraction":
            await self._result_persistence.cleanup_old_data(
                project_id, chapter_number, chapter_id
            )

        # 定义断点保存回调
        async def save_checkpoint_callback(status: str, progress: dict, data: dict):
            if chapter_id:
                await self._checkpoint_manager.save_checkpoint(
                    chapter_id, status, progress, data, style, source_version_id
                )

        # ========== 步骤1：信息提取（支持分步断点） ==========
        if start_stage == "extraction" or not cp_data.get("chapter_info"):
            logger.info("步骤1: 提取章节信息")

            # 定义提取步骤完成回调
            async def on_extraction_step_complete(step: int, extraction_data: dict):
                step_labels = {
                    1: "提取角色和事件",
                    2: "提取对话",
                    3: "提取场景",
                    4: "提取物品和摘要"
                }
                await save_checkpoint_callback(
                    "extracting",
                    {
                        "stage": "extracting",
                        "current": step,
                        "total": 4,
                        "message": f"完成: {step_labels.get(step, '未知步骤')}"
                    },
                    extraction_data
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
                f"规划完成: {page_plan.total_pages} 页, "
                f"高潮页: {page_plan.climax_pages}"
            )

            # 保存断点
            cp_data["page_plan"] = page_plan.to_dict()
            await save_checkpoint_callback(
                "storyboard",
                {"stage": "storyboard", "current": 2, "total": 4,
                 "message": f"准备设计 {page_plan.total_pages} 页分镜..."},
                cp_data
            )
        else:
            # 从断点恢复 page_plan
            page_plan = PagePlanResult.from_dict(cp_data["page_plan"])
            logger.info(f"从断点恢复 page_plan: {page_plan.total_pages} 页")

        # ========== 步骤3：分镜设计（支持每页断点） ==========
        if not cp_data.get("storyboard"):
            logger.info("步骤3: 分镜设计")

            # 获取已设计的页面数据
            designed_pages_data = cp_data.get("designed_pages", [])

            # 定义每页完成回调
            async def on_page_design_complete(page_number: int, all_pages_data: list):
                cp_data["designed_pages"] = all_pages_data
                completed = len(all_pages_data)
                total = page_plan.total_pages
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
        else:
            # 从断点恢复 storyboard
            storyboard = StoryboardResult.from_dict(cp_data["storyboard"])
            logger.info(f"从断点恢复 storyboard: {storyboard.total_pages} 页, {storyboard.total_panels} 格")

        # ========== 步骤4：提示词构建（无LLM调用，不需要断点） ==========
        logger.info("步骤4: 构建提示词")

        await save_checkpoint_callback(
            "prompt_building",
            {"stage": "prompt_building", "current": 3, "total": 4, "message": "正在生成提示词..."},
            cp_data
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
            dialogue_language=dialogue_language,
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
        await self._save_result(project_id, chapter_number, result)

        logger.info(
            f"漫画分镜生成完成: {result.total_pages} 页, "
            f"{result.total_panels} 格"
        )

        return result

    def _determine_start_stage(self, cp_data: dict) -> str:
        """根据断点数据确定起始阶段"""
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

    async def _save_result(
        self,
        project_id: str,
        chapter_number: int,
        result: MangaPromptResult,
    ):
        """保存生成结果"""
        # 转换为数据库存储格式
        result_data = result.to_dict()

        # 获取章节
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter:
            logger.warning(f"未找到章节: {project_id}/{chapter_number}")
            return

        # 保存到数据库
        await self.manga_prompt_repo.save_result(
            chapter_id=chapter.id,
            result_data=result_data,
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
