"""
增强型查询构建器

负责构建多维度的RAG查询，从章节大纲、蓝图、前一章分析数据和待回收伏笔中
提取多个查询维度，提高检索的精准度和召回率。
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from ...schemas.novel import (
    ChapterAnalysisData,
    ForeshadowingItem,
)
from .utils import extract_involved_characters, build_outline_text


@dataclass
class EnhancedQuery:
    """增强型查询结构

    包含多个维度的查询，用于从不同角度检索相关内容：
    - main_query: 基于章节大纲的主查询
    - character_queries: 涉及角色的历史状态查询
    - foreshadow_queries: 需要回收的伏笔查询
    - location_query: 场景相关查询
    - entity_hints: 实体提示（用于增强检索）
    """
    main_query: str
    character_queries: List[str] = field(default_factory=list)
    foreshadow_queries: List[str] = field(default_factory=list)
    location_query: Optional[str] = None
    entity_hints: Dict[str, List[str]] = field(default_factory=dict)

    def get_all_queries(self) -> List[str]:
        """获取所有查询列表"""
        queries = [self.main_query]
        queries.extend(self.character_queries)
        queries.extend(self.foreshadow_queries)
        if self.location_query:
            queries.append(self.location_query)
        return queries

    def get_combined_query(self, separator: str = "\n") -> str:
        """获取合并后的查询文本"""
        return separator.join(self.get_all_queries())


class EnhancedQueryBuilder:
    """增强型查询构建器

    从多个数据源提取信息，构建多维度的查询，用于RAG检索。

    数据源包括：
    1. 章节大纲（title, summary, writing_notes）
    2. 蓝图角色信息（用于实体匹配）
    3. 前一章分析数据（用于状态延续）
    4. 待回收伏笔列表
    """

    def __init__(
        self,
        character_query_limit: int = 3,
        foreshadow_query_limit: int = 2,
    ):
        """
        Args:
            character_query_limit: 角色查询数量限制
            foreshadow_query_limit: 伏笔查询数量限制
        """
        self.character_query_limit = character_query_limit
        self.foreshadow_query_limit = foreshadow_query_limit

    def build_queries(
        self,
        outline: Dict[str, Any],
        blueprint_characters: List[Dict[str, Any]],
        prev_chapter_analysis: Optional[ChapterAnalysisData] = None,
        pending_foreshadowing: Optional[List[Dict[str, Any]]] = None,
        writing_notes: Optional[str] = None,
    ) -> EnhancedQuery:
        """
        构建多维查询

        Args:
            outline: 章节大纲 {"chapter_number": int, "title": str, "summary": str}
            blueprint_characters: 蓝图角色列表 [{"name": str, "identity": str, ...}]
            prev_chapter_analysis: 前一章的分析数据
            pending_foreshadowing: 待回收的伏笔列表
            writing_notes: 用户的写作指令

        Returns:
            EnhancedQuery: 多维查询结构
        """
        # 1. 构建主查询
        main_query = self._build_main_query(outline, writing_notes)

        # 2. 提取并构建角色查询
        involved_characters = self._extract_involved_characters(
            outline, blueprint_characters
        )
        character_queries = self._build_character_queries(
            involved_characters, prev_chapter_analysis
        )

        # 3. 构建伏笔查询
        foreshadow_queries = self._build_foreshadow_queries(
            outline, pending_foreshadowing
        )

        # 4. 构建场景查询
        location_query = self._build_location_query(outline, prev_chapter_analysis)

        # 5. 提取实体提示
        entity_hints = self._extract_entity_hints(
            involved_characters, outline, prev_chapter_analysis
        )

        return EnhancedQuery(
            main_query=main_query,
            character_queries=character_queries,
            foreshadow_queries=foreshadow_queries,
            location_query=location_query,
            entity_hints=entity_hints,
        )

    def _build_main_query(
        self,
        outline: Dict[str, Any],
        writing_notes: Optional[str] = None,
    ) -> str:
        """构建主查询（基于章节大纲）"""
        parts = []

        chapter_number = outline.get("chapter_number", "")
        title = outline.get("title", "")
        summary = outline.get("summary", "")

        if title:
            parts.append(f"章节标题: {title}")

        if summary:
            parts.append(f"章节摘要: {summary}")

        if writing_notes:
            parts.append(f"写作要点: {writing_notes}")

        return "\n".join(parts) if parts else f"第{chapter_number}章"

    def _extract_involved_characters(
        self,
        outline: Dict[str, Any],
        blueprint_characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """从大纲中提取涉及的角色

        通过匹配角色名称在大纲文本中出现来确定涉及的角色
        """
        return extract_involved_characters(
            outline=outline,
            blueprint_characters=blueprint_characters,
            include_details=False,
        )

    def _build_character_queries(
        self,
        involved_characters: List[Dict[str, Any]],
        prev_chapter_analysis: Optional[ChapterAnalysisData] = None,
    ) -> List[str]:
        """构建角色相关查询"""
        queries = []

        # 限制查询数量
        chars_to_query = involved_characters[:self.character_query_limit]

        for char in chars_to_query:
            char_name = char.get("name", "")
            if not char_name:
                continue

            # 基本角色查询
            query_parts = [f"角色 {char_name}"]

            # 如果有前一章的角色状态，添加状态信息
            if prev_chapter_analysis and prev_chapter_analysis.character_states:
                char_state = prev_chapter_analysis.character_states.get(char_name)
                if char_state:
                    if char_state.location:
                        query_parts.append(f"位于{char_state.location}")
                    if char_state.status:
                        query_parts.append(f"状态:{char_state.status}")

            query_parts.append("的行动和状态变化")
            queries.append(" ".join(query_parts))

        return queries

    def _build_foreshadow_queries(
        self,
        outline: Dict[str, Any],
        pending_foreshadowing: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """构建伏笔相关查询

        选择与当前章节可能相关的伏笔进行查询
        """
        if not pending_foreshadowing:
            return []

        queries = []
        outline_text = build_outline_text(outline).lower()

        # 按优先级排序伏笔
        sorted_foreshadowing = sorted(
            pending_foreshadowing,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(
                x.get("priority", "medium"), 1
            )
        )

        for fs in sorted_foreshadowing:
            if len(queries) >= self.foreshadow_query_limit:
                break

            description = fs.get("description", "")
            if not description:
                continue

            # 检查伏笔是否可能与当前章节相关
            if self._should_include_foreshadow(fs, outline_text):
                queries.append(f"伏笔: {description}")

        return queries

    def _should_include_foreshadow(
        self,
        foreshadow: Dict[str, Any],
        outline_text: str,
    ) -> bool:
        """判断伏笔是否应该包含在查询中

        基于以下条件：
        1. 高优先级伏笔总是包含
        2. 伏笔描述或关联实体与大纲文本有重叠
        """
        priority = foreshadow.get("priority", "medium")

        # 高优先级总是包含
        if priority == "high":
            return True

        # 检查描述关键词
        description = foreshadow.get("description", "").lower()
        if any(word in outline_text for word in description.split() if len(word) > 1):
            return True

        # 检查关联实体
        related_entities = foreshadow.get("related_entities", [])
        for entity in related_entities:
            if entity.lower() in outline_text:
                return True

        return False

    def _build_location_query(
        self,
        outline: Dict[str, Any],
        prev_chapter_analysis: Optional[ChapterAnalysisData] = None,
    ) -> Optional[str]:
        """构建场景相关查询"""
        outline_text = build_outline_text(outline)

        # 尝试从大纲中提取地点
        location = self._extract_location_from_text(outline_text)

        # 如果没有从大纲提取到，尝试从前一章分析中获取
        if not location and prev_chapter_analysis:
            if prev_chapter_analysis.metadata and prev_chapter_analysis.metadata.locations:
                # 使用前一章的最后一个地点
                location = prev_chapter_analysis.metadata.locations[-1]

        if location:
            return f"场景 {location} 中发生的事件"

        return None

    def _extract_location_from_text(self, text: str) -> Optional[str]:
        """从文本中提取地点

        使用简单的模式匹配提取常见的地点表述
        """
        # 常见地点模式
        patterns = [
            r"在(.{2,10}?)(?:中|里|内|上|下|旁|边)",
            r"来到(.{2,10})",
            r"抵达(.{2,10})",
            r"前往(.{2,10})",
            r"回到(.{2,10})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                location = match.group(1).strip()
                # 过滤掉太短或太长的结果
                if 2 <= len(location) <= 10:
                    return location

        return None

    def _extract_entity_hints(
        self,
        involved_characters: List[Dict[str, Any]],
        outline: Dict[str, Any],
        prev_chapter_analysis: Optional[ChapterAnalysisData] = None,
    ) -> Dict[str, List[str]]:
        """提取实体提示，用于增强检索"""
        hints = {
            "characters": [],
            "locations": [],
            "items": [],
        }

        # 角色提示
        for char in involved_characters:
            char_name = char.get("name")
            if char_name:
                hints["characters"].append(char_name)
                # 添加身份作为别名
                identity = char.get("identity")
                if identity:
                    hints["characters"].append(f"{char_name}({identity})")

        # 从前一章分析中获取地点和物品提示
        if prev_chapter_analysis and prev_chapter_analysis.metadata:
            if prev_chapter_analysis.metadata.locations:
                hints["locations"].extend(prev_chapter_analysis.metadata.locations)
            if prev_chapter_analysis.metadata.items:
                hints["items"].extend(prev_chapter_analysis.metadata.items)

        return hints


class EntityAwareQueryEnhancer:
    """基于实体的查询增强器

    使用蓝图信息增强查询，添加实体标注以提高检索精度

    注意: 此类是RAG优化计划的一部分（见RAG_OPTIMIZATION_PLAN.md Phase 2），
    目前尚未集成到主流程中，保留用于后续优化。
    """

    def enhance_query(
        self,
        base_query: str,
        blueprint_characters: List[Dict[str, Any]],
        world_setting: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        使用蓝图信息增强查询

        Args:
            base_query: 基础查询文本
            blueprint_characters: 蓝图角色列表
            world_setting: 世界观设定

        Returns:
            增强后的查询文本
        """
        enhancements = []

        # 提取查询中提到的角色并添加身份标注
        for char in blueprint_characters:
            char_name = char.get("name", "")
            if char_name and char_name in base_query:
                identity = char.get("identity", "")
                if identity:
                    enhancements.append(f"[角色:{char_name}|{identity}]")
                else:
                    enhancements.append(f"[角色:{char_name}]")

        # 提取地点标注
        if world_setting:
            key_locations = world_setting.get("key_locations", [])
            for loc in key_locations:
                loc_name = loc.get("name", "") if isinstance(loc, dict) else str(loc)
                if loc_name and loc_name in base_query:
                    enhancements.append(f"[地点:{loc_name}]")

        # 合并增强信息
        if enhancements:
            return f"{base_query}\n关联实体: {' '.join(enhancements)}"

        return base_query
