"""
UV包管理器模块

包含:
- check_uv_available() - 检查uv是否可用
- install_uv() - 安装uv
- ensure_uv() - 确保uv可用
"""

import sys
import subprocess

from .config import USE_UV
from .logging_setup import logger

# 全局变量：是否uv可用（缓存检查结果）
_uv_available = None


def check_uv_available() -> bool:
    """检查uv是否可用"""
    global _uv_available
    if _uv_available is not None:
        return _uv_available

    try:
        result = subprocess.run(
            ['uv', '--version'],
            capture_output=True,
            text=True,
            errors='replace'
        )
        if result.returncode == 0:
            _uv_available = True
            return True
    except FileNotFoundError:
        pass

    _uv_available = False
    return False


def install_uv() -> bool:
    """安装uv"""
    print("\n[安装] 正在安装 uv 包管理器...")
    print("       uv 比 pip 快 10-100 倍，可以大幅加速依赖安装")

    try:
        # 使用pip安装uv
        process = subprocess.Popen(
            [sys.executable, '-m', 'pip', 'install', 'uv', '-q'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace'
        )
        process.wait()

        if process.returncode == 0:
            global _uv_available
            _uv_available = True
            print("       uv 安装成功 [OK]")
            return True
        else:
            print("       uv 安装失败，将使用 pip 作为回退")
            return False
    except Exception as e:
        print(f"       uv 安装失败: {e}")
        return False


def ensure_uv() -> bool:
    """确保uv可用，如果不可用则尝试安装"""
    if not USE_UV:
        return False

    if check_uv_available():
        return True

    return install_uv()
