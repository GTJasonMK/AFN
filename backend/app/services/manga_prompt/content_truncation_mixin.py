"""
内容截断Mixin

提供智能内容截断、分段采样等功能，用于处理超长章节内容。
"""

import logging
import re
from typing import List

from ...core.config import settings

logger = logging.getLogger(__name__)


class ContentTruncationMixin:
    """内容截断相关方法的Mixin"""

    # Token/字符转换比率（用于更精确的估算）
    TOKEN_CHAR_RATIO_ZH = 1.5  # 中文：约1.5字符/token
    TOKEN_CHAR_RATIO_EN = 4.0  # 英文：约4字符/token
    TOKEN_CHAR_RATIO_MIXED = 2.0  # 混合：取中间值

    @property
    def CONTENT_LIMIT_SCENE_EXTRACTION(self) -> int:
        """场景提取使用的内容限制（字符数）"""
        return getattr(settings, 'manga_content_limit_scene', 12000)

    @property
    def CONTENT_LIMIT_FULL_PROMPT(self) -> int:
        """完整提示词生成使用的内容限制（字符数）"""
        return getattr(settings, 'manga_content_limit_prompt', 8000)

    @property
    def CONTENT_LIMIT_LAYOUT(self) -> int:
        """排版生成使用的内容限制（字符数）"""
        return getattr(settings, 'manga_content_limit_layout', 2000)

    @property
    def LONG_CHAPTER_THRESHOLD(self) -> int:
        """长章节阈值：超过此长度使用智能分段"""
        return getattr(settings, 'manga_long_chapter_threshold', 15000)

    def _truncate_content(
        self, content: str, max_chars: int, preserve_structure: bool = True
    ) -> str:
        """
        智能截断内容

        对于超长内容，采用分段采样策略而非简单首尾截断，
        确保中间的关键情节（如战斗、高潮）不会丢失。

        Args:
            content: 原始内容
            max_chars: 最大字符数
            preserve_structure: 是否保留首尾结构

        Returns:
            截断后的内容
        """
        if len(content) <= max_chars:
            return content

        original_length = len(content)

        # 对于超长章节，使用智能分段采样
        if original_length > self.LONG_CHAPTER_THRESHOLD and preserve_structure:
            return self._smart_segment_sampling(content, max_chars)

        if preserve_structure:
            # 标准的首尾保留策略
            head_size = max_chars // 2
            tail_size = max_chars // 2
            truncated = (
                f"{content[:head_size]}\n\n"
                f"[...内容过长，已省略中间约 {original_length - max_chars} 字...]\n\n"
                f"{content[-tail_size:]}"
            )
        else:
            # 简单截断，只保留开头
            truncated = (
                content[:max_chars]
                + f"\n\n[...内容已截断，原文共 {original_length} 字...]"
            )

        logger.debug(
            "内容已截断: 原始长度=%d, 截断后=%d, 限制=%d",
            original_length,
            len(truncated),
            max_chars,
        )
        return truncated

    def _smart_segment_sampling(self, content: str, max_chars: int) -> str:
        """
        智能分段采样

        将长文本按段落分割，然后均匀采样各部分的关键段落，
        确保故事的开头、中间、结尾都有代表性内容。

        策略：
        1. 按段落分割文本
        2. 根据段落数量动态调整区域划分
        3. 从每个区域选取最有视觉价值的段落
        4. 组装成最终文本

        Args:
            content: 原始内容
            max_chars: 最大字符数

        Returns:
            采样后的内容
        """
        # 按段落分割（双换行或单换行）
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 3:
            # 尝试单换行分割
            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]

        total_paragraphs = len(paragraphs)

        # 改进段落较少时的处理策略
        if total_paragraphs < 3:
            # 极少段落：使用句子级别分割
            return self._sentence_level_sampling(content, max_chars)

        if total_paragraphs < 5:
            # 较少段落：使用三区域策略（开头、中间、结尾）
            return self._three_region_sampling(paragraphs, max_chars)

        if total_paragraphs < 10:
            # 中等段落数：使用三区域策略但分配更均匀
            return self._three_region_sampling(paragraphs, max_chars, balanced=True)

        # 标准的五区域策略
        return self._five_region_sampling(paragraphs, max_chars)

    def _sentence_level_sampling(self, content: str, max_chars: int) -> str:
        """
        句子级别采样策略

        用于段落极少的情况，按句子分割后选择关键句子。
        """
        # 按句号、感叹号、问号分割（保留标点）
        sentences = re.split(r'([。！？!?])', content)
        # 重新组合句子和标点
        combined_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if sentences[i].strip():
                combined_sentences.append(
                    sentences[i].strip()
                    + (sentences[i + 1] if i + 1 < len(sentences) else '')
                )

        if not combined_sentences:
            # 无法分割，使用简单首尾截断
            head_size = max_chars * 2 // 3
            tail_size = max_chars // 3
            return (
                f"{content[:head_size]}\n\n"
                f"[...中间内容省略...]\n\n"
                f"{content[-tail_size:]}"
            )

        # 对句子评分并选择
        scored = [
            (s, self._score_paragraph_visual_value(s)) for s in combined_sentences
        ]

        # 分三部分：开头必选、结尾必选、中间按分数选
        total = len(scored)
        head_count = max(1, total // 5)  # 开头20%
        tail_count = max(1, total // 5)  # 结尾20%

        # 开头和结尾句子直接选取（按顺序）
        head_sentences = [s for s, _ in scored[:head_count]]
        tail_sentences = [s for s, _ in scored[-tail_count:]]

        # 中间句子按分数排序选取
        mid_pool = (
            scored[head_count:-tail_count] if tail_count > 0 else scored[head_count:]
        )
        mid_pool.sort(key=lambda x: x[1], reverse=True)

        # 计算剩余可用字符数
        used_chars = sum(len(s) for s in head_sentences) + sum(
            len(s) for s in tail_sentences
        )
        remaining = max_chars - used_chars - 100  # 留出标注空间

        mid_selected = []
        mid_chars = 0
        for sentence, score in mid_pool:
            if mid_chars + len(sentence) > remaining:
                break
            mid_selected.append(
                (
                    sentence,
                    (
                        combined_sentences.index(sentence)
                        if sentence in combined_sentences
                        else 999
                    ),
                )
            )
            mid_chars += len(sentence)

        # 按原顺序排列中间句子
        mid_selected.sort(key=lambda x: x[1])
        mid_sentences = [s for s, _ in mid_selected]

        # 组装结果
        result_parts = []
        if head_sentences:
            result_parts.append("【开篇】\n" + "".join(head_sentences))
        if mid_sentences:
            result_parts.append("【关键情节】\n" + "".join(mid_sentences))
        if tail_sentences:
            result_parts.append("【结局】\n" + "".join(tail_sentences))

        result = (
            f"[以下是章节关键内容采样，原文共 {len(content)} 字]\n\n"
            + "\n\n".join(result_parts)
        )

        logger.info(
            "句子级采样: 原始长度=%d, 采样后=%d, 句子数=%d",
            len(content),
            len(result),
            len(combined_sentences),
        )

        return result

    def _three_region_sampling(
        self,
        paragraphs: List[str],
        max_chars: int,
        balanced: bool = False,
    ) -> str:
        """
        三区域采样策略

        用于段落数在3-9之间的情况。
        """
        total = len(paragraphs)

        # 分配比例
        if balanced:
            # 均衡分配：开头30%，中间40%，结尾30%
            allocations = [0.30, 0.40, 0.30]
        else:
            # 首尾优先：开头35%，中间25%，结尾40%
            allocations = [0.35, 0.25, 0.40]

        region_limits = [int(max_chars * a) for a in allocations]

        # 划分区域
        if total < 6:
            # 段落较少时，各取1/3
            region_size = total // 3
            regions = [
                paragraphs[: region_size + 1],
                (
                    paragraphs[region_size + 1 : -region_size - 1]
                    if total > 3
                    else []
                ),
                (
                    paragraphs[-region_size - 1 :]
                    if region_size > 0
                    else paragraphs[-1:]
                ),
            ]
        else:
            region_size = total // 3
            regions = [
                paragraphs[:region_size],
                paragraphs[region_size : total - region_size],
                paragraphs[total - region_size :],
            ]

        region_labels = ['【开篇】', '【发展】', '【结局】']

        return self._assemble_sampled_content(
            regions, region_limits, region_labels, len("".join(paragraphs))
        )

    def _five_region_sampling(self, paragraphs: List[str], max_chars: int) -> str:
        """
        五区域采样策略

        用于段落数>=10的长章节。
        """
        # 分配：开头25%，前中15%，中间20%，后中15%，结尾25%
        allocations = [0.25, 0.15, 0.20, 0.15, 0.25]
        region_limits = [int(max_chars * a) for a in allocations]

        # 将段落分成5个区域
        total_paragraphs = len(paragraphs)
        region_size = total_paragraphs // 5
        regions = [
            paragraphs[:region_size],  # 开头
            paragraphs[region_size : region_size * 2],  # 前中
            paragraphs[region_size * 2 : region_size * 3],  # 中间
            paragraphs[region_size * 3 : region_size * 4],  # 后中
            paragraphs[region_size * 4 :],  # 结尾
        ]

        region_labels = ['【开篇】', '【发展】', '【高潮】', '【转折】', '【结局】']

        return self._assemble_sampled_content(
            regions, region_limits, region_labels, len("\n\n".join(paragraphs))
        )

    def _assemble_sampled_content(
        self,
        regions: List[List[str]],
        region_limits: List[int],
        region_labels: List[str],
        original_length: int,
    ) -> str:
        """
        组装采样内容的通用方法

        Args:
            regions: 区域段落列表
            region_limits: 各区域字符限制
            region_labels: 区域标签
            original_length: 原始内容长度

        Returns:
            组装后的文本
        """
        selected_parts = []

        for i, (region, limit) in enumerate(zip(regions, region_limits)):
            if not region:
                continue

            # 对每个区域，优先选择包含动作/情感词汇的段落
            scored_paragraphs = [
                (p, self._score_paragraph_visual_value(p)) for p in region
            ]
            scored_paragraphs.sort(key=lambda x: x[1], reverse=True)

            # 选取段落直到达到字符限制
            region_content = []
            region_chars = 0
            for para, score in scored_paragraphs:
                if region_chars + len(para) > limit:
                    # 如果还没选任何段落，至少选第一个的一部分
                    if not region_content:
                        region_content.append(para[:limit])
                    break
                region_content.append(para)
                region_chars += len(para)

            if region_content:
                # 按原顺序排列（保持叙事逻辑）
                original_order = [
                    (p, region.index(p) if p in region else 999) for p in region_content
                ]
                original_order.sort(key=lambda x: x[1])
                selected_parts.append('\n\n'.join([p for p, _ in original_order]))

        # 组装最终文本
        result_parts = []
        for i, part in enumerate(selected_parts):
            if part and i < len(region_labels):
                result_parts.append(f"{region_labels[i]}\n{part}")

        result = '\n\n'.join(result_parts)

        # 添加说明
        result = f"[以下是章节关键内容采样，原文共 {original_length} 字]\n\n{result}"

        logger.info(
            "智能分段采样: 原始长度=%d, 采样后=%d, 区域数=%d",
            original_length,
            len(result),
            len(selected_parts),
        )

        return result

    def _score_paragraph_visual_value(self, paragraph: str) -> int:
        """
        评估段落的视觉价值（用于漫画场景选择）

        包含动作、对话、情感描写的段落更适合转化为漫画画面。

        Args:
            paragraph: 段落文本

        Returns:
            视觉价值分数（0-100）
        """
        score = 0

        # 动作词汇（高分）
        action_keywords = [
            '冲',
            '跑',
            '跳',
            '打',
            '踢',
            '砍',
            '刺',
            '射',
            '飞',
            '追',
            '挥',
            '握',
            '抓',
            '推',
            '拉',
            '撞',
            '闪',
            '躲',
            '挡',
            '攻',
            '战',
            '斗',
            '杀',
            '死',
            '血',
            '伤',
            '倒',
            '起',
            '站',
            '坐',
        ]
        for kw in action_keywords:
            if kw in paragraph:
                score += 5

        # 对话标记（中高分）
        dialogue_markers = [
            '"',
            '"',
            '「',
            '」',
            '『',
            '』',
            '说',
            '道',
            '问',
            '答',
            '喊',
            '叫',
        ]
        for marker in dialogue_markers:
            if marker in paragraph:
                score += 3

        # 情感词汇（中分）
        emotion_keywords = [
            '惊',
            '怒',
            '喜',
            '悲',
            '恐',
            '愤',
            '笑',
            '哭',
            '泪',
            '颤',
            '震',
            '惧',
            '爱',
            '恨',
            '痛',
            '苦',
            '乐',
            '忧',
            '愁',
            '怨',
        ]
        for kw in emotion_keywords:
            if kw in paragraph:
                score += 2

        # 视觉描写词汇（中分）
        visual_keywords = [
            '光',
            '影',
            '色',
            '亮',
            '暗',
            '红',
            '黑',
            '白',
            '金',
            '银',
            '闪',
            '耀',
            '照',
            '映',
            '看',
            '望',
            '见',
            '显',
            '现',
            '露',
        ]
        for kw in visual_keywords:
            if kw in paragraph:
                score += 2

        # 段落长度奖励（适中长度更好）
        length = len(paragraph)
        if 50 <= length <= 200:
            score += 10  # 理想长度
        elif 30 <= length <= 300:
            score += 5  # 可接受长度

        return min(score, 100)
