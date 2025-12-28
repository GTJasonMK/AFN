"""
书香风格样式 Mixin

提供书香风格的字体、颜色和样式方法。
"""

from .themes import BookPalette


class BookStylesMixin:
    """书香风格样式方法 Mixin"""

    # ==================== 字体方法 ====================

    def ui_font(self) -> str:
        """获取UI字体族 - 现代无衬线字体（包含emoji支持）"""
        # 包含emoji字体以正确渲染表情符号，避免显示为方框
        return "'Segoe UI', 'Microsoft YaHei', 'PingFang SC', 'Roboto', 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif"

    def serif_font(self) -> str:
        """获取衬线字体族 - 书香风格核心字体"""
        return "Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif"

    # ==================== 书香风格颜色方法 ====================

    def book_accent_color(self) -> str:
        """获取书香风格强调色 - 赭石(亮)/暖琥珀(暗)"""
        return "#8B4513" if self.is_light_mode() else "#E89B6C"

    def book_accent_light(self) -> str:
        """获取书香风格浅强调色"""
        return "#A0522D" if self.is_light_mode() else "#F2B896"

    def book_text_primary(self) -> str:
        """获取书香风格主文字色 - 深褐(亮)/暖白(暗)"""
        return "#2C1810" if self.is_light_mode() else "#F5F0EB"

    def book_text_secondary(self) -> str:
        """获取书香风格次要文字色"""
        return "#5D4037" if self.is_light_mode() else "#D4CCC4"

    def book_text_tertiary(self) -> str:
        """获取书香风格三级文字色 - 确保在对应背景上有足够对比度"""
        # 亮色模式使用更深的灰色，深色模式使用暖浅灰
        return "#6D6560" if self.is_light_mode() else "#C4BAB0"

    def book_bg_primary(self) -> str:
        """获取书香风格主背景色 - 米色(亮)/深暖褐(暗)"""
        return "#F9F5F0" if self.is_light_mode() else "#171412"

    def book_bg_secondary(self) -> str:
        """获取书香风格次要背景色 - 亮米色(亮)/中暖褐(暗)"""
        return "#FFFBF0" if self.is_light_mode() else "#1F1B18"

    def book_border_color(self) -> str:
        """获取书香风格边框色"""
        return "#D7CCC8" if self.is_light_mode() else "#3D3835"

    # ==================== 语义文字颜色方法 ====================

    def text_success(self) -> str:
        """获取用于文字的成功色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的绿色，深色模式使用标准成功色
        return "#2E7D4A" if self.is_light_mode() else "#4ade80"

    def text_warning(self) -> str:
        """获取用于文字的警告色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的琥珀棕色（对比度 > 5:1），深色模式使用标准警告色
        return "#8B5A00" if self.is_light_mode() else "#fbbf24"

    def text_error(self) -> str:
        """获取用于文字的错误色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的红色，深色模式使用标准错误色
        return "#B8433C" if self.is_light_mode() else "#fb7185"

    def text_info(self) -> str:
        """获取用于文字的信息色 - 确保在背景上有足够对比度"""
        # 亮色模式使用更深的蓝色，深色模式使用标准信息色
        return "#2A6B8F" if self.is_light_mode() else "#38bdf8"

    # ==================== 玻璃态效果 ====================

    def glassmorphism_bg(self, opacity: float = 0.85) -> str:
        """获取玻璃态背景色

        Args:
            opacity: 透明度 (0.0-1.0)

        Returns:
            rgba颜色字符串
        """
        if self.is_dark_mode():
            # 深色模式 - 暖褐玻璃效果（与暖夜书香主题一致）
            return f"rgba(26, 23, 20, {opacity})"
        else:
            # 亮色模式 - 暖米色玻璃
            return f"rgba(255, 251, 240, {opacity})"

    # ==================== 书香风格组件样式 ====================

    def book_card_style(self, hover: bool = False) -> str:
        """书香风格卡片样式

        Args:
            hover: 是否为悬停状态

        Returns:
            CSS样式字符串
        """
        bg = self.book_bg_secondary()
        border = self.book_border_color()
        accent = self.book_accent_color()

        if hover:
            return f"""
                background-color: {bg};
                border: 1px solid {accent};
                border-radius: 4px;
            """
        return f"""
            background-color: {bg};
            border: 1px solid {border};
            border-radius: 4px;
        """

    def book_title_style(self, size: int = 28) -> str:
        """书香风格标题样式

        Args:
            size: 字体大小 (px)

        Returns:
            CSS样式字符串
        """
        return f"""
            font-family: {self.serif_font()};
            font-size: {size}px;
            font-weight: bold;
            color: {self.book_text_primary()};
            letter-spacing: 2px;
        """

    def book_body_style(self, size: int = 15) -> str:
        """书香风格正文样式

        Args:
            size: 字体大小 (px)

        Returns:
            CSS样式字符串
        """
        return f"""
            font-family: {self.serif_font()};
            font-size: {size}px;
            color: {self.book_text_primary()};
            line-height: 1.8;
        """

    def book_button_style(self, primary: bool = False) -> str:
        """书香风格按钮样式

        Args:
            primary: 是否为主要按钮

        Returns:
            CSS样式字符串
        """
        accent = self.book_accent_color()
        text_secondary = self.book_text_secondary()
        border = self.book_border_color()
        serif = self.serif_font()

        if primary:
            return f"""
                QPushButton {{
                    background-color: {accent};
                    color: {self.BUTTON_TEXT};
                    border: 1px solid {accent};
                    border-radius: 4px;
                    font-family: {serif};
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.book_text_primary()};
                    border-color: {self.book_text_primary()};
                }}
                QPushButton:pressed {{
                    background-color: {self.book_accent_light()};
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {text_secondary};
                    border: 1px solid {border};
                    border-radius: 4px;
                    font-family: {serif};
                    padding: 8px 16px;
                }}
                QPushButton:hover {{
                    color: {accent};
                    border-color: {accent};
                    background-color: rgba(0,0,0,0.03);
                }}
                QPushButton:pressed {{
                    background-color: rgba(0,0,0,0.05);
                }}
            """

    def book_tag_style(self, accent: bool = False) -> str:
        """书香风格标签样式

        Args:
            accent: 是否使用强调色

        Returns:
            CSS样式字符串
        """
        border = self.book_border_color()
        text = self.book_text_secondary()
        bg = "transparent"
        serif = self.serif_font()

        if accent:
            color = self.book_accent_color()
            return f"""
                background-color: {bg};
                color: {color};
                border: 1px solid {color};
                padding: 4px 12px;
                border-radius: 4px;
                font-family: {serif};
                font-size: 12px;
                font-weight: bold;
            """
        return f"""
            background-color: {bg};
            color: {text};
            border: 1px solid {border};
            padding: 4px 12px;
            border-radius: 4px;
            font-family: {serif};
            font-size: 12px;
        """

    def book_input_style(self) -> str:
        """书香风格输入框样式"""
        bg = self.book_bg_secondary()
        border = self.book_border_color()
        text = self.book_text_primary()
        accent = self.book_accent_color()
        serif = self.serif_font()

        return f"""
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 12px 16px;
                font-family: {serif};
                font-size: 15px;
                color: {text};
                line-height: 1.8;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border-color: {accent};
            }}
        """

    def book_separator(self, vertical: bool = False) -> str:
        """书香风格分隔线样式

        Args:
            vertical: 是否为垂直分隔线

        Returns:
            CSS样式字符串
        """
        border = self.book_border_color()
        if vertical:
            return f"border-left: 1px solid {border};"
        return f"border-top: 1px solid {border};"

    def get_book_palette(self) -> BookPalette:
        """获取书香风格完整调色板

        返回一个命名元组，包含所有常用的书香风格颜色和字体，
        用于在组件的 _apply_theme 方法中一次性获取所有颜色，
        减少重复代码。

        Returns:
            BookPalette: 包含所有常用颜色和字体的命名元组

        Example:
            def _apply_theme(self):
                palette = theme_manager.get_book_palette()
                self.title_label.setStyleSheet(f"color: {palette.text_primary};")
                self.content.setStyleSheet(f"background: {palette.bg_primary};")
        """
        return BookPalette(
            bg_primary=self.book_bg_primary(),
            bg_secondary=self.book_bg_secondary(),
            text_primary=self.book_text_primary(),
            text_secondary=self.book_text_secondary(),
            text_tertiary=self.book_text_tertiary(),
            accent_color=self.book_accent_color(),
            accent_light=self.book_accent_light(),
            border_color=self.book_border_color(),
            serif_font=self.serif_font(),
            ui_font=self.ui_font(),
        )
