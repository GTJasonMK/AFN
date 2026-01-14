"""
AFN (Agents for Novel) - 环境检查与配置

功能:
1. 检查 Python 版本
2. 安装 uv 包管理器（可选，加速依赖安装）
3. 创建虚拟环境
4. 安装依赖

使用方法:
  python setup_env.py          # 检查并配置环境
  python setup_env.py --force  # 强制重新安装依赖

模块结构已拆分到 backend/startup/ 包中，本文件作为兼容层重新导出所有接口。
"""

import sys
import time

# 从 backend.startup 包导入所有公共接口
from backend.startup import (
    # 配置常量
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
    # 日志
    logger,
    setup_logging,
    _load_logging_config,
    # 端口工具
    is_port_in_use,
    get_pid_using_port,
    kill_process_on_port,
    ensure_port_available,
    # UV包管理器
    check_uv_available,
    install_uv,
    ensure_uv,
    # 启动动画
    print_banner,
    StartupProgress,
    startup_progress,
    # 依赖安装
    check_python_version,
    create_venv,
    check_dependencies_installed,
    install_dependencies,
)


# ============================================================
# 工具函数
# ============================================================

def is_interactive():
    """检查是否在交互式终端运行"""
    try:
        return sys.stdin is not None and sys.stdin.isatty()
    except:
        return False


def safe_input(prompt: str = ""):
    """安全的 input 函数，在非交互模式下不会阻塞"""
    if is_interactive():
        try:
            return input(prompt)
        except EOFError:
            return ""
    else:
        # 非交互模式下等待几秒让用户看到消息
        print(prompt + " (非交互模式，3秒后退出)")
        time.sleep(3)
        return ""


# ============================================================
# 环境设置
# ============================================================

def setup_environment(force: bool = False) -> bool:
    """设置开发环境（创建虚拟环境、安装依赖）

    Args:
        force: 是否强制重新安装依赖
    """
    # 如果是打包环境，跳过环境设置
    if IS_FROZEN:
        logger.info("打包环境，跳过环境设置")
        return True

    print("\n" + "=" * 60)
    print(" 环境检查与配置")
    print("=" * 60)

    # 检查 Python 版本
    print(f"\n[检查] Python 版本...")
    if not check_python_version():
        return False
    print(f"       Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} [OK]")

    # 尝试使用uv加速（如果USE_UV=True）
    if USE_UV:
        print(f"\n[检查] 包管理器...")
        if ensure_uv():
            print(f"       uv 可用 (快速模式) [OK]")
        else:
            print(f"       将使用 pip (标准模式)")

    # 创建后端虚拟环境
    print(f"\n[检查] 后端虚拟环境...")
    if not create_venv(BACKEND_VENV, "后端"):
        return False

    # 创建前端虚拟环境
    print(f"\n[检查] 前端虚拟环境...")
    if not create_venv(FRONTEND_VENV, "前端"):
        return False

    # 安装后端依赖
    print(f"\n[检查] 后端依赖...")
    backend_requirements = BACKEND_DIR / 'requirements.txt'
    if not install_dependencies(BACKEND_PYTHON, backend_requirements, "后端", force):
        return False

    # 安装前端依赖
    print(f"\n[检查] 前端依赖...")
    frontend_requirements = FRONTEND_DIR / 'requirements.txt'
    if not install_dependencies(FRONTEND_PYTHON, frontend_requirements, "前端", force):
        return False

    print("\n" + "=" * 60)
    print(" 环境检查完成")
    print("=" * 60)
    return True


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数 - 仅环境检查"""
    try:
        # 打印启动横幅
        print_banner()

        # 检查命令行参数
        force = '--force' in sys.argv or '-f' in sys.argv
        if force:
            print("[模式] 强制重新安装依赖")

        # 设置环境
        if not setup_environment(force=force):
            print("\n[错误] 环境设置失败，请查看 storage/logs/startup.log")
            safe_input("按回车键退出...")
            sys.exit(1)

        print("\n[完成] 环境配置成功！")
        print("       运行 python run_app.py 启动应用")

    except KeyboardInterrupt:
        print("\n\n[中断] 用户中断")
        sys.exit(0)

    except Exception as e:
        logger.exception(f"环境设置失败: {e}")
        print(f"\n[错误] 环境设置失败: {e}")
        print("       请查看 storage/logs/startup.log 获取详细信息")
        safe_input("\n按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
