"""
常量定义模块

集中管理项目中使用的常量，避免魔术数字散落在代码各处。

模块包含：
- WorkerTimeouts: Worker线程超时配置
- UIConstants: UI布局相关常量
- PageConstants: 页面相关常量
- VersionConstants: 版本管理相关常量
"""


class WorkerTimeouts:
    """Worker 线程超时配置（毫秒）

    用于 QThread.wait() 方法的超时参数。
    """
    # 默认等待时间：用于一般 Worker 停止等待
    DEFAULT_MS = 1000

    # 强制终止前的等待时间：用于 terminate() 后的最终等待
    FORCE_TERMINATE_MS = 500

    # 长操作等待时间：用于可能需要更长时间完成的操作
    LONG_OPERATION_MS = 3000


class UIConstants:
    """UI布局相关常量

    集中管理UI布局中的魔术数字，使代码更易读和维护。
    """
    # ==================== 间距 ====================
    # 容器边距
    MARGIN_NONE = 0
    MARGIN_XS = 4
    MARGIN_SM = 8
    MARGIN_MD = 12
    MARGIN_LG = 16
    MARGIN_XL = 24
    MARGIN_XXL = 32

    # 组件间距
    SPACING_NONE = 0
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 16
    SPACING_XL = 24

    # ==================== 尺寸 ====================
    # 头部高度
    HEADER_HEIGHT = 64
    HEADER_HEIGHT_SM = 48

    # 侧边栏宽度
    SIDEBAR_WIDTH = 280
    SIDEBAR_WIDTH_SM = 240

    # 卡片最小高度
    CARD_MIN_HEIGHT = 80
    CARD_MIN_HEIGHT_SM = 60

    # 按钮尺寸
    BUTTON_HEIGHT_SM = 28
    BUTTON_HEIGHT_MD = 36
    BUTTON_HEIGHT_LG = 44

    # ==================== 圆角 ====================
    RADIUS_XS = 2
    RADIUS_SM = 4
    RADIUS_MD = 6
    RADIUS_LG = 8
    RADIUS_XL = 12

    # ==================== 动画 ====================
    ANIMATION_DURATION_FAST = 150
    ANIMATION_DURATION_NORMAL = 250
    ANIMATION_DURATION_SLOW = 400


class PageConstants:
    """页面相关常量"""
    # 页面缓存限制
    MAX_CACHED_PAGES = 10

    # 导航历史最大深度
    MAX_NAVIGATION_HISTORY = 50

    # 滚动延迟（毫秒）
    SCROLL_DELAY_MS = 100


class VersionConstants:
    """版本管理相关常量"""
    # 最大版本卡片数量（workspace.py中使用）
    MAX_VERSION_CARDS = 10

    # 版本内容预览长度
    VERSION_PREVIEW_LENGTH = 200

    # 版本标题最大长度
    VERSION_TITLE_MAX_LENGTH = 50


class ChapterConstants:
    """章节相关常量"""
    # 章节内容最小长度
    MIN_CHAPTER_LENGTH = 100

    # 章节内容建议长度
    RECOMMENDED_CHAPTER_LENGTH = 2000

    # 章节标题最大长度
    CHAPTER_TITLE_MAX_LENGTH = 100


class APIConstants:
    """API相关常量"""
    # 默认端口
    DEFAULT_PORT = 8123

    # 请求超时（秒）
    CONNECT_TIMEOUT = 10
    READ_TIMEOUT_DEFAULT = 60
    READ_TIMEOUT_GENERATION = 300
    READ_TIMEOUT_LONG = 600

    # 重试次数
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 1.0  # 基础重试延迟（秒）


class NovelConstants:
    """小说创作相关常量（与后端保持一致）"""

    # 部分大纲配置
    CHAPTERS_PER_PART = 25  # 每部分包含的章节数（长篇小说分部阈值）
    LONG_NOVEL_THRESHOLD = 50  # 长篇小说阈值（章节数>=此值需使用部分大纲）

    # 章节数范围验证
    MIN_TOTAL_CHAPTERS = 5  # 最小章节数
    MAX_TOTAL_CHAPTERS = 10000  # 最大章节数


class ConversationConstants:
    """对话相关常量（与后端保持一致）"""

    # 灵感对话轮数阈值
    TURNS_THRESHOLD = 5  # 对话轮数达到此值后可生成蓝图

