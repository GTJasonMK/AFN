"""
后端服务器启动脚本 - 用于 PyInstaller 打包

此脚本作为打包后的入口点，启动 uvicorn 服务器运行 FastAPI 应用。
"""

import sys
import os
from pathlib import Path

# 确定运行目录
if getattr(sys, 'frozen', False):
    # 打包后的运行目录
    BASE_DIR = Path(sys._MEIPASS)
    # 设置工作目录为可执行文件所在目录，用于存储数据库等文件
    WORK_DIR = Path(sys.executable).parent
    storage_dir = WORK_DIR / "storage"
else:
    # 开发环境
    BASE_DIR = Path(__file__).parent
    # 开发环境：存储目录在项目根目录（与 run_app.py 和 config.py 保持一致）
    WORK_DIR = BASE_DIR.parent  # E:\code\AFN
    storage_dir = WORK_DIR / "storage"

# 切换到工作目录
os.chdir(WORK_DIR)

# 确保 storage 目录存在
storage_dir.mkdir(exist_ok=True)

# 设置环境变量
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{storage_dir}/afn.db"
os.environ["VECTOR_DB_PATH"] = str(storage_dir / "vectors.db")

# 将提示词目录添加到环境变量
prompts_dir = BASE_DIR / "prompts"
os.environ["PROMPTS_DIR"] = str(prompts_dir)


def main():
    """启动服务器"""
    import uvicorn
    from app.main import app

    print("=" * 60)
    print("AFN (Agents for Novel) 后端服务启动中...")
    print(f"工作目录: {WORK_DIR}")
    print(f"数据存储: {storage_dir}")
    print("=" * 60)

    # 启动服务器
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8123,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
