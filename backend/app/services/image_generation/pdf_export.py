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

            # 从 panels 数据中按页码分组
            # 注意：panels 使用 page_number 字段来标识页码

            # 按页码组织画格
            page_panels: Dict[int, List[Dict]] = {}  # page_number -> panels

            # 从 panels 中提取每页的画格
            for panel in panels_data:
                page_number = panel.get("page_number")
                if page_number is not None:
                    if page_number not in page_panels:
                        page_panels[page_number] = []
                    page_panels[page_number].append(panel)

            logger.info(f"页面数据: {len(page_panels)} 页, 总画格: {len(panels_data)}")

            # 如果没有有效的页面数据，回退到简单模式
            if not page_panels:
                logger.info("无有效页面数据，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            page_count = 0

            # 按页码顺序绘制（每个page_number对应一页PDF）
            for page_number in sorted(page_panels.keys()):
                panels = page_panels[page_number]

                logger.debug(f"绘制第 {page_number} 页: {len(panels)} 个画格")

                # 绘制页面背景（白色）
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

                # ========== 智能漫画排版算法 ==========
                # 充分利用画格的所有元数据：size, shape, aspect_ratio, is_key_panel, shot_type

                # size 对应的基础高度比例
                SIZE_HEIGHT_RATIO = {
                    "full": 1.0,      # 整页
                    "spread": 1.0,    # 跨页
                    "half": 0.45,     # 半页
                    "large": 0.32,    # 大格
                    "medium": 0.22,   # 中格
                    "small": 0.15,    # 小格
                }

                # shape 对应的宽高比调整
                SHAPE_ASPECT = {
                    "rectangle": 1.5,    # 标准横向
                    "square": 1.0,       # 正方形
                    "vertical": 0.7,     # 竖长
                    "horizontal": 2.0,   # 横长
                    "irregular": 1.3,    # 不规则（默认偏横）
                    "borderless": 1.5,   # 无边框
                }

                # shot_type 对应的尺寸加成
                SHOT_TYPE_MODIFIER = {
                    "establishing": 1.2,     # 全景建立镜头，加大
                    "long": 1.1,             # 远景，稍大
                    "bird_eye": 1.15,        # 鸟瞰，加大
                    "worm_eye": 1.1,         # 仰视
                    "medium": 1.0,           # 中景，标准
                    "over_shoulder": 0.95,   # 过肩
                    "close_up": 0.9,         # 近景，可以小一些
                    "extreme_close_up": 0.85, # 特写，更小但突出
                    "pov": 0.95,             # 主观视角
                }

                # 预处理：为每个画格计算理想尺寸
                panel_specs = []
                for panel in panels:
                    size = panel.get("size", "medium")
                    shape = panel.get("shape", "rectangle")
                    aspect_ratio = panel.get("aspect_ratio", "4:3")
                    is_key = panel.get("is_key_panel", False)
                    shot_type = panel.get("shot_type", "medium")

                    # 基础高度
                    base_height = SIZE_HEIGHT_RATIO.get(size, 0.22)

                    # shot_type 修正
                    shot_modifier = SHOT_TYPE_MODIFIER.get(shot_type, 1.0)
                    height = base_height * shot_modifier

                    # 关键画格加成 15%
                    if is_key:
                        height *= 1.15

                    # 根据 shape 和 aspect_ratio 计算宽度
                    shape_aspect = SHAPE_ASPECT.get(shape, 1.5)

                    # 解析 aspect_ratio (如 "16:9" -> 1.78)
                    try:
                        w, h = aspect_ratio.split(":")
                        ar = float(w) / float(h)
                    except:
                        ar = 1.33  # 默认 4:3

                    # 综合 shape 和 aspect_ratio 决定宽度倾向
                    # ar > 1 表示横向，ar < 1 表示纵向
                    if ar >= 1.7:  # 16:9 或更宽
                        width_tendency = 1.0  # 倾向占满宽度
                    elif ar >= 1.2:  # 4:3 左右
                        width_tendency = 0.48  # 可以并排
                    else:  # 纵向画格
                        width_tendency = 0.35  # 更窄

                    # half/full/spread/large 通常占满宽度
                    if size in ["full", "spread", "half", "large"]:
                        width_tendency = max(width_tendency, 0.65)

                    panel_specs.append({
                        "panel": panel,
                        "height": height,
                        "width_tendency": width_tendency,
                        "is_key": is_key,
                        "aspect_ratio": ar,
                    })

                # 行填充布局算法
                panel_layouts = []
                current_y = 0.0
                row_panels = []
                row_width_used = 0.0
                row_height = 0.0

                for spec in panel_specs:
                    width = spec["width_tendency"]
                    height = spec["height"]

                    # 检查当前行是否能容纳
                    if row_width_used + width > 1.02:
                        # 完成当前行
                        if row_panels:
                            # 计算实际分配：按比例分配剩余空间
                            total_width = sum(rp["width"] for rp in row_panels)
                            scale = 0.98 / total_width if total_width > 0 else 1.0
                            x_offset = 0.01  # 1% 左边距

                            for rp in row_panels:
                                actual_width = rp["width"] * scale
                                rp["final_x"] = x_offset
                                rp["final_y"] = current_y
                                rp["final_width"] = actual_width - 0.01  # 留间距
                                rp["final_height"] = row_height
                                x_offset += actual_width

                            panel_layouts.extend(row_panels)

                        # 新行
                        current_y += row_height + 0.015
                        row_panels = []
                        row_width_used = 0.0
                        row_height = 0.0

                    # 添加到当前行
                    row_panels.append({
                        "spec": spec,
                        "width": width,
                    })
                    row_width_used += width + 0.02
                    row_height = max(row_height, height)

                # 处理最后一行
                if row_panels:
                    total_width = sum(rp["width"] for rp in row_panels)
                    scale = 0.98 / total_width if total_width > 0 else 1.0
                    x_offset = 0.01

                    for rp in row_panels:
                        actual_width = rp["width"] * scale
                        rp["final_x"] = x_offset
                        rp["final_y"] = current_y
                        rp["final_width"] = actual_width - 0.01
                        rp["final_height"] = row_height
                        x_offset += actual_width

                    panel_layouts.extend(row_panels)

                # 计算总高度并缩放
                total_height = current_y + row_height
                if total_height > 0.98:
                    scale_factor = 0.96 / total_height
                    for pl in panel_layouts:
                        pl["final_y"] *= scale_factor
                        pl["final_height"] *= scale_factor

                logger.debug(f"页面 {page_number}: {len(panel_layouts)} 个画格布局完成，总高度={total_height:.2f}")

                # ========== 绘制画格 ==========
                for pl in panel_layouts:
                    spec = pl["spec"]
                    panel = spec["panel"]
                    panel_id = panel.get("panel_id", "")
                    panel_number = panel.get("panel_number", 1)
                    is_key = spec["is_key"]

                    # 获取布局坐标
                    rel_x = pl["final_x"]
                    rel_y = pl["final_y"]
                    rel_width = pl["final_width"]
                    rel_height = pl["final_height"]

                    # 获取图片
                    img_record = panel_image_map.get(panel_id)

                    if not img_record:
                        logger.debug(f"画格 {panel_id} 无图片")
                        continue

                    img_path = IMAGES_ROOT / img_record.file_path
                    if not await async_exists(img_path):
                        logger.warning(f"图片不存在: {img_path}")
                        continue

                    # 转换为绝对坐标
                    panel_x = content_x + rel_x * content_width
                    panel_width = rel_width * content_width - gutter
                    panel_height = rel_height * content_height - gutter
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

                        # 绘制格子边框
                        # 关键画格使用更粗的边框
                        if is_key:
                            c.setStrokeColorRGB(0.1, 0.1, 0.1)  # 更深的颜色
                            c.setLineWidth(2.5)  # 更粗的边框
                        else:
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
                            f"Panel {panel_number}"
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
