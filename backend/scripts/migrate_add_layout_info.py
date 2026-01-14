"""
数据库迁移脚本：添加 layout_info 列到 chapter_manga_prompts 表

用法：
    cd backend
    python migrate_add_layout_info.py
"""

import sqlite3
from pathlib import Path


def migrate_db(db_path: Path) -> bool:
    """迁移单个数据库文件

    Returns:
        True 如果迁移成功或无需迁移
    """
    if not db_path.exists():
        print(f"  数据库文件不存在: {db_path}")
        return False

    print(f"  连接数据库: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='chapter_manga_prompts'
        """)
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            # 创建表（包含新的 layout_info 列）
            print("  chapter_manga_prompts 表不存在，正在创建...")
            cursor.execute("""
                CREATE TABLE chapter_manga_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chapter_id INTEGER NOT NULL UNIQUE,
                    character_profiles JSON DEFAULT '{}',
                    style_guide TEXT,
                    scenes JSON DEFAULT '[]',
                    layout_info JSON DEFAULT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_chapter_manga_prompts_chapter_id
                ON chapter_manga_prompts(chapter_id)
            """)
            conn.commit()
            print("  表创建成功！")
            return True

        # 检查列是否已存在
        cursor.execute("PRAGMA table_info(chapter_manga_prompts)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'layout_info' in columns:
            print("  layout_info 列已存在，无需迁移")
            return True

        # 添加新列
        print("  正在添加 layout_info 列...")
        cursor.execute("""
            ALTER TABLE chapter_manga_prompts
            ADD COLUMN layout_info JSON DEFAULT NULL
        """)

        conn.commit()
        print("  迁移成功！layout_info 列已添加")
        return True

    except Exception as e:
        print(f"  迁移失败: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def migrate():
    """执行迁移 - 检查所有可能的数据库位置"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 可能的数据库位置
    possible_paths = [
        script_dir / "storage" / "afn.db",           # backend/storage/afn.db
        project_root / "storage" / "afn.db",          # storage/afn.db (项目根目录)
    ]

    print("检查所有可能的数据库位置...")
    migrated_any = False

    for db_path in possible_paths:
        print(f"\n检查: {db_path}")
        if db_path.exists():
            if migrate_db(db_path):
                migrated_any = True

    if not migrated_any:
        print("\n未找到需要迁移的数据库文件")


if __name__ == "__main__":
    migrate()
