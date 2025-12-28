"""
摘要生成器

负责逐章生成分析数据和摘要。
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.novel import Chapter, NovelProject
from ...services.llm_service import LLMService
from ...services.llm_wrappers import call_llm_json, LLMProfile
from ...services.prompt_service import PromptService
from ...services.chapter_analysis_service import ChapterAnalysisService
from ...utils.json_utils import parse_llm_json_safe

from .models import ChapterSummary
from .data_helper import DataHelper
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """
    摘要生成器

    负责：
    1. 逐章生成分析数据（analysis_data）
    2. 逐章生成摘要
    """

    MAX_CONTENT_LENGTH = 12000  # 每章内容截取长度
    MAX_RETRIES = 2  # 单章最大重试次数

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: PromptService,
        data_helper: DataHelper,
        progress: ProgressTracker,
    ):
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.data_helper = data_helper
        self.progress = progress

    def _truncate_content(self, content: str) -> str:
        """截取内容"""
        if len(content) <= self.MAX_CONTENT_LENGTH:
            return content
        return content[:self.MAX_CONTENT_LENGTH] + "..."

    async def generate_analysis_data(
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

        已有 analysis_data 的章节会被跳过。
        """
        analysis_service = ChapterAnalysisService(self.session)
        project = await self.data_helper.get_project(project_id)
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
            title = await self.data_helper.get_chapter_title(chapter)

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

                # 调用分析服务
                analysis_data = await analysis_service.analyze_chapter(
                    content=self._truncate_content(content),
                    title=title,
                    chapter_number=chapter_num,
                    novel_title=project.title,
                    user_id=user_id,
                    timeout=180.0,
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

    async def analyze_chapters(
        self,
        project_id: str,
        chapters: List[Chapter],
        user_id: int,
    ) -> List[ChapterSummary]:
        """
        逐章生成摘要（阶段2，支持断点续传）

        利用已生成的 analysis_data 来辅助摘要生成。
        已有有效摘要的章节会被复用，不重新生成。
        """
        summaries = []
        total = len(chapters)
        project = await self.data_helper.get_project(project_id)

        # 构建章节映射
        chapter_map = {c.chapter_number: c for c in chapters}

        # 获取所有已有的章节大纲
        existing_outlines = await self.data_helper.get_chapter_outlines(project_id)
        outline_map = {o.chapter_number: o for o in existing_outlines}

        # 默认摘要标记
        DEFAULT_SUMMARY = "（导入章节，待分析）"

        # 分类章节
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

        # 先添加已有摘要
        for chapter, outline, existing_summary in chapters_with_summary:
            summaries.append(ChapterSummary(
                chapter_number=chapter.chapter_number,
                title=outline.title if outline else f"第{chapter.chapter_number}章",
                summary=existing_summary,
                key_characters=[],
                key_events=[],
            ))
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

        processed_count = len(chapters_with_summary)

        for chapter in chapters_to_process:
            if await self.progress.is_cancelled(project_id):
                return summaries

            chapter_num = chapter.chapter_number
            title = await self.data_helper.get_chapter_title(chapter)
            content = chapter.selected_version.content if chapter.selected_version else ""

            await self.progress.update(
                project_id=project_id,
                stage='analyzing_chapters',
                completed=processed_count,
                total=total,
                message=f"正在生成第{chapter_num}章摘要: {title}",
            )
            await self.session.commit()

            # 构建输入数据
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

            # 保存到 Chapter.real_summary
            if generated_summary and chapter_num in chapter_map:
                chapter_map[chapter_num].real_summary = generated_summary
                logger.debug("章节 %d 摘要已保存到 real_summary", chapter_num)

            processed_count += 1
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

        summaries.sort(key=lambda s: s.chapter_number)
        return summaries


__all__ = [
    "SummaryGenerator",
]
