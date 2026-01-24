"""
目录规划Agent工具执行器

负责执行Agent选择的工具，管理规划状态。
包含文件信息质量验证，确保生成的目录结构可用于后续代码生成。
支持优化历程记录，用于LLM评估和完成决策。
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .tools import ToolCall, ToolResult, get_tool
from ...agent_tool_executor_base import BaseToolExecutor
from .evaluator import PlanningEvaluator

logger = logging.getLogger(__name__)


# ==================== 质量阈值常量 ====================

# 文件描述最小长度（用于后续生成代码Prompt，需要足够详细）
MIN_DESCRIPTION_LENGTH = 30
# 质量达标率阈值
MIN_QUALITY_RATE = 0.8


# ==================== 优化历程记录 ====================

@dataclass
class OptimizationRecord:
    """单次优化操作记录"""
    step: int                           # 步骤编号
    action: str                         # 操作类型: create_file, update_file, remove_item, create_directory
    target: str                         # 目标路径
    reason: str                         # 操作原因（Agent的reasoning）
    changes: Dict[str, Any] = field(default_factory=dict)  # 具体变更内容
    result: str = ""                    # 操作结果摘要
    timestamp: str = ""                 # 时间戳

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")


# 文件存在理由最小长度
MIN_PURPOSE_LENGTH = 15
# 依赖原因最小长度（如果有依赖的话）
MIN_DEPENDENCY_REASON_LENGTH = 10


@dataclass
class PlannedDirectory:
    """已规划的目录"""
    path: str
    description: str
    purpose: str = ""
    module_numbers: List[int] = field(default_factory=list)


@dataclass
class PlannedFile:
    """已规划的文件"""
    path: str
    filename: str
    description: str
    purpose: str
    module_number: int
    file_type: str = "source"
    language: str = "python"
    priority: str = "medium"
    dependencies: List[int] = field(default_factory=list)
    dependency_reasons: str = ""
    implementation_notes: str = ""

    def get_quality_issues(self) -> List[str]:
        """检查文件信息质量，返回问题列表"""
        issues = []

        if not self.description or len(self.description.strip()) < MIN_DESCRIPTION_LENGTH:
            issues.append(f"description过短(当前{len(self.description.strip())}字符，需要至少{MIN_DESCRIPTION_LENGTH}字符)，需要详细说明文件功能")

        if not self.purpose or len(self.purpose.strip()) < MIN_PURPOSE_LENGTH:
            issues.append(f"purpose过短(当前{len(self.purpose.strip())}字符，需要至少{MIN_PURPOSE_LENGTH}字符)，需要说明为什么需要这个文件")

        if self.module_number <= 0:
            issues.append("module_number无效，必须关联到一个模块")

        if self.dependencies and (not self.dependency_reasons or len(self.dependency_reasons.strip()) < MIN_DEPENDENCY_REASON_LENGTH):
            issues.append(f"有{len(self.dependencies)}个依赖但dependency_reasons为空或过短，需要解释为什么需要这些依赖")

        return issues

    def is_quality_ok(self) -> bool:
        """检查文件信息质量是否达标"""
        return len(self.get_quality_issues()) == 0


@dataclass
class AgentState:
    """
    Agent状态

    维护规划过程中的所有状态信息。
    """
    # 项目信息
    project_id: str
    project_data: Dict[str, Any] = field(default_factory=dict)
    blueprint_data: Dict[str, Any] = field(default_factory=dict)
    systems: List[Dict[str, Any]] = field(default_factory=list)
    modules: List[Dict[str, Any]] = field(default_factory=list)

    # 已规划的结构
    directories: List[PlannedDirectory] = field(default_factory=list)
    files: List[PlannedFile] = field(default_factory=list)

    # 索引（加速查询）
    _dir_by_path: Dict[str, PlannedDirectory] = field(default_factory=dict)
    _file_by_path: Dict[str, PlannedFile] = field(default_factory=dict)
    _files_by_module: Dict[int, List[PlannedFile]] = field(default_factory=lambda: defaultdict(list))

    # 模块覆盖追踪
    covered_modules: Set[int] = field(default_factory=set)

    # 优化历程记录
    optimization_history: List[OptimizationRecord] = field(default_factory=list)
    _step_counter: int = 0

    # 完成标志
    is_complete: bool = False
    finish_summary: str = ""

    def add_directory(self, directory: PlannedDirectory) -> None:
        """添加目录"""
        if directory.path in self._dir_by_path:
            # 更新已存在的目录
            existing = self._dir_by_path[directory.path]
            existing.description = directory.description
            existing.purpose = directory.purpose
            for mn in directory.module_numbers:
                if mn not in existing.module_numbers:
                    existing.module_numbers.append(mn)
        else:
            self.directories.append(directory)
            self._dir_by_path[directory.path] = directory

    def add_file(self, file: PlannedFile) -> None:
        """添加文件"""
        if file.path in self._file_by_path:
            raise ValueError(f"文件已存在: {file.path}")

        self.files.append(file)
        self._file_by_path[file.path] = file

        if file.module_number:
            self._files_by_module[file.module_number].append(file)
            self.covered_modules.add(file.module_number)

    def update_file(self, path: str, **kwargs) -> bool:
        """更新文件信息"""
        file = self._file_by_path.get(path)
        if not file:
            return False

        for key, value in kwargs.items():
            if hasattr(file, key) and value is not None:
                setattr(file, key, value)

        return True

    def remove_item(self, path: str) -> bool:
        """移除目录或文件"""
        # 尝试移除文件
        if path in self._file_by_path:
            file = self._file_by_path.pop(path)
            self.files.remove(file)
            if file.module_number in self._files_by_module:
                self._files_by_module[file.module_number].remove(file)
            # 重新计算覆盖的模块
            self._recalculate_covered_modules()
            return True

        # 尝试移除目录
        if path in self._dir_by_path:
            directory = self._dir_by_path.pop(path)
            self.directories.remove(directory)
            # 同时移除该目录下的所有文件
            files_to_remove = [f for f in self.files if f.path.startswith(path + "/")]
            for f in files_to_remove:
                self._file_by_path.pop(f.path, None)
                self.files.remove(f)
                if f.module_number in self._files_by_module:
                    if f in self._files_by_module[f.module_number]:
                        self._files_by_module[f.module_number].remove(f)
            self._recalculate_covered_modules()
            return True

        return False

    def _recalculate_covered_modules(self) -> None:
        """重新计算已覆盖的模块"""
        self.covered_modules = set()
        for f in self.files:
            if f.module_number:
                self.covered_modules.add(f.module_number)

    def get_uncovered_modules(self) -> List[Dict[str, Any]]:
        """获取未覆盖的模块"""
        all_module_numbers = {m.get("module_number") for m in self.modules}
        uncovered_numbers = all_module_numbers - self.covered_modules
        return [m for m in self.modules if m.get("module_number") in uncovered_numbers]

    def get_module_by_number(self, module_number: int) -> Optional[Dict[str, Any]]:
        """通过编号获取模块"""
        for m in self.modules:
            if m.get("module_number") == module_number:
                return m
        return None

    def get_system_by_number(self, system_number: int) -> Optional[Dict[str, Any]]:
        """通过编号获取系统"""
        for s in self.systems:
            if s.get("system_number") == system_number:
                return s
        return None

    def get_modules_by_system(self, system_number: int) -> List[Dict[str, Any]]:
        """获取系统下的所有模块"""
        return [m for m in self.modules if m.get("system_number") == system_number]

    def get_modules_by_type(self, module_type: str) -> List[Dict[str, Any]]:
        """按类型获取模块"""
        return [m for m in self.modules if m.get("module_type", "").lower() == module_type.lower()]

    def record_optimization(self, action: str, target: str, reason: str,
                           changes: Dict[str, Any] = None, result: str = "") -> None:
        """记录一次优化操作"""
        self._step_counter += 1
        record = OptimizationRecord(
            step=self._step_counter,
            action=action,
            target=target,
            reason=reason,
            changes=changes or {},
            result=result,
        )
        self.optimization_history.append(record)

    def get_optimization_summary(self) -> Dict[str, Any]:
        """获取优化历程摘要"""
        action_counts = defaultdict(int)
        for record in self.optimization_history:
            action_counts[record.action] += 1

        return {
            "total_steps": len(self.optimization_history),
            "action_counts": dict(action_counts),
            "recent_actions": [
                {
                    "step": r.step,
                    "action": r.action,
                    "target": r.target,
                    "reason": r.reason[:100] if r.reason else "",
                }
                for r in self.optimization_history[-5:]  # 最近5条
            ],
        }

    def get_dependency_graph(self) -> Dict[str, Any]:
        """构建依赖关系图"""
        edges = defaultdict(list)
        in_degrees = defaultdict(int)

        for m in self.modules:
            deps = m.get("dependencies", [])
            module_name = m.get("name", "")
            for dep in deps:
                edges[module_name].append(dep)
                in_degrees[dep] += 1

        # 检测循环依赖（简化版）
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node, path):
            if len(cycles) >= 3:
                return
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in edges.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    try:
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:]
                        if len(cycle) > 1:
                            cycles.append(cycle.copy())
                    except ValueError:
                        pass

            path.pop()
            rec_stack.remove(node)

        for node in edges:
            if node not in visited:
                dfs(node, [])

        # 识别高依赖模块
        high_dependency_modules = [
            name for name, count in in_degrees.items() if count >= 3
        ]

        return {
            "edges": dict(edges),
            "in_degrees": dict(in_degrees),
            "cycles": cycles[:3],
            "high_dependency_modules": high_dependency_modules,
        }

    def get_quality_report(self) -> Dict[str, Any]:
        """获取整体质量报告"""
        total_files = len(self.files)
        files_with_issues = []
        quality_ok_count = 0

        for f in self.files:
            issues = f.get_quality_issues()
            if issues:
                files_with_issues.append({
                    "path": f.path,
                    "issues": issues,
                })
            else:
                quality_ok_count += 1

        quality_rate = quality_ok_count / total_files if total_files > 0 else 0

        return {
            "total_files": total_files,
            "quality_ok_count": quality_ok_count,
            "quality_rate": round(quality_rate, 2),
            "files_with_issues": files_with_issues[:10],  # 最多返回10个问题文件
            "total_issues_count": len(files_with_issues),
        }


class ToolExecutor(BaseToolExecutor):
    """
    工具执行器

    执行Agent选择的工具，返回执行结果。
    支持LLM评估器进行语义级质量评估。
    """

    def __init__(self, state: AgentState, llm_caller: Optional[Callable] = None):
        """
        初始化工具执行器

        Args:
            state: Agent状态
            llm_caller: LLM调用函数，用于评估
        """
        self.state = state
        self.evaluator = PlanningEvaluator(llm_caller)
        super().__init__()

    def _build_handlers(self) -> Dict[str, Callable]:
        """构建工具处理器映射"""
        return {
            # 信息获取
            "get_project_overview": self._handle_get_project_overview,
            "get_blueprint_details": self._handle_get_blueprint_details,
            "get_all_systems": self._handle_get_all_systems,
            "get_system_modules": self._handle_get_system_modules,
            "get_module_detail": self._handle_get_module_detail,
            "get_modules_by_type": self._handle_get_modules_by_type,
            "get_dependency_graph": self._handle_get_dependency_graph,
            # 分析
            "analyze_module_placement": self._handle_analyze_module_placement,
            "analyze_shared_candidates": self._handle_analyze_shared_candidates,
            "evaluate_structure": self._handle_evaluate_structure,
            "check_file_quality": self._handle_check_file_quality,
            "request_llm_evaluation": self._handle_request_llm_evaluation,
            # 操作
            "create_directory": self._handle_create_directory,
            "create_file": self._handle_create_file,
            "update_file": self._handle_update_file,
            "remove_item": self._handle_remove_item,
            # 控制
            "get_current_structure": self._handle_get_current_structure,
            "get_uncovered_modules": self._handle_get_uncovered_modules,
            "get_optimization_history": self._handle_get_optimization_history,
            "finish_planning": self._handle_finish_planning,
        }

    def _get_tool_name(self, tool_call: ToolCall) -> str:
        """获取工具名称"""
        return tool_call.tool

    def _get_tool_params(self, tool_call: ToolCall) -> Dict[str, Any]:
        """获取工具参数"""
        return tool_call.parameters

    def _build_result(
        self,
        tool_name: str,
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

    async def execute_batch(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """
        批量执行工具调用

        策略：
        - 信息获取工具(INFO)：可并行执行
        - 操作工具(ACTION)：串行执行，保证顺序
        - 分析工具(ANALYSIS)：可并行执行
        - 控制工具(CONTROL)：串行执行

        Args:
            tool_calls: 工具调用列表

        Returns:
            List[ToolResult]: 执行结果列表
        """
        import asyncio
        from .tools import ToolCategory, get_tool

        if not tool_calls:
            return []

        # 分类工具调用
        parallel_calls = []  # 可并行的
        serial_calls = []    # 需串行的

        for tc in tool_calls:
            tool_def = get_tool(tc.tool)
            if tool_def and tool_def.category in (ToolCategory.INFO, ToolCategory.ANALYSIS):
                parallel_calls.append(tc)
            else:
                serial_calls.append(tc)

        results = []

        # 先并行执行信息获取和分析工具
        if parallel_calls:
            logger.debug("[批量执行] 并行执行 %d 个工具", len(parallel_calls))
            tasks = [self.execute(tc) for tc in parallel_calls]
            parallel_results = await asyncio.gather(*tasks)
            results.extend(parallel_results)

        # 再串行执行操作和控制工具
        for tc in serial_calls:
            logger.debug("[批量执行] 串行执行: %s", tc.tool)
            result = await self.execute(tc)
            results.append(result)

        return results

    # ==================== 信息获取工具处理器 ====================

    def _handle_get_project_overview(self, params: Dict) -> Dict:
        """获取项目概览"""
        tech_stack = self.state.blueprint_data.get("tech_stack", {})
        return {
            "project_id": self.state.project_id,
            "title": self.state.project_data.get("title", ""),
            "initial_prompt": self.state.project_data.get("initial_prompt", "")[:500],
            "one_sentence_summary": self.state.blueprint_data.get("one_sentence_summary", ""),
            "architecture_synopsis": self.state.blueprint_data.get("architecture_synopsis", ""),
            "tech_style": self.state.blueprint_data.get("tech_style", ""),
            "primary_language": tech_stack.get("primary_language", "python"),
            "frameworks": tech_stack.get("frameworks", []),
            "total_systems": len(self.state.systems),
            "total_modules": len(self.state.modules),
        }

    def _handle_get_blueprint_details(self, params: Dict) -> Dict:
        """获取蓝图详情"""
        return {
            "core_requirements": self.state.blueprint_data.get("core_requirements", []),
            "technical_challenges": self.state.blueprint_data.get("technical_challenges", []),
            "non_functional_requirements": self.state.blueprint_data.get("non_functional_requirements", {}),
            "risks": self.state.blueprint_data.get("risks", []),
            "milestones": self.state.blueprint_data.get("milestones", []),
            "dependencies": self.state.blueprint_data.get("dependencies", []),
            "system_suggestions": self.state.blueprint_data.get("system_suggestions", []),
        }

    def _handle_get_all_systems(self, params: Dict) -> List[Dict]:
        """获取所有系统"""
        return [
            {
                "system_number": s.get("system_number"),
                "name": s.get("name"),
                "description": s.get("description"),
                "responsibilities": s.get("responsibilities", []),
                "module_count": len(self.state.get_modules_by_system(s.get("system_number"))),
            }
            for s in self.state.systems
        ]

    def _handle_get_system_modules(self, params: Dict) -> List[Dict]:
        """获取系统下的模块"""
        system_number = params.get("system_number")
        if system_number is None:
            raise ValueError("缺少system_number参数")

        modules = self.state.get_modules_by_system(system_number)
        return [
            {
                "module_number": m.get("module_number"),
                "name": m.get("name"),
                "module_type": m.get("module_type"),
                "description": m.get("description", "")[:200],
                "dependencies": m.get("dependencies", []),
            }
            for m in modules
        ]

    def _handle_get_module_detail(self, params: Dict) -> Dict:
        """获取模块详情"""
        module_number = params.get("module_number")
        if module_number is None:
            raise ValueError("缺少module_number参数")

        module = self.state.get_module_by_number(module_number)
        if not module:
            raise ValueError(f"模块不存在: {module_number}")

        # 获取所属系统信息
        system = self.state.get_system_by_number(module.get("system_number"))

        return {
            "module_number": module.get("module_number"),
            "system_number": module.get("system_number"),
            "system_name": system.get("name") if system else "",
            "name": module.get("name"),
            "module_type": module.get("module_type"),
            "description": module.get("description"),
            "interface": module.get("interface"),
            "dependencies": module.get("dependencies", []),
        }

    def _handle_get_modules_by_type(self, params: Dict) -> List[Dict]:
        """按类型获取模块"""
        module_type = params.get("module_type")
        if not module_type:
            raise ValueError("缺少module_type参数")

        modules = self.state.get_modules_by_type(module_type)
        return [
            {
                "module_number": m.get("module_number"),
                "name": m.get("name"),
                "system_number": m.get("system_number"),
                "description": m.get("description", "")[:200],
            }
            for m in modules
        ]

    def _handle_get_dependency_graph(self, params: Dict) -> Dict:
        """获取依赖关系图"""
        return self.state.get_dependency_graph()

    # ==================== 分析工具处理器 ====================

    def _handle_analyze_module_placement(self, params: Dict) -> Dict:
        """分析模块放置"""
        module_number = params.get("module_number")
        if module_number is None:
            raise ValueError("缺少module_number参数")

        module = self.state.get_module_by_number(module_number)
        if not module:
            raise ValueError(f"模块不存在: {module_number}")

        candidate_paths = params.get("candidate_paths", [])

        # 分析模块特征
        module_type = module.get("module_type", "").lower()
        dependencies = module.get("dependencies", [])
        system = self.state.get_system_by_number(module.get("system_number"))

        # 返回分析信息供Agent决策
        return {
            "module_number": module_number,
            "module_name": module.get("name"),
            "module_type": module_type,
            "system_name": system.get("name") if system else "",
            "dependencies": dependencies,
            "dependency_count": len(dependencies),
            "candidate_paths": candidate_paths,
            "analysis_hints": [
                f"模块类型为{module_type}，通常放在对应的层级目录",
                f"该模块依赖{len(dependencies)}个其他模块",
                f"所属系统: {system.get('name') if system else '未知'}",
            ]
        }

    def _handle_analyze_shared_candidates(self, params: Dict) -> Dict:
        """分析共享模块候选"""
        dep_graph = self.state.get_dependency_graph()
        high_deps = dep_graph.get("high_dependency_modules", [])

        # 找出工具类模块
        utility_modules = []
        for m in self.state.modules:
            module_type = m.get("module_type", "").lower()
            if module_type in ["utility", "util", "helper", "common", "shared"]:
                utility_modules.append({
                    "module_number": m.get("module_number"),
                    "name": m.get("name"),
                    "reason": "工具类模块",
                })

        # 高依赖模块
        high_dep_modules = []
        for m in self.state.modules:
            if m.get("name") in high_deps:
                high_dep_modules.append({
                    "module_number": m.get("module_number"),
                    "name": m.get("name"),
                    "reason": "被多个模块依赖",
                })

        return {
            "utility_modules": utility_modules,
            "high_dependency_modules": high_dep_modules,
            "total_candidates": len(utility_modules) + len(high_dep_modules),
        }

    def _handle_evaluate_structure(self, params: Dict) -> Dict:
        """评估当前结构（包含质量评估）"""
        total_modules = len(self.state.modules)
        covered = len(self.state.covered_modules)
        coverage_rate = covered / total_modules if total_modules > 0 else 0

        # 统计
        total_dirs = len(self.state.directories)
        total_files = len(self.state.files)

        # 检查深度
        max_depth = 0
        for d in self.state.directories:
            depth = d.path.count("/") + 1
            max_depth = max(max_depth, depth)

        # 文件分布
        files_per_dir = defaultdict(int)
        for f in self.state.files:
            dir_path = "/".join(f.path.split("/")[:-1])
            files_per_dir[dir_path] += 1

        large_dirs = [path for path, count in files_per_dir.items() if count > 10]

        # 质量评估
        quality_report = self.state.get_quality_report()

        # 综合评估是否可以完成
        can_finish = (
            coverage_rate >= 1.0 and
            quality_report["quality_rate"] >= MIN_QUALITY_RATE  # 至少80%的文件质量达标
        )

        return {
            "module_coverage": {
                "total": total_modules,
                "covered": covered,
                "rate": round(coverage_rate, 2),
            },
            "structure_stats": {
                "total_directories": total_dirs,
                "total_files": total_files,
                "max_depth": max_depth,
            },
            "quality_assessment": {
                "quality_rate": quality_report["quality_rate"],
                "quality_ok_count": quality_report["quality_ok_count"],
                "files_with_issues_count": quality_report["total_issues_count"],
                "sample_issues": quality_report["files_with_issues"][:3],  # 样例问题
            },
            "issues": {
                "large_directories": large_dirs,
                "uncovered_count": total_modules - covered,
            },
            "can_finish": can_finish,
            "blocking_reasons": self._get_blocking_reasons(coverage_rate, quality_report),
        }

    def _get_blocking_reasons(self, coverage_rate: float, quality_report: Dict) -> List[str]:
        """获取阻止完成的原因"""
        reasons = []
        if coverage_rate < 1.0:
            reasons.append(f"模块覆盖率不足: {coverage_rate:.0%}，还有{len(self.state.get_uncovered_modules())}个模块未覆盖")
        if quality_report["quality_rate"] < MIN_QUALITY_RATE:
            reasons.append(f"文件信息质量不足: {quality_report['quality_rate']:.0%}，有{quality_report['total_issues_count']}个文件需要补充信息")
        return reasons

    def _handle_check_file_quality(self, params: Dict) -> Dict:
        """检查单个文件的信息质量"""
        path = params.get("path")
        if not path:
            raise ValueError("缺少path参数")

        file = self.state._file_by_path.get(path)
        if not file:
            raise ValueError(f"文件不存在: {path}")

        issues = file.get_quality_issues()

        return {
            "path": path,
            "is_quality_ok": len(issues) == 0,
            "issues": issues,
            "current_values": {
                "description_length": len(file.description.strip()),
                "purpose_length": len(file.purpose.strip()),
                "module_number": file.module_number,
                "dependencies_count": len(file.dependencies),
                "has_dependency_reasons": bool(file.dependency_reasons.strip()),
                "has_implementation_notes": bool(file.implementation_notes.strip()),
            },
            "requirements": {
                "min_description_length": MIN_DESCRIPTION_LENGTH,
                "min_purpose_length": MIN_PURPOSE_LENGTH,
                "min_dependency_reason_length": MIN_DEPENDENCY_REASON_LENGTH,
            },
        }

    async def _handle_request_llm_evaluation(self, params: Dict) -> Dict:
        """请求LLM对指定文件进行语义级评估（直接调用evaluator）"""
        path = params.get("path")
        if not path:
            raise ValueError("缺少path参数")

        file = self.state._file_by_path.get(path)
        if not file:
            raise ValueError(f"文件不存在: {path}")

        # 构建文件信息
        module = self.state.get_module_by_number(file.module_number)
        file_info = {
            "path": file.path,
            "description": file.description,
            "purpose": file.purpose,
            "module_name": module.get("name", "") if module else "",
            "dependencies": file.dependencies,
            "dependency_reasons": file.dependency_reasons,
            "implementation_notes": file.implementation_notes,
        }

        # 构建项目上下文
        project_context = {
            "title": self.state.project_data.get("title", ""),
            "summary": self.state.blueprint_data.get("one_sentence_summary", ""),
            "tech_stack": self.state.blueprint_data.get("tech_stack", {}).get("primary_language", ""),
        }

        # 直接调用evaluator进行评估
        evaluation = await self.evaluator.evaluate_file(file_info, project_context)

        return {
            "path": path,
            "is_acceptable": evaluation.is_acceptable,
            "overall_score": evaluation.overall_score,
            "scores": evaluation.scores,
            "issues": evaluation.issues,
            "suggestions": evaluation.suggestions,
        }

    # ==================== 操作工具处理器 ====================

    def _handle_create_directory(self, params: Dict) -> Dict:
        """创建目录"""
        path = params.get("path")
        if not path:
            raise ValueError("缺少path参数")

        description = params.get("description", "")
        purpose = params.get("purpose", "")

        directory = PlannedDirectory(
            path=path,
            description=description,
            purpose=purpose,
        )

        self.state.add_directory(directory)

        return {
            "created": True,
            "path": path,
            "description": description,
        }

    def _handle_create_file(self, params: Dict) -> Dict:
        """创建文件（带质量验证）"""
        path = params.get("path")
        if not path:
            raise ValueError("缺少path参数")

        # 提取文件名
        filename = path.split("/")[-1]

        # 确保父目录存在
        dir_path = "/".join(path.split("/")[:-1])
        if dir_path and dir_path not in self.state._dir_by_path:
            # 自动创建父目录
            self.state.add_directory(PlannedDirectory(
                path=dir_path,
                description="自动创建的父目录",
            ))

        # 检测语言
        language = "python"
        if filename.endswith(".ts") or filename.endswith(".tsx"):
            language = "typescript"
        elif filename.endswith(".js") or filename.endswith(".jsx"):
            language = "javascript"
        elif filename.endswith(".go"):
            language = "go"
        elif filename.endswith(".rs"):
            language = "rust"
        elif filename.endswith(".java"):
            language = "java"

        # 获取参数
        description = params.get("description", "")
        purpose = params.get("purpose", "")
        module_number = params.get("module_number", 0)
        dependencies = params.get("dependencies", [])
        dependency_reasons = params.get("dependency_reasons", "")
        implementation_notes = params.get("implementation_notes", "")

        file = PlannedFile(
            path=path,
            filename=filename,
            description=description,
            purpose=purpose,
            module_number=module_number,
            file_type=params.get("file_type", "source"),
            language=language,
            priority=params.get("priority", "medium"),
            dependencies=dependencies,
            dependency_reasons=dependency_reasons,
            implementation_notes=implementation_notes,
        )

        self.state.add_file(file)

        # 检查质量并返回警告
        issues = file.get_quality_issues()

        # 记录优化历程
        result_msg = "创建成功" if not issues else f"创建成功，有{len(issues)}个质量问题"
        self.state.record_optimization(
            action="create_file",
            target=path,
            reason=params.get("_reasoning", ""),  # Agent的reasoning
            changes={
                "module_number": module_number,
                "description_length": len(description),
                "has_dependencies": len(dependencies) > 0,
            },
            result=result_msg,
        )

        result = {
            "created": True,
            "path": path,
            "module_number": file.module_number,
            "quality_ok": len(issues) == 0,
        }

        if issues:
            result["quality_warnings"] = issues
            result["message"] = f"文件已创建，但有{len(issues)}个质量问题需要通过update_file修复"

        return result

    def _handle_update_file(self, params: Dict) -> Dict:
        """更新文件"""
        path = params.get("path")
        if not path:
            raise ValueError("缺少path参数")

        update_fields = {k: v for k, v in params.items() if k != "path" and k != "_reasoning" and v is not None}
        success = self.state.update_file(path, **update_fields)

        if not success:
            raise ValueError(f"文件不存在: {path}")

        # 重新检查质量
        file = self.state._file_by_path.get(path)
        issues = file.get_quality_issues() if file else []

        # 记录优化历程
        result_msg = "更新成功，质量达标" if not issues else f"更新成功，还有{len(issues)}个问题"
        self.state.record_optimization(
            action="update_file",
            target=path,
            reason=params.get("_reasoning", ""),
            changes={"updated_fields": list(update_fields.keys())},
            result=result_msg,
        )

        return {
            "updated": True,
            "path": path,
            "updated_fields": list(update_fields.keys()),
            "quality_ok": len(issues) == 0,
            "remaining_issues": issues if issues else None,
        }

    def _handle_remove_item(self, params: Dict) -> Dict:
        """移除项目"""
        path = params.get("path")
        reason = params.get("reason", "")

        if not path:
            raise ValueError("缺少path参数")

        success = self.state.remove_item(path)

        if not success:
            raise ValueError(f"路径不存在: {path}")

        # 记录优化历程
        self.state.record_optimization(
            action="remove_item",
            target=path,
            reason=reason or params.get("_reasoning", ""),
            changes={},
            result="删除成功",
        )

        return {
            "removed": True,
            "path": path,
            "reason": reason,
        }

    # ==================== 控制工具处理器 ====================

    def _handle_get_current_structure(self, params: Dict) -> Dict:
        """获取当前结构"""
        return {
            "directories": [
                {"path": d.path, "description": d.description}
                for d in self.state.directories
            ],
            "files": [
                {
                    "path": f.path,
                    "module_number": f.module_number,
                    "description": f.description[:100] if f.description else "",
                    "quality_ok": f.is_quality_ok(),
                }
                for f in self.state.files
            ],
            "total_directories": len(self.state.directories),
            "total_files": len(self.state.files),
            "covered_modules": len(self.state.covered_modules),
        }

    def _handle_get_uncovered_modules(self, params: Dict) -> List[Dict]:
        """获取未覆盖的模块"""
        uncovered = self.state.get_uncovered_modules()
        return [
            {
                "module_number": m.get("module_number"),
                "name": m.get("name"),
                "module_type": m.get("module_type"),
                "system_number": m.get("system_number"),
            }
            for m in uncovered
        ]

    def _handle_get_optimization_history(self, params: Dict) -> Dict:
        """获取优化历程"""
        return self.state.get_optimization_summary()

    async def _handle_finish_planning(self, params: Dict) -> Dict:
        """完成规划（带LLM评估和优化历程）"""
        summary = params.get("summary", "")

        # 先进行规则评估
        eval_result = self._handle_evaluate_structure({})

        # 获取优化历程
        optimization_summary = self.state.get_optimization_summary()

        # 规则检查不通过，直接返回
        if not eval_result["can_finish"]:
            return {
                "finished": False,
                "blocked": True,
                "blocking_reasons": eval_result["blocking_reasons"],
                "evaluation": eval_result,
                "optimization_history": optimization_summary,
                "message": "规划无法完成，请先解决上述问题后再调用finish_planning",
            }

        # 规则检查通过后，使用LLM进行最终决策
        state_summary = {
            "total_modules": len(self.state.modules),
            "covered_modules": len(self.state.covered_modules),
            "coverage_rate": eval_result["module_coverage"]["rate"],
            "total_files": len(self.state.files),
            "quality_ok_count": eval_result["quality_assessment"]["quality_ok_count"],
            "quality_rate": eval_result["quality_assessment"]["quality_rate"],
        }

        # 调用LLM评估是否可以完成
        llm_decision = await self.evaluator.decide_finish(
            state_summary,
            [{"action": r.action, "target": r.target, "reason": r.reason}
             for r in self.state.optimization_history]
        )

        # LLM认为不能完成
        if not llm_decision.get("can_finish", False):
            return {
                "finished": False,
                "blocked": True,
                "blocking_reasons": llm_decision.get("remaining_issues", []),
                "llm_reasoning": llm_decision.get("reasoning", ""),
                "evaluation": eval_result,
                "optimization_history": optimization_summary,
                "message": "LLM评估认为规划尚未完成",
            }

        # 标记完成
        self.state.is_complete = True
        self.state.finish_summary = summary

        return {
            "finished": True,
            "summary": summary,
            "llm_reasoning": llm_decision.get("reasoning", ""),
            "final_evaluation": eval_result,
            "optimization_history": optimization_summary,
            "total_optimization_steps": optimization_summary["total_steps"],
        }
