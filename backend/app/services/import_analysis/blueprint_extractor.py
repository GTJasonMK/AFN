"""
蓝图提取器

负责从已有内容反推蓝图。
"""

import json
import logging
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.novel import Chapter, NovelProject
from ...models.part_outline import PartOutline
from ...services.llm_service import LLMService
from ...services.llm_wrappers import call_llm_json, LLMProfile
from ...services.prompt_service import PromptService
from ...utils.json_utils import parse_llm_json_safe

from .models import ChapterSummary
from .data_helper import DataHelper
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class BlueprintExtractor:
    """
    蓝图提取器

    负责从已有内容反推蓝图
    """

    MAX_SUMMARIES_FOR_BLUEPRINT = 50  # 蓝图反推最多使用的摘要数
    MAX_SUMMARY_LENGTH = 150  # 蓝图反推时单章摘要最大长度

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

    async def extract_blueprint(
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
        """
        prompt = await self.prompt_service.get_prompt("reverse_blueprint")
        if not prompt:
            prompt = "请从小说内容中提取蓝图信息。"

        # 收集所有章节的 analysis_data 中的角色和伏笔信息
        all_characters, all_foreshadowing = self._collect_analysis_data(chapters)

        # 抽样章节内容（用于风格分析）
        sample_chapters = self._sample_chapter_contents(chapters)

        # 采样摘要
        sampled_summaries = self._sample_summaries(summaries)

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
            "extracted_characters": list(all_characters.values())[:20],
            "extracted_foreshadowing": all_foreshadowing[:30],
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
                await self.data_helper.save_blueprint(
                    project_id, result, len(chapters), part_outlines is not None
                )

        except Exception as e:
            logger.warning("蓝图反推失败: %s，创建基础蓝图", e)
            await self.data_helper.save_blueprint(
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

    def _collect_analysis_data(
        self,
        chapters: List[Chapter],
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """收集所有章节的 analysis_data"""
        all_characters = {}
        all_foreshadowing = []

        for chapter in chapters:
            if chapter.analysis_data:
                # 收集角色
                for char in chapter.analysis_data.get("characters", []):
                    if isinstance(char, dict):
                        char_name = char.get("name", "")
                        if char_name and char_name not in all_characters:
                            all_characters[char_name] = char

                # 收集伏笔
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

    def _sample_chapter_contents(self, chapters: List[Chapter]) -> List[Dict[str, Any]]:
        """抽样章节内容（用于风格分析）"""
        sample_indices = self._select_sample_chapters(len(chapters))
        sample_chapters = []

        for idx in sample_indices:
            if idx < len(chapters):
                c = chapters[idx]
                content = c.selected_version.content if c.selected_version else ""
                sample_chapters.append({
                    "chapter_number": c.chapter_number,
                    "content": content[:6000],
                })

        return sample_chapters

    def _sample_summaries(self, summaries: List[ChapterSummary]) -> List[ChapterSummary]:
        """采样摘要：对于超长小说，均匀采样"""
        total_summaries = len(summaries)

        if total_summaries > self.MAX_SUMMARIES_FOR_BLUEPRINT:
            step = total_summaries // self.MAX_SUMMARIES_FOR_BLUEPRINT
            sampled = summaries[::step][:self.MAX_SUMMARIES_FOR_BLUEPRINT]
            logger.info(
                "摘要采样：从 %d 章采样 %d 章用于蓝图反推",
                total_summaries, len(sampled)
            )
            return sampled

        return summaries

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

        return sorted(indices)[:10]


__all__ = [
    "BlueprintExtractor",
]
