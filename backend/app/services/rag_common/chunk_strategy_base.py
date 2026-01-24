"""
分块策略通用管理器

用于抽取 coding/novel 的分块策略管理器重复逻辑。
"""

import copy
from dataclasses import fields
from enum import Enum
from typing import Any, Dict, Generic, Type, TypeVar


ConfigT = TypeVar("ConfigT")
DataTypeT = TypeVar("DataTypeT", bound=Enum)
MethodT = TypeVar("MethodT", bound=Enum)


def clone_chunk_config(config: ConfigT) -> ConfigT:
    """深拷贝分块配置，避免 preset 共享引用。"""
    return copy.deepcopy(config)


def serialize_chunk_config(config: ConfigT) -> Dict[str, Any]:
    """将分块配置序列化为字典，Enum 转为 value。"""
    result: Dict[str, Any] = {}
    for config_field in fields(config):
        value = getattr(config, config_field.name)
        if isinstance(value, Enum):
            result[config_field.name] = value.value
        else:
            result[config_field.name] = copy.deepcopy(value)
    return result


def build_chunk_config(
    config_cls: Type[ConfigT],
    method_enum: Type[MethodT],
    data: Dict[str, Any],
) -> ConfigT:
    """从字典构建分块配置，缺失字段使用 dataclass 默认值。"""
    default_config = config_cls()
    kwargs: Dict[str, Any] = {}
    for config_field in fields(default_config):
        if config_field.name == "method":
            method_value = data.get("method", default_config.method.value)
            kwargs[config_field.name] = method_enum(method_value)
            continue

        if config_field.name in data:
            kwargs[config_field.name] = data[config_field.name]
        else:
            kwargs[config_field.name] = copy.deepcopy(getattr(default_config, config_field.name))
    return config_cls(**kwargs)


class BaseChunkStrategyManager(Generic[DataTypeT, ConfigT, MethodT]):
    """
    通用分块策略管理器

    子类需提供 PRESETS / DATA_TYPE_ENUM / CONFIG_CLASS / METHOD_ENUM。
    """

    PRESETS: Dict[str, Dict[DataTypeT, ConfigT]] = {}
    DATA_TYPE_ENUM: Type[DataTypeT]
    CONFIG_CLASS: Type[ConfigT]
    METHOD_ENUM: Type[MethodT]

    def __init__(self, preset: str = "default"):
        """
        初始化策略管理器

        Args:
            preset: 预设策略名称，可选 "default" 或 "optimized"
        """
        self._preset_name = preset
        self._strategies: Dict[DataTypeT, ConfigT] = {}
        self._load_preset(preset)

    def _load_preset(self, preset: str):
        """加载预设策略"""
        if preset not in self.PRESETS:
            raise ValueError(f"未知的预设策略: {preset}，可选: {list(self.PRESETS.keys())}")

        for data_type, config in self.PRESETS[preset].items():
            self._strategies[data_type] = clone_chunk_config(config)

    def get_config(self, data_type: DataTypeT) -> ConfigT:
        """
        获取指定数据类型的分块配置

        Args:
            data_type: 数据类型

        Returns:
            分块配置
        """
        if data_type not in self._strategies:
            return self.CONFIG_CLASS()
        return self._strategies[data_type]

    def set_config(self, data_type: DataTypeT, config: ConfigT):
        """
        设置指定数据类型的分块配置

        Args:
            data_type: 数据类型
            config: 分块配置
        """
        self._strategies[data_type] = config

    def set_method(self, data_type: DataTypeT, method: MethodT):
        """
        快捷设置分块方法

        Args:
            data_type: 数据类型
            method: 分块方法
        """
        if data_type in self._strategies:
            self._strategies[data_type].method = method
        else:
            self._strategies[data_type] = self.CONFIG_CLASS(method=method)

    def switch_preset(self, preset: str):
        """
        切换预设策略

        Args:
            preset: 预设策略名称
        """
        self._load_preset(preset)
        self._preset_name = preset

    def get_current_preset(self) -> str:
        """获取当前预设名称"""
        return self._preset_name

    def get_all_configs(self) -> Dict[DataTypeT, ConfigT]:
        """获取所有数据类型的配置"""
        return dict(self._strategies)

    def to_dict(self) -> Dict[str, Any]:
        """
        导出配置为字典格式（用于序列化）

        Returns:
            配置字典
        """
        result: Dict[str, Any] = {
            "preset": self._preset_name,
            "strategies": {},
        }
        for data_type, config in self._strategies.items():
            result["strategies"][data_type.value] = serialize_chunk_config(config)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseChunkStrategyManager[DataTypeT, ConfigT, MethodT]":
        """
        从字典创建策略管理器

        Args:
            data: 配置字典

        Returns:
            策略管理器实例
        """
        preset = data.get("preset", "optimized")
        manager = cls(preset=preset)

        strategies = data.get("strategies", {})
        for type_str, config_dict in strategies.items():
            try:
                data_type = cls.DATA_TYPE_ENUM(type_str)
                config = build_chunk_config(cls.CONFIG_CLASS, cls.METHOD_ENUM, config_dict)
                manager.set_config(data_type, config)
            except (ValueError, KeyError):
                pass

        return manager


__all__ = [
    "BaseChunkStrategyManager",
    "build_chunk_config",
    "clone_chunk_config",
    "serialize_chunk_config",
]
