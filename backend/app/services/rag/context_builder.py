"""
智能上下文构建器

负责将检索到的RAG内容、蓝图信息、角色状态、伏笔追踪等多种数据源
组织成分层的上下文结构，为章节生成提供全面而有序的参考信息。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..vector_store_service import RetrievedChunk, RetrievedSummary
from ...schemas.novel import (
    ChapterAnalysisData,
    CharacterState,
    ForeshadowingData,
)
from .utils import extract_involved_characters, truncate_text, build_outline_text


@dataclass
class GenerationContext:
    """生成上下文结构

    分为三个优先级层次：
    1. must_have: 必须包含，直接影响生成的正确性
    2. important: 重要信息，影响故事连贯性
    3. reference: 参考信息，提升内容丰富度

    这种分层设计允许在token限制时进行智能裁剪。
    """

    # 必需层：核心约束信息
    must_have: Dict[str, Any] = field(default_factory=dict)

    # 重要层：连贯性相关信息
    important: Dict[str, Any] = field(default_factory=dict)

    # 参考层：可选的丰富信息
    reference: Dict[str, Any] = field(default_factory=dict)

    def get_all_data(self) -> Dict[str, Any]:
        """获取所有层次的数据"""
        return {
            "must_have": self.must_have,
            "important": self.important,
            "reference": self.reference,
        }

    def is_empty(self) -> bool:
        """检查上下文是否为空"""
        return not (self.must_have or self.important or self.reference)


@dataclass
class BlueprintInfo:
    """蓝图信息摘要，用于上下文构建"""
    title: str = ""
    genre: str = ""
    style: str = ""
    tone: str = ""
    one_sentence_summary: str = ""
    full_synopsis: str = ""
    world_setting: Dict[str, Any] = field(default_factory=dict)
    characters: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RAGContext:
    """RAG检索结果容器"""
    chunks: List[RetrievedChunk] = field(default_factory=list)
    summaries: List[RetrievedSummary] = field(default_factory=list)


class SmartContextBuilder:
    """智能上下文构建器

    核心职责：
    1. 整合多种数据源（蓝图、RAG检索、分析数据、伏笔）
    2. 按优先级组织上下文层次
    3. 提取与当前章节相关的角色和设定
    4. 格式化为适合LLM消费的结构

    数据源：
    - 蓝图：作品元信息、角色设定、世界观
    - RAG检索：相关章节片段和摘要
    - 前一章分析：角色状态、伏笔、关键事件
    - 伏笔追踪：待回收的伏笔列表
    """

    def __init__(
        self,
        chunk_max_length: int = 500,
        summary_max_length: int = 300,
        max_characters_detail: int = 5,
        max_relationships: int = 10,
    ):
        """
        Args:
            chunk_max_length: 单个chunk的最大长度
            summary_max_length: 单个摘要的最大长度
            max_characters_detail: 详细展示的角色数量限制
            max_relationships: 展示的关系数量限制
        """
        self.chunk_max_length = chunk_max_length
        self.summary_max_length = summary_max_length
        self.max_characters_detail = max_characters_detail
        self.max_relationships = max_relationships

    def build_generation_context(
        self,
        outline: Dict[str, Any],
        blueprint: BlueprintInfo,
        rag_context: RAGContext,
        prev_chapter_analysis: Optional[ChapterAnalysisData] = None,
        pending_foreshadowing: Optional[List[Dict[str, Any]]] = None,
    ) -> GenerationContext:
        """构建生成上下文

        Args:
            outline: 当前章节大纲 {"chapter_number", "title", "summary"}
            blueprint: 蓝图信息
            rag_context: RAG检索结果
            prev_chapter_analysis: 前一章的分析数据
            pending_foreshadowing: 待回收的伏笔列表

        Returns:
            GenerationContext: 分层组织的上下文
        """
        context = GenerationContext()

        # === 构建必需层 ===
        context.must_have = self._build_must_have_layer(
            outline=outline,
            blueprint=blueprint,
            prev_chapter_analysis=prev_chapter_analysis,
        )

        # === 构建重要层 ===
        context.important = self._build_important_layer(
            outline=outline,
            blueprint=blueprint,
            rag_context=rag_context,
            prev_chapter_analysis=prev_chapter_analysis,
            pending_foreshadowing=pending_foreshadowing,
        )

        # === 构建参考层 ===
        context.reference = self._build_reference_layer(
            blueprint=blueprint,
            rag_context=rag_context,
            pending_foreshadowing=pending_foreshadowing,
        )

        return context

    def _build_must_have_layer(
        self,
        outline: Dict[str, Any],
        blueprint: BlueprintInfo,
        prev_chapter_analysis: Optional[ChapterAnalysisData],
    ) -> Dict[str, Any]:
        """构建必需层

        必须包含的信息，缺失会导致生成错误：
        - 作品基本信息（题材、风格、基调）
        - 角色名称列表（防止改名/混淆）
        - 当前章节大纲
        - 前一章结尾状态（确保衔接）
        """
        must_have = {}

        # 1. 作品核心设定
        must_have["story_basics"] = {
            "title": blueprint.title,
            "genre": blueprint.genre,
            "style": blueprint.style,
            "tone": blueprint.tone,
            "one_sentence_summary": blueprint.one_sentence_summary,
        }

        # 2. 角色名称列表（核心约束，防止角色名错误）
        character_names = [c.get("name", "") for c in blueprint.characters if c.get("name")]
        must_have["character_names"] = character_names

        # 3. 当前章节大纲
        must_have["current_outline"] = {
            "chapter_number": outline.get("chapter_number"),
            "title": outline.get("title", ""),
            "summary": outline.get("summary", ""),
        }

        # 4. 前一章结尾状态
        must_have["prev_ending_state"] = self._extract_prev_ending_state(
            prev_chapter_analysis
        )

        return must_have

    def _build_important_layer(
        self,
        outline: Dict[str, Any],
        blueprint: BlueprintInfo,
        rag_context: RAGContext,
        prev_chapter_analysis: Optional[ChapterAnalysisData],
        pending_foreshadowing: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """构建重要层

        强烈建议包含的信息，影响故事连贯性：
        - 涉及角色的详细信息
        - 角色之间的关系
        - 待回收的高优先级伏笔
        - 前一章的角色状态
        - RAG检索的最相关摘要
        """
        important = {}

        # 1. 提取涉及角色的详细信息
        involved_characters = self._get_involved_characters(
            outline, blueprint.characters
        )
        important["involved_characters"] = involved_characters[:self.max_characters_detail]

        # 2. 涉及角色的关系
        relevant_relationships = self._get_relevant_relationships(
            involved_characters, blueprint.relationships
        )
        important["character_relationships"] = relevant_relationships[:self.max_relationships]

        # 3. 高优先级伏笔（需要在近期回收）
        if pending_foreshadowing:
            high_priority_fs = [
                fs for fs in pending_foreshadowing
                if fs.get("priority") == "high"
            ]
            important["high_priority_foreshadowing"] = high_priority_fs[:3]

        # 4. 前一章角色状态
        if prev_chapter_analysis and prev_chapter_analysis.character_states:
            important["prev_character_states"] = {
                name: {
                    "location": state.location,
                    "status": state.status,
                    "changes": state.changes[:3] if state.changes else [],
                }
                for name, state in prev_chapter_analysis.character_states.items()
            }

        # 5. 最相关的章节摘要
        if rag_context.summaries:
            formatted_summaries = []
            for s in rag_context.summaries[:3]:
                formatted_summaries.append({
                    "chapter": s.chapter_number,
                    "title": s.title,
                    "summary": self._truncate(s.summary, self.summary_max_length),
                })
            important["relevant_summaries"] = formatted_summaries

        return important

    def _build_reference_layer(
        self,
        blueprint: BlueprintInfo,
        rag_context: RAGContext,
        pending_foreshadowing: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """构建参考层

        可选包含的信息，提升内容丰富度：
        - 世界观设定
        - RAG检索的文本片段
        - 中低优先级伏笔
        """
        reference = {}

        # 1. 世界观设定
        if blueprint.world_setting:
            reference["world_setting"] = blueprint.world_setting

        # 2. 完整故事大纲（用于保持整体方向）
        if blueprint.full_synopsis:
            reference["full_synopsis"] = self._truncate(
                blueprint.full_synopsis, 500
            )

        # 3. RAG检索的文本片段
        if rag_context.chunks:
            formatted_chunks = []
            for c in rag_context.chunks[:5]:
                formatted_chunks.append({
                    "chapter": c.chapter_number,
                    "title": c.chapter_title or f"第{c.chapter_number}章",
                    "content": self._truncate(c.content, self.chunk_max_length),
                    "relevance_score": round(c.score, 3),
                })
            reference["relevant_passages"] = formatted_chunks

        # 4. 中低优先级伏笔
        if pending_foreshadowing:
            other_fs = [
                {
                    "description": fs.get("description", ""),
                    "priority": fs.get("priority", "medium"),
                    "planted_chapter": fs.get("planted_chapter"),
                }
                for fs in pending_foreshadowing
                if fs.get("priority") != "high"
            ]
            if other_fs:
                reference["other_foreshadowing"] = other_fs[:5]

        return reference

    def _extract_prev_ending_state(
        self,
        prev_analysis: Optional[ChapterAnalysisData],
    ) -> Dict[str, Any]:
        """提取前一章的结尾状态"""
        if not prev_analysis:
            return {}

        ending_state = {}

        # 角色位置
        if prev_analysis.character_states:
            character_positions = {}
            for name, state in prev_analysis.character_states.items():
                if state.location:
                    character_positions[name] = state.location
            if character_positions:
                ending_state["character_positions"] = character_positions

        # 未解决的悬念
        if prev_analysis.foreshadowing and prev_analysis.foreshadowing.tensions:
            ending_state["unresolved_tensions"] = prev_analysis.foreshadowing.tensions[:5]

        # 关键事件（用于情节延续）
        if prev_analysis.key_events:
            high_importance_events = [
                {"type": e.type, "description": e.description}
                for e in prev_analysis.key_events
                if e.importance == "high"
            ][:3]
            if high_importance_events:
                ending_state["recent_key_events"] = high_importance_events

        # 情感基调（用于氛围延续）
        if prev_analysis.metadata and prev_analysis.metadata.tone:
            ending_state["prev_tone"] = prev_analysis.metadata.tone

        return ending_state

    def _get_involved_characters(
        self,
        outline: Dict[str, Any],
        blueprint_characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """提取涉及的角色详细信息"""
        return extract_involved_characters(
            outline=outline,
            blueprint_characters=blueprint_characters,
            include_details=True,
        )

    def _get_relevant_relationships(
        self,
        involved_characters: List[Dict[str, Any]],
        all_relationships: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """提取与涉及角色相关的关系"""
        involved_names = {c.get("name", "") for c in involved_characters}

        relevant = []
        for rel in all_relationships:
            char_from = rel.get("character_from", "")
            char_to = rel.get("character_to", "")

            # 如果关系的任一方是涉及角色
            if char_from in involved_names or char_to in involved_names:
                relevant.append({
                    "from": char_from,
                    "to": char_to,
                    "description": rel.get("description", ""),
                })

        return relevant

    def _truncate(self, text: str, max_length: int) -> str:
        """截断文本到指定长度"""
        return truncate_text(text, max_length)

    def format_context_for_prompt(
        self,
        context: GenerationContext,
        include_reference: bool = True,
    ) -> str:
        """将上下文格式化为提示词文本

        Args:
            context: 生成上下文
            include_reference: 是否包含参考层

        Returns:
            格式化的上下文文本
        """
        sections = []

        # 必需层
        if context.must_have:
            sections.append(self._format_must_have_section(context.must_have))

        # 重要层
        if context.important:
            sections.append(self._format_important_section(context.important))

        # 参考层（可选）
        if include_reference and context.reference:
            sections.append(self._format_reference_section(context.reference))

        return "\n\n".join(sections)

    def _format_must_have_section(self, must_have: Dict[str, Any]) -> str:
        """格式化必需层"""
        lines = ["## 核心设定"]

        # 故事基础
        if basics := must_have.get("story_basics"):
            lines.append(f"- 题材: {basics.get('genre', '未知')}")
            lines.append(f"- 风格: {basics.get('style', '未知')}")
            lines.append(f"- 基调: {basics.get('tone', '未知')}")
            if summary := basics.get("one_sentence_summary"):
                lines.append(f"- 核心: {summary}")

        # 角色名单
        if names := must_have.get("character_names"):
            lines.append(f"\n角色名单: {', '.join(names)}")

        # 当前章节
        if outline := must_have.get("current_outline"):
            lines.append(f"\n## 当前章节")
            lines.append(f"第{outline.get('chapter_number')}章: {outline.get('title')}")
            if summary := outline.get("summary"):
                lines.append(f"大纲: {summary}")

        # 前一章状态
        if prev_state := must_have.get("prev_ending_state"):
            lines.append(f"\n## 前一章结尾状态")
            if positions := prev_state.get("character_positions"):
                pos_text = "; ".join(f"{k}在{v}" for k, v in positions.items())
                lines.append(f"角色位置: {pos_text}")
            if tensions := prev_state.get("unresolved_tensions"):
                lines.append(f"未解悬念: {'; '.join(tensions[:3])}")

        return "\n".join(lines)

    def _format_important_section(self, important: Dict[str, Any]) -> str:
        """格式化重要层"""
        lines = ["## 关键参考"]

        # 涉及角色
        if characters := important.get("involved_characters"):
            lines.append("\n### 涉及角色")
            for char in characters[:3]:
                lines.append(f"- {char.get('name')}: {char.get('identity', '未知身份')}")
                if personality := char.get("personality"):
                    lines.append(f"  性格: {personality[:50]}...")

        # 角色关系
        if relationships := important.get("character_relationships"):
            lines.append("\n### 角色关系")
            for rel in relationships[:5]:
                lines.append(f"- {rel.get('from')} -> {rel.get('to')}: {rel.get('description', '')}")

        # 高优先级伏笔
        if foreshadowing := important.get("high_priority_foreshadowing"):
            lines.append("\n### 待回收伏笔 (高优先级)")
            for fs in foreshadowing:
                lines.append(f"- {fs.get('description', '')}")

        # 前一章角色状态
        if prev_states := important.get("prev_character_states"):
            lines.append("\n### 角色当前状态")
            for name, state in list(prev_states.items())[:5]:
                status_parts = []
                if state.get("location"):
                    status_parts.append(f"位于{state['location']}")
                if state.get("status"):
                    status_parts.append(state["status"])
                if status_parts:
                    lines.append(f"- {name}: {', '.join(status_parts)}")

        # 相关摘要
        if summaries := important.get("relevant_summaries"):
            lines.append("\n### 相关章节摘要")
            for s in summaries:
                lines.append(f"- 第{s.get('chapter')}章《{s.get('title')}》: {s.get('summary')}")

        return "\n".join(lines)

    def _format_reference_section(self, reference: Dict[str, Any]) -> str:
        """格式化参考层"""
        lines = ["## 补充参考"]

        # 世界观
        if world := reference.get("world_setting"):
            lines.append("\n### 世界观设定")
            if isinstance(world, dict):
                for key, value in list(world.items())[:5]:
                    if isinstance(value, str):
                        lines.append(f"- {key}: {value[:100]}")

        # 相关段落
        if passages := reference.get("relevant_passages"):
            lines.append("\n### 相关段落")
            for p in passages[:3]:
                lines.append(f"[第{p.get('chapter')}章] {p.get('content')[:200]}...")

        # 其他伏笔
        if other_fs := reference.get("other_foreshadowing"):
            lines.append("\n### 其他伏笔")
            for fs in other_fs[:3]:
                lines.append(f"- [{fs.get('priority')}] {fs.get('description')}")

        return "\n".join(lines)
