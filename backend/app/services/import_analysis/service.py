"""
导入分析主服务

协调外部小说导入和智能分析的完整流程。
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.novel import (
    NovelProject, NovelBlueprint, Chapter, ChapterVersion,
    ChapterOutline, BlueprintCharacter, BlueprintRelationship,
)
from ...models.part_outline import PartOutline
from ...core.state_machine import ProjectStatus
from ...services.llm_service import LLMService
from ...services.llm_wrappers import call_llm_json, LLMProfile
from ...services.prompt_service import PromptService
from ...services.chapter_analysis_service import ChapterAnalysisService
from ...utils.json_utils import parse_llm_json_safe, parse_llm_json_or_fail
from ...utils.content_normalizer import count_chinese_characters

from .txt_parser import TxtParser, ParseResult, ParsedChapter
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class ChapterSummary:
    """章节摘要"""
    chapter_number: int
    title: str
    summary: str
    key_characters: List[str]
    key_events: List[str]


@dataclass
class ImportResult:
    """导入结果"""
    total_chapters: int
    chapters: List[Dict[str, Any]]
    parse_info: Dict[str, Any]


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

    MAX_CONTENT_LENGTH = 12000  # 每章内容截取长度（字符）
    MAX_RETRIES = 2  # 单章最大重试次数

    # 上下文限制常量
    MAX_CHAPTERS_FOR_LLM_OUTLINE = 100  # 超过此数量跳过LLM标准化大纲
    MAX_CHAPTERS_PER_PART_BATCH = 30  # 分部大纲每批处理的章节数
    MAX_SUMMARIES_FOR_BLUEPRINT = 50  # 蓝图反推最多使用的摘要数
    MAX_SUMMARY_LENGTH = 150  # 蓝图反推时单章摘要最大长度

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
        project = await self._get_project(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        # 3. 创建章节数据
        chapters_info = []
        for parsed_chapter in parse_result.chapters:
            # 创建或更新章节大纲
            outline = await self._upsert_chapter_outline(
                project_id=project_id,
                chapter_number=parsed_chapter.chapter_number,
                title=parsed_chapter.title,
                summary="（导入章节，待分析）",
            )

            # 创建或更新章节
            chapter = await self._upsert_chapter(
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
            project = await self._get_project_with_chapters(project_id)
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
            # 这是最重要的步骤，为后续所有分析提供基础数据
            if start_stage_idx <= stage_order.index('generating_analysis_data'):
                await self.progress.advance_stage(project_id, 'generating_analysis_data')
                await self.session.commit()

                await self._generate_analysis_data(
                    project_id=project_id,
                    chapters=chapters,
                    user_id=user_id,
                )

                if await self.progress.is_cancelled(project_id):
                    return
            else:
                logger.info("跳过阶段 'generating_analysis_data'（已完成）")

            # ========== 阶段2: 逐章生成摘要 ==========
            # 利用 analysis_data 生成更准确的摘要
            summaries = []
            if start_stage_idx <= stage_order.index('analyzing_chapters'):
                await self.progress.advance_stage(project_id, 'analyzing_chapters')
                await self.session.commit()

                # 重新加载章节以获取最新的 analysis_data
                project = await self._get_project_with_chapters(project_id)
                chapters = sorted(project.chapters, key=lambda c: c.chapter_number)

                summaries = await self._analyze_chapters(
                    project_id=project_id,
                    chapters=chapters,
                    user_id=user_id,
                )

                if await self.progress.is_cancelled(project_id):
                    return
            else:
                logger.info("跳过阶段 'analyzing_chapters'（已完成）")
                # 需要从现有大纲中加载摘要
                summaries = await self._load_existing_summaries(project_id)

            # ========== 阶段3: 更新章节大纲 ==========
            if start_stage_idx <= stage_order.index('generating_outlines'):
                await self.progress.advance_stage(project_id, 'generating_outlines')
                await self.session.commit()

                await self._update_chapter_outlines(
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

                    part_outlines = await self._generate_part_outlines(
                        project_id=project_id,
                        summaries=summaries,
                        user_id=user_id,
                    )
                else:
                    logger.info("跳过阶段 'generating_part_outlines'（已完成）")
                    part_outlines = await self._load_existing_part_outlines(project_id)

            if await self.progress.is_cancelled(project_id):
                return

            # ========== 阶段5: 反推蓝图 ==========
            # 利用 analysis_data 中的角色、伏笔等信息
            if start_stage_idx <= stage_order.index('extracting_blueprint'):
                await self.progress.advance_stage(project_id, 'extracting_blueprint')
                await self.session.commit()

                # 重新加载章节以获取 analysis_data
                project = await self._get_project_with_chapters(project_id)
                chapters = sorted(project.chapters, key=lambda c: c.chapter_number)

                await self._extract_blueprint(
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
            project = await self._get_project(project_id)
            project.status = ProjectStatus.WRITING.value
            await self.progress.mark_completed(project_id)
            await self.session.commit()

            logger.info("项目 %s 分析完成", project_id)

        except Exception as e:
            logger.exception("项目 %s 分析失败: %s", project_id, e)
            await self.progress.mark_failed(project_id, str(e))
            await self.session.commit()
            raise

    async def _generate_analysis_data(
        self,
        project_id: str,
        chapters: List[Chapter],
        user_id: int,
    ) -> None:
        """
        逐章生成分析数据（阶段1，支持断点续传）

        analysis_data 包含：
        - 角色状态变化
        - 伏笔和呼应
        - 情节点
        - 场景描写
        - 情感基调

        这些数据将作为后续步骤的参考。
        已有 analysis_data 的章节会被跳过。
        """
        analysis_service = ChapterAnalysisService(self.session)
        project = await self._get_project(project_id)
        total = len(chapters)

        # 统计已有数据和需要生成的章节
        chapters_with_data = sum(1 for c in chapters if c.analysis_data)
        chapters_to_process = [c for c in chapters if not c.analysis_data]

        logger.info(
            "开始逐章生成分析数据，共 %d 章，已有数据 %d 章，需生成 %d 章",
            total, chapters_with_data, len(chapters_to_process)
        )

        # 初始进度 = 已有数据的章节数
        processed_count = chapters_with_data

        for chapter in chapters_to_process:
            # 检查是否取消
            if await self.progress.is_cancelled(project_id):
                return

            chapter_num = chapter.chapter_number
            title = await self._get_chapter_title(chapter)

            try:
                content = chapter.selected_version.content if chapter.selected_version else ""
                if not content.strip():
                    logger.warning("章节 %d 内容为空，跳过分析", chapter_num)
                    processed_count += 1
                    continue

                # 更新进度
                await self.progress.update(
                    project_id=project_id,
                    stage='generating_analysis_data',
                    completed=processed_count,
                    total=total,
                    message=f"正在分析第{chapter_num}章: {title}",
                )
                await self.session.commit()

                # 调用分析服务（逐章分析，不批量）
                analysis_data = await analysis_service.analyze_chapter(
                    content=self._truncate_content(content),
                    title=title,
                    chapter_number=chapter_num,
                    novel_title=project.title,
                    user_id=user_id,
                    timeout=180.0,  # 单章分析给更多时间
                )

                # 保存到 chapter.analysis_data
                if analysis_data:
                    chapter.analysis_data = analysis_data.model_dump()
                    logger.debug("章节 %d 分析数据生成成功", chapter_num)
                else:
                    logger.warning("章节 %d 分析数据为空", chapter_num)

            except Exception as e:
                logger.warning("章节 %d 分析数据生成失败: %s", chapter_num, e)
                # 继续处理下一章，不中断整个流程

            # 每章提交一次，确保进度保存
            processed_count += 1
            await self.session.commit()

        # 最终进度更新
        await self.progress.update(
            project_id=project_id,
            stage='generating_analysis_data',
            completed=total,
            total=total,
            message="分析数据生成完成",
        )
        await self.session.commit()

    async def _analyze_chapters(
        self,
        project_id: str,
        chapters: List[Chapter],
        user_id: int,
    ) -> List[ChapterSummary]:
        """
        逐章生成摘要（阶段2，支持断点续传）

        利用已生成的 analysis_data 来辅助摘要生成。
        已有有效摘要的章节会被复用，不重新生成。
        生成的摘要会同时保存到 Chapter.real_summary（用于写作台显示）。
        """
        summaries = []
        total = len(chapters)
        project = await self._get_project(project_id)

        # 构建章节映射，用于更新 real_summary
        chapter_map = {c.chapter_number: c for c in chapters}

        # 获取所有已有的章节大纲
        existing_outlines = await self._get_chapter_outlines(project_id)
        outline_map = {o.chapter_number: o for o in existing_outlines}

        # 默认摘要标记（导入时的占位符）
        DEFAULT_SUMMARY = "（导入章节，待分析）"

        # 分类章节：已有有效摘要 vs 需要生成
        chapters_with_summary = []
        chapters_to_process = []

        for chapter in chapters:
            outline = outline_map.get(chapter.chapter_number)
            # 检查 ChapterOutline.summary 或 Chapter.real_summary 是否已有有效值
            has_outline_summary = outline and outline.summary and outline.summary != DEFAULT_SUMMARY
            has_real_summary = chapter.real_summary and chapter.real_summary.strip()

            if has_outline_summary or has_real_summary:
                # 已有有效摘要，直接使用
                existing_summary = chapter.real_summary if has_real_summary else outline.summary
                chapters_with_summary.append((chapter, outline, existing_summary))
            else:
                # 需要生成摘要
                chapters_to_process.append(chapter)

        logger.info(
            "开始逐章生成摘要，共 %d 章，已有摘要 %d 章，需生成 %d 章",
            total, len(chapters_with_summary), len(chapters_to_process)
        )

        # 先添加已有摘要
        for chapter, outline, existing_summary in chapters_with_summary:
            summaries.append(ChapterSummary(
                chapter_number=chapter.chapter_number,
                title=outline.title if outline else f"第{chapter.chapter_number}章",
                summary=existing_summary,
                key_characters=[],
                key_events=[],
            ))
            # 确保 real_summary 也有值
            if not chapter.real_summary:
                chapter.real_summary = existing_summary

        # 获取提示词
        prompt = await self.prompt_service.get_prompt("chapter_summary_single")
        if not prompt:
            prompt = """你是一位专业的小说编辑，请为提供的章节生成简短摘要。

请分析章节内容，提取以下信息并以JSON格式返回：
{
    "summary": "100-200字的章节摘要",
    "key_characters": ["出场的主要角色名"],
    "key_events": ["关键情节点"]
}"""

        # 初始进度 = 已有摘要的章节数
        processed_count = len(chapters_with_summary)

        for chapter in chapters_to_process:
            # 检查是否取消
            if await self.progress.is_cancelled(project_id):
                return summaries

            chapter_num = chapter.chapter_number
            title = await self._get_chapter_title(chapter)
            content = chapter.selected_version.content if chapter.selected_version else ""

            # 更新进度
            await self.progress.update(
                project_id=project_id,
                stage='analyzing_chapters',
                completed=processed_count,
                total=total,
                message=f"正在生成第{chapter_num}章摘要: {title}",
            )
            await self.session.commit()

            # 构建输入数据，包含 analysis_data 作为参考
            input_data = {
                "novel_title": project.title,
                "chapter_number": chapter_num,
                "title": title,
                "content": self._truncate_content(content),
            }

            # 如果有 analysis_data，添加为参考
            if chapter.analysis_data:
                input_data["analysis_reference"] = {
                    "characters": chapter.analysis_data.get("characters", []),
                    "plot_points": chapter.analysis_data.get("plot_points", []),
                    "foreshadowing": chapter.analysis_data.get("foreshadowing", []),
                }

            # 调用LLM生成摘要
            generated_summary = None
            for attempt in range(self.MAX_RETRIES + 1):
                try:
                    response = await call_llm_json(
                        self.llm_service,
                        LLMProfile.SUMMARY,
                        system_prompt=prompt,
                        user_content=json.dumps(input_data, ensure_ascii=False),
                        user_id=user_id,
                        timeout_override=120.0,
                    )

                    result = parse_llm_json_safe(response)
                    if result:
                        generated_summary = result.get("summary", "")
                        summaries.append(ChapterSummary(
                            chapter_number=chapter_num,
                            title=title,
                            summary=generated_summary,
                            key_characters=result.get("key_characters", []),
                            key_events=result.get("key_events", []),
                        ))
                        break

                except Exception as e:
                    if attempt == self.MAX_RETRIES:
                        logger.warning("章节 %d 摘要生成失败: %s，使用降级摘要", chapter_num, e)
                        # 使用降级摘要
                        generated_summary = content[:200] + "..." if len(content) > 200 else content
                        summaries.append(ChapterSummary(
                            chapter_number=chapter_num,
                            title=title,
                            summary=generated_summary,
                            key_characters=[],
                            key_events=[],
                        ))
                    else:
                        await asyncio.sleep(2 ** attempt)

            # 同时保存到 Chapter.real_summary（用于写作台显示）
            if generated_summary and chapter_num in chapter_map:
                chapter_map[chapter_num].real_summary = generated_summary
                logger.debug("章节 %d 摘要已保存到 real_summary", chapter_num)

            processed_count += 1
            # 每章提交一次，确保数据保存
            await self.session.commit()

        # 最终进度更新
        await self.progress.update(
            project_id=project_id,
            stage='analyzing_chapters',
            completed=total,
            total=total,
            message="摘要生成完成",
        )
        await self.session.commit()

        # 按章节号排序返回
        summaries.sort(key=lambda s: s.chapter_number)
        return summaries

    async def _update_chapter_outlines(
        self,
        project_id: str,
        summaries: List[ChapterSummary],
        user_id: int,
    ) -> None:
        """根据摘要更新章节大纲（阶段3）

        上下文优化：
        - 超过 MAX_CHAPTERS_FOR_LLM_OUTLINE 章时跳过LLM标准化
        - 直接使用原始摘要更新大纲，避免上下文爆炸
        """
        total_chapters = len(summaries)

        # 检查是否超过阈值
        if total_chapters > self.MAX_CHAPTERS_FOR_LLM_OUTLINE:
            logger.info(
                "章节数(%d)超过阈值(%d)，跳过LLM标准化，直接使用原始摘要",
                total_chapters, self.MAX_CHAPTERS_FOR_LLM_OUTLINE
            )
            for s in summaries:
                await self._upsert_chapter_outline(
                    project_id=project_id,
                    chapter_number=s.chapter_number,
                    title=s.title,
                    summary=s.summary[:500] if s.summary else "",
                )
            await self.session.commit()
            await self.progress.update(
                project_id=project_id,
                stage='generating_outlines',
                completed=1,
                total=1,
            )
            return

        # 获取提示词
        prompt = await self.prompt_service.get_prompt("reverse_outline")
        if not prompt:
            # 直接使用摘要作为大纲
            for s in summaries:
                await self._upsert_chapter_outline(
                    project_id=project_id,
                    chapter_number=s.chapter_number,
                    title=s.title,
                    summary=s.summary[:500] if s.summary else "",
                )
            await self.session.commit()
            await self.progress.update(
                project_id=project_id,
                stage='generating_outlines',
                completed=1,
                total=1,
            )
            return

        # 使用LLM标准化大纲
        input_data = {
            "novel_title": (await self._get_project(project_id)).title,
            "summaries": [
                {
                    "chapter_number": s.chapter_number,
                    "title": s.title,
                    "summary": s.summary,
                    "key_characters": s.key_characters,
                    "key_events": s.key_events,
                }
                for s in summaries
            ],
        }

        updated = False
        try:
            response = await call_llm_json(
                self.llm_service,
                LLMProfile.OUTLINE,
                system_prompt=prompt,
                user_content=json.dumps(input_data, ensure_ascii=False),
                user_id=user_id,
                timeout_override=180.0,
            )

            result = parse_llm_json_safe(response)
            if result and "outlines" in result and result["outlines"]:
                for o in result["outlines"]:
                    await self._upsert_chapter_outline(
                        project_id=project_id,
                        chapter_number=o.get("chapter_number", 0),
                        title=o.get("title", ""),
                        summary=o.get("summary", ""),
                    )
                updated = True
                logger.info("使用LLM标准化大纲成功，共 %d 章", len(result["outlines"]))
            else:
                logger.warning("LLM返回结果缺少outlines字段，使用原始摘要")
        except Exception as e:
            logger.warning("大纲标准化失败: %s，使用原始摘要", e)

        # 如果LLM没有成功更新，使用原始摘要
        if not updated:
            for s in summaries:
                await self._upsert_chapter_outline(
                    project_id=project_id,
                    chapter_number=s.chapter_number,
                    title=s.title,
                    summary=s.summary[:500] if s.summary else "",
                )
            logger.info("使用原始摘要更新大纲，共 %d 章", len(summaries))

        await self.progress.update(
            project_id=project_id,
            stage='generating_outlines',
            completed=1,
            total=1,
        )
        await self.session.commit()

    async def _generate_part_outlines(
        self,
        project_id: str,
        summaries: List[ChapterSummary],
        user_id: int,
    ) -> List[PartOutline]:
        """生成分部大纲（阶段4，仅长篇）

        上下文优化：
        - 先预分组章节（每25章一组）
        - 对每个分组单独调用LLM生成大纲
        - 每次只发送该分组的摘要，避免一次性发送全部
        """
        prompt = await self.prompt_service.get_prompt("reverse_part_outline")
        if not prompt:
            prompt = """你是一位专业的小说编辑。请根据提供的章节摘要，为这一部分内容生成一个分部大纲。

请以JSON格式返回：
{
    "title": "分部标题",
    "summary": "分部内容概述（100-200字）",
    "theme": "主题",
    "key_events": ["关键事件1", "关键事件2"],
    "character_arcs": {"角色名": "发展变化"},
    "ending_hook": "结尾悬念/钩子"
}"""

        project = await self._get_project(project_id)
        total_chapters = len(summaries)

        # 预分组：每25章一个分部
        chapters_per_part = 25
        part_count = (total_chapters + chapters_per_part - 1) // chapters_per_part
        part_outlines = []

        logger.info(
            "开始分批生成分部大纲：共%d章，预计%d个分部",
            total_chapters, part_count
        )

        for part_idx in range(part_count):
            start_idx = part_idx * chapters_per_part
            end_idx = min((part_idx + 1) * chapters_per_part, total_chapters)
            part_summaries = summaries[start_idx:end_idx]

            # 构建输入数据（只包含当前分部的摘要）
            input_data = {
                "novel_title": project.title,
                "part_number": part_idx + 1,
                "total_parts": part_count,
                "start_chapter": part_summaries[0].chapter_number,
                "end_chapter": part_summaries[-1].chapter_number,
                "chapter_outlines": [
                    {
                        "chapter_number": s.chapter_number,
                        "title": s.title,
                        "summary": s.summary[:200] if s.summary else "",  # 限制摘要长度
                    }
                    for s in part_summaries
                ],
            }

            # 添加前后分部的简要上下文（如果有）
            if part_idx > 0:
                prev_summaries = summaries[max(0, start_idx - 3):start_idx]
                input_data["previous_context"] = [
                    {"chapter": s.chapter_number, "title": s.title}
                    for s in prev_summaries
                ]
            if part_idx < part_count - 1:
                next_summaries = summaries[end_idx:min(end_idx + 3, total_chapters)]
                input_data["next_context"] = [
                    {"chapter": s.chapter_number, "title": s.title}
                    for s in next_summaries
                ]

            try:
                response = await call_llm_json(
                    self.llm_service,
                    LLMProfile.OUTLINE,
                    system_prompt=prompt,
                    user_content=json.dumps(input_data, ensure_ascii=False),
                    user_id=user_id,
                    timeout_override=120.0,
                )

                result = parse_llm_json_safe(response)
                if result:
                    part = PartOutline(
                        project_id=project_id,
                        part_number=part_idx + 1,
                        title=result.get("title", f"第{part_idx + 1}部"),
                        start_chapter=part_summaries[0].chapter_number,
                        end_chapter=part_summaries[-1].chapter_number,
                        summary=result.get("summary", ""),
                        theme=result.get("theme", ""),
                        key_events=result.get("key_events", []),
                        character_arcs=result.get("character_arcs", {}),
                        ending_hook=result.get("ending_hook", ""),
                        generation_status="completed",
                    )
                    self.session.add(part)
                    part_outlines.append(part)
                    logger.debug("分部 %d 大纲生成成功", part_idx + 1)
                else:
                    # 使用默认值
                    part = PartOutline(
                        project_id=project_id,
                        part_number=part_idx + 1,
                        title=f"第{part_idx + 1}部",
                        start_chapter=part_summaries[0].chapter_number,
                        end_chapter=part_summaries[-1].chapter_number,
                        summary=f"第{part_summaries[0].chapter_number}-{part_summaries[-1].chapter_number}章内容",
                        generation_status="completed",
                    )
                    self.session.add(part)
                    part_outlines.append(part)

            except Exception as e:
                logger.warning("分部 %d 大纲生成失败: %s", part_idx + 1, e)
                # 创建默认分部大纲
                part = PartOutline(
                    project_id=project_id,
                    part_number=part_idx + 1,
                    title=f"第{part_idx + 1}部",
                    start_chapter=part_summaries[0].chapter_number,
                    end_chapter=part_summaries[-1].chapter_number,
                    summary=f"第{part_summaries[0].chapter_number}-{part_summaries[-1].chapter_number}章内容",
                    generation_status="completed",
                )
                self.session.add(part)
                part_outlines.append(part)

            # 更新进度
            await self.progress.update(
                project_id=project_id,
                stage='generating_part_outlines',
                completed=part_idx + 1,
                total=part_count,
                message=f"正在生成第{part_idx + 1}/{part_count}部大纲",
            )
            await self.session.commit()

        await self.session.flush()
        logger.info("分部大纲生成完成，共%d个分部", len(part_outlines))
        return part_outlines

    async def _extract_blueprint(
        self,
        project_id: str,
        project: NovelProject,
        chapters: List[Chapter],
        summaries: List[ChapterSummary],
        part_outlines: Optional[List[PartOutline]],
        user_id: int,
    ) -> None:
        """
        反推蓝图（阶段5）

        利用 analysis_data 中的角色、伏笔等信息来提高蓝图质量。

        上下文优化：
        - 采样摘要（最多 MAX_SUMMARIES_FOR_BLUEPRINT 章）
        - 限制单章摘要长度（最多 MAX_SUMMARY_LENGTH 字符）
        - 限制 key_characters 和 key_events 数量
        """
        prompt = await self.prompt_service.get_prompt("reverse_blueprint")
        if not prompt:
            prompt = "请从小说内容中提取蓝图信息。"

        # 收集所有章节的 analysis_data 中的角色信息
        all_characters = {}
        all_foreshadowing = []

        for chapter in chapters:
            if chapter.analysis_data:
                # 收集角色
                for char in chapter.analysis_data.get("characters", []):
                    # 确保 char 是字典
                    if isinstance(char, dict):
                        char_name = char.get("name", "")
                        if char_name and char_name not in all_characters:
                            all_characters[char_name] = char

                # 收集伏笔
                for foreshadow in chapter.analysis_data.get("foreshadowing", []):
                    # 确保 foreshadow 是字典
                    if isinstance(foreshadow, dict):
                        all_foreshadowing.append({
                            "chapter": chapter.chapter_number,
                            **foreshadow,
                        })
                    elif isinstance(foreshadow, str):
                        # 如果是字符串，包装成字典
                        all_foreshadowing.append({
                            "chapter": chapter.chapter_number,
                            "content": foreshadow,
                        })

        # 抽样章节内容（用于风格分析）
        sample_indices = self._select_sample_chapters(len(chapters))
        sample_chapters = []
        for idx in sample_indices:
            if idx < len(chapters):
                c = chapters[idx]
                content = c.selected_version.content if c.selected_version else ""
                sample_chapters.append({
                    "chapter_number": c.chapter_number,
                    "content": content[:6000],  # 减少到6000字符
                })

        # 采样摘要：对于超长小说，均匀采样
        total_summaries = len(summaries)
        if total_summaries > self.MAX_SUMMARIES_FOR_BLUEPRINT:
            step = total_summaries // self.MAX_SUMMARIES_FOR_BLUEPRINT
            sampled_summaries = summaries[::step][:self.MAX_SUMMARIES_FOR_BLUEPRINT]
            logger.info(
                "摘要采样：从 %d 章采样 %d 章用于蓝图反推",
                total_summaries, len(sampled_summaries)
            )
        else:
            sampled_summaries = summaries

        # 构建压缩后的摘要列表
        compressed_summaries = [
            {
                "chapter_number": s.chapter_number,
                "title": s.title,
                "summary": s.summary[:self.MAX_SUMMARY_LENGTH] if s.summary else "",
                "key_characters": s.key_characters[:3] if s.key_characters else [],
                "key_events": s.key_events[:2] if s.key_events else [],
            }
            for s in sampled_summaries
        ]

        input_data = {
            "novel_title": project.title,
            "total_chapters": len(chapters),
            "sampled_chapters_count": len(sampled_summaries),
            "chapter_summaries": compressed_summaries,
            "sample_chapters": sample_chapters,
            # 利用 analysis_data 提取的信息
            "extracted_characters": list(all_characters.values())[:20],  # 最多20个角色
            "extracted_foreshadowing": all_foreshadowing[:30],  # 最多30个伏笔
        }

        if part_outlines:
            input_data["part_outlines"] = [
                {
                    "part_number": p.part_number,
                    "title": p.title,
                    "summary": p.summary,
                    "start_chapter": p.start_chapter,
                    "end_chapter": p.end_chapter,
                }
                for p in part_outlines
            ]

        try:
            response = await call_llm_json(
                self.llm_service,
                LLMProfile.BLUEPRINT,
                system_prompt=prompt,
                user_content=json.dumps(input_data, ensure_ascii=False),
                user_id=user_id,
                timeout_override=300.0,
            )

            result = parse_llm_json_safe(response)
            if result:
                await self._save_blueprint(project_id, result, len(chapters), part_outlines is not None)

        except Exception as e:
            logger.warning("蓝图反推失败: %s，创建基础蓝图", e)
            # 创建基础蓝图
            await self._save_blueprint(
                project_id,
                {
                    "title": project.title,
                    "genre": "未知",
                    "style": "未知",
                    "tone": "未知",
                    "one_sentence_summary": project.title,
                    "full_synopsis": "（待补充）",
                },
                len(chapters),
                part_outlines is not None,
            )

        await self.progress.update(
            project_id=project_id,
            stage='extracting_blueprint',
            completed=1,
            total=1,
        )
        await self.session.commit()

    # ==================== 辅助方法 ====================

    async def _get_project(self, project_id: str) -> Optional[NovelProject]:
        """获取项目"""
        result = await self.session.execute(
            select(NovelProject).where(NovelProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def _get_project_with_chapters(self, project_id: str) -> Optional[NovelProject]:
        """获取项目及其章节"""
        result = await self.session.execute(
            select(NovelProject)
            .where(NovelProject.id == project_id)
            .options(
                selectinload(NovelProject.chapters).selectinload(Chapter.selected_version),
                selectinload(NovelProject.outlines),
            )
        )
        return result.scalar_one_or_none()

    async def _get_chapter_title(self, chapter: Chapter) -> str:
        """获取章节标题"""
        result = await self.session.execute(
            select(ChapterOutline)
            .where(ChapterOutline.project_id == chapter.project_id)
            .where(ChapterOutline.chapter_number == chapter.chapter_number)
        )
        outline = result.scalar_one_or_none()
        return outline.title if outline else f"第{chapter.chapter_number}章"

    async def _upsert_chapter_outline(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        summary: str,
    ) -> ChapterOutline:
        """创建或更新章节大纲"""
        result = await self.session.execute(
            select(ChapterOutline)
            .where(ChapterOutline.project_id == project_id)
            .where(ChapterOutline.chapter_number == chapter_number)
        )
        outline = result.scalar_one_or_none()

        if outline:
            outline.title = title
            outline.summary = summary
        else:
            outline = ChapterOutline(
                project_id=project_id,
                chapter_number=chapter_number,
                title=title,
                summary=summary,
            )
            self.session.add(outline)

        await self.session.flush()
        return outline

    async def _upsert_chapter(
        self,
        project_id: str,
        chapter_number: int,
        content: str,
    ) -> Chapter:
        """创建或更新章节"""
        result = await self.session.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .where(Chapter.chapter_number == chapter_number)
            .options(selectinload(Chapter.versions))
        )
        chapter = result.scalar_one_or_none()

        if not chapter:
            chapter = Chapter(
                project_id=project_id,
                chapter_number=chapter_number,
            )
            self.session.add(chapter)
            await self.session.flush()

        # 创建新版本
        version = ChapterVersion(
            chapter_id=chapter.id,
            version_label="imported",
            provider="imported",
            content=content,
        )
        self.session.add(version)
        await self.session.flush()

        # 设置选中版本和状态
        chapter.selected_version_id = version.id
        chapter.word_count = count_chinese_characters(content)
        chapter.status = "successful" if content.strip() else "waiting_for_confirm"

        return chapter

    async def _save_blueprint(
        self,
        project_id: str,
        data: Dict[str, Any],
        total_chapters: int,
        needs_part_outlines: bool,
    ) -> None:
        """保存蓝图数据

        确保与正常创作流程生成的蓝图结构一致，包括：
        - 所有基础字段（title, genre, style, tone等）
        - 角色信息（包含 relationship_to_protagonist）
        - 关系信息
        - 世界观设定
        """
        from sqlalchemy import delete

        # 检查是否已有蓝图
        result = await self.session.execute(
            select(NovelBlueprint).where(NovelBlueprint.project_id == project_id)
        )
        blueprint = result.scalar_one_or_none()

        if not blueprint:
            blueprint = NovelBlueprint(project_id=project_id)
            self.session.add(blueprint)

        # 更新蓝图字段
        blueprint.title = data.get("title", "")
        blueprint.genre = data.get("genre", "")
        blueprint.style = data.get("style", "")
        blueprint.tone = data.get("tone", "")
        blueprint.target_audience = data.get("target_audience", "")
        blueprint.one_sentence_summary = data.get("one_sentence_summary", "")
        blueprint.full_synopsis = data.get("full_synopsis", "")
        blueprint.world_setting = data.get("world_setting", {})
        blueprint.total_chapters = total_chapters
        blueprint.needs_part_outlines = needs_part_outlines

        # 先删除旧角色（使用 delete 语句而非 select）
        await self.session.execute(
            delete(BlueprintCharacter).where(BlueprintCharacter.project_id == project_id)
        )

        # 保存新角色
        characters = data.get("characters", [])
        for i, char_data in enumerate(characters):
            char = BlueprintCharacter(
                project_id=project_id,
                name=char_data.get("name", ""),
                identity=char_data.get("identity", ""),
                personality=char_data.get("personality", ""),
                goals=char_data.get("goals", ""),
                abilities=char_data.get("abilities", ""),
                relationship_to_protagonist=char_data.get("relationship_to_protagonist", ""),
                position=i,
            )
            self.session.add(char)

        # 先删除旧关系
        await self.session.execute(
            delete(BlueprintRelationship).where(BlueprintRelationship.project_id == project_id)
        )

        # 保存新关系
        relationships = data.get("relationships", [])
        for i, rel_data in enumerate(relationships):
            rel = BlueprintRelationship(
                project_id=project_id,
                character_from=rel_data.get("character_from", ""),
                character_to=rel_data.get("character_to", ""),
                description=rel_data.get("description", ""),
                position=i,
            )
            self.session.add(rel)

        await self.session.flush()

    def _select_sample_chapters(self, total: int) -> List[int]:
        """选择抽样章节索引"""
        if total <= 3:
            return list(range(total))

        indices = [0]  # 首章

        # 每10章抽1章
        step = max(1, total // 10)
        for i in range(step, total - 1, step):
            if i not in indices:
                indices.append(i)

        # 末章
        if total - 1 not in indices:
            indices.append(total - 1)

        return sorted(indices)[:10]  # 最多10章

    def _truncate_content(self, content: str) -> str:
        """截取内容"""
        if len(content) <= self.MAX_CONTENT_LENGTH:
            return content
        return content[:self.MAX_CONTENT_LENGTH] + "..."

    async def _get_chapter_outlines(self, project_id: str) -> List[ChapterOutline]:
        """获取所有章节大纲"""
        result = await self.session.execute(
            select(ChapterOutline)
            .where(ChapterOutline.project_id == project_id)
            .order_by(ChapterOutline.chapter_number)
        )
        return list(result.scalars().all())

    async def _load_existing_summaries(self, project_id: str) -> List[ChapterSummary]:
        """从现有大纲加载摘要（用于断点续传跳过阶段时）"""
        outlines = await self._get_chapter_outlines(project_id)
        summaries = []
        for outline in outlines:
            summaries.append(ChapterSummary(
                chapter_number=outline.chapter_number,
                title=outline.title,
                summary=outline.summary or "",
                key_characters=[],
                key_events=[],
            ))
        return summaries

    async def _load_existing_part_outlines(self, project_id: str) -> List[PartOutline]:
        """加载现有分部大纲（用于断点续传跳过阶段时）"""
        result = await self.session.execute(
            select(PartOutline)
            .where(PartOutline.project_id == project_id)
            .order_by(PartOutline.part_number)
        )
        return list(result.scalars().all())
