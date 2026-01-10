"""
语义分块算法

基于句子嵌入相似度和动态规划的智能文本分块算法。
核心思想：
1. 将文本切分为句子序列
2. 计算句子间的语义相似度矩阵
3. 应用结构增强（距离加权）
4. 使用动态规划找到最优切分点
5. 回溯生成最终的文本块
"""

import re
import math
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SemanticChunkConfig:
    """语义分块配置"""

    # 门控阈值：相似度低于此值不进行距离增强
    gate_threshold: float = 0.3

    # 距离增强系数
    alpha: float = 0.1

    # 长度归一化指数（1.0-1.5之间，防止块过大或过小）
    gamma: float = 1.1

    # 最小块大小（句子数）
    min_chunk_sentences: int = 2

    # 最大块大小（句子数）
    max_chunk_sentences: int = 20

    # 最小块字符长度
    min_chunk_chars: int = 100

    # 最大块字符长度
    max_chunk_chars: int = 1500

    # 是否添加重叠
    with_overlap: bool = False

    # 重叠句子数
    overlap_sentences: int = 1


@dataclass
class ChunkResult:
    """分块结果"""
    content: str                    # 块内容
    start_sentence_idx: int         # 起始句子索引
    end_sentence_idx: int           # 结束句子索引（不包含）
    sentence_count: int             # 句子数量
    density_score: float            # 密度得分
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticChunker:
    """
    语义分块器

    使用句子嵌入和动态规划实现智能文本分块，
    最大化块内语义相关度，最小化块间相关度。
    """

    # 中文句子分隔符（不包括引号内的）
    CN_SENTENCE_DELIMITERS = r'[。！？；\n]+'
    # 英文句子分隔符
    EN_SENTENCE_DELIMITERS = r'[.!?;]+\s+'
    # 混合分隔符（简单版本）
    MIXED_DELIMITERS = r'[。！？；.!?\n]+\s*'

    # 小说文本专用分句模式
    # 处理：引号内对话、省略号、破折号等
    NOVEL_SENTENCE_PATTERN = re.compile(
        r'(?<=[。！？；…」』"\'）\)])\s*(?![，、：；])|'  # 中文句末标点后（排除逗号等）
        r'(?<=[.!?])\s+(?=[A-Z"\'（「『])|'  # 英文句末后跟大写字母或引号
        r'(?<=\n)\s*(?=\S)'  # 换行后
    )

    def __init__(
        self,
        config: Optional[SemanticChunkConfig] = None,
        embedding_func: Optional[Callable[[List[str]], np.ndarray]] = None
    ):
        """
        初始化语义分块器

        Args:
            config: 分块配置
            embedding_func: 嵌入函数，接受句子列表返回嵌入矩阵
        """
        self.config = config or SemanticChunkConfig()
        self.embedding_func = embedding_func

    def set_embedding_func(self, func: Callable[[List[str]], np.ndarray]):
        """设置嵌入函数"""
        self.embedding_func = func

    async def chunk_text_async(
        self,
        text: str,
        embedding_func: Optional[Callable] = None,
        config: Optional[SemanticChunkConfig] = None
    ) -> List[ChunkResult]:
        """
        异步分块文本

        Args:
            text: 要分块的文本
            embedding_func: 异步嵌入函数（可选，覆盖默认）
            config: 分块配置（可选，覆盖默认）

        Returns:
            分块结果列表
        """
        cfg = config or self.config
        emb_func = embedding_func or self.embedding_func

        if not emb_func:
            raise ValueError("未提供嵌入函数")

        # Step 1: 分句
        sentences = self._split_sentences(text)
        if len(sentences) <= cfg.min_chunk_sentences:
            # 句子太少，整体返回
            return [ChunkResult(
                content=text.strip(),
                start_sentence_idx=0,
                end_sentence_idx=len(sentences),
                sentence_count=len(sentences),
                density_score=1.0,
            )]

        # Step 2: 获取嵌入向量
        # 过滤空句子
        valid_sentences = [s for s in sentences if s.strip()]
        if len(valid_sentences) < 2:
            return [ChunkResult(
                content=text.strip(),
                start_sentence_idx=0,
                end_sentence_idx=len(sentences),
                sentence_count=len(sentences),
                density_score=1.0,
            )]

        try:
            embeddings = await emb_func(valid_sentences)
            if embeddings is None or len(embeddings) == 0:
                logger.warning("嵌入函数返回空结果，使用简单分块")
                return self._fallback_chunk(text, cfg)
        except Exception as e:
            logger.warning("获取嵌入失败: %s，使用简单分块", str(e))
            return self._fallback_chunk(text, cfg)

        # 确保embeddings是numpy数组
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        # Step 3: 构建结构增强相关度矩阵
        sim_matrix = self._build_similarity_matrix(embeddings)
        enhanced_matrix = self._apply_structure_enhancement(sim_matrix, cfg)

        # Step 4: 计算二维前缀和
        prefix_sum = self._compute_prefix_sum(enhanced_matrix)

        # Step 5: 动态规划找最优切分
        n = len(valid_sentences)
        dp, path = self._dynamic_programming(
            n, prefix_sum, valid_sentences, cfg
        )

        # Step 6: 回溯获取切分点
        cut_points = self._backtrack(n, path)

        # Step 7: 生成分块结果
        results = self._generate_chunks(
            valid_sentences, cut_points, dp, prefix_sum, cfg
        )

        return results

    def chunk_text_sync(
        self,
        text: str,
        embeddings: np.ndarray,
        sentences: Optional[List[str]] = None,
        config: Optional[SemanticChunkConfig] = None
    ) -> List[ChunkResult]:
        """
        同步分块文本（已有嵌入向量）

        Args:
            text: 原始文本
            embeddings: 句子嵌入矩阵
            sentences: 句子列表（可选，不提供则自动分句）
            config: 分块配置

        Returns:
            分块结果列表
        """
        cfg = config or self.config

        # 分句
        if sentences is None:
            sentences = self._split_sentences(text)

        if len(sentences) <= cfg.min_chunk_sentences:
            return [ChunkResult(
                content=text.strip(),
                start_sentence_idx=0,
                end_sentence_idx=len(sentences),
                sentence_count=len(sentences),
                density_score=1.0,
            )]

        # 确保embeddings是numpy数组
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        # 构建结构增强相关度矩阵
        sim_matrix = self._build_similarity_matrix(embeddings)
        enhanced_matrix = self._apply_structure_enhancement(sim_matrix, cfg)

        # 计算二维前缀和
        prefix_sum = self._compute_prefix_sum(enhanced_matrix)

        # 动态规划找最优切分
        n = len(sentences)
        dp, path = self._dynamic_programming(n, prefix_sum, sentences, cfg)

        # 回溯获取切分点
        cut_points = self._backtrack(n, path)

        # 生成分块结果
        results = self._generate_chunks(sentences, cut_points, dp, prefix_sum, cfg)

        return results

    def _split_sentences(self, text: str, novel_mode: bool = True) -> List[str]:
        """
        分句

        Args:
            text: 原始文本
            novel_mode: 是否使用小说专用分句模式

        Returns:
            句子列表
        """
        if not text or not text.strip():
            return []

        if novel_mode:
            # 小说模式：更智能的分句
            return self._split_sentences_novel(text)
        else:
            # 简单模式：正则分句
            sentences = re.split(self.MIXED_DELIMITERS, text)
            result = []
            for s in sentences:
                s = s.strip()
                if s and len(s) > 1:
                    result.append(s)
            return result

    def _split_sentences_novel(self, text: str) -> List[str]:
        """
        小说文本专用分句

        智能处理：
        - 引号内的对话（"你好。"作为整体）
        - 省略号（……）
        - 破折号（——）
        - 段落换行

        Args:
            text: 小说文本

        Returns:
            句子列表
        """
        sentences = []

        # 首先按段落分割（双换行或单换行后跟非空白字符）
        paragraphs = re.split(r'\n\s*\n|\n(?=\S)', text)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 对每个段落进行句子分割
            para_sentences = self._split_paragraph_to_sentences(para)
            sentences.extend(para_sentences)

        return sentences

    def _split_paragraph_to_sentences(self, paragraph: str) -> List[str]:
        """
        将单个段落分割为句子

        Args:
            paragraph: 段落文本

        Returns:
            句子列表
        """
        if not paragraph:
            return []

        sentences = []
        current = ""
        i = 0

        # 追踪引号状态
        in_chinese_quote = False  # "..." 或 「...」 或 『...』
        in_english_quote = False  # "..." 或 '...'

        while i < len(paragraph):
            char = paragraph[i]
            current += char

            # 检测中文开引号
            if char in '"「『':
                in_chinese_quote = True
            # 检测中文闭引号
            elif char in '"」』':
                in_chinese_quote = False
            # 检测英文引号（需要上下文判断）
            elif char == '"' or char == "'":
                # 简单处理：交替状态
                if char == '"':
                    in_english_quote = not in_english_quote

            # 判断是否是句子结束（不在引号内）
            is_end = False

            if not in_chinese_quote and not in_english_quote:
                # 中文句末标点
                if char in '。！？':
                    # 检查下一个字符是否是闭引号
                    next_char = paragraph[i + 1] if i + 1 < len(paragraph) else ''
                    if next_char not in '"」』"\'':
                        is_end = True
                # 分号（可选择是否分句）
                elif char == '；':
                    is_end = True

            # 闭引号后检查
            if char in '"」』"\'' and not in_chinese_quote and not in_english_quote:
                # 检查引号前是否有句末标点
                if len(current) >= 2 and current[-2] in '。！？':
                    is_end = True

            # 省略号后（必须是两个连续的…）
            if char == '…' and len(current) >= 2 and current[-2] == '…':
                next_char = paragraph[i + 1] if i + 1 < len(paragraph) else ''
                if next_char not in '。！？"」』':
                    # 省略号后不是标点或引号，考虑分句
                    if not in_chinese_quote and not in_english_quote:
                        is_end = True

            if is_end:
                sentence = current.strip()
                if sentence and len(sentence) >= 2:
                    sentences.append(sentence)
                current = ""

            i += 1

        # 处理剩余内容
        if current.strip() and len(current.strip()) >= 2:
            sentences.append(current.strip())

        # 对超长句子进行二次分割
        final_sentences = []
        for sent in sentences:
            if len(sent) > 200:  # 超过200字的句子尝试二次分割
                sub_sentences = self._split_long_sentence(sent)
                final_sentences.extend(sub_sentences)
            else:
                final_sentences.append(sent)

        return final_sentences

    def _split_long_sentence(self, sentence: str, max_len: int = 150) -> List[str]:
        """
        对超长句子进行二次分割

        按逗号、顿号等次级标点分割

        Args:
            sentence: 长句子
            max_len: 最大长度

        Returns:
            分割后的句子列表
        """
        if len(sentence) <= max_len:
            return [sentence]

        # 尝试按逗号、顿号分割
        parts = re.split(r'([，,、：:]+)', sentence)

        result = []
        current = ""

        for i, part in enumerate(parts):
            if i % 2 == 1:  # 分隔符
                current += part
            else:  # 内容
                if len(current) + len(part) <= max_len:
                    current += part
                else:
                    if current.strip():
                        result.append(current.strip())
                    current = part

        if current.strip():
            result.append(current.strip())

        # 如果分割后只有一个结果，说明没法分割，直接返回原句
        if len(result) <= 1:
            return [sentence]

        return result

    def _build_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """
        构建余弦相似度矩阵

        Args:
            embeddings: 句子嵌入矩阵 [N, D]

        Returns:
            相似度矩阵 [N, N]
        """
        # 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # 避免除零
        normalized = embeddings / norms

        # 计算余弦相似度矩阵
        sim_matrix = np.dot(normalized, normalized.T)

        return sim_matrix

    def _apply_structure_enhancement(
        self,
        sim_matrix: np.ndarray,
        config: SemanticChunkConfig
    ) -> np.ndarray:
        """
        应用结构增强（距离加权）

        公式：
        M'[i,j] = M[i,j] + alpha * M[i,j] * ln(1+d)  if M[i,j] > tau
        M'[i,j] = M[i,j]                              else

        Args:
            sim_matrix: 原始相似度矩阵
            config: 配置

        Returns:
            增强后的矩阵
        """
        n = sim_matrix.shape[0]
        enhanced = sim_matrix.copy()

        # 创建距离矩阵
        i_indices, j_indices = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
        distance_matrix = np.abs(j_indices - i_indices)

        # 计算增强因子: alpha * ln(1 + d)
        enhancement_factor = config.alpha * np.log1p(distance_matrix)

        # 创建门控掩码：只对高于阈值的相似度应用增强
        gate_mask = sim_matrix > config.gate_threshold

        # 应用增强（只在上三角，因为是对称矩阵）
        upper_mask = j_indices > i_indices

        # 对有效信号应用距离加权增强
        enhanced = np.where(
            gate_mask & upper_mask,
            sim_matrix + sim_matrix * enhancement_factor,
            sim_matrix
        )

        # 保持对称性
        enhanced = np.triu(enhanced) + np.triu(enhanced, 1).T

        return enhanced

    def _compute_prefix_sum(self, matrix: np.ndarray) -> np.ndarray:
        """
        计算二维前缀和（积分图）

        Args:
            matrix: 输入矩阵 [N, N]

        Returns:
            前缀和矩阵 [N+1, N+1]
        """
        n = matrix.shape[0]
        prefix = np.zeros((n + 1, n + 1), dtype=np.float64)

        for i in range(1, n + 1):
            for j in range(1, n + 1):
                prefix[i][j] = (
                    matrix[i - 1][j - 1]
                    + prefix[i - 1][j]
                    + prefix[i][j - 1]
                    - prefix[i - 1][j - 1]
                )

        return prefix

    def _sum_region(
        self,
        prefix: np.ndarray,
        r1: int, c1: int,
        r2: int, c2: int
    ) -> float:
        """
        计算子矩阵和（O(1)时间）

        Args:
            prefix: 前缀和矩阵
            r1, c1: 左上角坐标
            r2, c2: 右下角坐标

        Returns:
            子矩阵元素和
        """
        return (
            prefix[r2 + 1][c2 + 1]
            - prefix[r1][c2 + 1]
            - prefix[r2 + 1][c1]
            + prefix[r1][c1]
        )

    def _block_score(
        self,
        prefix: np.ndarray,
        start: int,
        end: int,
        gamma: float
    ) -> float:
        """
        计算块得分

        Score = SumRegion(start, start, end-1, end-1) / (end-start)^gamma

        Args:
            prefix: 前缀和矩阵
            start: 块起始索引
            end: 块结束索引（不包含）
            gamma: 长度归一化指数

        Returns:
            块得分
        """
        if end <= start:
            return 0.0

        length = end - start
        region_sum = self._sum_region(prefix, start, start, end - 1, end - 1)

        # 长度归一化
        score = region_sum / (length ** gamma)

        return score

    def _dynamic_programming(
        self,
        n: int,
        prefix: np.ndarray,
        sentences: List[str],
        config: SemanticChunkConfig
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        动态规划找最优切分

        DP[i] = max{ DP[j] + BlockScore(j, i) } for all valid j

        Args:
            n: 句子数量
            prefix: 前缀和矩阵
            sentences: 句子列表
            config: 配置

        Returns:
            (DP数组, 路径数组)
        """
        dp = np.zeros(n + 1, dtype=np.float64)
        path = np.zeros(n + 1, dtype=np.int32)

        # 预计算每个句子的字符长度累积和
        char_lengths = [0]
        for s in sentences:
            char_lengths.append(char_lengths[-1] + len(s))

        min_sents = config.min_chunk_sentences
        max_sents = config.max_chunk_sentences

        logger.debug(
            "DP参数: n=%d, min_sentences=%d, max_sentences=%d, min_chars=%d, max_chars=%d",
            n, min_sents, max_sents, config.min_chunk_chars, config.max_chunk_chars
        )

        for i in range(1, n + 1):
            best_score = float('-inf')
            best_j = -1

            # 块大小 = i - j，约束: min_sents <= i - j <= max_sents
            # 所以 j 的范围: i - max_sents <= j <= i - min_sents
            j_min = max(0, i - max_sents)
            j_max = i - min_sents  # 可能为负数

            # 只有当 j_max >= 0 时才能形成有效块
            if j_max >= 0:
                # 第一阶段：严格遵守句子数和字符数约束
                for j in range(j_min, j_max + 1):
                    chunk_chars = char_lengths[i] - char_lengths[j]

                    # 检查字符长度约束（最后一块可以短一些）
                    if chunk_chars < config.min_chunk_chars and i < n:
                        continue
                    if chunk_chars > config.max_chunk_chars:
                        continue

                    score = dp[j] + self._block_score(prefix, j, i, config.gamma)

                    if score > best_score:
                        best_score = score
                        best_j = j

                # 第二阶段：放宽字符约束，保持句子数约束
                if best_j < 0:
                    for j in range(j_min, j_max + 1):
                        score = dp[j] + self._block_score(prefix, j, i, config.gamma)
                        if score > best_score:
                            best_score = score
                            best_j = j

            # 如果还是找不到（i < min_sents），标记为"未完成块"
            # path[i] = -1 表示在位置 i 不切分，继续累积
            if best_j < 0:
                # 继承前一个位置的状态
                dp[i] = dp[i - 1]
                path[i] = -1  # 标记为不切分
                logger.debug("DP[%d]: 句子数不足，继续累积 (需要 %d 句)", i, min_sents)
            else:
                dp[i] = best_score
                path[i] = best_j
                logger.debug(
                    "DP[%d] = %.4f, 切分点 = %d, 块大小 = %d",
                    i, dp[i], best_j, i - best_j
                )

        return dp, path

    def _backtrack(self, n: int, path: np.ndarray) -> List[int]:
        """
        回溯获取切分点

        Args:
            n: 句子数量
            path: 路径数组

        Returns:
            切分点列表（升序）
        """
        cut_points = []
        k = n

        # 添加终点
        cut_points.append(n)

        while k > 0:
            if path[k] == -1:
                # 未切分标记，继续向前
                k -= 1
            elif path[k] >= 0:
                if path[k] > 0:
                    cut_points.append(path[k])
                k = path[k]
            else:
                k -= 1

        cut_points.append(0)
        cut_points = list(set(cut_points))  # 去重
        cut_points.sort()

        return cut_points

    def _generate_chunks(
        self,
        sentences: List[str],
        cut_points: List[int],
        dp: np.ndarray,
        prefix: np.ndarray,
        config: SemanticChunkConfig
    ) -> List[ChunkResult]:
        """
        根据切分点生成分块结果

        Args:
            sentences: 句子列表
            cut_points: 切分点列表
            dp: DP数组
            prefix: 前缀和矩阵
            config: 配置

        Returns:
            分块结果列表
        """
        results = []

        for i in range(len(cut_points) - 1):
            start = cut_points[i]
            end = cut_points[i + 1]

            if start >= end:
                continue

            # 合并句子
            chunk_sentences = sentences[start:end]

            # 添加重叠（如果配置了且不是第一个块）
            if config.with_overlap and i > 0 and config.overlap_sentences > 0:
                overlap_start = max(0, start - config.overlap_sentences)
                overlap_sentences = sentences[overlap_start:start]
                if overlap_sentences:
                    chunk_content = "[...] " + "。".join(overlap_sentences) + "。\n\n"
                    chunk_content += "。".join(chunk_sentences)
                else:
                    chunk_content = "。".join(chunk_sentences)
            else:
                chunk_content = "。".join(chunk_sentences)

            # 确保内容以句号结尾
            if chunk_content and not chunk_content.endswith(('。', '！', '？', '.', '!', '?')):
                chunk_content += '。'

            # 计算密度得分
            density = self._block_score(prefix, start, end, config.gamma)

            results.append(ChunkResult(
                content=chunk_content,
                start_sentence_idx=start,
                end_sentence_idx=end,
                sentence_count=end - start,
                density_score=density,
                metadata={
                    'chunk_index': i,
                    'total_chunks': len(cut_points) - 1,
                }
            ))

        return results

    def _fallback_chunk(
        self,
        text: str,
        config: SemanticChunkConfig
    ) -> List[ChunkResult]:
        """
        降级分块（当嵌入失败时使用）

        使用简单的段落/长度分割

        Args:
            text: 原始文本
            config: 配置

        Returns:
            分块结果列表
        """
        # 按段落分割
        paragraphs = re.split(r'\n\s*\n', text)
        results = []
        current_chunk = ""
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) <= config.max_chunk_chars:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para
            else:
                if current_chunk:
                    results.append(ChunkResult(
                        content=current_chunk,
                        start_sentence_idx=0,
                        end_sentence_idx=0,
                        sentence_count=0,
                        density_score=0.0,
                        metadata={'chunk_index': chunk_idx, 'fallback': True}
                    ))
                    chunk_idx += 1
                current_chunk = para

        if current_chunk:
            results.append(ChunkResult(
                content=current_chunk,
                start_sentence_idx=0,
                end_sentence_idx=0,
                sentence_count=0,
                density_score=0.0,
                metadata={'chunk_index': chunk_idx, 'fallback': True}
            ))

        return results if results else [ChunkResult(
            content=text.strip(),
            start_sentence_idx=0,
            end_sentence_idx=0,
            sentence_count=0,
            density_score=0.0,
            metadata={'fallback': True}
        )]


# 全局默认实例
_default_chunker: Optional[SemanticChunker] = None


def get_semantic_chunker() -> SemanticChunker:
    """获取全局语义分块器实例"""
    global _default_chunker
    if _default_chunker is None:
        _default_chunker = SemanticChunker()
    return _default_chunker


def set_semantic_chunker(chunker: SemanticChunker):
    """设置全局语义分块器实例"""
    global _default_chunker
    _default_chunker = chunker


__all__ = [
    "SemanticChunkConfig",
    "ChunkResult",
    "SemanticChunker",
    "get_semantic_chunker",
    "set_semantic_chunker",
]
