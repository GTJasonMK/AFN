"""
对话气泡组件 - 现代化设计 (2025)

展示用户和AI的对话消息，带渐变背景和动画效果
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QColor
from components.base import ThemeAwareFrame
from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from utils.dpi_utils import dp, sp


class ChatBubble(ThemeAwareFrame):
    """对话气泡 - 现代化设计，渐变背景"""

    def __init__(self, message, is_user=True, typing_effect=False, show_loading=False, parent=None):
        self.message = message
        self.is_user = is_user
        self.typing_effect = typing_effect
        self.is_loading = show_loading

        # 保存组件引用
        self.message_label = None
        self.sender_label = None

        # 打字机效果相关
        self.typing_timer = None
        self.typing_index = 0
        self.full_message = message

        # 加载动画相关
        self.loading_timer = None
        self.loading_dots = 0

        super().__init__(parent)
        self.setupUI()

        # 入场动画
        QTimer.singleShot(50, self._animate_entrance)

        # 如果是加载状态，启动加载动画
        if self.is_loading:
            self._start_loading_animation()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)  # 修正：20不符合8pt网格，改为24
        layout.setSpacing(12)

        # 发送者标签
        self.sender_label = QLabel("你" if self.is_user else "AI 助手")
        self.sender_label.setObjectName("sender_label")
        layout.addWidget(self.sender_label)

        # 消息内容 - 如果启用打字机效果，初始为空
        initial_text = "" if self.typing_effect else self.message
        self.message_label = QLabel(initial_text)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.message_label)

        # 为动画准备透明度效果
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        # 如果启用打字机效果，启动定时器
        if self.typing_effect:
            self.typing_timer = QTimer()
            self.typing_timer.timeout.connect(self._type_next_char)
            # 延迟启动打字机效果，等待入场动画完成
            QTimer.singleShot(500, self._start_typing)

    def _apply_theme(self):
        """应用主题样式（可多次调用） - 书香风格"""
        is_dark = theme_manager.is_dark_mode()
        ui_font = theme_manager.ui_font()
        highlight_color = theme_manager.book_accent_color()

        if self.is_user:
            # 用户气泡 - 使用 theme_manager 的颜色，避免硬编码
            if is_dark:
                bg_color = theme_manager.BG_TERTIARY
                text_color = theme_manager.TEXT_PRIMARY
            else:
                bg_color = theme_manager.PRIMARY_DARK  # 使用主题的深主色
                text_color = theme_manager.BUTTON_TEXT
            sender_color = highlight_color

            # 注意：不使用Python类名选择器，Qt不识别Python类名
            # 直接设置样式
            self.setStyleSheet(f"""
                background-color: {bg_color};
                border: none;
                border-radius: {dp(4)}px;
                border-top-right-radius: 0px;
            """)
        else:
            # AI气泡 - 透明背景 + 左侧装饰线
            border_color = highlight_color
            text_color = theme_manager.book_text_primary()
            sender_color = theme_manager.book_text_secondary()
            bg_color = "rgba(255, 255, 255, 0.05)" if is_dark else "rgba(0, 0, 0, 0.02)"

            # 注意：不使用Python类名选择器，Qt不识别Python类名
            # 直接设置样式
            self.setStyleSheet(f"""
                background-color: {bg_color};
                border: none;
                border-left: 3px solid {border_color};
                border-radius: {dp(2)}px;
            """)
            
            # 移除阴影效果
            # shadow = QGraphicsDropShadowEffect() ... 移除

        # 发送者标签
        if self.sender_label:
            self.sender_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(12)}px;
                font-weight: bold;
                color: {sender_color};
                letter-spacing: {dp(1)}px;
                margin-bottom: {dp(4)}px;
            """)

        # 消息内容
        if self.message_label:
            self.message_label.setStyleSheet(f"""
                font-family: {ui_font};
                font-size: {sp(15)}px;
                color: {text_color};
                line-height: 1.6;
                padding: 0px;
            """)

    def _animate_entrance(self):
        """入场动画 - 淡入+轻微上移"""
        # 淡入动画
        fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_anim.setDuration(400)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade_anim.start()

        # 保存动画引用防止被垃圾回收
        self.fade_animation = fade_anim

    def _start_typing(self):
        """启动打字机效果 - 根据内容长度动态调整速度"""
        if self.typing_timer:
            self.typing_index = 0

            # 根据消息长度动态调整打字速度
            message_length = len(self.full_message)
            if message_length > 300:
                # 长消息：跳过打字效果，直接显示
                self.message_label.setText(self.full_message)
                return
            elif message_length < 100:
                # 短消息：快速打字（20ms/字符）
                interval = 20
            else:
                # 中等消息：正常打字（30ms/字符）
                interval = 30

            self.typing_timer.start(interval)

    def _type_next_char(self):
        """显示下一个字符"""
        if self.typing_index < len(self.full_message):
            self.typing_index += 1
            # 更新显示的文本
            current_text = self.full_message[:self.typing_index]
            self.message_label.setText(current_text)
        else:
            # 打字完成，停止定时器
            if self.typing_timer:
                self.typing_timer.stop()

    def set_text(self, text):
        """设置气泡文本（用于SSE流式更新）"""
        if self.message_label:
            self.message_label.setText(text)
        self.full_message = text

    def get_text(self):
        """获取当前气泡文本"""
        if self.message_label:
            return self.message_label.text()
        return ""

    def append_text(self, text):
        """追加文本到气泡（用于SSE流式更新）"""
        # 如果是首次追加文本且正在加载，先停止加载动画
        if self.is_loading:
            self.stop_loading()

        current = self.get_text()
        self.set_text(current + text)

    def _start_loading_animation(self):
        """启动加载动画 - 循环显示点"""
        if not self.loading_timer:
            self.loading_timer = QTimer()
            self.loading_timer.timeout.connect(self._update_loading_dots)
            self.loading_timer.start(400)  # 每400ms更新一次
            self.loading_dots = 0
            self._update_loading_dots()

    def _update_loading_dots(self):
        """更新加载动画的点数"""
        self.loading_dots = (self.loading_dots % 3) + 1
        dots = "." * self.loading_dots
        loading_text = f"正在思考{dots}"
        if self.message_label:
            self.message_label.setText(loading_text)

    def stop_loading(self):
        """停止加载动画"""
        if self.loading_timer:
            self.loading_timer.stop()
            self.loading_timer = None
        self.is_loading = False
        # 清空加载文本
        if self.message_label:
            self.message_label.setText("")

    def closeEvent(self, event):
        """组件关闭时清理资源"""
        self._cleanup_timers()
        super().closeEvent(event)

    def deleteLater(self):
        """删除前清理资源"""
        self._cleanup_timers()
        super().deleteLater()

    def _cleanup_timers(self):
        """清理定时器"""
        if self.typing_timer:
            try:
                self.typing_timer.stop()
            except RuntimeError:
                pass  # 对象可能已被删除
            self.typing_timer = None
        if self.loading_timer:
            try:
                self.loading_timer.stop()
            except RuntimeError:
                pass  # 对象可能已被删除
            self.loading_timer = None