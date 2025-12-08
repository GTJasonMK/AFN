#"空状态组件 - 禅意风格

#提供友好、有指引性的空状态显示
#符合2025年UX最佳实践

#特点：
#- 清晰的视觉层次
#- 明确的行动指引
#- 情感化设计（图标/插画）
#- 可自定义内容
#"

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal
from components.base.theme_aware_widget import ThemeAwareWidget
from themes.theme_manager import theme_manager


class EmptyState(ThemeAwareWidget):
    """空状态组件基类"""

    actionClicked = pyqtSignal()

    def __init__(
        self,
        icon='◐',
        title='暂无内容',
        description='',
        action_text='',
        parent=None
    ):
        self.icon = icon
        self.title = title
        self.description = description
        self.action_text = action_text
        self.icon_label = None
        self.title_label = None
        self.desc_label = None
        self.action_btn = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)

        # 图标
        self.icon_label = QLabel(self.icon)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 标题
        self.title_label = QLabel(self.title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 描述文字
        if self.description:
            self.desc_label = QLabel(self.description)
            self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.desc_label.setWordWrap(True)
            self.desc_label.setMaximumWidth(480)
            layout.addWidget(self.desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 行动按钮
        if self.action_text:
            self.action_btn = QPushButton(self.action_text)
            self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.action_btn.clicked.connect(self.actionClicked.emit)
            layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        if self.icon_label:
            self.icon_label.setStyleSheet(f"""
                font-size: 96px;
                color: {theme_manager.PRIMARY};
                background-color: transparent;
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_2XL};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
                letter-spacing: {theme_manager.LETTER_SPACING_TIGHT};
            """)

        if self.desc_label:
            self.desc_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.7;
            """)

        if self.action_btn:
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 14px 32px;
                    font-size: {theme_manager.FONT_SIZE_MD};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                    min-width: 160px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING};
                }}
                QPushButton:pressed {{
                    padding: 15px 32px 13px 32px;
                }}
            """)


class EmptyStateWithIllustration(ThemeAwareWidget):
    """带插画的空状态（高级版）"""

    actionClicked = pyqtSignal()

    def __init__(
        self,
        illustration_char='📖',
        title='',
        description='',
        action_text='',
        secondary_action_text='',
        parent=None
    ):
        # 先初始化成员变量，再调用父类构造函数
        self.illustration_char = illustration_char
        self.title = title
        self.description = description
        self.action_text = action_text
        self.secondary_action_text = secondary_action_text
        self.illustration_container = None
        self.title_label = None
        self.desc_label = None
        self.action_btn = None
        self.secondary_btn = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(32)
        layout.setContentsMargins(48, 48, 48, 48)

        # 插画容器（移除背景，保持简洁）
        self.illustration_container = QFrame()
        self.illustration_container.setFixedSize(200, 200)

        illustration_layout = QVBoxLayout(self.illustration_container)
        illustration_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        illustration = QLabel(self.illustration_char)
        illustration.setAlignment(Qt.AlignmentFlag.AlignCenter)
        illustration.setStyleSheet("""
            font-size: 96px;
            background-color: transparent;
        """)
        illustration_layout.addWidget(illustration)

        layout.addWidget(self.illustration_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # 标题
        if self.title:
            self.title_label = QLabel(self.title)
            self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 描述
        if self.description:
            self.desc_label = QLabel(self.description)
            self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.desc_label.setWordWrap(True)
            self.desc_label.setMaximumWidth(520)
            layout.addWidget(self.desc_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 按钮组
        if self.action_text or self.secondary_action_text:
            button_layout = QHBoxLayout()
            button_layout.setSpacing(12)

            if self.secondary_action_text:
                self.secondary_btn = QPushButton(self.secondary_action_text)
                self.secondary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                button_layout.addWidget(self.secondary_btn)

            if self.action_text:
                self.action_btn = QPushButton(self.action_text)
                self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.action_btn.clicked.connect(self.actionClicked.emit)
                button_layout.addWidget(self.action_btn)

            layout.addLayout(button_layout)

    def _apply_theme(self):
        """应用主题样式"""
        # 使用现代UI字体
        ui_font = theme_manager.ui_font()

        if self.illustration_container:
            self.illustration_container.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                    border: 2px dashed {theme_manager.BORDER_LIGHT};
                    border-radius: 100px;
                }}
            """)

        if self.title_label:
            self.title_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_3XL};
                font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                color: {theme_manager.TEXT_PRIMARY};
                letter-spacing: {theme_manager.LETTER_SPACING_TIGHT};
            """)

        if self.desc_label:
            self.desc_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {theme_manager.FONT_SIZE_MD};
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.8;
            """)

        if self.secondary_btn:
            self.secondary_btn.setStyleSheet(theme_manager.button_secondary())

        if self.action_btn:
            self.action_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {ui_font};
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: 14px 36px;
                    font-size: {theme_manager.FONT_SIZE_MD};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                    min-width: 160px;
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.WARNING};
                }}
            """)


class EmptyStatePresets:
    """空状态预设模板"""

    @staticmethod
    def no_projects(parent=None):
        """无项目"""
        return EmptyStateWithIllustration(
            illustration_char='*',
            title='还没有创作项目',
            description='开始你的第一个小说创作，\n让AI助手帮助你构建完整的故事世界。',
            action_text='创建新项目',
            secondary_action_text='查看示例',
            parent=parent
        )

    @staticmethod
    def no_chapters(parent=None):
        """无章节"""
        return EmptyState(
            icon='*',
            title='还未生成章节',
            description='点击下方按钮开始生成你的第一个章节',
            action_text='生成章节',
            parent=parent
        )

    @staticmethod
    def no_search_results(parent=None):
        """无搜索结果"""
        return EmptyState(
            icon='*',
            title='未找到匹配结果',
            description='请尝试使用其他关键词搜索',
            action_text='清除搜索',
            parent=parent
        )

    @staticmethod
    def no_data(parent=None):
        """无数据（通用）"""
        return EmptyState(
            icon='*',
            title='暂无数据',
            description='',
            action_text='',
            parent=parent
        )

    @staticmethod
    def error_state(parent=None):
        """错误状态"""
        return EmptyState(
            icon='!',
            title='加载失败',
            description='数据加载出现问题，请稍后重试',
            action_text='重新加载',
            parent=parent
        )

    @staticmethod
    def connection_error(parent=None):
        """连接错误"""
        return EmptyStateWithIllustration(
            illustration_char='x',
            title='无法连接服务器',
            description='请检查网络连接后重试',
            action_text='重新连接',
            parent=parent
        )

    @staticmethod
    def permission_denied(parent=None):
        """权限不足"""
        return EmptyState(
            icon='#',
            title='权限不足',
            description='你没有权限访问此内容',
            action_text='',
            parent=parent
        )

    @staticmethod
    def coming_soon(parent=None):
        """即将推出"""
        return EmptyStateWithIllustration(
            illustration_char='>',
            title='即将推出',
            description='这个功能正在开发中，敬请期待',
            action_text='',
            parent=parent
        )
