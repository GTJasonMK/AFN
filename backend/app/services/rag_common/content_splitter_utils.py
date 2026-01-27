"""
内容分割器公共工具

目标：收敛 Coding/Novel 两套内容分割器中可安全共享的“纯逻辑骨架”，避免策略漂移。
本文件只提供通用 helper，不引入业务数据类型（CodingDataType/NovelDataType）。
"""

from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple

from .text_split_utils import sentence_boundary_cut_length
from .markdown_splitter import split_markdown_sections

_SENTENCE_END_CHARS = ("。", "？", "！", ".", "?", "!")


def split_fixed_length_chunks(content: str, *, chunk_size: int, overlap: int) -> List[str]:
    """按固定长度分割文本（支持重叠与句子边界截断）

    说明：
    - 去除首尾空白后进行分割
    - 若 chunk 不是最后一段，会尝试在句子边界处“向左截断”，减少硬截断带来的语义断裂
    - overlap 会在每次推进时回退对应字符数，保持上下文连贯
    """
    if not content or not content.strip():
        return []

    normalized = content.strip()
    size = max(1, int(chunk_size))
    ov = max(0, int(overlap))
    if ov >= size:
        ov = max(0, size - 1)

    chunks: List[str] = []
    start = 0
    while start < len(normalized):
        end = start + size
        chunk = normalized[start:end]

        # 尝试在句子边界截断（仅对非最后一段）
        if end < len(normalized):
            cut_len = sentence_boundary_cut_length(chunk, size)
            if cut_len is not None:
                chunk = chunk[:cut_len]
                end = start + cut_len

        stripped = chunk.strip()
        if stripped:
            chunks.append(stripped)

        start = end - ov if end < len(normalized) else end

    return chunks


def _choose_overlap_text(prev_chunk: str, *, overlap_length: int) -> str:
    """从上一块尾部选择 overlap 文本（尽量对齐句末标点）。"""
    if not prev_chunk or overlap_length <= 0:
        return ""

    if len(prev_chunk) <= overlap_length:
        return ""

    overlap_start = len(prev_chunk) - overlap_length
    # 优先选“重叠区内第一个句末标点之后”的内容，减少句子被截断的概率
    for punct in _SENTENCE_END_CHARS:
        pos = prev_chunk.find(punct, overlap_start)
        if pos != -1 and pos < len(prev_chunk) - 10:
            overlap_text = prev_chunk[pos + 1 :].strip()
            if overlap_text:
                return overlap_text

    return prev_chunk[overlap_start:].strip()


def _add_overlap_prefix(chunks: List[str], *, overlap_length: int) -> List[str]:
    """为 chunks 添加重叠前缀（第 2 块起在开头追加上一块尾部内容）。"""
    if len(chunks) <= 1 or overlap_length <= 0:
        return chunks

    result = [chunks[0]]
    for idx in range(1, len(chunks)):
        overlap_text = _choose_overlap_text(chunks[idx - 1], overlap_length=overlap_length)
        if overlap_text:
            result.append(f"[...] {overlap_text}\n\n{chunks[idx]}")
        else:
            result.append(chunks[idx])

    return result


def split_paragraph_chunks(
    content: str,
    *,
    min_length: int,
    max_length: int,
    with_overlap: bool,
    overlap_length: int,
) -> List[str]:
    """按段落分割文本，返回 chunk 列表（支持重叠）。

    规则：
    - 以空行作为段落边界；尽量合并相邻段落使 chunk 不超过 max_length；
    - 单段超过 max_length 时，优先在句末标点边界向左截断，否则硬截断；
    - with_overlap=True 时，在后续 chunk 开头追加上一 chunk 尾部片段（`"[...] "` 前缀）；
    - 不丢内容：不会因为“过短段落”直接丢弃。
    """
    if not content or not content.strip():
        return []

    normalized = content.strip()
    min_len = max(0, int(min_length or 0))
    max_len = max(1, int(max_length or 1))
    overlap_len = max(0, int(overlap_length or 0))
    if overlap_len >= max_len:
        overlap_len = max(0, max_len - 1)

    paragraphs = re.split(r"\n\s*\n", normalized)
    paragraphs = [p.strip() for p in paragraphs if p and p.strip()]
    if not paragraphs:
        return []

    # 1) 合并段落（尽量不超过 max_len）
    merged: List[str] = []
    current = ""
    for para in paragraphs:
        if not current:
            current = para
            continue

        candidate = f"{current}\n\n{para}"
        if len(candidate) <= max_len:
            current = candidate
        else:
            merged.append(current)
            current = para

    if current:
        merged.append(current)

    # 2) 强制切分过长 chunk（单段/合并段落仍可能超限）
    chunks: List[str] = []
    for text in merged:
        rest = text.strip()
        while len(rest) > max_len:
            segment = rest[:max_len]
            cut_len = sentence_boundary_cut_length(segment, max_len)
            if cut_len is None:
                cut_len = max_len

            part = rest[:cut_len].strip()
            if part:
                chunks.append(part)

            rest = rest[cut_len:].strip()

        if rest:
            chunks.append(rest)

    # 3) 尝试合并过短尾块（不强制，避免破坏 max_len 约束）
    if (
        min_len > 0
        and len(chunks) > 1
        and len(chunks[-1]) < min_len
        and (len(chunks[-2]) + 2 + len(chunks[-1]) <= max_len)
    ):
        chunks[-2] = f"{chunks[-2]}\n\n{chunks[-1]}".strip()
        chunks.pop()

    # 4) 添加重叠
    if with_overlap and overlap_len > 0 and len(chunks) > 1:
        chunks = _add_overlap_prefix(chunks, overlap_length=overlap_len)

    return chunks


def build_paragraph_chunk_records(
    *,
    content: str,
    min_length: int,
    max_length: int,
    with_overlap: bool,
    overlap_length: int,
    add_context_prefix: bool,
    parent_title: Optional[str],
    extra_metadata: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    """paragraph 分块：返回 (chunk_content, metadata) 列表，供上层包装为具体 Record 类型。"""
    chunks = split_paragraph_chunks(
        content,
        min_length=min_length,
        max_length=max_length,
        with_overlap=with_overlap,
        overlap_length=overlap_length,
    )
    if not chunks:
        return []

    total_sections = len(chunks)
    records: List[Tuple[str, Dict[str, Any]]] = []
    for idx, chunk in enumerate(chunks):
        chunk_content = apply_context_prefix(chunk, enabled=add_context_prefix, parent_title=parent_title)
        records.append(
            (
                chunk_content,
                {
                    "section_index": idx,
                    "total_sections": total_sections,
                    **(extra_metadata or {}),
                },
            )
        )

    return records


def build_semantic_chunk_config(
    strategy_config: Any,
    *,
    with_overlap: bool,
    overlap_sentences: int,
) -> Any:
    """从策略配置构建 SemanticChunkConfig

    这里使用 duck-typing：strategy_config 需要提供 semantic_* 与 min/max_chunk_* 字段。
    """
    from .semantic_chunker import SemanticChunkConfig

    return SemanticChunkConfig(
        gate_threshold=strategy_config.semantic_gate_threshold,
        alpha=strategy_config.semantic_alpha,
        gamma=strategy_config.semantic_gamma,
        min_chunk_sentences=strategy_config.semantic_min_sentences,
        max_chunk_sentences=strategy_config.semantic_max_sentences,
        min_chunk_chars=strategy_config.min_chunk_length,
        max_chunk_chars=strategy_config.max_chunk_length,
        with_overlap=with_overlap,
        overlap_sentences=overlap_sentences,
    )


async def semantic_chunk_text_async(
    *,
    text: str,
    embedding_func: Callable[[List[str]], Awaitable[Any]],
    semantic_config: Any,
) -> Any:
    """执行语义分块（延迟导入避免循环依赖）"""
    from .semantic_chunker import SemanticChunker

    chunker = SemanticChunker(config=semantic_config)
    return await chunker.chunk_text_async(
        text=text,
        embedding_func=embedding_func,
        config=semantic_config,
    )


def iter_qa_rounds(conversations: List[Dict[str, Any]]) -> Iterable[List[Dict[str, Any]]]:
    """将对话列表按“user 开启新轮次 + assistant 归入当前轮次”的规则切分为轮次列表"""
    current_round: List[Dict[str, Any]] = []

    for conv in conversations:
        role = conv.get("role", "")
        if role == "user":
            if current_round:
                yield current_round
            current_round = [conv]
        elif role == "assistant" and current_round:
            current_round.append(conv)

    if current_round:
        yield current_round


def build_qa_round_text(round_convs: List[Dict[str, Any]]) -> Tuple[str, int, int]:
    """将一轮对话拼装为文本，并返回 (merged_content, start_seq, message_count)"""
    if not round_convs:
        return "", 0, 0

    parts: List[str] = []
    start_seq = round_convs[0].get("seq", 0)

    for conv in round_convs:
        role = conv.get("role", "")
        content = conv.get("content", "")
        if role == "user":
            parts.append(f"用户: {content}")
        elif role == "assistant":
            parts.append(f"助手: {content}")

    merged_content = "\n\n".join(parts)
    return merged_content, start_seq, len(round_convs)


def build_semantic_chunk_metadata(
    *,
    idx: int,
    total_sections: int,
    chunk: Any,
    extra_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """构建语义分块的通用 metadata（用于 Coding/Novel 两套入库记录）。"""
    return {
        "section_index": idx,
        "total_sections": total_sections,
        "sentence_count": getattr(chunk, "sentence_count", None),
        "density_score": getattr(chunk, "density_score", None),
        "semantic_chunked": True,
        **(extra_metadata or {}),
    }


def apply_context_prefix(content: str, *, enabled: bool, parent_title: Optional[str]) -> str:
    """按 parent_title 添加上下文前缀（用于提升检索可解释性）"""
    if enabled and parent_title:
        return f"[{parent_title}]\n\n{content}"
    return content


def build_fixed_length_chunk_records(
    *,
    content: str,
    chunk_size: int,
    overlap: int,
    add_context_prefix: bool,
    parent_title: Optional[str],
    extra_metadata: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    """fixed_length 分块：返回 (chunk_content, metadata) 列表，供上层包装为具体 Record 类型。"""
    chunks = split_fixed_length_chunks(content, chunk_size=chunk_size, overlap=overlap)
    if not chunks:
        return []

    total_sections = len(chunks)
    records: List[Tuple[str, Dict[str, Any]]] = []
    for idx, chunk in enumerate(chunks):
        chunk_content = apply_context_prefix(chunk, enabled=add_context_prefix, parent_title=parent_title)
        records.append(
            (
                chunk_content,
                {
                    "section_index": idx,
                    "total_sections": total_sections,
                    **(extra_metadata or {}),
                },
            )
        )
    return records


def build_whole_chunk_records(
    *,
    content: str,
    add_context_prefix: bool,
    parent_title: Optional[str],
    extra_metadata: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    """whole 分块：返回单条 (chunk_content, metadata) 记录，供上层包装为具体 Record 类型。"""
    if not content or not content.strip():
        return []

    chunk_content = apply_context_prefix(content.strip(), enabled=add_context_prefix, parent_title=parent_title)
    return [
        (
            chunk_content,
            {
                "section_index": 0,
                "total_sections": 1,
                **(extra_metadata or {}),
            },
        )
    ]


def build_markdown_section_records(
    *,
    sections: List[Any],
    add_context_prefix: bool,
    parent_title: Optional[str],
    extra_metadata: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    """markdown_header 分块：返回 (chunk_content, metadata) 列表，供上层包装为具体 Record 类型。"""
    if not sections:
        return []

    total_sections = len(sections)
    records: List[Tuple[str, Dict[str, Any]]] = []
    for idx, section in enumerate(sections):
        title = getattr(section, "title", "") or ""
        content = getattr(section, "content", "") or ""
        section_content = f"## {title}\n\n{content}" if title else content
        chunk_content = apply_context_prefix(section_content, enabled=add_context_prefix, parent_title=parent_title)
        records.append(
            (
                chunk_content,
                {
                    "section_title": title,
                    "section_index": getattr(section, "index", idx),
                    "total_sections": total_sections,
                    **(extra_metadata or {}),
                },
            )
        )

    return records


async def build_semantic_chunk_records_async(
    *,
    content: str,
    embedding_func: Callable[[List[str]], Awaitable[Any]],
    strategy_config: Any,
    with_overlap: bool,
    overlap_sentences: int,
    add_context_prefix: bool,
    parent_title: Optional[str],
    extra_metadata: Dict[str, Any],
) -> List[Tuple[str, Dict[str, Any]]]:
    """semantic 分块：返回 (chunk_content, metadata) 列表，供上层包装为具体 Record 类型。"""
    if not content or not content.strip():
        return []

    semantic_config = build_semantic_chunk_config(
        strategy_config,
        with_overlap=with_overlap,
        overlap_sentences=overlap_sentences,
    )
    chunk_results = await semantic_chunk_text_async(
        text=content,
        embedding_func=embedding_func,
        semantic_config=semantic_config,
    )

    total_sections = len(chunk_results)
    records: List[Tuple[str, Dict[str, Any]]] = []
    for idx, chunk in enumerate(chunk_results):
        chunk_content = apply_context_prefix(
            chunk.content,
            enabled=add_context_prefix,
            parent_title=parent_title,
        )
        records.append(
            (
                chunk_content,
                build_semantic_chunk_metadata(
                    idx=idx,
                    total_sections=total_sections,
                    chunk=chunk,
                    extra_metadata=extra_metadata,
                ),
            )
        )
    return records


def split_by_markdown_headers(
    *,
    content: str,
    min_level: int,
    max_level: int,
    section_factory: Callable[..., Any],
) -> List[Any]:
    """按 Markdown 标题分割内容（薄封装，集中维护参数转发）。"""
    return split_markdown_sections(
        content=content,
        min_level=min_level,
        max_level=max_level,
        section_factory=section_factory,
    )
