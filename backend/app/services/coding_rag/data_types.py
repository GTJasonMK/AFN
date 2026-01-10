"""
编程项目RAG数据类型定义

定义11种需要入库的数据类型及其检索权重。
"""

from enum import Enum
from typing import Dict


class CodingDataType(str, Enum):
    """编程项目RAG数据类型枚举"""

    INSPIRATION = "inspiration"           # 灵感对话
    ARCHITECTURE = "architecture"         # 架构设计
    TECH_STACK = "tech_stack"            # 技术栈
    REQUIREMENT = "requirement"           # 核心需求
    CHALLENGE = "challenge"               # 技术挑战
    SYSTEM = "system"                     # 系统划分
    MODULE = "module"                     # 模块定义
    FEATURE_OUTLINE = "feature_outline"   # 功能大纲
    DEPENDENCY = "dependency"             # 依赖关系
    FEATURE_PROMPT = "feature_prompt"     # 功能实现Prompt
    REVIEW_PROMPT = "review_prompt"       # 功能审查/测试Prompt

    @classmethod
    def get_weight(cls, data_type: str) -> float:
        """
        获取数据类型的检索权重

        权重越高，检索时该类型结果越优先。
        权重影响排序，不影响召回。

        Args:
            data_type: 数据类型字符串

        Returns:
            权重值，范围0.0-1.0
        """
        weights: Dict[str, float] = {
            cls.ARCHITECTURE.value: 1.0,      # 架构最重要
            cls.REQUIREMENT.value: 0.95,      # 核心需求次之
            cls.TECH_STACK.value: 0.9,        # 技术栈
            cls.SYSTEM.value: 0.85,           # 系统划分
            cls.MODULE.value: 0.8,            # 模块定义
            cls.FEATURE_OUTLINE.value: 0.75,  # 功能大纲
            cls.FEATURE_PROMPT.value: 0.7,    # 功能实现Prompt
            cls.REVIEW_PROMPT.value: 0.65,    # 功能审查/测试Prompt
            cls.DEPENDENCY.value: 0.6,        # 依赖关系
            cls.CHALLENGE.value: 0.5,         # 技术挑战
            cls.INSPIRATION.value: 0.4,       # 灵感对话权重较低
        }
        return weights.get(data_type, 0.5)

    @classmethod
    def get_display_name(cls, data_type: str) -> str:
        """
        获取数据类型的显示名称

        Args:
            data_type: 数据类型字符串

        Returns:
            中文显示名称
        """
        names: Dict[str, str] = {
            cls.INSPIRATION.value: "灵感对话",
            cls.ARCHITECTURE.value: "架构设计",
            cls.TECH_STACK.value: "技术栈",
            cls.REQUIREMENT.value: "核心需求",
            cls.CHALLENGE.value: "技术挑战",
            cls.SYSTEM.value: "系统划分",
            cls.MODULE.value: "模块定义",
            cls.FEATURE_OUTLINE.value: "功能大纲",
            cls.DEPENDENCY.value: "依赖关系",
            cls.FEATURE_PROMPT.value: "功能Prompt",
            cls.REVIEW_PROMPT.value: "测试Prompt",
        }
        return names.get(data_type, data_type)

    @classmethod
    def get_source_table(cls, data_type: str) -> str:
        """
        获取数据类型对应的数据库表名

        【重要设计说明】
        编程项目使用独立的数据库表：
        - coding_features: 存储功能Prompt和审查Prompt

        Args:
            data_type: 数据类型字符串

        Returns:
            数据库表名
        """
        tables: Dict[str, str] = {
            cls.INSPIRATION.value: "novel_conversations",
            cls.ARCHITECTURE.value: "novel_blueprints",
            cls.TECH_STACK.value: "novel_blueprints",
            cls.REQUIREMENT.value: "novel_blueprints",
            cls.CHALLENGE.value: "novel_blueprints",
            cls.SYSTEM.value: "part_outlines",
            cls.MODULE.value: "blueprint_characters",
            cls.FEATURE_OUTLINE.value: "chapter_outlines",
            cls.DEPENDENCY.value: "blueprint_relationships",
            cls.FEATURE_PROMPT.value: "coding_features",
            cls.REVIEW_PROMPT.value: "coding_features",
        }
        return tables.get(data_type, "unknown")

    @classmethod
    def all_types(cls) -> list:
        """获取所有数据类型列表"""
        return list(cls)


# 蓝图生成时需要入库的类型
BLUEPRINT_INGESTION_TYPES = [
    CodingDataType.ARCHITECTURE,
    CodingDataType.TECH_STACK,
    CodingDataType.REQUIREMENT,
    CodingDataType.CHALLENGE,
]


__all__ = [
    "CodingDataType",
    "BLUEPRINT_INGESTION_TYPES",
]
