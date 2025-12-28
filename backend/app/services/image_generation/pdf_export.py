"""
PDF导出服务

将选中的图片导出为PDF文件，支持：
1. 基础导出：简单的图片列表
2. 漫画导出：一页一图的阅读体验
3. 专业排版导出：根据AI生成的排版方案，将图片按分镜布局排列
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import PDFExportRequest, PDFExportResult, ChapterMangaPDFRequest, ChapterMangaPDFResponse
from ...models.image_config import GeneratedImage
from ...models.novel import ChapterMangaPrompt
from ...core.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# 异步文件操作辅助函数
# ============================================================================

async def async_exists(path: Path) -> bool:
    """异步检查文件是否存在"""
    return await asyncio.to_thread(path.exists)


async def async_mkdir(path: Path, parents: bool = False, exist_ok: bool = False) -> None:
    """异步创建目录"""
    await asyncio.to_thread(path.mkdir, parents=parents, exist_ok=exist_ok)


async def async_stat(path: Path):
    """异步获取文件状态"""
    return await asyncio.to_thread(path.stat)


async def async_glob(path: Path, pattern: str) -> List[Path]:
    """异步glob匹配"""
    return await asyncio.to_thread(lambda: list(path.glob(pattern)))

# 使用统一的路径配置
EXPORT_DIR = settings.exports_dir
IMAGES_ROOT = settings.generated_images_dir

# P2修复: 统一页面尺寸定义，避免在多处重复定义
# 页面尺寸常量（单位：点，1点=1/72英寸）
PAGE_SIZES = {
    "A4": (595.27, 841.89),   # 210x297mm
    "B5": (498.90, 708.66),   # 176x250mm
    "A5": (419.53, 595.27),   # 148x210mm
    "Letter": (612, 792),      # 8.5x11英寸
    "A3": (841.89, 1190.55),  # 297x420mm
}


def get_page_size(size_name: str, default: str = "A4") -> tuple:
    """
    获取页面尺寸（统一入口）

    Args:
        size_name: 页面尺寸名称（A4, A3, B5, A5, Letter）
        default: 默认尺寸

    Returns:
        (width, height) 元组，单位为点
    """
    return PAGE_SIZES.get(size_name, PAGE_SIZES.get(default, PAGE_SIZES["A4"]))

# 中文字体配置
# 默认使用系统字体，如果不可用则回退到Helvetica
_CHINESE_FONT_REGISTERED = False
_CHINESE_FONT_NAME = "Helvetica"  # 默认回退字体
_CHINESE_FONT_BOLD = "Helvetica-Bold"


def _register_chinese_font():
    """注册中文字体（仅执行一次）"""
    global _CHINESE_FONT_REGISTERED, _CHINESE_FONT_NAME, _CHINESE_FONT_BOLD

    if _CHINESE_FONT_REGISTERED:
        return

    _CHINESE_FONT_REGISTERED = True

    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # 尝试注册常见的中文字体
        font_paths = [
            # Windows 字体路径
            ("SimHei", "C:/Windows/Fonts/simhei.ttf"),
            ("SimSun", "C:/Windows/Fonts/simsun.ttc"),
            ("Microsoft YaHei", "C:/Windows/Fonts/msyh.ttc"),
            # Linux 字体路径
            ("WenQuanYi", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            # macOS 字体路径
            ("PingFang", "/System/Library/Fonts/PingFang.ttc"),
        ]

        for font_name, font_path in font_paths:
            if Path(font_path).exists():
                try:
                    pdfmetrics.registerFont(TTFont(font_name, font_path))
                    _CHINESE_FONT_NAME = font_name
                    _CHINESE_FONT_BOLD = font_name  # 中文字体通常没有单独的粗体版本
                    logger.info("成功注册中文字体: %s", font_name)
                    return
                except Exception as e:
                    logger.warning("注册字体 %s 失败: %s", font_name, e)
                    continue

        logger.warning("未找到可用的中文字体，将使用默认字体（中文可能显示为方块）")
    except ImportError:
        logger.warning("无法导入字体模块，使用默认字体")


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

            # 确保导出目录存在（异步）
            await async_mkdir(EXPORT_DIR, parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = request.title or f"漫画导出_{request.project_id}"
            file_name = f"{title}_{timestamp}.pdf"
            file_path = EXPORT_DIR / file_name

            # P2修复: 使用统一的页面尺寸定义
            page_size = get_page_size(request.page_size)

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

                # 添加图片（异步检查文件存在性）
                img_path = IMAGES_ROOT / img.file_path
                if await async_exists(img_path):
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
        """获取项目的导出历史（使用异步文件操作）"""
        export_dir = EXPORT_DIR
        if not await async_exists(export_dir):
            return []

        exports = []
        files = await async_glob(export_dir, f"*{project_id}*.pdf")
        for file in files:
            stat = await async_stat(file)
            exports.append({
                "file_name": file.name,
                "file_path": str(file),
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime),
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
                from reportlab.lib.units import cm, mm
                from reportlab.pdfgen import canvas
                from reportlab.lib.utils import ImageReader
                from PIL import Image as PILImage
            except ImportError:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="PDF生成库未安装，请运行: pip install reportlab pillow",
                )

            # 获取章节所有图片（支持版本过滤）
            query = select(GeneratedImage).where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
            )

            # P1修复: 版本过滤逻辑优化 - 严格按版本过滤，不混入历史数据
            # 如果指定了版本ID，只查询该版本的图片；否则只查询没有版本ID的历史图片
            if request.chapter_version_id is not None:
                query = query.where(
                    GeneratedImage.chapter_version_id == request.chapter_version_id
                )
            else:
                # 未指定版本时，只获取无版本标记的历史图片
                query = query.where(
                    GeneratedImage.chapter_version_id.is_(None)
                )

            result = await self.session.execute(
                query.order_by(GeneratedImage.scene_id, GeneratedImage.created_at)
            )
            images = list(result.scalars().all())

            # 如果指定版本没有图片，尝试回退到历史图片（仅作为降级策略）
            if not images and request.chapter_version_id is not None:
                logger.info(
                    "版本 %s 无图片，尝试回退到历史图片",
                    request.chapter_version_id
                )
                fallback_query = select(GeneratedImage).where(
                    GeneratedImage.project_id == project_id,
                    GeneratedImage.chapter_number == chapter_number,
                    GeneratedImage.chapter_version_id.is_(None),
                ).order_by(GeneratedImage.scene_id, GeneratedImage.created_at)
                result = await self.session.execute(fallback_query)
                images = list(result.scalars().all())

            if not images:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="该章节暂无图片",
                )

            # 确保导出目录存在（异步）
            await async_mkdir(EXPORT_DIR, parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = request.title or f"第{chapter_number}章"
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-")
            file_name = f"manga_{project_id}_ch{chapter_number}_{timestamp}.pdf"
            file_path = EXPORT_DIR / file_name

            # P2修复: 使用统一的页面尺寸定义
            page_size = get_page_size(request.page_size)
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
                if not await async_exists(img_path):
                    logger.warning(f"图片不存在: {img_path}")
                    continue

                try:
                    # 读取图片获取尺寸（异步）
                    pil_img = await asyncio.to_thread(PILImage.open, str(img_path))
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
                    _register_chinese_font()  # 确保字体已注册
                    c.setFont(_CHINESE_FONT_BOLD, 10)
                    c.setFillColorRGB(0.3, 0.3, 0.3)
                    c.drawString(margin, page_height - margin - 10, f"Scene {img.scene_id}")

                    # 绘制提示词（底部）
                    if request.include_prompts and img.prompt:
                        c.setFont(_CHINESE_FONT_NAME, 8)
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
        - 使用页面模板定义的画格坐标
        - 按panel_id精确匹配图片
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

            # 导入页面模板
            from ..manga_prompt.page_templates import get_template

            # 获取章节的漫画提示词（包含排版信息）
            from ...repositories.chapter_repository import ChapterRepository
            chapter_repo = ChapterRepository(self.session)
            chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

            if not chapter or not chapter.manga_prompt:
                # 如果没有排版信息，回退到简单模式
                logger.info("章节无排版信息，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            manga_prompt = chapter.manga_prompt
            scenes_data = manga_prompt.scenes or []
            panels_data = manga_prompt.panels or []

            # 如果没有场景或画格数据，回退到简单模式
            if not scenes_data or not panels_data:
                logger.info("排版信息为空，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            # 获取章节所有图片
            result = await self.session.execute(
                select(GeneratedImage).where(
                    GeneratedImage.project_id == project_id,
                    GeneratedImage.chapter_number == chapter_number,
                ).order_by(GeneratedImage.scene_id, GeneratedImage.created_at)
            )
            all_images = list(result.scalars().all())

            if not all_images:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="该章节暂无图片",
                )

            # 按 panel_id 索引图片（精确匹配）
            # 同时按 scene_id 索引作为后备
            panel_image_map: Dict[str, GeneratedImage] = {}
            scene_image_map: Dict[int, GeneratedImage] = {}

            for img in all_images:
                if img.panel_id and img.panel_id not in panel_image_map:
                    panel_image_map[img.panel_id] = img
                if img.scene_id not in scene_image_map:
                    scene_image_map[img.scene_id] = img

            logger.info(f"图片索引: panel_id={len(panel_image_map)}, scene_id={len(scene_image_map)}")

            # 确保导出目录存在（异步）
            await async_mkdir(EXPORT_DIR, parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"manga_pro_{project_id}_ch{chapter_number}_{timestamp}.pdf"
            file_path = EXPORT_DIR / file_name

            # 获取页面尺寸（从请求参数获取，默认A4）
            page_size_name = request.page_size or "A4"
            page_size = PAGE_SIZES.get(page_size_name, PAGE_SIZES["A4"])
            page_width, page_height = page_size

            # 出血线和安全区域（单位：点）
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

            # 从 scenes 数据中提取页面和模板信息
            # 注意：每个场景的 page_number 都是从1开始的相对页码
            # 所以我们需要按场景组织，每个场景作为独立的页面

            # 按场景组织画格
            scene_panels: Dict[int, List[Dict]] = {}  # scene_id -> panels
            scene_templates: Dict[int, str] = {}  # scene_id -> template_id

            # 从 scenes 中提取模板信息
            for scene in scenes_data:
                scene_id = scene.get("scene_id")
                if scene_id is None:
                    continue
                for page_info in scene.get("pages", []):
                    template_id = page_info.get("template_id")
                    if template_id:
                        scene_templates[scene_id] = template_id
                        break  # 每个场景取第一个模板

            # 从 panels 中提取每个场景的画格
            for panel in panels_data:
                scene_id = panel.get("scene_id")
                if scene_id is not None:
                    if scene_id not in scene_panels:
                        scene_panels[scene_id] = []
                    scene_panels[scene_id].append(panel)

            logger.info(f"场景数据: {len(scene_panels)} 个场景, 模板: {scene_templates}")

            # 如果没有有效的场景数据，回退到简单模式
            if not scene_panels:
                logger.info("无有效场景数据，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            page_count = 0

            # 按场景顺序绘制（每个场景一页）
            for scene_id in sorted(scene_panels.keys()):
                panels = scene_panels[scene_id]
                template_id = scene_templates.get(scene_id)

                # 获取模板
                template = get_template(template_id) if template_id else None

                logger.debug(f"绘制场景 {scene_id}: {len(panels)} 个画格, 模板={template_id}")

                # 绘制页面背景（白色）
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

                # 绘制每个画格
                for panel in panels:
                    panel_id = panel.get("panel_id", "")
                    scene_id = panel.get("scene_id")
                    slot_id = panel.get("slot_id", 1)

                    # 获取图片：优先按 panel_id 匹配，后备按 scene_id
                    img_record = panel_image_map.get(panel_id)
                    if not img_record and scene_id:
                        img_record = scene_image_map.get(scene_id)

                    if not img_record:
                        logger.debug(f"画格 {panel_id} 无图片")
                        continue

                    img_path = IMAGES_ROOT / img_record.file_path
                    if not await async_exists(img_path):
                        logger.warning(f"图片不存在: {img_path}")
                        continue

                    # 从模板获取画格坐标
                    rel_x, rel_y, rel_width, rel_height = 0.0, 0.0, 1.0, 1.0

                    if template:
                        # 根据 slot_id 在模板中查找画格位置
                        for slot in template.panel_slots:
                            if slot.slot_id == slot_id:
                                rel_x = slot.x
                                rel_y = slot.y
                                rel_width = slot.width
                                rel_height = slot.height
                                break
                    else:
                        # 无模板时，根据画格数量简单排版
                        panel_count = len(panels)
                        panel_index = panels.index(panel)
                        if panel_count == 1:
                            rel_x, rel_y, rel_width, rel_height = 0.0, 0.0, 1.0, 1.0
                        elif panel_count == 2:
                            rel_x = 0.0
                            rel_y = 0.5 * panel_index
                            rel_width = 1.0
                            rel_height = 0.48
                        elif panel_count <= 4:
                            col = panel_index % 2
                            row = panel_index // 2
                            rel_x = 0.52 * col
                            rel_y = 0.52 * row
                            rel_width = 0.48
                            rel_height = 0.48
                        else:
                            # 更多画格时使用三行布局
                            col = panel_index % 2
                            row = panel_index // 2
                            rel_x = 0.52 * col
                            rel_y = 0.34 * row
                            rel_width = 0.48
                            rel_height = 0.32

                    # 转换为绝对坐标（PDF坐标系是左下角为原点）
                    panel_x = content_x + rel_x * content_width
                    panel_width = rel_width * content_width - gutter
                    panel_height = rel_height * content_height - gutter
                    # PDF的y坐标是从下往上的，需要转换
                    panel_y = page_height - content_y - rel_y * content_height - panel_height

                    try:
                        # 读取图片（异步）
                        pil_img = await asyncio.to_thread(PILImage.open, str(img_path))
                        img_width, img_height = pil_img.size

                        # 计算图片在格子内的尺寸（保持比例，适配格子）
                        scale_w = panel_width / img_width
                        scale_h = panel_height / img_height

                        # 使用较小的缩放比例（适配模式，确保图片完整显示不被裁剪）
                        scale = min(scale_w, scale_h)

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
                        _register_chinese_font()
                        c.setFont(_CHINESE_FONT_NAME, 10)
                        c.setFillColorRGB(0.5, 0.5, 0.5)
                        c.drawCentredString(
                            panel_x + panel_width / 2,
                            panel_y + panel_height / 2,
                            f"Panel {slot_id}"
                        )

                # 绘制页码
                _register_chinese_font()
                c.setFillColorRGB(0.5, 0.5, 0.5)
                c.setFont(_CHINESE_FONT_NAME, 9)
                c.drawCentredString(page_width / 2, 15, str(page_count + 1))

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

            logger.info(f"专业排版PDF生成完成: {page_count} 页")

            return ChapterMangaPDFResponse(
                success=True,
                file_path=str(file_path),
                file_name=file_name,
                download_url=f"/api/image-generation/export/download/{file_name}",
                page_count=page_count,
            )

        except Exception as e:
            logger.error(f"生成专业漫画PDF失败: {e}", exc_info=True)
            return ChapterMangaPDFResponse(
                success=False,
                error_message=str(e),
            )
