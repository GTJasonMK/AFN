"""
常量定义模块

集中管理项目中使用的常量，避免魔术数字散落在代码各处。

模块包含：
- WorkerTimeouts: Worker线程超时配置
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


class VersionConstants:
    """版本管理相关常量"""
    # 最大版本卡片数量（workspace.py中使用）
    MAX_VERSION_CARDS = 10

    # 版本内容预览长度
    VERSION_PREVIEW_LENGTH = 200

    # 版本标题最大长度
    VERSION_TITLE_MAX_LENGTH = 50


class NovelConstants:
    """小说创作相关常量（与后端保持一致）"""

    # 部分大纲配置
    CHAPTERS_PER_PART = 25  # 每部分包含的章节数（长篇小说分部阈值）
    LONG_NOVEL_THRESHOLD = 50  # 长篇小说阈值（章节数>=此值需使用部分大纲）

    # 章节数范围验证
    MIN_TOTAL_CHAPTERS = 5  # 最小章节数
    MAX_TOTAL_CHAPTERS = 10000  # 最大章节数


class SSEConstants:
    """SSE (Server-Sent Events) 相关常量"""

    # Token批量发射间隔（秒）
    # 将高频token累积后批量发射，减少UI更新频率
    TOKEN_FLUSH_INTERVAL = 0.1

    # SSE连接超时配置（秒）
    CONNECT_TIMEOUT = 10   # 连接建立超时
    READ_TIMEOUT = 300     # 读取超时（5分钟，适应长时间生成）

    # 错误响应文本最大长度
    # 超过此长度的错误文本将被截断，避免显示过长的错误信息
    ERROR_TEXT_MAX_LENGTH = 200
