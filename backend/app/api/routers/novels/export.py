"""
章节导出路由

处理小说章节的导出功能（支持TXT和Markdown格式）。
"""

import logging
from typing import Dict, List
from urllib.parse import quote
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_novel_service,
)
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{project_id}/export")
async def export_chapters(
    project_id: str,
    format: str = "txt",
    novel_service: NovelService = Depends(get_novel_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> StreamingResponse:
    """导出所有已完成的章节内容"""
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取项目完整信息
    project_schema = await novel_service.get_project_schema(project_id, desktop_user.id)

    # 收集所有已选择版本的章节
    completed_chapters = []
    outlines_map = {outline.chapter_number: outline for outline in project.outlines}

    for chapter in sorted(project.chapters, key=lambda x: x.chapter_number):
        if chapter.selected_version and chapter.selected_version.content:
            outline = outlines_map.get(chapter.chapter_number)
            completed_chapters.append({
                "chapter_number": chapter.chapter_number,
                "title": outline.title if outline else f"第{chapter.chapter_number}章",
                "content": chapter.selected_version.content,
            })

    if not completed_chapters:
        raise ResourceNotFoundError("可导出章节", project_id)

    # 获取小说标题
    novel_title = project.title or "未命名小说"
    blueprint_title = project_schema.blueprint.title if project_schema.blueprint else None
    if blueprint_title:
        novel_title = blueprint_title

    # 生成导出内容
    if format.lower() == "markdown" or format.lower() == "md":
        content = _generate_markdown_export(novel_title, completed_chapters)
        filename = f"{novel_title}.md"
        media_type = "text/markdown"
    else:  # 默认为 txt
        content = _generate_txt_export(novel_title, completed_chapters)
        filename = f"{novel_title}.txt"
        media_type = "text/plain"

    # 创建字节流
    buffer = BytesIO(content.encode("utf-8"))

    # 对文件名进行 URL 编码以支持中文（RFC 2231）
    encoded_filename = quote(filename.encode('utf-8'))

    logger.info(
        "用户 %s 导出项目 %s，格式：%s，章节数：%s",
        desktop_user.id,
        project_id,
        format,
        len(completed_chapters),
    )

    return StreamingResponse(
        buffer,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "Content-Type": f"{media_type}; charset=utf-8",
        },
    )


def _generate_txt_export(novel_title: str, chapters: List[Dict]) -> str:
    """生成 TXT 格式的导出内容"""
    lines = []

    # 添加标题和元信息
    lines.append("=" * 60)
    lines.append(novel_title)
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"导出时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append(f"总章节数：{len(chapters)}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    # 添加章节内容
    for chapter in chapters:
        lines.append("")
        lines.append(f"第{chapter['chapter_number']}章 {chapter['title']}")
        lines.append("-" * 60)
        lines.append("")
        lines.append(chapter["content"])
        lines.append("")
        lines.append("")

    return "\n".join(lines)


def _generate_markdown_export(novel_title: str, chapters: List[Dict]) -> str:
    """生成 Markdown 格式的导出内容"""
    lines = []

    # 添加标题和元信息
    lines.append(f"# {novel_title}")
    lines.append("")
    lines.append(f"> 导出时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M')}")
    lines.append(f"> 总章节数：{len(chapters)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 添加目录
    lines.append("## 目录")
    lines.append("")
    for chapter in chapters:
        lines.append(f"- [第{chapter['chapter_number']}章 {chapter['title']}](#第{chapter['chapter_number']}章)")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 添加章节内容
    for chapter in chapters:
        lines.append(f"## 第{chapter['chapter_number']}章 {chapter['title']}")
        lines.append("")
        lines.append(chapter["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
