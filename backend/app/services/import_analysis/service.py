"""
导入分析主服务

协调外部小说导入和智能分析的完整流程。
"""

import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.novel import Chapter
from ...core.state_machine import ProjectStatus
from ...services.llm_service import LLMService
from ...services.prompt_service import PromptService

from .txt_parser import TxtParser
from .progress_tracker import ProgressTracker
from .models import ChapterSummary, ImportResult
from .data_helper import DataHelper
from .summary_generator import SummaryGenerator
from .outline_generator import OutlineGenerator
from .blueprint_extractor import BlueprintExtractor

logger = logging.getLogger(__name__)


class ImportAnalysisService:
    """
    导入分析主服务

    负责：
    1. TXT文件解析和章节导入
    2. 逐章生成分析数据（analysis_data）
    3. 逐章生成摘要
    4. 章节大纲生成
    5. 分部大纲生成（长篇）
    6. 蓝图反推

    分析顺序说明：
    先生成 analysis_data，因为它包含角色状态、伏笔、情节点等深度分析，
    可以作为后续步骤（摘要、大纲、蓝图）的参考数据，提高整体分析质量。

    上下文限制说明：
    为避免 LLM 上下文爆炸，对长篇小说做了以下限制：
    - 阶段3（大纲更新）：超过100章时跳过LLM标准化，直接使用摘要
    - 阶段4（分部大纲）：分批处理，每批最多30章摘要
    - 阶段5（蓝图反推）：采样摘要（最多50章）并压缩单章摘要长度
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: PromptService,
    ):
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.parser = TxtParser()
        self.progress = ProgressTracker(session)
        self.data_helper = DataHelper(session)

        # 初始化子组件
        self.summary_generator = SummaryGenerator(
            session=session,
            llm_service=llm_service,
            prompt_service=prompt_service,
            data_helper=self.data_helper,
            progress=self.progress,
        )
        self.outline_generator = OutlineGenerator(
            session=session,
            llm_service=llm_service,
            prompt_service=prompt_service,
            data_helper=self.data_helper,
            progress=self.progress,
        )
        self.blueprint_extractor = BlueprintExtractor(
            session=session,
            llm_service=llm_service,
            prompt_service=prompt_service,
            data_helper=self.data_helper,
            progress=self.progress,
        )

    async def import_txt(
        self,
        project_id: str,
        file_content: bytes,
        user_id: int,
    ) -> ImportResult:
        """
        导入TXT文件

        流程:
        1. 解析文件编码和章节
        2. 创建ChapterOutline + Chapter + ChapterVersion
        3. 设置项目为导入状态
        """
        # 1. 解析TXT
        parse_result = self.parser.parse(file_content)

        if not parse_result.chapters:
            raise ValueError("无法从文件中识别任何章节")

        # 2. 获取项目
        project = await self.data_helper.get_project(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        # 3. 创建章节数据
        chapters_info = []
        for parsed_chapter in parse_result.chapters:
            # 创建或更新章节大纲
            await self.data_helper.upsert_chapter_outline(
                project_id=project_id,
                chapter_number=parsed_chapter.chapter_number,
                title=parsed_chapter.title,
                summary="（导入章节，待分析）",
            )

            # 创建或更新章节
            await self.data_helper.upsert_chapter(
                project_id=project_id,
                chapter_number=parsed_chapter.chapter_number,
                content=parsed_chapter.content,
            )

            chapters_info.append({
                "chapter_number": parsed_chapter.chapter_number,
                "title": parsed_chapter.title,
                "word_count": parsed_chapter.word_count,
            })

        # 4. 更新项目状态
        project.is_imported = True
        project.import_analysis_status = ProgressTracker.STATUS_PENDING
        project.import_analysis_progress = None

        await self.session.commit()

        logger.info(
            "项目 %s 导入完成，共 %d 章，编码: %s，模式: %s",
            project_id,
            len(parse_result.chapters),
            parse_result.encoding,
            parse_result.pattern_name,
        )

        return ImportResult(
            total_chapters=len(parse_result.chapters),
            chapters=chapters_info,
            parse_info={
                "encoding": parse_result.encoding,
                "pattern_used": parse_result.pattern_name,
                "total_characters": parse_result.total_characters,
                "warnings": parse_result.warnings,
            },
        )

    async def start_analysis(
        self,
        project_id: str,
        user_id: int,
    ) -> None:
        """
        执行完整分析流程（优化后的顺序，支持断点续传）

        阶段:
        1. generating_analysis_data - 逐章生成分析数据（最重要，作为后续步骤的基础）
        2. analyzing_chapters - 逐章生成摘要（利用analysis_data）
        3. generating_outlines - 更新章节大纲
        4. generating_part_outlines - 生成分部大纲（仅长篇>=50章）
        5. extracting_blueprint - 反推蓝图（利用analysis_data）

        断点续传:
        - 如果之前分析中断，会从上次的阶段继续
        - 已生成的 analysis_data 和摘要会被复用
        """
        try:
            # 获取项目和章节
            project = await self.data_helper.get_project_with_chapters(project_id)
            if not project:
                raise ValueError(f"项目不存在: {project_id}")

            chapters = sorted(project.chapters, key=lambda c: c.chapter_number)
            total_chapters = len(chapters)

            if total_chapters == 0:
                raise ValueError("项目没有章节内容")

            # 判断是否需要分部大纲
            needs_part_outlines = total_chapters >= 50

            # 检查是否有之前的进度（断点续传）
            previous_progress = project.import_analysis_progress
            resume_from_stage = None

            if previous_progress and previous_progress.get('status') in ('failed', 'cancelled', 'analyzing'):
                # 有之前的进度，尝试恢复
                resume_from_stage = previous_progress.get('current_stage')
                logger.info(
                    "项目 %s 检测到之前的进度，将从阶段 '%s' 继续",
                    project_id, resume_from_stage
                )
                # 恢复进度状态
                await self.progress.resume(project_id)
            else:
                # 全新开始，初始化进度
                await self.progress.initialize(
                    project_id=project_id,
                    total_chapters=total_chapters,
                    needs_part_outlines=needs_part_outlines,
                )
            await self.session.commit()

            # 定义阶段顺序
            stage_order = [
                'generating_analysis_data',
                'analyzing_chapters',
                'generating_outlines',
                'generating_part_outlines',
                'extracting_blueprint',
            ]

            # 确定起始阶段索引
            start_stage_idx = 0
            if resume_from_stage and resume_from_stage in stage_order:
                start_stage_idx = stage_order.index(resume_from_stage)

            # ========== 阶段1: 逐章生成分析数据 ==========
            if start_stage_idx <= stage_order.index('generating_analysis_data'):
                await self.progress.advance_stage(project_id, 'generating_analysis_data')
                await self.session.commit()

                await self.summary_generator.generate_analysis_data(
                    project_id=project_id,
                    chapters=chapters,
                    user_id=user_id,
                )

                if await self.progress.is_cancelled(project_id):
                    return
            else:
                logger.info("跳过阶段 'generating_analysis_data'（已完成）")

            # ========== 阶段2: 逐章生成摘要 ==========
            summaries: List[ChapterSummary] = []
            if start_stage_idx <= stage_order.index('analyzing_chapters'):
                await self.progress.advance_stage(project_id, 'analyzing_chapters')
                await self.session.commit()

                # 重新加载章节以获取最新的 analysis_data
                project = await self.data_helper.get_project_with_chapters(project_id)
                chapters = sorted(project.chapters, key=lambda c: c.chapter_number)

                summaries = await self.summary_generator.analyze_chapters(
                    project_id=project_id,
                    chapters=chapters,
                    user_id=user_id,
                )

                if await self.progress.is_cancelled(project_id):
                    return
            else:
                logger.info("跳过阶段 'analyzing_chapters'（已完成）")
                # 需要从现有大纲中加载摘要
                summaries = await self.data_helper.load_existing_summaries(project_id)

            # ========== 阶段3: 更新章节大纲 ==========
            if start_stage_idx <= stage_order.index('generating_outlines'):
                await self.progress.advance_stage(project_id, 'generating_outlines')
                await self.session.commit()

                await self.outline_generator.update_chapter_outlines(
                    project_id=project_id,
                    summaries=summaries,
                    user_id=user_id,
                )

                if await self.progress.is_cancelled(project_id):
                    return
            else:
                logger.info("跳过阶段 'generating_outlines'（已完成）")

            # ========== 阶段4: 生成分部大纲（如果需要） ==========
            part_outlines = None
            if needs_part_outlines:
                if start_stage_idx <= stage_order.index('generating_part_outlines'):
                    await self.progress.advance_stage(project_id, 'generating_part_outlines')
                    await self.session.commit()

                    part_outlines = await self.outline_generator.generate_part_outlines(
                        project_id=project_id,
                        summaries=summaries,
                        user_id=user_id,
                    )
                else:
                    logger.info("跳过阶段 'generating_part_outlines'（已完成）")
                    part_outlines = await self.data_helper.load_existing_part_outlines(project_id)

            if await self.progress.is_cancelled(project_id):
                return

            # ========== 阶段5: 反推蓝图 ==========
            if start_stage_idx <= stage_order.index('extracting_blueprint'):
                await self.progress.advance_stage(project_id, 'extracting_blueprint')
                await self.session.commit()

                # 重新加载章节以获取 analysis_data
                project = await self.data_helper.get_project_with_chapters(project_id)
                chapters = sorted(project.chapters, key=lambda c: c.chapter_number)

                await self.blueprint_extractor.extract_blueprint(
                    project_id=project_id,
                    project=project,
                    chapters=chapters,
                    summaries=summaries,
                    part_outlines=part_outlines,
                    user_id=user_id,
                )
            else:
                logger.info("跳过阶段 'extracting_blueprint'（已完成）")

            # 更新项目状态为WRITING
            project = await self.data_helper.get_project(project_id)
            project.status = ProjectStatus.WRITING.value
            await self.progress.mark_completed(project_id)
            await self.session.commit()

            logger.info("项目 %s 分析完成", project_id)

        except Exception as e:
            logger.exception("项目 %s 分析失败: %s", project_id, e)
            await self.progress.mark_failed(project_id, str(e))
            await self.session.commit()
            raise


__all__ = [
    "ImportAnalysisService",
]
