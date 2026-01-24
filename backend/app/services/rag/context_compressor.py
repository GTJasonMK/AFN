"""
上下文压缩器

负责在token限制内智能压缩上下文，确保最重要的信息优先保留。
采用分层压缩策略：必需层 > 重要层 > 参考层
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional

from .context_builder import GenerationContext
from .utils import (
    format_character_lines,
    format_character_state_lines,
    format_foreshadowing_lines,
    format_rag_chunk_line,
    truncate_text,
)


class ContextCompressor:
    """上下文压缩器

    核心功能：
    1. 估算上下文的token数量
    2. 按优先级裁剪内容以适应token限制
    3. 智能选择保留最重要的信息

    压缩策略：
    - 必需层：尽量完整保留，实在超限才压缩
    - 重要层：按项目优先级选择性保留
    - 参考层：作为补充，空间不足时首先裁剪
    """

    # 各层次的默认token占比
    DEFAULT_MUST_HAVE_RATIO = 0.45
    DEFAULT_IMPORTANT_RATIO = 0.35
    DEFAULT_REFERENCE_RATIO = 0.20

    def __init__(
        self,
        max_context_tokens: int = 4000,
        must_have_ratio: float = DEFAULT_MUST_HAVE_RATIO,
        important_ratio: float = DEFAULT_IMPORTANT_RATIO,
        reference_ratio: float = DEFAULT_REFERENCE_RATIO,
        chars_per_token: float = 1.5,  # 中文约1.5字符一个token
    ):
        """
        Args:
            max_context_tokens: 最大上下文token数
            must_have_ratio: 必需层token占比
            important_ratio: 重要层token占比
            reference_ratio: 参考层token占比
            chars_per_token: 每个token对应的字符数（用于估算）
        """
        self.max_context_tokens = max_context_tokens
        self.must_have_ratio = must_have_ratio
        self.important_ratio = important_ratio
        self.reference_ratio = reference_ratio
        self.chars_per_token = chars_per_token

        # 归一化比例
        total_ratio = must_have_ratio + important_ratio + reference_ratio
        if abs(total_ratio - 1.0) > 0.01:
            self.must_have_ratio /= total_ratio
            self.important_ratio /= total_ratio
            self.reference_ratio /= total_ratio

    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量

        使用简单的字符计数方法估算，对于中文约1.5字符/token
        """
        if not text:
            return 0
        return int(len(text) / self.chars_per_token)

    def estimate_dict_tokens(self, data: Dict[str, Any]) -> int:
        """估算字典数据的token数量"""
        try:
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return self.estimate_tokens(text)
        except (TypeError, ValueError):
            return 0

    def compress_context(
        self,
        context: GenerationContext,
        token_counter: Optional[Callable[[str], int]] = None,
    ) -> str:
        """智能压缩上下文

        按优先级压缩，确保不超过token限制：
        1. 首先分配各层的token预算
        2. 按层次压缩内容
        3. 如有剩余空间，可分配给更高优先级层

        Args:
            context: 生成上下文
            token_counter: 可选的自定义token计数函数

        Returns:
            压缩后的上下文文本
        """
        counter = token_counter or self.estimate_tokens

        # 计算各层token预算
        must_have_budget = int(self.max_context_tokens * self.must_have_ratio)
        important_budget = int(self.max_context_tokens * self.important_ratio)
        reference_budget = int(self.max_context_tokens * self.reference_ratio)

        result_parts = []
        used_tokens = 0

        # 1. 处理必需层（最高优先级）
        must_have_text = self._compress_must_have(
            context.must_have,
            must_have_budget,
            counter,
        )
        must_have_tokens = counter(must_have_text)

        if must_have_text:
            result_parts.append(must_have_text)
            used_tokens += must_have_tokens

        # 计算必需层节省的空间，分配给其他层
        saved_from_must_have = max(0, must_have_budget - must_have_tokens)
        important_budget += int(saved_from_must_have * 0.6)
        reference_budget += int(saved_from_must_have * 0.4)

        # 2. 处理重要层
        remaining_tokens = self.max_context_tokens - used_tokens
        actual_important_budget = min(important_budget, remaining_tokens - 200)  # 预留一些空间

        if actual_important_budget > 200:
            important_text = self._compress_important(
                context.important,
                actual_important_budget,
                counter,
            )
            if important_text:
                result_parts.append(important_text)
                used_tokens += counter(important_text)

        # 3. 处理参考层（如果还有空间）
        remaining_tokens = self.max_context_tokens - used_tokens
        actual_reference_budget = min(reference_budget, remaining_tokens - 100)

        if actual_reference_budget > 200:
            reference_text = self._compress_reference(
                context.reference,
                actual_reference_budget,
                counter,
            )
            if reference_text:
                result_parts.append(reference_text)

        return "\n\n".join(result_parts)

    def format_reference_layers(
        self,
        context: GenerationContext,
        *,
        include_reference: bool = True,
        token_counter: Optional[Callable[[str], int]] = None,
    ) -> str:
        """格式化重要层与参考层为文本"""
        if not context:
            return ""

        counter = token_counter or self.estimate_tokens
        max_tokens = max(self.max_context_tokens, 10000)
        sections = []

        if context.important:
            important_text = self._compress_important(
                context.important,
                max_tokens,
                counter,
            )
            if important_text:
                sections.append(important_text)

        if include_reference and context.reference:
            reference_text = self._compress_reference(
                context.reference,
                max_tokens,
                counter,
            )
            if reference_text:
                sections.append(reference_text)

        return "\n\n".join(sections)

    def _compress_must_have(
        self,
        must_have: Dict[str, Any],
        max_tokens: int,
        counter: Callable[[str], int],
    ) -> str:
        """压缩必需层

        必需层信息非常重要，尽量完整保留。
        如果超出预算，按以下优先级裁剪：
        1. 保留完整的角色名单和章节大纲
        2. 压缩前一章状态
        3. 精简故事基础信息
        """
        if not must_have:
            return ""

        lines = ["## 核心设定"]
        current_tokens = counter("\n".join(lines))

        # 1. 故事基础（优先级高）
        if basics := must_have.get("story_basics"):
            basics_lines = []
            if basics.get("genre"):
                basics_lines.append(f"- 题材: {basics['genre']}")
            if basics.get("style"):
                basics_lines.append(f"- 风格: {basics['style']}")
            if basics.get("tone"):
                basics_lines.append(f"- 基调: {basics['tone']}")
            if basics.get("one_sentence_summary"):
                summary = basics["one_sentence_summary"]
                if len(summary) > 100:
                    summary = summary[:97] + "..."
                basics_lines.append(f"- 核心: {summary}")

            basics_text = "\n".join(basics_lines)
            if current_tokens + counter(basics_text) < max_tokens:
                lines.extend(basics_lines)
                current_tokens += counter(basics_text)

        # 2. 角色名单（必须保留）
        if names := must_have.get("character_names"):
            names_text = f"\n角色名单: {', '.join(names)}"
            # 如果名单太长，只保留前10个
            if counter(names_text) > 200:
                names_text = f"\n角色名单: {', '.join(names[:10])}..."
            lines.append(names_text)
            current_tokens += counter(names_text)

        # 3. 当前章节大纲（必须保留）
        if outline := must_have.get("current_outline"):
            outline_lines = ["\n## 当前章节"]
            chapter_title = f"第{outline.get('chapter_number')}章: {outline.get('title', '')}"
            outline_lines.append(chapter_title)

            if summary := outline.get("summary"):
                # 如果摘要太长，截断
                if len(summary) > 200:
                    summary = summary[:197] + "..."
                outline_lines.append(f"大纲: {summary}")

            outline_text = "\n".join(outline_lines)
            lines.extend(outline_lines)
            current_tokens += counter(outline_text)

        # 4. 前一章状态（可压缩）
        if prev_state := must_have.get("prev_ending_state"):
            remaining = max_tokens - current_tokens
            if remaining > 100:
                prev_lines = ["\n## 前一章状态"]

                # 角色位置（精简版）
                if positions := prev_state.get("character_positions"):
                    pos_items = list(positions.items())[:5]
                    pos_text = "; ".join(f"{k}在{v}" for k, v in pos_items)
                    if len(pos_text) > 100:
                        pos_text = pos_text[:97] + "..."
                    prev_lines.append(f"位置: {pos_text}")

                # 未解悬念（只保留最重要的）
                if tensions := prev_state.get("unresolved_tensions"):
                    tension_text = "; ".join(tensions[:2])
                    if len(tension_text) > 80:
                        tension_text = tension_text[:77] + "..."
                    prev_lines.append(f"悬念: {tension_text}")

                prev_text = "\n".join(prev_lines)
                if counter(prev_text) < remaining:
                    lines.extend(prev_lines)

        return "\n".join(lines)

    def _compress_important(
        self,
        important: Dict[str, Any],
        max_tokens: int,
        counter: Callable[[str], int],
    ) -> str:
        """压缩重要层

        按优先级选择性保留：
        1. 高优先级伏笔
        2. 涉及角色详情
        3. 角色关系
        4. 相关摘要
        """
        if not important:
            return ""

        lines = ["## 关键参考"]
        current_tokens = counter("\n".join(lines))

        # 各部分的优先级权重
        sections = [
            ("high_priority_foreshadowing", self._format_foreshadowing, 0.25),
            ("involved_characters", self._format_characters, 0.30),
            ("character_relationships", self._format_relationships, 0.20),
            ("prev_character_states", self._format_prev_states, 0.15),
            ("relevant_summaries", self._format_summaries, 0.10),
        ]

        for key, formatter, weight in sections:
            if data := important.get(key):
                section_budget = int(max_tokens * weight)
                section_text = formatter(data, section_budget, counter)
                if section_text:
                    section_tokens = counter(section_text)
                    if current_tokens + section_tokens < max_tokens:
                        lines.append(section_text)
                        current_tokens += section_tokens

        return "\n".join(lines) if len(lines) > 1 else ""

    def _compress_reference(
        self,
        reference: Dict[str, Any],
        max_tokens: int,
        counter: Callable[[str], int],
    ) -> str:
        """压缩参考层

        参考层优先级最低，空间不足时大幅裁剪
        """
        if not reference:
            return ""

        lines = ["## 补充参考"]
        current_tokens = counter("\n".join(lines))

        # 相关段落（最有价值的参考）
        if passages := reference.get("relevant_passages"):
            passage_budget = int(max_tokens * 0.5)
            passage_text = self._format_passages(passages, passage_budget, counter)
            if passage_text and current_tokens + counter(passage_text) < max_tokens:
                lines.append(passage_text)
                current_tokens += counter(passage_text)

        # 其他伏笔
        if other_fs := reference.get("other_foreshadowing"):
            fs_lines = ["\n### 其他伏笔"]
            for fs in other_fs[:2]:
                fs_lines.append(f"- [{fs.get('priority', 'medium')}] {fs.get('description', '')[:50]}")
            fs_text = "\n".join(fs_lines)
            if current_tokens + counter(fs_text) < max_tokens:
                lines.append(fs_text)

        return "\n".join(lines) if len(lines) > 1 else ""

    def _format_foreshadowing(
        self,
        foreshadowing: List[Dict[str, Any]],
        budget: int,
        counter: Callable[[str], int],
    ) -> str:
        """格式化伏笔信息"""
        if not foreshadowing:
            return ""

        lines = ["\n### 待回收伏笔"]
        lines.extend(format_foreshadowing_lines(
            foreshadowing,
            max_items=3,
            description_limit=60,
            add_ellipsis=True,
            use_priority_marker=False,
            marker_for_high="[重要]",
            default_marker="[重要]",
            description_key="description",
            fallback_key=None,
        ))

        return "\n".join(lines)

    def _format_characters(
        self,
        characters: List[Dict[str, Any]],
        budget: int,
        counter: Callable[[str], int],
    ) -> str:
        """格式化角色信息"""
        if not characters:
            return ""

        lines = ["\n### 涉及角色"]
        lines.extend(format_character_lines(
            characters,
            max_items=3,
            default_name="",
            identity_key="identity",
            personality_key="personality",
            personality_limit=30,
            add_ellipsis=True,
        ))

        return "\n".join(lines)

    def _format_relationships(
        self,
        relationships: List[Dict[str, Any]],
        budget: int,
        counter: Callable[[str], int],
    ) -> str:
        """格式化关系信息"""
        if not relationships:
            return ""

        lines = ["\n### 角色关系"]
        for rel in relationships[:4]:
            desc = rel.get("description", "")
            if len(desc) > 30:
                desc = desc[:27] + "..."
            lines.append(f"- {rel.get('from')} -> {rel.get('to')}: {desc}")

        return "\n".join(lines)

    def _format_prev_states(
        self,
        states: Dict[str, Any],
        budget: int,
        counter: Callable[[str], int],
    ) -> str:
        """格式化前一章角色状态"""
        if not states:
            return ""

        lines = ["\n### 角色状态"]
        lines.extend(format_character_state_lines(
            states,
            max_items=4,
            status_limit=20,
            add_ellipsis=True,
        ))

        return "\n".join(lines)

    def _format_summaries(
        self,
        summaries: List[Dict[str, Any]],
        budget: int,
        counter: Callable[[str], int],
    ) -> str:
        """格式化相关摘要"""
        if not summaries:
            return ""

        lines = ["\n### 相关摘要"]
        for s in summaries[:2]:
            summary_text = s.get("summary", "")
            summary_text = truncate_text(summary_text, 80)
            lines.append(f"- 第{s.get('chapter')}章: {summary_text}")

        return "\n".join(lines)

    def _format_passages(
        self,
        passages: List[Dict[str, Any]],
        budget: int,
        counter: Callable[[str], int],
    ) -> str:
        """格式化相关段落"""
        if not passages:
            return ""

        lines = ["\n### 相关段落"]
        budget_per_passage = budget // min(len(passages), 3)

        for p in passages[:2]:
            content = p.get("content", "")
            max_len = int(budget_per_passage * self.chars_per_token * 0.8)
            lines.append(format_rag_chunk_line(
                p.get("chapter"),
                None,
                content,
                max_content_length=max_len,
            ))

        return "\n".join(lines)


class AdaptiveCompressor:
    """自适应压缩器

    根据章节复杂度动态调整压缩策略
    """

    def __init__(self, base_compressor: ContextCompressor):
        self.base_compressor = base_compressor

    def compress_with_complexity(
        self,
        context: GenerationContext,
        chapter_complexity: str = "medium",  # low, medium, high
        token_counter: Optional[Callable[[str], int]] = None,
    ) -> str:
        """根据章节复杂度调整压缩

        复杂章节（如大战、多线叙事）需要更多上下文
        简单章节（如过渡、对话）可以减少上下文

        Args:
            context: 生成上下文
            chapter_complexity: 章节复杂度
            token_counter: token计数函数

        Returns:
            压缩后的上下文
        """
        # 根据复杂度调整token上限
        complexity_multipliers = {
            "low": 0.7,
            "medium": 1.0,
            "high": 1.3,
        }
        multiplier = complexity_multipliers.get(chapter_complexity, 1.0)

        # 临时调整最大token数
        original_max = self.base_compressor.max_context_tokens
        self.base_compressor.max_context_tokens = int(original_max * multiplier)

        try:
            return self.base_compressor.compress_context(context, token_counter)
        finally:
            # 恢复原始设置
            self.base_compressor.max_context_tokens = original_max
