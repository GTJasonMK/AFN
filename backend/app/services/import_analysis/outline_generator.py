"""
大纲生成器

负责章节大纲和分部大纲的生成。
"""

import json
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.part_outline import PartOutline
from ...services.llm_service import LLMService
from ...services.llm_wrappers import call_llm_json, LLMProfile
from ...services.prompt_service import PromptService
from ...utils.json_utils import parse_llm_json_safe

from .models import ChapterSummary
from .data_helper import DataHelper
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class OutlineGenerator:
    """
    大纲生成器

    负责：
    1. 更新章节大纲
    2. 生成分部大纲（仅长篇>=50章）
    """

    MAX_CHAPTERS_FOR_LLM_OUTLINE = 100  # 超过此数量跳过LLM标准化大纲

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

    async def update_chapter_outlines(
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
                await self.data_helper.upsert_chapter_outline(
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
                await self.data_helper.upsert_chapter_outline(
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
        project = await self.data_helper.get_project(project_id)
        input_data = {
            "novel_title": project.title,
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
                    await self.data_helper.upsert_chapter_outline(
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
                await self.data_helper.upsert_chapter_outline(
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

    async def generate_part_outlines(
        self,
        project_id: str,
        summaries: List[ChapterSummary],
        user_id: int,
    ) -> List[PartOutline]:
        """生成分部大纲（阶段4，仅长篇）

        上下文优化：
        - 先预分组章节（每25章一组）
        - 对每个分组单独调用LLM生成大纲
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

        project = await self.data_helper.get_project(project_id)
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

            # 构建输入数据
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
                        "summary": s.summary[:200] if s.summary else "",
                    }
                    for s in part_summaries
                ],
            }

            # 添加前后分部的简要上下文
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
                    part = self._create_default_part_outline(
                        project_id, part_idx + 1, part_summaries
                    )
                    self.session.add(part)
                    part_outlines.append(part)

            except Exception as e:
                logger.warning("分部 %d 大纲生成失败: %s", part_idx + 1, e)
                part = self._create_default_part_outline(
                    project_id, part_idx + 1, part_summaries
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

    def _create_default_part_outline(
        self,
        project_id: str,
        part_number: int,
        part_summaries: List[ChapterSummary],
    ) -> PartOutline:
        """创建默认分部大纲"""
        return PartOutline(
            project_id=project_id,
            part_number=part_number,
            title=f"第{part_number}部",
            start_chapter=part_summaries[0].chapter_number,
            end_chapter=part_summaries[-1].chapter_number,
            summary=f"第{part_summaries[0].chapter_number}-{part_summaries[-1].chapter_number}章内容",
            generation_status="completed",
        )


__all__ = [
    "OutlineGenerator",
]
