"""
正文优化工作流

使用Agent驱动的方式进行段落分析和优化建议生成。
Agent根据环境自主决定调用哪些工具、执行哪些检查。
"""

import logging
from typing import AsyncGenerator, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    AnalysisScope,
    CheckDimension,
    OptimizationContext,
    OptimizationEventType,
    OptimizationMode,
    OptimizeContentRequest,
    RAGContext,
)
from .paragraph_analyzer import ParagraphAnalyzer
from .agent import ContentOptimizationAgent
from .tool_executor import ToolExecutor, AgentState
from .session_manager import OptimizationSession
from ...utils.sse_helpers import sse_event

logger = logging.getLogger(__name__)


class ContentOptimizationWorkflow:
    """正文优化工作流 - Agent驱动模式"""

    def __init__(
        self,
        session: AsyncSession,
        llm_service,
        vector_store=None,
        prompt_service=None,
        embedding_service=None,
        optimization_session: Optional[OptimizationSession] = None,
    ):
        """
        初始化工作流

        Args:
            session: 数据库会话
            llm_service: LLM服务
            vector_store: 向量存储服务（可选）
            prompt_service: 提示词服务（可选）
            embedding_service: 嵌入服务（可选，用于时序感知检索）
            optimization_session: 优化会话（用于暂停/继续控制）
        """
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.prompt_service = prompt_service
        self.embedding_service = embedding_service
        self.optimization_session = optimization_session

    async def execute_with_stream(
        self,
        project_id: str,
        chapter_number: int,
        request: OptimizeContentRequest,
        user_id: int,
    ) -> AsyncGenerator[str, None]:
        """
        流式执行优化分析（Agent驱动）

        Agent会自主决定：
        1. 分析哪些维度
        2. 何时调用RAG检索
        3. 何时生成建议
        4. 何时移动到下一段

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            request: 优化请求
            user_id: 用户ID

        Yields:
            SSE事件字符串
        """
        try:
            # 阶段1: 初始化 - 加载上下文
            context = await self._load_context(project_id, chapter_number)

            # 初始化段落分析器
            paragraph_analyzer = ParagraphAnalyzer(known_characters=context.character_names)

            # 阶段2: 分段
            all_paragraphs = paragraph_analyzer.split_paragraphs(request.content)

            if not all_paragraphs:
                yield sse_event(OptimizationEventType.ERROR, {
                    "message": "无法分割段落，请检查内容格式"
                })
                return

            # 确定要分析的段落
            if request.scope == AnalysisScope.SELECTED and request.selected_paragraphs:
                # 过滤无效索引（负数或超出范围）
                valid_indices = []
                invalid_indices = []
                for idx in request.selected_paragraphs:
                    if 0 <= idx < len(all_paragraphs):
                        valid_indices.append(idx)
                    else:
                        invalid_indices.append(idx)

                if invalid_indices:
                    logger.warning(
                        "发现无效的段落索引: %s (总段落数: %d)",
                        invalid_indices, len(all_paragraphs)
                    )

                paragraphs_to_analyze = [all_paragraphs[idx] for idx in valid_indices]
            else:
                paragraphs_to_analyze = all_paragraphs

            if not paragraphs_to_analyze:
                yield sse_event(OptimizationEventType.ERROR, {
                    "message": "没有有效的段落可以分析",
                    "total_paragraphs": len(all_paragraphs),
                    "selected_count": len(request.selected_paragraphs) if request.selected_paragraphs else 0,
                })
                return

            # 阶段3: 初始化Agent和工具执行器
            # 传入索引标志以启用角色状态和伏笔查询功能
            # 传入llm_service以支持深度检查工具(DEEP_CHECK)
            # 传入prompt_service以支持外部提示词加载
            tool_executor = ToolExecutor(
                session=self.session,
                vector_store=self.vector_store,
                paragraph_analyzer=paragraph_analyzer,
                embedding_service=self.embedding_service,
                enable_character_index=True,  # 启用角色状态索引查询
                enable_foreshadowing_index=True,  # 启用伏笔索引查询
                llm_service=self.llm_service,  # 用于深度LLM检查
                prompt_service=self.prompt_service,  # 用于加载提示词
                user_id=user_id,  # 用户ID，用于LLM调用
            )

            agent = ContentOptimizationAgent(
                llm_service=self.llm_service,
                tool_executor=tool_executor,
                user_id=user_id,
                optimization_session=self.optimization_session,
                optimization_mode=request.mode,
                prompt_service=self.prompt_service,  # 用于加载提示词
            )

            # 创建Agent状态
            state = AgentState(
                paragraphs=paragraphs_to_analyze,
                project_id=project_id,
                chapter_number=chapter_number,
                total_chapters=context.total_chapters,
                paragraph_analyzer=paragraph_analyzer,  # 用于内容更新时重新分段
            )

            # 阶段4: 运行Agent
            logger.info(
                "启动Agent: 项目=%s, 章节=%d, 段落数=%d, 维度=%s",
                project_id,
                chapter_number,
                len(paragraphs_to_analyze),
                request.dimensions,
            )

            async for event in agent.run(state, request.dimensions):
                yield event

        except Exception as e:
            logger.exception("优化工作流执行失败: %s", str(e))
            yield sse_event(OptimizationEventType.ERROR, {
                "message": f"优化分析失败: {str(e)}",
            })

    async def _load_context(
        self,
        project_id: str,
        chapter_number: int,
    ) -> OptimizationContext:
        """
        加载优化上下文

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            优化上下文
        """
        from ...repositories.novel_repository import NovelRepository
        from ...repositories.chapter_repository import ChapterRepository

        novel_repo = NovelRepository(self.session)
        chapter_repo = ChapterRepository(self.session)

        # 获取项目信息（使用 get_by_id 以 eager load blueprint 等关系）
        project = await novel_repo.get_by_id(project_id)

        # 获取蓝图核心信息
        blueprint_core = None
        if project and project.blueprint:
            bp = project.blueprint
            blueprint_core = f"""
标题: {bp.title or project.title}
类型: {bp.genre or '未设定'}
风格: {bp.style or '未设定'}
基调: {bp.tone or '未设定'}
"""

        # 获取角色名称（characters 在 NovelProject 上）
        character_names = []
        if project and project.characters:
            character_names = [
                c.name for c in project.characters if c.name
            ]

        # 获取前章结尾
        prev_chapter_ending = None
        if chapter_number > 1:
            prev_chapter = await chapter_repo.get_by_project_and_number(
                project_id, chapter_number - 1
            )
            if prev_chapter and prev_chapter.selected_version:
                content = prev_chapter.selected_version.content
                if content:
                    # 取最后500字符
                    prev_chapter_ending = content[-500:] if len(content) > 500 else content

        # 获取风格指南
        style_guide = None
        if project and project.blueprint:
            style_guide = project.blueprint.style

        # 获取总章节数（用于时序感知检索）
        total_chapters = 0
        if project and project.blueprint:
            total_chapters = project.blueprint.total_chapters or 0

        return OptimizationContext(
            project_id=project_id,
            chapter_number=chapter_number,
            blueprint_core=blueprint_core,
            character_names=character_names,
            style_guide=style_guide,
            prev_chapter_ending=prev_chapter_ending,
            total_chapters=total_chapters,
        )


# 注：LegacyContentOptimizationWorkflow 已删除
# 如需恢复旧版线性工作流，请从 git 历史中获取
# commit: 删除前的最后一个包含此类的提交
