"""
漫画提示词API路由 V2

基于页面驱动的漫画分镜生成API。
"""

import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
)
from ....core.config import settings
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError, AFNException
from ....schemas.user import UserInDB
from ....services.manga_prompt import (
    MangaPromptServiceV2,
    MangaStyle,
    MangaPromptResult,
)
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....repositories.chapter_repository import ChapterRepository
from ....repositories.character_portrait_repository import CharacterPortraitRepository

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 请求/响应模型
# ============================================================

class GenerateRequest(BaseModel):
    """生成请求"""
    style: str = Field(default="manga", description="漫画风格: manga/anime/comic/webtoon")
    min_pages: int = Field(default=8, ge=3, le=20, description="最少页数")
    max_pages: int = Field(default=15, ge=5, le=30, description="最多页数")
    language: str = Field(default="chinese", description="对话/音效语言: chinese/japanese/english/korean")
    use_portraits: bool = Field(default=True, description="是否使用角色立绘作为参考图")
    auto_generate_portraits: bool = Field(default=True, description="是否自动为缺失立绘的角色生成立绘")
    force_restart: bool = Field(default=False, description="是否强制从头开始，忽略断点")


class PanelResponse(BaseModel):
    """画格响应"""
    panel_id: str
    page_number: int
    panel_number: int
    size: str
    shape: str
    shot_type: str
    aspect_ratio: str
    prompt_en: str
    prompt_zh: str
    negative_prompt: str
    # 文字元素
    dialogues: List[Dict[str, Any]] = []
    narration: str = ""
    sound_effects: List[Dict[str, Any]] = []
    # 角色信息
    characters: List[str] = []
    character_actions: Dict[str, str] = {}
    character_expressions: Dict[str, str] = {}
    # 视觉信息
    focus_point: str = ""
    lighting: str = ""
    atmosphere: str = ""
    background: str = ""
    motion_lines: bool = False
    impact_effects: bool = False
    is_key_panel: bool = False
    # 参考图
    reference_image_paths: List[str] = []


class PageResponse(BaseModel):
    """页面响应"""
    page_number: int
    panel_count: int
    layout_description: str = ""
    reading_flow: str = "right_to_left"


class GenerateResponse(BaseModel):
    """生成响应"""
    chapter_number: int
    style: str
    character_profiles: Dict[str, str]
    total_pages: int
    total_panels: int
    pages: List[PageResponse]
    panels: List[PanelResponse]


# ============================================================
# API端点
# ============================================================

@router.post("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def generate_manga_prompts(
    project_id: str,
    chapter_number: int,
    request: GenerateRequest,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GenerateResponse:
    """
    生成章节的漫画分镜

    基于页面驱动的4步流水线：
    1. 信息提取 - 提取角色、对话、事件、场景
    2. 页面规划 - 全局页数分配和节奏控制
    3. 分镜设计 - 每页画格设计
    4. 提示词构建 - 生成AI绘图提示词

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        request: 生成请求

    Returns:
        漫画分镜结果
    """
    logger.info(
        f"生成漫画分镜: project={project_id}, chapter={chapter_number}, "
        f"style={request.style}, language={request.language}, "
        f"pages={request.min_pages}-{request.max_pages}"
    )

    # 创建服务
    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    # 获取章节内容
    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

    if not chapter:
        raise ResourceNotFoundError("章节", f"第{chapter_number}章")

    # 获取章节内容
    content = None
    if chapter.versions:
        selected = next((v for v in chapter.versions if v.id == chapter.selected_version_id), None)
        if selected:
            content = selected.content
        elif chapter.versions:
            content = chapter.versions[0].content

    if not content:
        raise HTTPException(
            status_code=400,
            detail=f"章节 {chapter_number} 没有内容，请先生成章节"
        )

    # 获取角色立绘（需要转换为完整路径）
    character_portraits = {}
    if request.use_portraits:
        portrait_repo = CharacterPortraitRepository(session)
        portraits = await portrait_repo.get_all_active_by_project(project_id)
        if portraits:
            character_portraits = {
                p.character_name: str(settings.generated_images_dir / p.image_path)
                for p in portraits
                if p.image_path
            }
            logger.info(f"加载了 {len(character_portraits)} 个角色立绘")

    try:
        result = await service.generate(
            project_id=project_id,
            chapter_number=chapter_number,
            chapter_content=content,
            style=request.style,
            min_pages=request.min_pages,
            max_pages=request.max_pages,
            user_id=desktop_user.id,
            dialogue_language=request.language,
            character_portraits=character_portraits,
            auto_generate_portraits=request.auto_generate_portraits,
            resume=not request.force_restart,  # 如果 force_restart=True，则不从断点恢复
        )

        await session.commit()
        return _convert_to_response(result)

    except AFNException as e:
        # 业务异常，使用 detail 返回用户友好的错误消息
        logger.error(f"漫画分镜生成失败: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail)

    except Exception as e:
        logger.exception(f"漫画分镜生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def get_manga_prompts(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> GenerateResponse:
    """
    获取已保存的漫画分镜

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        已保存的漫画分镜结果
    """
    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
    )

    result = await service.get_result(project_id, chapter_number)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"章节 {chapter_number} 尚未生成漫画分镜"
        )

    # 将 MangaPromptResult 对象转换为字典
    return _convert_dict_to_response(result.to_dict())


@router.delete("/novels/{project_id}/chapters/{chapter_number}/manga-prompts")
async def delete_manga_prompts(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    删除章节的漫画分镜

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        删除结果
    """
    logger.info(f"删除漫画分镜: project={project_id}, chapter={chapter_number}")

    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
    )

    success = await service.delete_result(project_id, chapter_number)
    await session.commit()

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"章节 {chapter_number} 没有漫画分镜可删除"
        )

    return {"success": True, "message": "漫画分镜已删除"}


@router.get("/novels/{project_id}/chapters/{chapter_number}/manga-prompts/progress")
async def get_manga_prompt_progress(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
) -> dict:
    """
    获取漫画分镜生成进度

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        进度信息
    """
    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
    )

    # 检查是否已完成
    result = await service.get_result(project_id, chapter_number)
    if result:
        return {
            "status": "completed",
            "stage": "completed",
            "stage_label": "已完成",
            "current": result.total_panels,
            "total": result.total_panels,
            "message": "生成完成",
            "can_resume": False,
        }

    # 获取断点信息
    checkpoint = await service._checkpoint_manager.get_checkpoint(
        project_id, chapter_number
    )

    if checkpoint:
        progress = checkpoint.get("progress", {})
        status = checkpoint["status"]
        stage = progress.get("stage", status)

        stage_labels = {
            "extracting": "提取信息中",
            "planning": "规划页面中",
            "storyboard": "设计分镜中",
            "prompt_building": "生成提示词中",
        }
        stage_label = stage_labels.get(stage, "处理中")

        return {
            "status": status,
            "stage": stage,
            "stage_label": stage_label,
            "current": progress.get("current", 0),
            "total": progress.get("total", 0),
            "message": progress.get("message", ""),
            "can_resume": True,
        }

    return {
        "status": "pending",
        "stage": "pending",
        "stage_label": "未开始",
        "current": 0,
        "total": 0,
        "message": "等待生成",
        "can_resume": False,
    }


# ============================================================
# 辅助函数
# ============================================================

def _convert_to_response(result: MangaPromptResult) -> GenerateResponse:
    """将生成结果转换为API响应格式"""
    pages = []
    for page in result.pages:
        pages.append(PageResponse(
            page_number=page.page_number,
            panel_count=len(page.panels),
            layout_description=page.layout_description,
            reading_flow=page.reading_flow,
        ))

    panels = []
    for prompt in result.get_all_prompts():
        panels.append(PanelResponse(
            panel_id=prompt.panel_id,
            page_number=prompt.page_number,
            panel_number=prompt.panel_number,
            size=prompt.size,
            shape=prompt.shape,
            shot_type=prompt.shot_type,
            aspect_ratio=prompt.aspect_ratio,
            prompt_en=prompt.prompt_en,
            prompt_zh=prompt.prompt_zh,
            negative_prompt=prompt.negative_prompt,
            dialogues=prompt.dialogues,
            narration=prompt.narration,
            sound_effects=prompt.sound_effects,
            characters=prompt.characters,
            character_actions=prompt.character_actions,
            character_expressions=prompt.character_expressions,
            focus_point=prompt.focus_point,
            lighting=prompt.lighting,
            atmosphere=prompt.atmosphere,
            background=prompt.background,
            motion_lines=prompt.motion_lines,
            impact_effects=prompt.impact_effects,
            is_key_panel=prompt.is_key_panel,
            reference_image_paths=prompt.reference_image_paths or [],
        ))

    return GenerateResponse(
        chapter_number=result.chapter_number,
        style=result.style,
        character_profiles=result.character_profiles,
        total_pages=result.total_pages,
        total_panels=result.total_panels,
        pages=pages,
        panels=panels,
    )


def _convert_dict_to_response(data: Dict[str, Any]) -> GenerateResponse:
    """将存储的字典数据转换为API响应格式"""
    pages = []
    all_panels = []  # 收集所有页面中的画格

    for page_data in data.get("pages", []):
        page_panels = page_data.get("panels", [])
        pages.append(PageResponse(
            page_number=page_data.get("page_number", 0),
            panel_count=len(page_panels),
            layout_description=page_data.get("layout_description", ""),
            reading_flow=page_data.get("reading_flow", "right_to_left"),
        ))
        # 收集画格到扁平列表
        all_panels.extend(page_panels)

    # 如果没有从 pages 中提取到画格，尝试从顶层 panels 获取（兼容旧格式）
    if not all_panels:
        all_panels = data.get("panels", [])

    panels = []
    for p in all_panels:
        panels.append(PanelResponse(
            panel_id=p.get("panel_id") or "",
            page_number=p.get("page_number") or 0,
            panel_number=p.get("panel_number") or 0,
            size=p.get("size") or "medium",
            shape=p.get("shape") or "rectangle",
            shot_type=p.get("shot_type") or "medium",
            aspect_ratio=p.get("aspect_ratio") or "4:3",
            prompt_en=p.get("prompt_en") or "",
            prompt_zh=p.get("prompt_zh") or "",
            negative_prompt=p.get("negative_prompt") or "",
            dialogues=p.get("dialogues") or [],
            narration=p.get("narration") or "",
            sound_effects=p.get("sound_effects") or [],
            characters=p.get("characters") or [],
            character_actions=p.get("character_actions") or {},
            character_expressions=p.get("character_expressions") or {},
            focus_point=p.get("focus_point") or "",
            lighting=p.get("lighting") or "",
            atmosphere=p.get("atmosphere") or "",
            background=p.get("background") or "",
            motion_lines=p.get("motion_lines") or False,
            impact_effects=p.get("impact_effects") or False,
            is_key_panel=p.get("is_key_panel") or False,
            reference_image_paths=p.get("reference_image_paths") or [],
        ))

    return GenerateResponse(
        chapter_number=data.get("chapter_number", 0),
        style=data.get("style", "manga"),
        character_profiles=data.get("character_profiles", {}),
        total_pages=data.get("total_pages", 0),
        total_panels=data.get("total_panels", 0),
        pages=pages,
        panels=panels,
    )
