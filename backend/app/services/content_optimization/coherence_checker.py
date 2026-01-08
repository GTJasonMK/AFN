"""
连贯性检查器

使用LLM检查段落的逻辑连贯性、角色一致性、伏笔呼应等维度。
"""

import logging
from typing import List, Optional

from ..llm_wrappers import call_llm, LLMProfile
from .schemas import (
    CoherenceIssue,
    ParagraphAnalysis,
    RAGContext,
    OptimizationContext,
    SuggestionEvent,
    SuggestionPriority,
)

logger = logging.getLogger(__name__)

# 用户消息模板（系统提示词已迁移到 prompts/coherence_check.md）
COHERENCE_CHECK_USER_TEMPLATE = """## 当前段落（第{paragraph_index}段）
{paragraph}

## 前文段落
{prev_paragraphs}

## 已知信息
{context_info}

## 本次需要检查的维度
{dimensions_to_check}

请根据以上信息进行检查。"""

# 维度简称映射（详细说明在 prompts/coherence_check.md 中）
# 使用字符串键以匹配传入的维度参数
DIMENSION_LABELS = {
    "coherence": "逻辑连贯性（coherence）",
    "character": "角色一致性（character）",
    "foreshadow": "伏笔呼应（foreshadow）",
    "timeline": "时间线一致性（timeline）",
    "style": "风格一致性（style）",
    "scene": "场景描写（scene）",
}


class CoherenceChecker:
    """连贯性检查器"""

    def __init__(self, llm_service, prompt_service=None):
        """
        初始化检查器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例（可选）
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def _get_system_prompt(self) -> str:
        """获取系统提示词，优先从prompt_service获取"""
        if self.prompt_service:
            prompt = await self.prompt_service.get_prompt("coherence_check")
            if prompt:
                return prompt
        # 回退到默认提示词
        return "你是一个专业的小说编辑，擅长发现和修正文本中的逻辑问题。请仔细检查段落内容，找出可能存在的问题，并以JSON格式输出。"

    async def check_paragraph(
        self,
        paragraph: str,
        paragraph_index: int,
        prev_paragraphs: List[str],
        context: OptimizationContext,
        rag_context: RAGContext,
        dimensions: List[str],
        user_id: str,
    ) -> List[SuggestionEvent]:
        """
        检查段落并生成建议

        Args:
            paragraph: 当前段落
            paragraph_index: 段落索引
            prev_paragraphs: 前文段落列表
            context: 优化上下文
            rag_context: RAG检索上下文
            dimensions: 检查维度列表
            user_id: 用户ID

        Returns:
            建议事件列表
        """
        # 构建用户消息
        user_content = self._build_check_prompt(
            paragraph=paragraph,
            paragraph_index=paragraph_index,
            prev_paragraphs=prev_paragraphs,
            context=context,
            rag_context=rag_context,
            dimensions=dimensions,
        )

        try:
            # 获取系统提示词
            system_prompt = await self._get_system_prompt()

            # 使用统一的LLM调用包装器
            response = await call_llm(
                self.llm_service,
                LLMProfile.COHERENCE,
                system_prompt=system_prompt,
                user_content=user_content,
                user_id=user_id,
            )

            # 解析响应
            suggestions = self._parse_llm_response(response, paragraph_index)
            return suggestions

        except Exception as e:
            logger.error("连贯性检查失败: %s", str(e))
            return []

    def _build_check_prompt(
        self,
        paragraph: str,
        paragraph_index: int,
        prev_paragraphs: List[str],
        context: OptimizationContext,
        rag_context: RAGContext,
        dimensions: List[str],
    ) -> str:
        """
        构建检查提示词

        Args:
            paragraph: 当前段落
            paragraph_index: 段落索引
            prev_paragraphs: 前文段落列表
            context: 优化上下文
            rag_context: RAG检索上下文
            dimensions: 检查维度列表

        Returns:
            完整提示词
        """
        # 构建前文段落文本
        prev_text = "\n\n".join(prev_paragraphs[-3:]) if prev_paragraphs else "（这是第一段）"

        # 构建上下文信息
        context_parts = []

        if context.blueprint_core:
            context_parts.append(f"【蓝图核心】\n{context.blueprint_core[:500]}")

        if context.character_names:
            context_parts.append(f"【已知角色】\n{', '.join(context.character_names)}")

        if context.prev_chapter_ending:
            context_parts.append(f"【前章结尾】\n{context.prev_chapter_ending[:300]}")

        # 添加RAG上下文
        if rag_context.character_states:
            states = [f"- {s.get('character', '?')}: {s.get('state', '?')}"
                     for s in rag_context.character_states[:5]]
            context_parts.append(f"【角色状态】\n" + "\n".join(states))

        if rag_context.foreshadowings:
            fs = [f"- {f.get('description', '?')} (状态: {f.get('status', '?')})"
                 for f in rag_context.foreshadowings[:5]]
            context_parts.append(f"【相关伏笔】\n" + "\n".join(fs))

        context_info = "\n\n".join(context_parts) if context_parts else "（无额外上下文）"

        # 构建检查维度描述（详细说明在系统提示词中，这里只列出维度名称）
        dimensions_text = "\n".join(
            f"- {DIMENSION_LABELS.get(dim, str(dim))}"
            for dim in dimensions
        )

        return COHERENCE_CHECK_USER_TEMPLATE.format(
            paragraph_index=paragraph_index + 1,
            paragraph=paragraph,
            prev_paragraphs=prev_text,
            context_info=context_info,
            dimensions_to_check=dimensions_text,
        )

    def _parse_llm_response(
        self,
        response: str,
        paragraph_index: int
    ) -> List[SuggestionEvent]:
        """
        解析LLM响应

        Args:
            response: LLM响应文本
            paragraph_index: 段落索引

        Returns:
            建议事件列表
        """
        from ...utils.json_utils import parse_llm_json_safe

        data = parse_llm_json_safe(response)
        if not data:
            return []

        suggestions = []
        issues = data.get("issues", [])

        for issue in issues:
            if not isinstance(issue, dict):
                continue

            # 转换严重程度为优先级
            severity = issue.get("severity", "medium")
            priority_map = {
                "high": SuggestionPriority.HIGH.value,
                "medium": SuggestionPriority.MEDIUM.value,
                "low": SuggestionPriority.LOW.value,
            }
            priority = priority_map.get(severity, SuggestionPriority.MEDIUM.value)

            suggestion = SuggestionEvent(
                paragraph_index=paragraph_index,
                original_text=issue.get("original_text", ""),
                suggested_text=issue.get("suggested_text", ""),
                reason=issue.get("reason", issue.get("description", "")),
                category=issue.get("type", "coherence"),
                priority=priority,
            )
            suggestions.append(suggestion)

        return suggestions

    def quick_check_coherence(
        self,
        paragraph: str,
        prev_paragraph: Optional[str],
        analysis: ParagraphAnalysis,
        prev_analysis: Optional[ParagraphAnalysis],
    ) -> List[CoherenceIssue]:
        """
        快速检查连贯性（不使用LLM）

        基于规则的快速检查，用于初步筛选

        Args:
            paragraph: 当前段落
            prev_paragraph: 前一段落
            analysis: 当前段落分析
            prev_analysis: 前一段落分析

        Returns:
            问题列表
        """
        issues = []

        if not prev_paragraph or not prev_analysis:
            return issues

        # 检查角色突然出现
        if analysis.characters:
            for char in analysis.characters:
                if char not in prev_analysis.characters:
                    # 检查是否是首次提及
                    if char not in (prev_paragraph or ""):
                        issues.append(CoherenceIssue(
                            dimension="character",  # 使用字符串而非 Enum
                            description=f"角色'{char}'突然出现，可能需要过渡",
                            severity="low",
                            location=f"段落{analysis.index + 1}",
                        ))

        # 检查场景突然变化
        if analysis.scene and prev_analysis.scene:
            if analysis.scene != prev_analysis.scene:
                # 检查是否有场景转换词
                transition_words = ["来到", "走进", "进入", "离开", "回到"]
                has_transition = any(w in paragraph[:50] for w in transition_words)
                if not has_transition:
                    issues.append(CoherenceIssue(
                        dimension="scene",  # 使用字符串而非 Enum
                        description=f"场景从'{prev_analysis.scene}'变为'{analysis.scene}'，但缺少过渡",
                        severity="medium",
                        location=f"段落{analysis.index + 1}开头",
                    ))

        # 检查时间跳跃
        if analysis.time_marker and prev_analysis.time_marker:
            if analysis.time_marker != prev_analysis.time_marker:
                issues.append(CoherenceIssue(
                    dimension="timeline",  # 使用字符串而非 Enum
                    description=f"时间从'{prev_analysis.time_marker}'变为'{analysis.time_marker}'",
                    severity="low",
                    location=f"段落{analysis.index + 1}",
                ))

        # 检查情感基调突变
        if analysis.emotion_tone and prev_analysis.emotion_tone:
            opposite_emotions = {
                "喜悦": ["悲伤", "愤怒", "恐惧"],
                "悲伤": ["喜悦"],
                "愤怒": ["喜悦", "平静"],
                "平静": ["愤怒", "恐惧", "紧张"],
            }
            if analysis.emotion_tone in opposite_emotions.get(prev_analysis.emotion_tone, []):
                issues.append(CoherenceIssue(
                    dimension="coherence",  # 使用字符串而非 Enum
                    description=f"情感基调从'{prev_analysis.emotion_tone}'突变为'{analysis.emotion_tone}'",
                    severity="medium",
                    location=f"段落{analysis.index + 1}",
                ))

        return issues
