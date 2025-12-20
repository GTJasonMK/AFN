"""
主题属性代理 Mixin

将当前主题的颜色和设计常量以属性方式暴露给外部使用。
"""


class ThemePropertiesMixin:
    """主题属性代理 Mixin - 提供便捷的属性访问"""

    # ==================== 主色调属性 ====================
    @property
    def PRIMARY(self):
        return self._current_theme.PRIMARY

    @property
    def PRIMARY_LIGHT(self):
        return self._current_theme.PRIMARY_LIGHT

    @property
    def PRIMARY_DARK(self):
        return self._current_theme.PRIMARY_DARK

    @property
    def PRIMARY_PALE(self):
        return self._current_theme.PRIMARY_PALE

    @property
    def PRIMARY_GRADIENT(self):
        return getattr(self._current_theme, 'PRIMARY_GRADIENT', [self.PRIMARY, self.PRIMARY_DARK])

    # ==================== 强调色属性 ====================
    @property
    def ACCENT(self):
        return getattr(self._current_theme, 'ACCENT', self.PRIMARY)

    @property
    def ACCENT_LIGHT(self):
        return getattr(self._current_theme, 'ACCENT_LIGHT', self.PRIMARY_LIGHT)

    @property
    def ACCENT_DARK(self):
        return getattr(self._current_theme, 'ACCENT_DARK', self.PRIMARY_DARK)

    @property
    def ACCENT_PALE(self):
        return getattr(self._current_theme, 'ACCENT_PALE', self.PRIMARY_PALE)

    @property
    def ACCENT_GRADIENT(self):
        return getattr(self._current_theme, 'ACCENT_GRADIENT', [self.ACCENT, self.ACCENT_DARK])

    # 保留旧的强调色属性以兼容
    @property
    def ACCENT_PRIMARY(self):
        return self.SUCCESS

    @property
    def ACCENT_SECONDARY(self):
        return self.INFO

    @property
    def ACCENT_TERTIARY(self):
        return self.WARNING

    # ==================== 文字颜色属性 ====================
    @property
    def TEXT_PRIMARY(self):
        return self._current_theme.TEXT_PRIMARY

    @property
    def TEXT_SECONDARY(self):
        return self._current_theme.TEXT_SECONDARY

    @property
    def TEXT_TERTIARY(self):
        return self._current_theme.TEXT_TERTIARY

    @property
    def TEXT_PLACEHOLDER(self):
        return self._current_theme.TEXT_PLACEHOLDER

    @property
    def TEXT_DISABLED(self):
        return self._current_theme.TEXT_DISABLED

    # ==================== 背景颜色属性 ====================
    @property
    def BG_PRIMARY(self):
        return self._current_theme.BG_PRIMARY

    @property
    def BG_SECONDARY(self):
        return self._current_theme.BG_SECONDARY

    @property
    def BG_TERTIARY(self):
        return self._current_theme.BG_TERTIARY

    @property
    def BG_CARD(self):
        return self._current_theme.BG_CARD

    @property
    def BG_CARD_HOVER(self):
        return self._current_theme.BG_CARD_HOVER

    # ==================== 边框颜色属性 ====================
    @property
    def BORDER_DEFAULT(self):
        return self._current_theme.BORDER_DEFAULT

    @property
    def BORDER_LIGHT(self):
        return self._current_theme.BORDER_LIGHT

    @property
    def BORDER_DARK(self):
        return self._current_theme.BORDER_DARK

    # ==================== 按钮文字颜色属性 ====================
    @property
    def BUTTON_TEXT(self):
        """按钮文字颜色"""
        return self._current_theme.BUTTON_TEXT

    @property
    def BUTTON_TEXT_SECONDARY(self):
        """次要按钮文字颜色"""
        return self._current_theme.BUTTON_TEXT_SECONDARY

    # ==================== 特殊效果颜色属性 ====================
    @property
    def OVERLAY_COLOR(self):
        """遮罩层颜色"""
        return self._current_theme.OVERLAY_COLOR

    @property
    def SHADOW_COLOR(self):
        """阴影颜色"""
        return self._current_theme.SHADOW_COLOR

    # ==================== 语义颜色属性 ====================
    @property
    def SUCCESS(self):
        return self._current_theme.SUCCESS

    @property
    def SUCCESS_LIGHT(self):
        return self._current_theme.SUCCESS_LIGHT

    @property
    def SUCCESS_DARK(self):
        return self._current_theme.SUCCESS_DARK

    @property
    def SUCCESS_BG(self):
        return self._current_theme.SUCCESS_BG

    @property
    def ERROR(self):
        return self._current_theme.ERROR

    @property
    def ERROR_LIGHT(self):
        return self._current_theme.ERROR_LIGHT

    @property
    def ERROR_DARK(self):
        return self._current_theme.ERROR_DARK

    @property
    def ERROR_BG(self):
        return self._current_theme.ERROR_BG

    @property
    def WARNING(self):
        return self._current_theme.WARNING

    @property
    def WARNING_LIGHT(self):
        return self._current_theme.WARNING_LIGHT

    @property
    def WARNING_DARK(self):
        return self._current_theme.WARNING_DARK

    @property
    def WARNING_BG(self):
        return self._current_theme.WARNING_BG

    @property
    def INFO(self):
        return self._current_theme.INFO

    @property
    def INFO_LIGHT(self):
        return self._current_theme.INFO_LIGHT

    @property
    def INFO_DARK(self):
        return self._current_theme.INFO_DARK

    @property
    def INFO_BG(self):
        return self._current_theme.INFO_BG

    # ==================== 渐变属性 ====================
    @property
    def SUCCESS_GRADIENT(self):
        return self._current_theme.SUCCESS_GRADIENT

    @property
    def ERROR_GRADIENT(self):
        return self._current_theme.ERROR_GRADIENT

    @property
    def WARNING_GRADIENT(self):
        return self._current_theme.WARNING_GRADIENT

    @property
    def INFO_GRADIENT(self):
        return self._current_theme.INFO_GRADIENT

    # ==================== 设计系统常量 - 圆角 ====================
    @property
    def RADIUS_XS(self):
        return self._current_theme.RADIUS_XS

    @property
    def RADIUS_SM(self):
        return self._current_theme.RADIUS_SM

    @property
    def RADIUS_MD(self):
        return self._current_theme.RADIUS_MD

    @property
    def RADIUS_LG(self):
        return self._current_theme.RADIUS_LG

    @property
    def RADIUS_ROUND(self):
        return self._current_theme.RADIUS_ROUND

    # ==================== 设计系统常量 - 间距 ====================
    @property
    def SPACING_XS(self):
        return self._current_theme.SPACING_XS

    @property
    def SPACING_SM(self):
        return self._current_theme.SPACING_SM

    @property
    def SPACING_MD(self):
        return self._current_theme.SPACING_MD

    @property
    def SPACING_LG(self):
        return self._current_theme.SPACING_LG

    @property
    def SPACING_XL(self):
        return self._current_theme.SPACING_XL

    @property
    def SPACING_XXL(self):
        return self._current_theme.SPACING_XXL

    # ==================== 设计系统常量 - 字体大小 ====================
    @property
    def FONT_SIZE_XS(self):
        return self._current_theme.FONT_SIZE_XS

    @property
    def FONT_SIZE_SM(self):
        return self._current_theme.FONT_SIZE_SM

    @property
    def FONT_SIZE_BASE(self):
        return self._current_theme.FONT_SIZE_BASE

    @property
    def FONT_SIZE_MD(self):
        return self._current_theme.FONT_SIZE_MD

    @property
    def FONT_SIZE_LG(self):
        return self._current_theme.FONT_SIZE_LG

    @property
    def FONT_SIZE_XL(self):
        return self._current_theme.FONT_SIZE_XL

    @property
    def FONT_SIZE_2XL(self):
        return self._current_theme.FONT_SIZE_2XL

    @property
    def FONT_SIZE_3XL(self):
        return self._current_theme.FONT_SIZE_3XL

    # ==================== 设计系统常量 - 字体粗细 ====================
    @property
    def FONT_WEIGHT_NORMAL(self):
        return self._current_theme.FONT_WEIGHT_NORMAL

    @property
    def FONT_WEIGHT_MEDIUM(self):
        return self._current_theme.FONT_WEIGHT_MEDIUM

    @property
    def FONT_WEIGHT_SEMIBOLD(self):
        return self._current_theme.FONT_WEIGHT_SEMIBOLD

    @property
    def FONT_WEIGHT_BOLD(self):
        return self._current_theme.FONT_WEIGHT_BOLD

    # ==================== 设计系统常量 - 行高 ====================
    @property
    def LINE_HEIGHT_TIGHT(self):
        return self._current_theme.LINE_HEIGHT_TIGHT

    @property
    def LINE_HEIGHT_NORMAL(self):
        return self._current_theme.LINE_HEIGHT_NORMAL

    @property
    def LINE_HEIGHT_RELAXED(self):
        return self._current_theme.LINE_HEIGHT_RELAXED

    @property
    def LINE_HEIGHT_LOOSE(self):
        return self._current_theme.LINE_HEIGHT_LOOSE

    # ==================== 设计系统常量 - 字母间距 ====================
    @property
    def LETTER_SPACING_TIGHT(self):
        return self._current_theme.LETTER_SPACING_TIGHT

    @property
    def LETTER_SPACING_NORMAL(self):
        return self._current_theme.LETTER_SPACING_NORMAL

    @property
    def LETTER_SPACING_WIDE(self):
        return self._current_theme.LETTER_SPACING_WIDE

    @property
    def LETTER_SPACING_WIDER(self):
        return self._current_theme.LETTER_SPACING_WIDER
