"""
Section加载Mixin

负责编程项目Section内容的加载和创建。
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
            'planning': '项目规划',
            'systems': '项目结构',
            'dependencies': '依赖',
            'generated': '已生成',
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
            ProjectPlanningSection,
            SystemsSection,
            DependenciesSection,
            GeneratedSection,
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

        elif section_id == 'planning':
            # 项目规划：核心需求、技术挑战、非功能需求、风险、里程碑
            planning_data = {
                'core_requirements': blueprint.get('core_requirements', []),
                'technical_challenges': blueprint.get('technical_challenges', []),
                'non_functional_requirements': blueprint.get('non_functional_requirements'),
                'risks': blueprint.get('risks', []),
                'milestones': blueprint.get('milestones', []),
            }
            # 调试日志：查看传递给 Section 的数据
            logger.info(
                "planning section data: core_requirements count=%d, "
                "technical_challenges count=%d, blueprint keys=%s",
                len(planning_data.get('core_requirements', [])),
                len(planning_data.get('technical_challenges', [])),
                list(blueprint.keys()) if blueprint else [],
            )
            # 如果有数据，打印第一条用于验证格式
            if planning_data.get('core_requirements'):
                logger.info("Frontend core_requirements[0] = %s", planning_data['core_requirements'][0])
            if planning_data.get('technical_challenges'):
                logger.info("Frontend technical_challenges[0] = %s", planning_data['technical_challenges'][0])
            section = ProjectPlanningSection(data=planning_data, editable=True)
            section.editRequested.connect(self.onEditRequested)

        elif section_id == 'systems':
            # 三层结构：系统 -> 模块 -> 功能
            systems = blueprint.get('systems', [])
            modules = blueprint.get('modules', [])
            features = blueprint.get('features', [])
            section = SystemsSection(
                systems=systems,
                modules=modules,
                features=features,
                project_id=self.project_id,
                editable=True
            )
            section.editRequested.connect(self.onEditRequested)
            section.refreshRequested.connect(self.refreshProject)
            section.navigateToDesk.connect(self._navigateToCodingDesk)
            section.loadingRequested.connect(self.show_loading)
            section.loadingFinished.connect(self.hide_loading)

        elif section_id == 'dependencies':
            dependencies = blueprint.get('dependencies', [])
            modules = blueprint.get('modules', [])
            section = DependenciesSection(
                data=dependencies,
                modules=modules,
                project_id=self.project_id,
                editable=True
            )
            section.editRequested.connect(self.onEditRequested)
            section.refreshRequested.connect(self.refreshProject)
            section.loadingRequested.connect(self.show_loading)
            section.loadingFinished.connect(self.hide_loading)

        elif section_id == 'generated':
            # 编程项目的生成内容存储在 features 中，需要转换为 chapters 格式
            features = blueprint.get('features', [])

            # 筛选已生成内容的功能，并转换为 chapters 格式
            chapters = []
            for f in features:
                # 检查功能是否已生成内容
                has_content = f.get('has_content', False)
                status = f.get('status', 'not_generated')

                # 只显示已生成内容的功能
                if has_content or status in ('generated', 'successful'):
                    chapters.append({
                        'chapter_number': f.get('feature_number', 0),
                        'word_count': 0,  # 字数需要从版本内容获取，暂时为0
                        'versions': [],   # 版本详情需要额外API获取
                        'status': 'generated' if has_content else status,
                        'created_at': '',
                        'version_count': f.get('version_count', 0),
                    })

            section = GeneratedSection(chapters=chapters, features=features)
            section.setProjectId(self.project_id)
            section.dataChanged.connect(self.refreshProject)
            section.navigateToDesk.connect(self._navigateToCodingDesk)

        else:
            section = QLabel("未知Section")

        return section


__all__ = ["SectionLoaderMixin"]
