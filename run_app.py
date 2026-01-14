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
    _load_logging_config,
    # 工具函数
    safe_input,
    ensure_port_available,
    # 环境设置
    print_banner,
    setup_environment,
    # 进度管理
    startup_progress,
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

    logger.info("启动后端服务（子进程模式）...")

    # 使用后端虚拟环境的 Python
    python_exe = str(BACKEND_PYTHON) if BACKEND_PYTHON.exists() else sys.executable

    # 获取用户配置的日志级别（用于 uvicorn）
    user_config = _load_logging_config()
    user_levels = user_config.get('levels', {})
    uvicorn_level = user_levels.get('app', 'info').lower()

    # 启动期间总是重定向输出到文件（保证启动动画干净）
    # 后端应用的业务日志通过 Python logging 系统写入各个日志文件
    logs_dir = STORAGE_DIR / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    backend_log = logs_dir / 'backend_console.log'

    # 清空旧的控制台日志（每次启动重新记录）
    with open(backend_log, 'w', encoding='utf-8') as f:
        f.write(f"=== 后端启动日志 ===\n")

    log_file = open(backend_log, 'a', encoding='utf-8')
    backend_process = subprocess.Popen(
        [
            python_exe, '-m', 'uvicorn',
            'app.main:app',
            '--host', '127.0.0.1',
            '--port', str(BACKEND_PORT),
            '--log-level', uvicorn_level
        ],
        cwd=str(BACKEND_DIR),
        stdout=log_file,
        stderr=log_file
    )
    # 注意：log_file 不关闭，让子进程持续写入

    logger.info(f"后端进程已启动 (PID: {backend_process.pid})")


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
        log_level="debug",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_backend(timeout=60):
    """等待后端服务就绪"""
    import urllib.request
    import urllib.error
    import socket

    logger.info("等待后端服务就绪...")

    # Windows 上给后端进程一点启动时间
    time.sleep(1)

    # 创建不使用代理的 opener（避免系统代理影响 localhost 访问）
    no_proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(no_proxy_handler)

    start_time = time.time()
    url = f'http://127.0.0.1:{BACKEND_PORT}/health'

    while time.time() - start_time < timeout:
        # 检查后端进程是否还在运行（仅子进程模式）
        if backend_process is not None:
            exit_code = backend_process.poll()
            if exit_code is not None:
                # 进程已退出，说明启动失败
                logger.error(f"后端进程异常退出，退出码: {exit_code}")
                logger.error("请查看 storage/logs/backend_console.log 或控制台输出了解详情")
                return False

        try:
            response = opener.open(url, timeout=2)
            if response.status == 200:
                logger.info("后端服务已就绪")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, TimeoutError, socket.timeout, OSError) as e:
            logger.debug("健康检查等待中: %s", type(e).__name__)
            pass
        except Exception as e:
            logger.debug("健康检查遇到异常: %s - %s", type(e).__name__, e)

        time.sleep(0.5)

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


def show_backend_error_log(max_lines=30):
    """显示后端错误日志的最后几行，帮助用户调试"""
    backend_log = STORAGE_DIR / 'logs' / 'backend_console.log'
    if not backend_log.exists():
        return

    print("\n" + "=" * 60)
    print("  后端启动日志 (最后 {} 行):".format(max_lines))
    print("=" * 60)

    try:
        with open(backend_log, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            # 显示最后 max_lines 行
            for line in lines[-max_lines:]:
                print("  " + line.rstrip())
    except Exception as e:
        print(f"  [无法读取日志: {e}]")

    print("=" * 60)
    print(f"  完整日志: {backend_log}")
    print("=" * 60 + "\n")


# ============================================================
# 前端 GUI
# ============================================================

def start_frontend_subprocess():
    """以子进程方式启动前端（开发模式）"""
    python_exe = str(FRONTEND_PYTHON) if FRONTEND_PYTHON.exists() else sys.executable

    logger.info(f"启动前端应用（子进程模式），使用: {python_exe}")

    process = subprocess.Popen(
        [python_exe, 'main.py'],
        cwd=str(FRONTEND_DIR)
    )

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

    logger.info("前端应用已启动")

    # 运行应用
    return app.exec()


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    import io

    # 保存原始 stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # 创建一个空输出用于静默其他模块的 print
    null_out = io.StringIO()

    try:
        # 启动时清屏并开始循环动画
        startup_progress.clear_screen()
        startup_progress.start_loop_animation("检查运行环境")

        # 阶段0：环境检查
        sys.stdout = null_out
        sys.stderr = null_out
        env_ok = setup_environment()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        if not env_ok:
            startup_progress.stop_loop_animation()
            startup_progress.show_error("环境设置失败，请查看 storage/logs/startup.log")
            safe_input("按回车键退出...")
            sys.exit(1)

        # 阶段1：配置路径
        startup_progress.update_stage_name("配置系统路径")
        frontend_path, backend_path = setup_paths()
        logger.info(f"前端路径: {frontend_path}")
        logger.info(f"后端路径: {backend_path}")
        storage_dir = ensure_storage_dir()
        logger.info(f"存储目录: {storage_dir}")

        # 阶段2：检查端口
        startup_progress.update_stage_name("检查服务端口")
        sys.stdout = null_out
        sys.stderr = null_out
        port_ok = ensure_port_available(BACKEND_PORT)
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        if not port_ok:
            startup_progress.stop_loop_animation()
            startup_progress.show_error(f"无法释放端口 {BACKEND_PORT}，请手动关闭占用程序")
            safe_input("\n按回车键退出...")
            sys.exit(1)

        # 阶段3：启动后端
        startup_progress.update_stage_name("启动后端服务")
        if IS_FROZEN:
            backend_thread = threading.Thread(target=start_backend_thread, daemon=True)
            backend_thread.start()
        else:
            start_backend_subprocess()

        # 阶段4：等待后端就绪
        startup_progress.update_stage_name("等待服务就绪")
        if not wait_for_backend(timeout=60):
            startup_progress.stop_loop_animation()
            startup_progress.show_error("后端服务启动失败")
            show_backend_error_log()  # 直接显示日志，方便调试
            stop_backend()
            safe_input("按回车键退出...")
            sys.exit(1)

        # 全部完成 - 停止循环动画（等待当前循环完成）然后显示最终Logo
        startup_progress.stop_loop_animation()
        startup_progress.complete_all()

        # 启动前端（此时控制台只剩 Logo）
        if IS_FROZEN:
            exit_code = start_frontend()
        else:
            exit_code = start_frontend_subprocess()

        stop_backend()
        logger.info("AFN 已退出")
        sys.exit(exit_code)

    except KeyboardInterrupt:
        startup_progress.stop_loop_animation()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        print("\n\n[中断] 用户中断，正在退出...")
        stop_backend()
        sys.exit(0)

    except Exception as e:
        startup_progress.stop_loop_animation()
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        logger.exception(f"启动失败: {e}")
        startup_progress.show_error(f"启动失败: {e}")
        show_backend_error_log()  # 显示后端日志帮助调试
        stop_backend()
        safe_input("按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
