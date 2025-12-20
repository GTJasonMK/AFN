"""
设计系统共享常量

包含所有主题共享的设计规范，确保亮色/深色主题间的一致性。
"""


class DesignSystemConstants:
    """设计系统共享常量基类

    包含所有主题共享的设计规范，确保亮色/深色主题间的一致性。
    子类只需定义颜色相关属性。
    """

    # ==================== 圆角规范 - 方正风格（微圆角设计）====================
    # 遵循 4px 递增规律：2 -> 4 -> 6 -> 8 -> 12 -> 16
    RADIUS_XS = "2px"    # 超小元素（几乎直角）
    RADIUS_SM = "4px"    # 小元素：按钮、标签、小卡片
    RADIUS_MD = "6px"    # 中等元素：卡片、输入框
    RADIUS_LG = "8px"    # 大元素：大型容器
    RADIUS_XL = "16px"   # 超大元素：模态框（符合8pt网格）
    RADIUS_ROUND = "50%"  # 圆形：头像、图标按钮

    # ==================== 间距规范 - 8px网格系统 ====================
    SPACING_XS = "8px"
    SPACING_SM = "16px"
    SPACING_MD = "24px"
    SPACING_LG = "32px"
    SPACING_XL = "40px"
    SPACING_XXL = "48px"

    # ==================== 字体大小规范 - 符合8pt网格 ====================
    FONT_SIZE_XS = "12px"
    FONT_SIZE_SM = "12px"   # 修正：13px不符合8pt网格，改为12px
    FONT_SIZE_BASE = "14px"
    FONT_SIZE_MD = "16px"
    FONT_SIZE_LG = "18px"
    FONT_SIZE_XL = "20px"
    FONT_SIZE_2XL = "24px"
    FONT_SIZE_3XL = "32px"

    # ==================== 字体粗细规范 ====================
    FONT_WEIGHT_NORMAL = "400"
    FONT_WEIGHT_MEDIUM = "500"
    FONT_WEIGHT_SEMIBOLD = "600"
    FONT_WEIGHT_BOLD = "700"

    # ==================== 行高规范 - 符合可读性标准 ====================
    LINE_HEIGHT_TIGHT = "1.4"   # 修正：1.2低于最小可读性阈值，改为1.4
    LINE_HEIGHT_NORMAL = "1.5"
    LINE_HEIGHT_RELAXED = "1.6"
    LINE_HEIGHT_LOOSE = "1.8"

    # ==================== 字母间距规范 ====================
    LETTER_SPACING_TIGHT = "-0.02em"
    LETTER_SPACING_NORMAL = "0"
    LETTER_SPACING_WIDE = "0.05em"
    LETTER_SPACING_WIDER = "0.1em"
