"""
骨架屏加载组件 - 禅意风格

提供更优雅的加载状态显示，替代简单的Loading文字
符合2025年UI设计趋势

特点：
- 模拟真实内容结构
- 平滑的闪烁动画
- 可自定义形状和大小
- 非阻塞式加载提示
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from components.base.theme_aware_widget import ThemeAwareFrame
from themes.theme_manager import theme_manager


class SkeletonLine(ThemeAwareFrame):
    """骨架屏单行元素"""

    def __init__(self, width='100%', height=16, radius=8, parent=None):
        self.height = height
        self.radius = radius
        self.width_param = width
        self.width_percentage = None
        self.opacity_effect = None
        self.animation = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setFixedHeight(self.height)

        if isinstance(self.width_param, str) and self.width_param.endswith('%'):
            # 百分比宽度（相对于父容器）
            self.width_percentage = int(self.width_param.rstrip('%'))
        else:
            # 固定宽度
            self.setFixedWidth(self.width_param)
            self.width_percentage = None

        # 闪烁动画
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.startAnimation()

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {self.radius}px;
            }}
        """)

    def startAnimation(self):
        """启动闪烁动画"""
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(1500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.3)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setLoopCount(-1)  # 无限循环
        self.animation.start()


class SkeletonCircle(ThemeAwareFrame):
    """骨架屏圆形元素（用于头像等）"""

    def __init__(self, size=64, parent=None):
        self.size = size
        self.opacity_effect = None
        self.animation = None

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        self.setFixedSize(self.size, self.size)

        # 闪烁动画
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(1500)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.3)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.animation.setLoopCount(-1)
        self.animation.start()

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {self.size // 2}px;
            }}
        """)


class SkeletonCard(ThemeAwareFrame):
    """骨架屏卡片 - 模拟卡片内容结构"""

    def __init__(self, has_avatar=False, lines=3, parent=None):
        self.has_avatar = has_avatar
        self.lines = lines

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        if self.has_avatar:
            # 头部（头像 + 标题）
            header_layout = QHBoxLayout()
            header_layout.setSpacing(12)

            # 头像
            avatar = SkeletonCircle(48)
            header_layout.addWidget(avatar)

            # 标题和副标题
            title_container = QVBoxLayout()
            title_container.setSpacing(8)

            title = SkeletonLine(width='60%', height=20, radius=10)
            title_container.addWidget(title)

            subtitle = SkeletonLine(width='40%', height=14, radius=7)
            title_container.addWidget(subtitle)

            header_layout.addLayout(title_container)
            header_layout.addStretch()

            layout.addLayout(header_layout)

        # 内容行
        for i in range(self.lines):
            # 最后一行通常较短
            width = '70%' if i == self.lines - 1 else '100%'
            line = SkeletonLine(width=width, height=14, radius=7)
            layout.addWidget(line)

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            SkeletonCard {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_LG};
                padding: 20px;
            }}
        """)


class SkeletonList(QWidget):
    """骨架屏列表 - 多个卡片堆叠"""

    def __init__(self, card_count=3, has_avatar=True, lines=3, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        for _ in range(card_count):
            card = SkeletonCard(has_avatar=has_avatar, lines=lines)
            layout.addWidget(card)

        layout.addStretch()


class SkeletonTable(QWidget):
    """骨架屏表格 - 模拟表格结构"""

    def __init__(self, rows=5, columns=4, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # 表头
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        for _ in range(columns):
            header_cell = SkeletonLine(height=20, radius=10)
            header_layout.addWidget(header_cell)
        layout.addLayout(header_layout)

        # 表格行
        for _ in range(rows):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(12)
            for _ in range(columns):
                cell = SkeletonLine(height=16, radius=8)
                row_layout.addWidget(cell)
            layout.addLayout(row_layout)

        layout.addStretch()


class SkeletonDetailPage(QWidget):
    """骨架屏详情页 - 模拟详情页结构"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.content_card = None
        self.setupUI()
        # 连接主题变化信号
        theme_manager.theme_changed.connect(self._apply_theme)

    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题区域
        title_layout = QHBoxLayout()
        title = SkeletonLine(width=300, height=32, radius=16)
        title_layout.addWidget(title)
        title_layout.addStretch()

        action_btn1 = SkeletonLine(width=100, height=36, radius=18)
        title_layout.addWidget(action_btn1)

        action_btn2 = SkeletonLine(width=100, height=36, radius=18)
        title_layout.addWidget(action_btn2)

        layout.addLayout(title_layout)

        # 元信息
        meta_layout = QHBoxLayout()
        for width in [80, 100, 120]:
            meta = SkeletonLine(width=width, height=14, radius=7)
            meta_layout.addWidget(meta)
        meta_layout.addStretch()
        layout.addLayout(meta_layout)

        # 主要内容区域
        self.content_card = QFrame()
        content_layout = QVBoxLayout(self.content_card)
        content_layout.setSpacing(16)

        # 段落
        for i in range(5):
            width = '85%' if i == 4 else '100%'
            line = SkeletonLine(width=width, height=16, radius=8)
            content_layout.addWidget(line)

        layout.addWidget(self.content_card)

        # 底部卡片
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        for _ in range(2):
            card = SkeletonCard(has_avatar=False, lines=2)
            bottom_row.addWidget(card)

        layout.addLayout(bottom_row)
        layout.addStretch()

        # 应用主题
        self._apply_theme()

    def _apply_theme(self):
        """应用主题样式"""
        if self.content_card:
            self.content_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {theme_manager.BG_CARD};
                    border: 1px solid {theme_manager.BORDER_LIGHT};
                    border-radius: {theme_manager.RADIUS_LG};
                    padding: 24px;
                }}
            """)


# 预定义的骨架屏模板
class SkeletonPresets:
    """骨架屏预设模板"""

    @staticmethod
    def novel_list(parent=None):
        """小说列表骨架屏"""
        return SkeletonList(card_count=4, has_avatar=True, lines=2, parent=parent)

    @staticmethod
    def chapter_list(parent=None):
        """章节列表骨架屏"""
        return SkeletonList(card_count=6, has_avatar=False, lines=2, parent=parent)

    @staticmethod
    def novel_detail(parent=None):
        """小说详情骨架屏"""
        return SkeletonDetailPage(parent=parent)

    @staticmethod
    def data_table(parent=None):
        """数据表格骨架屏"""
        return SkeletonTable(rows=8, columns=5, parent=parent)

    @staticmethod
    def simple_card(parent=None):
        """简单卡片骨架屏"""
        return SkeletonCard(has_avatar=False, lines=3, parent=parent)
