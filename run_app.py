"""
AFN (Agents for Novel) - 统一启动入口

功能:
1. 自动创建虚拟环境（如不存在）
2. 自动安装依赖（如未安装）
3. 启动后端服务和前端GUI
4. 支持开发环境和打包后的exe环境

使用方法:
  开发环境: python run_app.py
  打包后:   双击 AFN.exe
"""

import sys
import os
import time
import logging
import subprocess
import threading
import shutil
import socket
from pathlib import Path

# ============================================================
# 基础配置
# ============================================================

# 后端服务端口
BACKEND_PORT = 8123


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except socket.error:
            return True


def get_pid_using_port(port: int) -> int | None:
    """获取占用指定端口的进程PID（Windows专用）"""
    if sys.platform != 'win32':
        return None

    try:
        # 使用 netstat 查找占用端口的进程
        result = subprocess.run(
            ['netstat', '-ano', '-p', 'TCP'],
            capture_output=True,
            text=True,
            errors='replace'
        )

        for line in result.stdout.split('\n'):
            # 查找监听在指定端口的行
            if f'127.0.0.1:{port}' in line or f'0.0.0.0:{port}' in line:
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[-1])
                        return pid
                    except ValueError:
                        continue
        return None
    except Exception:
        return None


def kill_process_on_port(port: int) -> bool:
    """关闭占用指定端口的进程"""
    pid = get_pid_using_port(port)
    if pid is None:
        return False

    try:
        # 使用 taskkill 强制结束进程
        result = subprocess.run(
            ['taskkill', '/F', '/PID', str(pid)],
            capture_output=True,
            text=True,
            errors='replace'
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_port_available(port: int) -> bool:
    """确保端口可用，如果被占用则尝试关闭占用进程"""
    if not is_port_in_use(port):
        return True

    print(f"\n[检测] 端口 {port} 被占用，尝试关闭占用进程...")

    pid = get_pid_using_port(port)
    if pid:
        print(f"       发现占用进程 PID: {pid}")

        if kill_process_on_port(port):
            print(f"       已关闭进程 {pid}")
            # 等待端口释放
            time.sleep(1)

            if not is_port_in_use(port):
                print(f"       端口 {port} 已释放")
                return True
            else:
                print(f"[警告] 端口 {port} 仍被占用")
                return False
        else:
            print(f"[错误] 无法关闭进程 {pid}")
            return False
    else:
        print(f"[错误] 无法确定占用端口的进程")
        return False


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


# 判断运行环境
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的运行环境
    BASE_DIR = Path(sys._MEIPASS)
    WORK_DIR = Path(sys.executable).parent
    IS_FROZEN = True
else:
    # 开发环境
    BASE_DIR = Path(__file__).parent
    WORK_DIR = BASE_DIR
    IS_FROZEN = False

# 路径配置
BACKEND_DIR = BASE_DIR / 'backend'
FRONTEND_DIR = BASE_DIR / 'frontend'
STORAGE_DIR = WORK_DIR / 'storage'

# 虚拟环境路径
BACKEND_VENV = BACKEND_DIR / '.venv'
FRONTEND_VENV = FRONTEND_DIR / '.venv'

# Windows 下的 Python 可执行文件路径
if sys.platform == 'win32':
    BACKEND_PYTHON = BACKEND_VENV / 'Scripts' / 'python.exe'
    FRONTEND_PYTHON = FRONTEND_VENV / 'Scripts' / 'python.exe'
else:
    BACKEND_PYTHON = BACKEND_VENV / 'bin' / 'python'
    FRONTEND_PYTHON = FRONTEND_VENV / 'bin' / 'python'


# ============================================================
# 日志配置
# ============================================================

def setup_logging():
    """配置日志系统"""
    # 确保存储目录存在
    STORAGE_DIR.mkdir(exist_ok=True)
    log_file = STORAGE_DIR / 'app.log'

    handlers = []

    # 检测是否有控制台
    has_console = sys.stdout is not None and hasattr(sys.stdout, 'write')

    if has_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        ))
        handlers.append(console_handler)

    # 文件日志
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    handlers.append(file_handler)

    logging.basicConfig(level=logging.INFO, handlers=handlers)

    # 无控制台时重定向 stdout/stderr
    if not has_console:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

    return logging.getLogger('AFN')


logger = setup_logging()


# ============================================================
# 环境检查和安装
# ============================================================

def print_banner():
    """打印启动横幅"""
    banner = """
============================================================
     _    _____ _   _
    / \\  |  ___| \\ | |  Agents for Novel
   / _ \\ | |_  |  \\| |  AI 辅助长篇小说创作工具
  / ___ \\|  _| | |\\  |
 /_/   \\_\\_|   |_| \\_|  v1.0.0

============================================================
"""
    print(banner)
    logger.info("AFN (Agents for Novel) 启动中...")


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        logger.error(f"Python 版本过低: {version.major}.{version.minor}")
        logger.error("AFN 需要 Python 3.10 或更高版本")
        print("\n[错误] Python 版本过低，需要 3.10+")
        print(f"       当前版本: {version.major}.{version.minor}.{version.micro}")
        return False
    logger.info(f"Python 版本: {version.major}.{version.minor}.{version.micro}")
    return True


def create_venv(venv_path: Path, name: str) -> bool:
    """创建虚拟环境"""
    if venv_path.exists():
        logger.info(f"{name} 虚拟环境已存在")
        return True

    logger.info(f"创建 {name} 虚拟环境...")
    print(f"\n[安装] 创建 {name} 虚拟环境...")

    try:
        subprocess.run(
            [sys.executable, '-m', 'venv', str(venv_path)],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"{name} 虚拟环境创建成功")
        print(f"       {name} 虚拟环境创建成功")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"创建 {name} 虚拟环境失败: {e.stderr}")
        print(f"[错误] 创建 {name} 虚拟环境失败")
        return False


def check_dependencies_installed(python_path: Path, requirements_file: Path) -> bool:
    """检查依赖是否已安装

    使用简单的关键包检测策略，通过 python -m pip show 检测核心包
    """
    if not python_path.exists():
        return False

    if not requirements_file.exists():
        return True

    # 定义关键包（每个环境必须有的核心包）
    # 如果这些包存在，认为依赖已安装
    key_packages = {
        'backend': ['fastapi', 'uvicorn', 'sqlalchemy'],
        'frontend': ['PyQt6', 'requests']
    }

    # 根据路径判断是哪个环境
    env_type = 'backend' if 'backend' in str(python_path) else 'frontend'
    packages_to_check = key_packages.get(env_type, [])

    if not packages_to_check:
        return False

    try:
        # 使用 python -m pip show 检查关键包是否存在
        for pkg in packages_to_check:
            result = subprocess.run(
                [str(python_path), '-m', 'pip', 'show', pkg],
                capture_output=True,
                text=True,
                errors='replace'
            )
            if result.returncode != 0:
                logger.info(f"关键包 {pkg} 未安装")
                return False

        logger.info(f"{env_type} 关键依赖已安装")
        return True

    except Exception as e:
        logger.warning(f"检查依赖时出错: {e}")
        return False


def install_dependencies(python_path: Path, requirements_file: Path, name: str) -> bool:
    """安装依赖"""
    if not requirements_file.exists():
        logger.warning(f"{name} requirements.txt 不存在")
        return True

    # 检查 Python 是否存在
    if not python_path.exists():
        logger.error(f"{name} Python 不存在: {python_path}")
        print(f"[错误] {name} Python 不存在，虚拟环境可能损坏")
        return False

    # 先检查是否已安装
    if check_dependencies_installed(python_path, requirements_file):
        logger.info(f"{name} 依赖已安装")
        return True

    logger.info(f"安装 {name} 依赖...")
    print(f"\n[安装] 安装 {name} 依赖（首次运行需要几分钟）...")

    try:
        # 先升级 pip（忽略错误）
        subprocess.run(
            [str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip', '-q'],
            capture_output=True,
            text=True,
            errors='replace'
        )

        # 安装依赖 - 使用 python -m pip
        logger.info(f"执行: {python_path} -m pip install -r {requirements_file}")
        result = subprocess.run(
            [str(python_path), '-m', 'pip', 'install', '-r', str(requirements_file)],
            capture_output=True,
            text=True,
            errors='replace',
            timeout=600  # 10分钟超时
        )

        if result.returncode != 0:
            # 同时记录 stdout 和 stderr，因为 pip 可能将错误输出到任一位置
            error_output = result.stderr or result.stdout or "(无输出)"
            logger.error(f"安装 {name} 依赖失败 (返回码 {result.returncode})")
            logger.error(f"stdout: {result.stdout[:2000] if result.stdout else '(空)'}")
            logger.error(f"stderr: {result.stderr[:2000] if result.stderr else '(空)'}")
            print(f"[错误] 安装 {name} 依赖失败")
            print(f"       详情请查看 storage/app.log")
            return False

        logger.info(f"{name} 依赖安装成功")
        print(f"       {name} 依赖安装成功")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"安装 {name} 依赖超时（超过10分钟）")
        print(f"[错误] 安装 {name} 依赖超时")
        return False
    except Exception as e:
        logger.error(f"安装 {name} 依赖时出错: {e}")
        print(f"[错误] 安装 {name} 依赖时出错: {e}")
        return False


def setup_environment() -> bool:
    """设置开发环境（创建虚拟环境、安装依赖）"""
    # 如果是打包环境，跳过环境设置
    if IS_FROZEN:
        logger.info("打包环境，跳过环境设置")
        return True

    print("\n[检查] 检查运行环境...")

    # 检查 Python 版本
    if not check_python_version():
        return False

    # 创建后端虚拟环境
    if not create_venv(BACKEND_VENV, "后端"):
        return False

    # 创建前端虚拟环境
    if not create_venv(FRONTEND_VENV, "前端"):
        return False

    # 安装后端依赖（使用 python -m pip）
    backend_requirements = BACKEND_DIR / 'requirements.txt'
    if not install_dependencies(BACKEND_PYTHON, backend_requirements, "后端"):
        return False

    # 安装前端依赖（使用 python -m pip）
    frontend_requirements = FRONTEND_DIR / 'requirements.txt'
    if not install_dependencies(FRONTEND_PYTHON, frontend_requirements, "前端"):
        return False

    print("\n[完成] 环境检查通过")
    return True


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

    # 设置数据库路径
    db_path = STORAGE_DIR / 'afn.db'
    os.environ['DATABASE_URL'] = f"sqlite+aiosqlite:///{db_path}"
    os.environ['VECTOR_DB_PATH'] = str(STORAGE_DIR / 'vectors.db')

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

    # 启动 uvicorn - 输出直接显示到当前控制台
    # 这样可以看到后端的启动过程和错误信息
    backend_process = subprocess.Popen(
        [
            python_exe, '-m', 'uvicorn',
            'app.main:app',
            '--host', '127.0.0.1',
            '--port', str(BACKEND_PORT),
            '--log-level', 'info'  # 显示启动信息
        ],
        cwd=str(BACKEND_DIR)
        # 不设置 stdout/stderr，输出直接显示到当前控制台
    )

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
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_backend(timeout=60):
    """等待后端服务就绪"""
    import urllib.request
    import urllib.error

    print("\n[启动] 等待后端服务就绪...")
    logger.info("等待后端服务就绪...")

    start_time = time.time()
    dots = 0

    while time.time() - start_time < timeout:
        try:
            response = urllib.request.urlopen(f'http://127.0.0.1:{BACKEND_PORT}/health', timeout=2)
            if response.status == 200:
                print("\n[完成] 后端服务已就绪")
                logger.info("后端服务已就绪")
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError, TimeoutError):
            pass

        # 显示进度
        dots = (dots + 1) % 4
        print(f"\r[启动] 等待后端服务就绪{'.' * dots}{' ' * (3 - dots)}", end='', flush=True)
        time.sleep(0.5)

    print("\n[错误] 后端服务启动超时")
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
    """以子进程方式启动前端（开发模式 - 备选方案）"""
    python_exe = str(FRONTEND_PYTHON) if FRONTEND_PYTHON.exists() else sys.executable

    process = subprocess.Popen(
        [python_exe, 'main.py'],
        cwd=str(FRONTEND_DIR)
    )

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

    print("[完成] AFN 已启动，祝您创作愉快！\n")
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
        exit_code = start_frontend()

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
