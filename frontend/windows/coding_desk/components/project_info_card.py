"""
项目信息卡片组件

显示编程项目的基本信息，包括技术栈、统计数据等。
"""

import logging
from typing import Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt

from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp

logger = logging.getLogger(__name__)


class TechStackTag(QLabel):
    """技术栈标签"""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("tech_tag")
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QLabel#tech_tag {{
                background-color: {theme_manager.PRIMARY}15;
                color: {theme_manager.PRIMARY};
                font-size: {dp(10)}px;
                padding: {dp(2)}px {dp(8)}px;
                border-radius: {dp(3)}px;
            }}
        """)


class FlowLayout(QHBoxLayout):
    """简单的流式布局（标签换行）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSpacing(dp(4))
        self.setContentsMargins(0, 0, 0, 0)


class ProjectInfoCard(ThemeAwareFrame):
    """项目信息卡片

    显示：
    - 项目名称
    - 项目类型
    - 技术栈标签
    - 文件统计（模块数/目录数/文件数）
    """

    def __init__(self, parent=None):
        self._project_data: Dict[str, Any] = {}
        self._stats: Dict[str, int] = {
            'modules': 0,
            'directories': 0,
            'files': 0,
        }

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(6))

        # 项目名称
        self.title_label = QLabel("加载中...")
        self.title_label.setObjectName("title")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumHeight(dp(20))
        self.title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self.title_label)

        # 项目类型
        self.type_label = QLabel("")
        self.type_label.setObjectName("type")
        self.type_label.setWordWrap(True)
        self.type_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self.type_label)

        # 技术栈标签容器（使用wrap布局）
        self.tech_container = QWidget()
        self.tech_layout = QHBoxLayout(self.tech_container)
        self.tech_layout.setContentsMargins(0, dp(2), 0, dp(2))
        self.tech_layout.setSpacing(dp(4))
        self.tech_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.tech_container)

        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        divider.setObjectName("divider")
        layout.addWidget(divider)

        # 统计信息
        self.stats_label = QLabel("0 模块 / 0 目录 / 0 文件")
        self.stats_label.setObjectName("stats")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)

    def _apply_theme(self):
        """应用主题"""
        self.setStyleSheet(f"""
            ProjectInfoCard {{
                background-color: {theme_manager.book_bg_primary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
            }}
        """)

        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet(f"""
                font-size: {dp(14)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.3;
            """)

        if hasattr(self, 'type_label'):
            self.type_label.setStyleSheet(f"""
                font-size: {dp(11)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.2;
            """)

        divider = self.findChild(QFrame, "divider")
        if divider:
            divider.setStyleSheet(f"background-color: {theme_manager.BORDER_DEFAULT};")

        if hasattr(self, 'stats_label'):
            self.stats_label.setStyleSheet(f"""
                font-size: {dp(11)}px;
                color: {theme_manager.TEXT_TERTIARY};
            """)

    def set_project_data(self, data: Dict[str, Any]):
        """设置项目数据"""
        self._project_data = data

        # 更新标题
        title = data.get('title', '未命名项目')
        self.title_label.setText(title)
        self.title_label.setToolTip(title)  # 添加tooltip防止截断

        # 更新类型
        blueprint = data.get('blueprint', {})
        project_type = blueprint.get('project_type_desc', '')
        self.type_label.setText(project_type)
        self.type_label.setToolTip(project_type)
        self.type_label.setVisible(bool(project_type))

        # 更新技术栈标签
        self._update_tech_tags(blueprint)

    def _update_tech_tags(self, blueprint: Dict):
        """更新技术栈标签"""
        # 清除现有标签
        while self.tech_layout.count() > 0:
            item = self.tech_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取技术栈
        tech_stack = blueprint.get('tech_stack', {})
        tags = []

        # 主要语言
        if tech_stack.get('primary_language'):
            tags.append(tech_stack['primary_language'])

        # 框架
        frameworks = tech_stack.get('frameworks', [])
        tags.extend(frameworks[:2])  # 最多显示2个框架

        # 添加标签（最多显示4个）
        for tag_text in tags[:4]:
            if tag_text:
                tag = TechStackTag(tag_text)
                self.tech_layout.addWidget(tag)

        self.tech_layout.addStretch()
        self.tech_container.setVisible(len(tags) > 0)

    def set_stats(self, modules: int, directories: int, files: int):
        """设置统计信息"""
        self._stats = {
            'modules': modules,
            'directories': directories,
            'files': files,
        }
        self.stats_label.setText(f"{modules} 模块 / {directories} 目录 / {files} 文件")


__all__ = ["ProjectInfoCard", "TechStackTag"]
