"""
RAG增强模块

提供增强型的检索增强生成(RAG)功能，包括：
- 增强型查询构建
- 时序感知检索
- 智能上下文构建
- 上下文压缩
- 大纲RAG检索
- 场景状态提取
- 公共工具函数
"""

from .query_builder import EnhancedQueryBuilder, EnhancedQuery
from .temporal_retriever import TemporalAwareRetriever
from .context_builder import SmartContextBuilder, GenerationContext
from .context_compressor import ContextCompressor
from .outline_retriever import get_outline_rag_retriever

__all__ = [
    # 查询构建
    "EnhancedQueryBuilder",
    "EnhancedQuery",
    # 检索器
    "TemporalAwareRetriever",
    "get_outline_rag_retriever",
    # 上下文
    "SmartContextBuilder",
    "GenerationContext",
    "ContextCompressor",
]
