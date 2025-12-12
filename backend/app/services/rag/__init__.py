"""
RAG增强模块

提供增强型的检索增强生成(RAG)功能，包括：
- 增强型查询构建
- 时序感知检索
- 智能上下文构建
- 上下文压缩
- 大纲RAG检索
- 公共工具函数
"""

from .query_builder import EnhancedQueryBuilder, EnhancedQuery
from .temporal_retriever import TemporalAwareRetriever
from .context_builder import SmartContextBuilder, GenerationContext, BlueprintInfo, RAGContext
from .context_compressor import ContextCompressor
from .outline_retriever import OutlineRAGRetriever, get_outline_rag_retriever
from .utils import (
    extract_involved_characters,
    truncate_text,
    build_outline_text,
    format_chapter_reference,
)

__all__ = [
    # 查询构建
    "EnhancedQueryBuilder",
    "EnhancedQuery",
    # 检索器
    "TemporalAwareRetriever",
    "OutlineRAGRetriever",
    "get_outline_rag_retriever",
    # 上下文
    "SmartContextBuilder",
    "GenerationContext",
    "BlueprintInfo",
    "RAGContext",
    "ContextCompressor",
    # 工具函数
    "extract_involved_characters",
    "truncate_text",
    "build_outline_text",
    "format_chapter_reference",
]
