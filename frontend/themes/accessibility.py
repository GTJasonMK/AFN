"""
可访问性主题扩展 - 符合2025年桌面应用最佳实践

提供：
- 明显的焦点指示器
- 键盘导航样式
- 高对比度模式支持
- 屏幕阅读器友好的语义化标签
"""

from .theme_manager import theme_manager


class AccessibilityTheme:
    """可访问性主题扩展（使用动态主题）"""

    @classmethod
    def focus_indicator(cls):
        """全局焦点指示器样式

        符合WCAG 2.1 AA级标准
        - 2px实线边框
        - 高对比度颜色
        - 明显的视觉反馈
        - 移除outline避免蓝色方框
        """
        return f"""
            *:focus {{
                outline: none;
            }}

            QPushButton:focus {{
                border: 2px solid {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY_PALE};
                outline: none;
            }}

            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {theme_manager.PRIMARY};
                background-color: {theme_manager.BG_PRIMARY};
                color: {theme_manager.TEXT_PRIMARY};
                outline: none;
            }}

            QListWidget::item:focus {{
                border: 2px solid {theme_manager.PRIMARY};
                background-color: {theme_manager.PRIMARY_PALE};
                outline: none;
            }}

            QTabBar::tab:focus {{
                border: 2px solid {theme_manager.PRIMARY};
                outline: none;
            }}
        """

    @classmethod
    def keyboard_navigation(cls):
        """键盘导航增强样式"""
        return f"""
            /* Tab键导航高亮 */
            QWidget[accessibleName="keyboard-focus"] {{
                border: 2px solid {theme_manager.INFO};
                background-color: {theme_manager.PRIMARY_PALE};
                outline: none;
            }}

            /* 选中项强调 */
            QListWidget::item:selected:active {{
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
            }}

            /* 禁用状态明显标识 */
            QPushButton:disabled {{
                opacity: 0.5;
            }}

            QLineEdit:disabled, QTextEdit:disabled {{
                background-color: {theme_manager.BG_TERTIARY};
                color: {theme_manager.TEXT_DISABLED};
                border-style: dashed;
            }}
        """

    @classmethod
    def high_contrast_mode(cls):
        """高对比度模式（支持亮色/深色主题）

        根据当前主题自动调整高对比度配色
        符合WCAG 2.1 AAA级对比度标准
        """
        is_dark = theme_manager.is_dark_mode()

        if is_dark:
            # 深色主题的高对比度模式
            text_color = "#FFFFFF"
            bg_color = "#000000"
            border_color = "#FFFFFF"
            focus_color = "#00FFFF"  # 青色焦点
        else:
            # 亮色主题的高对比度模式
            text_color = "#000000"
            bg_color = "#FFFFFF"
            border_color = "#000000"
            focus_color = theme_manager.PRIMARY

        return f"""
            /* 高对比度文本 */
            QLabel, QPushButton, QLineEdit, QTextEdit {{
                color: {text_color};
            }}

            /* 高对比度边框 */
            QFrame, QWidget {{
                border: 2px solid {border_color};
            }}

            /* 高对比度按钮 */
            QPushButton {{
                background-color: {bg_color};
                border: 3px solid {border_color};
                color: {text_color};
            }}

            QPushButton:hover {{
                background-color: {focus_color};
                color: {bg_color};
            }}

            QPushButton:pressed {{
                background-color: {theme_manager.PRIMARY_DARK};
                color: {theme_manager.BUTTON_TEXT};
            }}

            QPushButton:focus {{
                border: 4px solid {focus_color};
            }}

            /* 高对比度输入框 */
            QLineEdit, QTextEdit {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                color: {text_color};
            }}

            QLineEdit:focus, QTextEdit:focus {{
                border: 3px solid {focus_color};
            }}

            /* 高对比度列表项 */
            QListWidget::item:selected {{
                background-color: {focus_color};
                color: {bg_color};
            }}
        """

    @classmethod
    def tooltips(cls):
        """优化的工具提示样式"""
        return f"""
            QToolTip {{
                background-color: {theme_manager.TEXT_PRIMARY};
                color: {theme_manager.BG_PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {theme_manager.RADIUS_SM};
                padding: 8px 12px;
                font-size: {theme_manager.FONT_SIZE_SM};
                font-weight: {theme_manager.FONT_WEIGHT_MEDIUM};
            }}
        """

    @classmethod
    def get_all_accessibility_styles(cls):
        """获取所有可访问性样式"""
        return f"""
            {cls.focus_indicator()}
            {cls.keyboard_navigation()}
            {cls.tooltips()}
        """

