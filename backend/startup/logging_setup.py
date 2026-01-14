"""
日志配置模块

包含:
- _load_logging_config() - 加载用户日志配置
- setup_logging() - 配置日志系统
- logger - 全局日志实例
"""

import sys
import os
import logging

from .config import STORAGE_DIR


def _load_logging_config() -> dict:
    """加载用户日志配置"""
    config_path = STORAGE_DIR / 'logging_config.yaml'
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def setup_logging():
    """配置日志系统（遵循用户配置）"""
    # 确保日志目录存在
    logs_dir = STORAGE_DIR / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / 'startup.log'

    # 读取用户配置的日志级别
    user_config = _load_logging_config()
    user_levels = user_config.get('levels', {})
    # 启动器使用 app 域的级别，默认 INFO
    level_str = user_levels.get('app', 'INFO').upper()
    log_level = getattr(logging, level_str, logging.INFO)

    handlers = []

    # 检测是否有控制台
    has_console = sys.stdout is not None and hasattr(sys.stdout, 'write')

    if has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)  # 使用用户配置的级别
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        handlers.append(console_handler)

    # 文件日志
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setLevel(log_level)  # 使用用户配置的级别
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    handlers.append(file_handler)

    logging.basicConfig(level=log_level, handlers=handlers)

    # 无控制台时重定向 stdout/stderr
    if not has_console:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    return logging.getLogger('AFN')


# 全局日志实例
logger = setup_logging()
