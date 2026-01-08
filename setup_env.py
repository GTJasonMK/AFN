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
"""

import sys
import os
import subprocess
import socket
import time
import logging
from pathlib import Path

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


# ============================================================
# UV 包管理器
# ============================================================

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
    logger.info("AFN (Agents for Novel) 环境检查...")


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
    """创建虚拟环境（优先使用uv，回退到venv）"""
    if venv_path.exists():
        logger.info(f"{name} 虚拟环境已存在")
        print(f"       {name} 虚拟环境已存在 [OK]")
        return True

    logger.info(f"创建 {name} 虚拟环境...")
    print(f"\n[安装] 创建 {name} 虚拟环境...")
    print(f"       路径: {venv_path}")

    use_uv = check_uv_available()

    try:
        if use_uv:
            # 使用uv创建虚拟环境（更快）
            print(f"       使用 uv 创建 (快速模式)")
            cmd = ['uv', 'venv', str(venv_path), '--python', sys.executable]
        else:
            # 回退到标准venv
            print(f"       使用 python -m venv 创建")
            cmd = [sys.executable, '-m', 'venv', str(venv_path)]

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace'
        )

        # 实时显示输出
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line:
                    print(f"       {line}")

        process.wait()

        if process.returncode != 0:
            logger.error(f"创建 {name} 虚拟环境失败，返回码: {process.returncode}")
            print(f"[错误] 创建 {name} 虚拟环境失败")
            return False

        logger.info(f"{name} 虚拟环境创建成功")
        print(f"       {name} 虚拟环境创建成功 [OK]")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"创建 {name} 虚拟环境失败: {e.stderr}")
        print(f"[错误] 创建 {name} 虚拟环境失败")
        return False


def check_dependencies_installed(python_path: Path, requirements_file: Path, name: str = "") -> bool:
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
        'backend': ['fastapi', 'uvicorn', 'sqlalchemy', 'sentence-transformers'],
        'frontend': ['PyQt6', 'requests']
    }

    # 根据路径判断是哪个环境
    env_type = 'backend' if 'backend' in str(python_path) else 'frontend'
    packages_to_check = key_packages.get(env_type, [])

    if not packages_to_check:
        return False

    try:
        print(f"       检查 {name or env_type} 核心依赖...")
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
                print(f"       - {pkg}: 未安装")
                return False
            else:
                # 从输出中提取版本号
                version = ""
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        break
                print(f"       - {pkg}: {version} [OK]")

        logger.info(f"{env_type} 关键依赖已安装")
        return True

    except Exception as e:
        logger.warning(f"检查依赖时出错: {e}")
        return False


def install_dependencies(python_path: Path, requirements_file: Path, name: str, force: bool = False) -> bool:
    """安装依赖（优先使用uv，回退到pip）"""
    if not requirements_file.exists():
        logger.warning(f"{name} requirements.txt 不存在")
        return True

    # 检查 Python 是否存在
    if not python_path.exists():
        logger.error(f"{name} Python 不存在: {python_path}")
        print(f"[错误] {name} Python 不存在，虚拟环境可能损坏")
        return False

    # 先检查是否已安装（除非强制重装）
    if not force and check_dependencies_installed(python_path, requirements_file, name):
        logger.info(f"{name} 依赖已安装")
        print(f"       {name} 依赖检查通过 [OK]")
        return True

    use_uv = check_uv_available()

    if use_uv:
        return _install_with_uv(python_path, requirements_file, name)
    else:
        return _install_with_pip(python_path, requirements_file, name)


def _install_with_uv(python_path: Path, requirements_file: Path, name: str) -> bool:
    """使用uv安装依赖（快速模式）"""
    logger.info(f"使用 uv 安装 {name} 依赖...")
    print(f"\n[安装] 安装 {name} 依赖 (uv 快速模式)...")
    print(f"       requirements: {requirements_file}")
    print(f"       正在解析依赖...", flush=True)

    try:
        # uv pip install 直接安装，无需先升级pip
        logger.info(f"执行: uv pip install -r {requirements_file}")

        # 设置环境变量禁用颜色输出，便于解析
        env = os.environ.copy()
        env['NO_COLOR'] = '1'
        env['UV_NO_PROGRESS'] = '1'

        process = subprocess.Popen(
            ['uv', 'pip', 'install', '-r', str(requirements_file),
             '--python', str(python_path),
             '--no-progress',
             '--verbose'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace',
            bufsize=1,
            env=env,
        )

        # 实时显示安装进度
        package_count = 0
        has_output = False
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                has_output = True
                if 'Resolved' in line:
                    print(f"       {line}", flush=True)
                elif 'Prepared' in line:
                    print(f"       {line}", flush=True)
                elif 'Installed' in line and 'packages' in line:
                    print(f"       {line}", flush=True)
                elif 'Uninstalled' in line:
                    print(f"       {line}", flush=True)
                elif 'Audited' in line:
                    print(f"       {line}", flush=True)
                elif line.startswith('+'):
                    package_count += 1
                    pkg_info = line[1:].strip()
                    print(f"       [{package_count}] + {pkg_info}", flush=True)
                elif line.startswith('-'):
                    print(f"       {line}", flush=True)
                elif 'Installing' in line:
                    package_count += 1
                    pkg_info = line.replace('Installing ', '').strip()
                    print(f"       [{package_count}] Installing: {pkg_info[:60]}", flush=True)
                elif 'Building' in line:
                    print(f"       Building: {line[:50]}...", flush=True)
                elif 'Downloading' in line:
                    print(f"       Downloading...", flush=True)
                elif 'Using' in line and 'Python' in line:
                    print(f"       {line}", flush=True)
                elif 'error' in line.lower() or 'Error' in line:
                    print(f"       [!] {line}", flush=True)
                    logger.warning(f"uv输出: {line}")
                elif 'warning' in line.lower():
                    logger.debug(f"uv警告: {line}")
                else:
                    logger.debug(f"uv: {line}")

        process.wait()

        if not has_output:
            print(f"       (依赖已是最新)", flush=True)

        if process.returncode != 0:
            logger.error(f"uv 安装 {name} 依赖失败 (返回码 {process.returncode})")
            print(f"\n[错误] 安装 {name} 依赖失败")
            print(f"       尝试使用 pip 回退...")
            return _install_with_pip(python_path, requirements_file, name)

        logger.info(f"{name} 依赖安装成功 (uv)")
        print(f"\n       {name} 依赖安装成功 [OK]")
        return True

    except Exception as e:
        logger.error(f"uv 安装 {name} 依赖时出错: {e}")
        print(f"       uv 安装失败，尝试使用 pip 回退...")
        return _install_with_pip(python_path, requirements_file, name)


def _install_with_pip(python_path: Path, requirements_file: Path, name: str) -> bool:
    """使用pip安装依赖（传统模式）"""
    logger.info(f"使用 pip 安装 {name} 依赖...")
    print(f"\n[安装] 安装 {name} 依赖 (pip 模式)...")
    print(f"       这可能需要几分钟，请耐心等待...")
    print(f"       requirements: {requirements_file}")

    try:
        # 先升级 pip
        print(f"\n       [1/2] 升级 pip...")
        pip_process = subprocess.Popen(
            [str(python_path), '-m', 'pip', 'install', '--upgrade', 'pip'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace'
        )
        if pip_process.stdout:
            for line in pip_process.stdout:
                line = line.strip()
                if line and not line.startswith('WARNING'):
                    if 'Successfully' in line or 'Requirement' in line:
                        print(f"             {line}")
        pip_process.wait()

        # 安装依赖
        print(f"\n       [2/2] 安装依赖包...")
        logger.info(f"执行: {python_path} -m pip install -r {requirements_file}")

        process = subprocess.Popen(
            [str(python_path), '-m', 'pip', 'install', '-r', str(requirements_file)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace'
        )

        installed_count = 0
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('WARNING'):
                    continue

                if line.startswith('Collecting'):
                    pkg_name = line.split()[1].split('==')[0].split('>=')[0].split('<')[0]
                    print(f"             Collecting: {pkg_name}")
                elif line.startswith('Downloading'):
                    if '(' in line and ')' in line:
                        size_info = line[line.rfind('('):line.rfind(')')+1]
                        print(f"             Downloading {size_info}")
                elif line.startswith('Installing collected'):
                    parts = line.replace('Installing collected packages:', '').strip()
                    packages = [p.strip() for p in parts.split(',') if p.strip()]
                    installed_count = len(packages)
                    print(f"             Installing {installed_count} packages...")
                elif line.startswith('Successfully installed'):
                    print(f"             {line}")
                elif 'error' in line.lower() or 'Error' in line:
                    print(f"             [!] {line}")
                    logger.warning(f"pip输出: {line}")

        process.wait()

        if process.returncode != 0:
            logger.error(f"安装 {name} 依赖失败 (返回码 {process.returncode})")
            print(f"\n[错误] 安装 {name} 依赖失败")
            print(f"       详情请查看 storage/app.log")
            return False

        logger.info(f"{name} 依赖安装成功")
        print(f"\n       {name} 依赖安装成功 [OK]")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"安装 {name} 依赖超时（超过10分钟）")
        print(f"[错误] 安装 {name} 依赖超时")
        return False
    except Exception as e:
        logger.error(f"安装 {name} 依赖时出错: {e}")
        print(f"[错误] 安装 {name} 依赖时出错: {e}")
        return False


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
            print("\n[错误] 环境设置失败，请查看 storage/app.log")
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
        print("       请查看 storage/app.log 获取详细信息")
        safe_input("\n按回车键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
