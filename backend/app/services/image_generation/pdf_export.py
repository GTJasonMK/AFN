"""
PDF导出服务

将选中的图片导出为PDF文件，支持：
1. 基础导出：简单的图片列表
2. 漫画导出：一页一图的阅读体验
3. 专业排版导出：根据AI生成的排版方案，将图片按分镜布局排列
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import PDFExportRequest, PDFExportResult, ChapterMangaPDFRequest, ChapterMangaPDFResponse
from ...models.image_config import GeneratedImage
from ...models.novel import ChapterMangaPrompt

logger = logging.getLogger(__name__)

# 计算存储目录路径（与 config.py 中 SQLite 路径计算方式一致）
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # backend/app/services/image_generation -> 项目根目录
STORAGE_DIR = _PROJECT_ROOT / "backend" / "storage"

# PDF导出目录
EXPORT_DIR = STORAGE_DIR / "exports"

# 图片存储根目录
IMAGES_ROOT = STORAGE_DIR / "generated_images"

# 页面尺寸常量（单位：点，1点=1/72英寸）
PAGE_SIZES = {
    "A4": (595.27, 841.89),   # 210x297mm
    "B5": (498.90, 708.66),   # 176x250mm
    "A5": (419.53, 595.27),   # 148x210mm
    "Letter": (612, 792),      # 8.5x11英寸
}


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

    async def generate_chapter_manga_pdf(
        self,
        project_id: str,
        chapter_number: int,
        request: ChapterMangaPDFRequest,
    ) -> ChapterMangaPDFResponse:
        """
        生成章节漫画PDF（一页一张图片，像正常漫画阅读体验）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            request: 生成请求

        Returns:
            ChapterMangaPDFResponse: 生成结果
        """
        try:
            # 导入reportlab
            try:
                from reportlab.lib.pagesizes import A4, A3, letter
                from reportlab.lib.units import cm, mm
                from reportlab.pdfgen import canvas
                from reportlab.lib.utils import ImageReader
                from PIL import Image as PILImage
            except ImportError:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="PDF生成库未安装，请运行: pip install reportlab pillow",
                )

            # 获取章节所有图片
            result = await self.session.execute(
                select(GeneratedImage)
                .where(
                    GeneratedImage.project_id == project_id,
                    GeneratedImage.chapter_number == chapter_number,
                )
                .order_by(GeneratedImage.scene_id, GeneratedImage.created_at)
            )
            images = list(result.scalars().all())

            if not images:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="该章节暂无图片",
                )

            # 确保导出目录存在
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = request.title or f"第{chapter_number}章"
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-")
            file_name = f"manga_{project_id}_ch{chapter_number}_{timestamp}.pdf"
            file_path = EXPORT_DIR / file_name

            # 选择页面大小
            page_sizes = {
                "A4": A4,
                "A3": A3,
                "Letter": letter,
            }
            page_size = page_sizes.get(request.page_size, A4)
            page_width, page_height = page_size

            # 创建PDF
            c = canvas.Canvas(str(file_path), pagesize=page_size)

            # 设置元数据
            c.setTitle(title)
            c.setAuthor("AFN Novel Writing Assistant")

            page_count = 0

            # 按场景分组，每个场景的图片连续排列
            for img in images:
                img_path = IMAGES_ROOT / img.file_path
                if not img_path.exists():
                    logger.warning(f"图片不存在: {img_path}")
                    continue

                try:
                    # 读取图片获取尺寸
                    pil_img = PILImage.open(str(img_path))
                    img_width, img_height = pil_img.size

                    # 计算图片在页面上的尺寸（保持比例，最大化显示）
                    # 留出边距
                    margin = 1 * cm
                    available_width = page_width - 2 * margin
                    available_height = page_height - 2 * margin

                    # 如果需要显示提示词，留出底部空间
                    if request.include_prompts:
                        available_height -= 2 * cm

                    # 计算缩放比例
                    scale_w = available_width / img_width
                    scale_h = available_height / img_height
                    scale = min(scale_w, scale_h)

                    # 计算绘制尺寸和位置（居中）
                    draw_width = img_width * scale
                    draw_height = img_height * scale
                    x = (page_width - draw_width) / 2
                    y = (page_height - draw_height) / 2

                    if request.include_prompts:
                        y += 1 * cm  # 向上偏移，给提示词留空间

                    # 绘制图片
                    c.drawImage(
                        str(img_path),
                        x, y,
                        width=draw_width,
                        height=draw_height,
                        preserveAspectRatio=True,
                    )

                    # 绘制场景标签（左上角）
                    c.setFont("Helvetica-Bold", 10)
                    c.setFillColorRGB(0.3, 0.3, 0.3)
                    c.drawString(margin, page_height - margin - 10, f"Scene {img.scene_id}")

                    # 绘制提示词（底部）
                    if request.include_prompts and img.prompt:
                        c.setFont("Helvetica", 8)
                        c.setFillColorRGB(0.5, 0.5, 0.5)
                        # 截断过长的提示词
                        prompt_text = img.prompt[:150] + "..." if len(img.prompt) > 150 else img.prompt
                        # 简单换行处理
                        max_chars = int(available_width / 4)  # 大约每4个点一个字符
                        lines = [prompt_text[i:i+max_chars] for i in range(0, len(prompt_text), max_chars)]
                        for i, line in enumerate(lines[:3]):  # 最多3行
                            c.drawString(margin, margin + (2 - i) * 12, line)

                    # 新页面
                    c.showPage()
                    page_count += 1

                except Exception as e:
                    logger.warning(f"处理图片失败: {img_path}, {e}")
                    continue

            if page_count == 0:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="没有有效的图片可以导出",
                )

            # 保存PDF
            c.save()

            return ChapterMangaPDFResponse(
                success=True,
                file_path=str(file_path),
                file_name=file_name,
                download_url=f"/api/image-generation/export/download/{file_name}",
                page_count=page_count,
            )

        except Exception as e:
            logger.error(f"生成章节漫画PDF失败: {e}")
            return ChapterMangaPDFResponse(
                success=False,
                error_message=str(e),
            )

    async def generate_professional_manga_pdf(
        self,
        project_id: str,
        chapter_number: int,
        request: ChapterMangaPDFRequest,
    ) -> ChapterMangaPDFResponse:
        """
        生成专业排版的漫画PDF

        根据AI生成的排版方案，将图片按分镜布局排列在页面上。
        支持：
        - 多图排版（一页多个分镜格子）
        - 不同大小的格子（hero/major/standard/minor）
        - 出血线和安全区域
        - 专业的页面边距

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            request: 生成请求

        Returns:
            ChapterMangaPDFResponse: 生成结果
        """
        try:
            # 导入依赖
            try:
                from reportlab.lib.units import mm
                from reportlab.pdfgen import canvas
                from PIL import Image as PILImage
            except ImportError:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="PDF生成库未安装，请运行: pip install reportlab pillow",
                )

            # 获取章节的漫画提示词（包含排版信息）
            from ...repositories.chapter_repository import ChapterRepository
            chapter_repo = ChapterRepository(self.session)
            chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

            if not chapter or not chapter.manga_prompt:
                # 如果没有排版信息，回退到简单模式
                logger.info("章节无排版信息，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            manga_prompt = chapter.manga_prompt
            layout_info = manga_prompt.layout_info
            scenes_data = manga_prompt.scenes or []

            # 如果没有排版信息，回退到简单模式
            if not layout_info:
                logger.info("排版信息为空，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            # 获取章节所有图片
            result = await self.session.execute(
                select(GeneratedImage)
                .where(
                    GeneratedImage.project_id == project_id,
                    GeneratedImage.chapter_number == chapter_number,
                )
                .order_by(GeneratedImage.scene_id, GeneratedImage.created_at)
            )
            all_images = list(result.scalars().all())

            if not all_images:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="该章节暂无图片",
                )

            # 按场景ID分组图片（取每个场景的第一张）
            scene_images: Dict[int, GeneratedImage] = {}
            for img in all_images:
                if img.scene_id not in scene_images:
                    scene_images[img.scene_id] = img

            # 确保导出目录存在
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"manga_pro_{project_id}_ch{chapter_number}_{timestamp}.pdf"
            file_path = EXPORT_DIR / file_name

            # 获取页面尺寸
            page_size_name = layout_info.get("page_size", "A4")
            page_size = PAGE_SIZES.get(page_size_name, PAGE_SIZES["A4"])
            page_width, page_height = page_size

            # 出血线和安全区域（单位：点）
            bleed_margin = 3 * mm  # 出血线 3mm
            safe_margin = 5 * mm   # 安全区域 5mm
            gutter = 2 * mm        # 格子间距 2mm

            # 可用区域（减去安全边距）
            content_x = safe_margin
            content_y = safe_margin
            content_width = page_width - 2 * safe_margin
            content_height = page_height - 2 * safe_margin

            # 创建PDF
            c = canvas.Canvas(str(file_path), pagesize=page_size)
            c.setTitle(f"第{chapter_number}章 漫画")
            c.setAuthor("AFN Novel Writing Assistant")

            page_count = 0

            # 从场景数据中提取排版信息并绘制
            # 按页码分组场景
            pages_data: Dict[int, List[Dict]] = {}
            for scene in scenes_data:
                panel_info = scene.get("panel_info")
                if not panel_info:
                    continue

                page_num = panel_info.get("page_number", 1)
                if page_num not in pages_data:
                    pages_data[page_num] = []
                pages_data[page_num].append({
                    "scene_id": scene.get("scene_id"),
                    "panel_info": panel_info,
                })

            # 如果没有页面数据，使用简单布局
            if not pages_data:
                logger.info("无页面排版数据，使用简单布局")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            # 按页码顺序绘制
            for page_num in sorted(pages_data.keys()):
                panels = pages_data[page_num]

                # 绘制页面背景（白色）
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

                # 绘制每个格子
                for panel_data in panels:
                    scene_id = panel_data["scene_id"]
                    panel = panel_data["panel_info"]

                    # 获取场景图片
                    if scene_id not in scene_images:
                        logger.warning(f"场景 {scene_id} 无图片")
                        continue

                    img_record = scene_images[scene_id]
                    img_path = IMAGES_ROOT / img_record.file_path

                    if not img_path.exists():
                        logger.warning(f"图片不存在: {img_path}")
                        continue

                    # 计算格子位置（相对坐标转绝对坐标）
                    # panel_info中的x,y,width,height是0-1的相对值
                    rel_x = panel.get("x", 0)
                    rel_y = panel.get("y", 0)
                    rel_width = panel.get("width", 0.5)
                    rel_height = panel.get("height", 0.5)

                    # 转换为绝对坐标（注意PDF坐标系是左下角为原点）
                    panel_x = content_x + rel_x * content_width
                    panel_width = rel_width * content_width - gutter
                    panel_height = rel_height * content_height - gutter
                    # PDF的y坐标是从下往上的，需要转换
                    panel_y = page_height - content_y - rel_y * content_height - panel_height

                    # 绘制格子边框（可选）
                    c.setStrokeColorRGB(0.9, 0.9, 0.9)
                    c.setLineWidth(0.5)
                    c.rect(panel_x, panel_y, panel_width, panel_height, fill=False, stroke=True)

                    try:
                        # 读取图片
                        pil_img = PILImage.open(str(img_path))
                        img_width, img_height = pil_img.size

                        # 计算图片在格子内的尺寸（保持比例，填充格子）
                        scale_w = panel_width / img_width
                        scale_h = panel_height / img_height

                        # 使用较大的缩放比例（填充模式）
                        scale = max(scale_w, scale_h)

                        draw_width = img_width * scale
                        draw_height = img_height * scale

                        # 计算居中偏移
                        offset_x = (panel_width - draw_width) / 2
                        offset_y = (panel_height - draw_height) / 2

                        # 设置裁剪区域（只显示格子内的部分）
                        c.saveState()
                        path = c.beginPath()
                        path.rect(panel_x, panel_y, panel_width, panel_height)
                        c.clipPath(path, stroke=0)

                        # 绘制图片
                        c.drawImage(
                            str(img_path),
                            panel_x + offset_x,
                            panel_y + offset_y,
                            width=draw_width,
                            height=draw_height,
                            preserveAspectRatio=True,
                        )

                        c.restoreState()

                        # 绘制格子边框（深色）
                        c.setStrokeColorRGB(0.2, 0.2, 0.2)
                        c.setLineWidth(1)
                        c.rect(panel_x, panel_y, panel_width, panel_height, fill=False, stroke=True)

                    except Exception as e:
                        logger.warning(f"绘制图片失败: {img_path}, {e}")
                        # 绘制占位符
                        c.setFillColorRGB(0.95, 0.95, 0.95)
                        c.rect(panel_x, panel_y, panel_width, panel_height, fill=True, stroke=True)
                        c.setFillColorRGB(0.5, 0.5, 0.5)
                        c.drawCentredString(
                            panel_x + panel_width / 2,
                            panel_y + panel_height / 2,
                            f"Scene {scene_id}"
                        )

                # 绘制页码
                c.setFillColorRGB(0.5, 0.5, 0.5)
                c.setFont("Helvetica", 9)
                c.drawCentredString(page_width / 2, 15, str(page_num))

                # 新页面
                c.showPage()
                page_count += 1

            if page_count == 0:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="没有有效的页面可以导出",
                )

            # 保存PDF
            c.save()

            return ChapterMangaPDFResponse(
                success=True,
                file_path=str(file_path),
                file_name=file_name,
                download_url=f"/api/image-generation/export/download/{file_name}",
                page_count=page_count,
            )

        except Exception as e:
            logger.error(f"生成专业漫画PDF失败: {e}")
            return ChapterMangaPDFResponse(
                success=False,
                error_message=str(e),
            )
