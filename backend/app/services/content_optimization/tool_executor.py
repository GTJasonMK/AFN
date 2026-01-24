"""
工具执行器

负责实际执行Agent调用的工具，并返回结果。
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from .tools import ToolName, ToolCall, ToolResult
from .paragraph_analyzer import ParagraphAnalyzer
from ..foreshadowing_service import ForeshadowingService
from ..incremental_indexer import IncrementalIndexer
from ..vector_store_service import VectorStoreService
from ..rag.temporal_retriever import TemporalAwareRetriever
from ..agent_tool_executor_base import BaseToolExecutor

logger = logging.getLogger(__name__)


class AgentState:
    """Agent状态，跟踪分析过程中的信息"""

    # 缓存大小限制
    MAX_ANALYSIS_CACHE = 50  # 只保留最近50段的分析结果
    MAX_CHARACTER_STATES = 30  # 只保留最近30个角色的状态

    def __init__(
        self,
        paragraphs: List[str],
        project_id: str,
        chapter_number: int,
        total_chapters: int = 0,
        paragraph_analyzer: Optional["ParagraphAnalyzer"] = None,
    ):
        self.paragraphs = paragraphs
        self.project_id = project_id
        self.chapter_number = chapter_number
        self.total_chapters = total_chapters
        self.paragraph_analyzer = paragraph_analyzer  # 用于内容更新时重新分段

        # 当前段落索引
        self.current_index = 0

        # 已生成的建议
        self.suggestions: List[Dict[str, Any]] = []

        # 观察记录
        self.observations: List[Dict[str, Any]] = []

        # 段落分析缓存（带LRU清理）
        self.paragraph_analyses: Dict[int, Dict[str, Any]] = {}
        self._analysis_access_order: List[int] = []  # 追踪访问顺序

        # 角色状态缓存（带LRU清理）
        self.character_states: Dict[str, Dict[str, Any]] = {}
        self._character_access_order: List[str] = []  # 追踪访问顺序

        # 是否完成
        self.is_complete = False

        # 分析总结
        self.summary = ""

        # P0修复: 存储RAG检索结果，用于传递给深度检查
        self.rag_results: List[Dict[str, Any]] = []

    def update_content(self, new_content: str) -> bool:
        """
        更新分析内容（当用户在前端应用了建议后）

        此方法在 Agent 从暂停状态恢复时调用，用于同步前端编辑器的最新内容。
        它会重新分段并尝试定位到当前分析位置。

        Args:
            new_content: 前端发送的最新编辑器内容

        Returns:
            是否成功更新
        """
        if not self.paragraph_analyzer:
            logger.warning("无法更新内容：paragraph_analyzer 未设置")
            return False

        # 保存当前段落的特征（用于重新定位）
        old_paragraph = self.current_paragraph
        old_index = self.current_index

        # 重新分段
        new_paragraphs = self.paragraph_analyzer.split_paragraphs(new_content)
        if not new_paragraphs:
            logger.warning("更新内容失败：分段结果为空")
            return False

        # 更新段落列表
        self.paragraphs = new_paragraphs

        # 重新定位当前段落
        new_index = self._relocate_paragraph(old_paragraph, old_index)
        self.current_index = new_index

        # 清除已分析段落的缓存（内容已变化，缓存失效）
        self.paragraph_analyses.clear()
        self._analysis_access_order.clear()

        logger.info(
            "内容已更新: 旧段落数=%d, 新段落数=%d, 旧索引=%d, 新索引=%d",
            old_index + 1 if old_paragraph else 0,
            len(new_paragraphs),
            old_index,
            new_index,
        )

        return True

    def _relocate_paragraph(self, old_paragraph: Optional[str], old_index: int) -> int:
        """
        在新内容中重新定位段落位置

        策略：
        1. 如果旧段落文本在新段落中存在，使用该位置
        2. 否则使用旧索引（但不超过新段落数）
        3. 如果旧索引也超出范围，从最后一段继续

        Args:
            old_paragraph: 旧的当前段落文本
            old_index: 旧的段落索引

        Returns:
            新的段落索引
        """
        if not old_paragraph:
            return min(old_index, len(self.paragraphs) - 1)

        # 尝试精确匹配
        for i, para in enumerate(self.paragraphs):
            if para == old_paragraph:
                return i

        # 尝试部分匹配（前100字符）
        old_prefix = old_paragraph[:100] if len(old_paragraph) > 100 else old_paragraph
        for i, para in enumerate(self.paragraphs):
            if para.startswith(old_prefix):
                return i

        # 回退到旧索引（但不超过范围）
        return min(old_index, len(self.paragraphs) - 1)

    def cache_paragraph_analysis(self, index: int, analysis: Dict[str, Any]):
        """缓存段落分析结果（带LRU清理）"""
        # 如果已存在，先从访问顺序中移除
        if index in self._analysis_access_order:
            self._analysis_access_order.remove(index)

        # 添加到缓存和访问顺序末尾
        self.paragraph_analyses[index] = analysis
        self._analysis_access_order.append(index)

        # 超出限制时清理最早访问的条目
        while len(self._analysis_access_order) > self.MAX_ANALYSIS_CACHE:
            old_index = self._analysis_access_order.pop(0)
            if old_index in self.paragraph_analyses:
                del self.paragraph_analyses[old_index]

    def get_paragraph_analysis(self, index: int) -> Optional[Dict[str, Any]]:
        """获取段落分析结果（更新访问顺序）"""
        if index in self.paragraph_analyses:
            # 更新访问顺序
            if index in self._analysis_access_order:
                self._analysis_access_order.remove(index)
            self._analysis_access_order.append(index)
            return self.paragraph_analyses[index]
        return None

    def cache_character_state(self, name: str, state: Dict[str, Any]):
        """缓存角色状态（带LRU清理）"""
        # 如果已存在，先从访问顺序中移除
        if name in self._character_access_order:
            self._character_access_order.remove(name)

        # 添加到缓存和访问顺序末尾
        self.character_states[name] = state
        self._character_access_order.append(name)

        # 超出限制时清理最早访问的条目
        while len(self._character_access_order) > self.MAX_CHARACTER_STATES:
            old_name = self._character_access_order.pop(0)
            if old_name in self.character_states:
                del self.character_states[old_name]

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


class ToolExecutor(BaseToolExecutor):
    """工具执行器"""

    def __init__(
        self,
        session: AsyncSession,
        vector_store: Optional[VectorStoreService],
        paragraph_analyzer: ParagraphAnalyzer,
        embedding_service: Optional[Any] = None,  # EmbeddingService
        enable_character_index: bool = False,  # 是否启用角色状态索引查询
        enable_foreshadowing_index: bool = False,  # 是否启用伏笔索引查询
        llm_service: Optional[Any] = None,  # LLMService，用于深度检查
        prompt_service: Optional[Any] = None,  # PromptService，用于加载提示词
        user_id: str = "1",  # 用户ID，用于LLM调用
    ):
        self.session = session
        self.vector_store = vector_store
        self.paragraph_analyzer = paragraph_analyzer
        self.embedding_service = embedding_service
        self.enable_character_index = enable_character_index
        self.enable_foreshadowing_index = enable_foreshadowing_index
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.user_id = user_id

        # 初始化时序感知检索器
        self.temporal_retriever: Optional[TemporalAwareRetriever] = None
        if vector_store:
            self.temporal_retriever = TemporalAwareRetriever(vector_store)
        super().__init__()

    def _build_handlers(self) -> Dict[ToolName, Any]:
        """构建工具处理器映射"""
        return {
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

    def _get_tool_name(self, tool_call: ToolCall) -> ToolName:
        """获取工具名称"""
        return tool_call.tool_name

    def _get_tool_params(self, tool_call: ToolCall) -> Dict[str, Any]:
        """获取工具参数"""
        return tool_call.parameters

    def _build_result(
        self,
        tool_name: ToolName,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> ToolResult:
        """构建工具结果"""
        return ToolResult(
            tool_name=tool_name,
            success=success,
            result=result,
            error=error,
        )

    def _format_unknown_tool_error(self, tool_name: ToolName) -> str:
        """格式化未知工具错误信息"""
        return f"未知工具: {tool_name.value}"

    def _log_tool_call(self, tool_call: ToolCall) -> None:
        """记录工具调用日志"""
        logger.info(
            "执行工具: %s, 参数: %s, 理由: %s",
            tool_call.tool_name.value,
            tool_call.parameters,
            tool_call.reasoning,
        )

    def _log_execute_error(self, tool_name: ToolName, error: Exception) -> None:
        """记录工具执行错误"""
        logger.error("工具执行失败: %s - %s", tool_name.value, error, exc_info=True)

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
                try:
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

                    # P0修复: 存储RAG结果到state，供DEEP_CHECK使用
                    state.rag_results = results

                    return {
                        "success": True,
                        "query": query,
                        "results_count": len(results),
                        "results": results,
                        "retrieval_mode": "temporal_aware",
                    }

                except Exception as e:
                    # P0修复: 时序检索失败时不静默降级，而是抛出异常
                    # 遵循CLAUDE.md规范："功能无法正常执行就直接报错"
                    logger.error("时序感知检索失败: %s", e)
                    raise RuntimeError(
                        f"时序感知检索失败: {str(e)}。"
                        "请检查嵌入服务配置是否正确。"
                    ) from e

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

            # P0修复: 存储RAG结果到state，供DEEP_CHECK使用
            state.rag_results = results

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
            # 更新访问顺序
            if character_name in state._character_access_order:
                state._character_access_order.remove(character_name)
            state._character_access_order.append(character_name)
            return state.character_states[character_name]

        # 从索引中查询
        if self.enable_character_index:
            indexer = IncrementalIndexer(self.session)
            char_state = await indexer.get_latest_character_state_before(
                project_id=state.project_id,
                chapter_number=state.chapter_number,
                character_name=character_name,
            )
            if char_state:
                state.cache_character_state(character_name, char_state)
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

        if self.enable_foreshadowing_index:
            service = ForeshadowingService(self.session)
            suggestions = await service.get_pending_for_generation(
                project_id=state.project_id,
                chapter_number=state.chapter_number,
                max_suggestions=10,
                keywords=keywords,
            )

            foreshadows = []
            for item in suggestions:
                foreshadows.append({
                    "description": item["description"],
                    "planted_chapter": item["planted_chapter"],
                    "is_resolved": False,
                    "resolved_chapter": None,
                    "priority": item["priority"],
                    "category": item["category"],
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
            return {
                "error": "没有当前段落",
                "current_paragraph_index": state.current_index,
                "total_paragraphs": len(state.paragraphs),
            }

        # 检查缓存（使用新的缓存方法）
        cached = state.get_paragraph_analysis(state.current_index)
        if cached:
            # 添加位置信息到缓存结果
            cached["current_paragraph_index"] = state.current_index
            cached["total_paragraphs"] = len(state.paragraphs)
            return cached

        # 使用段落分析器（同步方法）
        analysis = self.paragraph_analyzer.analyze_paragraph(
            paragraph,
            state.current_index,
            state.previous_paragraph,
        )

        # 转换为字典格式
        # 注意：提供完整段落文本（full_text），供Agent在生成建议时精确匹配原文
        result = {
            "current_paragraph_index": state.current_index,
            "total_paragraphs": len(state.paragraphs),
            "characters": analysis.characters,
            "scene": analysis.scene,
            "time_marker": analysis.time_marker,
            "emotion_tone": analysis.emotion_tone,
            "key_actions": analysis.key_actions,
            "scene_descriptor": self.paragraph_analyzer.build_scene_descriptor(analysis),
            "text_preview": paragraph[:200] + "..." if len(paragraph) > 200 else paragraph,
            "full_text": paragraph,  # 完整段落文本，用于生成建议时精确匹配
        }

        # 缓存结果（使用新的缓存方法）
        state.cache_paragraph_analysis(state.current_index, result)
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
            return {
                "error": "没有当前段落",
                "current_paragraph_index": state.current_index,
            }

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
            "current_paragraph_index": state.current_index,
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
            return {
                "error": "没有当前段落",
                "current_paragraph_index": state.current_index,
            }

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
            "current_paragraph_index": state.current_index,
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
            return {
                "error": "没有当前段落",
                "current_paragraph_index": state.current_index,
            }

        issues = []

        # 时间标记词 - 使用反向映射提高查询效率
        time_marker_map = {
            # morning
            "清晨": "morning", "早晨": "morning", "早上": "morning",
            "黎明": "morning", "拂晓": "morning",
            # noon
            "中午": "noon", "正午": "noon", "午时": "noon",
            # afternoon
            "下午": "afternoon", "午后": "afternoon",
            # evening
            "傍晚": "evening", "黄昏": "evening", "日暮": "evening",
            # night
            "夜晚": "night", "深夜": "night", "半夜": "night",
            "子夜": "night", "午夜": "night", "入夜": "night",
        }

        def find_time_marker(text: str) -> Optional[str]:
            """在文本中查找第一个时间标记"""
            if not text:
                return None
            for marker, period in time_marker_map.items():
                if marker in text:
                    return period
            return None

        current_time = find_time_marker(paragraph)
        prev_time = find_time_marker(prev_paragraph) if prev_paragraph else None

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
            "current_paragraph_index": state.current_index,
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
        from .schemas import RAGContext, OptimizationContext

        paragraph = state.current_paragraph
        if not paragraph:
            return {
                "error": "没有当前段落",
                "current_paragraph_index": state.current_index,
            }

        # 解析检查维度（统一使用字符串格式）
        dimensions_param = params.get("dimensions", ["coherence"])
        if isinstance(dimensions_param, str):
            # 支持中文和英文逗号，并过滤空字符串
            normalized = dimensions_param.replace("，", ",")
            dimensions_param = [d.strip() for d in normalized.split(",") if d.strip()]
        elif not isinstance(dimensions_param, list):
            # 处理其他类型
            logger.warning("未预期的维度参数类型: %s，使用默认值", type(dimensions_param))
            dimensions_param = ["coherence"]

        # 验证维度有效性
        valid_dimensions = {"coherence", "character", "foreshadow", "timeline", "style", "scene"}
        dimensions = [d for d in dimensions_param if d in valid_dimensions]

        # 记录被过滤的无效维度
        invalid_dims = [d for d in dimensions_param if d and d not in valid_dimensions]
        if invalid_dims:
            logger.warning("忽略无效的检查维度: %s", invalid_dims)

        if not dimensions:
            dimensions = ["coherence"]

        # 获取前文段落
        prev_paragraphs = []
        start_idx = max(0, state.current_index - 3)
        for i in range(start_idx, state.current_index):
            if i < len(state.paragraphs):
                prev_paragraphs.append(state.paragraphs[i])

        # 构建RAG上下文（转换 character_states 为 List[dict] 格式）
        character_states_list = [
            {"character": name, "state": info.get("status", ""), **info}
            for name, info in state.character_states.items()
        ]
        # P0修复: 使用state中存储的RAG检索结果，而非硬编码空列表
        # RAG结果在RETRIEVE_CONTEXT工具执行时已存储到state.rag_results
        rag_context = RAGContext(
            related_chunks=state.rag_results,
            character_states=character_states_list,
            foreshadowings=[],
        )

        # 构建优化上下文
        context = OptimizationContext(
            project_id=state.project_id,
            chapter_number=state.chapter_number,
            total_chapters=state.total_chapters,
            blueprint_core="",  # 可以从外部传入
        )

        # P0修复: LLM服务未配置时直接抛出异常，不使用降级策略
        # 遵循CLAUDE.md规范："功能无法正常执行就直接报错"
        if self.llm_service is None:
            logger.error("深度检查请求但LLM服务未注入")
            raise ValueError(
                "深度检查需要LLM服务，当前未配置。"
                "请在设置页面配置LLM服务后重试。"
            )

        try:
            # P1修复: 传入 prompt_service 以支持外部提示词加载
            checker = CoherenceChecker(self.llm_service, self.prompt_service)
            suggestions = await checker.check_paragraph(
                paragraph=paragraph,
                paragraph_index=state.current_index,
                prev_paragraphs=prev_paragraphs,
                context=context,
                rag_context=rag_context,
                dimensions=dimensions,
                user_id=self.user_id,
            )

            # 转换建议为返回格式（SuggestionEvent 的 category/priority 是 str 类型）
            issues = []
            for suggestion in suggestions:
                issues.append({
                    "type": suggestion.category,
                    "description": suggestion.reason,  # SuggestionEvent 没有 description，使用 reason
                    "severity": suggestion.priority,
                    "original_text": suggestion.original_text,
                    "suggested_text": suggestion.suggested_text,
                    "reason": suggestion.reason,
                })

            return {
                "success": True,
                "current_paragraph_index": state.current_index,
                "dimensions_checked": dimensions,  # 已经是字符串列表
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
                "dimensions_requested": dimensions,  # 已经是字符串列表
                "alternative_tools": ["check_coherence", "check_character", "check_timeline"],
            }

    # ==================== 输出工具 ====================

    async def _handle_generate_suggestion(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> Dict[str, Any]:
        """生成修改建议"""
        original_text = params.get("original_text", "")
        suggested_text = params.get("suggested_text", "")

        # 验证 original_text 必须存在于当前段落中
        current_paragraph = state.current_paragraph or ""
        if original_text and original_text not in current_paragraph:
            # 尝试去除首尾空白后再匹配
            trimmed_original = original_text.strip()
            if trimmed_original not in current_paragraph:
                logger.warning(
                    "generate_suggestion: original_text 不存在于当前段落中。"
                    "original_text前50字: %s, 当前段落前100字: %s",
                    original_text[:50],
                    current_paragraph[:100],
                )
                return {
                    "recorded": False,
                    "error": "original_text 必须是当前段落中实际存在的文本片段。"
                             "请从 analyze_paragraph 返回的 full_text 中精确复制需要修改的文本。",
                    "current_paragraph_index": state.current_index,
                    "hint": f"当前段落内容前200字: {current_paragraph[:200]}...",
                }

        suggestion = {
            "paragraph_index": state.current_index,
            "category": params.get("issue_type", "coherence"),
            "issue_description": params.get("issue_description", ""),
            "original_text": original_text,
            "suggested_text": suggested_text,
            "reason": params.get("reason", ""),
            "priority": params.get("priority", "medium"),
        }

        state.suggestions.append(suggestion)

        return {
            "recorded": True,
            "current_paragraph_index": state.current_index,
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
            "current_paragraph_index": state.current_index,
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
        """完成当前段落分析并自动移动到下一段"""
        summary = params.get("summary", "")
        finished_index = state.current_index
        suggestions_count = len([s for s in state.suggestions if s["paragraph_index"] == finished_index])

        # 自动移动到下一段
        has_more = state.has_more_paragraphs()
        if has_more:
            state.move_to_next()
            return {
                "finished_paragraph_index": finished_index,
                "summary": summary,
                "suggestions_count": suggestions_count,
                "moved_to_next": True,
                "current_paragraph_index": state.current_index,
                "current_paragraph_preview": state.current_paragraph[:200] + "..." if state.current_paragraph and len(state.current_paragraph) > 200 else state.current_paragraph,
                "remaining_paragraphs": len(state.paragraphs) - state.current_index - 1,
                "message": f"第{finished_index + 1}段分析完成，已自动移动到第{state.current_index + 1}段",
            }
        else:
            return {
                "finished_paragraph_index": finished_index,
                "summary": summary,
                "suggestions_count": suggestions_count,
                "moved_to_next": False,
                "is_last_paragraph": True,
                "message": f"第{finished_index + 1}段分析完成，这是最后一段，请调用 complete_workflow 结束分析",
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
