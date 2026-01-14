"""
架构设计Agent模块

三阶段流水线架构：
1. ProjectProfiler - 项目画像构建
2. ArchitectureDecisionMaker - 架构决策
3. ArchitectureBasedGenerator + RefinementAgent - 生成与精化
"""

from .schemas import (
    ArchitecturePattern,
    ProjectProfile,
    ArchitectureDecision,
    QualityMetrics,
    LayerDefinition,
    ModulePlacement,
    SystemSummary,
    ModuleSummary,
    DependencyGraph,
    SharedModuleStrategy,
    IssueType,
    IssueSeverity,
    StructureIssue,
)
from .patterns import (
    PatternTemplate,
    PATTERN_TEMPLATES,
    get_pattern_template,
    recommend_pattern,
)
from .profiler import ProjectProfiler
from .decision_maker import ArchitectureDecisionMaker
from .generator import ArchitectureBasedGenerator
from .quality_evaluator import QualityEvaluator
from .refiner import RefinementAgent

__all__ = [
    # 数据模型
    "ArchitecturePattern",
    "ProjectProfile",
    "ArchitectureDecision",
    "QualityMetrics",
    "LayerDefinition",
    "ModulePlacement",
    "SystemSummary",
    "ModuleSummary",
    "DependencyGraph",
    "SharedModuleStrategy",
    "IssueType",
    "IssueSeverity",
    "StructureIssue",
    # 模式模板
    "PatternTemplate",
    "PATTERN_TEMPLATES",
    "get_pattern_template",
    "recommend_pattern",
    # 核心类
    "ProjectProfiler",
    "ArchitectureDecisionMaker",
    "ArchitectureBasedGenerator",
    "QualityEvaluator",
    "RefinementAgent",
]
