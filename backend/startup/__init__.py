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
    Colors,
    BASE_DIR,
    WORK_DIR,
    IS_FROZEN,
    BACKEND_DIR,
    FRONTEND_DIR,
    STORAGE_DIR,
    BACKEND_VENV,
    FRONTEND_VENV,
    BACKEND_PYTHON,
    FRONTEND_PYTHON,
    BACKEND_PORT,
    USE_UV,
)

# 日志
from .logging_setup import (
    logger,
    setup_logging,
    _load_logging_config,
)

# 端口工具
from .port_utils import (
    is_port_in_use,
    get_pid_using_port,
    kill_process_on_port,
    ensure_port_available,
)

# UV包管理器
from .uv_manager import (
    check_uv_available,
    install_uv,
    ensure_uv,
)

# 启动动画
from .animation import (
    print_banner,
    StartupProgress,
    startup_progress,
)

# 依赖安装
from .installer import (
    check_python_version,
    create_venv,
    check_dependencies_installed,
    install_dependencies,
)

__all__ = [
    # config
    'Colors',
    'BASE_DIR',
    'WORK_DIR',
    'IS_FROZEN',
    'BACKEND_DIR',
    'FRONTEND_DIR',
    'STORAGE_DIR',
    'BACKEND_VENV',
    'FRONTEND_VENV',
    'BACKEND_PYTHON',
    'FRONTEND_PYTHON',
    'BACKEND_PORT',
    'USE_UV',
    # logging
    'logger',
    'setup_logging',
    '_load_logging_config',
    # port_utils
    'is_port_in_use',
    'get_pid_using_port',
    'kill_process_on_port',
    'ensure_port_available',
    # uv_manager
    'check_uv_available',
    'install_uv',
    'ensure_uv',
    # animation
    'print_banner',
    'StartupProgress',
    'startup_progress',
    # installer
    'check_python_version',
    'create_venv',
    'check_dependencies_installed',
    'install_dependencies',
]
