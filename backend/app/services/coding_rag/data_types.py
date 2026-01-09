"""
编程项目RAG数据类型定义

定义10种需要入库的数据类型及其检索权重。
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
    FEATURE_PROMPT = "feature_prompt"     # 功能Prompt

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
            cls.FEATURE_PROMPT.value: 0.7,    # 功能Prompt
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
        }
        return names.get(data_type, data_type)

    @classmethod
    def get_source_table(cls, data_type: str) -> str:
        """
        获取数据类型对应的数据库表名

        【重要设计说明】
        编程项目复用了小说系统的数据库表结构，以减少代码重复：
        - novel_conversations: 存储灵感对话（编程需求分析对话）
        - novel_blueprints: 存储架构蓝图（full_synopsis=架构描述, world_setting=技术栈等）
        - part_outlines: 存储系统划分（title=系统名, summary=描述, theme=职责, key_events=技术要求）
        - blueprint_characters: 存储模块定义（name=模块名, identity=类型, personality=描述, goals=接口, abilities=依赖）
        - chapter_outlines: 存储功能大纲
        - blueprint_relationships: 存储模块依赖关系
        - chapters: 存储功能Prompt内容

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
            cls.FEATURE_PROMPT.value: "chapters",
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
