"""
漫画提示词服务

主服务入口，协调工作流执行并提供对外接口。
新流程：先生成排版 -> 再基于排版生成提示词 -> 最后组装结果

采用Mixin架构，各功能模块分离到独立文件中。
"""

import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    MangaPromptRequest,
    MangaPromptResult,
    MangaStyle,
)
from .layout_schemas import (
    LayoutType,
    PageSize,
    LayoutGenerationRequest,
)
from .layout_service import LayoutService
from .content_truncation_mixin import ContentTruncationMixin
from .prompt_builder_mixin import PromptBuilderMixin
from .response_parser_mixin import ResponseParserMixin
from .layout_utils_mixin import LayoutUtilsMixin
from .checkpoint_mixin import CheckpointMixin
from .crud_mixin import CrudMixin
from ...repositories.chapter_repository import ChapterRepository
from ...utils.json_utils import parse_llm_json_safe
from ..llm_wrappers import call_llm, call_llm_json, LLMProfile
from ..image_generation.service import ImageGenerationService

logger = logging.getLogger(__name__)


class MangaPromptService(
    ContentTruncationMixin,
    PromptBuilderMixin,
    ResponseParserMixin,
    LayoutUtilsMixin,
    CheckpointMixin,
    CrudMixin,
):
    """
    漫画提示词服务

    组合多个Mixin提供完整功能：
    - ContentTruncationMixin: 内容截断和智能分段采样
    - PromptBuilderMixin: LLM提示词构建
    - ResponseParserMixin: LLM响应解析
    - LayoutUtilsMixin: 排版工具方法
    - CheckpointMixin: 断点续传
    - CrudMixin: CRUD操作
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service,
        prompt_service=None,
    ):
        """
        初始化服务

        Args:
            session: 数据库会话
            llm_service: LLM服务
            prompt_service: 提示词服务
        """
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.chapter_repo = ChapterRepository(session)
        self.layout_service = LayoutService(session, llm_service, prompt_service)

    async def generate_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
        request: MangaPromptRequest,
        user_id: str,
        continue_from_checkpoint: bool = False,
    ) -> MangaPromptResult:
        """
        生成章节的漫画提示词（带排版）

        支持断点续传：如果 continue_from_checkpoint=True，会从上次中断的步骤继续。

        新流程：
        1. 获取章节内容
        2. 快速提取场景概要（完成后保存检查点）
        3. 调用LayoutService生成排版（完成后保存检查点）
        4. 基于排版信息生成详细提示词
        5. 组装最终结果

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            request: 生成请求
            user_id: 用户ID
            continue_from_checkpoint: 是否从检查点继续

        Returns:
            漫画提示词结果
        """
        # 获取章节内容
        chapter = await self.chapter_repo.get_by_project_and_number(
            project_id, chapter_number
        )
        if not chapter or not chapter.selected_version:
            raise ValueError(f"章节 {chapter_number} 不存在或未生成内容")

        content = chapter.selected_version.content

        # 获取角色信息
        character_profiles = await self._build_character_profiles(project_id)

        # 检查是否有未完成的生成任务
        existing_prompt = chapter.manga_prompt
        scene_summaries = None
        layout_result = None

        if continue_from_checkpoint and existing_prompt:
            # 使用检查点恢复逻辑
            status, progress = self._check_checkpoint_status(
                existing_prompt, chapter.selected_version_id
            )

            # 尝试从场景提取检查点恢复
            should_resume, summaries = self._should_resume_from_scene_extraction(
                status, progress
            )
            if should_resume:
                scene_summaries = summaries

            # 尝试从排版检查点恢复
            if not scene_summaries:
                should_resume, summaries, layout = self._should_resume_from_layout(
                    status, progress, self._restore_layout_result
                )
                if should_resume:
                    scene_summaries = summaries
                    layout_result = layout

        # 如果是重新生成（非断点续传），删除旧的图片记录
        if not continue_from_checkpoint or scene_summaries is None:
            image_service = ImageGenerationService(self.session)
            deleted_count = await image_service.delete_chapter_images(
                project_id=project_id,
                chapter_number=chapter_number,
            )
            if deleted_count > 0:
                logger.info(
                    "重新生成漫画提示词，已删除旧图片: project_id=%s, chapter=%d, count=%d",
                    project_id,
                    chapter_number,
                    deleted_count,
                )

        # 步骤1: 快速提取场景概要
        if scene_summaries is None:
            logger.info("步骤1: 提取场景概要")
            # 保存初始状态
            await self._save_generation_progress(
                chapter_id=chapter.id,
                status="pending",
                progress={"request_params": request.model_dump()},
                source_version_id=chapter.selected_version_id,
            )

            try:
                scene_summaries = await self._extract_scene_summaries(
                    content=content,
                    scene_count=request.scene_count,
                    user_id=user_id,
                )
                # 保存场景提取完成的检查点
                await self._save_generation_progress(
                    chapter_id=chapter.id,
                    status="scene_extracted",
                    progress={
                        "request_params": request.model_dump(),
                        "scene_summaries": scene_summaries,
                    },
                    source_version_id=chapter.selected_version_id,
                )
            except Exception as e:
                await self._save_generation_progress(
                    chapter_id=chapter.id,
                    status="failed",
                    progress={"error": str(e), "failed_step": "scene_extraction"},
                    source_version_id=chapter.selected_version_id,
                )
                raise

        # 步骤2: 生成排版方案
        if layout_result is None:
            logger.info("步骤2: 生成排版方案，共 %d 个场景", len(scene_summaries))
            layout_request = LayoutGenerationRequest(
                layout_type=self._get_layout_type(request.style),
                page_size=PageSize.A4,
                panels_per_page=6,
                reading_direction="ltr",
            )

            try:
                layout_result = await self.layout_service.generate_layout(
                    chapter_content=self._truncate_content(
                        content, self.CONTENT_LIMIT_LAYOUT, preserve_structure=False
                    ),
                    scene_summaries=scene_summaries,
                    request=layout_request,
                    user_id=user_id,
                )
                # 保存排版完成的检查点
                await self._save_generation_progress(
                    chapter_id=chapter.id,
                    status="layout_generated",
                    progress={
                        "request_params": request.model_dump(),
                        "scene_summaries": scene_summaries,
                        "layout_result": self._serialize_layout_result(layout_result),
                    },
                    source_version_id=chapter.selected_version_id,
                )
            except Exception as e:
                await self._save_generation_progress(
                    chapter_id=chapter.id,
                    status="failed",
                    progress={
                        "request_params": request.model_dump(),
                        "scene_summaries": scene_summaries,
                        "error": str(e),
                        "failed_step": "layout_generation",
                    },
                    source_version_id=chapter.selected_version_id,
                )
                raise

        # 步骤3: 基于排版生成详细提示词
        logger.info("步骤3: 基于排版生成详细提示词")
        try:
            system_prompt, user_prompt = await self._build_prompts_with_layout(
                content=content,
                character_profiles=character_profiles,
                style=request.style,
                scene_summaries=scene_summaries,
                layout_result=layout_result,
                dialogue_language=request.dialogue_language,
                include_dialogue=request.include_dialogue,
                include_sound_effects=request.include_sound_effects,
            )

            # 调用LLM生成
            llm_response = await call_llm(
                self.llm_service,
                LLMProfile.MANGA,
                system_prompt=system_prompt,
                user_content=user_prompt,
                user_id=int(user_id) if user_id else 0,
            )

            # 解析响应并附加排版信息
            result = self._parse_llm_response_with_layout(
                llm_response,
                chapter_number=chapter_number,
                style=request.style,
                layout_result=layout_result,
            )

            # 保存最终结果（状态为completed）
            await self._save_manga_prompt(
                chapter_id=chapter.id,
                result=result,
                source_version_id=chapter.selected_version_id,
            )

            return result

        except Exception as e:
            await self._save_generation_progress(
                chapter_id=chapter.id,
                status="failed",
                progress={
                    "request_params": request.model_dump(),
                    "scene_summaries": scene_summaries,
                    "layout_result": (
                        self._serialize_layout_result(layout_result)
                        if layout_result
                        else None
                    ),
                    "error": str(e),
                    "failed_step": "prompt_generation",
                },
                source_version_id=chapter.selected_version_id,
            )
            raise

    async def _extract_scene_summaries(
        self,
        content: str,
        scene_count: Optional[int],
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """
        快速提取场景概要

        Args:
            content: 章节内容
            scene_count: 目标场景数
            user_id: 用户ID

        Returns:
            场景概要列表
        """
        scene_hint = (
            f"分割成 {scene_count} 个场景" if scene_count else "分割成5-15个场景"
        )

        system_prompt = """你是专业的漫画分镜师。请快速将小说章节内容分割成漫画场景。
只需要返回场景的简要信息，不需要生成详细提示词。

输出JSON格式：
{
  "scenes": [
    {
      "scene_id": 1,
      "summary": "场景的一句话描述",
      "emotion": "情感基调（如：紧张、温馨、悲伤）",
      "characters": ["出场角色列表"],
      "scene_type": "场景类型：对话/动作/环境/特写/转场"
    }
  ]
}"""

        user_prompt = f"""请将以下章节内容{scene_hint}：

{self._truncate_content(content, self.CONTENT_LIMIT_SCENE_EXTRACTION)}

要求：
1. 选择视觉上有意义的关键画面
2. 按故事时间线顺序
3. 识别每个场景的情感和类型"""

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=system_prompt,
            user_content=user_prompt,
            user_id=int(user_id) if user_id else 0,
            temperature_override=0.5,
        )

        data = parse_llm_json_safe(response)
        if not data or "scenes" not in data:
            # 返回默认场景列表
            return [
                {
                    "scene_id": i + 1,
                    "summary": f"场景{i + 1}",
                    "emotion": "",
                    "characters": [],
                    "scene_type": "对话",
                }
                for i in range(8)
            ]

        return data["scenes"]
