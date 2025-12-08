"""
蓝图展示组件

展示生成的蓝图详细信息
"""

from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QFrame, QWidget, QLabel
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager


class BlueprintDisplay(ThemeAwareWidget):
    """蓝图展示组件"""

    def __init__(self, blueprint=None, parent=None):
        self.blueprint = blueprint or {}

        # 保存组件引用
        self.scroll = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(24, 24, 24, 24)
        container_layout.setSpacing(16)

        # 展示蓝图各个字段
        fields = [
            ('title', '标题'),
            ('one_sentence_summary', '核心摘要'),
            ('genre', '类型'),
            ('style', '风格'),
            ('tone', '基调'),
            ('target_audience', '目标受众'),
            ('full_synopsis', '完整剧情'),
        ]

        for field_key, field_label in fields:
            value = self.blueprint.get(field_key, '')
            if value:
                field_widget = self.createFieldWidget(field_label, value)
                container_layout.addWidget(field_widget)

        container_layout.addStretch()

        self.scroll.setWidget(container)
        layout.addWidget(self.scroll)

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        if self.scroll:
            self.scroll.setStyleSheet(theme_manager.scrollbar())

    def createFieldWidget(self, label, value):
        """创建字段展示widget"""
        # 使用 theme_manager 的便捷方法
        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        widget = QFrame()
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_MD};
                padding: 16px;
            }}
        """)

        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        # 标签
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {theme_manager.FONT_SIZE_XS};
            font-weight: {theme_manager.FONT_WEIGHT_BOLD};
            color: {theme_manager.TEXT_SECONDARY};
        """)
        layout.addWidget(label_widget)

        # 值
        value_widget = QLabel(str(value))
        value_widget.setWordWrap(True)
        value_widget.setStyleSheet(f"""
            font-family: {serif_font};
            font-size: {theme_manager.FONT_SIZE_SM};
            color: {theme_manager.TEXT_PRIMARY};
            line-height: 1.6;
        """)
        layout.addWidget(value_widget)

        return widget

    def setBlueprint(self, blueprint):
        """更新蓝图数据并重新渲染"""
        self.blueprint = blueprint

        # 获取容器和布局
        container = self.scroll.widget()
        layout = container.layout()

        # 清空现有字段widget（保留stretch）
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 重新渲染字段
        fields = [
            ('title', '标题'),
            ('one_sentence_summary', '核心摘要'),
            ('genre', '类型'),
            ('style', '风格'),
            ('tone', '基调'),
            ('target_audience', '目标受众'),
            ('full_synopsis', '完整剧情'),
        ]

        for field_key, field_label in fields:
            value = self.blueprint.get(field_key, '')
            if value:
                field_widget = self.createFieldWidget(field_label, value)
                # 插入到stretch之前
                layout.insertWidget(layout.count() - 1, field_widget)
