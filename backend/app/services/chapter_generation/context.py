"""
章节生成上下文

封装章节生成所需的所有数据结构。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..chapter_context_service import EnhancedRAGContext, ChapterRAGContext
    from ..rag.context_builder import BlueprintInfo


@dataclass
class ChapterGenerationContext:
    """
    章节生成上下文，封装生成所需的所有数据

    Attributes:
        outline_dict: 章节大纲字典
        blueprint_info: 蓝图信息对象
        prev_chapter_analysis: 前一章分析数据
        pending_foreshadowing: 待回收伏笔列表
        total_chapters: 总章节数
        enhanced_rag_context: 增强型RAG上下文
        protagonist_profiles: 主角档案列表（用于生成时约束角色行为）
    """
    outline_dict: Dict[str, Any]
    blueprint_info: "BlueprintInfo"
    prev_chapter_analysis: Optional[Any]  # ChapterAnalysisData
    pending_foreshadowing: Optional[List[Dict[str, Any]]]
    total_chapters: int
    enhanced_rag_context: Optional["EnhancedRAGContext"] = None
    protagonist_profiles: Optional[List[Dict[str, Any]]] = None

    @property
    def rag_context(self) -> Optional["ChapterRAGContext"]:
        """
        获取传统RAG上下文（兼容旧接口）

        封装空值检查逻辑，简化调用方代码。

        Returns:
            ChapterRAGContext: 传统RAG上下文，无增强上下文时返回None
        """
        if self.enhanced_rag_context is None:
            return None
        return self.enhanced_rag_context.get_legacy_context()

    @property
    def generation_context(self) -> Optional[Any]:
        """
        获取生成上下文信息

        封装空值检查逻辑，用于提取涉及角色、伏笔等信息。
        Bug 9 修复: 当没有向量库时，返回包含基本伏笔和主角档案的兼容对象。

        Returns:
            生成上下文，无增强上下文时返回包含基本信息的字典
        """
        if self.enhanced_rag_context is not None:
            return self.enhanced_rag_context.generation_context

        # Bug 9 修复: 无向量库时，创建包含伏笔和主角档案的兼容对象
        # 确保 ChapterPromptBuilder 可以获取这些关键信息
        fallback_context = {
            "important": {},
            "protagonist_profiles": self.protagonist_profiles,
        }

        # 将待回收伏笔添加到 important 层
        if self.pending_foreshadowing:
            fallback_context["important"]["high_priority_foreshadowing"] = self.pending_foreshadowing

        return fallback_context


@dataclass
class ChapterGenerationResult:
    """
    章节生成结果

    Attributes:
        contents: 生成的内容列表
        metadata: 元数据列表
        chapter_number: 章节号
        version_count: 版本数量
    """
    contents: List[str]
    metadata: List[Dict]
    chapter_number: int
    version_count: int


__all__ = [
    "ChapterGenerationContext",
    "ChapterGenerationResult",
]
