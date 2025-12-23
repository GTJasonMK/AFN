"""
部分大纲生成工作流

封装部分大纲的串行生成逻辑，支持同步和流式两种调用方式。
"""

import logging
import math
from typing import Any, List, Optional, TYPE_CHECKING

from ...core.constants import LLMConstants
from ...core.state_machine import ProjectStatus
from ...models.part_outline import PartOutline
from ...schemas.novel import PartOutlineGenerationProgress
from ...utils.exception_helpers import get_safe_error_message
from ..llm_wrappers import call_llm_json, LLMProfile

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PartOutlineWorkflow:
    """
    部分大纲生成工作流

    封装部分大纲的串行生成逻辑，支持同步和流式两种调用方式。
    消除generate_part_outlines_stream和continue_part_outlines_stream之间的代码重复。

    使用方式：
    ```python
    workflow = PartOutlineWorkflow(...)
    # 同步执行
    result = await workflow.execute()

    # 流式执行（带进度回调）
    async for progress in workflow.execute_with_progress():
        yield sse_event("progress", progress)
    ```
    """

    def __init__(
        self,
        session: "AsyncSession",
        project_id: str,
        user_id: int,
        total_chapters: int,
        chapters_per_part: int,
        continue_mode: bool = False,
        count: Optional[int] = None,
        optimization_prompt: Optional[str] = None,
    ):
        """
        初始化工作流

        Args:
            session: 数据库会话
            project_id: 项目ID
            user_id: 用户ID
            total_chapters: 总章节数
            chapters_per_part: 每部分章节数
            continue_mode: 是否为增量模式（从现有部分继续生成）
            count: 限制生成的部分数量（仅在continue_mode时有效）
            optimization_prompt: 优化提示词（可选）
        """
        self.session = session
        self.project_id = project_id
        self.user_id = user_id
        self.total_chapters = total_chapters
        self.chapters_per_part = chapters_per_part
        self.continue_mode = continue_mode
        self.count = count
        self.optimization_prompt = optimization_prompt

        # 延迟导入避免循环依赖
        from .service import PartOutlineService
        self._part_service = PartOutlineService(session)

        # 计算总部分数
        self.target_total_parts = math.ceil(total_chapters / chapters_per_part)

        # 状态变量
        self._project = None
        self._world_setting = None
        self._full_synopsis = None
        self._characters = None
        self._start_part = 1
        self._end_part = self.target_total_parts
        self._existing_parts: List[PartOutline] = []

    async def _initialize(self) -> None:
        """阶段1：初始化和验证"""
        # 验证请求
        self._project = await self._part_service._validate_part_outline_request(
            self.project_id, self.user_id, self.total_chapters
        )

        # 准备蓝图数据
        (
            self._world_setting,
            self._full_synopsis,
            self._characters,
        ) = self._part_service._prepare_blueprint_data(self._project)

        if self.continue_mode:
            # 获取现有部分大纲
            self._existing_parts = await self._part_service.repo.get_by_project_id(
                self.project_id
            )
            existing_count = len(self._existing_parts)

            if existing_count >= self.target_total_parts:
                # 已经生成完毕
                return

            # 计算生成范围
            self._start_part = existing_count + 1
            remaining = self.target_total_parts - existing_count

            if self.count is not None:
                parts_to_generate = min(self.count, remaining)
            else:
                parts_to_generate = remaining

            self._end_part = self._start_part + parts_to_generate - 1
        else:
            # 全新生成模式：删除旧数据
            await self._part_service.repo.delete_by_project_id(self.project_id)
            self._existing_parts = []

    async def _generate_single_part(
        self,
        part_number: int,
        previous_parts: List[PartOutline],
        system_prompt: str,
    ) -> PartOutline:
        """生成单个部分大纲"""
        # 构建提示词
        user_prompt = self._part_service.prompt_builder.build_part_outline_prompt(
            total_chapters=self.total_chapters,
            chapters_per_part=self.chapters_per_part,
            total_parts=self.target_total_parts,
            world_setting=self._world_setting,
            characters=self._characters,
            full_synopsis=self._full_synopsis,
            current_part_number=part_number,
            previous_parts=previous_parts,
            optimization_prompt=self.optimization_prompt,
        )

        # 调用LLM
        response = await call_llm_json(
            self._part_service.llm_service,
            LLMProfile.BLUEPRINT,
            system_prompt=system_prompt,
            user_content=user_prompt,
            user_id=self.user_id,
            timeout_override=LLMConstants.PART_OUTLINE_GENERATION_TIMEOUT,
        )

        # 解析响应
        part_data = self._part_service._parser.parse_single_part(response, part_number)
        part_outline = self._part_service._model_factory.create_from_dict(
            self.project_id, part_data
        )

        # 保存到数据库
        await self._part_service.repo.add(part_outline)
        await self.session.commit()

        return part_outline

    async def _update_project_status(self) -> None:
        """更新项目状态为PART_OUTLINES_READY"""
        if self._project:
            await self._part_service.novel_service.transition_project_status(
                self._project, ProjectStatus.PART_OUTLINES_READY.value
            )
            await self.session.commit()

    async def execute(self) -> PartOutlineGenerationProgress:
        """
        同步执行完整的部分大纲生成流程

        Returns:
            PartOutlineGenerationProgress: 生成进度和结果
        """
        await self._initialize()

        # 检查是否需要生成
        if self.continue_mode and len(self._existing_parts) >= self.target_total_parts:
            return PartOutlineGenerationProgress(
                parts=[self._part_service._to_schema(p) for p in self._existing_parts],
                total_parts=len(self._existing_parts),
                completed_parts=len(self._existing_parts),
                status="completed",
            )

        # 获取系统提示词（使用新的单部分生成专用提示词，回退到旧版本）
        system_prompt = await self._part_service.prompt_service.get_prompt("part_outline_single")
        if not system_prompt:
            system_prompt = await self._part_service.prompt_service.get_prompt("part_outline")

        # 串行生成每个部分
        part_outlines = list(self._existing_parts)

        for current_part_num in range(self._start_part, self._end_part + 1):
            part_outline = await self._generate_single_part(
                part_number=current_part_num,
                previous_parts=part_outlines,
                system_prompt=system_prompt,
            )
            part_outlines.append(part_outline)
            logger.info(
                "第 %d/%d 部分生成成功：%s",
                current_part_num,
                self._end_part,
                part_outline.title,
            )

        # 更新项目状态（仅在全新生成模式时）
        if not self.continue_mode:
            await self._update_project_status()

        return PartOutlineGenerationProgress(
            parts=[self._part_service._to_schema(p) for p in part_outlines],
            total_parts=len(part_outlines),
            completed_parts=len(part_outlines),
            status="completed",
        )

    async def execute_with_progress(self):
        """
        流式执行部分大纲生成，通过yield返回进度

        Yields:
            Dict: 进度信息 {"status", "current_part", "total_parts", "message"}
        """
        saved_parts = []

        try:
            # 阶段1：初始化
            yield {
                "status": "starting",
                "current_part": 0,
                "total_parts": self.target_total_parts,
                "message": "正在初始化...",
            }
            await self._initialize()

            # 检查是否已完成
            if self.continue_mode and len(self._existing_parts) >= self.target_total_parts:
                yield {
                    "status": "complete",
                    "message": f"已有 {len(self._existing_parts)} 个部分大纲，无需继续生成",
                    "total_parts": len(self._existing_parts),
                    "new_parts_count": 0,
                }
                return

            # 获取系统提示词
            system_prompt = await self._part_service.prompt_service.get_prompt(
                "part_outline"
            )

            # 串行生成每个部分
            part_outlines = list(self._existing_parts)

            for current_part_num in range(self._start_part, self._end_part + 1):
                # 发送进度更新
                yield {
                    "status": "generating",
                    "current_part": current_part_num,
                    "total_parts": self._end_part,
                    "message": f"正在生成第 {current_part_num}/{self._end_part} 部分...",
                }

                # 生成当前部分
                part_outline = await self._generate_single_part(
                    part_number=current_part_num,
                    previous_parts=part_outlines,
                    system_prompt=system_prompt,
                )

                part_outlines.append(part_outline)
                saved_parts.append(current_part_num)

                logger.info(
                    "第 %d/%d 部分生成成功：%s",
                    current_part_num,
                    self._end_part,
                    part_outline.title,
                )

            # 更新项目状态（仅在全新生成模式时）
            if not self.continue_mode:
                await self._update_project_status()
                logger.info("串行生成完成，共 %d 个部分大纲", len(part_outlines))

                yield {
                    "status": "complete",
                    "message": f"部分大纲生成完成，共 {self._end_part} 个部分",
                    "total_parts": self._end_part,
                }
            else:
                new_parts_count = self._end_part - self._start_part + 1
                logger.info("增量生成完成，新增 %d 个部分大纲", new_parts_count)

                yield {
                    "status": "complete",
                    "message": f"继续生成完成，新增 {new_parts_count} 个部分（第 {self._start_part}-{self._end_part} 部分）",
                    "total_parts": self._end_part,
                    "new_parts_count": new_parts_count,
                }

        except Exception as exc:
            logger.exception("部分大纲生成失败: %s", exc)
            # 使用安全的错误消息过滤，避免泄露敏感信息
            safe_message = get_safe_error_message(exc, "部分大纲生成失败，请稍后重试")
            yield {
                "status": "error",
                "message": safe_message,
                "saved_parts": saved_parts,
                "saved_count": len(saved_parts),
            }


__all__ = [
    "PartOutlineWorkflow",
]
