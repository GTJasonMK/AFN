"""
Section加载Mixin

负责编程项目Section内容的加载和创建。
重构版：适配4个Tab（概览、架构设计、目录结构、生成管理）
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QFrame, QLabel
from PyQt6.QtCore import QTimer

from components.loading_spinner import LoadingOverlay
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

if TYPE_CHECKING:
    from ..main import CodingDetail

logger = logging.getLogger(__name__)


class SectionLoaderMixin:
    """Section加载Mixin

    负责：
    - 加载Section内容
    - 创建Section widget
    - 提供数据获取方法
    """

    def _ensure_section_loading_overlay(self: "CodingDetail"):
        """确保加载遮罩存在"""
        if not hasattr(self, '_section_loading_overlay') or not self._section_loading_overlay:
            self._section_loading_overlay = LoadingOverlay(
                text="加载中...",
                parent=self.content_stack
            )

    def loadSection(self: "CodingDetail", section_id):
        """加载Section内容"""
        # 如果已缓存，直接显示
        if section_id in self.section_widgets:
            self.content_stack.setCurrentWidget(self.section_widgets[section_id])
            return

        # 显示加载状态
        self._ensure_section_loading_overlay()
        self._section_loading_overlay.show_with_animation(f"加载{self._get_section_display_name(section_id)}...")

        # 创建Section骨架
        scroll, container, layout = self._create_section_skeleton()

        # 缓存并显示
        self.section_widgets[section_id] = scroll
        self.content_stack.addWidget(scroll)
        self.content_stack.setCurrentWidget(scroll)

        # 延迟填充内容
        QTimer.singleShot(8, lambda: self._fill_section_content(section_id, container, layout))

    def _get_section_display_name(self: "CodingDetail", section_id: str) -> str:
        """获取Section显示名称"""
        names = {
            'overview': '概览',
            'architecture': '架构设计',
            'directory': '目录结构',
            'generation': '生成管理',
        }
        return names.get(section_id, section_id)

    def _create_section_skeleton(self: "CodingDetail"):
        """创建Section骨架"""
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

        if scroll.viewport():
            scroll.viewport().setStyleSheet("background-color: transparent;")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(dp(24), dp(24), dp(24), dp(24))
        layout.setSpacing(dp(20))

        scroll.setWidget(container)
        return scroll, container, layout

    def _fill_section_content(self: "CodingDetail", section_id, container, layout):
        """填充Section内容"""
        try:
            # 检查对象有效性
            try:
                _ = layout.count()
                _ = container.isVisible()
            except RuntimeError:
                logger.debug("Section '%s' 的布局已被删除", section_id)
                return

            section = self._create_section_content(section_id)
            if section:
                layout.addWidget(section, stretch=1)

        except RuntimeError as e:
            logger.debug("填充Section '%s' 时对象已删除: %s", section_id, str(e))
        except Exception as e:
            logger.error("创建Section '%s' 时出错: %s", section_id, str(e), exc_info=True)
            try:
                _ = layout.count()
                error_label = QLabel(f"加载 {section_id} 失败: {str(e)}")
                error_label.setWordWrap(True)
                error_label.setStyleSheet(f"color: {theme_manager.ERROR}; padding: {dp(20)}px; background-color: transparent;")
                layout.addWidget(error_label)
            except RuntimeError:
                pass
        finally:
            if hasattr(self, '_section_loading_overlay') and self._section_loading_overlay:
                try:
                    self._section_loading_overlay.hide_with_animation()
                except RuntimeError:
                    pass

    def _create_section_content(self: "CodingDetail", section_id):
        """创建Section内容组件"""
        from ..sections import (
            CodingOverviewSection,
            ArchitectureSection,
            DirectorySection,
            GenerationSection,
        )

        blueprint = self.get_blueprint()
        section = None

        if section_id == 'overview':
            section = CodingOverviewSection(
                data=blueprint,
                editable=True,
                project_id=self.project_id
            )
            section.editRequested.connect(self.onEditRequested)
            section.regenerateBlueprintRequested.connect(self._on_regenerate_blueprint)

        elif section_id == 'architecture':
            # 架构设计：合并蓝图展示 + 两层结构（系统/模块）
            systems = blueprint.get('systems', [])
            modules = blueprint.get('modules', [])
            planning_data = {
                'core_requirements': blueprint.get('core_requirements', []),
                'technical_challenges': blueprint.get('technical_challenges', []),
                'non_functional_requirements': blueprint.get('non_functional_requirements'),
                'risks': blueprint.get('risks', []),
                'milestones': blueprint.get('milestones', []),
            }
            section = ArchitectureSection(
                blueprint=blueprint,
                planning_data=planning_data,
                systems=systems,
                modules=modules,
                project_id=self.project_id,
                editable=True
            )
            section.editRequested.connect(self.onEditRequested)
            section.refreshRequested.connect(self.refreshProject)
            section.loadingRequested.connect(self.show_loading)
            section.loadingFinished.connect(self.hide_loading)

        elif section_id == 'directory':
            # 目录结构：DirectorySection会自动加载目录树数据
            modules = blueprint.get('modules', [])
            section = DirectorySection(
                modules=modules,
                project_id=self.project_id,
                editable=True
            )
            section.refreshRequested.connect(self.refreshProject)
            section.loadingRequested.connect(self.show_loading)
            section.loadingFinished.connect(self.hide_loading)
            section.fileClicked.connect(self._on_file_clicked)

        elif section_id == 'generation':
            # 生成管理：合并依赖关系 + 已生成文件 + RAG状态
            dependencies = blueprint.get('dependencies', [])
            modules = blueprint.get('modules', [])
            features = blueprint.get('features', [])
            section = GenerationSection(
                dependencies=dependencies,
                modules=modules,
                features=features,
                project_id=self.project_id,
                editable=True
            )
            section.editRequested.connect(self.onEditRequested)
            section.refreshRequested.connect(self.refreshProject)
            section.loadingRequested.connect(self.show_loading)
            section.loadingFinished.connect(self.hide_loading)

        else:
            section = QLabel("未知Section")

        return section


__all__ = ["SectionLoaderMixin"]
