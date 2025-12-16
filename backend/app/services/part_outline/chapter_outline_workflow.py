"""
章节大纲生成工作流

负责为指定部分串行生成章节大纲的核心业务逻辑。
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.constants import LLMConstants, GenerationStatus
from ...models.part_outline import PartOutline
from ...models.novel import NovelProject
from ...repositories.part_outline_repository import PartOutlineRepository
from ...repositories.chapter_repository import ChapterOutlineRepository
from ...schemas.novel import ChapterOutline as ChapterOutlineSchema
from ...utils.exception_helpers import log_exception
from ..llm_service import LLMService
from ..llm_wrappers import call_llm_json, LLMProfile
from ..prompt_service import PromptService
from ..prompt_builder import PromptBuilder

from .parser import PartOutlineParser
from .context_retriever import PartOutlineContextRetriever

logger = logging.getLogger(__name__)


class GenerationCancelledException(Exception):
    """生成被用户取消的异常"""
    pass


class ChapterOutlineWorkflow:
    """
    章节大纲生成工作流

    负责为指定部分串行生成章节大纲，将复杂的生成逻辑从 PartOutlineService 中分离。
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: PromptService,
        prompt_builder: PromptBuilder,
        parser: PartOutlineParser,
        context_retriever: PartOutlineContextRetriever,
        part_repo: PartOutlineRepository,
        chapter_outline_repo: ChapterOutlineRepository,
    ):
        """
        初始化工作流

        Args:
            session: 数据库会话
            llm_service: LLM服务
            prompt_service: 提示词服务
            prompt_builder: 提示词构建器
            parser: 解析器
            context_retriever: 上下文检索器
            part_repo: 部分大纲仓储
            chapter_outline_repo: 章节大纲仓储
        """
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.prompt_builder = prompt_builder
        self.parser = parser
        self.context_retriever = context_retriever
        self.part_repo = part_repo
        self.chapter_outline_repo = chapter_outline_repo

    async def execute(
        self,
        project: NovelProject,
        part_outline: PartOutline,
        user_id: int,
        regenerate: bool = False,
        chapters_per_batch: int = 5,
        cancellation_checker: Optional[Callable[[PartOutline], Awaitable[bool]]] = None,
    ) -> List[ChapterOutlineSchema]:
        """
        执行章节大纲生成工作流

        Args:
            project: 项目对象
            part_outline: 部分大纲对象
            user_id: 用户ID
            regenerate: 是否重新生成
            chapters_per_batch: 每批生成的章节数
            cancellation_checker: 取消检查回调函数

        Returns:
            List[ChapterOutlineSchema]: 生成的章节大纲列表

        Raises:
            GenerationCancelledException: 如果生成被取消
        """
        project_id = project.id
        part_number = part_outline.part_number

        logger.info(
            "开始章节大纲生成工作流：项目=%s, 部分=%d",
            project_id, part_number
        )

        # 检查取消状态
        if cancellation_checker:
            await cancellation_checker(part_outline)

        start_chapter = part_outline.start_chapter
        end_chapter = part_outline.end_chapter
        total_chapters = end_chapter - start_chapter + 1

        logger.info(
            "第 %d 部分需要生成 %d 章（第 %d-%d 章）",
            part_number, total_chapters, start_chapter, end_chapter
        )

        system_prompt = await self.prompt_service.get_prompt("screenwriting")
        all_generated_chapters: List[Dict[str, Any]] = []
        current_chapter = start_chapter

        while current_chapter <= end_chapter:
            # 检查取消状态
            if cancellation_checker:
                await cancellation_checker(part_outline)

            batch_end = min(current_chapter + chapters_per_batch - 1, end_chapter)
            batch_count = batch_end - current_chapter + 1

            logger.info("开始生成第 %d-%d 章", current_chapter, batch_end)

            # 获取上下文
            previous_chapters_data = await self.context_retriever.get_previous_chapters(
                project_id, current_chapter
            )

            relevant_summaries = await self.context_retriever.retrieve_relevant_summaries(
                project_id=project_id,
                user_id=user_id,
                start_chapter=current_chapter,
                end_chapter=batch_end,
                part_summary=part_outline.summary or "",
            )

            # 构建提示词
            user_prompt = await self.prompt_builder.build_part_chapters_prompt(
                part_outline=part_outline,
                project=project,
                start_chapter=current_chapter,
                num_chapters=batch_count,
                previous_chapters=previous_chapters_data,
                relevant_summaries=relevant_summaries,
            )

            # 调用LLM
            response = await call_llm_json(
                self.llm_service,
                LLMProfile.BLUEPRINT,
                system_prompt=system_prompt,
                user_content=user_prompt,
                user_id=user_id,
                timeout_override=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
            )

            # 检查取消状态
            if cancellation_checker:
                await cancellation_checker(part_outline)

            # 解析响应
            chapters_data = self.parser.parse_chapter_outlines(response)

            # 保存章节大纲
            for chapter_data in chapters_data:
                chapter_number = chapter_data.get("chapter_number")
                if not chapter_number:
                    continue

                if not regenerate:
                    existing = next(
                        (o for o in project.outlines if o.chapter_number == chapter_number),
                        None,
                    )
                    if existing:
                        logger.info("章节 %d 大纲已存在，跳过", chapter_number)
                        continue

                await self.chapter_outline_repo.upsert_outline(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    title=chapter_data.get("title", ""),
                    summary=chapter_data.get("summary", "")
                )
                all_generated_chapters.append(chapter_data)

            logger.info("成功生成第 %d-%d 章大纲", current_chapter, batch_end)

            # 更新进度
            progress = int((current_chapter - start_chapter + batch_count) / total_chapters * 100)
            await self.part_repo.update_status(part_outline, GenerationStatus.GENERATING, progress)
            await self.session.commit()

            current_chapter = batch_end + 1

        logger.info(
            "章节大纲生成工作流完成：部分=%d, 生成章节数=%d",
            part_number, len(all_generated_chapters)
        )

        return [
            ChapterOutlineSchema(
                chapter_number=c.get("chapter_number"),
                title=c.get("title", ""),
                summary=c.get("summary", ""),
            )
            for c in all_generated_chapters
        ]


def get_chapter_outline_workflow(
    session: AsyncSession,
    llm_service: LLMService,
    prompt_service: PromptService,
    prompt_builder: PromptBuilder,
    parser: PartOutlineParser,
    context_retriever: PartOutlineContextRetriever,
    part_repo: PartOutlineRepository,
    chapter_outline_repo: ChapterOutlineRepository,
) -> ChapterOutlineWorkflow:
    """工厂函数：创建章节大纲工作流实例"""
    return ChapterOutlineWorkflow(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
        prompt_builder=prompt_builder,
        parser=parser,
        context_retriever=context_retriever,
        part_repo=part_repo,
        chapter_outline_repo=chapter_outline_repo,
    )


__all__ = [
    "ChapterOutlineWorkflow",
    "GenerationCancelledException",
    "get_chapter_outline_workflow",
]
