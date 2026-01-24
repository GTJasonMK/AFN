"""
Section加载Mixin

负责编程项目Section内容的加载和创建。
重构版：适配4个Tab（概览、架构设计、目录结构、生成管理）
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QLabel

from components.loading_spinner import LoadingOverlay
from windows.base.detail_page import BaseDetailPage

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
        BaseDetailPage.load_section(self, section_id)

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
        return BaseDetailPage._create_section_skeleton(self)

    def _fill_section_content(self: "CodingDetail", section_id, container, layout):
        """填充Section内容"""
        return BaseDetailPage._fill_section_content(self, section_id, container, layout)

    def create_section_content(self: "CodingDetail", section_id: str):
        """适配 BaseDetailPage 的Section创建入口，复用既有实现"""
        return self._create_section_content(section_id)

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
