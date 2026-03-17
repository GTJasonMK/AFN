import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser

# 配置路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend-web")

# 默认端口（优先尝试）
DEFAULT_BACKEND_PORT = 8123
DEFAULT_FRONTEND_PORT = 5173

# 存储子进程列表
processes = []


def get_npm_executable() -> str:
    """获取 npm 可执行文件名"""
    return "npm.cmd" if sys.platform == "win32" else "npm"


def get_node_executable() -> str:
    """获取 node 可执行文件名"""
    return "node.exe" if sys.platform == "win32" else "node"


def get_python_executable():
    """获取后端 Python 解释器路径，优先使用虚拟环境"""
    venv_python = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def get_local_vite_bin() -> str | None:
    """获取当前平台可直接执行的本地 vite 路径"""
    vite_bin = "vite.cmd" if sys.platform == "win32" else "vite"
    vite_path = os.path.join(FRONTEND_DIR, "node_modules", ".bin", vite_bin)
    return vite_path if os.path.exists(vite_path) else None


def get_vite_js_entry() -> str | None:
    """获取 vite 的 JS 入口文件路径"""
    vite_js = os.path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js")
    return vite_js if os.path.exists(vite_js) else None


def has_local_vite() -> bool:
    """检查当前平台是否存在可直接执行的本地 vite"""
    return get_local_vite_bin() is not None


def get_node_package_version(package_name: str) -> str | None:
    """读取本地 node_modules 中某个包的版本号"""
    package_json_path = os.path.join(
        FRONTEND_DIR,
        "node_modules",
        *package_name.split("/"),
        "package.json",
    )
    if not os.path.exists(package_json_path):
        return None

    try:
        with open(package_json_path, "r", encoding="utf-8") as file:
            return json.load(file).get("version")
    except Exception:
        return None


def extract_missing_module_name(output: str) -> str | None:
    """从 Node/Vite 错误输出中提取缺失模块名"""
    patterns = [
        r"Cannot find module ['\"]([^'\"]+)['\"]",
        r"Cannot find module ([^ \r\n]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1).strip().rstrip(".,:;")
    return None


def resolve_runtime_package_spec(package_name: str) -> str:
    """为平台相关运行时包拼装带版本号的安装目标"""
    version = None
    if package_name.startswith("@rollup/rollup-"):
        version = get_node_package_version("rollup")
    elif package_name.startswith("@esbuild/"):
        version = get_node_package_version("esbuild")

    return f"{package_name}@{version}" if version else package_name


def run_frontend_npm_install(args: list[str]) -> bool:
    """在 frontend-web 目录执行 npm install 类命令"""
    npm_bin = get_npm_executable()
    if shutil.which(npm_bin) is None:
        print("[!] 未找到 npm，请先安装 Node.js（建议 18+，推荐 20 LTS）")
        return False

    env = os.environ.copy()
    env["NODE_ENV"] = "development"

    result = subprocess.run(
        [npm_bin, *args],
        cwd=FRONTEND_DIR,
        shell=False,
        env=env,
    )
    if result.returncode != 0:
        print(f"[!] 执行 {npm_bin} {' '.join(args)} 失败，退出码: {result.returncode}")
        return False
    return True


def get_vite_probe_command() -> list[str] | None:
    """构造 vite 运行时自检命令"""
    vite_js_entry = get_vite_js_entry()
    if sys.platform == "win32" and vite_js_entry:
        node_bin = get_node_executable()
        if shutil.which(node_bin) is None:
            print("[!] 未找到 node，请先安装 Node.js（建议 18+，推荐 20 LTS）")
            return None
        return [node_bin, vite_js_entry, "--version"]

    local_vite_bin = get_local_vite_bin()
    if local_vite_bin:
        return [local_vite_bin, "--version"]

    if vite_js_entry:
        node_bin = get_node_executable()
        if shutil.which(node_bin) is None:
            print("[!] 未找到 node，请先安装 Node.js（建议 18+，推荐 20 LTS）")
            return None
        return [node_bin, vite_js_entry, "--version"]

    return None


def ensure_vite_runtime_dependencies() -> bool:
    """确认 vite 真正可运行，并在必要时补装缺失的平台包"""
    probe_cmd = get_vite_probe_command()
    if probe_cmd is None:
        return False

    repaired_modules: set[str] = set()
    for _ in range(3):
        result = subprocess.run(
            probe_cmd,
            cwd=FRONTEND_DIR,
            shell=False,
            env={**os.environ.copy(), "NODE_ENV": "development"},
            capture_output=True,
            text=True,
            errors="replace",
        )
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()

        if result.returncode == 0:
            return True

        missing_module = extract_missing_module_name(output)
        if not missing_module or missing_module in repaired_modules:
            print("[!] vite 运行时自检失败。")
            if output:
                first_line = output.splitlines()[0].strip()
                if first_line:
                    print(f"[!] {first_line}")
            return False

        repaired_modules.add(missing_module)
        if missing_module.startswith("@rollup/rollup-") or missing_module.startswith("@esbuild/"):
            print(
                f"[*] 检测到缺少可选的平台运行时包 {missing_module}。"
                "这通常意味着 npm 跳过了 optionalDependencies。"
                "正在执行: npm install --include=dev --include=optional"
            )
            if not run_frontend_npm_install(["install", "--include=dev", "--include=optional"]):
                return False
            continue

        package_spec = resolve_runtime_package_spec(missing_module)
        print(f"[*] 检测到缺少前端运行时包 {missing_module}，正在安装 {package_spec} ...")
        if not run_frontend_npm_install(["install", "--no-save", "--no-package-lock", package_spec]):
            return False

    print("[!] vite 运行时依赖自动修复失败。")
    return False


def ensure_frontend_dependencies() -> bool:
    """确保 Web 前端依赖已安装，且包含 vite 这类 devDependencies"""
    if not has_local_vite():
        vite_js_entry = get_vite_js_entry()
        if sys.platform == "win32" and vite_js_entry:
            print("[*] 检测到 vite.js，但缺少 Windows 所需的 vite.cmd，正在修复 Web 前端依赖...")
        else:
            print("[*] 未检测到当前平台可用的本地 vite，正在安装/修复 Web 前端依赖...")

        if not run_frontend_npm_install(["install", "--include=dev", "--include=optional"]):
            return False

        if not has_local_vite():
            print("[!] 已执行 npm install，但仍未检测到本地 vite。")
            print("[!] 可尝试手动执行: cd frontend-web && npm install --include=dev --include=optional")
            return False

    if not ensure_vite_runtime_dependencies():
        print("[!] 已检测到 vite，但其运行时平台依赖仍不完整。")
        return False

    print("[+] Web 前端依赖已就绪")
    return True


def get_frontend_dev_command(frontend_port: int) -> list[str]:
    """构造前端开发服务器启动命令，优先使用本地 vite"""
    vite_args = [
        "--host",
        "127.0.0.1",
        "--port",
        str(frontend_port),
        "--strictPort",
    ]

    local_vite_bin = get_local_vite_bin()
    if local_vite_bin:
        return [local_vite_bin, *vite_args]

    vite_js_entry = get_vite_js_entry()
    if vite_js_entry:
        node_bin = get_node_executable()
        if shutil.which(node_bin) is None:
            raise RuntimeError("未找到 node，请先安装 Node.js（建议 18+，推荐 20 LTS）")
        return [node_bin, vite_js_entry, *vite_args]

    raise RuntimeError("未检测到本地 vite，请先执行: cd frontend-web && npm install --include=dev --include=optional")


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(preferred_port: int, *, host: str = "127.0.0.1", exclude_ports: set[int] | None = None) -> int:
    """从首选端口开始向上查找可用端口"""
    excludes = exclude_ports or set()

    def candidate_ok(port: int) -> bool:
        return port not in excludes and is_port_free(port, host=host)

    if candidate_ok(preferred_port):
        return preferred_port

    max_port = 65535
    for port in range(preferred_port + 1, max_port + 1):
        if candidate_ok(port):
            return port

    # 兜底：让系统分配一个随机空闲端口
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        random_port = int(sock.getsockname()[1])

    if random_port in excludes:
        raise RuntimeError("无法找到可用端口，请释放端口后重试")

    return random_port


def wait_for_backend_ready(port: int, timeout: int = 30) -> bool:
    """等待后端健康检查通过"""
    health_url = f"http://127.0.0.1:{port}/health"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = opener.open(health_url, timeout=2)
            if response.status == 200:
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            pass
        time.sleep(0.4)

    return False


def start_backend(backend_port: int):
    """启动后端 FastAPI 服务"""
    print(f"[*] 正在启动后端服务 (Path: {BACKEND_DIR})...")
    python_exe = get_python_executable()

    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(backend_port),
        "--reload",
    ]

    p = subprocess.Popen(
        cmd,
        cwd=BACKEND_DIR,
        shell=False,
        env=os.environ.copy(),
    )
    processes.append(p)
    return p


def start_frontend(frontend_port: int, backend_port: int):
    """启动前端 Vite 服务"""
    print(f"[*] 正在启动前端服务 (Path: {FRONTEND_DIR})...")

    env = os.environ.copy()
    env["VITE_BACKEND_PORT"] = str(backend_port)
    env["VITE_WEB_PORT"] = str(frontend_port)
    env["VITE_BACKEND_HOST"] = "127.0.0.1"
    env["NODE_ENV"] = "development"

    cmd = get_frontend_dev_command(frontend_port)

    p = subprocess.Popen(
        cmd,
        cwd=FRONTEND_DIR,
        shell=False,
        env=env,
    )
    processes.append(p)
    return p


def cleanup(signum=None, frame=None):
    """清理进程"""
    print("\n[!] 正在停止所有服务...")
    for p in processes:
        try:
            if sys.platform == "win32":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(p.pid)])
            else:
                p.terminate()
        except Exception as e:
            print(f"停止进程失败: {e}")
    sys.exit(0)


def main():
    # 注册信号处理 (Ctrl+C)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        backend_port = find_available_port(DEFAULT_BACKEND_PORT)
        frontend_port = find_available_port(DEFAULT_FRONTEND_PORT, exclude_ports={backend_port})

        if backend_port != DEFAULT_BACKEND_PORT:
            print(f"[提示] 默认后端端口 {DEFAULT_BACKEND_PORT} 被占用，自动切换到 {backend_port}")
        if frontend_port != DEFAULT_FRONTEND_PORT:
            print(f"[提示] 默认前端端口 {DEFAULT_FRONTEND_PORT} 被占用，自动切换到 {frontend_port}")

        # 1. 启动后端
        backend_proc = start_backend(backend_port)

        # 2. 等待后端就绪
        if not wait_for_backend_ready(backend_port, timeout=45):
            print("[!] 后端服务未在预期时间内就绪")
            cleanup()

        if not ensure_frontend_dependencies():
            print("[!] Web 前端依赖未准备完成，无法启动前端服务")
            cleanup()

        # 3. 启动前端
        frontend_proc = start_frontend(frontend_port, backend_port)
        time.sleep(2)
        if frontend_proc.poll() is not None:
            print("[!] 前端服务启动后立即退出")
            print("[!] 常见原因：node_modules 不是在当前平台安装，缺少 vite.cmd 或平台相关依赖")
            print("[!] 若仍提示 vite 不存在，可手动执行: cd frontend-web && npm install --include=dev --include=optional")
            cleanup()

        frontend_url = f"http://127.0.0.1:{frontend_port}"

        print("\n" + "=" * 50)
        print(" [+] AFN Web 版启动成功！")
        print(f"     后端 API: http://127.0.0.1:{backend_port}/docs")
        print(f"     前端页面: {frontend_url}")
        print("     (请在浏览器中访问前端地址)")
        print("=" * 50 + "\n")
        print("按 Ctrl+C 停止运行")

        webbrowser.open(frontend_url)

        # 保持主线程运行并监控子进程
        while True:
            time.sleep(1)
            if backend_proc.poll() is not None:
                print("[!] 后端服务异常退出")
                cleanup()
            if frontend_proc.poll() is not None:
                print("[!] 前端服务异常退出")
                cleanup()

    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"[!] 发生错误: {e}")
        cleanup()


if __name__ == "__main__":
    main()
