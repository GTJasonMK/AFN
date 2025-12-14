# -*- coding: utf-8 -*-
"""
日志记录模块
记录每次生成的参数、prompt和结果
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


def get_log_dir() -> str:
    """
    获取日志目录
    打包后的exe使用exe所在目录，开发环境使用项目目录
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(__file__))


@dataclass
class GenerationLog:
    """生成日志数据类"""
    timestamp: str
    # 输入参数
    model: str
    style: str
    ratio: str
    resolution: str
    count: int
    quality: str
    temperature: float
    seed: str
    # 提示词
    prompt: str
    negative_prompt: str
    full_prompt: str
    # 结果
    success: bool
    error_message: str = ""
    image_paths: List[str] = None
    duration_seconds: float = 0.0
    save_dir: str = ""

    def __post_init__(self):
        if self.image_paths is None:
            self.image_paths = []


class Logger:
    """日志管理器"""

    def __init__(self, log_file: Optional[str] = None):
        """
        初始化日志管理器

        Args:
            log_file: 日志文件路径，默认为logs/generation.log
        """
        if log_file is None:
            log_dir = os.path.join(get_log_dir(), "logs")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "generation.log")
        self.log_file = log_file

    def log_generation(
        self,
        model: str,
        style: str,
        ratio: str,
        resolution: str,
        count: int,
        quality: str,
        temperature: float,
        seed: str,
        prompt: str,
        negative_prompt: str,
        full_prompt: str,
        success: bool,
        error_message: str = "",
        image_paths: List[str] = None,
        duration_seconds: float = 0.0,
        save_dir: str = ""
    ) -> None:
        """
        记录一次生成日志

        Args:
            model: 使用的模型
            style: 风格
            ratio: 宽高比
            resolution: 分辨率
            count: 生成数量
            quality: 质量预设
            temperature: 温度参数
            seed: 随机种子
            prompt: 用户输入的提示词
            negative_prompt: 负面提示词
            full_prompt: 完整提示词（包含风格后缀）
            success: 是否成功
            error_message: 错误信息
            image_paths: 生成的图片路径列表
            duration_seconds: 耗时（秒）
            save_dir: 保存目录
        """
        log_entry = GenerationLog(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            model=model,
            style=style,
            ratio=ratio,
            resolution=resolution,
            count=count,
            quality=quality,
            temperature=temperature,
            seed=seed,
            prompt=prompt,
            negative_prompt=negative_prompt,
            full_prompt=full_prompt,
            success=success,
            error_message=error_message,
            image_paths=image_paths or [],
            duration_seconds=round(duration_seconds, 2),
            save_dir=save_dir
        )

        self._write_log(log_entry)

    def _write_log(self, log_entry: GenerationLog) -> None:
        """将日志写入文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            # 追加写入，每行一条JSON记录
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(asdict(log_entry), f, ensure_ascii=False)
                f.write('\n')
        except IOError as e:
            print(f"写入日志失败: {e}")

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取最近的日志记录

        Args:
            limit: 最大返回条数

        Returns:
            日志记录列表（最新的在前）
        """
        logs = []
        if not os.path.exists(self.log_file):
            return logs

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except IOError:
            pass

        # 返回最新的记录
        return logs[-limit:][::-1]

    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return self.log_file

    def clear_logs(self) -> bool:
        """清空日志文件"""
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
            return True
        except IOError:
            return False
