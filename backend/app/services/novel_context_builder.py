"""
小说上下文构建器

提供统一的上下文构建接口，消除在各个服务中重复拼接上下文的代码。
用于章节生成、大纲生成、评估等需要构建小说上下文的场景。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NovelContext:
    """
    小说上下文容器

    统一管理章节生成、大纲生成等任务所需的上下文信息。
    支持转换为不同格式以适应各种LLM调用场景。

    Attributes:
        blueprint: 小说蓝图（核心设定）
        previous_chapters: 前序章节信息列表
        current_outline: 当前章节大纲
        relevant_summaries: RAG检索的相关摘要
        character_states: 角色状态信息
        foreshadowings: 伏笔信息
        prev_chapter_ending: 前章结尾
        context_note: 上下文说明
    """
    blueprint: Dict[str, Any] = field(default_factory=dict)
    previous_chapters: List[Dict[str, Any]] = field(default_factory=list)
    current_outline: Optional[Dict[str, Any]] = None
    relevant_summaries: List[str] = field(default_factory=list)
    character_states: List[Dict[str, Any]] = field(default_factory=list)
    foreshadowings: List[Dict[str, Any]] = field(default_factory=list)
    prev_chapter_ending: Optional[str] = None
    context_note: str = ""

    def to_payload(self) -> Dict[str, Any]:
        """
        转换为LLM payload格式

        生成适合作为LLM输入的字典格式。

        Returns:
            Dict[str, Any]: 包含所有上下文信息的字典
        """
        payload: Dict[str, Any] = {}

        if self.blueprint:
            payload["novel_blueprint"] = self.blueprint

        if self.previous_chapters:
            payload["previous_chapters"] = self.previous_chapters
            if not self.context_note:
                self.context_note = f"前面已生成 {len(self.previous_chapters)} 章，请确保与前文保持连贯。"

        if self.context_note:
            payload["context_note"] = self.context_note

        if self.current_outline:
            payload["current_outline"] = self.current_outline

        if self.relevant_summaries:
            payload["relevant_completed_chapters"] = {
                "description": "通过语义检索找到的相关章节摘要，请确保新内容与这些已完成内容保持一致",
                "summaries": self.relevant_summaries,
            }

        if self.character_states:
            payload["character_states"] = {
                "description": "角色当前状态（来自前序章节）",
                "states": self.character_states,
            }

        if self.foreshadowings:
            payload["active_foreshadowings"] = {
                "description": "需要注意的伏笔信息",
                "items": self.foreshadowings,
            }

        if self.prev_chapter_ending:
            payload["prev_chapter_ending"] = self.prev_chapter_ending

        return payload

    def to_json(self, ensure_ascii: bool = False) -> str:
        """
        转换为JSON字符串

        Args:
            ensure_ascii: 是否转义非ASCII字符

        Returns:
            str: JSON字符串
        """
        return json.dumps(self.to_payload(), ensure_ascii=ensure_ascii)

    def to_prompt_string(self, include_blueprint: bool = True) -> str:
        """
        转换为提示词字符串格式

        生成适合直接拼接到提示词中的格式化字符串。

        Args:
            include_blueprint: 是否包含蓝图

        Returns:
            str: 格式化的上下文字符串
        """
        parts = []

        if include_blueprint and self.blueprint:
            # 只提取蓝图核心信息
            core_info = {
                "title": self.blueprint.get("title", ""),
                "genre": self.blueprint.get("genre", ""),
                "synopsis": self.blueprint.get("synopsis", ""),
                "theme": self.blueprint.get("theme", ""),
            }
            parts.append(f"## 小说蓝图\n{json.dumps(core_info, ensure_ascii=False, indent=2)}")

        if self.previous_chapters:
            chapter_summaries = []
            for ch in self.previous_chapters[-5:]:  # 最多显示最近5章
                num = ch.get("chapter_number", "?")
                title = ch.get("title", "")
                summary = ch.get("summary", "")[:200]  # 截断摘要
                chapter_summaries.append(f"第{num}章 {title}: {summary}")
            parts.append(f"## 前序章节 ({len(self.previous_chapters)}章)\n" + "\n".join(chapter_summaries))

        if self.current_outline:
            parts.append(f"## 当前章节大纲\n标题: {self.current_outline.get('title', '')}\n摘要: {self.current_outline.get('summary', '')}")

        if self.prev_chapter_ending:
            parts.append(f"## 前章结尾\n{self.prev_chapter_ending[:500]}")

        if self.character_states:
            states = [f"- {s.get('character', '?')}: {s.get('state', '')[:100]}" for s in self.character_states[:5]]
            parts.append(f"## 角色状态\n" + "\n".join(states))

        if self.foreshadowings:
            fs = [f"- {f.get('description', '')[:100]} (状态: {f.get('status', 'pending')})" for f in self.foreshadowings[:5]]
            parts.append(f"## 活跃伏笔\n" + "\n".join(fs))

        if self.relevant_summaries:
            parts.append(f"## 相关章节摘要\n" + "\n".join(self.relevant_summaries[:3]))

        return "\n\n".join(parts) if parts else "（无上下文信息）"


class NovelContextBuilder:
    """
    小说上下文构建器

    提供流式API构建NovelContext，便于在不同场景下灵活组装上下文。

    示例:
        context = (
            NovelContextBuilder()
            .with_blueprint(blueprint_dict)
            .with_previous_chapters(chapters)
            .with_current_outline(outline)
            .with_rag_context(summaries, states, foreshadowings)
            .build()
        )

        payload = context.to_payload()
    """

    def __init__(self):
        self._blueprint: Dict[str, Any] = {}
        self._previous_chapters: List[Dict[str, Any]] = []
        self._current_outline: Optional[Dict[str, Any]] = None
        self._relevant_summaries: List[str] = []
        self._character_states: List[Dict[str, Any]] = []
        self._foreshadowings: List[Dict[str, Any]] = []
        self._prev_chapter_ending: Optional[str] = None
        self._context_note: str = ""

    def with_blueprint(self, blueprint: Dict[str, Any]) -> "NovelContextBuilder":
        """添加蓝图"""
        self._blueprint = blueprint
        return self

    def with_previous_chapters(
        self,
        chapters: List[Dict[str, Any]],
        limit: Optional[int] = None,
    ) -> "NovelContextBuilder":
        """
        添加前序章节

        Args:
            chapters: 章节列表
            limit: 最多保留的章节数（None表示全部）
        """
        if limit is not None and len(chapters) > limit:
            self._previous_chapters = chapters[-limit:]
        else:
            self._previous_chapters = chapters
        return self

    def with_current_outline(self, outline: Dict[str, Any]) -> "NovelContextBuilder":
        """添加当前章节大纲"""
        self._current_outline = outline
        return self

    def with_relevant_summaries(self, summaries: List[str]) -> "NovelContextBuilder":
        """添加RAG检索的相关摘要"""
        self._relevant_summaries = summaries
        return self

    def with_character_states(self, states: List[Dict[str, Any]]) -> "NovelContextBuilder":
        """添加角色状态"""
        self._character_states = states
        return self

    def with_foreshadowings(self, foreshadowings: List[Dict[str, Any]]) -> "NovelContextBuilder":
        """添加伏笔信息"""
        self._foreshadowings = foreshadowings
        return self

    def with_prev_chapter_ending(self, ending: str) -> "NovelContextBuilder":
        """添加前章结尾"""
        self._prev_chapter_ending = ending
        return self

    def with_context_note(self, note: str) -> "NovelContextBuilder":
        """添加上下文说明"""
        self._context_note = note
        return self

    def with_rag_context(
        self,
        summaries: Optional[List[str]] = None,
        character_states: Optional[List[Dict[str, Any]]] = None,
        foreshadowings: Optional[List[Dict[str, Any]]] = None,
    ) -> "NovelContextBuilder":
        """
        一次性添加所有RAG上下文

        便捷方法，用于一次性设置所有RAG检索结果。
        """
        if summaries:
            self._relevant_summaries = summaries
        if character_states:
            self._character_states = character_states
        if foreshadowings:
            self._foreshadowings = foreshadowings
        return self

    def build(self) -> NovelContext:
        """构建NovelContext实例"""
        return NovelContext(
            blueprint=self._blueprint,
            previous_chapters=self._previous_chapters,
            current_outline=self._current_outline,
            relevant_summaries=self._relevant_summaries,
            character_states=self._character_states,
            foreshadowings=self._foreshadowings,
            prev_chapter_ending=self._prev_chapter_ending,
            context_note=self._context_note,
        )
