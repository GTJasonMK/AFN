"""
settings 路由共享工具

用途：
- 负责 `storage/config.json` 的定位与读写（兼容开发环境与打包环境）。
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger(__name__)


def get_config_file() -> Path:
    """获取配置文件路径（适配打包环境）"""
    if getattr(sys, "frozen", False):
        # 打包环境：配置保存到 exe 所在目录的 storage 文件夹
        work_dir = Path(sys.executable).parent
    else:
        # 开发环境：配置保存到项目根目录的 storage 文件夹
        # 从 backend/app/api/routers/settings_utils.py 向上4级到达项目根目录
        work_dir = Path(__file__).resolve().parents[4]

    storage_dir = work_dir / "storage"
    storage_dir.mkdir(exist_ok=True)
    return storage_dir / "config.json"


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_file = get_config_file()
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("读取配置文件失败：%s", str(e))
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """保存配置文件"""
    config_file = get_config_file()
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def persist_config_updates(updates: Mapping[str, Any]) -> Dict[str, Any]:
    """
    读取并更新配置文件，然后写回磁盘。

    Args:
        updates: 需要写入 config.json 的键值对（与存储 key 保持一致）

    Returns:
        合并后的完整配置字典
    """
    current_config = load_config()
    current_config.update(dict(updates))
    save_config(current_config)
    return current_config


def try_apply_runtime_settings(
    settings_obj: Any,
    updates: Mapping[str, Any],
    *,
    key_map: Optional[Mapping[str, str]] = None,
    warn_logger: Optional[logging.Logger] = None,
) -> bool:
    """
    尝试将更新同步到运行时 settings（hot reload）。

    注意：
    - 默认按同名字段 setattr；
    - 如存在 key_map，则按 key_map 做字段映射（用于 config key 与 settings 字段不一致的场景）。
    """
    try:
        effective_map = dict(key_map or {})
        for key, value in updates.items():
            setattr(settings_obj, effective_map.get(key, key), value)
        return True
    except Exception as reload_error:
        (warn_logger or logger).warning("运行时配置更新失败: %s", str(reload_error), exc_info=True)
        return False


def build_hot_reload_response(updated_config: Dict[str, Any], hot_reload_success: bool) -> Dict[str, Any]:
    """构建统一的配置更新响应结构。"""
    return {
        "success": True,
        "message": "配置已保存并立即生效" if hot_reload_success else "配置已保存，重启应用后生效",
        "hot_reload": hot_reload_success,
        "updated_config": updated_config,
    }

__all__ = [
    "get_config_file",
    "load_config",
    "save_config",
    "persist_config_updates",
    "try_apply_runtime_settings",
    "build_hot_reload_response",
]
