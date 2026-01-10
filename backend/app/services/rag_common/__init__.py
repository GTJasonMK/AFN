"""
RAG通用模块

提供小说系统和编程系统共用的RAG相关功能。
"""

from .semantic_chunker import (
    SemanticChunkConfig,
    ChunkResult,
    SemanticChunker,
    get_semantic_chunker,
    set_semantic_chunker,
)

__all__ = [
    "SemanticChunkConfig",
    "ChunkResult",
    "SemanticChunker",
    "get_semantic_chunker",
    "set_semantic_chunker",
]
