"""
Section加载Mixin

负责Section内容的加载和创建。

性能优化：
- 分步异步创建Section，避免UI阻塞
- 先显示骨架，再填充内容
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QLabel

from components.loading_spinner import LoadingOverlay
from windows.base.detail_page import BaseDetailPage

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class SectionLoaderMixin:
    """
    Section加载Mixin

    负责：
    - 加载Section内容
    - 创建Section widget
    - 提供安全的数据获取方法
    """

    def _ensure_section_loading_overlay(self: "NovelDetail"):
        """确保加载遮罩存在"""
        if not hasattr(self, '_section_loading_overlay') or not self._section_loading_overlay:
            self._section_loading_overlay = LoadingOverlay(
                text="加载中...",
                parent=self.content_stack
            )

    def loadSection(self: "NovelDetail", section_id):
        """加载Section内容

        性能优化：使用分步异步加载
        """
        BaseDetailPage.load_section(self, section_id)

    def _get_section_display_name(self: "NovelDetail", section_id: str) -> str:
        """获取Section显示名称"""
        names = {
            'overview': '概览',
            'world_setting': '世界观',
            'characters': '角色',
            'relationships': '关系',
            'chapter_outline': '章节大纲',
            'chapters': '已生成章节',
        }
        return names.get(section_id, section_id)

    def _create_section_skeleton(self: "NovelDetail"):
        """创建Section骨架（轻量操作，立即执行）"""
        return BaseDetailPage._create_section_skeleton(self)

    def _fill_section_content(self: "NovelDetail", section_id, container, layout):
        """填充Section内容（异步执行）

        注意：此方法由QTimer异步调用，需要检查对象是否仍然有效
        """
        return BaseDetailPage._fill_section_content(self, section_id, container, layout)

    def create_section_content(self: "NovelDetail", section_id: str):
        """适配 BaseDetailPage 的Section创建入口，复用既有实现"""
        return self._create_section_content(section_id)

    def _create_section_content(self: "NovelDetail", section_id):
        """创建Section内容组件"""
        from ..sections import (
            OverviewSection,
            WorldSettingSection,
            CharactersSection,
            RelationshipsSection,
            ChaptersSection,
        )
        from ..chapter_outline import ChapterOutlineSection

        section = None

        # 根据section_id创建对应组件
        if section_id == 'overview':
            blueprint = self._safe_get_blueprint()
            section = OverviewSection(data=blueprint, editable=True)
            section.editRequested.connect(self.onEditRequested)
        elif section_id == 'world_setting':
            world_setting = self._safe_get_nested(self._safe_get_blueprint(), 'world_setting', {})
            section = WorldSettingSection(data=world_setting, editable=True)
            section.editRequested.connect(self.onEditRequested)
        elif section_id == 'characters':
            characters = self._safe_get_nested(self._safe_get_blueprint(), 'characters', [])
            # 确保是列表
            if not isinstance(characters, list):
                logger.warning("characters数据类型错误，期望list，实际为%s，使用空列表", type(characters).__name__)
                characters = []
            section = CharactersSection(data=characters, editable=True, project_id=self.project_id)
            section.editRequested.connect(self.onEditRequested)
        elif section_id == 'relationships':
            relationships = self._safe_get_nested(self._safe_get_blueprint(), 'relationships', [])
            # 确保是列表
            if not isinstance(relationships, list):
                logger.warning("relationships数据类型错误，期望list，实际为%s，使用空列表", type(relationships).__name__)
                relationships = []
            section = RelationshipsSection(data=relationships, editable=True)
            section.editRequested.connect(self.onEditRequested)
        elif section_id == 'chapter_outline':
            blueprint = self._safe_get_blueprint()
            # 章节大纲在 blueprint.chapter_outline 中
            outline = self._safe_get_nested(blueprint, 'chapter_outline', [])
            # 确保是列表
            if not isinstance(outline, list):
                logger.warning("chapter_outline数据类型错误，期望list，实际为%s，使用空列表", type(outline).__name__)
                outline = []

            # 调试日志
            logger.info(
                f"创建ChapterOutlineSection: "
                f"blueprint存在={bool(blueprint)}, "
                f"outline章节数={len(outline)}, "
                f"needs_part_outlines={blueprint.get('needs_part_outlines', False)}"
            )

            # 获取保存的tab状态（如果有）
            initial_tab_index = 0
            if hasattr(self, '_saved_section_state') and self._saved_section_state:
                initial_tab_index = self._saved_section_state.get('tab_index', 0)
                logger.info(f"使用保存的tab索引: {initial_tab_index}")
                # 使用后清除，避免影响其他刷新
                self._saved_section_state = {}

            section = ChapterOutlineSection(
                outline=outline,
                blueprint=blueprint,
                project_id=self.project_id,
                editable=True,
                initial_tab_index=initial_tab_index
            )
            section.editRequested.connect(self.onEditRequested)
            section.refreshRequested.connect(self.refreshProject)
        elif section_id == 'chapters':
            chapters = self._safe_get_data('chapters', [])
            # 确保是列表
            if not isinstance(chapters, list):
                logger.warning("chapters数据类型错误，期望list，实际为%s，使用空列表", type(chapters).__name__)
                chapters = []
            section = ChaptersSection(chapters=chapters)
            section.setProjectId(self.project_id)
            section.dataChanged.connect(self.refreshProject)
        else:
            section = QLabel("未知Section")

        return section

    def _safe_get_blueprint(self: "NovelDetail"):
        """安全获取蓝图数据（小说项目专用）"""
        if not self.project_data:
            return {}
        blueprint = self.project_data.get('blueprint')
        if blueprint is None or not isinstance(blueprint, dict):
            return {}
        return blueprint

    def _safe_get_data(self: "NovelDetail", key, default=None):
        """安全获取项目数据"""
        if not self.project_data:
            return default
        return self.project_data.get(key, default)

    def _safe_get_nested(self: "NovelDetail", data, key, default=None):
        """安全获取嵌套数据"""
        if not data or not isinstance(data, dict):
            return default
        return data.get(key, default)


__all__ = [
    "SectionLoaderMixin",
]
