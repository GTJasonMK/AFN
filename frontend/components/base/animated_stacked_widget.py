"""
动画堆叠窗口 - 支持淡入淡出切换效果
"""

from PyQt6.QtWidgets import QStackedWidget, QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QParallelAnimationGroup


class AnimatedStackedWidget(QStackedWidget):
    """
    带有切换动画的 QStackedWidget
    支持淡入淡出 (Fade) 和 滑动 (Slide) 效果
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_animating = False
        self._duration = 300
        self._easing_curve = QEasingCurve.Type.OutCubic

    def setCurrentIndex(self, index: int):
        """重写切换页面方法，添加动画"""
        if index == self.currentIndex():
            return

        if self._is_animating:
            # 如果正在动画中，直接完成
            return

        self._fade_transition(index)

    def _fade_transition(self, next_index: int):
        """淡入淡出过渡"""
        current_widget = self.currentWidget()
        next_widget = self.widget(next_index)

        if not current_widget:
            super().setCurrentIndex(next_index)
            return

        self._is_animating = True

        # 确保下一页可见且大小正确
        next_widget.setGeometry(self.rect())
        next_widget.show()
        next_widget.raise_() # 放在最上层

        # 创建透明度效果
        self.next_opacity = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(self.next_opacity)
        self.next_opacity.setOpacity(0.0)

        # 动画组
        self.anim_group = QParallelAnimationGroup()

        # 下一页淡入
        anim_in = QPropertyAnimation(self.next_opacity, b"opacity")
        anim_in.setDuration(self._duration)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)
        anim_in.setEasingCurve(self._easing_curve)
        self.anim_group.addAnimation(anim_in)

        # 当前页淡出 (可选，如果只需覆盖则不需要)
        # 简单的淡入覆盖通常效果更好且闪烁更少
        
        # 动画完成回调
        self.anim_group.finished.connect(lambda: self._on_animation_finished(next_index, next_widget))
        self.anim_group.start()

    def _on_animation_finished(self, next_index, next_widget):
        """动画结束清理"""
        super().setCurrentIndex(next_index)
        
        # 移除特效
        next_widget.setGraphicsEffect(None)
        
        self._is_animating = False
        
        # 确保其他页面隐藏（QStackedWidget默认行为，但动画过程中我们手动show了）
        for i in range(self.count()):
            if i != next_index:
                self.widget(i).hide()

    def setDuration(self, duration: int):
        """设置动画时长 (ms)"""
        self._duration = duration
