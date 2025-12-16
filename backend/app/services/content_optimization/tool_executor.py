"""
工具执行器

负责实际执行Agent调用的工具，并返回结果。
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from .tools import ToolName, ToolCall, ToolResult
from .paragraph_analyzer import ParagraphAnalyzer
from ..vector_store_service import VectorStoreService
from ..rag.temporal_retriever import TemporalAwareRetriever

logger = logging.getLogger(__name__)


class AgentState:
    """Agent状态，跟踪分析过程中的信息"""

    def __init__(
        self,
        paragraphs: List[str],
        project_id: str,
        chapter_number: int,
        total_chapters: int = 0,
    ):
        self.paragraphs = paragraphs
        self.project_id = project_id
        self.chapter_number = chapter_number
        self.total_chapters = total_chapters

        # 当前段落索引
        self.current_index = 0

        # 已生成的建议
        self.suggestions: List[Dict[str, Any]] = []

        # 观察记录
        self.observations: List[Dict[str, Any]] = []

        # 段落分析缓存
        self.paragraph_analyses: Dict[int, Dict[str, Any]] = {}

        # 角色状态缓存
        self.character_states: Dict[str, Dict[str, Any]] = {}

        # 是否完成
        self.is_complete = False

        # 分析总结
        self.summary = ""

    @property
    def current_paragraph(self) -> Optional[str]:
        """获取当前段落"""
        if 0 <= self.current_index < len(self.paragraphs):
            return self.paragraphs[self.current_index]
        return None

    @property
    def previous_paragraph(self) -> Optional[str]:
        """获取前一段落"""
        if self.current_index > 0:
            return self.paragraphs[self.current_index - 1]
        return None

    def has_more_paragraphs(self) -> bool:
        """是否还有更多段落"""
        return self.current_index < len(self.paragraphs) - 1

    def move_to_next(self) -> bool:
        """移动到下一段"""
        if self.has_more_paragraphs():
            self.current_index += 1
            return True
        return False


class ToolExecutor:
    """工具执行器"""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: Optional[VectorStoreService],
        paragraph_analyzer: ParagraphAnalyzer,
        embedding_service: Optional[Any] = None,  # EmbeddingService
        character_index: Any = None,  # CharacterStateIndex model
        foreshadowing_index: Any = None,  # ForeshadowingIndex model
        llm_service: Optional[Any] = None,  # LLMService，用于深度检查
    ):
        self.session = session
        self.vector_store = vector_store
        self.paragraph_analyzer = paragraph_analyzer
        self.embedding_service = embedding_service
        self.character_index = character_index
        self.foreshadowing_index = foreshadowing_index
        self.llm_service = llm_service

        # 初始化时序感知检索器
        self.temporal_retriever: Optional[TemporalAwareRetriever] = None
        if vector_store:
            self.temporal_retriever = TemporalAwareRetriever(vector_store)

    async def execute(self, tool_call: ToolCall, state: AgentState) -> ToolResult:
        """
        执行工具调用

        Args:
            tool_call: 工具调用请求
            state: Agent状态

        Returns:
            工具执行结果
        """
        logger.info(
            "执行工具: %s, 参数: %s, 理由: %s",
            tool_call.tool_name.value,
            tool_call.parameters,
            tool_call.reasoning,
        )

        try:
            handler = self._get_handler(tool_call.tool_name)
            if handler is None:
                return ToolResult(
                    tool_name=tool_call.tool_name,
                    success=False,
                    result=None,
                    error=f"未知工具: {tool_call.tool_name.value}",
                )

            result = await handler(tool_call.parameters, state)
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=True,
                result=result,
            )

        except Exception as e:
            logger.error("工具执行失败: %s - %s", tool_call.tool_name.value, e, exc_info=True)
            return ToolResult(
                tool_name=tool_call.tool_name,
                success=False,
                result=None,
                error=str(e),
            )

    def _get_handler(self, tool_name: ToolName):
        """获取工具处理器"""
        handlers = {
            ToolName.RAG_RETRIEVE: self._handle_rag_retrieve,
            ToolName.GET_CHARACTER_STATE: self._handle_get_character_state,
            ToolName.GET_FORESHADOWING: self._handle_get_foreshadowing,
            ToolName.GET_PREVIOUS_CONTENT: self._handle_get_previous_content,
            ToolName.ANALYZE_PARAGRAPH: self._handle_analyze_paragraph,
            ToolName.CHECK_COHERENCE: self._handle_check_coherence,
            ToolName.CHECK_CHARACTER: self._handle_check_character,
            ToolName.CHECK_TIMELINE: self._handle_check_timeline,
            ToolName.DEEP_CHECK: self._handle_deep_check,
            ToolName.GENERATE_SUGGESTION: self._handle_generate_suggestion,
            ToolName.RECORD_OBSERVATION: self._handle_record_observation,
            ToolName.NEXT_PARAGRAPH: self._handle_next_paragraph,
            ToolName.FINISH_ANALYSIS: self._handle_finish_analysis,
            ToolName.COMPLETE_WORKFLOW: self._handle_complete_workflow,
        }
        return handlers.get(tool_name)

    # ==================== 信息获取工具 ====================

    async def _handle_rag_retrieve(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """处理RAG检索（使用时序感知检索）"""
        query = params.get("query", "")
        query_type = params.get("query_type", "general")
        top_k = params.get("top_k", 5)

        if not self.vector_store:
            return {
                "success": False,
                "message": "向量存储服务不可用",
                "results": [],
            }

        # 构建查询
        full_query = query
        if query_type == "character":
            full_query = f"角色状态 {query}"
        elif query_type == "plot":
            full_query = f"情节发展 {query}"
        elif query_type == "scene":
            full_query = f"场景描写 {query}"

        try:
            # 优先使用时序感知检索（需要embedding_service和total_chapters）
            if (
                self.temporal_retriever
                and self.embedding_service
                and state.total_chapters > 0
            ):
                # 将文本查询转换为向量
                query_embedding = await self.embedding_service.get_embedding(full_query)

                # 使用时序感知检索
                chunks = await self.temporal_retriever.retrieve_chunks_with_temporal(
                    project_id=state.project_id,
                    query_embedding=query_embedding,
                    target_chapter=state.chapter_number,
                    total_chapters=state.total_chapters,
                    top_k=top_k,
                )

                results = []
                for chunk in chunks:
                    results.append({
                        "chapter_number": chunk.chapter_number,
                        "content": chunk.content[:300] if chunk.content else "",
                        "score": chunk.score,
                        "temporal_score": chunk.metadata.get("_temporal_score", 0) if chunk.metadata else 0,
                    })

                return {
                    "success": True,
                    "query": query,
                    "results_count": len(results),
                    "results": results,
                    "retrieval_mode": "temporal_aware",
                }

            # 回退到简单相似度检索
            chunks = await self.vector_store.similarity_search(
                state.project_id,
                full_query,
                top_k=top_k,
            )

            results = []
            for chunk in chunks:
                results.append({
                    "chapter_number": chunk.get("chapter_number"),
                    "content": chunk.get("content", "")[:300],
                    "score": chunk.get("score", 0),
                })

            return {
                "success": True,
                "query": query,
                "results_count": len(results),
                "results": results,
                "retrieval_mode": "similarity_only",
            }

        except Exception as e:
            logger.warning("RAG检索失败: %s", e)
            return {
                "success": False,
                "message": str(e),
                "results": [],
            }

    async def _handle_get_character_state(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """获取角色状态"""
        character_name = params.get("character_name", "")

        # 检查缓存
        if character_name in state.character_states:
            return state.character_states[character_name]

        # 从索引中查询
        if self.character_index is not None:
            from ...models.novel import CharacterStateIndex
            from sqlalchemy import select

            stmt = select(CharacterStateIndex).where(
                CharacterStateIndex.project_id == state.project_id,
                CharacterStateIndex.character_name == character_name,
                CharacterStateIndex.chapter_number < state.chapter_number,
            ).order_by(CharacterStateIndex.chapter_number.desc()).limit(1)

            result = await self.session.execute(stmt)
            record = result.scalar_one_or_none()

            if record:
                char_state = {
                    "character_name": character_name,
                    "found": True,
                    "last_chapter": record.chapter_number,
                    "location": record.location,
                    "status": record.status,
                    "changes": record.changes or [],
                    "emotional_state": record.emotional_state,
                    "relationships_snapshot": record.relationships_snapshot,
                }
                state.character_states[character_name] = char_state
                return char_state

        return {
            "character_name": character_name,
            "found": False,
            "message": f"未找到角色 '{character_name}' 的状态记录",
        }

    async def _handle_get_foreshadowing(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """获取伏笔信息（仅返回未解决的伏笔）"""
        keywords = params.get("keywords", [])

        if self.foreshadowing_index is not None:
            from ...models.novel import ForeshadowingIndex
            from sqlalchemy import select

            # 构建查询条件：只查询pending状态的伏笔
            conditions = [
                ForeshadowingIndex.project_id == state.project_id,
                ForeshadowingIndex.planted_chapter < state.chapter_number,
                ForeshadowingIndex.status == "pending",  # 只返回未解决的伏笔
            ]

            stmt = select(ForeshadowingIndex).where(*conditions).order_by(
                # 高优先级优先，埋得越久越优先
                ForeshadowingIndex.priority.desc(),
                ForeshadowingIndex.planted_chapter.asc(),
            ).limit(10)
            result = await self.session.execute(stmt)
            records = result.scalars().all()

            # 简单关键词匹配过滤
            foreshadows = []
            for record in records:
                # 检查关键词匹配（使用description和original_text）
                content = f"{record.description} {record.original_text or ''}"
                if any(kw in content for kw in keywords) or not keywords:
                    foreshadows.append({
                        "description": record.description,
                        "planted_chapter": record.planted_chapter,
                        "is_resolved": record.status == "resolved",
                        "resolved_chapter": record.resolved_chapter,
                        "priority": record.priority,
                        "category": record.category,
                    })

            return {
                "keywords": keywords,
                "found_count": len(foreshadows),
                "foreshadows": foreshadows[:5],  # 最多返回5个
            }

        return {
            "keywords": keywords,
            "found_count": 0,
            "foreshadows": [],
            "message": "伏笔索引不可用",
        }

    async def _handle_get_previous_content(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """获取前文内容"""
        count = params.get("count", 1)

        previous_paragraphs = []
        for i in range(1, count + 1):
            idx = state.current_index - i
            if idx >= 0:
                previous_paragraphs.append({
                    "index": idx,
                    "content": state.paragraphs[idx][:500],  # 限制长度
                })

        return {
            "current_index": state.current_index,
            "previous_count": len(previous_paragraphs),
            "paragraphs": previous_paragraphs,
        }

    # ==================== 分析工具 ====================

    async def _handle_analyze_paragraph(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """分析当前段落"""
        paragraph = state.current_paragraph
        if not paragraph:
            return {"error": "没有当前段落"}

        # 检查缓存
        if state.current_index in state.paragraph_analyses:
            return state.paragraph_analyses[state.current_index]

        # 使用段落分析器（同步方法）
        analysis = self.paragraph_analyzer.analyze_paragraph(
            paragraph,
            state.current_index,
            state.previous_paragraph,
        )

        # 转换为字典格式
        result = {
            "index": analysis.index,
            "characters": analysis.characters,
            "scene": analysis.scene,
            "time_marker": analysis.time_marker,
            "emotion_tone": analysis.emotion_tone,
            "key_actions": analysis.key_actions,
            "text_preview": paragraph[:200] + "..." if len(paragraph) > 200 else paragraph,
        }

        # 缓存结果
        state.paragraph_analyses[state.current_index] = result
        return result

    async def _handle_check_coherence(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """检查逻辑连贯性"""
        focus = params.get("focus", "general")
        paragraph = state.current_paragraph
        prev_paragraph = state.previous_paragraph

        if not paragraph:
            return {"error": "没有当前段落"}

        issues = []

        # 基础规则检查
        if prev_paragraph:
            # 检查过渡
            transition_words = ["然而", "但是", "因此", "于是", "随后", "接着", "然后"]
            has_transition = any(word in paragraph[:50] for word in transition_words)

            # 检查场景变化是否有过渡
            scene_changed, _ = self.paragraph_analyzer.detect_scene_change(paragraph, prev_paragraph)
            if scene_changed:
                if not has_transition and not paragraph.startswith(("　　", "  ", '"', "「")):
                    issues.append({
                        "type": "transition",
                        "description": "场景发生变化但缺少过渡",
                        "severity": "medium",
                    })

        return {
            "focus": focus,
            "paragraph_index": state.current_index,
            "issues_found": len(issues),
            "issues": issues,
            "needs_deeper_check": len(issues) > 0 or focus != "general",
        }

    async def _handle_check_character(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """检查角色一致性"""
        character_name = params.get("character_name", "")
        paragraph = state.current_paragraph

        if not paragraph:
            return {"error": "没有当前段落"}

        # 获取角色状态
        char_state = await self._handle_get_character_state(
            {"character_name": character_name},
            state,
        )

        issues = []

        if char_state.get("found"):
            # 检查位置一致性
            last_location = char_state.get("location", "")
            if last_location:
                # 简单检查：如果前文提到角色在某地，但当前段落暗示不同位置
                location_words = ["走进", "来到", "离开", "回到", "站在", "坐在"]
                for word in location_words:
                    if word in paragraph and character_name in paragraph:
                        # 可能涉及位置变化，标记需要进一步检查
                        issues.append({
                            "type": "location_change",
                            "description": f"角色 '{character_name}' 可能有位置变化，前文位置: {last_location}",
                            "severity": "low",
                            "needs_verification": True,
                        })
                        break

        return {
            "character_name": character_name,
            "previous_state": char_state if char_state.get("found") else None,
            "issues_found": len(issues),
            "issues": issues,
        }

    async def _handle_check_timeline(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """检查时间线"""
        paragraph = state.current_paragraph
        prev_paragraph = state.previous_paragraph

        if not paragraph:
            return {"error": "没有当前段落"}

        issues = []

        # 时间标记词
        time_markers = {
            "morning": ["清晨", "早晨", "早上", "黎明", "拂晓"],
            "noon": ["中午", "正午", "午时"],
            "afternoon": ["下午", "午后"],
            "evening": ["傍晚", "黄昏", "日暮"],
            "night": ["夜晚", "深夜", "半夜", "子夜", "午夜", "入夜"],
        }

        current_time = None
        prev_time = None

        for period, markers in time_markers.items():
            for marker in markers:
                if marker in paragraph:
                    current_time = period
                    break
            if prev_paragraph:
                for marker in markers:
                    if marker in prev_paragraph:
                        prev_time = period
                        break

        # 检查时间跳跃是否合理
        time_order = ["morning", "noon", "afternoon", "evening", "night"]
        if current_time and prev_time:
            curr_idx = time_order.index(current_time) if current_time in time_order else -1
            prev_idx = time_order.index(prev_time) if prev_time in time_order else -1

            if curr_idx != -1 and prev_idx != -1:
                if curr_idx < prev_idx:
                    # 时间倒退，可能是新的一天或问题
                    issues.append({
                        "type": "time_regression",
                        "description": f"时间可能倒退: 从'{prev_time}'到'{current_time}'，请确认是否为新的一天",
                        "severity": "medium",
                    })

        return {
            "current_time_marker": current_time,
            "previous_time_marker": prev_time,
            "issues_found": len(issues),
            "issues": issues,
        }

    async def _handle_deep_check(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """
        使用LLM进行深度内容检查

        调用CoherenceChecker进行深度分析，返回详细的问题列表和修改建议。
        """
        from .coherence_checker import CoherenceChecker
        from .schemas import CheckDimension, RAGContext, OptimizationContext

        paragraph = state.current_paragraph
        if not paragraph:
            return {"error": "没有当前段落"}

        # 解析检查维度
        dimensions_param = params.get("dimensions", ["coherence"])
        if isinstance(dimensions_param, str):
            dimensions_param = [d.strip() for d in dimensions_param.split(",")]

        dimensions = []
        dimension_map = {
            "coherence": CheckDimension.COHERENCE,
            "character": CheckDimension.CHARACTER,
            "foreshadow": CheckDimension.FORESHADOW,
            "timeline": CheckDimension.TIMELINE,
            "style": CheckDimension.STYLE,
            "scene": CheckDimension.SCENE,
        }
        for d in dimensions_param:
            if d in dimension_map:
                dimensions.append(dimension_map[d])

        if not dimensions:
            dimensions = [CheckDimension.COHERENCE]

        # 获取前文段落
        prev_paragraphs = []
        start_idx = max(0, state.current_index - 3)
        for i in range(start_idx, state.current_index):
            if i < len(state.paragraphs):
                prev_paragraphs.append(state.paragraphs[i])

        # 构建RAG上下文（如果有缓存的信息）
        rag_context = RAGContext(
            retrieved_chunks=[],  # 可以从之前的RAG检索结果中获取
            character_states=state.character_states,
            foreshadowings=[],
        )

        # 构建优化上下文
        context = OptimizationContext(
            project_id=state.project_id,
            chapter_number=state.chapter_number,
            total_chapters=state.total_chapters,
            blueprint_summary="",  # 可以从外部传入
            chapter_outline="",
        )

        # P1修复: 改进LLM服务可用性检查和降级策略
        if self.llm_service is None:
            # LLM服务未注入，返回提示并建议使用快速检查
            logger.warning("深度检查请求但LLM服务未注入")
            return {
                "success": False,
                "message": "深度检查需要LLM服务，当前未配置。建议使用快速检查工具（check_coherence等）进行基础分析。",
                "fallback": True,
                "fallback_reason": "llm_service_not_configured",
                "dimensions_requested": [d.value for d in dimensions],
                "alternative_tools": ["check_coherence", "check_character", "check_timeline"],
            }

        try:
            checker = CoherenceChecker(self.llm_service)
            suggestions = await checker.check_paragraph(
                paragraph=paragraph,
                paragraph_index=state.current_index,
                prev_paragraphs=prev_paragraphs,
                context=context,
                rag_context=rag_context,
                dimensions=dimensions,
                user_id=1,  # 默认用户ID
            )

            # 转换建议为返回格式
            issues = []
            for suggestion in suggestions:
                issues.append({
                    "type": suggestion.category.value if hasattr(suggestion.category, 'value') else str(suggestion.category),
                    "description": suggestion.description,
                    "severity": suggestion.priority.value if hasattr(suggestion.priority, 'value') else str(suggestion.priority),
                    "original_text": suggestion.original_text,
                    "suggested_text": suggestion.suggested_text,
                    "reason": suggestion.reason,
                })

            return {
                "success": True,
                "dimensions_checked": [d.value for d in dimensions],
                "issues_found": len(issues),
                "issues": issues,
                "analysis_mode": "llm_deep_check",
            }

        except Exception as e:
            error_str = str(e).lower()
            logger.error("深度检查失败: %s", e, exc_info=True)

            # P1修复: 根据错误类型提供更好的降级建议
            fallback_reason = "unknown_error"
            fallback_message = f"深度检查执行失败: {str(e)}"

            if "quota" in error_str or "limit" in error_str or "rate" in error_str:
                fallback_reason = "quota_exceeded"
                fallback_message = "LLM服务配额已用尽，建议使用快速检查工具进行基础分析"
            elif "timeout" in error_str:
                fallback_reason = "timeout"
                fallback_message = "深度检查超时，建议使用快速检查工具或稍后重试"
            elif "connection" in error_str or "network" in error_str:
                fallback_reason = "network_error"
                fallback_message = "网络连接失败，请检查网络后重试"

            return {
                "success": False,
                "message": fallback_message,
                "fallback": True,
                "fallback_reason": fallback_reason,
                "dimensions_requested": [d.value for d in dimensions],
                "alternative_tools": ["check_coherence", "check_character", "check_timeline"],
            }

    # ==================== 输出工具 ====================

    async def _handle_generate_suggestion(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """生成修改建议"""
        suggestion = {
            "paragraph_index": state.current_index,
            "category": params.get("issue_type", "coherence"),
            "issue_description": params.get("issue_description", ""),
            "original_text": params.get("original_text", ""),
            "suggested_text": params.get("suggested_text", ""),
            "reason": params.get("reason", ""),
            "priority": params.get("priority", "medium"),
        }

        state.suggestions.append(suggestion)

        return {
            "recorded": True,
            "suggestion_index": len(state.suggestions) - 1,
            "message": "建议已记录",
        }

    async def _handle_record_observation(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """记录观察"""
        observation = {
            "paragraph_index": state.current_index,
            "content": params.get("observation", ""),
            "category": params.get("category", "info"),
        }

        state.observations.append(observation)

        return {
            "recorded": True,
            "observation_index": len(state.observations) - 1,
        }

    # ==================== 控制工具 ====================

    async def _handle_next_paragraph(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """移动到下一段"""
        if state.move_to_next():
            return {
                "success": True,
                "new_index": state.current_index,
                "paragraph_preview": state.current_paragraph[:100] if state.current_paragraph else "",
                "remaining": len(state.paragraphs) - state.current_index - 1,
            }
        else:
            return {
                "success": False,
                "message": "已是最后一段",
                "should_complete": True,
            }

    async def _handle_finish_analysis(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """完成当前段落分析"""
        summary = params.get("summary", "")

        return {
            "paragraph_index": state.current_index,
            "summary": summary,
            "suggestions_count": len([s for s in state.suggestions if s["paragraph_index"] == state.current_index]),
            "has_more": state.has_more_paragraphs(),
        }

    async def _handle_complete_workflow(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """完成工作流"""
        state.is_complete = True
        state.summary = params.get("overall_summary", "分析完成")

        return {
            "completed": True,
            "total_paragraphs": len(state.paragraphs),
            "total_suggestions": len(state.suggestions),
            "total_observations": len(state.observations),
            "summary": state.summary,
        }
