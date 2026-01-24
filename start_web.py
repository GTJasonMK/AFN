import subprocess
import os
import sys
import time
import signal
import webbrowser

# 配置路径
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend-web")

# 存储子进程列表
processes = []

def get_python_executable():
    """获取后端 Python 解释器路径，优先使用虚拟环境"""
    venv_python = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def start_backend():
    """启动后端 FastAPI 服务"""
    print(f"[*] 正在启动后端服务 (Path: {BACKEND_DIR})...")
    python_exe = get_python_executable()
    
    cmd = [
        python_exe, "-m", "uvicorn", 
        "app.main:app", 
        "--host", "127.0.0.1", 
        "--port", "8123", 
        "--reload"
    ]
    
    # 启动进程
    p = subprocess.Popen(
        cmd, 
        cwd=BACKEND_DIR,
        shell=False, # Windows 下不需要 shell=True 运行 exe
        env=os.environ.copy()
    )
    processes.append(p)
    return p

def start_frontend():
    """启动前端 Vite 服务"""
    print(f"[*] 正在启动前端服务 (Path: {FRONTEND_DIR})...")
    
    # npm 需要在 shell 中运行
    cmd = "npm run dev"
    
    p = subprocess.Popen(
        cmd, 
        cwd=FRONTEND_DIR, 
        shell=True
    )
    processes.append(p)
    return p

def cleanup(signum=None, frame=None):
    """清理进程"""
    print("\n[!] 正在停止所有服务...")
    for p in processes:
        try:
            if sys.platform == 'win32':
                # Windows 下强制终止进程树，确保 npm 启动的 node 进程也被杀死
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(p.pid)])
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
        # 1. 启动后端
        backend_proc = start_backend()
        
        # 等待几秒让后端初始化
        time.sleep(2)
        
        # 2. 启动前端
        frontend_proc = start_frontend()

        print("\n" + "="*50)
        print(" [+] AFN Web 版启动成功！")
        print("     后端 API: http://127.0.0.1:8123/docs")
        print("     前端页面: http://localhost:5173")
        print("     (请在浏览器中访问前端地址)")
        print("="*50 + "\n")
        print("按 Ctrl+C 停止运行")

        # 尝试自动打开浏览器（延迟一点，等待 Vite 启动）
        time.sleep(2)
        webbrowser.open("http://localhost:5173")

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
