"""
项目服务工厂

根据项目类型（novel/coding）提供不同的提示词映射和配置。
采用策略模式，使现有服务可以根据项目类型使用不同的提示词。
"""

from enum import Enum
from typing import Dict, Optional


class ProjectStage(str, Enum):
    """项目阶段枚举"""
    INSPIRATION = "inspiration"     # 灵感对话 / 需求分析
    BLUEPRINT = "blueprint"         # 蓝图生成 / 架构设计
    PART_OUTLINE = "part_outline"   # 分部大纲 / 模块设计
    CHAPTER_OUTLINE = "outline"     # 章节大纲 / 功能设计
    WRITING = "writing"             # 章节写作 / Prompt生成


class ProjectTypeConfig:
    """项目类型配置"""

    # 提示词映射：project_type -> stage -> prompt_name
    PROMPT_MAPPINGS: Dict[str, Dict[str, str]] = {
        "novel": {
            ProjectStage.INSPIRATION: "inspiration",
            ProjectStage.BLUEPRINT: "blueprint",
            ProjectStage.PART_OUTLINE: "part_outline",
            ProjectStage.CHAPTER_OUTLINE: "outline",
            ProjectStage.WRITING: "writing",
        },
        "coding": {
            ProjectStage.INSPIRATION: "requirement_analysis",
            ProjectStage.BLUEPRINT: "architecture_design",
            ProjectStage.PART_OUTLINE: "module_design",
            ProjectStage.CHAPTER_OUTLINE: "feature_design",
            ProjectStage.WRITING: "prompt_generation",
        },
    }

    # UI术语映射：project_type -> term_key -> display_text
    TERMINOLOGY: Dict[str, Dict[str, str]] = {
        "novel": {
            "inspiration": "灵感对话",
            "blueprint": "蓝图",
            "part": "分部",
            "chapter": "章节",
            "content": "正文",
            "writing": "写作",
        },
        "coding": {
            "inspiration": "需求分析",
            "blueprint": "架构设计",
            "part": "模块",
            "chapter": "功能",
            "content": "Prompt",
            "writing": "生成",
        },
    }

    # 页面标题映射
    PAGE_TITLES: Dict[str, Dict[str, str]] = {
        "novel": {
            "inspiration_page": "灵感对话",
            "blueprint_page": "蓝图设计",
            "outline_page": "大纲规划",
            "writing_page": "章节写作",
        },
        "coding": {
            "inspiration_page": "需求分析",
            "blueprint_page": "架构设计",
            "outline_page": "功能规划",
            "writing_page": "Prompt生成",
        },
    }

    @classmethod
    def get_prompt_name(cls, project_type: str, stage: str) -> str:
        """
        获取指定项目类型和阶段的提示词名称

        Args:
            project_type: 项目类型 (novel/coding)
            stage: 项目阶段 (inspiration/blueprint/part_outline/outline/writing)

        Returns:
            提示词名称
        """
        type_mapping = cls.PROMPT_MAPPINGS.get(project_type, cls.PROMPT_MAPPINGS["novel"])
        return type_mapping.get(stage, stage)

    @classmethod
    def get_term(cls, project_type: str, term_key: str) -> str:
        """
        获取指定项目类型的术语

        Args:
            project_type: 项目类型 (novel/coding)
            term_key: 术语键

        Returns:
            显示文本
        """
        type_terms = cls.TERMINOLOGY.get(project_type, cls.TERMINOLOGY["novel"])
        return type_terms.get(term_key, term_key)

    @classmethod
    def get_page_title(cls, project_type: str, page_key: str) -> str:
        """
        获取指定项目类型的页面标题

        Args:
            project_type: 项目类型 (novel/coding)
            page_key: 页面键

        Returns:
            页面标题
        """
        type_titles = cls.PAGE_TITLES.get(project_type, cls.PAGE_TITLES["novel"])
        return type_titles.get(page_key, page_key)

    @classmethod
    def is_valid_project_type(cls, project_type: str) -> bool:
        """
        检查项目类型是否有效

        Args:
            project_type: 项目类型

        Returns:
            是否有效
        """
        return project_type in cls.PROMPT_MAPPINGS

    @classmethod
    def get_all_project_types(cls) -> list:
        """获取所有支持的项目类型"""
        return list(cls.PROMPT_MAPPINGS.keys())
