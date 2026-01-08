"""
Section加载Mixin

负责Section内容的加载和创建。

性能优化：
- 分步异步创建Section，避免UI阻塞
- 先显示骨架，再填充内容
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QFrame, QLabel
from PyQt6.QtCore import QTimer

from components.loading_spinner import LoadingOverlay
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

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
        # 如果已缓存，直接显示
        if section_id in self.section_widgets:
            self.content_stack.setCurrentWidget(self.section_widgets[section_id])
            return

        # 显示加载状态
        self._ensure_section_loading_overlay()
        self._section_loading_overlay.show_with_animation(f"加载{self._get_section_display_name(section_id)}...")

        # 第一步：立即创建容器框架（轻量操作）
        scroll, container, layout = self._create_section_skeleton()

        # 缓存并显示骨架
        self.section_widgets[section_id] = scroll
        self.content_stack.addWidget(scroll)
        self.content_stack.setCurrentWidget(scroll)

        # 第二步：延迟创建Section内容（重操作异步执行）
        QTimer.singleShot(8, lambda: self._fill_section_content(section_id, container, layout))

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
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            {theme_manager.scrollbar()}
        """)
        # 设置viewport透明背景
        if scroll.viewport():
            scroll.viewport().setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        scroll.setWidget(container)
        return scroll, container, layout

    def _fill_section_content(self: "NovelDetail", section_id, container, layout):
        """填充Section内容（异步执行）

        注意：此方法由QTimer异步调用，需要检查对象是否仍然有效
        """
        try:
            # 安全检查：确保布局和容器对象仍然存在
            # 使用 sip.isdeleted 或捕获 RuntimeError 来检测已删除的对象
            try:
                # 尝试访问布局属性来检测是否已删除
                _ = layout.count()
                _ = container.isVisible()
            except RuntimeError:
                # 对象已被删除，静默退出
                logger.debug("Section '%s' 的布局已被删除，跳过填充", section_id)
                return

            section = self._create_section_content(section_id)
            if section:
                layout.addWidget(section, stretch=1)
        except RuntimeError as e:
            # C++对象已删除，静默处理
            logger.debug("填充Section '%s' 时对象已删除: %s", section_id, str(e))
        except Exception as e:
            logger.error("创建Section '%s' 时出错: %s", section_id, str(e), exc_info=True)
            # 创建一个错误提示widget（需要再次检查布局有效性）
            try:
                _ = layout.count()  # 检查布局是否有效
                error_label = QLabel(f"加载 {section_id} 失败: {str(e)}")
                error_label.setWordWrap(True)
                error_label.setStyleSheet(f"color: {theme_manager.ERROR}; padding: {dp(20)}px; background-color: transparent;")
                layout.addWidget(error_label)
            except RuntimeError:
                # 布局已删除，无法添加错误提示
                pass
        finally:
            # 隐藏加载状态
            if hasattr(self, '_section_loading_overlay') and self._section_loading_overlay:
                try:
                    self._section_loading_overlay.hide_with_animation()
                except RuntimeError:
                    # 遮罩层也可能已被删除
                    pass

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
