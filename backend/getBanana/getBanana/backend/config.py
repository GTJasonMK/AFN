# -*- coding: utf-8 -*-
"""
配置管理模块
负责加载、保存和管理应用程序配置
"""

import json
import os
import sys
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


def get_user_config_dir() -> str:
    """
    获取配置目录
    打包后的exe使用exe所在目录，开发环境使用项目目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后运行，使用exe所在目录
        config_dir = os.path.dirname(sys.executable)
    else:
        # 开发环境运行，使用项目目录
        config_dir = os.path.dirname(__file__)

    return config_dir


@dataclass
class AppConfig:
    """应用配置数据类"""
    api_key: str = ""
    last_model: str = "nano-banana-pro"
    last_ratio: str = "1:1"
    last_resolution: str = "原始"
    last_style: str = "无"
    last_quality: str = "标准"
    last_count: str = "2"
    temperature: float = 0.7
    seed: str = ""
    save_dir: str = ""
    prompt_history: List[str] = field(default_factory=list)

    def __post_init__(self):
        # 设置默认保存目录
        if not self.save_dir:
            self.save_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        # 限制历史记录数量
        if len(self.prompt_history) > 100:
            self.prompt_history = self.prompt_history[-100:]


class Config:
    """配置管理器"""

    # 可用模型列表（使用小写，与API一致）
    MODELS = [
        "nano-banana-pro",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-3-pro-image-preview",
    ]

    # 宽高比选项
    ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9"]

    # 宽高比对应的裁剪比例 (w:h)
    RATIO_MAP = {
        "1:1": (1, 1), "16:9": (16, 9), "9:16": (9, 16),
        "4:3": (4, 3), "3:4": (3, 4), "3:2": (3, 2),
        "2:3": (2, 3), "21:9": (21, 9)
    }

    # 分辨率选项
    RESOLUTIONS = ["原始", "1K", "2K"]

    # 生成数量选项
    COUNTS = ["1", "2", "3", "4"]

    # 风格选项 (显示名, 提示词后缀)
    STYLES = [
        ("无", ""), ("写实摄影", "写实摄影风格"), ("动漫卡通", "动漫卡通风格"),
        ("油画艺术", "油画艺术风格"), ("水彩插画", "水彩插画风格"), ("3D渲染", "3D渲染风格"),
        ("像素艺术", "像素艺术风格"), ("赛博朋克", "赛博朋克风格"), ("极简主义", "极简主义风格"),
    ]

    # 质量预设
    QUALITY_PRESETS = {
        "草稿": {"temperature": 0.9, "max_tokens": 2000},
        "标准": {"temperature": 0.7, "max_tokens": 4000},
        "高质量": {"temperature": 0.5, "max_tokens": 6000},
        "自定义": None,
    }

    # API基础URL（本地服务）
    API_BASE_URL = "http://127.0.0.1:8000"

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为用户配置目录下的config.json
        """
        if config_path is None:
            config_path = os.path.join(get_user_config_dir(), "config.json")
        self.config_path = config_path
        self.data = AppConfig()
        self.load()

    def load(self) -> None:
        """从文件加载配置"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    # 更新配置数据
                    for key, value in saved_data.items():
                        if hasattr(self.data, key):
                            setattr(self.data, key, value)
            except (json.JSONDecodeError, IOError) as e:
                print(f"加载配置文件失败: {e}")

    def save(self) -> None:
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.data), f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"保存配置文件失败: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self.data, key, default)

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        if hasattr(self.data, key):
            setattr(self.data, key, value)

    def add_prompt_to_history(self, prompt: str) -> None:
        """添加提示词到历史记录"""
        prompt = prompt.strip()
        if not prompt:
            return
        # 避免重复添加
        if self.data.prompt_history and self.data.prompt_history[-1] == prompt:
            return
        self.data.prompt_history.append(prompt)
        # 保持最多100条
        if len(self.data.prompt_history) > 100:
            self.data.prompt_history = self.data.prompt_history[-100:]

    def get_prompt_history(self) -> List[str]:
        """获取提示词历史记录"""
        return self.data.prompt_history.copy()

    def get_style_suffix(self, style_name: str) -> str:
        """根据风格名称获取提示词后缀"""
        for name, suffix in self.STYLES:
            if name == style_name:
                return suffix
        return ""

    def get_quality_preset(self, quality_name: str) -> Optional[Dict[str, Any]]:
        """获取质量预设参数"""
        return self.QUALITY_PRESETS.get(quality_name)

    def get_ratio_tuple(self, ratio_name: str) -> tuple:
        """获取宽高比元组"""
        return self.RATIO_MAP.get(ratio_name, (1, 1))
