"""
架构设计Agent数据模型定义

核心数据模型：
- ProjectProfile: 项目画像（阶段一输出）
- ArchitectureDecision: 架构决策（阶段二输出）
- QualityMetrics: 质量指标（阶段三输出）
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ==================== 架构模式枚举 ====================

class ArchitecturePattern(str, Enum):
    """架构模式枚举（先实现3种核心模式）"""
    LAYERED = "layered"              # 分层架构
    FEATURE_BASED = "feature_based"  # 功能模块架构
    SIMPLE = "simple"                # 简单架构（默认/兜底）
    # 后续扩展：
    # HEXAGONAL = "hexagonal"        # 六边形架构
    # CLEAN = "clean"                # 整洁架构


# ==================== 阶段一：项目画像 ====================

@dataclass
class SystemSummary:
    """系统摘要"""
    system_number: int
    name: str
    description: str
    responsibilities: List[str]
    module_count: int
    module_types: Dict[str, int]  # {"service": 3, "repository": 2}


@dataclass
class ModuleSummary:
    """模块摘要"""
    module_number: int
    system_number: int
    name: str
    module_type: str
    description: str
    interface: str
    dependencies: List[str]
    dependent_count: int  # 被多少个模块依赖


@dataclass
class DependencyGraph:
    """依赖关系图"""
    # 模块名 -> 依赖的模块名列表
    edges: Dict[str, List[str]] = field(default_factory=dict)
    # 模块名 -> 被依赖次数
    in_degrees: Dict[str, int] = field(default_factory=dict)
    # 循环依赖
    cycles: List[List[str]] = field(default_factory=list)
    # 高依赖模块（被3+模块依赖）
    high_dependency_modules: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edges": self.edges,
            "in_degrees": self.in_degrees,
            "cycles": self.cycles,
            "high_dependency_modules": self.high_dependency_modules,
        }


@dataclass
class ProjectProfile:
    """
    项目画像

    阶段一输出：一次性收集的所有项目信息，为后续决策提供完整上下文。
    """
    # 基本信息
    project_id: str
    project_name: str
    project_type: str  # Web应用/CLI/API服务/桌面应用
    tech_style: str    # 前后端分离/单体/微服务
    one_sentence_summary: str
    architecture_synopsis: str

    # 技术栈
    primary_language: str
    frameworks: List[str]
    tech_components: List[str]
    tech_constraints: str

    # 系统和模块
    systems: List[SystemSummary]
    modules_by_type: Dict[str, List[ModuleSummary]]  # {"service": [...], "repository": [...]}
    total_modules: int
    total_systems: int

    # 依赖关系
    dependency_graph: DependencyGraph

    # 项目复杂度评估
    complexity_score: float  # 0.0-1.0
    complexity_factors: Dict[str, Any] = field(default_factory=dict)

    # 推荐的架构模式（基于项目特征自动推荐）
    recommended_pattern: Optional[ArchitecturePattern] = None
    recommendation_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_type": self.project_type,
            "tech_style": self.tech_style,
            "one_sentence_summary": self.one_sentence_summary,
            "architecture_synopsis": self.architecture_synopsis,
            "primary_language": self.primary_language,
            "frameworks": self.frameworks,
            "tech_components": self.tech_components,
            "tech_constraints": self.tech_constraints,
            "systems": [
                {
                    "system_number": s.system_number,
                    "name": s.name,
                    "description": s.description,
                    "responsibilities": s.responsibilities,
                    "module_count": s.module_count,
                    "module_types": s.module_types,
                }
                for s in self.systems
            ],
            "modules_by_type": {
                k: [
                    {
                        "module_number": m.module_number,
                        "name": m.name,
                        "module_type": m.module_type,
                        "description": m.description[:100],
                        "dependent_count": m.dependent_count,
                    }
                    for m in v
                ]
                for k, v in self.modules_by_type.items()
            },
            "total_modules": self.total_modules,
            "total_systems": self.total_systems,
            "dependency_graph": self.dependency_graph.to_dict(),
            "complexity_score": self.complexity_score,
            "complexity_factors": self.complexity_factors,
            "recommended_pattern": self.recommended_pattern.value if self.recommended_pattern else None,
            "recommendation_reason": self.recommendation_reason,
        }

    def get_all_modules(self) -> List[ModuleSummary]:
        """获取所有模块的扁平列表"""
        result = []
        for modules in self.modules_by_type.values():
            result.extend(modules)
        return result

    def get_module_by_number(self, module_number: int) -> Optional[ModuleSummary]:
        """根据模块编号获取模块"""
        for modules in self.modules_by_type.values():
            for m in modules:
                if m.module_number == module_number:
                    return m
        return None


# ==================== 阶段二：架构决策 ====================

@dataclass
class LayerDefinition:
    """层级定义"""
    name: str           # 层级名称：presentation, application, domain, infrastructure
    path: str           # 目录路径：src/presentation
    description: str    # 层级描述
    allowed_dependencies: List[str]  # 允许依赖的层级名称


@dataclass
class ModulePlacement:
    """模块放置计划"""
    module_number: int
    module_name: str
    target_layer: str           # 目标层级名称
    target_path: str            # 目标目录路径
    files_to_create: List[str]  # 需要创建的文件列表
    rationale: str              # 放置理由


@dataclass
class SharedModuleStrategy:
    """共享模块策略"""
    shared_path: str = "src/shared"
    criteria: List[str] = field(default_factory=list)  # 成为共享模块的条件
    candidates: List[str] = field(default_factory=list)  # 候选共享模块


@dataclass
class ArchitectureDecision:
    """
    架构决策

    阶段二输出：选择的架构模式和具体的模块放置计划。
    """
    # 选择的架构模式
    pattern: ArchitecturePattern
    pattern_rationale: str  # 选择该模式的理由

    # 层级定义（根据模式生成）
    layers: List[LayerDefinition]

    # 模块放置计划
    module_placements: List[ModulePlacement]

    # 共享模块策略
    shared_strategy: SharedModuleStrategy

    # 命名约定
    naming_convention: str  # snake_case / kebab-case

    # 特殊配置
    root_path: str = "src"
    create_init_files: bool = True  # Python项目创建__init__.py

    # 用户自定义约束
    custom_constraints: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern.value,
            "pattern_rationale": self.pattern_rationale,
            "layers": [
                {
                    "name": l.name,
                    "path": l.path,
                    "description": l.description,
                    "allowed_dependencies": l.allowed_dependencies,
                }
                for l in self.layers
            ],
            "module_placements": [
                {
                    "module_number": p.module_number,
                    "module_name": p.module_name,
                    "target_layer": p.target_layer,
                    "target_path": p.target_path,
                    "files_to_create": p.files_to_create,
                    "rationale": p.rationale,
                }
                for p in self.module_placements
            ],
            "shared_strategy": {
                "shared_path": self.shared_strategy.shared_path,
                "criteria": self.shared_strategy.criteria,
                "candidates": self.shared_strategy.candidates,
            },
            "naming_convention": self.naming_convention,
            "root_path": self.root_path,
            "create_init_files": self.create_init_files,
            "custom_constraints": self.custom_constraints,
        }

    def get_layer_by_name(self, name: str) -> Optional[LayerDefinition]:
        """根据名称获取层级定义"""
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def get_placement_by_module(self, module_number: int) -> Optional[ModulePlacement]:
        """根据模块编号获取放置计划"""
        for placement in self.module_placements:
            if placement.module_number == module_number:
                return placement
        return None


# ==================== 阶段三：质量指标 ====================

@dataclass
class QualityMetrics:
    """
    目录结构质量指标

    多维度评估生成的目录结构质量。
    """
    # 覆盖率（保留现有）
    module_coverage: float = 0.0        # 模块覆盖率 (0.0-1.0)
    file_completeness: float = 0.0      # 文件信息完整度 (0.0-1.0)

    # 内聚性（新增）
    directory_cohesion: float = 0.0     # 目录内文件功能相关性 (0.0-1.0)
    module_cohesion: float = 0.0        # 模块职责一致性 (0.0-1.0)

    # 耦合度（新增）
    coupling_score: float = 0.0         # 耦合度评分 (0.0-1.0，越高表示低耦合)
    circular_dependencies: int = 0      # 循环依赖数量
    cross_layer_violations: int = 0     # 跨层违规数量

    # 可理解性（新增）
    depth_score: float = 0.0            # 层级深度评分 (0.0-1.0，浅而扁平得分高)
    naming_consistency: float = 0.0     # 命名一致性 (0.0-1.0)
    structure_clarity: float = 0.0      # 结构清晰度 (0.0-1.0)

    # 架构一致性（新增）
    pattern_adherence: float = 0.0      # 与选定架构模式的符合度 (0.0-1.0)

    # 详细问题列表
    issues: List[Dict[str, Any]] = field(default_factory=list)

    # 统计信息
    total_directories: int = 0
    total_files: int = 0
    max_depth: int = 0
    avg_files_per_dir: float = 0.0

    @property
    def coverage_score(self) -> float:
        """覆盖率综合评分"""
        return (self.module_coverage + self.file_completeness) / 2

    @property
    def cohesion_score(self) -> float:
        """内聚性综合评分"""
        return (self.directory_cohesion + self.module_cohesion) / 2

    @property
    def understandability_score(self) -> float:
        """可理解性综合评分"""
        return (self.depth_score + self.naming_consistency + self.structure_clarity) / 3

    @property
    def overall_score(self) -> float:
        """
        综合质量评分

        权重分配：
        - 覆盖率: 25%
        - 内聚性: 20%
        - 耦合度: 20%
        - 可理解性: 15%
        - 架构一致性: 20%
        """
        weights = {
            "coverage": 0.25,
            "cohesion": 0.20,
            "coupling": 0.20,
            "understandability": 0.15,
            "architecture": 0.20,
        }
        scores = {
            "coverage": self.coverage_score,
            "cohesion": self.cohesion_score,
            "coupling": self.coupling_score,
            "understandability": self.understandability_score,
            "architecture": self.pattern_adherence,
        }
        return sum(scores[k] * weights[k] for k in weights)

    def to_dict(self) -> Dict[str, Any]:
        return {
            # 覆盖率
            "module_coverage": self.module_coverage,
            "file_completeness": self.file_completeness,
            "coverage_score": self.coverage_score,
            # 内聚性
            "directory_cohesion": self.directory_cohesion,
            "module_cohesion": self.module_cohesion,
            "cohesion_score": self.cohesion_score,
            # 耦合度
            "coupling_score": self.coupling_score,
            "circular_dependencies": self.circular_dependencies,
            "cross_layer_violations": self.cross_layer_violations,
            # 可理解性
            "depth_score": self.depth_score,
            "naming_consistency": self.naming_consistency,
            "structure_clarity": self.structure_clarity,
            "understandability_score": self.understandability_score,
            # 架构一致性
            "pattern_adherence": self.pattern_adherence,
            # 综合
            "overall_score": self.overall_score,
            # 统计
            "total_directories": self.total_directories,
            "total_files": self.total_files,
            "max_depth": self.max_depth,
            "avg_files_per_dir": self.avg_files_per_dir,
            # 问题
            "issues": self.issues,
        }

    def get_grade(self) -> str:
        """获取质量等级"""
        score = self.overall_score
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"


# ==================== 问题类型（从旧模块保留） ====================

class IssueType(str, Enum):
    """问题类型"""
    MISSING_MODULE = "missing_module"
    DUPLICATE_STRUCTURE = "duplicate_structure"
    DEEP_NESTING = "deep_nesting"
    NAMING_VIOLATION = "naming_violation"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    OVER_DEPENDENCY = "over_dependency"
    LARGE_DIRECTORY = "large_directory"
    LAYER_VIOLATION = "layer_violation"  # 新增：层级违规
    INCOMPLETE_FILE_INFO = "incomplete_file_info"  # 新增：文件信息不完整


class IssueSeverity(str, Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class StructureIssue:
    """结构问题"""
    issue_type: IssueType
    severity: IssueSeverity
    description: str
    affected_paths: List[str] = field(default_factory=list)
    affected_modules: List[int] = field(default_factory=list)
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "affected_paths": self.affected_paths,
            "affected_modules": self.affected_modules,
            "suggestion": self.suggestion,
        }
