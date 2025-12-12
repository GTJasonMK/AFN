"""
数据库迁移脚本：为蓝图表添加头像字段

使用方法：
    cd backend
    python -m scripts.migrate_add_avatar

此脚本会检查并添加以下字段到 novel_blueprints 表：
- avatar_svg: TEXT 类型，存储SVG代码
- avatar_animal: VARCHAR(64) 类型，存储动物类型
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    """获取数据库路径"""
    # 数据库在项目根目录的 storage 目录下
    return Path(__file__).resolve().parents[2] / "storage" / "afn.db"


def check_column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """检查列是否存在"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate():
    """执行迁移"""
    db_path = get_db_path()

    if not db_path.exists():
        print(f"数据库文件不存在: {db_path}")
        print("将在首次启动应用时自动创建新表结构")
        return

    print(f"连接数据库: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='novel_blueprints'")
        if not cursor.fetchone():
            print("novel_blueprints 表不存在，将在首次启动应用时自动创建")
            return

        # 添加 avatar_svg 字段
        if not check_column_exists(cursor, "novel_blueprints", "avatar_svg"):
            print("添加 avatar_svg 字段...")
            cursor.execute("ALTER TABLE novel_blueprints ADD COLUMN avatar_svg TEXT")
            print("  -> 完成")
        else:
            print("avatar_svg 字段已存在，跳过")

        # 添加 avatar_animal 字段
        if not check_column_exists(cursor, "novel_blueprints", "avatar_animal"):
            print("添加 avatar_animal 字段...")
            cursor.execute("ALTER TABLE novel_blueprints ADD COLUMN avatar_animal VARCHAR(64)")
            print("  -> 完成")
        else:
            print("avatar_animal 字段已存在，跳过")

        conn.commit()
        print("\n迁移完成!")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
