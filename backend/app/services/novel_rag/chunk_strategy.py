"""
小说项目分块策略配置

定义各数据类型的分块策略，支持灵活切换。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .data_types import NovelDataType
from ..rag_common.chunk_strategy_base import BaseChunkStrategyManager


class NovelChunkMethod(str, Enum):
    """小说分块方法枚举"""

    # 整体入库，不分割
    WHOLE = "whole"

    # 按Markdown标题分割（##/###）
    MARKDOWN_HEADER = "markdown_header"

    # 按Q&A轮次合并
    QA_ROUND = "qa_round"

    # 简单记录（每条数据1个chunk）
    SIMPLE = "simple"

    # 按段落分割（带重叠）
    PARAGRAPH = "paragraph"

    # 按段落分割（不带重叠）
    PARAGRAPH_NO_OVERLAP = "paragraph_no_overlap"

    # 按固定长度分割
    FIXED_LENGTH = "fixed_length"

    # 按字段分割（用于世界观、分部大纲等）
    BY_FIELD = "by_field"

    # 按维度分割（用于角色、主角档案）
    BY_DIMENSION = "by_dimension"

    # 语义动态规划分割（基于句子嵌入和DP最优切分）
    SEMANTIC_DP = "semantic_dp"


@dataclass
class NovelChunkConfig:
    """单个数据类型的分块配置"""

    # 分块方法
    method: NovelChunkMethod = NovelChunkMethod.SIMPLE

    # Markdown分割的最小标题级别（2=##）
    md_min_level: int = 2

    # Markdown分割的最大标题级别（3=###）
    md_max_level: int = 3

    # 最小chunk长度（小于此值可能合并）
    min_chunk_length: int = 80

    # 最大chunk长度（大于此值可能分割）
    max_chunk_length: int = 800

    # 是否添加重叠
    with_overlap: bool = True

    # 重叠长度
    overlap_length: int = 100

    # 长字段阈值（超过此长度的字段需要分割）
    long_field_threshold: int = 300

    # 是否添加上下文前缀
    add_context_prefix: bool = True

    # 固定长度分割时的chunk大小
    fixed_chunk_size: int = 500

    # ==================== 语义分块相关配置 ====================

    # 语义分块：门控阈值（相似度低于此值不进行距离增强）
    semantic_gate_threshold: float = 0.3

    # 语义分块：距离增强系数
    semantic_alpha: float = 0.1

    # 语义分块：长度归一化指数（1.0-1.5之间）
    semantic_gamma: float = 1.1

    # 语义分块：最小块句子数
    semantic_min_sentences: int = 2

    # 语义分块：最大块句子数
    semantic_max_sentences: int = 20

    # 额外配置参数
    extra: Dict[str, Any] = field(default_factory=dict)


# ==================== 预定义策略配置 ====================

# 默认配置：当前系统的行为
DEFAULT_NOVEL_STRATEGIES: Dict[NovelDataType, NovelChunkConfig] = {
    # 灵感对话：按Q&A轮次合并
    NovelDataType.INSPIRATION: NovelChunkConfig(
        method=NovelChunkMethod.QA_ROUND,
        max_chunk_length=2000,
    ),

    # 故事概述：按Markdown标题分割
    NovelDataType.SYNOPSIS: NovelChunkConfig(
        method=NovelChunkMethod.MARKDOWN_HEADER,
        md_min_level=2,
        md_max_level=3,
        min_chunk_length=80,
    ),

    # 世界观设定：按字段分割
    NovelDataType.WORLD_SETTING: NovelChunkConfig(
        method=NovelChunkMethod.BY_FIELD,
        long_field_threshold=300,
        with_overlap=True,
        add_context_prefix=True,
    ),

    # 蓝图元数据：简单记录
    NovelDataType.BLUEPRINT_METADATA: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 角色设定：按维度分割
    NovelDataType.CHARACTER: NovelChunkConfig(
        method=NovelChunkMethod.BY_DIMENSION,
        add_context_prefix=True,
    ),

    # 角色关系：简单记录
    NovelDataType.RELATIONSHIP: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 角色状态：简单记录
    NovelDataType.CHARACTER_STATE: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 主角档案：按维度分割
    NovelDataType.PROTAGONIST: NovelChunkConfig(
        method=NovelChunkMethod.BY_DIMENSION,
        long_field_threshold=300,
        add_context_prefix=True,
    ),

    # 主角属性变更：简单记录
    NovelDataType.PROTAGONIST_CHANGE: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 分部大纲：按字段分割
    NovelDataType.PART_OUTLINE: NovelChunkConfig(
        method=NovelChunkMethod.BY_FIELD,
        long_field_threshold=300,
        with_overlap=True,
        add_context_prefix=True,
    ),

    # 章节大纲：简单记录
    NovelDataType.CHAPTER_OUTLINE: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 章节正文：按段落分割（带重叠）
    NovelDataType.CHAPTER_CONTENT: NovelChunkConfig(
        method=NovelChunkMethod.PARAGRAPH,
        min_chunk_length=80,
        max_chunk_length=800,
        with_overlap=True,
        overlap_length=100,
    ),

    # 章节摘要：简单记录
    NovelDataType.CHAPTER_SUMMARY: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 关键事件：简单记录
    NovelDataType.KEY_EVENT: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 章节元数据：简单记录
    NovelDataType.CHAPTER_METADATA: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 伏笔记录：简单记录
    NovelDataType.FORESHADOWING: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),
}


# 优化配置：提高块内相关度
OPTIMIZED_NOVEL_STRATEGIES: Dict[NovelDataType, NovelChunkConfig] = {
    # 灵感对话：按Q&A轮次合并，限制最大长度
    NovelDataType.INSPIRATION: NovelChunkConfig(
        method=NovelChunkMethod.QA_ROUND,
        max_chunk_length=1500,
    ),

    # 故事概述：整体入库（通常不会太长）
    NovelDataType.SYNOPSIS: NovelChunkConfig(
        method=NovelChunkMethod.WHOLE,
    ),

    # 世界观设定：按字段分割
    NovelDataType.WORLD_SETTING: NovelChunkConfig(
        method=NovelChunkMethod.BY_FIELD,
        long_field_threshold=400,  # 放宽阈值，减少碎片
        with_overlap=False,
        add_context_prefix=True,
    ),

    # 蓝图元数据：整体入库
    NovelDataType.BLUEPRINT_METADATA: NovelChunkConfig(
        method=NovelChunkMethod.WHOLE,
    ),

    # 角色设定：按维度分割
    NovelDataType.CHARACTER: NovelChunkConfig(
        method=NovelChunkMethod.BY_DIMENSION,
        add_context_prefix=True,
    ),

    # 角色关系：简单记录
    NovelDataType.RELATIONSHIP: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
        add_context_prefix=True,
    ),

    # 角色状态：简单记录
    NovelDataType.CHARACTER_STATE: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 主角档案：按维度分割
    NovelDataType.PROTAGONIST: NovelChunkConfig(
        method=NovelChunkMethod.BY_DIMENSION,
        long_field_threshold=400,
        add_context_prefix=True,
    ),

    # 主角属性变更：简单记录
    NovelDataType.PROTAGONIST_CHANGE: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 分部大纲：整体入库（每个分部作为一个完整语义单元）
    NovelDataType.PART_OUTLINE: NovelChunkConfig(
        method=NovelChunkMethod.WHOLE,
        add_context_prefix=True,
    ),

    # 章节大纲：简单记录
    NovelDataType.CHAPTER_OUTLINE: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 章节正文：使用语义动态规划分块（基于句子嵌入的最优切分）
    NovelDataType.CHAPTER_CONTENT: NovelChunkConfig(
        method=NovelChunkMethod.SEMANTIC_DP,
        min_chunk_length=100,
        max_chunk_length=1200,
        with_overlap=False,  # 语义分块已考虑上下文连贯性
        semantic_gate_threshold=0.3,  # 门控阈值
        semantic_alpha=0.1,  # 距离增强系数
        semantic_gamma=1.1,  # 长度归一化指数
        semantic_min_sentences=3,  # 最小块句子数
        semantic_max_sentences=15,  # 最大块句子数
    ),

    # 章节摘要：整体入库
    NovelDataType.CHAPTER_SUMMARY: NovelChunkConfig(
        method=NovelChunkMethod.WHOLE,
    ),

    # 关键事件：简单记录
    NovelDataType.KEY_EVENT: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),

    # 章节元数据：整体入库
    NovelDataType.CHAPTER_METADATA: NovelChunkConfig(
        method=NovelChunkMethod.WHOLE,
    ),

    # 伏笔记录：简单记录
    NovelDataType.FORESHADOWING: NovelChunkConfig(
        method=NovelChunkMethod.SIMPLE,
    ),
}


class NovelChunkStrategyManager(BaseChunkStrategyManager[NovelDataType, NovelChunkConfig, NovelChunkMethod]):
    """
    小说分块策略管理器

    管理各数据类型的分块配置，支持切换预设策略或自定义配置。
    """

    PRESETS = {
        "default": DEFAULT_NOVEL_STRATEGIES,
        "optimized": OPTIMIZED_NOVEL_STRATEGIES,
    }
    DATA_TYPE_ENUM = NovelDataType
    CONFIG_CLASS = NovelChunkConfig
    METHOD_ENUM = NovelChunkMethod


# 全局默认策略管理器实例
_novel_default_manager: Optional[NovelChunkStrategyManager] = None


def get_novel_strategy_manager() -> NovelChunkStrategyManager:
    """
    获取全局小说策略管理器实例

    默认使用 "optimized" 预设，启用语义动态规划分块等优化策略。

    Returns:
        策略管理器实例
    """
    global _novel_default_manager
    if _novel_default_manager is None:
        _novel_default_manager = NovelChunkStrategyManager(preset="optimized")
    return _novel_default_manager


def set_novel_strategy_manager(manager: NovelChunkStrategyManager):
    """
    设置全局小说策略管理器实例

    Args:
        manager: 策略管理器实例
    """
    global _novel_default_manager
    _novel_default_manager = manager


def switch_novel_global_preset(preset: str):
    """
    切换全局小说预设策略

    Args:
        preset: 预设策略名称
    """
    get_novel_strategy_manager().switch_preset(preset)


__all__ = [
    "NovelChunkMethod",
    "NovelChunkConfig",
    "NovelChunkStrategyManager",
    "DEFAULT_NOVEL_STRATEGIES",
    "OPTIMIZED_NOVEL_STRATEGIES",
    "get_novel_strategy_manager",
    "set_novel_strategy_manager",
    "switch_novel_global_preset",
]
