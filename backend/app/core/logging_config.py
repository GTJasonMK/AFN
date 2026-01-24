"""
日志配置模块

提供按功能域分离的日志系统，使用程序化配置确保严格的日志隔离：
- app.log: 系统级别日志（启动、配置、数据库、未匹配的模块）
- manga.log: 漫画分镜功能
- coding.log: 编程项目功能
- novel.log: 小说创作功能
- llm.log: LLM调用日志
- image.log: 图片生成功能
- embedding.log: 向量检索日志
- queue.log: 队列处理日志

支持用户自定义配置文件: storage/logging_config.yaml
"""

import sys
import logging
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any

import yaml

from .config import settings


# ============================================================
# 功能域映射配置
# ============================================================

# Logger命名空间 -> 功能域文件映射
# 注意：匹配时按前缀长度从长到短匹配，确保更精确的匹配优先
LOGGER_DOMAIN_MAPPING = {
    # 漫画功能 -> manga.log
    "app.services.manga_prompt": "manga",
    "app.api.routers.writer.manga_prompt": "manga",
    "app.api.routers.writer.manga_prompt_v2": "manga",  # 添加 v2 路由

    # 编程功能 -> coding.log
    "app.services.coding": "coding",
    "app.services.coding_files": "coding",
    "app.services.coding_rag": "coding",
    "app.api.routers.coding": "coding",

    # 小说功能 -> novel.log
    "app.services.chapter_generation": "novel",
    "app.services.chapter_analysis": "novel",
    "app.services.chapter_context": "novel",
    "app.services.chapter_evaluation": "novel",
    "app.services.chapter_ingest": "novel",
    "app.services.chapter_version": "novel",
    "app.services.part_outline": "novel",
    "app.services.novel_rag": "novel",
    "app.services.novel_service": "novel",
    "app.services.content_optimization": "novel",
    "app.services.blueprint_service": "novel",
    "app.services.inspiration_service": "novel",
    "app.services.conversation_service": "novel",
    "app.services.import_analysis": "novel",
    "app.services.protagonist_profile": "novel",
    "app.services.foreshadowing": "novel",
    "app.services.summary_service": "novel",
    "app.services.incremental_indexer": "novel",
    "app.services.prompt_builder": "novel",
    "app.api.routers.novels": "novel",
    "app.api.routers.writer": "novel",
    "app.api.routers.protagonist": "novel",

    # LLM调用 -> llm.log
    "app.services.llm_service": "llm",
    "app.services.llm_wrappers": "llm",
    "app.services.llm_config": "llm",
    "app.api.routers.llm_config": "llm",
    "app.utils.llm_request_logger": "llm",
    "app.utils.llm_tool": "llm",

    # 图片生成 -> image.log
    "app.services.image_generation": "image",
    "app.services.avatar_service": "image",
    "app.services.character_portrait": "image",
    "app.api.routers.image_generation": "image",
    "app.api.routers.character_portrait": "image",

    # 向量/嵌入 -> embedding.log
    "app.services.vector_store": "embedding",
    "app.services.embedding": "embedding",
    "app.services.rag": "embedding",
    "app.services.rag_common": "embedding",
    "app.api.routers.embedding_config": "embedding",

    # 队列 -> queue.log
    "app.services.queue": "queue",
    "app.api.routers.queue": "queue",

    # 数据库 -> db.log
    "app.db": "db",
    "app.repositories": "db",
    "sqlalchemy.engine": "db",
}

# 默认功能域（未匹配的logger归入此域）
DEFAULT_DOMAIN = "app"

# 所有功能域列表
ALL_DOMAINS = ["app", "manga", "coding", "novel", "llm", "image", "embedding", "queue", "db"]

# 默认日志级别配置
DEFAULT_LEVELS = {
    "app": "INFO",
    "manga": "INFO",
    "coding": "INFO",
    "novel": "INFO",
    "llm": "WARNING",       # LLM日志默认只看警告和错误
    "image": "INFO",
    "embedding": "WARNING",  # 向量检索日志默认只看警告
    "queue": "INFO",
    "db": "WARNING",        # 数据库日志默认只看警告（避免SQL刷屏）
}

# 第三方库日志级别（减少噪音）
THIRD_PARTY_LEVELS = {
    "httpx": "WARNING",
    "httpcore": "WARNING",
    "uvicorn.access": "WARNING",
    "uvicorn.error": "INFO",
    "asyncio": "WARNING",
    "aiosqlite": "WARNING",
    "chromadb": "WARNING",
    "sentence_transformers": "WARNING",
    "transformers": "WARNING",
    "torch": "WARNING",
}

# 日志格式
CONSOLE_FORMAT = "%(asctime)s [%(levelname).1s] %(name)s - %(message)s"
CONSOLE_DATE_FORMAT = "%H:%M:%S"
FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
FILE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================
# 配置加载
# ============================================================

def _get_logs_dir() -> Path:
    """获取日志目录路径"""
    logs_dir = settings.storage_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _get_config_path() -> Path:
    """获取用户配置文件路径"""
    return settings.storage_dir / "logging_config.yaml"


def _load_user_config() -> Dict[str, Any]:
    """
    加载用户自定义日志配置

    Returns:
        配置字典，如果文件不存在或解析失败返回空字典
    """
    config_path = _get_config_path()
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        print(f"[WARNING] 加载日志配置文件失败: {e}")
        return {}


def _get_domain_for_logger(logger_name: str) -> str:
    """
    根据logger名称确定所属功能域

    使用前缀匹配，按前缀长度从长到短匹配，确保更精确的匹配优先。

    Args:
        logger_name: logger的__name__值

    Returns:
        功能域名称
    """
    # 按前缀长度从长到短排序
    sorted_prefixes = sorted(
        LOGGER_DOMAIN_MAPPING.keys(),
        key=len,
        reverse=True
    )

    for prefix in sorted_prefixes:
        if logger_name.startswith(prefix):
            return LOGGER_DOMAIN_MAPPING[prefix]

    return DEFAULT_DOMAIN


def _get_level_for_domain(domain: str, user_config: Dict[str, Any]) -> int:
    """
    获取功能域的日志级别（返回整数）

    Args:
        domain: 功能域名称
        user_config: 用户配置

    Returns:
        日志级别整数值
    """
    # 优先使用用户配置
    user_levels = user_config.get("levels", {})
    if domain in user_levels:
        level_str = user_levels[domain]
    else:
        level_str = DEFAULT_LEVELS.get(domain, "INFO")

    return getattr(logging, level_str.upper(), logging.INFO)


# ============================================================
# 自定义Filter
# ============================================================

class DomainFilter(logging.Filter):
    """
    按功能域过滤日志

    只允许属于指定功能域的日志通过，确保每个域的日志文件只包含该域的日志。
    """

    def __init__(self, domain: str, name: str = ""):
        super().__init__(name)
        self.domain = domain

    def filter(self, record: logging.LogRecord) -> bool:
        """检查日志记录是否属于此功能域"""
        record_domain = _get_domain_for_logger(record.name)
        return record_domain == self.domain


class ConsoleDomainLevelFilter(logging.Filter):
    """
    控制台输出的域级别过滤器

    根据日志所属功能域动态应用不同的日志级别过滤。
    """

    def __init__(self, domain_levels: Dict[str, int], name: str = ""):
        super().__init__(name)
        self.domain_levels = domain_levels

    def filter(self, record: logging.LogRecord) -> bool:
        """根据功能域检查日志级别"""
        domain = _get_domain_for_logger(record.name)
        min_level = self.domain_levels.get(domain, logging.INFO)
        return record.levelno >= min_level


# ============================================================
# 日志配置（程序化配置）
# ============================================================

# 全局存储已创建的handlers，用于后续动态调整
_domain_handlers: Dict[str, RotatingFileHandler] = {}
_console_handler: logging.Handler = None
_console_filter: "ConsoleDomainLevelFilter" = None


def setup_logging() -> None:
    """
    配置日志系统（程序化配置）

    使用程序化方式配置日志，确保 DomainFilter 正确应用到每个文件handler。
    必须在导入其他模块之前调用。
    """
    global _domain_handlers, _console_handler, _console_filter

    # 确保日志目录存在
    logs_dir = _get_logs_dir()

    # 创建默认配置文件（如果不存在）
    _create_default_config_if_needed()

    # 加载用户配置
    user_config = _load_user_config()

    # 创建格式化器
    console_formatter = logging.Formatter(CONSOLE_FORMAT, CONSOLE_DATE_FORMAT)
    file_formatter = logging.Formatter(FILE_FORMAT, FILE_DATE_FORMAT)

    # 计算每个域的日志级别
    domain_levels = {}
    for domain in ALL_DOMAINS:
        domain_levels[domain] = _get_level_for_domain(domain, user_config)

    # 获取 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设为最低，让handlers决定实际级别

    # 清理已有的handlers（防止重复配置）
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    # 检查是否启用控制台输出
    console_config = user_config.get("console", {})
    console_enabled = console_config.get("enabled", True)

    if console_enabled:
        # 创建控制台handler（带域级别过滤器）
        # 注意：启动期间后端stdout被重定向到文件，所以实际输出到backend_console.log
        _console_handler = logging.StreamHandler(sys.stdout)
        _console_handler.setLevel(logging.DEBUG)  # 让filter决定实际级别
        _console_handler.setFormatter(console_formatter)
        _console_filter = ConsoleDomainLevelFilter(domain_levels)
        _console_handler.addFilter(_console_filter)
        root_logger.addHandler(_console_handler)

    # 为每个功能域创建独立的文件handler（带域过滤器）
    _domain_handlers.clear()
    for domain in ALL_DOMAINS:
        log_file = logs_dir / f"{domain}.log"
        handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(domain_levels[domain])
        handler.setFormatter(file_formatter)
        handler.addFilter(DomainFilter(domain))  # 关键：添加域过滤器
        root_logger.addHandler(handler)
        _domain_handlers[domain] = handler

    # 配置第三方库日志级别（不低于 app 域的级别）
    app_level = domain_levels.get("app", logging.INFO)
    for logger_name, level_str in THIRD_PARTY_LEVELS.items():
        default_level = getattr(logging, level_str.upper(), logging.WARNING)
        # 使用配置级别和 app 级别中较高的那个
        effective_level = max(default_level, app_level)
        third_party_logger = logging.getLogger(logger_name)
        third_party_logger.setLevel(effective_level)

    # 显式设置 sqlalchemy 相关 logger 的级别（跟随 db 域配置）
    db_level = domain_levels["db"]
    for sa_logger_name in ["sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine"]:
        sa_logger = logging.getLogger(sa_logger_name)
        sa_logger.setLevel(db_level)

    # 应用用户自定义的模块级别覆盖
    user_overrides = user_config.get("overrides", {})
    for logger_name, level_str in user_overrides.items():
        override_logger = logging.getLogger(logger_name)
        override_logger.setLevel(getattr(logging, level_str.upper(), logging.DEBUG))


def _create_default_config_if_needed() -> None:
    """如果用户配置文件不存在，创建默认配置"""
    config_path = _get_config_path()
    if config_path.exists():
        return

    default_config = """# AFN 日志配置文件
# 修改后需要重启后端服务生效

# 各功能域的日志级别配置
# 可选值: DEBUG, INFO, WARNING, ERROR
levels:
  app: INFO           # 系统日志（启动、配置）
  manga: INFO         # 漫画分镜功能
  coding: INFO        # 编程项目功能
  novel: INFO         # 小说创作功能
  llm: WARNING        # LLM调用日志（默认只看警告和错误，调试时改为DEBUG）
  image: INFO         # 图片生成功能
  embedding: WARNING  # 向量检索日志
  queue: INFO         # 队列处理日志
  db: WARNING         # 数据库操作日志（默认关闭SQL输出，调试时改为DEBUG）

# 控制台输出开关
console:
  enabled: true

# 特定模块的日志级别覆盖（可选）
# 用于调试特定模块时临时启用DEBUG
# overrides:
#   app.services.manga_prompt.core.service: DEBUG
#   app.services.chapter_generation.workflow: DEBUG
#   sqlalchemy.engine: DEBUG  # 看SQL语句
"""

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(default_config)
    except Exception as e:
        print(f"[WARNING] 创建默认日志配置文件失败: {e}")


def setup_exception_hook() -> None:
    """
    设置全局异常钩子，捕获未处理的异常并记录到日志
    """
    original_hook = sys.excepthook

    def exception_hook(exc_type, exc_value, exc_traceback):
        # 记录到日志
        logger = logging.getLogger(__name__)
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical(f"未捕获的异常导致程序崩溃:\n{error_msg}")

        # 确保日志被写入
        for handler in logging.root.handlers:
            handler.flush()

        # 调用原始钩子
        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_hook


def log_startup_info() -> None:
    """
    输出启动信息到日志
    """
    logger = logging.getLogger(__name__)
    user_config = _load_user_config()

    logger.info("=" * 60)
    logger.info("AFN 后端服务启动")
    logger.info("日志目录: %s", _get_logs_dir())
    logger.info("日志级别配置:")
    for domain in ALL_DOMAINS:
        level = _get_level_for_domain(domain, user_config)
        level_name = logging.getLevelName(level)
        logger.info("  - %s.log: %s", domain, level_name)
    logger.info("=" * 60)


# ============================================================
# 运行时动态调整
# ============================================================

def set_domain_level(domain: str, level: str) -> None:
    """
    运行时动态修改功能域日志级别

    同时更新文件handler和控制台filter的级别。

    Args:
        domain: 功能域名称（app/manga/coding/novel/llm/image/embedding/queue/db）
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）
    """
    if domain not in ALL_DOMAINS:
        logging.getLogger(__name__).warning(f"未知的功能域: {domain}")
        return

    level_num = getattr(logging, level.upper(), logging.INFO)

    # 修改对应的文件handler级别
    if domain in _domain_handlers:
        _domain_handlers[domain].setLevel(level_num)

    # 同时更新控制台filter的域级别
    if _console_filter is not None:
        _console_filter.domain_levels[domain] = level_num

    # 如果是db域，同步更新所有sqlalchemy logger的级别
    if domain == "db":
        for sa_logger_name in ["sqlalchemy", "sqlalchemy.engine", "sqlalchemy.engine.Engine"]:
            sa_logger = logging.getLogger(sa_logger_name)
            sa_logger.setLevel(level_num)

    logging.getLogger(__name__).info(f"已将 {domain} 域日志级别调整为 {level}")


def get_domain_level(domain: str) -> str:
    """
    获取功能域当前的日志级别

    Args:
        domain: 功能域名称

    Returns:
        日志级别名称
    """
    if domain in _domain_handlers:
        return logging.getLevelName(_domain_handlers[domain].level)
    return "UNKNOWN"


# ============================================================
# 便捷函数
# ============================================================

def get_logger(name: str) -> logging.Logger:
    """
    获取logger实例（便捷函数）

    Args:
        name: 通常传入 __name__

    Returns:
        配置好的logger实例
    """
    return logging.getLogger(name)
