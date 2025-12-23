"""
图片生成API路由

提供图片生成配置管理和图片生成功能。
配置管理使用 ImageConfigService，图片生成使用 ImageGenerationService。
"""

from typing import List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.dependencies import get_default_user, get_image_config_service
from ...db.session import get_session
from ...exceptions import ResourceNotFoundError, InvalidParameterError
from ...schemas.user import UserInDB
from ...services.image_generation import (
    ImageGenerationService,
    ImageConfigService,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageConfigCreate,
    ImageConfigUpdate,
    ImageConfigResponse,
)
from ...services.image_generation.schemas import (
    SceneImagesResponse,
    GeneratedImageInfo,
    PDFExportRequest,
    PDFExportResult,
    ChapterMangaPDFRequest,
    ChapterMangaPDFResponse,
    DEFAULT_MANGA_NEGATIVE_PROMPT,
)
from ...services.image_generation.pdf_export import PDFExportService

router = APIRouter(prefix="/image-generation", tags=["image-generation"])

# 使用统一的路径配置
IMAGES_ROOT = settings.generated_images_dir


# ==================== 配置管理 ====================

@router.get("/configs", response_model=List[ImageConfigResponse])
async def get_image_configs(
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """获取所有图片生成配置"""
    configs = await service.get_configs(desktop_user.id)
    return configs


@router.get("/configs/{config_id}", response_model=ImageConfigResponse)
async def get_image_config(
    config_id: int,
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """获取单个配置"""
    config = await service.get_config(config_id, desktop_user.id)
    if not config:
        raise ResourceNotFoundError("图片生成配置", f"ID={config_id}")
    return config


@router.post("/configs", response_model=ImageConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_image_config(
    data: ImageConfigCreate,
    session: AsyncSession = Depends(get_session),
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """创建新配置"""
    config = await service.create_config(desktop_user.id, data)
    await session.commit()
    await session.refresh(config)
    return config


@router.put("/configs/{config_id}", response_model=ImageConfigResponse)
async def update_image_config(
    config_id: int,
    data: ImageConfigUpdate,
    session: AsyncSession = Depends(get_session),
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """更新配置"""
    config = await service.update_config(config_id, desktop_user.id, data)
    if not config:
        raise ResourceNotFoundError("图片生成配置", f"ID={config_id}")
    await session.commit()
    await session.refresh(config)
    return config


@router.delete("/configs/{config_id}")
async def delete_image_config(
    config_id: int,
    session: AsyncSession = Depends(get_session),
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """删除配置"""
    try:
        success = await service.delete_config(config_id, desktop_user.id)
        if not success:
            raise ResourceNotFoundError("图片生成配置", f"ID={config_id}")
        await session.commit()
        return {"success": True}
    except ValueError as e:
        raise InvalidParameterError(str(e))


@router.post("/configs/{config_id}/activate")
async def activate_image_config(
    config_id: int,
    session: AsyncSession = Depends(get_session),
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """激活配置"""
    success = await service.activate_config(config_id, desktop_user.id)
    if not success:
        raise ResourceNotFoundError("图片生成配置", f"ID={config_id}")
    await session.commit()
    return {"success": True}


@router.post("/configs/{config_id}/test")
async def test_image_config(
    config_id: int,
    session: AsyncSession = Depends(get_session),
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """测试配置连接"""
    result = await service.test_config(config_id, desktop_user.id)
    await session.commit()
    return result


# ==================== 配置导入导出 ====================

@router.get("/configs/{config_id}/export")
async def export_image_config(
    config_id: int,
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出单个图片生成配置"""
    try:
        export_data = await service.export_config(config_id, desktop_user.id)
        return export_data
    except ValueError as e:
        raise ResourceNotFoundError("图片生成配置", str(e))


@router.get("/configs/export/all")
async def export_all_image_configs(
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出用户的所有图片生成配置"""
    try:
        export_data = await service.export_all_configs(desktop_user.id)
        return export_data
    except ValueError as e:
        raise ResourceNotFoundError("图片生成配置", str(e))


@router.post("/configs/import")
async def import_image_configs(
    import_data: dict,
    session: AsyncSession = Depends(get_session),
    service: ImageConfigService = Depends(get_image_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导入图片生成配置"""
    try:
        result = await service.import_configs(desktop_user.id, import_data)
        await session.commit()
        return result
    except ValueError as e:
        raise InvalidParameterError(str(e))


# ==================== 图片生成 ====================

@router.post(
    "/novels/{project_id}/chapters/{chapter_number}/scenes/{scene_id}/generate",
    response_model=ImageGenerationResult,
)
async def generate_scene_image(
    project_id: str,
    chapter_number: int,
    scene_id: int,
    request: ImageGenerationRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """为场景生成图片

    自动合并默认的漫画负面提示词，避免AI常见的渲染问题（塑料感、解剖错误等）。
    """
    # 合并默认负面提示词与用户提供的负面提示词
    if request.negative_prompt:
        # 用户提供了负面提示词，与默认合并
        merged_negative = f"{DEFAULT_MANGA_NEGATIVE_PROMPT}, {request.negative_prompt}"
    else:
        # 使用默认负面提示词
        merged_negative = DEFAULT_MANGA_NEGATIVE_PROMPT

    # 创建合并后的请求
    merged_request = ImageGenerationRequest(
        prompt=request.prompt,
        negative_prompt=merged_negative,
        style=request.style,
        ratio=request.ratio,
        resolution=request.resolution,
        quality=request.quality,
        count=request.count,
        seed=request.seed,
        chapter_version_id=request.chapter_version_id,
        panel_id=request.panel_id,
    )

    service = ImageGenerationService(session)
    result = await service.generate_image(
        user_id=desktop_user.id,
        project_id=project_id,
        chapter_number=chapter_number,
        scene_id=scene_id,
        request=merged_request,
    )
    await session.commit()
    return result


# ==================== 图片管理 ====================

@router.get(
    "/novels/{project_id}/chapters/{chapter_number}/scenes/{scene_id}/images",
    response_model=SceneImagesResponse,
)
async def get_scene_images(
    project_id: str,
    chapter_number: int,
    scene_id: int,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """获取场景的所有图片"""
    service = ImageGenerationService(session)
    images = await service.get_scene_images(project_id, chapter_number, scene_id)

    # 构建响应
    image_infos = [
        GeneratedImageInfo(
            id=img.id,
            file_name=img.file_name,
            file_path=img.file_path,
            url=f"/api/images/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{img.file_name}",
            width=img.width,
            height=img.height,
            prompt=img.prompt,
            created_at=img.created_at,
        )
        for img in images
    ]

    return SceneImagesResponse(
        project_id=project_id,
        chapter_number=chapter_number,
        scene_id=scene_id,
        images=image_infos,
        total=len(image_infos),
    )


@router.get(
    "/novels/{project_id}/chapters/{chapter_number}/images",
    response_model=List[GeneratedImageInfo],
)
async def get_chapter_images(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """获取章节的所有图片"""
    service = ImageGenerationService(session)
    images = await service.get_chapter_images(project_id, chapter_number)

    return [
        GeneratedImageInfo(
            id=img.id,
            file_name=img.file_name,
            file_path=img.file_path,
            url=f"/api/images/{project_id}/chapter_{chapter_number}/scene_{img.scene_id}/{img.file_name}",
            scene_id=img.scene_id,
            panel_id=img.panel_id,
            width=img.width,
            height=img.height,
            prompt=img.prompt,
            created_at=img.created_at,
        )
        for img in images
    ]


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """删除图片"""
    service = ImageGenerationService(session)
    success = await service.delete_image(image_id)
    if not success:
        raise ResourceNotFoundError("图片", f"ID={image_id}")
    await session.commit()
    return {"success": True}


@router.post("/images/{image_id}/toggle-selection")
async def toggle_image_selection(
    image_id: int,
    selected: bool = True,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """切换图片选中状态"""
    service = ImageGenerationService(session)
    success = await service.toggle_image_selection(image_id, selected)
    if not success:
        raise ResourceNotFoundError("图片", f"ID={image_id}")
    await session.commit()
    return {"success": True}


# ==================== PDF导出 ====================

@router.post("/export/pdf", response_model=PDFExportResult)
async def export_images_to_pdf(
    request: PDFExportRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出图片为PDF"""
    service = PDFExportService(session)
    result = await service.export_images_to_pdf(request)
    return result


@router.post(
    "/novels/{project_id}/chapters/{chapter_number}/manga-pdf",
    response_model=ChapterMangaPDFResponse,
)
async def generate_chapter_manga_pdf(
    project_id: str,
    chapter_number: int,
    request: ChapterMangaPDFRequest = None,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    生成章节漫画PDF

    支持两种模式：
    1. 专业排版模式：如果章节有AI生成的排版信息，按分镜布局排列图片
    2. 简单模式：一页一图的漫画阅读体验（无排版信息时自动使用）
    """
    if request is None:
        request = ChapterMangaPDFRequest()
    service = PDFExportService(session)
    # 优先使用专业排版模式，无排版信息时自动回退到简单模式
    result = await service.generate_professional_manga_pdf(project_id, chapter_number, request)
    return result


@router.get(
    "/novels/{project_id}/chapters/{chapter_number}/manga-pdf/latest",
    response_model=ChapterMangaPDFResponse,
)
async def get_latest_chapter_manga_pdf(
    project_id: str,
    chapter_number: int,
    desktop_user: UserInDB = Depends(get_default_user),
):
    """获取章节最新的漫画PDF（如果存在）"""
    export_dir = settings.exports_dir

    if not export_dir.exists():
        return ChapterMangaPDFResponse(
            success=False,
            error_message="暂无PDF文件",
        )

    # 查找匹配的文件（支持简单模式和专业模式）
    pdf_files = []
    patterns = [
        f"manga_{project_id}_ch{chapter_number}_",      # 简单模式
        f"manga_pro_{project_id}_ch{chapter_number}_",  # 专业排版模式
    ]
    for pattern in patterns:
        for f in export_dir.glob(f"{pattern}*.pdf"):
            pdf_files.append(f)

    if not pdf_files:
        return ChapterMangaPDFResponse(
            success=False,
            error_message="暂无PDF文件",
        )

    # 按修改时间排序，获取最新的
    latest_pdf = max(pdf_files, key=lambda x: x.stat().st_mtime)

    return ChapterMangaPDFResponse(
        success=True,
        file_path=str(latest_pdf),
        file_name=latest_pdf.name,
        download_url=f"/api/image-generation/export/download/{latest_pdf.name}",
        page_count=0,  # 这里不计算页数
    )


@router.get("/export/download/{file_name}")
async def download_export_file(
    file_name: str,
    desktop_user: UserInDB = Depends(get_default_user),
):
    """下载导出的PDF文件"""
    export_dir = settings.exports_dir
    file_path = export_dir / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/pdf",
    )


# ==================== 图片文件访问 ====================

@router.get("/files/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{file_name}")
async def get_image_file(
    project_id: str,
    chapter_number: int,
    scene_id: int,
    file_name: str,
):
    """获取图片文件"""
    file_path = IMAGES_ROOT / project_id / f"chapter_{chapter_number}" / f"scene_{scene_id}" / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(
        path=file_path,
        media_type="image/png",
    )
