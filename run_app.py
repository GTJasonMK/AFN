"""
AFN (Agents for Novel) - 应用启动入口

功能:
1. 调用环境检查（自动创建虚拟环境、安装依赖）
2. 启动后端服务
3. 启动前端GUI

使用方法:
  开发环境: python run_app.py
  打包后:   双击 AFN.exe

环境检查: python setup_env.py
"""

import sys
import os
import time
import subprocess
import threading
import shutil
from pathlib import Path

# 导入环境检查模块
from setup_env import (
    # 配置
    BACKEND_PORT,
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
    # 日志
    logger,
    # 工具函数
    safe_input,
    ensure_port_available,
    # 环境设置
    print_banner,
    setup_environment,
)


# ============================================================
# 环境变量和路径设置
# ============================================================

def setup_paths():
    """设置 Python 路径"""
    if IS_FROZEN:
        frontend_path = BASE_DIR / 'frontend'
        backend_path = BASE_DIR / 'backend'
    else:
        frontend_path = FRONTEND_DIR
        backend_path = BACKEND_DIR

    # 添加到 Python 路径
    for path in [frontend_path, backend_path]:
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)

    return frontend_path, backend_path


def ensure_storage_dir():
    """确保存储目录存在并设置环境变量"""
    STORAGE_DIR.mkdir(exist_ok=True)

    # 同时创建后端的 storage 目录（用于日志等）
    backend_storage = BACKEND_DIR / 'storage'
    backend_storage.mkdir(exist_ok=True)

    # 创建模型下载目录并设置环境变量
    # HuggingFace 和 sentence-transformers 模型将下载到此目录
    models_dir = STORAGE_DIR / 'models'
    models_dir.mkdir(exist_ok=True)
    os.environ['HF_HOME'] = str(models_dir)
    os.environ['SENTENCE_TRANSFORMERS_HOME'] = str(models_dir)

    # 设置数据库路径
    db_path = STORAGE_DIR / 'afn.db'
    os.environ['DATABASE_URL'] = f"sqlite+aiosqlite:///{db_path}"
    # 设置向量库路径（使用 file: 前缀表示本地文件）
    vector_db_path = STORAGE_DIR / 'vectors.db'
    os.environ['VECTOR_DB_URL'] = f"file:{vector_db_path}"

    # 设置安全密钥（桌面版使用固定密钥）
    os.environ['SECRET_KEY'] = 'afn-desktop-secret-key-2024'

    # 设置提示词目录
    if IS_FROZEN:
        prompts_dir = BASE_DIR / 'prompts'
    else:
        prompts_dir = BACKEND_DIR / 'prompts'
    os.environ['PROMPTS_DIR'] = str(prompts_dir)

    # 复制 .env 文件（如果不存在）
    env_file = BACKEND_DIR / '.env'
    env_example = BACKEND_DIR / '.env.example'
    if not env_file.exists() and env_example.exists():
        shutil.copy(env_example, env_file)
        logger.info("已创建 .env 配置文件")

    return STORAGE_DIR


# ============================================================
# 后端服务
# ============================================================

backend_process = None


def start_backend_subprocess():
    """以子进程方式启动后端（开发模式）"""
    global backend_process

    print(f"\n[启动] 启动后端服务...")
    print(f"       端口: {BACKEND_PORT}")
    logger.info("启动后端服务（子进程模式）...")

    # 使用后端虚拟环境的 Python
    python_exe = str(BACKEND_PYTHON) if BACKEND_PYTHON.exists() else sys.executable
    print(f"       Python: {python_exe}")

    # 启动 uvicorn - 输出直接显示到当前控制台
    backend_process = subprocess.Popen(
        [
            python_exe, '-m', 'uvicorn',
            'app.main:app',
            '--host', '127.0.0.1',
            '--port', str(BACKEND_PORT),
            '--log-level', 'info'
        ],
        cwd=str(BACKEND_DIR)
    )

    logger.info(f"后端进程已启动 (PID: {backend_process.pid})")
    print(f"       进程ID: {backend_process.pid}")


def start_backend_thread():
    """在线程中启动后端服务（打包模式）"""
    import uvicorn

    # 导入后端应用
    from app.main import app

    logger.info("启动后端服务（线程模式）...")

    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=BACKEND_PORT,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_backend(timeout=60):
    """等待后端服务就绪"""
    import urllib.request
    import urllib.error

    print(f"\n[等待] 等待后端服务就绪...")
    print(f"       健康检查地址: http://127.0.0.1:{BACKEND_PORT}/health")
    logger.info("等待后端服务就绪...")

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(f'http://127.0.0.1:{BACKEND_PORT}/health', timeout=2)
            if response.status == 200:
                elapsed = time.time() - start_time
                print(f"\n       后端服务已就绪 (耗时 {elapsed:.1f}s) [OK]")
                logger.info("后端服务已就绪")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, TimeoutError):
            pass

        # 显示进度
        elapsed = int(time.time() - start_time)
        print(f"\r       正在检查服务状态... ({elapsed}s)", end='', flush=True)
        time.sleep(0.5)

    print(f"\n[错误] 后端服务启动超时 (超过 {timeout}s)")
    logger.error("等待后端服务超时")
    return False


def stop_backend():
    """停止后端服务"""
    global backend_process

    if backend_process:
        logger.info("停止后端服务...")
        try:
            backend_process.terminate()
            backend_process.wait(timeout=5)
        except:
            backend_process.kill()
        backend_process = None


# ============================================================
# 前端 GUI
# ============================================================

def start_frontend_subprocess():
    """以子进程方式启动前端（开发模式）"""
    python_exe = str(FRONTEND_PYTHON) if FRONTEND_PYTHON.exists() else sys.executable

    print(f"\n[启动] 启动前端应用...")
    print(f"       Python: {python_exe}")
    logger.info(f"启动前端应用（子进程模式），使用: {python_exe}")

    process = subprocess.Popen(
        [python_exe, 'main.py'],
        cwd=str(FRONTEND_DIR)
    )

    print(f"       进程ID: {process.pid}")
    print("\n" + "=" * 60)
    print(" AFN 已启动，祝您创作愉快！")
    print("=" * 60 + "\n")
    logger.info(f"前端进程已启动 (PID: {process.pid})")

    return process.wait()


def start_frontend():
    """启动前端 GUI"""
    # 添加前端路径到 sys.path
    frontend_path = str(FRONTEND_DIR)
    if frontend_path not in sys.path:
        sys.path.insert(0, frontend_path)

    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    # 导入前端模块
    from windows.main_window import MainWindow
    from themes.theme_manager import theme_manager
    from themes.accessibility import AccessibilityTheme
    from utils.config_manager import ConfigManager

    print("\n[启动] 启动前端应用...")
    logger.info("启动前端应用...")

    # 启用高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("AFN")
    app.setOrganizationName("AFN")

    # 初始化配置管理器
    config_manager = ConfigManager()

    # 设置主题管理器
    theme_manager.set_config_manager(config_manager)
    theme_manager.load_theme_from_config()

    # 应用全局样式
    def apply_global_theme():
        dialog_bg = theme_manager.BG_CARD
        dialog_text = theme_manager.TEXT_PRIMARY
        input_bg = theme_manager.BG_PRIMARY
        input_border = theme_manager.BORDER_DEFAULT

        base_style = f"""
            QMessageBox {{
                background-color: {dialog_bg};
                color: {dialog_text};
            }}
            QMessageBox QLabel {{
                color: {dialog_text};
                font-size: 14px;
                background-color: transparent;
            }}
            QMessageBox QPushButton,
            QDialogButtonBox QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: 8px 20px;
                font-size: 14px;
                font-weight: 500;
                min-width: 70px;
            }}
            QMessageBox QPushButton:hover,
            QDialogButtonBox QPushButton:hover {{
                background-color: {theme_manager.PRIMARY_LIGHT};
            }}
            QInputDialog {{
                background-color: {dialog_bg};
                color: {dialog_text};
            }}
            QInputDialog QLabel {{
                color: {dialog_text};
                font-size: 14px;
                background-color: transparent;
            }}
            QInputDialog QLineEdit {{
                color: {dialog_text};
                background-color: {input_bg};
                border: 1px solid {input_border};
                border-radius: {theme_manager.RADIUS_SM};
                padding: 8px;
            }}
            QInputDialog QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: {theme_manager.BUTTON_TEXT};
                border: none;
                border-radius: {theme_manager.RADIUS_SM};
                padding: 8px 20px;
                font-size: 14px;
                min-width: 70px;
            }}
        """

        accessibility_style = AccessibilityTheme.get_all_accessibility_styles()
        app.setStyleSheet(base_style + "\n" + accessibility_style)

    theme_manager.theme_changed.connect(apply_global_theme)
    apply_global_theme()

    # 创建主窗口
    window = MainWindow()
    window.show()

    print("\n" + "=" * 60)
    print(" AFN 已启动，祝您创作愉快！")
    print("=" * 60 + "\n")
    logger.info("前端应用已启动")

    # 运行应用
    return app.exec()


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    try:
        # 打印启动横幅
        print_banner()

        # 设置环境（创建虚拟环境、安装依赖）
        if not setup_environment():
            print("\n[错误] 环境设置失败，请查看 storage/app.log")
            safe_input("按回车键退出...")
            sys.exit(1)

        # 设置路径
        frontend_path, backend_path = setup_paths()
        logger.info(f"前端路径: {frontend_path}")
        logger.info(f"后端路径: {backend_path}")

        # 确保存储目录存在
        storage_dir = ensure_storage_dir()
        logger.info(f"存储目录: {storage_dir}")

        # 检查并释放端口
        if not ensure_port_available(BACKEND_PORT):
            print(f"\n[错误] 无法释放端口 {BACKEND_PORT}")
            print("       请手动关闭占用端口的程序后重试")
            safe_input("\n按回车键退出...")
            sys.exit(1)

        # 启动后端服务
        if IS_FROZEN:
            # 打包模式：在线程中运行后端
            backend_thread = threading.Thread(target=start_backend_thread, daemon=True)
            backend_thread.start()
        else:
            # 开发模式：以子进程运行后端
            start_backend_subprocess()

        # 等待后端就绪
        if not wait_for_backend(timeout=60):
            print("\n[错误] 后端服务启动失败")
            print("       可能原因：")
            print("       1. 依赖安装不完整")
            print("       2. 配置文件错误")
            print("       3. 数据库损坏")
            print("\n       请查看 storage/app.log 获取详细信息")
            stop_backend()
            safe_input("\n按回车键退出...")
            sys.exit(1)

        # 启动前端
        if IS_FROZEN:
            # 打包模式：在当前进程中运行前端（PyQt6已打包）
            exit_code = start_frontend()
        else:
            # 开发模式：以子进程运行前端（使用前端venv的Python）
            exit_code = start_frontend_subprocess()

        # 清理
        stop_backend()
        logger.info("AFN 已退出")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print("\n\n[中断] 用户中断，正在退出...")
        stop_backend()
        sys.exit(0)

    except Exception as e:
        logger.exception(f"启动失败: {e}")
        print(f"\n[错误] 启动失败: {e}")
        print("       请查看 storage/app.log 获取详细信息")
        stop_backend()
        safe_input("\n按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
