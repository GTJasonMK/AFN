"""
编程项目详情页Sections模块

重构后的4-Tab结构:
- overview: 概览Tab
- architecture: 架构设计Tab（合并蓝图+两层结构）
- directory: 目录结构Tab
- generation: 生成管理Tab（合并依赖+已生成）
"""

from .overview import CodingOverviewSection
from .architecture import ArchitectureSection
from .directory import DirectorySection
from .generation import GenerationSection

# 保留旧组件供复用
from .systems import SystemNode, ModuleNode
from .dependencies import GroupedDependencyCard
from .generated import GeneratedItemCard

__all__ = [
    # 主要Section
    "CodingOverviewSection",
    "ArchitectureSection",
    "DirectorySection",
    "GenerationSection",
    # 可复用组件
    "SystemNode",
    "ModuleNode",
    "GroupedDependencyCard",
    "GeneratedItemCard",
]
