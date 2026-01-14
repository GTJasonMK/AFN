"""
Coding项目文件驱动Prompt生成服务

提供目录结构生成、文件Prompt生成和架构设计服务层。
"""

from .directory_service import DirectoryStructureService
from .file_prompt_service import FilePromptService
from .directory_generator import (
    DirectoryTreeBuilder,
    BruteForceOutput,
    PlannedDirectory,
    PlannedFile,
)
from .architect import (
    ArchitecturePattern,
    ProjectProfiler,
    ArchitectureDecisionMaker,
    ArchitectureBasedGenerator,
    QualityEvaluator,
    RefinementAgent,
    ProjectProfile,
    ArchitectureDecision,
    QualityMetrics,
)

__all__ = [
    # 服务
    "DirectoryStructureService",
    "FilePromptService",
    # 目录结构工具
    "DirectoryTreeBuilder",
    "BruteForceOutput",
    "PlannedDirectory",
    "PlannedFile",
    # 三阶段架构
    "ArchitecturePattern",
    "ProjectProfiler",
    "ArchitectureDecisionMaker",
    "ArchitectureBasedGenerator",
    "QualityEvaluator",
    "RefinementAgent",
    "ProjectProfile",
    "ArchitectureDecision",
    "QualityMetrics",
]
