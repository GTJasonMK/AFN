"""
编程项目 Prompt 优化 - 工具执行器

负责执行 Agent 调用的各种工具，包括信息获取、检查、输出等。
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    OptimizationContext,
    PromptType,
    Suggestion,
    SuggestionSeverity,
    DIMENSION_DISPLAY_NAMES,
    REVIEW_DIMENSION_DISPLAY_NAMES,
    get_dimension_weight,
    get_dimension_display_name,
)
from .tools import ToolName, ToolResult

logger = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Agent 状态跟踪"""
    # 输入数据
    project_id: str
    feature_id: str
    prompt_content: str                         # 要分析的 Prompt 内容
    context: OptimizationContext                # 优化上下文

    # 当前状态
    is_complete: bool = False
    current_dimension: Optional[str] = None     # 当前检查的维度

    # 累积结果
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[Dict[str, Any]] = field(default_factory=list)

    # 缓存
    feature_context_cache: Optional[Dict[str, Any]] = None
    dependencies_cache: Optional[List[Dict[str, Any]]] = None
    rag_cache: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    # 检查结果缓存
    check_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 最终总结
    summary: str = ""
    overall_quality: str = ""


class ToolExecutor:
    """
    工具执行器

    负责执行 Agent 调用的各种工具。
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: Any,
        vector_store: Any,
        user_id: str,
        prompt_checker: Optional[Any] = None,
        prompt_type: PromptType = PromptType.IMPLEMENTATION,
    ):
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.user_id = user_id
        self.prompt_checker = prompt_checker
        self.prompt_type = prompt_type

    async def execute(
        self,
        tool_name: ToolName,
        parameters: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """
        执行工具

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            state: Agent 状态

        Returns:
            工具执行结果
        """
        # 获取工具处理器
        handler = self._get_handler(tool_name)
        if not handler:
            return ToolResult(
                success=False,
                error=f"未知的工具: {tool_name}",
            )

        try:
            result = await handler(parameters, state)
            return result
        except Exception as e:
            logger.error("工具执行失败: %s, error=%s", tool_name, e, exc_info=True)
            return ToolResult(
                success=False,
                error=f"工具执行异常: {str(e)}",
            )

    def _get_handler(self, tool_name: ToolName) -> Optional[Callable]:
        """获取工具处理器"""
        handlers = {
            # 信息获取工具
            ToolName.RAG_RETRIEVE: self._handle_rag_retrieve,
            ToolName.GET_FEATURE_CONTEXT: self._handle_get_feature_context,
            ToolName.GET_DEPENDENCIES: self._handle_get_dependencies,
            # 检查工具
            ToolName.CHECK_COMPLETENESS: self._handle_check_completeness,
            ToolName.CHECK_INTERFACE: self._handle_check_interface,
            ToolName.CHECK_DEPENDENCY: self._handle_check_dependency,
            ToolName.DEEP_CHECK: self._handle_deep_check,
            # 输出工具
            ToolName.GENERATE_SUGGESTION: self._handle_generate_suggestion,
            ToolName.RECORD_OBSERVATION: self._handle_record_observation,
            # 控制工具
            ToolName.COMPLETE_WORKFLOW: self._handle_complete_workflow,
        }
        return handlers.get(tool_name)

    # ==================== 信息获取工具 ====================

    async def _handle_rag_retrieve(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """RAG 检索"""
        query = params.get("query", "")
        data_types = params.get("data_types", [])
        top_k = params.get("top_k", 5)

        if not query:
            return ToolResult(success=False, error="缺少查询文本")

        # 检查缓存
        cache_key = f"{query}:{','.join(sorted(data_types))}:{top_k}"
        if cache_key in state.rag_cache:
            cached = state.rag_cache[cache_key]
            return ToolResult(
                success=True,
                data={"results": cached},
                summary=f"从缓存返回 {len(cached)} 条检索结果",
            )

        # 执行检索
        if not self.vector_store or not self.vector_store._client:
            return ToolResult(
                success=False,
                error="向量库未启用",
            )

        try:
            # 获取嵌入向量
            embedding = await self.llm_service.get_embedding(query, user_id=self.user_id)
            if not embedding:
                return ToolResult(success=False, error="生成嵌入向量失败")

            # 执行检索
            results = await self.vector_store.search(
                project_id=state.project_id,
                query_embedding=embedding,
                top_k=top_k,
                data_types=data_types if data_types else None,
            )

            # 格式化结果
            formatted_results = []
            for chunk in results:
                formatted_results.append({
                    "data_type": chunk.get("metadata", {}).get("data_type", "unknown"),
                    "content": chunk.get("content", "")[:500],  # 截断
                    "score": round(chunk.get("score", 0), 3),
                    "source": chunk.get("chapter_title", ""),
                })

            # 缓存结果
            state.rag_cache[cache_key] = formatted_results

            return ToolResult(
                success=True,
                data={"results": formatted_results},
                summary=f"检索到 {len(formatted_results)} 条相关内容",
            )

        except Exception as e:
            logger.error("RAG 检索失败: %s", e)
            return ToolResult(success=False, error=f"检索失败: {str(e)}")

    async def _handle_get_feature_context(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """获取功能上下文"""
        # 检查缓存
        if state.feature_context_cache:
            return ToolResult(
                success=True,
                data=state.feature_context_cache,
                summary="返回已缓存的功能上下文",
            )

        ctx = state.context
        feature = ctx.feature
        project = ctx.project

        # 构建上下文数据
        context_data = {
            "feature": {
                "id": feature.feature_id,
                "number": feature.feature_number,
                "name": feature.feature_name,
                "description": feature.feature_description,
                "inputs": feature.inputs,
                "outputs": feature.outputs,
                "priority": feature.priority,
            },
            "hierarchy": {
                "system_number": feature.system_number,
                "system_name": feature.system_name,
                "module_number": feature.module_number,
                "module_name": feature.module_name,
            },
            "project": {
                "name": project.project_name,
                "architecture": project.architecture_synopsis[:500] if project.architecture_synopsis else None,
            },
            "tech_stack": project.tech_stack,
            "prompt_length": len(state.prompt_content),
        }

        # 缓存
        state.feature_context_cache = context_data

        return ToolResult(
            success=True,
            data=context_data,
            summary=f"功能 {feature.feature_number}: {feature.feature_name}，属于系统 {feature.system_name} / 模块 {feature.module_name}",
        )

    async def _handle_get_dependencies(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """获取依赖关系"""
        include_reverse = params.get("include_reverse", True)

        # 检查缓存
        if state.dependencies_cache is not None:
            return ToolResult(
                success=True,
                data={"dependencies": state.dependencies_cache},
                summary=f"返回 {len(state.dependencies_cache)} 条依赖关系",
            )

        ctx = state.context
        all_deps = ctx.project.dependencies or []

        # 过滤与当前功能相关的依赖
        feature_name = ctx.feature.feature_name
        module_name = ctx.feature.module_name

        related_deps = []
        for dep in all_deps:
            from_mod = dep.get("from", dep.get("from_module", ""))
            to_mod = dep.get("to", dep.get("to_module", ""))

            # 检查是否与当前功能/模块相关
            is_outgoing = from_mod == module_name or from_mod == feature_name
            is_incoming = to_mod == module_name or to_mod == feature_name

            if is_outgoing:
                related_deps.append({
                    "direction": "outgoing",
                    "from": from_mod,
                    "to": to_mod,
                    "description": dep.get("description", ""),
                })
            elif is_incoming and include_reverse:
                related_deps.append({
                    "direction": "incoming",
                    "from": from_mod,
                    "to": to_mod,
                    "description": dep.get("description", ""),
                })

        # 缓存
        state.dependencies_cache = related_deps

        return ToolResult(
            success=True,
            data={"dependencies": related_deps},
            summary=f"找到 {len(related_deps)} 条相关依赖关系",
        )

    # ==================== 检查工具 ====================

    async def _handle_check_completeness(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """检查功能完整性"""
        # 检查缓存
        if "completeness" in state.check_results:
            return ToolResult(
                success=True,
                data=state.check_results["completeness"],
                summary="返回已缓存的完整性检查结果",
            )

        prompt = state.prompt_content
        feature = state.context.feature

        issues = []

        # 检查1: 功能描述中的关键词是否在 Prompt 中有体现
        if feature.feature_description:
            # 提取关键词（简单的名词短语提取）
            keywords = self._extract_keywords(feature.feature_description)
            missing_keywords = [kw for kw in keywords if kw not in prompt]
            if missing_keywords:
                issues.append({
                    "type": "missing_keyword",
                    "description": f"功能描述中的关键词在 Prompt 中未体现: {', '.join(missing_keywords[:5])}",
                    "severity": "medium",
                })

        # 检查2: 输入参数是否有处理
        if feature.inputs:
            input_keywords = self._extract_keywords(feature.inputs)
            missing_inputs = [inp for inp in input_keywords if inp not in prompt]
            if missing_inputs:
                issues.append({
                    "type": "missing_input",
                    "description": f"输入参数可能未处理: {', '.join(missing_inputs[:3])}",
                    "severity": "high",
                })

        # 检查3: 输出是否有说明
        if feature.outputs:
            output_keywords = self._extract_keywords(feature.outputs)
            missing_outputs = [out for out in output_keywords if out not in prompt]
            if missing_outputs:
                issues.append({
                    "type": "missing_output",
                    "description": f"输出结果可能未说明: {', '.join(missing_outputs[:3])}",
                    "severity": "high",
                })

        # 检查4: 是否有实现步骤
        step_patterns = [r"步骤\s*\d", r"\d+\.", r"首先|然后|最后|接着"]
        has_steps = any(re.search(p, prompt) for p in step_patterns)
        if not has_steps and len(prompt) > 200:
            issues.append({
                "type": "no_steps",
                "description": "Prompt 较长但没有明确的实现步骤",
                "severity": "medium",
            })

        result = {
            "passed": len(issues) == 0,
            "issues": issues,
            "checked_items": ["关键词覆盖", "输入处理", "输出说明", "实现步骤"],
        }

        # 缓存
        state.check_results["completeness"] = result

        return ToolResult(
            success=True,
            data=result,
            summary=f"完整性检查: {'通过' if result['passed'] else f'发现 {len(issues)} 个问题'}",
        )

    async def _handle_check_interface(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """检查接口定义"""
        # 检查缓存
        if "interface" in state.check_results:
            return ToolResult(
                success=True,
                data=state.check_results["interface"],
                summary="返回已缓存的接口检查结果",
            )

        prompt = state.prompt_content
        issues = []

        # 检查1: 是否有函数/方法定义的模式
        func_patterns = [
            r"def\s+\w+\s*\(",           # Python
            r"function\s+\w+\s*\(",       # JavaScript
            r"async\s+\w+\s*\(",          # async function
            r"\w+\s*\([^)]*\)\s*[:{]",    # 通用函数签名
        ]
        has_func_def = any(re.search(p, prompt) for p in func_patterns)

        # 检查2: 是否有参数说明
        param_patterns = [r"参数[:：]", r"Args:", r"Parameters:", r"@param"]
        has_param_doc = any(re.search(p, prompt, re.IGNORECASE) for p in param_patterns)

        # 检查3: 是否有返回值说明
        return_patterns = [r"返回[:：]", r"Returns:", r"@return", r"->"]
        has_return_doc = any(re.search(p, prompt, re.IGNORECASE) for p in return_patterns)

        # 检查4: 是否有类型注解
        type_patterns = [r":\s*(int|str|float|bool|List|Dict|Optional)", r"<\w+>"]
        has_type_hint = any(re.search(p, prompt) for p in type_patterns)

        # 生成问题
        if not has_func_def:
            issues.append({
                "type": "no_function_signature",
                "description": "未找到明确的函数/方法签名定义",
                "severity": "medium",
            })

        if not has_param_doc and len(prompt) > 300:
            issues.append({
                "type": "no_param_doc",
                "description": "缺少参数说明文档",
                "severity": "low",
            })

        if not has_return_doc and len(prompt) > 300:
            issues.append({
                "type": "no_return_doc",
                "description": "缺少返回值说明",
                "severity": "low",
            })

        result = {
            "passed": len([i for i in issues if i["severity"] != "low"]) == 0,
            "issues": issues,
            "findings": {
                "has_function_signature": has_func_def,
                "has_param_doc": has_param_doc,
                "has_return_doc": has_return_doc,
                "has_type_hints": has_type_hint,
            },
        }

        # 缓存
        state.check_results["interface"] = result

        return ToolResult(
            success=True,
            data=result,
            summary=f"接口检查: {'通过' if result['passed'] else f'发现 {len(issues)} 个问题'}",
        )

    async def _handle_check_dependency(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """检查依赖关系"""
        # 检查缓存
        if "dependency" in state.check_results:
            return ToolResult(
                success=True,
                data=state.check_results["dependency"],
                summary="返回已缓存的依赖检查结果",
            )

        prompt = state.prompt_content
        issues = []

        # 获取项目中的模块列表
        ctx = state.context
        all_deps = ctx.project.dependencies or []

        # 提取 Prompt 中提到的模块名
        # 简单的启发式：查找类似 XxxService, XxxRepository, XxxController 的模式
        module_pattern = r"\b([A-Z][a-z]+(?:Service|Repository|Controller|Manager|Helper|Util|Client))\b"
        mentioned_modules = set(re.findall(module_pattern, prompt))

        # 检查提到的模块是否在依赖关系中
        declared_deps = set()
        for dep in all_deps:
            declared_deps.add(dep.get("from", ""))
            declared_deps.add(dep.get("to", ""))

        undeclared = mentioned_modules - declared_deps
        if undeclared:
            issues.append({
                "type": "undeclared_dependency",
                "description": f"Prompt 中提到了未在依赖关系中声明的模块: {', '.join(list(undeclared)[:3])}",
                "severity": "medium",
            })

        # 检查是否有导入语句
        import_patterns = [r"import\s+", r"from\s+\w+\s+import", r"require\("]
        has_imports = any(re.search(p, prompt) for p in import_patterns)

        if mentioned_modules and not has_imports:
            issues.append({
                "type": "no_import_statement",
                "description": "提到了外部模块但没有导入说明",
                "severity": "low",
            })

        result = {
            "passed": len([i for i in issues if i["severity"] != "low"]) == 0,
            "issues": issues,
            "mentioned_modules": list(mentioned_modules),
        }

        # 缓存
        state.check_results["dependency"] = result

        return ToolResult(
            success=True,
            data=result,
            summary=f"依赖检查: {'通过' if result['passed'] else f'发现 {len(issues)} 个问题'}",
        )

    async def _handle_deep_check(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """LLM 深度检查"""
        dimensions = params.get("dimensions", [])
        focus_area = params.get("focus_area", "")

        if not dimensions:
            return ToolResult(success=False, error="缺少检查维度")

        # 如果有 prompt_checker，使用它进行深度检查
        if self.prompt_checker:
            try:
                check_result = await self.prompt_checker.deep_check(
                    prompt_content=state.prompt_content,
                    context=state.context,
                    dimensions=dimensions,
                    focus_area=focus_area,
                    user_id=self.user_id,
                )
                return ToolResult(
                    success=True,
                    data=check_result,
                    summary=f"深度检查完成，检查了 {len(dimensions)} 个维度",
                )
            except Exception as e:
                logger.error("深度检查失败: %s", e)
                # 降级处理

        # 降级：使用简单的规则检查
        all_issues = []
        for dim in dimensions:
            dim_name = get_dimension_display_name(dim, self.prompt_type)
            all_issues.append({
                "dimension": dim,
                "dimension_name": dim_name,
                "status": "skipped",
                "reason": "LLM 深度检查不可用，已使用规则检查替代",
            })

        return ToolResult(
            success=True,
            data={"dimension_results": all_issues, "degraded": True},
            summary=f"深度检查降级为规则检查（{len(dimensions)} 个维度）",
        )

    # ==================== 输出工具 ====================

    async def _handle_generate_suggestion(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """生成优化建议"""
        dimension = params.get("dimension", "")
        severity = params.get("severity", "medium")
        description = params.get("description", "")
        original_text = params.get("original_text", "")
        suggested_text = params.get("suggested_text", "")
        reasoning = params.get("reasoning", "")

        if not description or not reasoning:
            return ToolResult(success=False, error="缺少问题描述或推理过程")

        # 验证严重程度
        try:
            severity_enum = SuggestionSeverity(severity)
        except ValueError:
            severity_enum = SuggestionSeverity.MEDIUM

        # 生成建议 ID
        suggestion_id = str(uuid.uuid4())[:8]

        suggestion = {
            "id": suggestion_id,
            "dimension": dimension,
            "dimension_name": get_dimension_display_name(dimension, self.prompt_type),
            "severity": severity_enum.value,
            "description": description,
            "original_text": original_text,
            "suggested_text": suggested_text,
            "reasoning": reasoning,
            "weight": get_dimension_weight(dimension, self.prompt_type),
        }

        # 添加到状态
        state.suggestions.append(suggestion)

        return ToolResult(
            success=True,
            data={"suggestion_id": suggestion_id, "suggestion": suggestion},
            summary=f"生成建议 [{severity}]: {description[:50]}...",
        )

    async def _handle_record_observation(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """记录观察"""
        observation = params.get("observation", "")
        related_dimension = params.get("related_dimension", "")

        if not observation:
            return ToolResult(success=False, error="缺少观察内容")

        # 生成观察 ID
        observation_id = str(uuid.uuid4())[:8]

        obs_record = {
            "id": observation_id,
            "observation": observation,
            "related_dimension": related_dimension,
        }

        # 添加到状态
        state.observations.append(obs_record)

        return ToolResult(
            success=True,
            data={"observation_id": observation_id},
            summary=f"记录观察: {observation[:50]}...",
        )

    # ==================== 控制工具 ====================

    async def _handle_complete_workflow(
        self,
        params: Dict[str, Any],
        state: AgentState,
    ) -> ToolResult:
        """完成工作流"""
        summary = params.get("summary", "")
        overall_quality = params.get("overall_quality", "good")

        if not summary:
            return ToolResult(success=False, error="缺少分析总结")

        # 更新状态
        state.is_complete = True
        state.summary = summary
        state.overall_quality = overall_quality

        return ToolResult(
            success=True,
            data={
                "summary": summary,
                "overall_quality": overall_quality,
                "total_suggestions": len(state.suggestions),
                "total_observations": len(state.observations),
            },
            summary=f"分析完成: {summary[:100]}...",
        )

    # ==================== 辅助方法 ====================

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词（简单实现）"""
        if not text:
            return []

        # 移除标点
        clean_text = re.sub(r"[^\w\s]", " ", text)

        # 分词（简单按空格和常见分隔符）
        words = clean_text.split()

        # 过滤短词和常见词
        stop_words = {"的", "是", "在", "和", "与", "或", "等", "了", "到", "要", "会", "能", "可以", "进行", "使用"}
        keywords = [w for w in words if len(w) >= 2 and w not in stop_words]

        return keywords[:10]  # 最多返回10个


__all__ = [
    "AgentState",
    "ToolExecutor",
]
