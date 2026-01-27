"""
项目画像构建器

阶段一：一次性收集所有项目信息，构建结构化的项目画像。
不消耗优化轮次，为后续架构决策提供完整上下文。
"""

import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from .schemas import (
    ArchitecturePattern,
    DependencyGraph,
    ModuleSummary,
    ProjectProfile,
    SystemSummary,
)
from .patterns import recommend_pattern
from ..graph_utils import detect_cycles

logger = logging.getLogger(__name__)


class ProjectProfiler:
    """
    项目画像构建器

    一次性收集所有项目信息，构建结构化的项目画像。
    整合了原有ProjectInfoTools的逻辑，但不作为工具暴露，而是直接构建。
    """

    def __init__(
        self,
        project_id: str,
        project_data: Dict[str, Any],
        blueprint_data: Dict[str, Any],
        systems: List[Dict[str, Any]],
        modules: List[Dict[str, Any]],
        module_dependencies: Optional[List[Dict[str, str]]] = None,
    ):
        """
        初始化项目画像构建器

        Args:
            project_id: 项目ID
            project_data: 项目基本信息
            blueprint_data: 蓝图数据
            systems: 系统列表
            modules: 模块列表
            module_dependencies: 模块依赖关系（可选，可从modules中提取）
        """
        self.project_id = project_id
        self.project_data = project_data or {}
        self.blueprint_data = blueprint_data or {}
        self.systems = systems or []
        self.modules = modules or []

        # 如果没有提供依赖关系，从模块中提取
        if module_dependencies:
            self.module_dependencies = module_dependencies
        else:
            self.module_dependencies = self._extract_dependencies_from_modules()

        # 构建索引
        self._system_by_number = {s.get("system_number"): s for s in self.systems}
        self._module_by_number = {m.get("module_number"): m for m in self.modules}
        self._module_by_name = {m.get("name"): m for m in self.modules}

    def _extract_dependencies_from_modules(self) -> List[Dict[str, str]]:
        """从模块定义中提取依赖关系"""
        dependencies = []
        for m in self.modules:
            deps = m.get("dependencies", [])
            if deps:
                for dep in deps:
                    dependencies.append({
                        "from_module": m.get("name", ""),
                        "to_module": dep,
                    })
        return dependencies

    def build_profile(self) -> ProjectProfile:
        """
        构建项目画像

        Returns:
            ProjectProfile: 结构化的项目画像
        """
        logger.info("开始构建项目画像: %s", self.project_id)

        # 1. 收集基本信息
        project_name = self.project_data.get("title", "")
        project_type = self._extract_project_type()
        tech_style = self._extract_tech_style()
        one_sentence_summary = self.blueprint_data.get("one_sentence_summary", "")
        architecture_synopsis = self.blueprint_data.get("architecture_synopsis", "")

        # 2. 收集技术栈信息
        primary_language, frameworks, components, constraints = self._collect_tech_stack()

        # 3. 构建系统摘要
        systems_summary = self._build_systems_summary()

        # 4. 按类型组织模块
        modules_by_type = self._organize_modules_by_type()

        # 5. 构建依赖图
        dependency_graph = self._build_dependency_graph()

        # 6. 计算复杂度
        complexity_score, complexity_factors = self._calculate_complexity()

        # 7. 推荐架构模式
        recommended_pattern, recommendation_reason = recommend_pattern(
            total_modules=len(self.modules),
            total_systems=len(self.systems),
            project_type=project_type,
            tech_style=tech_style,
        )

        profile = ProjectProfile(
            project_id=self.project_id,
            project_name=project_name,
            project_type=project_type,
            tech_style=tech_style,
            one_sentence_summary=one_sentence_summary,
            architecture_synopsis=architecture_synopsis,
            primary_language=primary_language,
            frameworks=frameworks,
            tech_components=components,
            tech_constraints=constraints,
            systems=systems_summary,
            modules_by_type=modules_by_type,
            total_modules=len(self.modules),
            total_systems=len(self.systems),
            dependency_graph=dependency_graph,
            complexity_score=complexity_score,
            complexity_factors=complexity_factors,
            recommended_pattern=recommended_pattern,
            recommendation_reason=recommendation_reason,
        )

        logger.info(
            "项目画像构建完成: 模块=%d, 系统=%d, 复杂度=%.2f, 推荐架构=%s",
            len(self.modules),
            len(self.systems),
            complexity_score,
            recommended_pattern.value,
        )

        return profile

    def _extract_project_type(self) -> str:
        """提取项目类型"""
        # 优先从蓝图获取
        project_type = self.blueprint_data.get("project_type_desc", "")
        if project_type:
            return project_type

        # 从项目数据获取
        return self.project_data.get("project_type", "")

    def _extract_tech_style(self) -> str:
        """提取技术风格"""
        return self.blueprint_data.get("tech_style", "")

    def _collect_tech_stack(self) -> Tuple[str, List[str], List[str], str]:
        """
        收集技术栈信息

        Returns:
            (主要语言, 框架列表, 组件列表, 技术约束)
        """
        tech_stack = self.blueprint_data.get("tech_stack", {})

        # 主要语言
        primary_language = tech_stack.get("primary_language", "python")

        # 框架
        frameworks = tech_stack.get("frameworks", [])
        if isinstance(frameworks, str):
            frameworks = [frameworks] if frameworks else []

        # 组件
        components_raw = tech_stack.get("components", [])
        if isinstance(components_raw, list):
            # 可能是对象列表或字符串列表
            components = []
            for c in components_raw:
                if isinstance(c, dict):
                    components.append(c.get("name", ""))
                elif isinstance(c, str):
                    components.append(c)
        else:
            components = []

        # 约束
        constraints = tech_stack.get("core_constraints", "")

        # 如果没有明确指定语言，尝试从框架推断
        if not primary_language or primary_language == "python":
            primary_language = self._detect_language_from_tech(frameworks, components)

        return primary_language, frameworks, components, constraints

    def _detect_language_from_tech(
        self,
        frameworks: List[str],
        components: List[str],
    ) -> str:
        """从技术栈推断主要编程语言"""
        language_keywords = {
            "python": ["python", "django", "fastapi", "flask", "pytorch", "pandas", "sqlalchemy"],
            "typescript": ["typescript", "angular", "react", "vue", "next.js", "nest.js", "express"],
            "javascript": ["javascript", "jquery", "webpack"],
            "java": ["java", "spring", "springboot", "maven", "gradle"],
            "go": ["go", "golang", "gin", "echo"],
            "rust": ["rust", "cargo", "tokio", "actix"],
        }

        all_tech = " ".join(frameworks + components).lower()

        scores = {}
        for lang, keywords in language_keywords.items():
            score = sum(1 for kw in keywords if kw in all_tech)
            if score > 0:
                scores[lang] = score

        if scores:
            return max(scores, key=scores.get)
        return "python"

    def _build_systems_summary(self) -> List[SystemSummary]:
        """构建系统摘要列表"""
        summaries = []

        for system in self.systems:
            system_number = system.get("system_number")

            # 统计该系统下的模块
            system_modules = [
                m for m in self.modules
                if m.get("system_number") == system_number
            ]

            # 按类型统计
            module_types = Counter(m.get("module_type", "unknown") for m in system_modules)

            summaries.append(SystemSummary(
                system_number=system_number,
                name=system.get("name", ""),
                description=system.get("description", ""),
                responsibilities=system.get("responsibilities", []),
                module_count=len(system_modules),
                module_types=dict(module_types),
            ))

        return summaries

    def _organize_modules_by_type(self) -> Dict[str, List[ModuleSummary]]:
        """按类型组织模块"""
        # 计算每个模块被依赖的次数
        dependent_counts = self._calculate_dependent_counts()

        modules_by_type = defaultdict(list)

        for m in self.modules:
            module_number = m.get("module_number")
            module_type = m.get("module_type", "unknown")

            summary = ModuleSummary(
                module_number=module_number,
                system_number=m.get("system_number", 0),
                name=m.get("name", ""),
                module_type=module_type,
                description=m.get("description", ""),
                interface=m.get("interface", ""),
                dependencies=m.get("dependencies", []),
                dependent_count=dependent_counts.get(m.get("name", ""), 0),
            )

            modules_by_type[module_type].append(summary)

        return dict(modules_by_type)

    def _calculate_dependent_counts(self) -> Dict[str, int]:
        """计算每个模块被依赖的次数"""
        counts = Counter()
        for dep in self.module_dependencies:
            to_module = dep.get("to_module", dep.get("to", ""))
            if to_module:
                counts[to_module] += 1
        return dict(counts)

    def _build_dependency_graph(self) -> DependencyGraph:
        """构建依赖关系图"""
        graph = DependencyGraph()

        # 构建边
        for dep in self.module_dependencies:
            from_module = dep.get("from_module", dep.get("from", ""))
            to_module = dep.get("to_module", dep.get("to", ""))
            if from_module and to_module:
                if from_module not in graph.edges:
                    graph.edges[from_module] = []
                graph.edges[from_module].append(to_module)

        # 计算入度
        for edges in graph.edges.values():
            for to_module in edges:
                graph.in_degrees[to_module] = graph.in_degrees.get(to_module, 0) + 1

        # 检测循环依赖
        graph.cycles = detect_cycles(graph.edges, max_cycles=5)

        # 识别高依赖模块（被3+模块依赖）
        graph.high_dependency_modules = [
            name for name, count in graph.in_degrees.items()
            if count >= 3
        ]

        return graph

    def _calculate_complexity(self) -> Tuple[float, Dict[str, Any]]:
        """
        计算项目复杂度评分

        复杂度因素：
        - 模块数量
        - 系统数量
        - 依赖密度
        - 循环依赖数量
        - 模块类型多样性

        Returns:
            (复杂度评分 0.0-1.0, 复杂度因素详情)
        """
        factors = {}

        # 模块数量因素 (0-1)
        module_count = len(self.modules)
        if module_count <= 5:
            module_factor = 0.1
        elif module_count <= 15:
            module_factor = 0.3
        elif module_count <= 30:
            module_factor = 0.5
        elif module_count <= 50:
            module_factor = 0.7
        else:
            module_factor = 0.9
        factors["module_count"] = {"value": module_count, "score": module_factor}

        # 系统数量因素 (0-1)
        system_count = len(self.systems)
        if system_count <= 2:
            system_factor = 0.2
        elif system_count <= 4:
            system_factor = 0.4
        elif system_count <= 6:
            system_factor = 0.6
        else:
            system_factor = 0.8
        factors["system_count"] = {"value": system_count, "score": system_factor}

        # 依赖密度因素 (0-1)
        dep_count = len(self.module_dependencies)
        max_possible_deps = module_count * (module_count - 1) if module_count > 1 else 1
        dep_density = dep_count / max_possible_deps if max_possible_deps > 0 else 0
        dep_factor = min(dep_density * 2, 1.0)  # 放大系数
        factors["dependency_density"] = {
            "value": dep_count,
            "density": dep_density,
            "score": dep_factor,
        }

        # 循环依赖因素 (0-1)
        # 构建依赖图以检测循环
        dep_graph = self._build_dependency_graph()
        cycle_count = len(dep_graph.cycles)
        if cycle_count == 0:
            cycle_factor = 0.0
        elif cycle_count <= 2:
            cycle_factor = 0.3
        elif cycle_count <= 5:
            cycle_factor = 0.6
        else:
            cycle_factor = 0.9
        factors["circular_dependencies"] = {"count": cycle_count, "score": cycle_factor}

        # 模块类型多样性 (0-1)
        module_types = set(m.get("module_type", "") for m in self.modules)
        type_count = len(module_types)
        if type_count <= 2:
            type_factor = 0.2
        elif type_count <= 4:
            type_factor = 0.4
        elif type_count <= 6:
            type_factor = 0.6
        else:
            type_factor = 0.8
        factors["module_type_diversity"] = {"types": list(module_types), "score": type_factor}

        # 综合评分（加权平均）
        weights = {
            "module_count": 0.3,
            "system_count": 0.2,
            "dependency_density": 0.2,
            "circular_dependencies": 0.15,
            "module_type_diversity": 0.15,
        }

        complexity_score = sum(
            factors[k]["score"] * weights[k]
            for k in weights
        )

        return complexity_score, factors
