"""
编程项目详情页Sections模块
"""

from .overview import CodingOverviewSection
from .planning import ProjectPlanningSection
from .modules import ModulesSection
from .systems import SystemsSection
from .dependencies import DependenciesSection
from .features import FeaturesSection
from .generated import GeneratedSection

__all__ = [
    "CodingOverviewSection",
    "ProjectPlanningSection",
    "ModulesSection",
    "SystemsSection",
    "DependenciesSection",
    "FeaturesSection",
    "GeneratedSection",
]
