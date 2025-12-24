"""
诊断脚本 - 检查 AFN 部署环境问题
"""
import sys
import os
import subprocess
from pathlib import Path

print("=" * 60)
print(" AFN 部署环境诊断")
print("=" * 60)

# 基础信息
print(f"\n[系统信息]")
print(f"  Python 版本: {sys.version}")
print(f"  Python 路径: {sys.executable}")
print(f"  当前目录: {os.getcwd()}")
print(f"  平台: {sys.platform}")

# 检查uv
print(f"\n[包管理器检查]")
try:
    result = subprocess.run(
        ['uv', '--version'],
        capture_output=True,
        text=True,
        errors='replace'
    )
    if result.returncode == 0:
        print(f"  uv 版本: {result.stdout.strip()}")
        print(f"  uv 状态: 可用 (快速模式)")
    else:
        print(f"  uv 状态: 不可用")
except FileNotFoundError:
    print(f"  uv 状态: 未安装")
    print(f"  提示: 运行 'pip install uv' 可安装uv加速包管理")

# 检查虚拟环境
BASE_DIR = Path(__file__).parent
FRONTEND_VENV = BASE_DIR / 'frontend' / '.venv'
BACKEND_VENV = BASE_DIR / 'backend' / '.venv'

print(f"\n[虚拟环境检查]")
print(f"  前端 venv 存在: {FRONTEND_VENV.exists()}")
print(f"  后端 venv 存在: {BACKEND_VENV.exists()}")

# 检查前端 Python
if sys.platform == 'win32':
    FRONTEND_PYTHON = FRONTEND_VENV / 'Scripts' / 'python.exe'
else:
    FRONTEND_PYTHON = FRONTEND_VENV / 'bin' / 'python'

print(f"  前端 Python 存在: {FRONTEND_PYTHON.exists()}")
print(f"  前端 Python 路径: {FRONTEND_PYTHON}")

if FRONTEND_PYTHON.exists():
    print(f"\n[前端依赖检查]")

    # 获取已安装的包
    try:
        result = subprocess.run(
            [str(FRONTEND_PYTHON), '-m', 'pip', 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            errors='replace'
        )
        packages = result.stdout.strip().split('\n') if result.stdout else []

        # 查找关键包
        key_packages = ['PyQt6', 'PyQt6-Qt6', 'PyQt6-sip', 'requests', 'PyMuPDF']
        print(f"  已安装的关键包:")
        for pkg in packages:
            pkg_name = pkg.split('==')[0] if '==' in pkg else pkg
            if any(kp.lower() in pkg_name.lower() for kp in key_packages):
                print(f"    - {pkg}")

        # 检查是否缺少关键包
        installed_names = [p.split('==')[0].lower() for p in packages]
        missing = []
        for kp in key_packages:
            if kp.lower() not in installed_names:
                missing.append(kp)

        if missing:
            print(f"\n  [警告] 缺少以下关键包: {', '.join(missing)}")

    except Exception as e:
        print(f"  [错误] 无法获取包列表: {e}")

    # 测试 PyQt6 导入
    print(f"\n[PyQt6 导入测试]")
    try:
        result = subprocess.run(
            [str(FRONTEND_PYTHON), '-c',
             'import PyQt6.QtCore; print("QtCore OK"); '
             'import PyQt6.QtWidgets; print("QtWidgets OK"); '
             'import PyQt6.QtGui; print("QtGui OK"); '
             'print("PyQt6 路径:", PyQt6.__file__)'
            ],
            capture_output=True,
            text=True,
            errors='replace'
        )
        if result.returncode == 0:
            print(f"  {result.stdout.strip()}")
        else:
            print(f"  [错误] PyQt6 导入失败:")
            print(f"  {result.stderr.strip()}")

            # 进一步诊断
            print(f"\n[PyQt6 详细诊断]")

            # 检查 PyQt6 包目录
            result2 = subprocess.run(
                [str(FRONTEND_PYTHON), '-c',
                 'import PyQt6; import os; '
                 'pyqt_dir = os.path.dirname(PyQt6.__file__); '
                 'print("PyQt6 目录:", pyqt_dir); '
                 'qt_dir = os.path.join(pyqt_dir, "Qt6"); '
                 'print("Qt6 目录存在:", os.path.exists(qt_dir)); '
                 'if os.path.exists(qt_dir): '
                 '    bin_dir = os.path.join(qt_dir, "bin"); '
                 '    print("bin 目录存在:", os.path.exists(bin_dir)); '
                 '    if os.path.exists(bin_dir): '
                 '        dlls = [f for f in os.listdir(bin_dir) if f.endswith(".dll")]; '
                 '        print("DLL 文件数:", len(dlls)); '
                 '        print("部分DLL:", dlls[:5] if dlls else "无")'
                ],
                capture_output=True,
                text=True,
                errors='replace'
            )
            print(f"  {result2.stdout.strip()}")
            if result2.stderr:
                print(f"  {result2.stderr.strip()}")

    except Exception as e:
        print(f"  [错误] 测试失败: {e}")

# 检查后端
if sys.platform == 'win32':
    BACKEND_PYTHON = BACKEND_VENV / 'Scripts' / 'python.exe'
else:
    BACKEND_PYTHON = BACKEND_VENV / 'bin' / 'python'

print(f"\n[后端依赖检查]")
print(f"  后端 Python 存在: {BACKEND_PYTHON.exists()}")

if BACKEND_PYTHON.exists():
    try:
        result = subprocess.run(
            [str(BACKEND_PYTHON), '-m', 'pip', 'list', '--format=freeze'],
            capture_output=True,
            text=True,
            errors='replace'
        )
        packages = result.stdout.strip().split('\n') if result.stdout else []

        key_packages = ['fastapi', 'uvicorn', 'sqlalchemy', 'aiosqlite']
        print(f"  已安装的关键包:")
        for pkg in packages:
            pkg_name = pkg.split('==')[0] if '==' in pkg else pkg
            if any(kp.lower() in pkg_name.lower() for kp in key_packages):
                print(f"    - {pkg}")

    except Exception as e:
        print(f"  [错误] 无法获取包列表: {e}")

print(f"\n[建议]")
print("  如果 PyQt6 导入失败，请尝试:")
print("  1. 删除前端虚拟环境并重建:")
print("     rmdir /s /q frontend\\.venv")
print("     python -m venv frontend\\.venv")
print("     frontend\\.venv\\Scripts\\pip install -r frontend\\requirements.txt")
print("")
print("  2. 或安装 Visual C++ Redistributable:")
print("     https://aka.ms/vs/17/release/vc_redist.x64.exe")
print("")
print("=" * 60)
