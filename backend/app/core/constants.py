"""
常量定义模块

集中管理应用中使用的所有常量，提升代码可维护性和可读性。
"""

from enum import Enum


class GenerationStatus(str, Enum):
    """生成任务状态枚举

    用于统一管理部分大纲、章节等生成任务的状态，消除魔术字符串。
    继承str使其可以直接与字符串比较，保持向后兼容。
    """
    PENDING = "pending"          # 等待生成
    GENERATING = "generating"    # 正在生成
    CANCELLING = "cancelling"    # 请求取消中
    COMPLETED = "completed"      # 生成完成
    FAILED = "failed"           # 生成失败
    PARTIAL = "partial"         # 部分完成


# ProjectStatus 定义在 state_machine.py 中，避免循环导入
# 使用时请从 app.core.state_machine 导入


class NovelConstants:
    """小说创作相关常量"""

    # 部分大纲配置
    CHAPTERS_PER_PART = 25  # 每部分包含的章节数（长篇小说分部阈值）
    LONG_NOVEL_THRESHOLD = 50  # 长篇小说阈值（章节数>=此值需使用部分大纲）

    # 默认章节数（基于对话轮次推断）
    DEFAULT_CHAPTERS_SHORT = 30  # 简单短篇故事（对话轮次 ≤ 5）
    DEFAULT_CHAPTERS_MEDIUM = 80  # 中等复杂度（对话轮次 6-10）
    DEFAULT_CHAPTERS_LONG = 150  # 复杂史诗（对话轮次 > 10）

    # 章节数范围验证
    MIN_TOTAL_CHAPTERS = 5  # 最小章节数
    MAX_TOTAL_CHAPTERS = 10000  # 最大章节数

    # 对话轮次阈值
    CONVERSATION_ROUNDS_SHORT = 5  # 短篇对话轮次阈值
    CONVERSATION_ROUNDS_MEDIUM = 10  # 中篇对话轮次阈值


class LLMConstants:
    """LLM调用相关常量"""

    # 超时配置（秒）
    BLUEPRINT_GENERATION_TIMEOUT = 480.0  # 蓝图生成超时（8分钟）
    CHAPTER_GENERATION_TIMEOUT = 600.0  # 章节生成超时（10分钟）
    PART_OUTLINE_GENERATION_TIMEOUT = 300.0  # 分部大纲生成超时（5分钟）
    SUMMARY_GENERATION_TIMEOUT = 180.0  # 摘要生成超时（3分钟）
    DEFAULT_TIMEOUT = 120.0  # 默认超时（2分钟）

    # Token限制
    BLUEPRINT_MAX_TOKENS = 8192  # 蓝图生成最大输出tokens（Gemini 2.5 Flash限制）
    CHAPTER_MAX_TOKENS = 8192  # 章节生成最大输出tokens
    DEFAULT_MAX_TOKENS = 4096  # 默认最大tokens

    # Temperature配置
    BLUEPRINT_TEMPERATURE = 0.3  # 蓝图生成温度（较低，更确定性）
    CHAPTER_GENERATION_TEMPERATURE = 0.75  # 章节生成温度（较高，更有创造性）
    CHAPTER_RETRY_TEMPERATURE = 0.75  # 章节重试生成温度（与生成保持一致）
    SUMMARY_TEMPERATURE = 0.15  # 摘要生成温度（很低，高确定性）
    DEFAULT_TEMPERATURE = 0.7  # 默认温度

    # 重试配置
    MAX_RETRIES = 2  # LLM调用最大重试次数


class VectorConstants:
    """向量检索相关常量"""

    # 检索配置
    TOP_K_CHUNKS = 5  # RAG检索返回的chunk数量
    TOP_K_SUMMARIES = 3  # RAG检索返回的摘要数量

    # 文本处理
    CHUNK_MAX_LENGTH = 1000  # 单个chunk最大长度（字符）
    TAIL_EXCERPT_LENGTH = 1000  # 章节结尾摘录长度（字符）


class ChapterConstants:
    """章节相关常量"""

    # 版本配置
    DEFAULT_VERSION_COUNT = 3  # 默认生成的章节版本数量
    MAX_VERSIONS_PER_CHAPTER = 10  # 单章最大版本数

    # 上下文配置
    CONTEXT_PREVIOUS_CHAPTERS = 3  # 生成时参考的前文章节数
    SUMMARY_RECENT_CHAPTERS = 10  # 分层摘要中完整摘要的最近章节数


class HTTPConstants:
    """HTTP相关常量"""

    # 状态码
    HTTP_OK = 200
    HTTP_CREATED = 201
    HTTP_BAD_REQUEST = 400
    HTTP_NOT_FOUND = 404
    HTTP_CONFLICT = 409
    HTTP_SERVER_ERROR = 500
    HTTP_SERVICE_UNAVAILABLE = 503
