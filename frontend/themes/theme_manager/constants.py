"""
设计系统共享常量

包含所有主题共享的设计规范，确保亮色/深色主题间的一致性。
"""


class DesignSystemConstants:
    """设计系统共享常量基类

    包含所有主题共享的设计规范，确保亮色/深色主题间的一致性。
    子类只需定义颜色相关属性。
    """

    # ==================== 字体族规范 ====================
    # 深色主题 (Academia/Classical) 使用衬线字体
    # 浅色主题 (Organic/Natural) 使用衬线标题 + 圆角无衬线正文

    # 标题字体 - 衬线字体（优雅、古典）
    # Academia: Cormorant Garamond - 高对比度老式衬线，书法优雅
    # Organic: Fraunces - 可变字体，有柔和轴，老派温暖但现代
    FONT_HEADING = "'Noto Serif SC', 'Source Han Serif SC', serif"

    # 正文字体 - 适合长时间阅读
    # Academia: Crimson Pro - 书籍风格衬线，适合长文阅读
    # Organic: Nunito - 圆角终端，与有机形状呼应
    FONT_BODY = "'Noto Sans SC', 'Source Han Sans SC', sans-serif"

    # 展示/标签字体 - 用于特殊强调
    # Academia: Cinzel - 雕刻风格，全大写展示字体
    FONT_DISPLAY = "'Noto Serif SC', 'Source Han Serif SC', serif"

    # UI字体 - 界面元素
    FONT_UI = "'Noto Sans SC', 'Microsoft YaHei', 'PingFang SC', sans-serif"

    # 代码/等宽字体 - 用于状态指示器、代码显示等需要对齐的场景
    FONT_CODE = "'Consolas', 'Monaco', 'Courier New', monospace"

    # ==================== 圆角规范 - 方正风格（微圆角设计）====================
    # 遵循 4px 递增规律：2 -> 4 -> 6 -> 8 -> 12 -> 16
    RADIUS_XS = "2px"    # 超小元素（几乎直角）
    RADIUS_SM = "4px"    # 小元素：按钮、标签、小卡片
    RADIUS_MD = "6px"    # 中等元素：卡片、输入框
    RADIUS_LG = "8px"    # 大元素：大型容器
    RADIUS_XL = "16px"   # 超大元素：模态框（符合8pt网格）
    RADIUS_2XL = "24px"  # 特大元素：Organic主题大圆角
    RADIUS_3XL = "32px"  # 超特大：Organic主题容器
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
    LETTER_SPACING_WIDEST = "0.15em"  # Academia标签使用

    # ==================== 动画/过渡规范 ====================
    # Academia: 庄重、沉稳、平滑 - 像翻阅皮革书籍
    # Organic: 自然、轻柔 - 像拾起河石

    TRANSITION_FAST = "150ms"     # 快速交互（按钮按压、焦点）
    TRANSITION_BASE = "300ms"     # 标准过渡（hover、边框变化）
    TRANSITION_SLOW = "500ms"     # 缓慢过渡（卡片抬升）
    TRANSITION_DRAMATIC = "700ms" # 戏剧性效果（棕褐色滤镜、缩放）

    EASING_DEFAULT = "ease-out"   # 自然减速（两种主题通用）

    # ==================== 按钮尺寸规范 ====================
    BUTTON_HEIGHT_SM = "40px"
    BUTTON_HEIGHT_DEFAULT = "48px"
    BUTTON_HEIGHT_LG = "56px"

    BUTTON_PADDING_SM = "24px"
    BUTTON_PADDING_DEFAULT = "32px"
    BUTTON_PADDING_LG = "40px"
