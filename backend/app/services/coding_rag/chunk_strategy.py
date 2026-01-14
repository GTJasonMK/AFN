"""
分块策略配置

定义各数据类型的分块策略，支持灵活切换。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from .data_types import CodingDataType


class ChunkMethod(str, Enum):
    """分块方法枚举"""

    # 整体入库，不分割
    WHOLE = "whole"

    # 按Markdown标题分割（##/###）
    MARKDOWN_HEADER = "markdown_header"

    # 按Q&A轮次合并
    QA_ROUND = "qa_round"

    # 简单记录（每条数据1个chunk）
    SIMPLE = "simple"

    # 按模块聚合（用于依赖关系）
    MODULE_AGGREGATE = "module_aggregate"

    # 按段落分割
    PARAGRAPH = "paragraph"

    # 按固定长度分割
    FIXED_LENGTH = "fixed_length"

    # 语义动态规划分割（基于句子嵌入和DP最优切分）
    SEMANTIC_DP = "semantic_dp"


@dataclass
class ChunkConfig:
    """单个数据类型的分块配置"""

    # 分块方法
    method: ChunkMethod = ChunkMethod.SIMPLE

    # Markdown分割的最小标题级别（2=##）
    md_min_level: int = 2

    # Markdown分割的最大标题级别（3=###）
    md_max_level: int = 3

    # 最小chunk长度（小于此值可能合并）
    min_chunk_length: int = 100

    # 最大chunk长度（大于此值可能分割）
    max_chunk_length: int = 2000

    # 是否添加上下文前缀（如功能名称）
    add_context_prefix: bool = False

    # 固定长度分割时的chunk大小
    fixed_chunk_size: int = 500

    # 固定长度分割时的重叠大小
    chunk_overlap: int = 50

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
DEFAULT_STRATEGIES: Dict[CodingDataType, ChunkConfig] = {
    CodingDataType.INSPIRATION: ChunkConfig(
        method=ChunkMethod.QA_ROUND,
        max_chunk_length=2000,
    ),
    CodingDataType.ARCHITECTURE: ChunkConfig(
        method=ChunkMethod.MARKDOWN_HEADER,
        md_min_level=2,
        md_max_level=3,
        min_chunk_length=100,
    ),
    CodingDataType.TECH_STACK: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.REQUIREMENT: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.CHALLENGE: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.SYSTEM: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.MODULE: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.DEPENDENCY: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.REVIEW_PROMPT: ChunkConfig(
        method=ChunkMethod.MARKDOWN_HEADER,
        md_min_level=2,
        md_max_level=3,
    ),
    CodingDataType.FILE_PROMPT: ChunkConfig(
        method=ChunkMethod.MARKDOWN_HEADER,
        md_min_level=2,
        md_max_level=3,
    ),
}


# 优化配置：提高块内相关度
OPTIMIZED_STRATEGIES: Dict[CodingDataType, ChunkConfig] = {
    CodingDataType.INSPIRATION: ChunkConfig(
        method=ChunkMethod.QA_ROUND,
        max_chunk_length=1500,  # 限制单轮最大长度
    ),
    CodingDataType.ARCHITECTURE: ChunkConfig(
        method=ChunkMethod.MARKDOWN_HEADER,
        md_min_level=2,
        md_max_level=3,
        min_chunk_length=100,
    ),
    CodingDataType.TECH_STACK: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.REQUIREMENT: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.CHALLENGE: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.SYSTEM: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.MODULE: ChunkConfig(
        method=ChunkMethod.SIMPLE,
    ),
    CodingDataType.DEPENDENCY: ChunkConfig(
        method=ChunkMethod.MODULE_AGGREGATE,  # 按模块聚合
    ),
    CodingDataType.REVIEW_PROMPT: ChunkConfig(
        method=ChunkMethod.SEMANTIC_DP,  # 使用语义动态规划分块
        min_chunk_length=100,
        max_chunk_length=1500,
        semantic_gate_threshold=0.3,
        semantic_alpha=0.1,
        semantic_gamma=1.1,
        semantic_min_sentences=2,
        semantic_max_sentences=15,
    ),
    CodingDataType.FILE_PROMPT: ChunkConfig(
        method=ChunkMethod.SEMANTIC_DP,  # 使用语义动态规划分块
        min_chunk_length=100,
        max_chunk_length=1500,
        semantic_gate_threshold=0.3,
        semantic_alpha=0.1,
        semantic_gamma=1.1,
        semantic_min_sentences=2,
        semantic_max_sentences=15,
    ),
}


class ChunkStrategyManager:
    """
    分块策略管理器

    管理各数据类型的分块配置，支持切换预设策略或自定义配置。
    """

    # 预设策略集合
    PRESETS = {
        "default": DEFAULT_STRATEGIES,
        "optimized": OPTIMIZED_STRATEGIES,
    }

    def __init__(self, preset: str = "default"):
        """
        初始化策略管理器

        Args:
            preset: 预设策略名称，可选 "default" 或 "optimized"
        """
        self._preset_name = preset
        self._strategies: Dict[CodingDataType, ChunkConfig] = {}
        self._load_preset(preset)

    def _load_preset(self, preset: str):
        """加载预设策略"""
        if preset not in self.PRESETS:
            raise ValueError(f"未知的预设策略: {preset}，可选: {list(self.PRESETS.keys())}")

        # 深拷贝预设配置
        for data_type, config in self.PRESETS[preset].items():
            self._strategies[data_type] = ChunkConfig(
                method=config.method,
                md_min_level=config.md_min_level,
                md_max_level=config.md_max_level,
                min_chunk_length=config.min_chunk_length,
                max_chunk_length=config.max_chunk_length,
                add_context_prefix=config.add_context_prefix,
                fixed_chunk_size=config.fixed_chunk_size,
                chunk_overlap=config.chunk_overlap,
                # 语义分块参数
                semantic_gate_threshold=config.semantic_gate_threshold,
                semantic_alpha=config.semantic_alpha,
                semantic_gamma=config.semantic_gamma,
                semantic_min_sentences=config.semantic_min_sentences,
                semantic_max_sentences=config.semantic_max_sentences,
                extra=dict(config.extra),
            )

    def get_config(self, data_type: CodingDataType) -> ChunkConfig:
        """
        获取指定数据类型的分块配置

        Args:
            data_type: 数据类型

        Returns:
            分块配置
        """
        if data_type not in self._strategies:
            # 返回默认配置
            return ChunkConfig()
        return self._strategies[data_type]

    def set_config(self, data_type: CodingDataType, config: ChunkConfig):
        """
        设置指定数据类型的分块配置

        Args:
            data_type: 数据类型
            config: 分块配置
        """
        self._strategies[data_type] = config

    def set_method(self, data_type: CodingDataType, method: ChunkMethod):
        """
        快捷设置分块方法

        Args:
            data_type: 数据类型
            method: 分块方法
        """
        if data_type in self._strategies:
            self._strategies[data_type].method = method
        else:
            self._strategies[data_type] = ChunkConfig(method=method)

    def switch_preset(self, preset: str):
        """
        切换预设策略

        Args:
            preset: 预设策略名称
        """
        self._load_preset(preset)
        self._preset_name = preset

    def get_current_preset(self) -> str:
        """获取当前预设名称"""
        return self._preset_name

    def get_all_configs(self) -> Dict[CodingDataType, ChunkConfig]:
        """获取所有数据类型的配置"""
        return dict(self._strategies)

    def to_dict(self) -> Dict[str, Any]:
        """
        导出配置为字典格式（用于序列化）

        Returns:
            配置字典
        """
        result = {
            "preset": self._preset_name,
            "strategies": {}
        }
        for data_type, config in self._strategies.items():
            result["strategies"][data_type.value] = {
                "method": config.method.value,
                "md_min_level": config.md_min_level,
                "md_max_level": config.md_max_level,
                "min_chunk_length": config.min_chunk_length,
                "max_chunk_length": config.max_chunk_length,
                "add_context_prefix": config.add_context_prefix,
                "fixed_chunk_size": config.fixed_chunk_size,
                "chunk_overlap": config.chunk_overlap,
                # 语义分块参数
                "semantic_gate_threshold": config.semantic_gate_threshold,
                "semantic_alpha": config.semantic_alpha,
                "semantic_gamma": config.semantic_gamma,
                "semantic_min_sentences": config.semantic_min_sentences,
                "semantic_max_sentences": config.semantic_max_sentences,
                "extra": config.extra,
            }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkStrategyManager":
        """
        从字典创建策略管理器

        Args:
            data: 配置字典

        Returns:
            策略管理器实例
        """
        preset = data.get("preset", "optimized")
        manager = cls(preset=preset)

        # 覆盖自定义配置
        strategies = data.get("strategies", {})
        for type_str, config_dict in strategies.items():
            try:
                data_type = CodingDataType(type_str)
                config = ChunkConfig(
                    method=ChunkMethod(config_dict.get("method", "simple")),
                    md_min_level=config_dict.get("md_min_level", 2),
                    md_max_level=config_dict.get("md_max_level", 3),
                    min_chunk_length=config_dict.get("min_chunk_length", 100),
                    max_chunk_length=config_dict.get("max_chunk_length", 2000),
                    add_context_prefix=config_dict.get("add_context_prefix", False),
                    fixed_chunk_size=config_dict.get("fixed_chunk_size", 500),
                    chunk_overlap=config_dict.get("chunk_overlap", 50),
                    # 语义分块参数
                    semantic_gate_threshold=config_dict.get("semantic_gate_threshold", 0.3),
                    semantic_alpha=config_dict.get("semantic_alpha", 0.1),
                    semantic_gamma=config_dict.get("semantic_gamma", 1.1),
                    semantic_min_sentences=config_dict.get("semantic_min_sentences", 2),
                    semantic_max_sentences=config_dict.get("semantic_max_sentences", 20),
                    extra=config_dict.get("extra", {}),
                )
                manager.set_config(data_type, config)
            except (ValueError, KeyError):
                pass

        return manager


# 全局默认策略管理器实例
_default_manager: Optional[ChunkStrategyManager] = None


def get_strategy_manager() -> ChunkStrategyManager:
    """
    获取全局策略管理器实例

    默认使用 "optimized" 预设，启用语义动态规划分块等优化策略。

    Returns:
        策略管理器实例
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = ChunkStrategyManager(preset="optimized")
    return _default_manager


def set_strategy_manager(manager: ChunkStrategyManager):
    """
    设置全局策略管理器实例

    Args:
        manager: 策略管理器实例
    """
    global _default_manager
    _default_manager = manager


def switch_global_preset(preset: str):
    """
    切换全局预设策略

    Args:
        preset: 预设策略名称
    """
    get_strategy_manager().switch_preset(preset)


__all__ = [
    "ChunkMethod",
    "ChunkConfig",
    "ChunkStrategyManager",
    "DEFAULT_STRATEGIES",
    "OPTIMIZED_STRATEGIES",
    "get_strategy_manager",
    "set_strategy_manager",
    "switch_global_preset",
]
