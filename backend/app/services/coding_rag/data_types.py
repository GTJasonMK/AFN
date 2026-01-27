"""
编程项目RAG数据类型定义

定义10种需要入库的数据类型及其检索权重。
"""

from enum import Enum
from ..rag_common.data_type_mixin import RAGDataTypeMixin


class CodingDataType(RAGDataTypeMixin, str, Enum):
    """编程项目RAG数据类型枚举"""

    INSPIRATION = "inspiration"           # 灵感对话
    ARCHITECTURE = "architecture"         # 架构设计
    TECH_STACK = "tech_stack"            # 技术栈
    REQUIREMENT = "requirement"           # 核心需求
    CHALLENGE = "challenge"               # 技术挑战
    SYSTEM = "system"                     # 系统划分
    MODULE = "module"                     # 模块定义
    DEPENDENCY = "dependency"             # 依赖关系
    REVIEW_PROMPT = "review_prompt"       # 审查/测试Prompt
    FILE_PROMPT = "file_prompt"           # 文件实现Prompt

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


CodingDataType.WEIGHTS = {
    CodingDataType.ARCHITECTURE.value: 1.0,      # 架构最重要
    CodingDataType.REQUIREMENT.value: 0.95,      # 核心需求次之
    CodingDataType.TECH_STACK.value: 0.9,        # 技术栈
    CodingDataType.SYSTEM.value: 0.85,           # 系统划分
    CodingDataType.MODULE.value: 0.8,            # 模块定义
    CodingDataType.FILE_PROMPT.value: 0.72,      # 文件实现Prompt
    CodingDataType.REVIEW_PROMPT.value: 0.65,    # 审查/测试Prompt
    CodingDataType.DEPENDENCY.value: 0.6,        # 依赖关系
    CodingDataType.CHALLENGE.value: 0.5,         # 技术挑战
    CodingDataType.INSPIRATION.value: 0.4,       # 灵感对话权重较低
}

CodingDataType.DISPLAY_NAMES = {
    CodingDataType.INSPIRATION.value: "灵感对话",
    CodingDataType.ARCHITECTURE.value: "架构设计",
    CodingDataType.TECH_STACK.value: "技术栈",
    CodingDataType.REQUIREMENT.value: "核心需求",
    CodingDataType.CHALLENGE.value: "技术挑战",
    CodingDataType.SYSTEM.value: "系统划分",
    CodingDataType.MODULE.value: "模块定义",
    CodingDataType.DEPENDENCY.value: "依赖关系",
    CodingDataType.REVIEW_PROMPT.value: "测试Prompt",
    CodingDataType.FILE_PROMPT.value: "文件Prompt",
}

# 【重要设计说明】
# 编程项目使用独立的数据库表：
# - coding_source_files: 存储审查Prompt和文件实现Prompt
CodingDataType.SOURCE_TABLES = {
    CodingDataType.INSPIRATION.value: "coding_conversations",
    CodingDataType.ARCHITECTURE.value: "coding_blueprints",
    CodingDataType.TECH_STACK.value: "coding_blueprints",
    CodingDataType.REQUIREMENT.value: "coding_blueprints",
    CodingDataType.CHALLENGE.value: "coding_blueprints",
    CodingDataType.SYSTEM.value: "coding_systems",
    CodingDataType.MODULE.value: "coding_modules",
    CodingDataType.DEPENDENCY.value: "coding_blueprints",
    CodingDataType.REVIEW_PROMPT.value: "coding_source_files",
    CodingDataType.FILE_PROMPT.value: "coding_source_files",
}


__all__ = [
    "CodingDataType",
    "BLUEPRINT_INGESTION_TYPES",
]
