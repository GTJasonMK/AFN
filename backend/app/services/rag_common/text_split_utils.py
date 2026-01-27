"""RAG 文本分割通用工具（收敛重复小逻辑，避免策略漂移）"""

from __future__ import annotations

_SENTENCE_END_CHARS = ("。", "？", "！", ".", "?", "!")


def sentence_boundary_cut_length(chunk: str, chunk_size: int, *, min_ratio: float = 0.5) -> int | None:
    """根据句子边界建议截断长度（cut_len）"""
    if not chunk:
        return None
    last_sentence_end = max(chunk.rfind(ch) for ch in _SENTENCE_END_CHARS)
    return (last_sentence_end + 1) if last_sentence_end > chunk_size * min_ratio else None
