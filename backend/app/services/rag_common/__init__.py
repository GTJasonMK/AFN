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
from .ingestion_base import (
    IngestionResult,
    TypeChangeDetail,
    CompletenessReport,
    BaseProjectIngestionService,
)
from .auto_ingestion import run_ingestion_task
from .markdown_splitter import split_markdown_sections
from .chunk_strategy_base import (
    BaseChunkStrategyManager,
    build_chunk_config,
    clone_chunk_config,
    serialize_chunk_config,
)

__all__ = [
    "SemanticChunkConfig",
    "ChunkResult",
    "SemanticChunker",
    "get_semantic_chunker",
    "set_semantic_chunker",
    "IngestionResult",
    "TypeChangeDetail",
    "CompletenessReport",
    "BaseProjectIngestionService",
    "run_ingestion_task",
    "split_markdown_sections",
    "BaseChunkStrategyManager",
    "build_chunk_config",
    "clone_chunk_config",
    "serialize_chunk_config",
]
