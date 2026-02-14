"""
导入分析主服务

协调外部小说导入和智能分析的完整流程。
"""

import json
import logging
import math
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.constants import NovelConstants
from ...core.state_machine import ProjectStatus
from ...services.llm_service import LLMService
from ...services.llm_wrappers import call_llm_json, LLMProfile
from ...services.prompt_service import PromptService
from ...services.chapter_analysis_service import ChapterAnalysisService
from ...services.summary_service import SummaryService
from ...services.blueprint_service import BlueprintService
from ...services.part_outline.service import PartOutlineService
from ...services.chapter_version_service import ChapterVersionService
from ...repositories.novel_repository import NovelRepository
from ...repositories.chapter_outline_repository import ChapterOutlineRepository
from ...utils.content_normalizer import count_chinese_characters
from ...utils.json_utils import parse_llm_json_safe
from ...exceptions import PermissionDeniedError

from .txt_parser import TxtParser
from .progress_tracker import ProgressTracker
from .models import ChapterSummary, ImportResult

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
    - 阶段4（蓝图反推）：采样摘要（最多50章）并压缩单章摘要长度
    - 阶段5（分部大纲）：复用 PartOutlineService 按章节数量生成
    """

    MAX_CONTENT_LENGTH = 12000
    MAX_CHAPTERS_FOR_LLM_OUTLINE = 100
    MAX_SUMMARIES_FOR_BLUEPRINT = 50
    MAX_SUMMARY_LENGTH = 150

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

        # 仓储与标准服务
        self.novel_repo = NovelRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)
        self.chapter_version_service = ChapterVersionService(session)
        self.chapter_analysis_service = ChapterAnalysisService(session)
        self.summary_service = SummaryService(llm_service)
        self.blueprint_service = BlueprintService(session)
        self.part_outline_service = PartOutlineService(session)

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
        project = await self.novel_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")
        if int(getattr(project, "user_id", 0) or 0) != int(user_id):
            raise PermissionDeniedError("无权访问该项目")

        # 3. 创建章节数据
        chapters_info = []
        for parsed_chapter in parse_result.chapters:
            # 创建或更新章节大纲
            await self.chapter_outline_repo.upsert_outline(
                project_id=project_id,
                chapter_number=parsed_chapter.chapter_number,
                title=parsed_chapter.title,
                summary="（导入章节，待分析）",
            )

            # 创建或更新章节版本
            chapter = await self.chapter_version_service.get_or_create_chapter(
                project_id=project_id,
                chapter_number=parsed_chapter.chapter_number,
            )
            versions = await self.chapter_version_service.replace_chapter_versions(
                chapter,
                [parsed_chapter.content],
                metadata=None,
            )

            if versions:
                selected = versions[0]
                chapter.selected_version_id = selected.id
                chapter.selected_version = selected
                chapter.word_count = count_chinese_characters(parsed_chapter.content)
                chapter.status = "successful" if parsed_chapter.content.strip() else "waiting_for_confirm"

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
        执行完整分析流程（支持断点续传）

        阶段:
        1. generating_analysis_data - 逐章生成分析数据
        2. analyzing_chapters - 逐章生成摘要
        3. generating_outlines - 更新章节大纲
        4. extracting_blueprint - 反推蓝图
        5. generating_part_outlines - 生成分部大纲（仅长篇>=50章）

        断点续传:
        - 如果之前分析中断，会从上次的阶段继续
        - 已生成的 analysis_data 和摘要会被复用
        """
        try:
            # 获取项目和章节
            project = await self.novel_repo.get_by_id(project_id)
            if not project:
                raise ValueError(f"项目不存在: {project_id}")
            if int(getattr(project, "user_id", 0) or 0) != int(user_id):
                raise PermissionDeniedError("无权访问该项目")

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
                'extracting_blueprint',
                'generating_part_outlines',
            ]

            # 确定起始阶段索引
            start_stage_idx = 0
            if resume_from_stage and resume_from_stage in stage_order:
                start_stage_idx = stage_order.index(resume_from_stage)

            # ========== 阶段1: 逐章生成分析数据 ==========
            if start_stage_idx <= stage_order.index('generating_analysis_data'):
                await self.progress.advance_stage(project_id, 'generating_analysis_data')
                await self.session.commit()

                await self._generate_analysis_data(
                    project_id=project_id,
                    chapters=chapters,
                    project_title=project.title,
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
                project = await self.novel_repo.get_by_id(project_id)
                chapters = sorted(project.chapters, key=lambda c: c.chapter_number)

                summaries = await self._generate_summaries(
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
                    project_title=project.title,
                    user_id=user_id,
                )

                if await self.progress.is_cancelled(project_id):
                    return
            else:
                logger.info("跳过阶段 'generating_outlines'（已完成）")

            # ========== 阶段4: 反推蓝图 ==========
            if start_stage_idx <= stage_order.index('extracting_blueprint'):
                await self.progress.advance_stage(project_id, 'extracting_blueprint')
                await self.session.commit()

                # 重新加载章节以获取 analysis_data
                project = await self.novel_repo.get_by_id(project_id)
                chapters = sorted(project.chapters, key=lambda c: c.chapter_number)

                await self._extract_blueprint(
                    project_id=project_id,
                    project=project,
                    chapters=chapters,
                    summaries=summaries,
                    needs_part_outlines=needs_part_outlines,
                    user_id=user_id,
                )
            else:
                logger.info("跳过阶段 'extracting_blueprint'（已完成）")

            if await self.progress.is_cancelled(project_id):
                return

            # ========== 阶段5: 生成分部大纲（如果需要） ==========
            if needs_part_outlines:
                if start_stage_idx <= stage_order.index('generating_part_outlines'):
                    await self.progress.advance_stage(project_id, 'generating_part_outlines')
                    await self.session.commit()

                    await self._generate_part_outlines(
                        project_id=project_id,
                        total_chapters=total_chapters,
                        user_id=user_id,
                    )
                else:
                    logger.info("跳过阶段 'generating_part_outlines'（已完成）")

            # 更新项目状态为WRITING
            project = await self.novel_repo.get_by_id(project_id)
            project.status = ProjectStatus.WRITING.value
            await self.progress.mark_completed(project_id)
            await self.session.commit()

            logger.info("项目 %s 分析完成", project_id)

        except Exception as e:
            logger.exception("项目 %s 分析失败: %s", project_id, e)
            await self.progress.mark_failed(project_id, str(e))
            await self.session.commit()
            raise

    def _truncate_content(self, content: str) -> str:
        """截断内容以避免上下文过长"""
        if len(content) <= self.MAX_CONTENT_LENGTH:
            return content
        return content[:self.MAX_CONTENT_LENGTH] + "..."

    async def _get_chapter_title(self, project_id: str, chapter_number: int) -> str:
        """获取章节标题（优先使用大纲）"""
        outline = await self.chapter_outline_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        return outline.title if outline else f"第{chapter_number}章"

    async def _generate_analysis_data(
        self,
        project_id: str,
        chapters: List[Any],
        project_title: str,
        user_id: int,
    ) -> None:
        """逐章生成分析数据"""
        total = len(chapters)
        chapters_with_data = sum(1 for c in chapters if c.analysis_data)
        chapters_to_process = [c for c in chapters if not c.analysis_data]

        logger.info(
            "开始逐章生成分析数据，共 %d 章，已有数据 %d 章，需生成 %d 章",
            total, chapters_with_data, len(chapters_to_process)
        )

        processed_count = chapters_with_data

        for chapter in chapters_to_process:
            if await self.progress.is_cancelled(project_id):
                return

            chapter_num = chapter.chapter_number
            title = await self._get_chapter_title(project_id, chapter_num)
            content = chapter.selected_version.content if chapter.selected_version else ""
            if not content.strip():
                logger.warning("章节 %d 内容为空，跳过分析", chapter_num)
                processed_count += 1
                continue

            await self.progress.update(
                project_id=project_id,
                stage='generating_analysis_data',
                completed=processed_count,
                total=total,
                message=f"正在分析第{chapter_num}章: {title}",
            )
            await self.session.commit()

            try:
                analysis_data = await self.chapter_analysis_service.analyze_and_store_chapter_analysis(
                    chapter=chapter,
                    content=self._truncate_content(content),
                    title=title,
                    chapter_number=chapter_num,
                    novel_title=project_title,
                    user_id=user_id,
                    timeout=180.0,
                )
                if analysis_data:
                    logger.debug("章节 %d 分析数据生成成功", chapter_num)
                else:
                    logger.warning("章节 %d 分析数据为空", chapter_num)
            except Exception as exc:
                logger.warning("章节 %d 分析数据生成失败: %s", chapter_num, exc)

            processed_count += 1
            await self.session.commit()

        await self.progress.update(
            project_id=project_id,
            stage='generating_analysis_data',
            completed=total,
            total=total,
            message="分析数据生成完成",
        )
        await self.session.commit()

    async def _generate_summaries(
        self,
        project_id: str,
        chapters: List[Any],
        user_id: int,
    ) -> List[ChapterSummary]:
        """逐章生成摘要（复用 SummaryService）"""
        summaries: List[ChapterSummary] = []
        total = len(chapters)
        DEFAULT_SUMMARY = "（导入章节，待分析）"

        outlines = await self.chapter_outline_repo.list_by_project(project_id)
        outline_map = {o.chapter_number: o for o in outlines}

        chapters_with_summary = []
        chapters_to_process = []

        for chapter in chapters:
            outline = outline_map.get(chapter.chapter_number)
            has_outline_summary = outline and outline.summary and outline.summary != DEFAULT_SUMMARY
            has_real_summary = chapter.real_summary and chapter.real_summary.strip()

            if has_outline_summary or has_real_summary:
                existing_summary = chapter.real_summary if has_real_summary else outline.summary
                chapters_with_summary.append((chapter, outline, existing_summary))
            else:
                chapters_to_process.append(chapter)

        logger.info(
            "开始逐章生成摘要，共 %d 章，已有摘要 %d 章，需生成 %d 章",
            total, len(chapters_with_summary), len(chapters_to_process)
        )

        for chapter, outline, existing_summary in chapters_with_summary:
            title = outline.title if outline else f"第{chapter.chapter_number}章"
            summaries.append(ChapterSummary(
                chapter_number=chapter.chapter_number,
                title=title,
                summary=existing_summary,
                key_characters=[],
                key_events=[],
            ))
            if not chapter.real_summary:
                chapter.real_summary = existing_summary

        processed_count = len(chapters_with_summary)

        for chapter in chapters_to_process:
            if await self.progress.is_cancelled(project_id):
                return summaries

            chapter_num = chapter.chapter_number
            title = await self._get_chapter_title(project_id, chapter_num)
            content = chapter.selected_version.content if chapter.selected_version else ""

            await self.progress.update(
                project_id=project_id,
                stage='analyzing_chapters',
                completed=processed_count,
                total=total,
                message=f"正在生成第{chapter_num}章摘要: {title}",
            )
            await self.session.commit()

            summary_text = await self.summary_service.generate_summary(
                self._truncate_content(content),
                user_id,
            )
            if not summary_text:
                summary_text = content[:200] + "..." if len(content) > 200 else content

            summaries.append(ChapterSummary(
                chapter_number=chapter_num,
                title=title,
                summary=summary_text,
                key_characters=[],
                key_events=[],
            ))
            chapter.real_summary = summary_text
            await self.chapter_outline_repo.upsert_outline(
                project_id=project_id,
                chapter_number=chapter_num,
                title=title,
                summary=summary_text,
            )

            processed_count += 1
            await self.session.commit()

        await self.progress.update(
            project_id=project_id,
            stage='analyzing_chapters',
            completed=total,
            total=total,
            message="摘要生成完成",
        )
        await self.session.commit()

        summaries.sort(key=lambda s: s.chapter_number)
        return summaries

    async def _load_existing_summaries(self, project_id: str) -> List[ChapterSummary]:
        """从现有大纲加载摘要"""
        outlines = await self.chapter_outline_repo.list_by_project(project_id)
        return [
            ChapterSummary(
                chapter_number=o.chapter_number,
                title=o.title,
                summary=o.summary or "",
                key_characters=[],
                key_events=[],
            )
            for o in outlines
        ]

    async def _update_chapter_outlines(
        self,
        project_id: str,
        summaries: List[ChapterSummary],
        project_title: str,
        user_id: int,
    ) -> None:
        """根据摘要更新章节大纲"""
        total_chapters = len(summaries)
        use_llm = total_chapters <= self.MAX_CHAPTERS_FOR_LLM_OUTLINE
        prompt = await self.prompt_service.get_prompt_or_default(
            "reverse_outline",
            logger=logger,
        )
        if not prompt:
            use_llm = False

        if not use_llm:
            for s in summaries:
                await self.chapter_outline_repo.upsert_outline(
                    project_id=project_id,
                    chapter_number=s.chapter_number,
                    title=s.title,
                    summary=s.summary[:500] if s.summary else "",
                )
            await self.progress.update(
                project_id=project_id,
                stage='generating_outlines',
                completed=1,
                total=1,
            )
            await self.session.commit()
            return

        input_data = {
            "novel_title": project_title,
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
            if result and result.get("outlines"):
                for outline in result["outlines"]:
                    await self.chapter_outline_repo.upsert_outline(
                        project_id=project_id,
                        chapter_number=outline.get("chapter_number", 0),
                        title=outline.get("title", ""),
                        summary=outline.get("summary", ""),
                    )
                updated = True
                logger.info("使用LLM标准化大纲成功，共 %d 章", len(result["outlines"]))
            else:
                logger.warning("LLM返回结果缺少outlines字段，使用原始摘要")
        except Exception as exc:
            logger.warning("大纲标准化失败: %s，使用原始摘要", exc)

        if not updated:
            for s in summaries:
                await self.chapter_outline_repo.upsert_outline(
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

    async def _extract_blueprint(
        self,
        project_id: str,
        project: Any,
        chapters: List[Any],
        summaries: List[ChapterSummary],
        needs_part_outlines: bool,
        user_id: int,
    ) -> None:
        """反推蓝图并写入标准蓝图服务"""
        prompt = await self.prompt_service.get_prompt_or_default(
            "reverse_blueprint",
            logger=logger,
        )

        patch = self._build_blueprint_patch(
            project=project,
            total_chapters=len(chapters),
            needs_part_outlines=needs_part_outlines,
            result=None,
        )

        if prompt:
            all_characters, all_foreshadowing = self._collect_analysis_data(chapters)
            sample_chapters = self._sample_chapter_contents(chapters)
            sampled_summaries = self._sample_summaries(summaries)
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
                "extracted_characters": list(all_characters.values())[:20],
                "extracted_foreshadowing": all_foreshadowing[:30],
            }

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
                    patch = self._build_blueprint_patch(
                        project=project,
                        total_chapters=len(chapters),
                        needs_part_outlines=needs_part_outlines,
                        result=result,
                    )
            except Exception as exc:
                logger.warning("蓝图反推失败: %s，使用基础蓝图", exc)

        await self.blueprint_service.patch_blueprint(project_id, patch)
        await self.progress.update(
            project_id=project_id,
            stage='extracting_blueprint',
            completed=1,
            total=1,
        )
        await self.session.commit()

    def _build_blueprint_patch(
        self,
        project: Any,
        total_chapters: int,
        needs_part_outlines: bool,
        result: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """构建蓝图补丁数据"""
        patch: Dict[str, Any] = {
            "title": project.title,
            "genre": "未知",
            "style": "未知",
            "tone": "未知",
            "target_audience": "",
            "one_sentence_summary": project.title,
            "full_synopsis": "（待补充）",
            "world_setting": {},
            "characters": [],
            "relationships": [],
        }

        if result:
            for key in (
                "title",
                "target_audience",
                "genre",
                "style",
                "tone",
                "one_sentence_summary",
                "full_synopsis",
                "world_setting",
            ):
                if key in result:
                    patch[key] = result.get(key) or patch[key]
            if result.get("characters"):
                patch["characters"] = result.get("characters", [])
            if result.get("relationships"):
                patch["relationships"] = result.get("relationships", [])

        patch["total_chapters"] = total_chapters
        patch["needs_part_outlines"] = needs_part_outlines
        patch["chapters_per_part"] = NovelConstants.CHAPTERS_PER_PART

        return patch

    def _collect_analysis_data(
        self,
        chapters: List[Any],
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """收集章节分析数据中的角色与伏笔"""
        all_characters: Dict[str, Any] = {}
        all_foreshadowing: List[Dict[str, Any]] = []

        for chapter in chapters:
            if chapter.analysis_data:
                for char in chapter.analysis_data.get("characters", []):
                    if isinstance(char, dict):
                        name = char.get("name", "")
                        if name and name not in all_characters:
                            all_characters[name] = char

                for foreshadow in chapter.analysis_data.get("foreshadowing", []):
                    if isinstance(foreshadow, dict):
                        all_foreshadowing.append({
                            "chapter": chapter.chapter_number,
                            **foreshadow,
                        })
                    elif isinstance(foreshadow, str):
                        all_foreshadowing.append({
                            "chapter": chapter.chapter_number,
                            "content": foreshadow,
                        })

        return all_characters, all_foreshadowing

    def _sample_chapter_contents(self, chapters: List[Any]) -> List[Dict[str, Any]]:
        """抽样章节内容"""
        sample_indices = self._select_sample_chapters(len(chapters))
        sample_chapters: List[Dict[str, Any]] = []

        for idx in sample_indices:
            if idx < len(chapters):
                chapter = chapters[idx]
                content = chapter.selected_version.content if chapter.selected_version else ""
                sample_chapters.append({
                    "chapter_number": chapter.chapter_number,
                    "content": content[:6000],
                })

        return sample_chapters

    def _sample_summaries(self, summaries: List[ChapterSummary]) -> List[ChapterSummary]:
        """采样摘要列表"""
        total = len(summaries)
        if total > self.MAX_SUMMARIES_FOR_BLUEPRINT:
            step = total // self.MAX_SUMMARIES_FOR_BLUEPRINT
            sampled = summaries[::step][:self.MAX_SUMMARIES_FOR_BLUEPRINT]
            logger.info(
                "摘要采样：从 %d 章采样 %d 章用于蓝图反推",
                total, len(sampled)
            )
            return sampled
        return summaries

    def _select_sample_chapters(self, total: int) -> List[int]:
        """选择抽样章节索引"""
        if total <= 3:
            return list(range(total))

        indices = [0]
        step = max(1, total // 10)
        for i in range(step, total - 1, step):
            if i not in indices:
                indices.append(i)

        if total - 1 not in indices:
            indices.append(total - 1)

        return sorted(indices)[:10]

    async def _generate_part_outlines(
        self,
        project_id: str,
        total_chapters: int,
        user_id: int,
    ) -> None:
        """生成分部大纲（复用 PartOutlineService）"""
        chapters_per_part = NovelConstants.CHAPTERS_PER_PART
        part_count = math.ceil(total_chapters / chapters_per_part)

        await self.part_outline_service.generate_part_outlines(
            project_id=project_id,
            user_id=user_id,
            total_chapters=total_chapters,
            chapters_per_part=chapters_per_part,
            skip_status_update=True,
        )

        await self.progress.update(
            project_id=project_id,
            stage='generating_part_outlines',
            completed=part_count,
            total=part_count,
            message="分部大纲生成完成",
        )
        await self.session.commit()


__all__ = [
    "ImportAnalysisService",
]
