"""
端口工具模块

包含:
- is_port_in_use() - 检查端口是否被占用
- get_pid_using_port() - 获取占用端口的进程PID
- kill_process_on_port() - 关闭占用端口的进程
- ensure_port_available() - 确保端口可用
"""

import sys
import time
import socket
import subprocess

from .logging_setup import logger


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
