"""
粒子系统模块

包含首页背景的粒子特效类，营造书香气息的视觉效果。
"""

import math
import random

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QPainterPath

from themes.theme_manager import theme_manager


class FloatingParticle:
    """基础粒子类"""

    def __init__(self, x, y, vx, vy, size, color, particle_type='dot'):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.particle_type = particle_type
        self.opacity = random.uniform(0.3, 0.7)
        self.phase = random.uniform(0, math.pi * 2)  # 用于呼吸效果
        self.rotation = random.uniform(0, 360)  # 旋转角度
        self.rotation_speed = random.uniform(-1, 1)  # 旋转速度
        self.life = 1.0  # 生命值（用于淡入淡出）
        self.pulse_speed = random.uniform(0.02, 0.05)  # 脉冲速度

    def update(self, width, height, time_tick):
        """更新粒子位置和状态"""
        self.x += self.vx
        self.y += self.vy
        self.rotation += self.rotation_speed
        self.phase += self.pulse_speed

        # 边界反弹
        if self.x <= 0 or self.x >= width:
            self.vx = -self.vx
        if self.y <= 0 or self.y >= height:
            self.vy = -self.vy

    def get_current_opacity(self):
        """获取当前透明度（带呼吸效果）"""
        breath = 0.3 + 0.2 * math.sin(self.phase)
        return self.opacity * breath * self.life


class InkParticle(FloatingParticle):
    """墨滴粒子 - 模拟墨水滴落扩散效果"""

    def __init__(self, x, y):
        vx = random.uniform(-0.15, 0.15)
        vy = random.uniform(-0.1, 0.2)  # 略向下飘
        size = random.uniform(3, 8)
        super().__init__(x, y, vx, vy, size, None, 'ink')
        self.spread = 0  # 扩散程度
        self.max_spread = random.uniform(0, 3)

    def update(self, width, height, time_tick):
        super().update(width, height, time_tick)
        # 缓慢扩散
        if self.spread < self.max_spread:
            self.spread += 0.01


class PaperParticle(FloatingParticle):
    """纸片粒子 - 模拟飘落的书页碎片"""

    def __init__(self, x, y):
        vx = random.uniform(-0.3, 0.3)
        vy = random.uniform(-0.2, 0.1)  # 略向上飘
        size = random.uniform(8, 15)
        super().__init__(x, y, vx, vy, size, None, 'paper')
        self.width_ratio = random.uniform(0.4, 0.8)  # 宽高比
        self.flutter = random.uniform(0.5, 1.5)  # 飘动幅度

    def update(self, width, height, time_tick):
        # 添加飘动效果
        self.x += math.sin(self.phase * 2) * self.flutter * 0.1
        super().update(width, height, time_tick)


class SparkleParticle(FloatingParticle):
    """星光粒子 - 闪烁的小光点"""

    def __init__(self, x, y):
        vx = random.uniform(-0.05, 0.05)
        vy = random.uniform(-0.05, 0.05)
        size = random.uniform(1, 3)
        super().__init__(x, y, vx, vy, size, None, 'sparkle')
        self.twinkle_speed = random.uniform(0.05, 0.15)

    def get_current_opacity(self):
        """闪烁效果"""
        twinkle = 0.2 + 0.8 * abs(math.sin(self.phase * 3))
        return self.opacity * twinkle * self.life


class CalligraphyStroke(FloatingParticle):
    """书法笔触粒子 - 优雅的曲线"""

    def __init__(self, x, y):
        vx = random.uniform(-0.1, 0.1)
        vy = random.uniform(-0.1, 0.1)
        size = random.uniform(20, 40)  # 笔触长度
        super().__init__(x, y, vx, vy, size, None, 'stroke')
        self.curve_amount = random.uniform(0.2, 0.5)  # 弯曲程度
        self.thickness = random.uniform(1, 2.5)  # 笔触粗细


class ParticleBackground(QWidget):
    """书香气息的粒子背景

    特效类型：
    - 墨滴：缓慢飘动的墨水滴，带扩散效果
    - 纸片：飘落的书页碎片，带旋转和飘动
    - 星光：闪烁的小光点，营造梦幻感
    - 笔触：优雅的书法曲线
    - 连线：近邻粒子间的淡淡连线，如星座图
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self._theme_connected = False
        self._time_tick = 0
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
                pass
            self._theme_connected = False

    def _on_theme_changed(self, theme_mode):
        """主题改变时刷新"""
        self.update()

    def _get_colors(self):
        """获取主题相关颜色"""
        is_dark = theme_manager.is_dark_mode()
        accent = theme_manager.book_accent_color()
        text_secondary = theme_manager.book_text_secondary()
        text_tertiary = theme_manager.TEXT_TERTIARY
        primary_light = theme_manager.PRIMARY_LIGHT
        bg_tertiary = theme_manager.BG_TERTIARY
        warning = theme_manager.WARNING
        warning_dark = theme_manager.WARNING_DARK

        if is_dark:
            return {
                'ink': QColor(accent),
                'ink_alt': QColor(primary_light),
                'paper': QColor(bg_tertiary),
                'sparkle': QColor(warning),
                'stroke': QColor(text_secondary),
                'line': QColor(accent),
            }
        else:
            return {
                'ink': QColor(text_secondary),
                'ink_alt': QColor(accent),
                'paper': QColor(bg_tertiary),
                'sparkle': QColor(warning_dark),
                'stroke': QColor(text_tertiary),
                'line': QColor(text_secondary),
            }

    def _init_particles(self):
        """初始化多种类型的粒子"""
        self.particles = []

        # 墨滴粒子（主要）
        for _ in range(15):
            x = random.randint(0, 1200)
            y = random.randint(0, 800)
            self.particles.append(InkParticle(x, y))

        # 纸片粒子
        for _ in range(8):
            x = random.randint(0, 1200)
            y = random.randint(0, 800)
            self.particles.append(PaperParticle(x, y))

        # 星光粒子
        for _ in range(20):
            x = random.randint(0, 1200)
            y = random.randint(0, 800)
            self.particles.append(SparkleParticle(x, y))

        # 书法笔触
        for _ in range(5):
            x = random.randint(0, 1200)
            y = random.randint(0, 800)
            self.particles.append(CalligraphyStroke(x, y))

    def _update_particles(self):
        """更新粒子位置"""
        self._time_tick += 1
        for particle in self.particles:
            particle.update(self.width(), self.height(), self._time_tick)
        self.update()

    def paintEvent(self, event):
        """绘制粒子"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = self._get_colors()

        # 1. 先绘制粒子间的连线（星座效果）
        self._draw_constellation_lines(painter, colors)

        # 2. 绘制各类粒子
        for particle in self.particles:
            if particle.particle_type == 'ink':
                self._draw_ink_particle(painter, particle, colors)
            elif particle.particle_type == 'paper':
                self._draw_paper_particle(painter, particle, colors)
            elif particle.particle_type == 'sparkle':
                self._draw_sparkle_particle(painter, particle, colors)
            elif particle.particle_type == 'stroke':
                self._draw_stroke_particle(painter, particle, colors)

    def _draw_constellation_lines(self, painter, colors):
        """绘制星座连线效果"""
        line_color = colors['line']
        max_distance = 150  # 最大连线距离

        # 只连接墨滴和星光粒子
        connectable = [p for p in self.particles if p.particle_type in ('ink', 'sparkle')]

        for i, p1 in enumerate(connectable):
            for p2 in connectable[i+1:]:
                dx = p1.x - p2.x
                dy = p1.y - p2.y
                distance = math.sqrt(dx * dx + dy * dy)

                if distance < max_distance:
                    # 距离越近，线越明显
                    alpha = int(20 * (1 - distance / max_distance))
                    if alpha > 0:
                        color = QColor(line_color)
                        color.setAlpha(alpha)
                        painter.setPen(QPen(color, 0.5))
                        painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))

    def _draw_ink_particle(self, painter, particle, colors):
        """绘制墨滴粒子"""
        color = colors['ink'] if random.random() > 0.3 else colors['ink_alt']
        opacity = particle.get_current_opacity()
        color.setAlpha(int(opacity * 60))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))

        # 主墨滴
        size = particle.size + particle.spread
        painter.drawEllipse(QPointF(particle.x, particle.y), size, size)

        # 墨晕效果（更大更淡的外圈）
        if particle.spread > 0:
            halo_color = QColor(color)
            halo_color.setAlpha(int(opacity * 15))
            painter.setBrush(QBrush(halo_color))
            painter.drawEllipse(QPointF(particle.x, particle.y), size * 1.8, size * 1.8)

    def _draw_paper_particle(self, painter, particle, colors):
        """绘制纸片粒子"""
        color = colors['paper']
        opacity = particle.get_current_opacity()
        color.setAlpha(int(opacity * 40))

        painter.save()
        painter.translate(particle.x, particle.y)
        painter.rotate(particle.rotation)

        # 绘制矩形纸片
        w = particle.size
        h = particle.size * particle.width_ratio
        rect = QRectF(-w/2, -h/2, w, h)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawRect(rect)

        # 纸片边缘高光
        edge_color = QColor(color)
        edge_color.setAlpha(int(opacity * 20))
        painter.setPen(QPen(edge_color, 0.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        painter.restore()

    def _draw_sparkle_particle(self, painter, particle, colors):
        """绘制星光粒子"""
        color = colors['sparkle']
        opacity = particle.get_current_opacity()
        color.setAlpha(int(opacity * 180))

        painter.setPen(Qt.PenStyle.NoPen)

        # 核心亮点
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(particle.x, particle.y), particle.size, particle.size)

        # 光晕
        glow_color = QColor(color)
        glow_color.setAlpha(int(opacity * 30))
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(QPointF(particle.x, particle.y), particle.size * 3, particle.size * 3)

        # 十字星芒
        if opacity > 0.5:
            star_color = QColor(color)
            star_color.setAlpha(int(opacity * 100))
            painter.setPen(QPen(star_color, 0.5))
            length = particle.size * 4
            painter.drawLine(
                QPointF(particle.x - length, particle.y),
                QPointF(particle.x + length, particle.y)
            )
            painter.drawLine(
                QPointF(particle.x, particle.y - length),
                QPointF(particle.x, particle.y + length)
            )

    def _draw_stroke_particle(self, painter, particle, colors):
        """绘制书法笔触"""
        color = colors['stroke']
        opacity = particle.get_current_opacity()
        color.setAlpha(int(opacity * 35))

        painter.save()
        painter.translate(particle.x, particle.y)
        painter.rotate(particle.rotation)

        # 使用贝塞尔曲线绘制优雅的笔触
        path = QPainterPath()
        length = particle.size
        curve = particle.curve_amount * length

        path.moveTo(-length/2, 0)
        path.cubicTo(
            QPointF(-length/4, -curve),
            QPointF(length/4, curve),
            QPointF(length/2, 0)
        )

        pen = QPen(color, particle.thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.restore()

    def start(self):
        """启动粒子动画"""
        if not self.timer.isActive():
            self.timer.start(33)  # ~30fps

    def stop(self):
        """停止粒子动画"""
        if self.timer.isActive():
            self.timer.stop()

    def is_running(self) -> bool:
        """检查动画是否正在运行"""
        return self.timer.isActive()

    def cleanup(self):
        """清理资源"""
        self.stop()
        self._disconnect_theme_signal()

    def deleteLater(self):
        """删除前清理"""
        self.cleanup()
        super().deleteLater()
