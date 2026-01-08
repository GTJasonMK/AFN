"""
修复已分析项目的 real_summary 字段

对于已完成分析但 real_summary 为空的章节，
从 ChapterOutline.summary 复制数据到 Chapter.real_summary
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.models.novel import NovelProject, Chapter, ChapterOutline


async def fix_real_summary():
    """修复所有项目的 real_summary 字段"""
    # 创建数据库连接（存储目录在项目根目录）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(project_root, "storage", "afn.db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 获取所有已导入且分析完成的项目
        result = await session.execute(
            select(NovelProject)
            .where(NovelProject.is_imported == True)
            .where(NovelProject.import_analysis_status == 'completed')
        )
        projects = result.scalars().all()

        print(f"找到 {len(projects)} 个已完成分析的导入项目")

        for project in projects:
            print(f"\n处理项目: {project.title} (ID: {project.id})")

            # 获取所有章节
            chapters_result = await session.execute(
                select(Chapter)
                .where(Chapter.project_id == project.id)
                .order_by(Chapter.chapter_number)
            )
            chapters = chapters_result.scalars().all()

            # 获取所有章节大纲
            outlines_result = await session.execute(
                select(ChapterOutline)
                .where(ChapterOutline.project_id == project.id)
            )
            outlines = {o.chapter_number: o for o in outlines_result.scalars().all()}

            updated_count = 0
            for chapter in chapters:
                # 检查 real_summary 是否为空
                if not chapter.real_summary or not chapter.real_summary.strip():
                    # 从大纲中获取摘要
                    outline = outlines.get(chapter.chapter_number)
                    if outline and outline.summary and outline.summary.strip():
                        # 排除占位符
                        if outline.summary != "（导入章节，待分析）":
                            chapter.real_summary = outline.summary
                            updated_count += 1
                            print(f"  章节 {chapter.chapter_number}: 已更新 real_summary")

            if updated_count > 0:
                await session.commit()
                print(f"  共更新 {updated_count} 个章节")
            else:
                print(f"  无需更新")

    await engine.dispose()
    print("\n修复完成!")


if __name__ == "__main__":
    asyncio.run(fix_real_summary())
