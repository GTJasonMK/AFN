"""
PDF导出服务

将选中的图片导出为PDF文件，支持自定义布局和样式。
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import PDFExportRequest, PDFExportResult
from ...models.image_config import GeneratedImage
from ...core.config import settings

logger = logging.getLogger(__name__)

# PDF导出目录
EXPORT_DIR = Path(settings.STORAGE_DIR) / "exports"

# 图片存储根目录
IMAGES_ROOT = Path(settings.STORAGE_DIR) / "generated_images"


class PDFExportService:
    """PDF导出服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_images_to_pdf(
        self,
        request: PDFExportRequest,
    ) -> PDFExportResult:
        """
        将图片导出为PDF

        Args:
            request: 导出请求

        Returns:
            PDFExportResult: 导出结果
        """
        try:
            # 导入reportlab（PDF生成库）
            try:
                from reportlab.lib.pagesizes import A4, A3, letter
                from reportlab.lib.units import cm
                from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer, PageBreak
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.pdfbase import pdfmetrics
                from reportlab.pdfbase.ttfonts import TTFont
            except ImportError:
                return PDFExportResult(
                    success=False,
                    error_message="PDF生成库未安装，请运行: pip install reportlab",
                )

            # 获取图片记录
            result = await self.session.execute(
                select(GeneratedImage)
                .where(GeneratedImage.id.in_(request.image_ids))
                .order_by(GeneratedImage.chapter_number, GeneratedImage.scene_id)
            )
            images = list(result.scalars().all())

            if not images:
                return PDFExportResult(
                    success=False,
                    error_message="未找到要导出的图片",
                )

            # 确保导出目录存在
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = request.title or f"漫画导出_{request.project_id}"
            file_name = f"{title}_{timestamp}.pdf"
            file_path = EXPORT_DIR / file_name

            # 选择页面大小
            page_sizes = {
                "A4": A4,
                "A3": A3,
                "Letter": letter,
            }
            page_size = page_sizes.get(request.page_size, A4)

            # 创建PDF文档
            doc = SimpleDocTemplate(
                str(file_path),
                pagesize=page_size,
                leftMargin=1.5 * cm,
                rightMargin=1.5 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
            )

            # 准备样式
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=20,
                alignment=1,  # 居中
            )
            prompt_style = ParagraphStyle(
                'PromptStyle',
                parent=styles['Normal'],
                fontSize=9,
                textColor='gray',
                spaceAfter=10,
            )
            scene_style = ParagraphStyle(
                'SceneStyle',
                parent=styles['Heading2'],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=5,
            )

            # 构建文档内容
            story = []

            # 添加标题
            story.append(Paragraph(title, title_style))
            story.append(Spacer(1, 20))

            # 计算图片尺寸
            page_width = page_size[0] - 3 * cm  # 减去左右边距
            page_height = page_size[1] - 4 * cm  # 减去上下边距

            if request.images_per_page == 1:
                img_width = page_width * 0.9
                img_height = page_height * 0.7
            elif request.images_per_page == 2:
                img_width = page_width * 0.9
                img_height = page_height * 0.4
            else:  # 3-4张
                img_width = page_width * 0.45
                img_height = page_height * 0.35

            # 添加图片
            current_chapter = None
            images_on_page = 0

            for img in images:
                # 章节标题
                if img.chapter_number != current_chapter:
                    if current_chapter is not None:
                        story.append(PageBreak())
                        images_on_page = 0
                    current_chapter = img.chapter_number
                    story.append(Paragraph(f"第 {img.chapter_number} 章", scene_style))

                # 场景标题
                story.append(Paragraph(f"场景 {img.scene_id}", prompt_style))

                # 添加图片
                img_path = IMAGES_ROOT / img.file_path
                if img_path.exists():
                    try:
                        pdf_image = Image(str(img_path), width=img_width, height=img_height)
                        pdf_image.hAlign = 'CENTER'
                        story.append(pdf_image)
                    except Exception as e:
                        logger.warning(f"添加图片失败: {img_path}, {e}")
                        story.append(Paragraph(f"[图片加载失败: {img.file_name}]", prompt_style))

                # 添加提示词
                if request.include_prompts and img.prompt:
                    # 截断过长的提示词
                    prompt_text = img.prompt[:200] + "..." if len(img.prompt) > 200 else img.prompt
                    story.append(Paragraph(f"Prompt: {prompt_text}", prompt_style))

                story.append(Spacer(1, 10))
                images_on_page += 1

                # 换页
                if images_on_page >= request.images_per_page:
                    story.append(PageBreak())
                    images_on_page = 0

            # 生成PDF
            doc.build(story)

            return PDFExportResult(
                success=True,
                file_path=str(file_path),
                file_name=file_name,
            )

        except Exception as e:
            logger.error(f"PDF导出失败: {e}")
            return PDFExportResult(
                success=False,
                error_message=str(e),
            )

    async def get_export_history(self, project_id: str) -> List[dict]:
        """获取项目的导出历史"""
        export_dir = EXPORT_DIR
        if not export_dir.exists():
            return []

        exports = []
        for file in export_dir.glob(f"*{project_id}*.pdf"):
            exports.append({
                "file_name": file.name,
                "file_path": str(file),
                "file_size": file.stat().st_size,
                "created_at": datetime.fromtimestamp(file.stat().st_ctime),
            })

        return sorted(exports, key=lambda x: x["created_at"], reverse=True)
