"""
图片生成API路由

提供图片生成配置管理和图片生成功能。
配置管理使用 ImageConfigService，图片生成使用 ImageGenerationService。
"""

from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

import logging

from ...core.config import settings
from ...core.dependencies import get_default_user, get_image_config_service
from ...db.session import get_session
from ...exceptions import ResourceNotFoundError, InvalidParameterError

logger = logging.getLogger(__name__)
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
    PageImageGenerationRequest,
)
from ...services.image_generation.pdf_export import PDFExportService
from ...services.image_generation.fs_utils import get_images_root

router = APIRouter(prefix="/image-generation", tags=["image-generation"])


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
    """为场景生成图片"""
    service = ImageGenerationService(session)
    merged_request = await service.prepare_scene_request(project_id, request)
    result = await service.generate_image(
        user_id=desktop_user.id,
        project_id=project_id,
        chapter_number=chapter_number,
        scene_id=scene_id,
        request=merged_request,
    )
    await session.commit()
    return result


@router.post(
    "/novels/{project_id}/chapters/{chapter_number}/pages/{page_number}/generate",
    response_model=ImageGenerationResult,
)
async def generate_page_image(
    project_id: str,
    chapter_number: int,
    page_number: int,
    request: PageImageGenerationRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """为整页漫画生成图片

    让AI直接生成带分格布局的整页漫画，包含对话气泡和音效文字。
    相比逐panel生成，整页生成的画面更统一，布局更自然。

    请求体需要包含由 PromptBuilder.build_page_prompt() 生成的页面级提示词。
    """
    service = ImageGenerationService(session)
    merged_request = await service.prepare_page_request(project_id, request)
    result = await service.generate_page_image(
        user_id=desktop_user.id,
        project_id=project_id,
        chapter_number=chapter_number,
        page_number=page_number,
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
            # Bug 41 修复: 使用正确的路由路径
            url=f"/api/image-generation/files/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{img.file_name}",
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
    # Bug 40 修复: 添加章节版本过滤参数
    chapter_version_id: Optional[int] = Query(None, description="章节版本ID，用于过滤特定版本的图片"),
    include_legacy: bool = Query(False, description="是否包含历史版本的图片（无版本ID的旧数据）"),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """获取章节的所有图片"""
    service = ImageGenerationService(session)
    # Bug 40 修复: 传递版本过滤参数
    images = await service.get_chapter_images(
        project_id, chapter_number,
        version_id=chapter_version_id,
        include_legacy=include_legacy,
    )

    return [
        GeneratedImageInfo(
            id=img.id,
            file_name=img.file_name,
            file_path=img.file_path,
            # Bug 41 修复: 使用正确的路由路径
            url=f"/api/image-generation/files/{project_id}/chapter_{chapter_number}/scene_{img.scene_id}/{img.file_name}",
            scene_id=img.scene_id,
            panel_id=img.panel_id,
            image_type=img.image_type,  # 图片类型: panel 或 page
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
    1. 专业排版模式(layout="manga")：如果章节有AI生成的排版信息，按分镜布局排列图片
    2. 简单模式(layout="full")：一页一图的漫画阅读体验（默认，或无排版信息时自动使用）
    """
    if request is None:
        request = ChapterMangaPDFRequest()
    service = PDFExportService(session)

    # Bug 21 修复: 根据layout参数选择导出模式
    if request.layout == "manga":
        # 漫画分格模式：使用专业排版，无排版信息时自动回退到简单模式
        result = await service.generate_professional_manga_pdf(project_id, chapter_number, request)
    else:
        # 全页模式（默认）：一页一图
        result = await service.generate_chapter_manga_pdf(project_id, chapter_number, request)
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


# ==================== 提示词预览 ====================

from pydantic import BaseModel
from typing import Optional, List


class PromptPreviewRequest(BaseModel):
    """提示词预览请求"""
    prompt: str
    negative_prompt: Optional[str] = None
    style: Optional[str] = None
    ratio: Optional[str] = None
    resolution: Optional[str] = None
    # 漫画画格元数据 - 对话相关
    dialogue: Optional[str] = None
    dialogue_speaker: Optional[str] = None
    dialogue_bubble_type: Optional[str] = None
    dialogue_emotion: Optional[str] = None
    dialogue_position: Optional[str] = None
    # 漫画画格元数据 - 旁白相关
    narration: Optional[str] = None
    narration_position: Optional[str] = None
    # 漫画画格元数据 - 音效相关
    sound_effects: Optional[List[str]] = None
    sound_effect_details: Optional[List[dict]] = None
    # 漫画画格元数据 - 视觉相关
    composition: Optional[str] = None
    camera_angle: Optional[str] = None
    is_key_panel: bool = False
    characters: Optional[List[str]] = None
    lighting: Optional[str] = None
    atmosphere: Optional[str] = None
    key_visual_elements: Optional[List[str]] = None
    # 语言设置
    dialogue_language: Optional[str] = None


@router.post("/preview-prompt")
async def preview_prompt(
    request: PromptPreviewRequest,
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    预览处理后的提示词（不生成图片）

    展示发送给生图模型的实际提示词，包括：
    - 场景类型检测结果
    - 动态添加的上下文前缀
    - 风格后缀（如果需要）
    - 宽高比描述
    - 漫画视觉元素（对话、旁白、音效、构图、镜头等）
    - 负面提示词
    """
    service = ImageGenerationService(session)
    result = await service.preview_prompt(
        user_id=desktop_user.id,
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        style=request.style,
        ratio=request.ratio,
        resolution=request.resolution,
        # 漫画画格元数据 - 对话相关
        dialogue=request.dialogue,
        dialogue_speaker=request.dialogue_speaker,
        dialogue_bubble_type=request.dialogue_bubble_type,
        dialogue_emotion=request.dialogue_emotion,
        dialogue_position=request.dialogue_position,
        # 漫画画格元数据 - 旁白相关
        narration=request.narration,
        narration_position=request.narration_position,
        # 漫画画格元数据 - 音效相关
        sound_effects=request.sound_effects,
        sound_effect_details=request.sound_effect_details,
        # 漫画画格元数据 - 视觉相关
        composition=request.composition,
        camera_angle=request.camera_angle,
        is_key_panel=request.is_key_panel,
        characters=request.characters,
        lighting=request.lighting,
        atmosphere=request.atmosphere,
        key_visual_elements=request.key_visual_elements,
        # 语言设置
        dialogue_language=request.dialogue_language,
    )
    return result


# ==================== 图片文件访问 ====================

@router.get("/files/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{file_name}")
async def get_image_file(
    project_id: str,
    chapter_number: int,
    scene_id: int,
    file_name: str,
):
    """获取图片文件"""
    file_path = get_images_root() / project_id / f"chapter_{chapter_number}" / f"scene_{scene_id}" / file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(
        path=file_path,
        media_type="image/png",
    )


@router.get("/files/{image_path:path}")
async def get_image_by_path(
    image_path: str,
):
    """
    通过相对路径获取图片文件

    用于立绘等任意路径的图片访问
    """
    # 安全检查：防止路径遍历攻击
    if ".." in image_path:
        raise HTTPException(status_code=400, detail="非法路径")

    file_path = get_images_root() / image_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    # 确保文件在get_images_root()目录下（安全检查）
    try:
        file_path.resolve().relative_to(get_images_root().resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="禁止访问")

    # 根据扩展名确定media_type
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
    )
