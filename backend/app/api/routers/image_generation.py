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

import logging

from ...core.config import settings
from ...core.dependencies import get_default_user, get_image_config_service
from ...db.session import get_session
from ...exceptions import ResourceNotFoundError, InvalidParameterError
from ...repositories.character_portrait_repository import CharacterPortraitRepository

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

# 用于检测负面提示词是否已包含关键质量词的关键词列表
# 如果包含这些关键词，说明是LLM生成的完整负面提示词，不需要再追加默认值
NEGATIVE_PROMPT_QUALITY_KEYWORDS = [
    "low quality",
    "bad anatomy",
    "blurry",
    "deformed",
    "extra limbs",
    "wrong proportions",
]


def _is_complete_negative_prompt(negative_prompt: str) -> bool:
    """
    检测负面提示词是否已经足够完整（由LLM生成）

    判断标准：包含至少3个关键质量词，说明是经过智能生成的

    Args:
        negative_prompt: 负面提示词

    Returns:
        是否足够完整，不需要追加默认值
    """
    if not negative_prompt:
        return False

    prompt_lower = negative_prompt.lower()
    match_count = sum(1 for kw in NEGATIVE_PROMPT_QUALITY_KEYWORDS if kw in prompt_lower)

    # 如果匹配了至少3个关键词，认为是完整的LLM生成的负面提示词
    return match_count >= 3


def _smart_merge_negative_prompt(user_negative: str) -> str:
    """
    智能合并负面提示词

    如果用户提供的负面提示词已经足够完整（包含关键质量词），
    则直接使用，不追加默认值，避免重复。

    Args:
        user_negative: 用户/LLM提供的负面提示词

    Returns:
        合并后的负面提示词
    """
    if not user_negative:
        # 没有提供，使用默认值
        return DEFAULT_MANGA_NEGATIVE_PROMPT

    if _is_complete_negative_prompt(user_negative):
        # 已足够完整，直接使用（LLM生成的场景感知负面提示词）
        return user_negative

    # 不够完整，合并默认值
    return f"{DEFAULT_MANGA_NEGATIVE_PROMPT}, {user_negative}"


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

    智能合并负面提示词：
    - 如果请求中的negative_prompt已包含关键质量词（说明是LLM智能生成的），则直接使用
    - 否则，与默认漫画负面提示词合并，避免AI常见的渲染问题

    动态获取立绘路径：
    - 如果请求中包含characters列表，根据角色名动态查询当前激活的立绘路径
    - 这样可以确保使用最新的立绘，即使用户重新生成了立绘
    """
    # 智能合并负面提示词
    merged_negative = _smart_merge_negative_prompt(request.negative_prompt)

    # 动态获取立绘路径：根据characters列表查询当前激活的立绘
    # 这解决了"存储的分镜数据引用旧立绘路径"的问题
    reference_image_paths = request.reference_image_paths or []
    if request.characters:
        portrait_repo = CharacterPortraitRepository(session)
        active_portraits = await portrait_repo.get_all_active_by_project(project_id)
        # 构建角色名到立绘路径的映射
        portrait_map = {
            p.character_name: str(settings.generated_images_dir / p.image_path)
            for p in active_portraits
            if p.image_path
        }
        # 根据画格中的角色列表获取对应的立绘路径
        dynamic_paths = []
        for char_name in request.characters:
            if char_name in portrait_map:
                dynamic_paths.append(portrait_map[char_name])
        if dynamic_paths:
            reference_image_paths = dynamic_paths
            logger.info(
                "动态获取立绘路径: characters=%s, paths=%d",
                request.characters, len(dynamic_paths)
            )

    # 创建合并后的请求（保留所有漫画元数据）
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
        reference_image_paths=reference_image_paths if reference_image_paths else None,
        reference_strength=request.reference_strength,
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
    file_path = IMAGES_ROOT / project_id / f"chapter_{chapter_number}" / f"scene_{scene_id}" / file_name

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

    file_path = IMAGES_ROOT / image_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    # 确保文件在IMAGES_ROOT目录下（安全检查）
    try:
        file_path.resolve().relative_to(IMAGES_ROOT.resolve())
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
