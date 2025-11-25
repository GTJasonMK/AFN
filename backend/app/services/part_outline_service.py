import asyncio
import json
import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.state_machine import ProjectStatus
from ..core.constants import NovelConstants, LLMConstants
from ..models.part_outline import PartOutline
from ..models.novel import ChapterOutline, NovelProject
from ..utils.exception_helpers import log_exception
from ..repositories.part_outline_repository import PartOutlineRepository
from ..repositories.novel_repository import NovelRepository
from ..repositories.chapter_repository import ChapterOutlineRepository
from ..schemas.novel import (
    PartOutline as PartOutlineSchema,
    PartOutlineGenerationProgress,
    ChapterOutline as ChapterOutlineSchema,
)
from ..utils.json_utils import remove_think_tags, unwrap_markdown_json
from .llm_service import LLMService
from .prompt_service import PromptService
from .novel_service import NovelService
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class GenerationCancelledException(Exception):
    """生成被用户取消的异常"""
    pass


class PartOutlineService:
    """部分大纲服务，负责长篇小说的分层大纲生成"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PartOutlineRepository(session)
        self.novel_repo = NovelRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)
        self.llm_service = LLMService(session)
        self.prompt_service = PromptService(session)
        self.novel_service = NovelService(session)  # 用于复用权限检查逻辑
        self.prompt_builder = PromptBuilder(part_outline_repo=self.repo)

    async def _check_if_cancelled(self, part_outline: PartOutline) -> bool:
        """
        检查部分大纲是否被请求取消

        参数：
            part_outline: 部分大纲对象

        返回：
            bool: 如果被取消返回True

        抛出：
            GenerationCancelledException: 如果检测到取消状态
        """
        # 刷新对象以获取最新状态
        await self.session.refresh(part_outline)

        if part_outline.generation_status == "cancelling":
            logger.info("检测到第 %d 部分被请求取消生成", part_outline.part_number)
            raise GenerationCancelledException(f"第 {part_outline.part_number} 部分的生成已被取消")

        return False

    async def cancel_part_generation(
        self,
        project_id: str,
        part_number: int,
        user_id: int,
    ) -> bool:
        """
        取消指定部分的大纲生成

        参数：
            project_id: 项目ID
            part_number: 部分编号
            user_id: 用户ID

        返回：
            bool: 是否成功设置取消标志
        """
        # 验证权限
        await self.novel_service.ensure_project_owner(project_id, user_id)

        # 获取部分大纲
        part_outline = await self.repo.get_by_part_number(project_id, part_number)
        if not part_outline:
            raise HTTPException(status_code=404, detail=f"未找到第 {part_number} 部分的大纲")

        # 只有正在生成的任务才能取消
        if part_outline.generation_status != "generating":
            logger.warning(
                "第 %d 部分当前状态为 %s，无法取消",
                part_number,
                part_outline.generation_status,
            )
            return False

        # 设置为取消中状态
        await self.repo.update_status(part_outline, "cancelling", part_outline.progress)
        await self.session.commit()

        logger.info("第 %d 部分已设置为取消中状态", part_number)
        return True

    async def cleanup_stale_generating_status(
        self,
        project_id: str,
        timeout_minutes: int = 15,
    ) -> int:
        """
        清理超时的generating状态，将其改为failed

        参数：
            project_id: 项目ID
            timeout_minutes: 超时时间（分钟），默认15分钟

        返回：
            int: 清理的数量
        """
        all_parts = await self.repo.get_by_project_id(project_id)
        timeout_threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
        cleaned_count = 0

        for part in all_parts:
            # 检查是否处于generating状态且更新时间超过阈值
            if part.generation_status == "generating":
                # 防御性检查：updated_at可能为None
                if part.updated_at is None or part.updated_at < timeout_threshold:
                    logger.warning(
                        "检测到第 %d 部分超时（超过%d分钟未更新），将状态改为failed",
                        part.part_number,
                        timeout_minutes,
                    )
                    await self.repo.update_status(part, "failed", 0)
                    cleaned_count += 1

        if cleaned_count > 0:
            await self.session.commit()
            logger.info("项目 %s 清理了 %d 个超时状态", project_id, cleaned_count)

        return cleaned_count

    async def _validate_part_outline_request(
        self,
        project_id: str,
        user_id: int,
        total_chapters: int,
    ) -> NovelProject:
        """
        验证部分大纲生成请求

        参数:
            project_id: 项目ID
            user_id: 用户ID
            total_chapters: 总章节数

        返回:
            NovelProject: 验证通过的项目对象

        抛出:
            HTTPException: 如果验证失败
        """
        # 检查章节数是否需要分部分
        if total_chapters < NovelConstants.LONG_NOVEL_THRESHOLD:
            raise HTTPException(
                status_code=400,
                detail=f"章节数为 {total_chapters}，不需要使用部分大纲功能（仅适用于{NovelConstants.LONG_NOVEL_THRESHOLD}章及以上的长篇小说）",
            )

        # 获取项目信息
        project = await self.novel_service.ensure_project_owner(project_id, user_id)

        if not project.blueprint:
            raise HTTPException(status_code=400, detail="项目蓝图未生成，无法创建部分大纲")

        return project

    def _prepare_blueprint_data(self, project: NovelProject) -> tuple[Dict, str, List[Dict]]:
        """
        准备蓝图数据

        参数:
            project: 项目对象

        返回:
            tuple: (world_setting, full_synopsis, characters)
        """
        world_setting = project.blueprint.world_setting or {}
        full_synopsis = project.blueprint.full_synopsis or ""

        # 将BlueprintCharacter模型转换为字典列表
        characters = [
            {
                "name": char.name,
                "identity": char.identity or "",
                "personality": char.personality or "",
                "goals": char.goals or "",
                "abilities": char.abilities or "",
                **(char.extra or {}),
            }
            for char in sorted(project.characters, key=lambda c: c.position)
        ]

        return world_setting, full_synopsis, characters

    def _parse_llm_part_outlines(self, response: str) -> List[Dict]:
        """
        解析LLM返回的部分大纲JSON

        参数:
            response: LLM响应字符串

        返回:
            List[Dict]: 部分大纲数据列表

        抛出:
            HTTPException: 如果解析失败或数据无效
        """
        cleaned = remove_think_tags(response)
        unwrapped = unwrap_markdown_json(cleaned)
        try:
            result = json.loads(unwrapped)
        except json.JSONDecodeError as exc:
            logger.error("解析部分大纲JSON失败: %s", exc)
            raise HTTPException(status_code=500, detail="LLM返回的部分大纲格式错误")

        parts_data = result.get("parts", [])
        if not parts_data:
            raise HTTPException(status_code=500, detail="LLM未返回有效的部分大纲")

        return parts_data

    def _create_part_outline_models(
        self,
        project_id: str,
        parts_data: List[Dict],
    ) -> List[PartOutline]:
        """
        根据解析后的数据创建PartOutline模型列表

        参数:
            project_id: 项目ID
            parts_data: 部分大纲数据列表

        返回:
            List[PartOutline]: PartOutline模型列表
        """
        part_outlines = []
        for idx, part_data in enumerate(parts_data):
            part = PartOutline(
                id=str(uuid.uuid4()),
                project_id=project_id,
                part_number=part_data.get("part_number", idx + 1),
                title=part_data.get("title", f"第{idx + 1}部分"),
                start_chapter=part_data.get("start_chapter"),
                end_chapter=part_data.get("end_chapter"),
                summary=part_data.get("summary", ""),
                theme=part_data.get("theme", ""),
                key_events=part_data.get("key_events", []),
                character_arcs=part_data.get("character_arcs", {}),
                conflicts=part_data.get("conflicts", []),
                ending_hook=part_data.get("ending_hook"),
                generation_status="pending",
                progress=0,
            )
            part_outlines.append(part)
        return part_outlines

    def _parse_single_part_outline(self, response: str, expected_part_number: int) -> Dict:
        """
        解析LLM返回的单个部分大纲JSON（串行生成模式）

        参数:
            response: LLM响应字符串
            expected_part_number: 期望的部分编号

        返回:
            Dict: 部分大纲数据

        抛出:
            HTTPException: 如果解析失败或数据无效
        """
        cleaned = remove_think_tags(response)
        unwrapped = unwrap_markdown_json(cleaned)
        try:
            part_data = json.loads(unwrapped)
        except json.JSONDecodeError as exc:
            logger.error("解析部分大纲JSON失败: %s", exc)
            raise HTTPException(status_code=500, detail="LLM返回的部分大纲格式错误")

        # 验证part_number
        if part_data.get("part_number") != expected_part_number:
            logger.warning(
                "LLM返回的部分编号(%s)与期望(%s)不符，使用期望值",
                part_data.get("part_number"),
                expected_part_number
            )
            part_data["part_number"] = expected_part_number

        return part_data

    def _create_single_part_outline_model(
        self,
        project_id: str,
        part_data: Dict,
    ) -> PartOutline:
        """
        根据解析后的数据创建单个PartOutline模型

        参数:
            project_id: 项目ID
            part_data: 部分大纲数据

        返回:
            PartOutline: PartOutline模型
        """
        part = PartOutline(
            id=str(uuid.uuid4()),
            project_id=project_id,
            part_number=part_data.get("part_number"),
            title=part_data.get("title", f"第{part_data.get('part_number')}部分"),
            start_chapter=part_data.get("start_chapter"),
            end_chapter=part_data.get("end_chapter"),
            summary=part_data.get("summary", ""),
            theme=part_data.get("theme", ""),
            key_events=part_data.get("key_events", []),
            character_arcs=part_data.get("character_arcs", {}),
            conflicts=part_data.get("conflicts", []),
            ending_hook=part_data.get("ending_hook"),
            generation_status="pending",
            progress=0,
        )
        return part

    async def _get_previous_chapters_for_context(
        self,
        project_id: str,
        current_chapter: int,
    ) -> List[Dict]:
        """
        获取前面已生成的章节大纲（用于上下文）

        参数:
            project_id: 项目ID
            current_chapter: 当前章节号

        返回:
            List[Dict]: 前面章节的大纲数据列表
        """
        # 查询所有在当前章节之前的章节大纲
        all_outlines = await self.chapter_outline_repo.list_by_project(project_id)

        # 筛选出当前章节之前的章节
        previous_chapters = [
            {
                "chapter_number": outline.chapter_number,
                "title": outline.title,
                "summary": outline.summary,
            }
            for outline in all_outlines
            if outline.chapter_number < current_chapter
        ]

        # 按章节号排序
        previous_chapters.sort(key=lambda x: x["chapter_number"])

        return previous_chapters

    async def generate_part_outlines(
        self,
        project_id: str,
        user_id: int,
        total_chapters: int,
        chapters_per_part: int = NovelConstants.CHAPTERS_PER_PART,
        optimization_prompt: Optional[str] = None,
        skip_status_update: bool = False,
    ) -> PartOutlineGenerationProgress:
        """
        生成部分大纲（大纲的大纲） - 串行生成模式

        改进：采用串行生成，每次生成一个部分时都能看到前面部分的实际内容，
        确保设定连贯、剧情承接、角色发展一致。

        注意：此方法不commit，调用方需要在适当时候commit

        参数：
            project_id: 项目ID
            user_id: 用户ID
            total_chapters: 总章节数
            chapters_per_part: 每个部分包含的章节数（默认25章）
            optimization_prompt: 可选的优化提示词，用于引导AI生成符合预期的部分大纲
            skip_status_update: 是否跳过状态更新（重新生成时使用）

        返回：
            PartOutlineGenerationProgress: 生成进度和结果
        """
        logger.info("开始为项目 %s 串行生成部分大纲，总章节数=%d，优化提示词=%s，跳过状态更新=%s",
                   project_id, total_chapters, optimization_prompt or "无", skip_status_update)

        # 验证请求和获取项目
        project = await self._validate_part_outline_request(project_id, user_id, total_chapters)

        # 准备蓝图数据
        world_setting, full_synopsis, characters = self._prepare_blueprint_data(project)

        # 计算部分数量
        total_parts = math.ceil(total_chapters / chapters_per_part)
        logger.info("计划串行生成 %d 个部分，每部分约 %d 章", total_parts, chapters_per_part)

        # 删除旧数据
        await self.repo.delete_by_project_id(project_id)

        # 串行生成每个部分
        part_outlines = []
        system_prompt = await self.prompt_service.get_prompt("part_outline")

        for current_part_num in range(1, total_parts + 1):
            logger.info("开始生成第 %d/%d 部分（串行模式）", current_part_num, total_parts)

            # 构建提示词，包含前面已生成的部分
            user_prompt = self.prompt_builder.build_part_outline_prompt(
                total_chapters=total_chapters,
                chapters_per_part=chapters_per_part,
                total_parts=total_parts,
                world_setting=world_setting,
                characters=characters,
                full_synopsis=full_synopsis,
                current_part_number=current_part_num,
                previous_parts=part_outlines,  # 传入前面已生成的部分
                optimization_prompt=optimization_prompt,
            )

            # 调用LLM生成当前部分
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": user_prompt}],
                temperature=LLMConstants.BLUEPRINT_TEMPERATURE,
                user_id=user_id,
                response_format="json_object",
                timeout=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
            )

            # 解析响应（解析单个部分）
            part_data = self._parse_single_part_outline(response, current_part_num)

            # 创建模型
            part_outline = self._create_single_part_outline_model(project_id, part_data)

            # 保存到数据库（逐个保存）
            await self.repo.add(part_outline)
            part_outlines.append(part_outline)

            logger.info("第 %d/%d 部分生成成功：%s", current_part_num, total_parts, part_outline.title)

        logger.info("串行生成完成，共 %d 个部分大纲", len(part_outlines))

        # 更新项目状态
        if not skip_status_update:
            novel_service = NovelService(self.session)
            await novel_service.transition_project_status(project, ProjectStatus.PART_OUTLINES_READY.value)
            logger.info("项目 %s 状态已更新为 %s", project_id, ProjectStatus.PART_OUTLINES_READY.value)
        else:
            logger.info("跳过状态更新（重新生成模式）")

        # 返回进度信息
        return PartOutlineGenerationProgress(
            parts=[self._to_schema(p) for p in part_outlines],
            total_parts=len(part_outlines),
            completed_parts=len(part_outlines),
            status="completed",
        )

    async def generate_part_chapters(
        self,
        project_id: str,
        user_id: int,
        part_number: int,
        regenerate: bool = False,
        chapters_per_batch: int = 5,
    ) -> List[ChapterOutlineSchema]:
        """
        为指定部分生成详细的章节大纲 - 串行生成模式

        改进：采用串行生成，每次生成一小批章节（默认5章），每次都能看到前面
        已生成章节的实际内容，确保设定连贯、剧情承接、角色发展一致。

        参数：
            project_id: 项目ID
            user_id: 用户ID
            part_number: 部分编号
            regenerate: 是否重新生成（默认False，如果章节已存在则跳过）
            chapters_per_batch: 每批生成的章节数（默认5章）

        返回：
            List[ChapterOutlineSchema]: 生成的章节大纲列表
        """
        logger.info("开始为项目 %s 的第 %d 部分串行生成章节大纲（每批 %d 章）",
                   project_id, part_number, chapters_per_batch)

        # 获取部分大纲
        part_outline = await self.repo.get_by_part_number(project_id, part_number)
        if not part_outline:
            raise HTTPException(status_code=404, detail=f"未找到第 {part_number} 部分的大纲")

        # 获取项目信息
        project = await self.novel_service.ensure_project_owner(project_id, user_id)

        if not project.blueprint:
            raise HTTPException(status_code=400, detail="项目蓝图未生成")

        # 更新状态为generating
        await self.repo.update_status(part_outline, "generating", 0)
        await self.session.commit()

        generation_successful = False  # 追踪是否成功完成
        all_generated_chapters = []

        try:
            # 检查是否已被取消
            await self._check_if_cancelled(part_outline)

            # 计算需要生成的章节范围
            start_chapter = part_outline.start_chapter
            end_chapter = part_outline.end_chapter
            total_chapters = end_chapter - start_chapter + 1

            logger.info(
                "第 %d 部分需要生成 %d 章（第 %d-%d 章），将分批串行生成",
                part_number, total_chapters, start_chapter, end_chapter
            )

            # 串行生成章节大纲（分批生成）
            system_prompt = await self.prompt_service.get_prompt("screenwriting")
            current_chapter = start_chapter

            while current_chapter <= end_chapter:
                # 检查取消状态
                await self._check_if_cancelled(part_outline)

                # 计算当前批次的章节范围
                batch_end = min(current_chapter + chapters_per_batch - 1, end_chapter)
                batch_count = batch_end - current_chapter + 1

                logger.info(
                    "开始生成第 %d-%d 章（共 %d 章，批次 %d/%d）",
                    current_chapter, batch_end, batch_count,
                    (current_chapter - start_chapter) // chapters_per_batch + 1,
                    (total_chapters + chapters_per_batch - 1) // chapters_per_batch
                )

                # 获取前面已生成的章节（用于上下文）
                previous_chapters_data = await self._get_previous_chapters_for_context(
                    project_id, current_chapter
                )

                # 构建提示词（包含前面已生成的章节）
                user_prompt = await self.prompt_builder.build_part_chapters_prompt(
                    part_outline=part_outline,
                    project=project,
                    start_chapter=current_chapter,
                    num_chapters=batch_count,
                    previous_chapters=previous_chapters_data,
                )

                # 调用LLM生成当前批次的章节大纲
                logger.info(
                    "调用LLM生成第 %d-%d 章的章节大纲",
                    current_chapter, batch_end
                )
                response = await self.llm_service.get_llm_response(
                    system_prompt=system_prompt,
                    conversation_history=[{"role": "user", "content": user_prompt}],
                    temperature=LLMConstants.BLUEPRINT_TEMPERATURE,
                    user_id=user_id,
                    response_format="json_object",
                    timeout=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
                )

                # LLM调用完成后检查取消状态
                await self._check_if_cancelled(part_outline)

                # 解析响应
                cleaned = remove_think_tags(response)
                unwrapped = unwrap_markdown_json(cleaned)
                try:
                    result = json.loads(unwrapped)
                except json.JSONDecodeError as exc:
                    logger.error("解析章节大纲JSON失败: %s", exc)
                    raise HTTPException(status_code=500, detail="LLM返回的章节大纲格式错误")

                chapters_data = result.get("chapter_outline", [])
                if not chapters_data:
                    raise HTTPException(status_code=500, detail="LLM未返回有效的章节大纲")

                # 将章节大纲插入数据库
                for chapter_data in chapters_data:
                    chapter_number = chapter_data.get("chapter_number")
                    if not chapter_number:
                        continue

                    # 检查是否已存在（非regenerate模式下跳过已存在的）
                    if not regenerate:
                        existing = next(
                            (o for o in project.outlines if o.chapter_number == chapter_number),
                            None,
                        )
                        if existing:
                            logger.info("章节 %d 大纲已存在，跳过", chapter_number)
                            continue

                    # 使用Repository的upsert方法
                    await self.chapter_outline_repo.upsert_outline(
                        project_id=project_id,
                        chapter_number=chapter_number,
                        title=chapter_data.get("title", ""),
                        summary=chapter_data.get("summary", "")
                    )
                    all_generated_chapters.append(chapter_data)

                logger.info(
                    "成功生成第 %d-%d 章大纲（本批 %d 章）",
                    current_chapter, batch_end, len(chapters_data)
                )

                # 更新进度
                progress = int((current_chapter - start_chapter + batch_count) / total_chapters * 100)
                await self.repo.update_status(part_outline, "generating", progress)
                await self.session.commit()

                # 移动到下一批
                current_chapter = batch_end + 1

            # 标记生成成功
            generation_successful = True

            logger.info("串行生成完成，第 %d 部分共生成 %d 个章节大纲", part_number, len(all_generated_chapters))

            # 返回章节大纲schema
            return [
                ChapterOutlineSchema(
                    chapter_number=c.get("chapter_number"),
                    title=c.get("title", ""),
                    summary=c.get("summary", ""),
                )
                for c in all_generated_chapters
            ]

        except GenerationCancelledException as exc:
            logger.info("第 %d 部分生成已被用户取消: %s", part_number, exc)
            # 取消异常不需要重新抛出，让finally块处理状态更新

        except Exception as exc:
            log_exception(
                exc,
                "生成部分章节大纲",
                project_id=project_id,
                part_number=part_number,
                user_id=user_id,
                chapter_range=f"{part_outline.start_chapter}-{part_outline.end_chapter}"
            )
            raise

        finally:
            # 确保状态总是会更新，防止永久卡在generating状态
            try:
                # 再次刷新状态，确保获取最新的generation_status
                await self.session.refresh(part_outline)

                if generation_successful:
                    await self.repo.update_status(part_outline, "completed", 100)
                    status_desc = "completed"
                elif part_outline.generation_status == "cancelling":
                    await self.repo.update_status(part_outline, "cancelled", part_outline.progress)
                    status_desc = "cancelled"
                else:
                    await self.repo.update_status(part_outline, "failed", 0)
                    status_desc = "failed"

                await self.session.commit()
                logger.info("第 %d 部分状态已更新: %s", part_number, status_desc)

                # 注意：不在此处检查所有部分状态，避免重复检查
                # 状态转换应该在batch_generate_chapters末尾统一执行

            except Exception as status_update_error:
                log_exception(
                    status_update_error,
                    "更新部分状态",
                    level="error",
                    project_id=project_id,
                    part_number=part_number,
                    note="状态更新失败不影响原始异常的抛出"
                )
                # 即使状态更新失败，也不影响原始异常的抛出

    async def batch_generate_chapters(
        self,
        project_id: str,
        user_id: int,
        part_numbers: Optional[List[int]] = None,
        max_concurrent: int = 3,
    ) -> PartOutlineGenerationProgress:
        """
        批量并发生成多个部分的章节大纲

        注意：为避免session并发问题，此方法不直接使用并发。
        建议在API层实现并发控制，每个请求使用独立的session。

        参数：
            project_id: 项目ID
            user_id: 用户ID
            part_numbers: 要生成的部分编号列表（None表示生成所有待生成的部分）
            max_concurrent: 最大并发数（默认3）

        返回：
            PartOutlineGenerationProgress: 生成进度
        """
        logger.info("开始批量生成章节大纲（串行模式），max_concurrent=%d", max_concurrent)

        # 获取要生成的部分
        if part_numbers:
            parts = []
            for pn in part_numbers:
                part = await self.repo.get_by_part_number(project_id, pn)
                if part:
                    parts.append(part)
        else:
            parts = await self.repo.get_pending_parts(project_id)

        if not parts:
            logger.info("没有待生成的部分大纲")
            return PartOutlineGenerationProgress(
                parts=[],
                total_parts=0,
                completed_parts=0,
                status="completed",
            )

        logger.info("共有 %d 个部分待生成（串行执行）", len(parts))

        # 串行生成（避免session并发问题）
        results = []
        for part in parts:
            try:
                logger.info("开始生成第 %d 部分", part.part_number)
                chapters = await self.generate_part_chapters(
                    project_id=project_id,
                    user_id=user_id,
                    part_number=part.part_number,
                    regenerate=False,
                )
                results.append({"success": True, "part_number": part.part_number, "chapters": len(chapters)})
            except Exception as exc:
                log_exception(
                    exc,
                    "批量生成部分章节",
                    level="error",
                    project_id=project_id,
                    part_number=part.part_number,
                    user_id=user_id
                )
                results.append({"success": False, "part_number": part.part_number, "error": str(exc)})

        # 统计结果
        completed = sum(1 for r in results if r["success"])
        failed = len(results) - completed

        logger.info("批量生成完成，成功=%d，失败=%d", completed, failed)

        # 重新加载所有部分大纲
        all_parts = await self.repo.get_by_project_id(project_id)

        # 检查是否所有部分都已完成，如果是则更新项目状态
        all_completed = all(p.generation_status == "completed" for p in all_parts)
        if all_completed and completed > 0:
            # 获取项目信息
            novel_repo = NovelRepository(self.session)
            project = await novel_repo.get(project_id)
            if project:
                # 使用状态机安全地转换状态
                novel_service = NovelService(self.session)
                await novel_service.transition_project_status(
                    project,
                    ProjectStatus.CHAPTER_OUTLINES_READY.value
                )
                logger.info("项目 %s 所有部分大纲已完成，状态已更新为 chapter_outlines_ready", project_id)

        return PartOutlineGenerationProgress(
            parts=[self._to_schema(p) for p in all_parts],
            total_parts=len(all_parts),
            completed_parts=sum(1 for p in all_parts if p.generation_status == "completed"),
            status="completed" if failed == 0 else "partial",
        )

    def _to_schema(self, part: PartOutline) -> PartOutlineSchema:
        """将数据库模型转换为Pydantic Schema"""
        return PartOutlineSchema(
            part_number=part.part_number,
            title=part.title or "",
            start_chapter=part.start_chapter,
            end_chapter=part.end_chapter,
            summary=part.summary or "",
            theme=part.theme or "",
            key_events=part.key_events or [],
            character_arcs=part.character_arcs or {},
            conflicts=part.conflicts or [],
            ending_hook=part.ending_hook,
            generation_status=part.generation_status,
            progress=part.progress,
        )
