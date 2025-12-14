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
        optimization_session: Optional[OptimizationSession] = None,
    ):
        """
        初始化工作流

        Args:
            session: 数据库会话
            llm_service: LLM服务
            vector_store: 向量存储服务（可选）
            prompt_service: 提示词服务（可选）
            optimization_session: 优化会话（用于暂停/继续控制）
        """
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.prompt_service = prompt_service
        self.optimization_session = optimization_session

    async def execute_with_stream(
        self,
        project_id: str,
        chapter_number: int,
        request: OptimizeContentRequest,
        user_id: str,
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
                paragraphs_to_analyze = [
                    all_paragraphs[idx]
                    for idx in request.selected_paragraphs
                    if idx < len(all_paragraphs)
                ]
            else:
                paragraphs_to_analyze = all_paragraphs

            if not paragraphs_to_analyze:
                yield sse_event(OptimizationEventType.ERROR, {
                    "message": "没有选中任何有效段落"
                })
                return

            # 阶段3: 初始化Agent和工具执行器
            tool_executor = ToolExecutor(
                session=self.session,
                vector_store=self.vector_store,
                paragraph_analyzer=paragraph_analyzer,
            )

            agent = ContentOptimizationAgent(
                llm_service=self.llm_service,
                tool_executor=tool_executor,
                user_id=user_id,
                optimization_session=self.optimization_session,
                optimization_mode=request.mode,
            )

            # 创建Agent状态
            state = AgentState(
                paragraphs=paragraphs_to_analyze,
                project_id=project_id,
                chapter_number=chapter_number,
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

        return OptimizationContext(
            project_id=project_id,
            chapter_number=chapter_number,
            blueprint_core=blueprint_core,
            character_names=character_names,
            style_guide=style_guide,
            prev_chapter_ending=prev_chapter_ending,
        )


class LegacyContentOptimizationWorkflow:
    """
    旧版线性工作流（保留作为备选方案）

    如果Agent模式遇到问题，可以回退到这个线性流程。
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service,
        vector_store=None,
        prompt_service=None,
    ):
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.prompt_service = prompt_service

        from .coherence_checker import CoherenceChecker
        self.coherence_checker = CoherenceChecker(llm_service, prompt_service)

    async def execute_with_stream(
        self,
        project_id: str,
        chapter_number: int,
        request: OptimizeContentRequest,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        线性流式执行优化分析（旧版，预设流程）
        """
        from .schemas import SuggestionPriority

        try:
            # 加载上下文
            context = await self._load_context(project_id, chapter_number)

            # 初始化段落分析器
            analyzer = ParagraphAnalyzer(known_characters=context.character_names)

            # 分段
            all_paragraphs = analyzer.split_paragraphs(request.content)

            if not all_paragraphs:
                yield sse_event(OptimizationEventType.ERROR, {
                    "message": "无法分割段落，请检查内容格式"
                })
                return

            # 确定要分析的段落
            if request.scope == AnalysisScope.SELECTED and request.selected_paragraphs:
                paragraphs_to_analyze = [
                    (idx, all_paragraphs[idx])
                    for idx in request.selected_paragraphs
                    if idx < len(all_paragraphs)
                ]
            else:
                paragraphs_to_analyze = list(enumerate(all_paragraphs))

            # 发送工作流开始事件
            yield sse_event(OptimizationEventType.WORKFLOW_START, {
                "total_paragraphs": len(paragraphs_to_analyze),
                "dimensions": request.dimensions,
            })

            total_suggestions = 0
            high_priority_count = 0
            prev_paragraphs: List[str] = []

            # 逐段分析（线性流程）
            for i, (idx, paragraph) in enumerate(paragraphs_to_analyze):
                # 发送段落开始事件
                preview = paragraph[:100] + "..." if len(paragraph) > 100 else paragraph
                yield sse_event(OptimizationEventType.PARAGRAPH_START, {
                    "index": idx,
                    "text_preview": preview,
                })

                # 思考: 分析段落内容
                yield sse_event(OptimizationEventType.THINKING, {
                    "paragraph_index": idx,
                    "content": f"正在分析第{idx + 1}段的内容结构...",
                    "step": "analyze",
                })

                # 分析段落
                analysis = analyzer.analyze_paragraph(
                    paragraph=paragraph,
                    index=idx,
                    prev_paragraph=prev_paragraphs[-1] if prev_paragraphs else None,
                )

                # 思考: 识别角色
                if analysis.characters:
                    yield sse_event(OptimizationEventType.THINKING, {
                        "paragraph_index": idx,
                        "content": f"识别到角色: {', '.join(analysis.characters)}",
                        "step": "character_check",
                    })

                # 动作: RAG检索
                yield sse_event(OptimizationEventType.ACTION, {
                    "paragraph_index": idx,
                    "action": "rag_retrieve",
                    "description": "检索相关角色状态和前文内容",
                })

                # 执行RAG检索
                rag_context = await self._retrieve_rag_context(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    paragraph=paragraph,
                    characters=analysis.characters,
                    user_id=user_id,
                )

                # 观察: RAG结果
                rag_summary = self._summarize_rag_results(rag_context)
                yield sse_event(OptimizationEventType.OBSERVATION, {
                    "paragraph_index": idx,
                    "action": "rag_retrieve",
                    "result": rag_summary,
                    "relevance": 0.85 if rag_context.character_states else 0.5,
                })

                # 思考: 检查连贯性
                yield sse_event(OptimizationEventType.THINKING, {
                    "paragraph_index": idx,
                    "content": "正在检查与前文的逻辑连贯性...",
                    "step": "coherence_check",
                })

                # 执行连贯性检查并生成建议
                suggestions = await self.coherence_checker.check_paragraph(
                    paragraph=paragraph,
                    paragraph_index=idx,
                    prev_paragraphs=prev_paragraphs[-3:],
                    context=context,
                    rag_context=rag_context,
                    dimensions=request.dimensions,
                    user_id=user_id,
                )

                # 发送建议事件
                paragraph_suggestion_count = 0
                for suggestion in suggestions:
                    yield sse_event(OptimizationEventType.SUGGESTION, {
                        "paragraph_index": suggestion.paragraph_index,
                        "original_text": suggestion.original_text,
                        "suggested_text": suggestion.suggested_text,
                        "reason": suggestion.reason,
                        "category": suggestion.category,
                        "priority": suggestion.priority,
                    })
                    paragraph_suggestion_count += 1
                    total_suggestions += 1
                    if suggestion.priority == SuggestionPriority.HIGH.value:
                        high_priority_count += 1

                # 发送段落完成事件
                yield sse_event(OptimizationEventType.PARAGRAPH_COMPLETE, {
                    "index": idx,
                    "suggestion_count": paragraph_suggestion_count,
                })

                # 更新前文段落列表
                prev_paragraphs.append(paragraph)
                if len(prev_paragraphs) > 5:
                    prev_paragraphs.pop(0)

            # 汇总
            summary = self._generate_summary(
                total_paragraphs=len(paragraphs_to_analyze),
                total_suggestions=total_suggestions,
                high_priority_count=high_priority_count,
            )

            yield sse_event(OptimizationEventType.WORKFLOW_COMPLETE, {
                "total_suggestions": total_suggestions,
                "high_priority_count": high_priority_count,
                "summary": summary,
            })

        except Exception as e:
            logger.exception("优化工作流执行失败: %s", str(e))
            yield sse_event(OptimizationEventType.ERROR, {
                "message": f"优化分析失败: {str(e)}",
            })

    async def _load_context(self, project_id: str, chapter_number: int) -> OptimizationContext:
        """加载上下文（同主工作流）"""
        from ...repositories.novel_repository import NovelRepository
        from ...repositories.chapter_repository import ChapterRepository

        novel_repo = NovelRepository(self.session)
        chapter_repo = ChapterRepository(self.session)

        # 使用 get_by_id 以 eager load blueprint 等关系
        project = await novel_repo.get_by_id(project_id)

        blueprint_core = None
        if project and project.blueprint:
            bp = project.blueprint
            blueprint_core = f"标题: {bp.title or project.title}\n类型: {bp.genre or '未设定'}\n风格: {bp.style or '未设定'}"

        # 获取角色名称（characters 在 NovelProject 上）
        character_names = []
        if project and project.characters:
            character_names = [
                c.name for c in project.characters if c.name
            ]

        prev_chapter_ending = None
        if chapter_number > 1:
            prev_chapter = await chapter_repo.get_by_project_and_number(
                project_id, chapter_number - 1
            )
            if prev_chapter and prev_chapter.selected_version:
                content = prev_chapter.selected_version.content
                if content:
                    prev_chapter_ending = content[-500:] if len(content) > 500 else content

        style_guide = None
        if project and project.blueprint:
            style_guide = project.blueprint.style

        return OptimizationContext(
            project_id=project_id,
            chapter_number=chapter_number,
            blueprint_core=blueprint_core,
            character_names=character_names,
            style_guide=style_guide,
            prev_chapter_ending=prev_chapter_ending,
        )

    async def _retrieve_rag_context(
        self,
        project_id: str,
        chapter_number: int,
        paragraph: str,
        characters: List[str],
        user_id: str,
    ) -> RAGContext:
        """检索RAG上下文"""
        character_states = []
        foreshadowings = []
        related_chunks = []
        chapter_summaries = []

        try:
            if characters:
                from ...models.novel import CharacterStateIndex
                from sqlalchemy import select

                for char_name in characters[:3]:
                    result = await self.session.execute(
                        select(CharacterStateIndex)
                        .where(
                            CharacterStateIndex.project_id == project_id,
                            CharacterStateIndex.character_name == char_name,
                            CharacterStateIndex.chapter_number < chapter_number,
                        )
                        .order_by(CharacterStateIndex.chapter_number.desc())
                        .limit(1)
                    )
                    state = result.scalar_one_or_none()
                    if state:
                        character_states.append({
                            "character": char_name,
                            "state": state.status_summary or "",
                            "chapter": state.chapter_number,
                            "location": state.location,
                            "emotion": state.emotion,
                        })

            from ...models.novel import ForeshadowingIndex
            from sqlalchemy import select, or_

            result = await self.session.execute(
                select(ForeshadowingIndex)
                .where(
                    ForeshadowingIndex.project_id == project_id,
                    ForeshadowingIndex.planted_chapter < chapter_number,
                    or_(
                        ForeshadowingIndex.status == "pending",
                        ForeshadowingIndex.resolved_chapter == chapter_number,
                    )
                )
                .limit(5)
            )
            for fs in result.scalars().all():
                foreshadowings.append({
                    "description": fs.description,
                    "status": fs.status,
                    "planted_chapter": fs.planted_chapter,
                })

            if self.vector_store:
                try:
                    chunks = await self.vector_store.similarity_search(
                        project_id=project_id,
                        query=paragraph[:200],
                        k=3,
                    )
                    for chunk in chunks:
                        related_chunks.append({
                            "content": chunk.get("content", "")[:200],
                            "chapter": chunk.get("chapter_number"),
                            "score": chunk.get("score", 0),
                        })
                except Exception as e:
                    logger.warning("向量检索失败: %s", str(e))

        except Exception as e:
            logger.error("RAG上下文检索失败: %s", str(e))

        return RAGContext(
            character_states=character_states,
            foreshadowings=foreshadowings,
            related_chunks=related_chunks,
            chapter_summaries=chapter_summaries,
        )

    def _summarize_rag_results(self, rag_context: RAGContext) -> str:
        """汇总RAG检索结果"""
        parts = []

        if rag_context.character_states:
            states = [f"{s['character']}({s.get('location', '?')})"
                     for s in rag_context.character_states]
            parts.append(f"角色状态: {', '.join(states)}")

        if rag_context.foreshadowings:
            fs_count = len(rag_context.foreshadowings)
            pending = sum(1 for f in rag_context.foreshadowings if f.get('status') == 'pending')
            parts.append(f"相关伏笔: {fs_count}个 (待回收: {pending})")

        if rag_context.related_chunks:
            parts.append(f"相关片段: {len(rag_context.related_chunks)}个")

        return "; ".join(parts) if parts else "未检索到相关上下文"

    def _generate_summary(
        self,
        total_paragraphs: int,
        total_suggestions: int,
        high_priority_count: int,
    ) -> str:
        """生成分析汇总"""
        if total_suggestions == 0:
            return f"分析完成，共检查{total_paragraphs}个段落，未发现明显问题。"

        summary = f"分析完成，共检查{total_paragraphs}个段落，"
        summary += f"发现{total_suggestions}个可优化项"

        if high_priority_count > 0:
            summary += f"（其中{high_priority_count}个高优先级）"

        summary += "。"

        return summary
