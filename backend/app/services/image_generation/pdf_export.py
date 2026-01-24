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


def get_export_dir() -> Path:
    """获取导出目录（支持热更新）"""
    return settings.exports_dir


def get_images_root() -> Path:
    """获取图片根目录（支持热更新）"""
    return settings.generated_images_dir

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

    async def _ensure_export_dir(self) -> None:
        """确保导出目录存在"""
        await async_mkdir(get_export_dir(), parents=True, exist_ok=True)

    def _build_export_file(self, prefix: str, project_id: str, chapter_number: int) -> tuple:
        """生成导出文件名与路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{prefix}_{project_id}_ch{chapter_number}_{timestamp}.pdf"
        return file_name, get_export_dir() / file_name

    def _create_canvas(self, file_path: Path, title: str, page_size: tuple):
        """创建PDF画布并写入元数据"""
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(str(file_path), pagesize=page_size)
        c.setTitle(title)
        c.setAuthor("AFN Novel Writing Assistant")
        return c

    async def _fetch_chapter_images(
        self,
        project_id: str,
        chapter_number: int,
        chapter_version_id: Optional[int],
        created_at_desc: bool = False,
        fallback_log: Optional[str] = None,
    ) -> List[GeneratedImage]:
        """获取章节图片（支持版本过滤与回退）"""
        query = select(GeneratedImage).where(
            GeneratedImage.project_id == project_id,
            GeneratedImage.chapter_number == chapter_number,
        )

        if chapter_version_id is not None:
            query = query.where(
                GeneratedImage.chapter_version_id == chapter_version_id
            )

        created_at_order = (
            GeneratedImage.created_at.desc()
            if created_at_desc
            else GeneratedImage.created_at
        )
        result = await self.session.execute(
            query.order_by(GeneratedImage.scene_id, created_at_order)
        )
        images = list(result.scalars().all())

        if not images and chapter_version_id is not None:
            if fallback_log:
                logger.info(fallback_log, chapter_version_id)
            fallback_query = select(GeneratedImage).where(
                GeneratedImage.project_id == project_id,
                GeneratedImage.chapter_number == chapter_number,
                GeneratedImage.chapter_version_id.is_(None),
            ).order_by(GeneratedImage.scene_id, created_at_order)
            result = await self.session.execute(fallback_query)
            images = list(result.scalars().all())

        return images

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
            await async_mkdir(get_export_dir(), parents=True, exist_ok=True)

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title = request.title or f"漫画导出_{request.project_id}"
            # Bug 17 修复: 过滤文件名中的危险字符，防止路径遍历攻击
            safe_title = "".join(c for c in title if c.isalnum() or c in " _-")
            file_name = f"{safe_title}_{timestamp}.pdf"
            file_path = get_export_dir() / file_name

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
                img_path = get_images_root() / img.file_path
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
        export_dir = get_export_dir()
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
            images = await self._fetch_chapter_images(
                project_id=project_id,
                chapter_number=chapter_number,
                chapter_version_id=request.chapter_version_id,
                created_at_desc=False,
                fallback_log="版本 %s 无图片，尝试回退到历史图片",
            )

            if not images:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="该章节暂无图片",
                )

            # 确保导出目录存在（异步）
            await self._ensure_export_dir()

            # 生成文件名
            title = request.title or f"第{chapter_number}章"
            file_name, file_path = self._build_export_file(
                "manga",
                project_id,
                chapter_number,
            )

            # P2修复: 使用统一的页面尺寸定义
            page_size = get_page_size(request.page_size)
            page_width, page_height = page_size

            # 创建PDF
            c = self._create_canvas(file_path, title, page_size)

            page_count = 0

            # 按场景分组，每个场景的图片连续排列
            for img in images:
                img_path = get_images_root() / img.file_path
                if not await async_exists(img_path):
                    logger.warning(f"图片不存在: {img_path}")
                    continue

                try:
                    # 读取图片获取尺寸（异步），立即关闭释放资源
                    def get_image_size(path):
                        with PILImage.open(path) as img:
                            return img.size
                    img_width, img_height = await asyncio.to_thread(get_image_size, str(img_path))

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
        生成专业排版的漫画PDF（基于row_id的精确布局）

        使用完整的排版数据进行布局：
        - row_id: 画格所在行号（从1开始）
        - row_span: 跨越行数（支持纵向跨行）
        - width_ratio: 宽度占比（full/two_thirds/half/third）
        - gutter_horizontal/gutter_vertical: 页面级别的间距配置

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
            panels_data = manga_prompt.panels or []
            # scenes字段存储的是pages数据，包含gutter信息
            pages_info = manga_prompt.scenes or []

            # 如果没有画格数据，回退到简单模式
            if not panels_data:
                logger.info("排版信息为空，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            # 获取章节所有图片
            # Bug 20 修复: 添加章节版本过滤，与简单模式保持一致
            all_images = await self._fetch_chapter_images(
                project_id=project_id,
                chapter_number=chapter_number,
                chapter_version_id=request.chapter_version_id,
                created_at_desc=True,
                fallback_log="专业模式: 版本 %s 无图片，尝试回退到历史图片",
            )

            if not all_images:
                return ChapterMangaPDFResponse(
                    success=False,
                    error_message="该章节暂无图片",
                )

            # Bug 32 修复: 按 panel_id 索引图片，由于排序为 created_at.desc()，
            # 第一个遇到的是最新图片，后续重复的 panel_id 被忽略
            panel_image_map: Dict[str, GeneratedImage] = {}
            # 整页图片索引（按页码）- 支持整页生成功能
            page_image_map: Dict[int, GeneratedImage] = {}

            for img in all_images:
                # 整页图片：image_type='page' 且 panel_id 格式为 "page{N}"
                if img.image_type == 'page' and img.panel_id and img.panel_id.startswith('page'):
                    try:
                        pn = int(img.panel_id[4:])  # 从 "page1" 提取页码
                        if pn not in page_image_map:
                            page_image_map[pn] = img
                    except (ValueError, IndexError):
                        pass
                elif img.panel_id and img.panel_id not in panel_image_map:
                    panel_image_map[img.panel_id] = img

            logger.info(f"图片索引: panel_id={len(panel_image_map)}, page_id={len(page_image_map)}")

            # 确保导出目录存在
            await self._ensure_export_dir()

            # 生成文件名
            file_name, file_path = self._build_export_file(
                "manga_pro",
                project_id,
                chapter_number,
            )

            # 获取页面尺寸
            page_size = get_page_size(request.page_size)
            page_width, page_height = page_size

            # 默认边距（PDF边距）
            margin = 10 * mm

            # 可用区域
            content_width = page_width - 2 * margin
            content_height = page_height - 2 * margin

            # 创建PDF
            c = self._create_canvas(file_path, f"第{chapter_number}章 漫画", page_size)

            # 构建页面gutter信息索引
            page_gutter_map: Dict[int, Dict[str, int]] = {}
            for page_info in pages_info:
                pn = page_info.get("page_number")
                if pn is not None:
                    page_gutter_map[pn] = {
                        "gutter_h": page_info.get("gutter_horizontal", 8),
                        "gutter_v": page_info.get("gutter_vertical", 8),
                    }

            # 按页码组织画格
            page_panels: Dict[int, List[Dict]] = {}
            for panel in panels_data:
                page_number = panel.get("page_number")
                if page_number is not None:
                    if page_number not in page_panels:
                        page_panels[page_number] = []
                    page_panels[page_number].append(panel)

            logger.info(f"页面数据: {len(page_panels)} 页, 总画格: {len(panels_data)}")

            if not page_panels:
                logger.info("无有效页面数据，使用简单模式")
                return await self.generate_chapter_manga_pdf(project_id, chapter_number, request)

            # 宽度比例映射（百分比）
            WIDTH_RATIO_MAP = {
                "full": 1.0,
                "two_thirds": 0.667,
                "half": 0.5,
                "third": 0.333,
                # 旧格式兼容
                "full_row": 1.0,
                "half_row": 0.5,
                "third_row": 0.333,
                "quarter_row": 0.25,
            }

            page_count = 0

            # 按页码顺序绘制
            for page_number in sorted(page_panels.keys()):
                panels = page_panels[page_number]

                logger.debug(f"绘制第 {page_number} 页: {len(panels)} 个画格")

                # 绘制页面背景
                c.setFillColorRGB(1, 1, 1)
                c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

                # ========== 检查是否有整页图片 ==========
                # 如果该页有整页生成的图片，直接渲染整页图片，跳过分格渲染
                page_img_record = page_image_map.get(page_number)
                if page_img_record:
                    img_path = get_images_root() / page_img_record.file_path
                    if await async_exists(img_path):
                        try:
                            # 读取图片尺寸
                            def get_image_size(path):
                                with PILImage.open(path) as img:
                                    return img.size
                            img_w, img_h = await asyncio.to_thread(get_image_size, str(img_path))

                            # 计算缩放（保持比例，最大化显示）
                            scale = min(content_width / img_w, content_height / img_h)
                            draw_width = img_w * scale
                            draw_height = img_h * scale

                            # 居中显示
                            offset_x = (page_width - draw_width) / 2
                            offset_y = (page_height - draw_height) / 2

                            # 绘制整页图片
                            c.drawImage(
                                str(img_path),
                                offset_x,
                                offset_y,
                                width=draw_width,
                                height=draw_height,
                                preserveAspectRatio=True,
                            )

                            logger.debug(f"第 {page_number} 页使用整页图片")

                            # 绘制页码
                            _register_chinese_font()
                            c.setFillColorRGB(0.5, 0.5, 0.5)
                            c.setFont(_CHINESE_FONT_NAME, 9)
                            c.drawCentredString(page_width / 2, 15, str(page_count + 1))

                            c.showPage()
                            page_count += 1
                            continue  # 跳过分格渲染

                        except Exception as e:
                            logger.warning(f"整页图片绘制失败，回退到分格模式: {e}")
                            # 继续执行分格渲染

                # 获取页面级别的gutter配置（转换为点单位，约0.35mm/point）
                gutter_info = page_gutter_map.get(page_number, {"gutter_h": 8, "gutter_v": 8})
                gap_h = gutter_info["gutter_h"] * 0.35 * mm  # 水平间距（列之间）
                gap_v = gutter_info["gutter_v"] * 0.35 * mm  # 垂直间距（行之间）

                # ========== 基于row_id的精确布局 ==========
                # 1. 按row_id分组画格
                row_panels: Dict[int, List[Dict]] = {}
                max_row_id = 0
                for panel in panels:
                    row_id = panel.get("row_id", 1)
                    if row_id not in row_panels:
                        row_panels[row_id] = []
                    row_panels[row_id].append(panel)
                    # 计算最大行号（考虑row_span）
                    row_span = panel.get("row_span", 1)
                    max_row_id = max(max_row_id, row_id + row_span - 1)

                if max_row_id == 0:
                    max_row_id = 1

                # 2. 计算基础行高（均分可用高度）
                total_rows = max_row_id
                base_row_height = (content_height - (total_rows - 1) * gap_v) / total_rows

                # 3. 绘制每一行的画格
                for row_id in sorted(row_panels.keys()):
                    row = row_panels[row_id]
                    if not row:
                        continue

                    # 计算该行的顶部y坐标（PDF坐标系y=0在底部）
                    # row_id从1开始，第1行在最顶部
                    row_top_y = page_height - margin - (row_id - 1) * (base_row_height + gap_v)

                    # 计算该行所有画格的总宽度比例
                    total_width_ratio = 0.0
                    for panel in row:
                        width_ratio = panel.get("width_ratio") or panel.get("layout_slot", "half")
                        total_width_ratio += WIDTH_RATIO_MAP.get(width_ratio, 0.5)

                    # 计算每个画格的实际宽度
                    num_gaps = len(row) - 1
                    available_width = content_width - num_gaps * gap_h

                    current_x = margin
                    for panel in row:
                        panel_id = panel.get("panel_id", "")
                        panel_number = panel.get("panel_number", 1)
                        is_key = panel.get("is_key_panel", False)
                        row_span = panel.get("row_span", 1)

                        # 计算画格宽度（按比例分配）
                        width_ratio = panel.get("width_ratio") or panel.get("layout_slot", "half")
                        ratio = WIDTH_RATIO_MAP.get(width_ratio, 0.5)
                        panel_width = available_width * (ratio / total_width_ratio) if total_width_ratio > 0 else available_width / len(row)

                        # 计算画格高度（考虑row_span）
                        panel_height = base_row_height * row_span + gap_v * (row_span - 1)

                        # 获取图片
                        img_record = panel_image_map.get(panel_id)

                        if img_record:
                            img_path = get_images_root() / img_record.file_path
                            if await async_exists(img_path):
                                try:
                                    # 读取图片尺寸，立即关闭释放资源
                                    def get_image_size(path):
                                        with PILImage.open(path) as img:
                                            return img.size
                                    img_w, img_h = await asyncio.to_thread(get_image_size, str(img_path))

                                    # 计算缩放（保持比例，完整显示图片）
                                    scale = min(panel_width / img_w, panel_height / img_h)
                                    draw_width = img_w * scale
                                    draw_height = img_h * scale

                                    # 居中偏移
                                    offset_x = (panel_width - draw_width) / 2
                                    offset_y = (panel_height - draw_height) / 2

                                    # 绘制图片（居中显示，保持完整）
                                    c.drawImage(
                                        str(img_path),
                                        current_x + offset_x,
                                        row_top_y - panel_height + offset_y,
                                        width=draw_width,
                                        height=draw_height,
                                        preserveAspectRatio=True,
                                    )

                                except Exception as e:
                                    logger.warning(f"绘制图片失败: {img_path}, {e}")
                                    # 绘制占位符
                                    c.setFillColorRGB(0.95, 0.95, 0.95)
                                    c.rect(current_x, row_top_y - panel_height, panel_width, panel_height, fill=True, stroke=False)
                            else:
                                # 图片不存在，绘制占位符
                                c.setFillColorRGB(0.95, 0.95, 0.95)
                                c.rect(current_x, row_top_y - panel_height, panel_width, panel_height, fill=True, stroke=False)
                        else:
                            # 无图片，绘制占位符
                            c.setFillColorRGB(0.95, 0.95, 0.95)
                            c.rect(current_x, row_top_y - panel_height, panel_width, panel_height, fill=True, stroke=False)
                            _register_chinese_font()
                            c.setFont(_CHINESE_FONT_NAME, 10)
                            c.setFillColorRGB(0.5, 0.5, 0.5)
                            c.drawCentredString(
                                current_x + panel_width / 2,
                                row_top_y - panel_height / 2,
                                f"P{page_number}R{row_id}-{panel_number}"
                            )

                        # 绘制边框
                        if is_key:
                            c.setStrokeColorRGB(0.1, 0.1, 0.1)
                            c.setLineWidth(2.5)
                        else:
                            c.setStrokeColorRGB(0.2, 0.2, 0.2)
                            c.setLineWidth(1)
                        c.rect(current_x, row_top_y - panel_height, panel_width, panel_height, fill=False, stroke=True)

                        current_x += panel_width + gap_h

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
