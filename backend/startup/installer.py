"""
依赖安装模块

包含:
- check_python_version() - 检查Python版本
- create_venv() - 创建虚拟环境
- check_dependencies_installed() - 检查依赖是否已安装
- install_dependencies() - 智能安装依赖（增量安装/更新/删除）
"""

import sys
import os
import re
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple, Optional

from .config import BACKEND_DIR, FRONTEND_DIR
from .logging_setup import logger
from .uv_manager import check_uv_available


# ============================================================
# 数据结构
# ============================================================

@dataclass
class PackageSpec:
    """包规格信息"""
    name: str                    # 包名（标准化后的小写）
    original_name: str           # 原始包名
    version_spec: str            # 版本规格（如 ==1.0.0, >=2.0）
    extras: List[str]            # extras（如 httpx[http2] 中的 http2）
    raw_line: str                # 原始行

    @property
    def install_spec(self) -> str:
        """获取用于安装的规格字符串"""
        if self.extras:
            return f"{self.original_name}[{','.join(self.extras)}]{self.version_spec}"
        return f"{self.original_name}{self.version_spec}"


@dataclass
class DependencyDiff:
    """依赖差异"""
    to_install: List[PackageSpec]   # 需要新安装的包
    to_update: List[PackageSpec]    # 需要更新的包（版本或extras变化）
    to_remove: List[str]            # 需要删除的包名
    unchanged: List[str]            # 无变化的包名


# ============================================================
# 解析函数
# ============================================================

def _normalize_package_name(name: str) -> str:
    """标准化包名（pip 包名不区分大小写，且 - 和 _ 等价）"""
    return re.sub(r'[-_.]+', '-', name.lower())


def _parse_requirement_line(line: str) -> Optional[PackageSpec]:
    """解析 requirements.txt 中的一行

    支持格式:
    - package==1.0.0
    - package>=1.0.0
    - package[extra1,extra2]==1.0.0
    - package  # 无版本约束
    """
    line = line.strip()

    # 跳过空行和注释
    if not line or line.startswith('#'):
        return None

    # 跳过 -r, -e, --index-url 等特殊行
    if line.startswith('-'):
        return None

    # 解析 extras: package[extra1,extra2]
    extras = []
    extras_match = re.match(r'^([a-zA-Z0-9_-]+)\[([^\]]+)\](.*)$', line)
    if extras_match:
        original_name = extras_match.group(1)
        extras = [e.strip() for e in extras_match.group(2).split(',')]
        rest = extras_match.group(3)
    else:
        # 无 extras
        match = re.match(r'^([a-zA-Z0-9_-]+)(.*)$', line)
        if not match:
            return None
        original_name = match.group(1)
        rest = match.group(2)

    # 解析版本规格
    version_spec = rest.strip()
    # 移除行内注释
    if '#' in version_spec:
        version_spec = version_spec.split('#')[0].strip()

    return PackageSpec(
        name=_normalize_package_name(original_name),
        original_name=original_name,
        version_spec=version_spec,
        extras=extras,
        raw_line=line
    )


def _parse_requirements_file(requirements_file: Path) -> Dict[str, PackageSpec]:
    """解析 requirements.txt 文件，返回包名到规格的映射"""
    packages = {}

    if not requirements_file.exists():
        return packages

    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            spec = _parse_requirement_line(line)
            if spec:
                packages[spec.name] = spec

    return packages


def _get_installed_packages(python_path: Path) -> Dict[str, Tuple[str, str]]:
    """获取已安装的包列表（优先使用uv，回退到pip）

    Returns:
        Dict[normalized_name, (original_name, version)]
    """
    packages = {}
    use_uv = check_uv_available()

    try:
        if use_uv:
            cmd = ['uv', 'pip', 'list', '--python', str(python_path), '--format=freeze']
        else:
            cmd = [str(python_path), '-m', 'pip', 'list', '--format=freeze']

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors='replace',
            timeout=60
        )

        if result.returncode != 0:
            tool_name = "uv" if use_uv else "pip"
            logger.warning(f"{tool_name} list 失败: {result.stderr}")
            return packages

        for line in result.stdout.strip().split('\n'):
            line = line.strip()
            if not line or '==' not in line:
                continue

            # 格式: package==version
            parts = line.split('==', 1)
            if len(parts) == 2:
                name, version = parts
                normalized = _normalize_package_name(name)
                packages[normalized] = (name, version)

    except Exception as e:
        logger.warning(f"获取已安装包列表失败: {e}")

    return packages


def _compute_dependency_diff(
    required: Dict[str, PackageSpec],
    installed: Dict[str, Tuple[str, str]],
    track_removals: bool = True
) -> DependencyDiff:
    """计算依赖差异

    Args:
        required: requirements.txt 中要求的包
        installed: 当前已安装的包
        track_removals: 是否跟踪需要删除的包

    Returns:
        DependencyDiff: 差异信息
    """
    to_install = []
    to_update = []
    to_remove = []
    unchanged = []

    # 检查需要安装或更新的包
    for name, spec in required.items():
        if name not in installed:
            # 新包，需要安装
            to_install.append(spec)
        else:
            # 已安装，检查是否需要更新
            _, installed_version = installed[name]
            needs_update = False

            # 检查版本是否匹配
            if spec.version_spec:
                # 提取精确版本号（如 ==1.0.0 -> 1.0.0）
                version_match = re.match(r'^==(.+)$', spec.version_spec)
                if version_match:
                    required_version = version_match.group(1)
                    if installed_version != required_version:
                        needs_update = True
                        logger.info(f"包 {name} 版本不匹配: 已安装 {installed_version}, 需要 {required_version}")

            # 检查 extras 是否变化（extras 变化也需要重新安装）
            if spec.extras:
                # 有 extras 要求，需要重新安装以确保 extras 被安装
                # 注意：pip list 不显示 extras 信息，所以我们保守地重新安装
                needs_update = True
                logger.info(f"包 {name} 有 extras 要求: {spec.extras}")

            if needs_update:
                to_update.append(spec)
            else:
                unchanged.append(name)

    # 检查需要删除的包（只删除明确在 requirements 中定义过但现在被移除的包）
    # 注意：不删除依赖包，只删除顶层包
    if track_removals:
        # 获取 requirements 中曾经定义的包（通过比较）
        for name in installed:
            if name in required:
                continue
            # 不在 requirements 中的包，可能是依赖包或用户手动安装的
            # 为安全起见，不自动删除
            pass

    return DependencyDiff(
        to_install=to_install,
        to_update=to_update,
        to_remove=to_remove,
        unchanged=unchanged
    )


def _load_previous_requirements(cache_file: Path) -> Set[str]:
    """加载上次的 requirements 包名列表（用于检测删除）"""
    if not cache_file.exists():
        return set()

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()


def _save_current_requirements(cache_file: Path, packages: Dict[str, PackageSpec]):
    """保存当前的 requirements 包名列表"""
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            for name in sorted(packages.keys()):
                f.write(f"{name}\n")
    except Exception as e:
        logger.warning(f"保存 requirements 缓存失败: {e}")


# ============================================================
# 主要函数
# ============================================================

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


def check_dependencies_installed(python_path: Path, requirements_file: Path, name: str = "") -> Optional[DependencyDiff]:
    """检查依赖是否已安装，返回差异信息

    Returns:
        None: 如果所有依赖都已正确安装
        DependencyDiff: 如果有需要安装/更新/删除的包
    """
    if not python_path.exists():
        return DependencyDiff(to_install=[], to_update=[], to_remove=[], unchanged=[])

    if not requirements_file.exists():
        return None

    env_type = 'backend' if 'backend' in str(python_path) else 'frontend'
    print(f"       检查 {name or env_type} 依赖...")

    # 解析 requirements.txt
    required = _parse_requirements_file(requirements_file)
    if not required:
        return None

    # 获取已安装的包
    installed = _get_installed_packages(python_path)

    # 计算差异
    diff = _compute_dependency_diff(required, installed)

    # 显示检查结果
    if diff.to_install:
        print(f"       - 需要安装: {len(diff.to_install)} 个包")
        for spec in diff.to_install[:3]:
            print(f"         + {spec.install_spec}")
        if len(diff.to_install) > 3:
            print(f"         ... 等 {len(diff.to_install)} 个")

    if diff.to_update:
        print(f"       - 需要更新: {len(diff.to_update)} 个包")
        for spec in diff.to_update[:3]:
            print(f"         ~ {spec.install_spec}")
        if len(diff.to_update) > 3:
            print(f"         ... 等 {len(diff.to_update)} 个")

    if diff.to_remove:
        print(f"       - 需要删除: {len(diff.to_remove)} 个包")

    # 如果没有变化，返回 None
    if not diff.to_install and not diff.to_update and not diff.to_remove:
        print(f"       {name or env_type} 依赖已是最新 [OK]")
        return None

    return diff


def install_dependencies(python_path: Path, requirements_file: Path, name: str, force: bool = False) -> bool:
    """智能安装依赖（增量安装/更新）

    Args:
        python_path: Python 解释器路径
        requirements_file: requirements.txt 文件路径
        name: 环境名称（用于显示）
        force: 是否强制重新安装所有依赖

    Returns:
        bool: 是否成功
    """
    if not requirements_file.exists():
        logger.warning(f"{name} requirements.txt 不存在")
        return True

    if not python_path.exists():
        logger.error(f"{name} Python 不存在: {python_path}")
        print(f"[错误] {name} Python 不存在，虚拟环境可能损坏")
        return False

    # 强制模式：重新安装所有依赖
    if force:
        print(f"\n[安装] 强制重新安装 {name} 所有依赖...")
        use_uv = check_uv_available()
        if use_uv:
            return _install_with_uv(python_path, requirements_file, name)
        else:
            return _install_with_pip(python_path, requirements_file, name)

    # 智能模式：检查差异，只安装/更新需要的包
    diff = check_dependencies_installed(python_path, requirements_file, name)

    # diff 为 None 表示所有依赖都已正确安装
    if diff is None:
        return True

    # 有需要处理的包
    packages_to_process = diff.to_install + diff.to_update

    if not packages_to_process and not diff.to_remove:
        print(f"       {name} 依赖检查通过 [OK]")
        return True

    use_uv = check_uv_available()

    # 安装/更新包
    if packages_to_process:
        success = _install_packages(
            python_path, packages_to_process, name, use_uv
        )
        if not success:
            return False

    # 删除不需要的包
    if diff.to_remove:
        _uninstall_packages(python_path, diff.to_remove, name, use_uv)

    print(f"\n       {name} 依赖更新完成 [OK]")
    return True


def _install_packages(
    python_path: Path,
    packages: List[PackageSpec],
    name: str,
    use_uv: bool
) -> bool:
    """安装指定的包列表"""
    if not packages:
        return True

    # 构建安装规格列表
    specs = [pkg.install_spec for pkg in packages]

    print(f"\n[安装] 安装/更新 {name} 依赖 ({len(specs)} 个包)...")
    for spec in specs[:5]:
        print(f"       - {spec}")
    if len(specs) > 5:
        print(f"       ... 等 {len(specs)} 个")

    try:
        if use_uv:
            cmd = ['uv', 'pip', 'install', '--python', str(python_path)] + specs
        else:
            cmd = [str(python_path), '-m', 'pip', 'install'] + specs

        logger.info(f"执行: {' '.join(cmd[:10])}...")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace'
        )

        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line or line.startswith('WARNING'):
                    continue
                # 显示关键信息
                if any(kw in line for kw in ['Installing', 'Successfully', 'Collecting', '+', 'Resolved']):
                    print(f"       {line[:70]}")
                elif 'error' in line.lower():
                    print(f"       [!] {line}")

        process.wait()

        if process.returncode != 0:
            logger.error(f"安装 {name} 依赖失败 (返回码 {process.returncode})")
            print(f"\n[错误] 安装 {name} 依赖失败")
            return False

        logger.info(f"{name} 依赖安装成功")
        return True

    except Exception as e:
        logger.error(f"安装 {name} 依赖时出错: {e}")
        print(f"[错误] 安装 {name} 依赖时出错: {e}")
        return False


def _uninstall_packages(
    python_path: Path,
    packages: List[str],
    name: str,
    use_uv: bool
) -> bool:
    """卸载指定的包列表"""
    if not packages:
        return True

    print(f"\n[清理] 删除 {name} 不需要的依赖 ({len(packages)} 个包)...")
    for pkg in packages[:5]:
        print(f"       - {pkg}")
    if len(packages) > 5:
        print(f"       ... 等 {len(packages)} 个")

    try:
        if use_uv:
            cmd = ['uv', 'pip', 'uninstall', '--python', str(python_path), '-y'] + packages
        else:
            cmd = [str(python_path), '-m', 'pip', 'uninstall', '-y'] + packages

        logger.info(f"执行: {' '.join(cmd[:10])}...")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors='replace'
        )

        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if line and 'Successfully' in line:
                    print(f"       {line}")

        process.wait()

        if process.returncode != 0:
            logger.warning(f"删除 {name} 部分依赖失败")
            return False

        logger.info(f"{name} 依赖清理成功")
        return True

    except Exception as e:
        logger.warning(f"删除 {name} 依赖时出错: {e}")
        return False


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
