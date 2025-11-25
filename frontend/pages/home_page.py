"""
首页 - 现代化设计 (2025)
添加渐变背景、玻璃态卡片、动画效果、浮动粒子
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QRectF, QPointF, pyqtProperty, QSequentialAnimationGroup
from PyQt6.QtGui import QLinearGradient, QGradient, QColor, QPalette, QPainter, QPen, QBrush, QTransform
from .base_page import BasePage
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from utils.dpi_utils import dp, sp
import random
import math


class BreathingLabel(QLabel):
    """支持缩放动画的Label"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._scale = 1.0

    @pyqtProperty(float)
    def scale(self):
        """获取缩放值"""
        return self._scale

    @scale.setter
    def scale(self, value):
        """设置缩放值并更新显示"""
        self._scale = value
        # 使用QTransform实现缩放（硬件加速，性能最优）
        transform = QTransform()
        transform.scale(value, value)
        self.setTransform(transform)

    def setTransform(self, transform):
        """应用变换矩阵"""
        # 保存原始尺寸提示
        hint = self.sizeHint()
        # 清除之前的变换
        self.setStyleSheet(self.styleSheet())
        # 应用新的变换（通过调整字体大小模拟）
        # 由于QLabel不直接支持transform，我们通过动态调整字体大小实现
        font = self.font()
        base_size = int(theme_manager.FONT_SIZE_3XL.replace('px', ''))
        font.setPointSize(int(base_size * self._scale * 0.75))  # 0.75是px到pt的转换系数
        self.setFont(font)


class FloatingParticle:
    """浮动粒子类"""
    def __init__(self, x, y, vx, vy, size, color):
        self.x = x
        self.y = y
        self.vx = vx  # x方向速度
        self.vy = vy  # y方向速度
        self.size = size
        self.color = color
        self.opacity = random.uniform(0.3, 0.7)

    def update(self, width, height):
        """更新粒子位置"""
        self.x += self.vx
        self.y += self.vy

        # 边界检测和反弹
        if self.x <= 0 or self.x >= width:
            self.vx = -self.vx
        if self.y <= 0 or self.y >= height:
            self.vy = -self.vy


class ParticleBackground(QWidget):
    """浮动粒子背景"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.init_particles()

        # 启动更新定时器
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_particles)
        self.timer.start(50)  # 50ms更新一次

    def init_particles(self):
        """初始化粒子"""
        # 创建30个粒子
        for _ in range(30):
            x = random.randint(0, 1000)
            y = random.randint(0, 800)
            vx = random.uniform(-0.5, 0.5)
            vy = random.uniform(-0.5, 0.5)
            size = random.randint(3, 8)
            # 使用主题色系的颜色
            colors = [
                QColor(theme_manager.PRIMARY),
                QColor(theme_manager.ACCENT),
                QColor(theme_manager.SUCCESS),
            ]
            color = random.choice(colors)
            color.setAlpha(int(random.uniform(30, 80)))

            self.particles.append(FloatingParticle(x, y, vx, vy, size, color))

    def update_particles(self):
        """更新粒子位置"""
        for particle in self.particles:
            particle.update(self.width(), self.height())
        self.update()  # 触发重绘

    def paintEvent(self, event):
        """绘制粒子"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for particle in self.particles:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(particle.color))
            painter.drawEllipse(
                QPointF(particle.x, particle.y),
                particle.size,
                particle.size
            )


class HomePage(BasePage):
    """首页 - 现代化设计，渐变背景，动画效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()

    def setupUI(self):
        """初始化现代化UI"""
        # 检查是否已有布局
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()
        # 启动入场动画
        QTimer.singleShot(100, self._animate_entrance)

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(40), dp(40), dp(40), dp(40))
        layout.setSpacing(dp(30))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # 添加浮动粒子背景
        self.particle_bg = ParticleBackground(self)
        self.particle_bg.lower()  # 放到最底层
        self.particle_bg.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # 右上角设置按钮
        header_layout = QHBoxLayout()
        header_layout.addStretch()

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setFixedSize(dp(80), dp(36))
        self.settings_btn.clicked.connect(lambda: self.navigateTo('SETTINGS'))
        header_layout.addWidget(self.settings_btn)

        layout.addLayout(header_layout)

        # 添加垂直间距
        layout.addSpacing(dp(40))

        # 主标题 - 使用BreathingLabel支持动画
        self.title = BreathingLabel("拯救小说家")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)

        # 副标题
        self.subtitle = QLabel("AI 驱动的长篇小说创作助手")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle)

        # 添加间距
        layout.addSpacing(dp(40))

        # 主要功能按钮容器
        buttons_widget = QWidget()
        buttons_widget.setMaximumWidth(dp(460))
        buttons_layout = QVBoxLayout(buttons_widget)
        buttons_layout.setSpacing(dp(16))

        # 灵感涌现按钮（主要按钮 - 渐变）
        self.inspiration_btn = QPushButton("✨ 灵感涌现")
        self.inspiration_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.inspiration_btn.setMinimumHeight(dp(56))
        self.inspiration_btn.clicked.connect(lambda: self.navigateTo('INSPIRATION'))
        buttons_layout.addWidget(self.inspiration_btn)

        # 创作工作台按钮（次要按钮）
        self.workspace_btn = QPushButton("📚 创作工作台")
        self.workspace_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.workspace_btn.setMinimumHeight(dp(56))
        self.workspace_btn.clicked.connect(lambda: self.navigateTo('WORKSPACE'))
        buttons_layout.addWidget(self.workspace_btn)

        layout.addWidget(buttons_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # 添加弹性空间
        layout.addStretch()

        # 为动画准备透明度效果
        self.title_opacity = QGraphicsOpacityEffect()
        self.title.setGraphicsEffect(self.title_opacity)
        self.subtitle_opacity = QGraphicsOpacityEffect()
        self.subtitle.setGraphicsEffect(self.subtitle_opacity)

    def resizeEvent(self, event):
        """窗口大小改变时，调整粒子背景大小"""
        super().resizeEvent(event)
        if hasattr(self, 'particle_bg'):
            self.particle_bg.setGeometry(self.rect())

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 获取渐变背景颜色
        gradient_colors = theme_manager.current_theme.BG_GRADIENT

        # 设置渐变背景
        self.setStyleSheet(f"""
            HomePage {{
                background: {ModernEffects.linear_gradient(gradient_colors, 180)};
            }}
        """)

        # 主标题样式 - 使用渐变文字效果（通过颜色模拟）
        if hasattr(self, 'title'):
            self.title.setStyleSheet(f"""
                QLabel {{
                    font-size: {theme_manager.FONT_SIZE_3XL};
                    font-weight: {theme_manager.FONT_WEIGHT_BOLD};
                    color: {theme_manager.TEXT_PRIMARY};
                    letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
                    margin: 0;
                    padding: 0;
                }}
            """)

        # 副标题样式
        if hasattr(self, 'subtitle'):
            self.subtitle.setStyleSheet(f"""
                QLabel {{
                    font-size: {theme_manager.FONT_SIZE_MD};
                    font-weight: {theme_manager.FONT_WEIGHT_NORMAL};
                    color: {theme_manager.TEXT_SECONDARY};
                    letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
                    margin: 0;
                    padding: 0;
                }}
            """)

        # 设置按钮 - 玻璃态效果
        if hasattr(self, 'settings_btn'):
            self.settings_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.current_theme.GLASS_BG};
                    color: {theme_manager.TEXT_PRIMARY};
                    border: 1px solid {theme_manager.BORDER_DEFAULT};
                    border-radius: {theme_manager.RADIUS_SM};
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {theme_manager.FONT_SIZE_SM};
                    font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY_PALE};
                    border-color: {theme_manager.PRIMARY};
                    color: {theme_manager.PRIMARY};
                }}
                QPushButton:pressed {{
                    background-color: {theme_manager.BG_SECONDARY};
                }}
            """)

        # 灵感涌现按钮 - 增强悬停效果
        if hasattr(self, 'inspiration_btn'):
            self.inspiration_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.PRIMARY};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: {dp(16)}px {dp(32)}px;
                    font-size: {theme_manager.FONT_SIZE_LG};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                    letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.PRIMARY_LIGHT};
                    padding: {dp(18)}px {dp(34)}px;
                }}
                QPushButton:pressed {{
                    background-color: {theme_manager.PRIMARY_DARK};
                    padding: {dp(15)}px {dp(30)}px;
                }}
            """)

        # 工作台按钮 - 增强悬停效果
        if hasattr(self, 'workspace_btn'):
            self.workspace_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {theme_manager.ACCENT};
                    color: {theme_manager.BUTTON_TEXT};
                    border: none;
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: {dp(16)}px {dp(32)}px;
                    font-size: {theme_manager.FONT_SIZE_LG};
                    font-weight: {theme_manager.FONT_WEIGHT_SEMIBOLD};
                    letter-spacing: {theme_manager.LETTER_SPACING_WIDE};
                }}
                QPushButton:hover {{
                    background-color: {theme_manager.ACCENT_LIGHT};
                    padding: {dp(18)}px {dp(34)}px;
                }}
                QPushButton:pressed {{
                    background-color: {theme_manager.ACCENT_DARK};
                    padding: {dp(15)}px {dp(30)}px;
                }}
            """)

    def _animate_entrance(self):
        """入场动画 - 淡入效果和呼吸动画"""
        # 标题淡入动画
        title_anim = QPropertyAnimation(self.title_opacity, b"opacity")
        title_anim.setDuration(800)
        title_anim.setStartValue(0.0)
        title_anim.setEndValue(1.0)
        title_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        title_anim.start()

        # 保存动画引用防止被垃圾回收
        self.title_animation = title_anim

        # 副标题淡入动画（延迟200ms）
        subtitle_anim = QPropertyAnimation(self.subtitle_opacity, b"opacity")
        subtitle_anim.setDuration(800)
        subtitle_anim.setStartValue(0.0)
        subtitle_anim.setEndValue(1.0)
        subtitle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # 延迟启动
        QTimer.singleShot(200, subtitle_anim.start)

        # 保存动画引用
        self.subtitle_animation = subtitle_anim

        # 标题呼吸动画（延迟1000ms后启动循环）
        QTimer.singleShot(1000, self._start_breathing_animation)

    def _start_breathing_animation(self):
        """启动标题呼吸动画 - 使用QPropertyAnimation替代QTimer"""
        # 创建缩放动画（从1.0到1.03，循环播放）
        self.breathing_anim = QPropertyAnimation(self.title, b"scale")
        self.breathing_anim.setDuration(3000)  # 3秒一个周期
        self.breathing_anim.setStartValue(1.0)
        self.breathing_anim.setEndValue(1.03)
        self.breathing_anim.setEasingCurve(QEasingCurve.Type.InOutSine)  # 平滑的正弦曲线
        self.breathing_anim.setLoopCount(-1)  # 无限循环

        # 使用QSequentialAnimationGroup实现往返动画
        self.breathing_group = QSequentialAnimationGroup()

        # 放大动画
        scale_up = QPropertyAnimation(self.title, b"scale")
        scale_up.setDuration(1500)  # 1.5秒放大
        scale_up.setStartValue(1.0)
        scale_up.setEndValue(1.03)
        scale_up.setEasingCurve(QEasingCurve.Type.InOutSine)

        # 缩小动画
        scale_down = QPropertyAnimation(self.title, b"scale")
        scale_down.setDuration(1500)  # 1.5秒缩小
        scale_down.setStartValue(1.03)
        scale_down.setEndValue(1.0)
        scale_down.setEasingCurve(QEasingCurve.Type.InOutSine)

        self.breathing_group.addAnimation(scale_up)
        self.breathing_group.addAnimation(scale_down)
        self.breathing_group.setLoopCount(-1)  # 无限循环
        self.breathing_group.start()

    def onShow(self):
        """页面显示时启动动画"""
        # 启动粒子动画
        if hasattr(self, 'particle_bg') and hasattr(self.particle_bg, 'timer'):
            if not self.particle_bg.timer.isActive():
                self.particle_bg.timer.start(50)

        # 启动呼吸动画
        if hasattr(self, 'breathing_group'):
            if self.breathing_group.state() != QSequentialAnimationGroup.State.Running:
                self.breathing_group.start()

    def onHide(self):
        """页面隐藏时停止动画以节省CPU"""
        # 停止粒子动画
        if hasattr(self, 'particle_bg') and hasattr(self.particle_bg, 'timer'):
            self.particle_bg.timer.stop()

        # 停止呼吸动画
        if hasattr(self, 'breathing_group'):
            self.breathing_group.pause()

