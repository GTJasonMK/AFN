"""
启动配置 - 路径常量和颜色定义

包含:
- Windows ANSI颜色支持
- Colors类（ANSI颜色代码）
- 路径常量（BASE_DIR, BACKEND_DIR等）
- 运行时配置（IS_FROZEN, WORK_DIR等）
"""

import sys
import ctypes
from pathlib import Path


# ============================================================
# Windows ANSI 颜色支持
# ============================================================

def _enable_windows_ansi():
    """启用 Windows 控制台的 ANSI 颜色支持"""
    if sys.platform != 'win32':
        return True
    try:
        kernel32 = ctypes.windll.kernel32
        # 获取标准输出句柄
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        # 获取当前控制台模式
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        # 启用 ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        return True
    except Exception:
        return False


# 启用 ANSI 支持
_enable_windows_ansi()


# ============================================================
# ANSI 颜色代码
# ============================================================

class Colors:
    """ANSI 颜色代码"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # 前景色
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # 亮色
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


# ============================================================
# 基础配置
# ============================================================

# 后端服务端口
BACKEND_PORT = 8123

# 是否使用uv加速（uv比pip快10-100倍）
USE_UV = True

# 全局变量：是否uv可用
_uv_available = None

# 判断运行环境
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的运行环境
    BASE_DIR = Path(sys._MEIPASS)
    WORK_DIR = Path(sys.executable).parent
    IS_FROZEN = True
else:
    # 开发环境 - 需要找到项目根目录
    # config.py 位于 backend/startup/ 目录下，所以需要向上两级
    BASE_DIR = Path(__file__).parent.parent.parent
    WORK_DIR = BASE_DIR
    IS_FROZEN = False

# 路径配置
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'
STORAGE_DIR = WORK_DIR / 'storage'

# 虚拟环境路径
BACKEND_VENV = BACKEND_DIR / '.venv'
FRONTEND_VENV = FRONTEND_DIR / '.venv'

# Python 可执行文件路径
if sys.platform == 'win32':
    BACKEND_PYTHON = BACKEND_VENV / 'Scripts' / 'python.exe'
    FRONTEND_PYTHON = FRONTEND_VENV / 'Scripts' / 'python.exe'
else:
    BACKEND_PYTHON = BACKEND_VENV / 'bin' / 'python'
    FRONTEND_PYTHON = FRONTEND_VENV / 'bin' / 'python'
