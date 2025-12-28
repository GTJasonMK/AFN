"""
蓝图展示组件

展示生成的蓝图详细信息
"""

from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QFrame, QWidget, QLabel
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes.transparency_aware_mixin import TransparencyAwareMixin
from themes.transparency_tokens import OpacityTokens


class BlueprintDisplay(TransparencyAwareMixin, ThemeAwareWidget):
    """蓝图展示组件

    使用 TransparencyAwareMixin 提供透明度控制能力。
    """

    # 透明度组件标识符
    _transparency_component_id = "content"

    def __init__(self, blueprint=None, parent=None):
        self.blueprint = blueprint or {}

        # 保存组件引用
        self.scroll = None
        self._field_widgets = []  # 保存字段组件引用

        super().__init__(parent)
        self._init_transparency_state()  # 初始化透明度状态
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
        """应用主题样式 - 使用TransparencyAwareMixin"""
        # 应用透明度效果
        self._apply_transparency()

        if self.scroll:
            self.scroll.setStyleSheet(theme_manager.scrollbar())

            # 透明模式下使滚动区域透明
            if self._transparency_enabled:
                self.scroll.viewport().setStyleSheet("background-color: transparent;")
                self._make_widget_transparent(self.scroll.viewport())
                container = self.scroll.widget()
                if container:
                    container.setStyleSheet("background-color: transparent;")
                    self._make_widget_transparent(container)

        # 更新所有字段组件的样式
        for widget in self._field_widgets:
            try:
                self._apply_field_widget_style(widget)
            except RuntimeError:
                pass  # 组件已被删除

    def _apply_field_widget_style(self, widget):
        """应用字段组件的主题样式"""
        if self._transparency_enabled:
            bg_rgba = self._hex_to_rgba(theme_manager.BG_CARD, self._current_opacity)
            border_rgba = self._hex_to_rgba(theme_manager.BORDER_LIGHT, OpacityTokens.BORDER_DEFAULT)
            widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_rgba};
                    border: 1px solid {border_rgba};
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 16px;
                }}
            """)
            self._make_widget_transparent(widget)
        else:
            widget.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 16px;
                }}
            """)

    def createFieldWidget(self, label, value):
        """创建字段展示widget"""
        # 使用 theme_manager 的便捷方法
        ui_font = theme_manager.ui_font()
        serif_font = theme_manager.serif_font()

        widget = QFrame()

        # 应用样式（根据透明度状态）
        self._apply_field_widget_style(widget)

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

        # 保存引用
        self._field_widgets.append(widget)

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

        # 清空字段组件引用列表
        self._field_widgets.clear()

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
