"""
首页 - VS风格欢迎页面
左侧：创建小说、打开项目入口
右侧：Tab切换（最近项目 / 全部项目）
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsOpacityEffect, QScrollArea, QFrame, QSizePolicy,
    QStackedWidget, QButtonGroup, QMenu
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPointF, pyqtProperty, QSequentialAnimationGroup, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QBrush, QTransform, QFont, QFontDatabase, QAction


# 创作箴言集 - 富有文学气息的启发性标语
# 格式：(中文主标语, 英文副标语/出处)
CREATIVE_QUOTES = [
    # ========== 原创箴言 ==========
    ("落笔成章，灵感无疆", "Let words flow, let imagination soar"),
    ("一念成世界，字里藏山河", "A thought becomes a world"),
    ("以墨为舟，载梦远航", "Sail your dreams with ink"),
    ("每个故事，都值得被讲述", "Every story deserves to be told"),
    ("笔墨之间，万千世界", "Infinite worlds between the lines"),
    ("让灵感落地，让想象生长", "Ground your inspiration, grow your vision"),
    ("文字有灵，故事不朽", "Words have soul, stories live forever"),

    # ========== 中国古典诗词 ==========
    ("文章千古事，得失寸心知", "— 杜甫《偶题》"),
    ("文章本天成，妙手偶得之", "— 陆游《文章》"),
    ("看似寻常最奇崛，成如容易却艰辛", "— 王安石"),
    ("我手写我口，古岂能拘牵", "— 黄遵宪《杂感》"),
    ("须教自我胸中出，切忌随人脚后行", "— 戴复古《论诗》"),
    ("天籁自鸣天趣足，好诗不过近人情", "— 张问陶"),
    ("山重水复疑无路，柳暗花明又一村", "— 陆游《游山西村》"),
    ("落红不是无情物，化作春泥更护花", "— 龚自珍《己亥杂诗》"),

    # ========== 中国现当代作家 ==========
    ("有一分热，发一分光", "— 鲁迅"),
    ("我之所以写作，不是我有才华，而是我有感情", "— 巴金"),
    ("世事犹如书籍，一页页被翻过去", "— 莫言"),
    ("文学最大的用处，也许就是它没有用处", "— 莫言"),

    # ========== 西方文学名言 ==========
    ("心中若有未讲的故事，便是最大的痛苦", "There is no greater agony than bearing an untold story — Maya Angelou"),
    ("想读却还未被写出的书，你必须亲自去写", "If there's a book you want to read but hasn't been written yet, write it — Toni Morrison"),
    ("初稿不过是你讲给自己听的故事", "The first draft is just you telling yourself the story — Terry Pratchett"),
    ("一个词接着一个词，便是力量", "A word after a word after a word is power — Margaret Atwood"),
    ("故事是我们除了食物与栖身之外最需要的东西", "After nourishment and shelter, stories are what we need most — Philip Pullman"),
    ("小说是一种谎言，却能道出真实", "Fiction is a lie that tells us true things — Neil Gaiman"),
    ("童话不只告诉我们恶龙存在，更告诉我们恶龙可以被打败", "Fairy tales tell us dragons can be beaten — Neil Gaiman"),
    ("故事不是被创造的，而是被发现的", "Stories are found things — Stephen King"),
    ("好作家与常人的区别：每天走过千种故事，作家能看见其中五六种", "Good writers see five or six story ideas where others see none — Orson Scott Card"),
    ("信任你的梦，信任你的心，信任你的故事", "Trust dreams. Trust your heart. Trust your story — Neil Gaiman"),

    # ========== 关于想象力与创造 ==========
    ("想象力比知识更重要", "Imagination is more important than knowledge — Einstein"),
    ("精神的浩瀚、想象的活跃、心灵的勤奋：这便是天才", "— 狄德罗"),
    ("世界对于有想象力的人来说，只是一块画布", "The world is but a canvas to imagination — Thoreau"),
    ("只要我们能梦想，我们就能实现", "If we can dream it, we can do it"),
]
from .base_page import BasePage
from components.base import ThemeAwareFrame, ThemeAwareButton
from themes.theme_manager import theme_manager
from api.manager import APIClientManager
from utils.dpi_utils import dp, sp
from utils.formatters import get_project_status_text, format_word_count
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)


def get_title_sort_key(title: str) -> str:
    """
    获取标题的排序键（用于首字母分组）

    规则：
    - 英文字母开头：返回大写字母（A-Z）
    - 数字开头：返回 "#"
    - 中文或其他字符：返回该字符本身
    """
    if not title:
        return "#"
    first_char = title[0].upper()
    if first_char.isascii() and first_char.isalpha():
        return first_char
    elif first_char.isdigit():
        return "#"
    else:
        # 中文或其他字符，返回字符本身作为分组键
        return first_char


class FloatingParticle:
    """浮动粒子类"""
    def __init__(self, x, y, vx, vy, size, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.opacity = random.uniform(0.3, 0.7)

    def update(self, width, height):
        """更新粒子位置"""
        self.x += self.vx
        self.y += self.vy
        if self.x <= 0 or self.x >= width:
            self.vx = -self.vx
        if self.y <= 0 or self.y >= height:
            self.vy = -self.vy


class ParticleBackground(QWidget):
    """浮动粒子背景

    特性：
    - 支持 pause/resume 控制动画生命周期
    - 安全的主题信号管理（不依赖 __del__）
    - 页面切换时自动暂停/恢复以节省资源
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self._theme_connected = False
        self._init_particles()

        # 动画定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_particles)

        # 连接主题信号
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        """连接主题信号（安全方式）"""
        if not self._theme_connected:
            theme_manager.theme_changed.connect(self._on_theme_changed)
            self._theme_connected = True

    def _disconnect_theme_signal(self):
        """断开主题信号"""
        if self._theme_connected:
            try:
                theme_manager.theme_changed.disconnect(self._on_theme_changed)
            except (TypeError, RuntimeError):
                pass  # 信号可能已断开
            self._theme_connected = False

    def _on_theme_changed(self, theme_mode):
        """主题改变时刷新粒子颜色"""
        self._refresh_particle_colors()

    def _refresh_particle_colors(self):
        """刷新粒子颜色"""
        is_dark = theme_manager.is_dark_mode()
        accent = theme_manager.book_accent_color()
        text_secondary = theme_manager.book_text_secondary()
        if is_dark:
            colors = [QColor(accent), QColor("#8B7E66"), QColor("#C4B093")]
        else:
            colors = [QColor(text_secondary), QColor(accent), QColor("#2C3E50")]
        for particle in self.particles:
            color = random.choice(colors)
            color.setAlpha(int(random.uniform(15, 50)))
            particle.color = color
        self.update()

    def _init_particles(self):
        """初始化粒子"""
        is_dark = theme_manager.is_dark_mode()
        accent = theme_manager.book_accent_color()
        text_secondary = theme_manager.book_text_secondary()
        if is_dark:
            colors = [QColor(accent), QColor("#8B7E66"), QColor("#C4B093")]
        else:
            colors = [QColor(text_secondary), QColor(accent), QColor("#2C3E50")]
        for _ in range(30):
            x = random.randint(0, 1000)
            y = random.randint(0, 800)
            vx = random.uniform(-0.2, 0.2)
            vy = random.uniform(-0.2, 0.2)
            size = random.randint(2, 5)
            color = random.choice(colors)
            color.setAlpha(int(random.uniform(15, 50)))
            self.particles.append(FloatingParticle(x, y, vx, vy, size, color))

    def _update_particles(self):
        """更新粒子位置"""
        for particle in self.particles:
            particle.update(self.width(), self.height())
        self.update()

    def paintEvent(self, event):
        """绘制粒子"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for particle in self.particles:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(particle.color))
            painter.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)

    def start(self):
        """启动粒子动画"""
        if not self.timer.isActive():
            self.timer.start(50)

    def stop(self):
        """停止粒子动画"""
        if self.timer.isActive():
            self.timer.stop()

    def is_running(self) -> bool:
        """检查动画是否正在运行"""
        return self.timer.isActive()

    def cleanup(self):
        """清理资源（显式调用）

        在父组件销毁前应调用此方法，确保：
        - 停止定时器
        - 断开主题信号
        """
        self.stop()
        self._disconnect_theme_signal()

    def deleteLater(self):
        """删除前清理"""
        self.cleanup()
        super().deleteLater()


class RecentProjectCard(ThemeAwareFrame):
    """最近项目卡片 - 继承主题感知基类，自动管理主题信号"""

    # 定义信号
    deleteRequested = pyqtSignal(str, str)  # project_id, title

    def __init__(self, project_data: dict, parent=None, show_delete: bool = False):
        self.project_data = project_data
        self.project_id = project_data.get('id')
        self._show_delete = show_delete  # 是否显示删除按钮
        # 预先声明UI组件
        self.title_label = None
        self.status_label = None
        self.time_label = None
        self.delete_btn = None
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(dp(80))
        self.setupUI()

    def _create_ui_structure(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(6))

        # 标题行（标题 + 删除按钮）
        title_row = QHBoxLayout()
        title_row.setSpacing(dp(8))

        self.title_label = QLabel(self.project_data.get('title', '未命名项目'))
        self.title_label.setWordWrap(True)
        title_row.addWidget(self.title_label, 1)

        # 删除按钮（仅在启用时创建，默认隐藏，hover时显示）
        if self._show_delete:
            self.delete_btn = QPushButton("删除")
            self.delete_btn.setFixedSize(dp(48), dp(24))
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.setVisible(False)
            self.delete_btn.clicked.connect(self._on_delete_clicked)
            title_row.addWidget(self.delete_btn)

        layout.addLayout(title_row)

        # 底部信息：状态 + 更新时间
        info_layout = QHBoxLayout()
        info_layout.setSpacing(dp(12))

        # 状态
        status = self.project_data.get('status', 'draft')
        status_text = get_project_status_text(status)
        self.status_label = QLabel(status_text)
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()

        # 更新时间
        updated_at = self.project_data.get('updated_at', '')
        time_text = self._format_time(updated_at)
        self.time_label = QLabel(time_text)
        info_layout.addWidget(self.time_label)

        layout.addLayout(info_layout)

    def _format_time(self, time_str: str) -> str:
        """格式化时间为友好显示"""
        if not time_str:
            return ""
        try:
            # 解析ISO格式时间
            if 'T' in time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')

            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = now - dt

            if diff.days == 0:
                if diff.seconds < 3600:
                    return f"{diff.seconds // 60}分钟前"
                else:
                    return f"{diff.seconds // 3600}小时前"
            elif diff.days == 1:
                return "昨天"
            elif diff.days < 7:
                return f"{diff.days}天前"
            else:
                return dt.strftime('%m-%d')
        except (ValueError, TypeError, AttributeError):
            # ValueError: 日期格式解析失败
            # TypeError: 类型不匹配
            # AttributeError: 属性访问失败
            return time_str[:10] if len(time_str) >= 10 else time_str

    def _apply_theme(self):
        bg_color = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        border_color = theme_manager.book_border_color()
        accent_color = theme_manager.book_accent_color()
        ui_font = theme_manager.ui_font()

        self.setStyleSheet(f"""
            RecentProjectCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
            }}
            RecentProjectCard:hover {{
                border-color: {accent_color};
                background-color: {theme_manager.book_bg_primary()};
            }}
        """)

        # 注意：这些属性在_create_ui_structure中创建，
        # setupUI保证_create_ui_structure在_apply_theme之前调用
        self.title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(15)}px;
                font-weight: 500;
                color: {text_primary};
                background: transparent;
            }}
        """)

        self.status_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(12)}px;
                color: {accent_color};
                background: transparent;
            }}
        """)

        self.time_label.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(12)}px;
                color: {text_secondary};
                background: transparent;
            }}
        """)

        # 删除按钮样式
        if self.delete_btn:
            self.delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(4)}px;
                    font-family: {ui_font};
                    font-size: {dp(11)}px;
                }}
                QPushButton:hover {{
                    background-color: #e74c3c;
                    color: white;
                    border-color: #e74c3c;
                }}
            """)

    def enterEvent(self, event):
        """鼠标进入时显示删除按钮"""
        if self.delete_btn:
            self.delete_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开时隐藏删除按钮"""
        if self.delete_btn:
            self.delete_btn.setVisible(False)
        super().leaveEvent(event)

    def _on_delete_clicked(self):
        """删除按钮点击处理"""
        title = self.project_data.get('title', '未命名项目')
        self.deleteRequested.emit(self.project_id, title)

    def mousePressEvent(self, event):
        """点击卡片时通知父组件（排除删除按钮区域）"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查点击位置是否在删除按钮上
            if self.delete_btn and self.delete_btn.isVisible():
                btn_rect = self.delete_btn.geometry()
                if btn_rect.contains(event.pos()):
                    return  # 让删除按钮处理点击
            # 查找HomePage父组件
            parent = self.parent()
            while parent and not isinstance(parent, HomePage):
                parent = parent.parent()
            if parent and hasattr(parent, '_on_project_clicked'):
                parent._on_project_clicked(self.project_data)


class TabButton(ThemeAwareButton):
    """Tab切换按钮 - 继承主题感知基类，自动管理主题信号"""

    def __init__(self, text: str, parent=None):
        self._is_active = False
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setCheckable(True)
        self.setupUI()

    def setActive(self, active: bool):
        """设置激活状态"""
        self._is_active = active
        self.setChecked(active)
        self._apply_theme()

    def _apply_theme(self):
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        bg_secondary = theme_manager.book_bg_secondary()
        ui_font = theme_manager.ui_font()

        if self._is_active:
            # 激活状态
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {accent_color};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(20)}px;
                    font-family: {ui_font};
                    font-size: {dp(14)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {text_primary};
                }}
            """)
        else:
            # 非激活状态
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border_color};
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(20)}px;
                    font-family: {ui_font};
                    font-size: {dp(14)}px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    color: {accent_color};
                    border-color: {accent_color};
                }}
            """)


class TabBar(ThemeAwareFrame):
    """Tab栏组件 - 继承主题感知基类，自动管理主题信号"""

    def __init__(self, parent=None):
        self.buttons = []
        self.recent_btn = None
        self.all_btn = None
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, dp(12))
        layout.setSpacing(dp(12))

        # 最近项目Tab
        self.recent_btn = TabButton("最近项目")
        self.recent_btn.setActive(True)
        layout.addWidget(self.recent_btn)

        # 全部项目Tab
        self.all_btn = TabButton("全部项目")
        layout.addWidget(self.all_btn)

        layout.addStretch()

        self.buttons = [self.recent_btn, self.all_btn]

    def setCurrentIndex(self, index: int):
        """设置当前激活的Tab"""
        for i, btn in enumerate(self.buttons):
            btn.setActive(i == index)

    def _apply_theme(self):
        self.setStyleSheet("background: transparent;")


class HomePage(BasePage):
    """首页 - VS风格欢迎页面"""

    def __init__(self, parent=None):
        self.api_client = APIClientManager.get_client()
        self.recent_projects = []  # 最近项目（按时间排序，最多10个）
        self.all_projects = []  # 全部项目（按首字母排序）
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()
        QTimer.singleShot(100, self._animate_entrance)

    def _create_ui_structure(self):
        # 主布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 添加浮动粒子背景
        self.particle_bg = ParticleBackground(self)
        self.particle_bg.lower()
        self.particle_bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # ========== 左侧区域 ==========
        left_widget = QWidget()
        left_widget.setMinimumWidth(dp(400))
        left_widget.setMaximumWidth(dp(500))
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(dp(60), dp(60), dp(40), dp(60))
        left_layout.setSpacing(dp(20))

        # 右上角设置按钮
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        self.settings_btn = QPushButton("设置")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedSize(dp(60), dp(32))
        self.settings_btn.clicked.connect(lambda: self.navigateTo('SETTINGS'))
        header_layout.addWidget(self.settings_btn)
        left_layout.addLayout(header_layout)

        left_layout.addSpacing(dp(40))

        # 主标题
        self.title = QLabel("AFN")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        left_layout.addWidget(self.title)

        # 副标题
        self.subtitle = QLabel("AI 驱动的长篇小说创作助手")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft)
        left_layout.addWidget(self.subtitle)

        # 创作箴言 - 艺术气息的启发性标语
        self.quote_container = QWidget()
        quote_layout = QVBoxLayout(self.quote_container)
        quote_layout.setContentsMargins(0, dp(16), 0, 0)
        quote_layout.setSpacing(dp(4))

        # 随机选择一句箴言
        self._current_quote = random.choice(CREATIVE_QUOTES)

        # 中文主标语
        self.quote_label = QLabel(self._current_quote[0])
        self.quote_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.quote_label.setWordWrap(True)  # 允许自动换行
        quote_layout.addWidget(self.quote_label)

        # 英文副标语（更小、更淡）
        self.quote_sub_label = QLabel(self._current_quote[1])
        self.quote_sub_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.quote_sub_label.setWordWrap(True)  # 允许自动换行，防止长英文被截断
        quote_layout.addWidget(self.quote_sub_label)

        left_layout.addWidget(self.quote_container)

        # 为引言添加透明度效果
        self.quote_opacity = QGraphicsOpacityEffect()
        self.quote_container.setGraphicsEffect(self.quote_opacity)

        left_layout.addSpacing(dp(50))

        # 操作按钮区域
        buttons_widget = QWidget()
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(dp(16))

        # 创建小说按钮（主要）
        self.create_btn = QPushButton("创建小说")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.setMinimumHeight(dp(48))
        self.create_btn.clicked.connect(self._on_create_novel)
        buttons_layout.addWidget(self.create_btn)

        # 打开现有项目按钮（次要）- 切换到全部项目Tab
        self.open_btn = QPushButton("查看全部项目")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.setMinimumHeight(dp(48))
        self.open_btn.clicked.connect(lambda: self._switch_tab(1))
        buttons_layout.addWidget(self.open_btn)

        left_layout.addWidget(buttons_widget)
        left_layout.addStretch()

        main_layout.addWidget(left_widget)

        # ========== 右侧区域（Tab切换：最近项目 / 全部项目） ==========
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(dp(40), dp(60), dp(60), dp(60))
        right_layout.setSpacing(0)

        # Tab栏
        self.tab_bar = TabBar()
        self.tab_bar.recent_btn.clicked.connect(lambda: self._switch_tab(0))
        self.tab_bar.all_btn.clicked.connect(lambda: self._switch_tab(1))
        right_layout.addWidget(self.tab_bar)

        # 堆叠页面（用于Tab切换）
        self.projects_stack = QStackedWidget()

        # ===== Tab 0: 最近项目页面 =====
        self.recent_page = QWidget()
        recent_page_layout = QVBoxLayout(self.recent_page)
        recent_page_layout.setContentsMargins(0, 0, 0, 0)
        recent_page_layout.setSpacing(0)

        self.recent_scroll = QScrollArea()
        self.recent_scroll.setWidgetResizable(True)
        self.recent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.recent_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.recent_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.recent_container = QWidget()
        self.recent_layout = QVBoxLayout(self.recent_container)
        self.recent_layout.setContentsMargins(0, 0, dp(8), 0)
        self.recent_layout.setSpacing(dp(8))
        self.recent_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 最近项目空状态提示
        self.recent_empty_label = QLabel("暂无最近项目\n点击\"创建小说\"开始您的创作之旅")
        self.recent_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_empty_label.setWordWrap(True)
        self.recent_layout.addWidget(self.recent_empty_label)
        self.recent_layout.addStretch()

        self.recent_scroll.setWidget(self.recent_container)
        recent_page_layout.addWidget(self.recent_scroll)
        self.projects_stack.addWidget(self.recent_page)

        # ===== Tab 1: 全部项目页面 =====
        self.all_page = QWidget()
        all_page_layout = QVBoxLayout(self.all_page)
        all_page_layout.setContentsMargins(0, 0, 0, 0)
        all_page_layout.setSpacing(0)

        self.all_scroll = QScrollArea()
        self.all_scroll.setWidgetResizable(True)
        self.all_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.all_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.all_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.all_container = QWidget()
        self.all_layout = QVBoxLayout(self.all_container)
        self.all_layout.setContentsMargins(0, 0, dp(8), 0)
        self.all_layout.setSpacing(dp(8))
        self.all_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 全部项目空状态提示
        self.all_empty_label = QLabel("暂无项目\n点击\"创建小说\"开始您的创作之旅")
        self.all_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_empty_label.setWordWrap(True)
        self.all_layout.addWidget(self.all_empty_label)
        self.all_layout.addStretch()

        self.all_scroll.setWidget(self.all_container)
        all_page_layout.addWidget(self.all_scroll)
        self.projects_stack.addWidget(self.all_page)

        right_layout.addWidget(self.projects_stack, 1)

        main_layout.addWidget(right_widget, 1)  # 右侧占据剩余空间

        # 为动画准备透明度效果
        self.title_opacity = QGraphicsOpacityEffect()
        self.title.setGraphicsEffect(self.title_opacity)
        self.subtitle_opacity = QGraphicsOpacityEffect()
        self.subtitle.setGraphicsEffect(self.subtitle_opacity)

    def _apply_theme(self):
        bg_color = theme_manager.book_bg_primary()
        bg_secondary = theme_manager.book_bg_secondary()
        text_primary = theme_manager.book_text_primary()
        text_secondary = theme_manager.book_text_secondary()
        accent_color = theme_manager.book_accent_color()
        border_color = theme_manager.book_border_color()
        serif_font = theme_manager.serif_font()
        ui_font = theme_manager.ui_font()

        self.setStyleSheet(f"""
            HomePage {{
                background-color: {bg_color};
            }}
        """)

        # 注意：以下属性都在_create_ui_structure中创建，
        # setupUI保证_create_ui_structure在_apply_theme之前调用

        self.title.setStyleSheet(f"""
            QLabel {{
                font-family: {serif_font};
                font-size: {dp(56)}px;
                font-weight: bold;
                color: {text_primary};
                letter-spacing: {dp(2)}px;
            }}
        """)

        self.subtitle.setStyleSheet(f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(16)}px;
                color: {text_secondary};
                letter-spacing: {dp(1)}px;
            }}
        """)

        # 创作箴言样式 - 艺术字体，斜体，淡雅
        # 计算一个介于 text_secondary 和 accent_color 之间的淡雅颜色
        quote_color = text_secondary  # 使用次要文字颜色
        quote_accent = accent_color  # 用于英文

        self.quote_container.setStyleSheet("background: transparent;")

        # 中文箴言 - 使用衬线字体，营造文学气息
        self.quote_label.setStyleSheet(f"""
            QLabel {{
                font-family: {serif_font};
                font-size: {dp(15)}px;
                font-style: italic;
                color: {quote_color};
                letter-spacing: {dp(3)}px;
                line-height: 1.5;
                background: transparent;
            }}
        """)

        # 英文副标语 - 更小、更淡，作为点缀
        self.quote_sub_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Georgia", "Times New Roman", {serif_font};
                font-size: {dp(11)}px;
                font-style: italic;
                color: {border_color};
                letter-spacing: {dp(1)}px;
                line-height: 1.4;
                background: transparent;
            }}
        """)

        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid transparent;
                border-radius: {dp(4)}px;
                font-family: {ui_font};
                font-size: {dp(13)}px;
            }}
            QPushButton:hover {{
                color: {accent_color};
                border-color: {border_color};
            }}
        """)

        # 创建按钮样式（主要按钮）
        self.create_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color};
                color: {bg_color};
                border: none;
                border-radius: {dp(8)}px;
                padding: {dp(12)}px {dp(24)}px;
                font-family: {ui_font};
                font-size: {dp(16)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {text_primary};
            }}
            QPushButton:pressed {{
                background-color: {text_secondary};
            }}
        """)

        # 打开按钮样式（次要按钮）
        self.open_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: {dp(8)}px;
                padding: {dp(12)}px {dp(24)}px;
                font-family: {ui_font};
                font-size: {dp(16)}px;
            }}
            QPushButton:hover {{
                border-color: {accent_color};
                color: {accent_color};
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
        """)

        # 滚动区域样式
        scroll_style = f"""
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: {dp(6)}px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {border_color};
                border-radius: {dp(3)}px;
                min-height: {dp(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {text_secondary};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """

        self.recent_scroll.setStyleSheet(scroll_style)
        self.all_scroll.setStyleSheet(scroll_style)

        # 容器透明背景
        for container_name in ['recent_container', 'all_container', 'recent_page', 'all_page']:
            container = getattr(self, container_name, None)
            if container:
                container.setStyleSheet("background-color: transparent;")

        # 堆叠页面透明背景
        self.projects_stack.setStyleSheet("background-color: transparent;")

        # 空状态标签样式
        empty_label_style = f"""
            QLabel {{
                font-family: {ui_font};
                font-size: {dp(14)}px;
                color: {text_secondary};
                padding: {dp(40)}px;
            }}
        """

        self.recent_empty_label.setStyleSheet(empty_label_style)
        self.all_empty_label.setStyleSheet(empty_label_style)

    def _animate_entrance(self):
        """入场动画"""
        title_anim = QPropertyAnimation(self.title_opacity, b"opacity")
        title_anim.setDuration(600)
        title_anim.setStartValue(0.0)
        title_anim.setEndValue(1.0)
        title_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        title_anim.start()
        self.title_animation = title_anim

        subtitle_anim = QPropertyAnimation(self.subtitle_opacity, b"opacity")
        subtitle_anim.setDuration(600)
        subtitle_anim.setStartValue(0.0)
        subtitle_anim.setEndValue(1.0)
        subtitle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(150, subtitle_anim.start)
        self.subtitle_animation = subtitle_anim

        # 引言淡入动画 - 延迟更久，更缓慢地出现，增加诗意感
        quote_anim = QPropertyAnimation(self.quote_opacity, b"opacity")
        quote_anim.setDuration(800)
        quote_anim.setStartValue(0.0)
        quote_anim.setEndValue(0.85)  # 不完全不透明，保持淡雅
        quote_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(400, quote_anim.start)
        self.quote_animation = quote_anim

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'particle_bg'):
            self.particle_bg.setGeometry(self.rect())

    def _on_create_novel(self):
        """创建小说 - 直接进入灵感对话模式"""
        self.navigateTo('INSPIRATION')

    def _on_project_clicked(self, project_data: dict):
        """点击项目卡片"""
        project_id = project_data.get('id')
        status = project_data.get('status', 'draft')

        # 根据状态决定导航目标
        if status in ['blueprint_ready', 'part_outlines_ready', 'chapter_outlines_ready', 'writing', 'completed']:
            # 已有蓝图，导航到详情页
            self.navigateTo('DETAIL', project_id=project_id)
        else:
            # 未完成蓝图（draft状态），导航回灵感对话继续
            self.navigateTo('INSPIRATION', project_id=project_id)

    def _switch_tab(self, index: int):
        """切换Tab页面"""
        self.tab_bar.setCurrentIndex(index)
        self.projects_stack.setCurrentIndex(index)

    def _load_recent_projects(self):
        """加载项目数据（最近项目 + 全部项目）

        使用AsyncWorker在后台线程执行API调用，避免UI线程阻塞。
        """
        from utils.async_worker import AsyncWorker

        def fetch_projects():
            """后台线程执行的API调用"""
            return self.api_client.get_novels()

        def on_success(projects):
            """API调用成功回调（在主线程执行）"""
            if projects:
                # 最近项目：按更新时间排序，取前10个
                sorted_by_time = sorted(
                    projects,
                    key=lambda x: x.get('updated_at', ''),
                    reverse=True
                )
                self.recent_projects = sorted_by_time[:10]

                # 全部项目：按首字母排序
                self.all_projects = sorted(
                    projects,
                    key=lambda x: (get_title_sort_key(x.get('title', '')), x.get('title', '').lower())
                )
            else:
                self.recent_projects = []
                self.all_projects = []

            self._update_projects_ui()

        def on_error(error):
            """API调用失败回调（在主线程执行）"""
            logger.error("加载项目失败: %s", error, exc_info=True)
            self.recent_projects = []
            self.all_projects = []
            self._update_projects_ui()

        # 创建并启动异步工作线程
        worker = AsyncWorker(fetch_projects)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        # 保持worker引用，防止被垃圾回收
        if not hasattr(self, '_workers'):
            self._workers = []
        # 清理已完成的worker（安全检查，避免访问已删除的C++对象）
        valid_workers = []
        for w in self._workers:
            try:
                if w.isRunning():
                    valid_workers.append(w)
            except RuntimeError:
                # C++ 对象已被删除，跳过
                pass
        self._workers = valid_workers
        self._workers.append(worker)

        worker.start()

    def _clear_layout(self, layout, preserve_widgets=None):
        """清空布局中的所有组件（可选保留指定widget）

        Args:
            layout: 要清空的布局
            preserve_widgets: 要保留的widget列表（不删除，只从布局中移除）
        """
        if preserve_widgets is None:
            preserve_widgets = []

        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                # 如果是要保留的widget，只从布局中移除，不删除
                if widget in preserve_widgets:
                    continue
                # 使用 deleteLater() 删除，ThemeAware 基类会自动断开信号
                widget.deleteLater()

    def _update_projects_ui(self):
        """更新项目列表UI（最近项目Tab + 全部项目Tab）"""
        # 清空现有内容（保留empty_label不被删除）
        self._clear_layout(self.recent_layout, preserve_widgets=[self.recent_empty_label])
        self._clear_layout(self.all_layout, preserve_widgets=[self.all_empty_label])

        # ===== 更新最近项目Tab（不显示删除按钮） =====
        if self.recent_projects:
            self.recent_empty_label.hide()
            for project in self.recent_projects:
                card = RecentProjectCard(project, self.recent_container, show_delete=False)
                self.recent_layout.addWidget(card)
            self.recent_layout.addStretch()
        else:
            self.recent_layout.addWidget(self.recent_empty_label)
            self.recent_empty_label.show()
            self.recent_layout.addStretch()

        # ===== 更新全部项目Tab（显示删除按钮） =====
        if self.all_projects:
            self.all_empty_label.hide()
            for project in self.all_projects:
                card = RecentProjectCard(project, self.all_container, show_delete=True)
                card.deleteRequested.connect(self._on_delete_project)
                self.all_layout.addWidget(card)
            self.all_layout.addStretch()
        else:
            self.all_layout.addWidget(self.all_empty_label)
            self.all_empty_label.show()
            self.all_layout.addStretch()

    def refresh(self, **params):
        """刷新页面"""
        self._load_recent_projects()

    def onShow(self):
        """页面显示时"""
        # 随机更换箴言，每次返回首页时显示不同的启发性标语
        if hasattr(self, 'quote_label') and hasattr(self, 'quote_sub_label'):
            self._current_quote = random.choice(CREATIVE_QUOTES)
            self.quote_label.setText(self._current_quote[0])
            self.quote_sub_label.setText(self._current_quote[1])

        # 加载最近项目
        self._load_recent_projects()

        # 启动粒子动画
        if hasattr(self, 'particle_bg'):
            self.particle_bg.start()

    def onHide(self):
        """页面隐藏时停止动画"""
        if hasattr(self, 'particle_bg'):
            self.particle_bg.stop()

    def _on_delete_project(self, project_id: str, title: str):
        """删除项目处理"""
        from utils.message_service import confirm, MessageService
        from utils.async_worker import AsyncWorker

        # 确认删除
        if not confirm(
            self,
            f"确定要删除项目「{title}」吗？\n\n此操作不可恢复，所有章节内容将被永久删除。",
            "确认删除"
        ):
            return

        def do_delete():
            return self.api_client.delete_novels([project_id])

        def on_success(result):
            MessageService.show_success(self, f"项目「{title}」已删除")
            # 刷新项目列表
            self._load_recent_projects()

        def on_error(error_msg):
            MessageService.show_error(self, f"删除失败：{error_msg}", "错误")

        # 异步执行删除
        worker = AsyncWorker(do_delete)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        # 保持worker引用
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        # 清理粒子背景资源
        if hasattr(self, 'particle_bg'):
            self.particle_bg.cleanup()
        super().closeEvent(event)
