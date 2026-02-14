import os
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


def get_python_executable():
    """获取后端 Python 解释器路径，优先使用虚拟环境"""
    venv_python = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


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

    npm_bin = "npm.cmd" if sys.platform == "win32" else "npm"
    cmd = [
        npm_bin,
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(frontend_port),
        "--strictPort",
    ]

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

        # 3. 启动前端
        frontend_proc = start_frontend(frontend_port, backend_port)

        frontend_url = f"http://127.0.0.1:{frontend_port}"

        print("\n" + "=" * 50)
        print(" [+] AFN Web 版启动成功！")
        print(f"     后端 API: http://127.0.0.1:{backend_port}/docs")
        print(f"     前端页面: {frontend_url}")
        print("     (请在浏览器中访问前端地址)")
        print("=" * 50 + "\n")
        print("按 Ctrl+C 停止运行")

        # 延迟一点，等待 Vite 启动
        time.sleep(2)
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
