"""
语义分块配置的通用默认参数

用于在 Coding/Novel 两套 ChunkConfig 之间复用语义分块相关字段，避免并行维护与参数漂移。
"""

from dataclasses import dataclass


@dataclass
class SemanticChunkConfigMixin:
    """语义分块相关配置（默认值）"""

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


__all__ = ["SemanticChunkConfigMixin"]

