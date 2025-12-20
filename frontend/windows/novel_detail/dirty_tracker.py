"""
脏数据追踪器

追踪项目详情页中未保存的修改，支持批量保存。
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FieldChange:
    """字段修改记录"""
    section: str           # 所属section（overview, world_setting, characters等）
    field: str            # 字段名
    original_value: Any   # 原始值
    current_value: Any    # 当前值


@dataclass
class ChapterOutlineChange:
    """章节大纲修改记录"""
    chapter_number: int
    original_title: str
    original_summary: str
    current_title: str
    current_summary: str


class DirtyTracker:
    """脏数据追踪器

    追踪项目详情页中的未保存修改，包括：
    - 蓝图字段（概览、世界观等）
    - 章节大纲（标题、摘要）

    使用方式：
        tracker = DirtyTracker()

        # 记录字段修改
        tracker.mark_field_dirty("overview", "title", "原标题", "新标题")

        # 记录章节大纲修改
        tracker.mark_outline_dirty(1, "原标题", "原摘要", "新标题", "新摘要")

        # 检查是否有修改
        if tracker.is_dirty():
            dirty_data = tracker.get_dirty_data()
            # 调用批量保存API...

        # 保存成功后重置
        tracker.reset()
    """

    def __init__(self):
        # 蓝图字段修改记录：field -> FieldChange
        self._field_changes: Dict[str, FieldChange] = {}

        # 章节大纲修改记录：chapter_number -> ChapterOutlineChange
        self._outline_changes: Dict[int, ChapterOutlineChange] = {}

        # 标记为需要删除的章节大纲
        self._deleted_outlines: Set[int] = set()

        # 新增的章节大纲
        self._new_outlines: Dict[int, ChapterOutlineChange] = {}

    def mark_field_dirty(
        self,
        section: str,
        field: str,
        original_value: Any,
        current_value: Any
    ) -> None:
        """标记字段为已修改

        Args:
            section: 所属section
            field: 字段名
            original_value: 原始值
            current_value: 当前值
        """
        # 如果新值等于原始值，移除修改记录
        if self._values_equal(original_value, current_value):
            if field in self._field_changes:
                del self._field_changes[field]
                logger.debug("字段 %s 恢复原值，移除修改记录", field)
            return

        # 检查是否已有该字段的修改记录
        if field in self._field_changes:
            existing = self._field_changes[field]
            # 如果新值等于原始值，移除记录
            if self._values_equal(existing.original_value, current_value):
                del self._field_changes[field]
                logger.debug("字段 %s 恢复原值，移除修改记录", field)
                return
            # 否则更新当前值
            existing.current_value = current_value
            logger.debug("更新字段 %s 的当前值", field)
        else:
            # 新建修改记录
            self._field_changes[field] = FieldChange(
                section=section,
                field=field,
                original_value=original_value,
                current_value=current_value
            )
            logger.debug("标记字段 %s 为已修改: %s -> %s", field, original_value, current_value)

    def mark_outline_dirty(
        self,
        chapter_number: int,
        original_title: str,
        original_summary: str,
        current_title: str,
        current_summary: str,
        is_new: bool = False
    ) -> None:
        """标记章节大纲为已修改

        Args:
            chapter_number: 章节号
            original_title: 原标题
            original_summary: 原摘要
            current_title: 当前标题
            current_summary: 当前摘要
            is_new: 是否为新增大纲
        """
        # 检查是否有实际修改
        title_changed = original_title != current_title
        summary_changed = original_summary != current_summary

        if not title_changed and not summary_changed and not is_new:
            # 没有修改，移除记录
            if chapter_number in self._outline_changes:
                del self._outline_changes[chapter_number]
            if chapter_number in self._new_outlines:
                del self._new_outlines[chapter_number]
            return

        change = ChapterOutlineChange(
            chapter_number=chapter_number,
            original_title=original_title,
            original_summary=original_summary,
            current_title=current_title,
            current_summary=current_summary
        )

        if is_new:
            self._new_outlines[chapter_number] = change
            logger.debug("标记章节 %d 为新增", chapter_number)
        else:
            self._outline_changes[chapter_number] = change
            logger.debug("标记章节 %d 大纲为已修改", chapter_number)

    def mark_outline_deleted(self, chapter_number: int) -> None:
        """标记章节大纲为待删除

        Args:
            chapter_number: 章节号
        """
        self._deleted_outlines.add(chapter_number)
        # 如果在新增列表中，直接移除
        if chapter_number in self._new_outlines:
            del self._new_outlines[chapter_number]
            self._deleted_outlines.discard(chapter_number)
        # 如果在修改列表中，移除修改记录
        if chapter_number in self._outline_changes:
            del self._outline_changes[chapter_number]
        logger.debug("标记章节 %d 为待删除", chapter_number)

    def unmark_outline_deleted(self, chapter_number: int) -> None:
        """取消章节大纲的删除标记"""
        self._deleted_outlines.discard(chapter_number)

    def is_dirty(self) -> bool:
        """检查是否有未保存的修改"""
        return bool(
            self._field_changes or
            self._outline_changes or
            self._new_outlines or
            self._deleted_outlines
        )

    def get_dirty_count(self) -> int:
        """获取未保存修改的数量"""
        return (
            len(self._field_changes) +
            len(self._outline_changes) +
            len(self._new_outlines) +
            len(self._deleted_outlines)
        )

    def get_dirty_summary(self) -> str:
        """获取修改摘要（用于显示）"""
        parts = []
        if self._field_changes:
            parts.append(f"{len(self._field_changes)}个字段")
        if self._outline_changes:
            parts.append(f"{len(self._outline_changes)}个大纲修改")
        if self._new_outlines:
            parts.append(f"{len(self._new_outlines)}个新大纲")
        if self._deleted_outlines:
            parts.append(f"{len(self._deleted_outlines)}个待删除")
        return "、".join(parts) if parts else "无修改"

    def get_dirty_data(self) -> Dict[str, Any]:
        """获取所有脏数据，用于批量保存API

        Returns:
            dict: {
                "blueprint_updates": {field: value, ...},
                "chapter_outline_updates": [
                    {"chapter_number": 1, "title": "...", "summary": "..."},
                    ...
                ]
            }
        """
        result = {}

        # 蓝图字段更新
        if self._field_changes:
            blueprint_updates = {}
            for field, change in self._field_changes.items():
                blueprint_updates[field] = change.current_value
            result["blueprint_updates"] = blueprint_updates

        # 章节大纲更新（包括修改和新增）
        outline_updates = []

        for chapter_number, change in self._outline_changes.items():
            outline_updates.append({
                "chapter_number": change.chapter_number,
                "title": change.current_title,
                "summary": change.current_summary
            })

        for chapter_number, change in self._new_outlines.items():
            outline_updates.append({
                "chapter_number": change.chapter_number,
                "title": change.current_title,
                "summary": change.current_summary
            })

        if outline_updates:
            # 按章节号排序
            outline_updates.sort(key=lambda x: x["chapter_number"])
            result["chapter_outline_updates"] = outline_updates

        return result

    def get_deleted_outlines(self) -> List[int]:
        """获取待删除的章节大纲列表"""
        return sorted(list(self._deleted_outlines))

    def reset(self) -> None:
        """重置所有修改记录（保存成功后调用）"""
        self._field_changes.clear()
        self._outline_changes.clear()
        self._new_outlines.clear()
        self._deleted_outlines.clear()
        logger.debug("脏数据追踪器已重置")

    def _values_equal(self, v1: Any, v2: Any) -> bool:
        """比较两个值是否相等（处理None和空字符串）"""
        # None 和 "" 视为相等
        if v1 is None:
            v1 = ""
        if v2 is None:
            v2 = ""

        # 字符串比较时去除首尾空白
        if isinstance(v1, str) and isinstance(v2, str):
            return v1.strip() == v2.strip()

        return v1 == v2

    def get_field_changes(self) -> Dict[str, FieldChange]:
        """获取所有字段修改记录（用于调试）"""
        return self._field_changes.copy()

    def get_outline_changes(self) -> Dict[int, ChapterOutlineChange]:
        """获取所有大纲修改记录（用于调试）"""
        return self._outline_changes.copy()
