"""
依赖安装模块

包含:
- check_python_version() - 检查Python版本
- create_venv() - 创建虚拟环境
- check_dependencies_installed() - 检查依赖是否已安装
- install_dependencies() - 安装依赖
"""

import sys
import os
import subprocess
from pathlib import Path

from .config import BACKEND_DIR, FRONTEND_DIR
from .logging_setup import logger
from .uv_manager import check_uv_available


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
            print(f"       详情请查看 storage/logs/startup.log")
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
