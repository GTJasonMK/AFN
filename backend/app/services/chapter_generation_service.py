"""
章节生成服务

集中管理章节内容生成的完整业务流程，包括版本生成、摘要收集、提示词构建等。
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..models.novel import ChapterOutline
from ..utils.json_utils import remove_think_tags, unwrap_markdown_json, parse_llm_json_safe
from ..utils.exception_helpers import log_exception
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class ChapterGenerationService:
    """
    章节生成服务

    负责章节内容生成的核心业务逻辑，包括：
    - 版本数配置解析
    - 章节摘要收集
    - 蓝图数据准备
    - 写作提示词构建
    - 多版本并行/串行生成
    - 生成结果处理
    """

    def __init__(self, session: AsyncSession, llm_service: LLMService):
        """
        初始化章节生成服务

        Args:
            session: 数据库会话
            llm_service: LLM服务实例
        """
        self.session = session
        self.llm_service = llm_service

    def resolve_version_count(self) -> int:
        """
        确定章节生成的版本数量

        从统一配置系统获取，默认值为3

        Returns:
            int: 版本数量
        """
        return settings.writer_chapter_versions

    async def collect_chapter_summaries(
        self,
        project: Any,
        current_chapter_number: int,
        user_id: int,
        project_id: str,
    ) -> Tuple[List[Dict], str, str]:
        """
        收集已完成章节的摘要和上下文

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project: 项目对象
            current_chapter_number: 当前章节号
            user_id: 用户ID
            project_id: 项目ID

        Returns:
            tuple: (completed_chapters, previous_summary_text, previous_tail_excerpt)
        """
        outlines_map = {item.chapter_number: item for item in project.outlines}
        completed_chapters = []
        latest_prev_number = -1
        previous_summary_text = ""
        previous_tail_excerpt = ""

        # 第1步：收集所有需要处理的章节（分为已有摘要和缺少摘要两类）
        chapters_with_summary = []
        chapters_need_summary = []

        for existing in project.chapters:
            if existing.chapter_number >= current_chapter_number:
                continue
            if existing.selected_version is None or not existing.selected_version.content:
                continue

            if existing.real_summary:
                chapters_with_summary.append(existing)
            else:
                chapters_need_summary.append(existing)

        # 第2步：批量并行生成缺失的摘要（使用信号量控制并发数）
        if chapters_need_summary:
            logger.info(
                "项目 %s 需要生成 %d 个章节摘要，开始批量并行处理",
                project_id,
                len(chapters_need_summary)
            )

            # 使用信号量限制并发数（与并行章节生成一致）
            semaphore = asyncio.Semaphore(settings.writer_max_parallel_requests)

            async def generate_summary_with_limit(chapter):
                """带并发限制的摘要生成"""
                async with semaphore:
                    try:
                        summary = await self.llm_service.get_summary(
                            chapter.selected_version.content,
                            temperature=settings.llm_temp_summary,
                            user_id=user_id,
                            timeout=180.0,
                        )
                        return (chapter, remove_think_tags(summary), None)
                    except Exception as exc:
                        log_exception(
                            exc,
                            "生成章节摘要",
                            level="warning",
                            include_traceback=False,
                            project_id=project_id,
                            chapter_number=chapter.chapter_number,
                            user_id=user_id
                        )
                        return (chapter, "摘要生成失败，请稍后手动生成", exc)

            # 并行生成所有摘要
            results = await asyncio.gather(
                *[generate_summary_with_limit(ch) for ch in chapters_need_summary],
                return_exceptions=False  # 单个失败不影响其他任务
            )

            # 第3步：保存结果到数据库
            for chapter, summary, error in results:
                chapter.real_summary = summary
                if not error:
                    logger.debug(
                        "项目 %s 第 %s 章摘要生成成功",
                        project_id,
                        chapter.chapter_number
                    )

            logger.info(
                "项目 %s 批量摘要生成完成，成功 %d 个，失败 %d 个",
                project_id,
                sum(1 for _, _, err in results if not err),
                sum(1 for _, _, err in results if err)
            )

        # 第4步：合并所有章节并构建completed_chapters列表
        all_chapters = chapters_with_summary + chapters_need_summary
        all_chapters.sort(key=lambda ch: ch.chapter_number)

        for existing in all_chapters:
            completed_chapters.append(
                {
                    "chapter_number": existing.chapter_number,
                    "title": outlines_map.get(existing.chapter_number).title if outlines_map.get(existing.chapter_number) else f"第{existing.chapter_number}章",
                    "summary": existing.real_summary,
                }
            )

            if existing.chapter_number > latest_prev_number:
                latest_prev_number = existing.chapter_number
                previous_summary_text = existing.real_summary or ""
                # 导入extract_tail_excerpt函数
                from ..utils.writer_helpers import extract_tail_excerpt
                previous_tail_excerpt = extract_tail_excerpt(existing.selected_version.content)

        return completed_chapters, previous_summary_text, previous_tail_excerpt

    def prepare_blueprint_for_generation(self, blueprint_dict: Dict) -> Dict:
        """
        准备用于生成的蓝图数据，清理敏感字段

        Args:
            blueprint_dict: 原始蓝图字典

        Returns:
            Dict: 清理后的蓝图字典
        """
        # 转换relationships字段名
        if "relationships" in blueprint_dict and blueprint_dict["relationships"]:
            for relation in blueprint_dict["relationships"]:
                if "character_from" in relation:
                    relation["from"] = relation.pop("character_from")
                if "character_to" in relation:
                    relation["to"] = relation.pop("character_to")

        # 移除禁止的章节级别细节
        banned_blueprint_keys = {
            "chapter_outline",
            "chapter_summaries",
            "chapter_details",
            "chapter_dialogues",
            "chapter_events",
            "conversation_history",
            "character_timelines",
        }
        for key in banned_blueprint_keys:
            blueprint_dict.pop(key, None)

        return blueprint_dict

    def build_writing_prompt(
        self,
        outline: ChapterOutline,
        blueprint_dict: Dict,
        completed_chapters: List[Dict],
        previous_summary_text: str,
        previous_tail_excerpt: str,
        rag_context: Any,
        writing_notes: Optional[str],
        chapter_number: int,
    ) -> str:
        """
        构建章节写作提示词

        Args:
            outline: 章节大纲
            blueprint_dict: 蓝图字典
            completed_chapters: 已完成章节列表
            previous_summary_text: 上一章摘要
            previous_tail_excerpt: 上一章结尾
            rag_context: RAG检索上下文
            writing_notes: 写作备注
            chapter_number: 当前章节号

        Returns:
            str: 完整的写作提示词
        """
        outline_title = outline.title or f"第{outline.chapter_number}章"
        outline_summary = outline.summary or "暂无摘要"

        blueprint_text = json.dumps(blueprint_dict, ensure_ascii=False, indent=2)

        # 导入build_layered_summary函数
        from ..utils.writer_helpers import build_layered_summary
        completed_section = build_layered_summary(completed_chapters, chapter_number)

        previous_summary_text = previous_summary_text or "暂无可用摘要"
        previous_tail_excerpt = previous_tail_excerpt or "暂无上一章结尾内容"
        rag_chunks_text = "\n\n".join(rag_context.chunk_texts()) if rag_context.chunks else "未检索到章节片段"
        rag_summaries_text = "\n".join(rag_context.summary_lines()) if rag_context.summaries else "未检索到章节摘要"
        writing_notes = writing_notes or "无额外写作指令"

        prompt_sections = [
            ("[世界蓝图](JSON)", blueprint_text),
            ("[前情摘要]", completed_section),
            ("[上一章摘要]", previous_summary_text),
            ("[上一章结尾]", previous_tail_excerpt),
            ("[检索到的剧情上下文](Markdown)", rag_chunks_text),
            ("[检索到的章节摘要]", rag_summaries_text),
            (
                "[当前章节目标]",
                f"标题：{outline_title}\n摘要：{outline_summary}\n写作要求：{writing_notes}",
            ),
        ]
        return "\n\n".join(f"{title}\n{content}" for title, content in prompt_sections if content)

    async def generate_chapter_versions(
        self,
        version_count: int,
        writer_prompt: str,
        prompt_input: str,
        llm_config: Optional[Dict],
        skip_usage_tracking: bool,
        user_id: int,
        project_id: str,
        chapter_number: int,
    ) -> List[Dict]:
        """
        生成章节的多个版本（支持并行和串行）

        Args:
            version_count: 生成版本数
            writer_prompt: 系统提示词
            prompt_input: 用户提示词
            llm_config: 缓存的LLM配置
            skip_usage_tracking: 是否跳过用量追踪
            user_id: 用户ID
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            List[Dict]: 生成的版本列表
        """
        async def _generate_single_version(idx: int) -> Dict:
            task_id = id(asyncio.current_task())
            logger.info("[Task %s] 开始生成版本 %s", task_id, idx + 1)
            try:
                response = await self.llm_service.get_llm_response(
                    system_prompt=writer_prompt,
                    conversation_history=[{"role": "user", "content": prompt_input}],
                    temperature=settings.llm_temp_writing,
                    user_id=user_id,
                    timeout=600.0,
                    skip_usage_tracking=skip_usage_tracking,
                    skip_daily_limit_check=skip_usage_tracking,
                    cached_config=llm_config,
                )
                logger.info("[Task %s] 版本 %s LLM 响应获取成功", task_id, idx + 1)
                cleaned = remove_think_tags(response)

                # 尝试解析JSON（安全模式）
                result = parse_llm_json_safe(cleaned)
                if result:
                    return result
                else:
                    return {"content": unwrap_markdown_json(cleaned)}
            except Exception as exc:
                import traceback
                error_details = traceback.format_exc()
                logger.exception(
                    "[Task %s] 项目 %s 生成第 %s 章第 %s 个版本时发生异常\n异常类型: %s\n异常信息: %s\n完整堆栈:\n%s",
                    task_id,
                    project_id,
                    chapter_number,
                    idx + 1,
                    type(exc).__name__,
                    exc,
                    error_details,
                )
                if "Session is already flushing" in str(exc) or "already flushing" in str(exc).lower():
                    logger.error(
                        "[Task %s] !!!!! 检测到 Session flushing 冲突 !!!!!\n"
                        "当前任务ID: %s\n版本索引: %s\n"
                        "cached_config 是否存在: %s\nskip_usage_tracking: %s\n完整异常: %s",
                        task_id, task_id, idx, bool(llm_config), skip_usage_tracking, error_details,
                    )
                return {"content": f"生成失败: {exc}"}

        logger.info(
            "项目 %s 第 %s 章计划生成 %s 个版本（并行模式配置：%s）",
            project_id, chapter_number, version_count, settings.writer_parallel_generation,
        )

        start_time = time.time()

        # 检查并行模式的前提条件：必须有缓存配置且跳过使用追踪
        # 这是为了避免Session并发冲突（并行任务不应该访问数据库）
        can_parallel = (
            settings.writer_parallel_generation
            and llm_config is not None  # 必须预先缓存LLM配置
            and skip_usage_tracking is True  # 必须跳过使用次数追踪
        )

        if not can_parallel and settings.writer_parallel_generation:
            logger.warning(
                "项目 %s 第 %s 章无法使用并行模式（前提条件不满足），降级为串行模式\n"
                "  - llm_config 是否存在: %s\n"
                "  - skip_usage_tracking: %s\n"
                "原因：并行模式要求预先缓存LLM配置且跳过使用追踪，以避免Session并发冲突",
                project_id, chapter_number, bool(llm_config), skip_usage_tracking
            )

        if can_parallel:
            # 并行模式
            logger.info(
                "项目 %s 第 %s 章进入并行生成模式\n  - 版本数: %s\n  - 最大并发数: %s\n"
                "  - cached_config 是否存在: %s\n  - skip_usage_tracking: %s\n  - session.autoflush: %s",
                project_id, chapter_number, version_count, settings.writer_max_parallel_requests,
                bool(llm_config), skip_usage_tracking, self.session.autoflush,
            )

            semaphore = asyncio.Semaphore(settings.writer_max_parallel_requests)

            async def _generate_with_semaphore(idx: int) -> Dict:
                async with semaphore:
                    logger.info("项目 %s 第 %s 章开始生成版本 %s/%s", project_id, chapter_number, idx + 1, version_count)
                    result = await _generate_single_version(idx)
                    logger.info("项目 %s 第 %s 章版本 %s/%s 生成完成", project_id, chapter_number, idx + 1, version_count)
                    return result

            logger.info("项目 %s 第 %s 章开始并行执行，进入 no_autoflush 上下文", project_id, chapter_number)
            with self.session.no_autoflush:
                logger.info("session.no_autoflush 已启用，session.autoflush=%s", self.session.autoflush)
                tasks = [_generate_with_semaphore(idx) for idx in range(version_count)]
                logger.info("项目 %s 第 %s 章创建了 %s 个并行任务，开始执行 gather", project_id, chapter_number, len(tasks))
                raw_versions = await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("项目 %s 第 %s 章 gather 执行完成，退出 no_autoflush 上下文", project_id, chapter_number)

            # 处理异常结果
            processed_versions = []
            for idx, result in enumerate(raw_versions):
                if isinstance(result, Exception):
                    logger.error("项目 %s 第 %s 章版本 %s 生成失败: %s", project_id, chapter_number, idx + 1, result)
                    processed_versions.append({"content": f"生成失败: {result}"})
                else:
                    processed_versions.append(result)
            raw_versions = processed_versions
        else:
            # 串行模式
            raw_versions = []
            for idx in range(version_count):
                logger.info("项目 %s 第 %s 章开始生成版本 %s/%s（串行模式）", project_id, chapter_number, idx + 1, version_count)
                raw_versions.append(await _generate_single_version(idx))

        elapsed_time = time.time() - start_time
        logger.info(
            "项目 %s 第 %s 章所有版本生成完成，耗时 %.2f 秒（实际模式：%s）",
            project_id, chapter_number, elapsed_time, "并行" if can_parallel else "串行",
        )

        return raw_versions

    def process_generated_versions(self, raw_versions: List[Any]) -> Tuple[List[str], List[Dict]]:
        """
        处理生成的版本数据，提取content和metadata

        Args:
            raw_versions: 原始版本数据列表

        Returns:
            tuple: (contents, metadata)
        """
        contents: List[str] = []
        metadata: List[Dict] = []

        for variant in raw_versions:
            if isinstance(variant, dict):
                # 按优先级检查可能的内容字段（writing.md提示词中使用的是full_content）
                if "content" in variant and isinstance(variant["content"], str):
                    contents.append(variant["content"])
                elif "full_content" in variant and isinstance(variant["full_content"], str):
                    # 提取full_content字段（writing.md提示词要求的格式）
                    contents.append(variant["full_content"])
                elif "chapter_content" in variant:
                    contents.append(str(variant["chapter_content"]))
                else:
                    # 如果所有预期字段都不存在，fallback到整个dict的序列化
                    contents.append(json.dumps(variant, ensure_ascii=False))
                metadata.append(variant)
            else:
                contents.append(str(variant))
                metadata.append({"raw": variant})

        return contents, metadata
