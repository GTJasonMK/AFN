"""
AFN 启动模块

将启动相关的功能拆分为多个子模块:
- config: 路径常量、颜色定义
- logging_setup: 日志配置
- port_utils: 端口工具函数
- uv_manager: UV包管理器
- animation: 启动动画
- installer: 依赖安装
"""

# 配置常量
from .config import (
    BASE_DIR,
    IS_FROZEN,
    BACKEND_DIR,
    FRONTEND_DIR,
    BACKEND_VENV,
    FRONTEND_VENV,
    BACKEND_PYTHON,
    FRONTEND_PYTHON,
    USE_UV,
)

# 日志
from .logging_setup import (
    logger,
)

# UV包管理器
from .uv_manager import (
    ensure_uv,
)

# 启动动画
from .animation import (
    print_banner,
)

# 依赖安装
from .installer import (
    check_python_version,
    create_venv,
    install_dependencies,
)

__all__ = [
    # config
    'BASE_DIR',
    'IS_FROZEN',
    'BACKEND_DIR',
    'FRONTEND_DIR',
    'BACKEND_VENV',
    'FRONTEND_VENV',
    'BACKEND_PYTHON',
    'FRONTEND_PYTHON',
    'USE_UV',
    # logging
    'logger',
    # uv_manager
    'ensure_uv',
    # animation
    'print_banner',
    # installer
    'check_python_version',
    'create_venv',
    'install_dependencies',
]
