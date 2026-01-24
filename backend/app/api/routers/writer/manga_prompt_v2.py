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
    start_from_stage: Optional[str] = Field(
        default=None,
        description=(
            "指定从哪个阶段开始生成，可选值: "
            "extraction(信息提取), planning(页面规划), storyboard(分镜设计), "
            "prompt_building(提示词构建), page_prompt_building(整页提示词构建)。"
            "为None时自动从断点恢复或从头开始"
        )
    )
    auto_generate_page_images: bool = Field(
        default=False,
        description="是否在分镜生成完成后自动生成所有整页图片"
    )
    page_prompt_concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="整页提示词LLM生成的并发数（1-20）"
    )


class PanelResponse(BaseModel):
    """画格响应"""
    panel_id: str
    page_number: int
    panel_number: int
    scene_id: int = 0
    shape: str  # horizontal/vertical/square
    shot_type: str  # long/medium/close_up

    # 排版信息
    row_id: int = 1  # 起始行号
    row_span: int = 1  # 跨越行数
    width_ratio: str = "half"  # full/two_thirds/half/third
    aspect_ratio: str = "4:3"  # 16:9/4:3/1:1/3:4/9:16

    # 提示词
    prompt: str
    negative_prompt: str

    # 文字元素
    dialogues: List[Dict[str, Any]] = []

    # 角色信息
    characters: List[str] = []

    # 参考图
    reference_image_paths: List[str] = []

    # 对话语言（用于图片生成）
    dialogue_language: str = "chinese"


class PageResponse(BaseModel):
    """页面响应"""
    page_number: int
    panel_count: int
    layout_description: str = ""
    gutter_horizontal: int = 8
    gutter_vertical: int = 8


class SceneResponse(BaseModel):
    """场景响应（页面信息）"""
    scene_id: int
    page_number: int
    panel_count: int
    layout_description: str = ""
    reading_flow: str = "right_to_left"
    gutter_horizontal: int = 8
    gutter_vertical: int = 8


class PagePromptResponse(BaseModel):
    """整页提示词响应"""
    page_number: int
    layout_template: str = ""
    layout_description: str = ""
    full_page_prompt: str = ""
    negative_prompt: str = ""
    aspect_ratio: str = "3:4"
    panel_summaries: List[Dict[str, Any]] = []
    reference_image_paths: List[str] = []


class GenerateResponse(BaseModel):
    """生成响应"""
    chapter_number: int
    style: str
    character_profiles: Dict[str, str]
    total_pages: int
    total_panels: int
    pages: List[PageResponse]
    scenes: List[SceneResponse]
    panels: List[PanelResponse]
    # Bug 24 修复: 添加对话语言字段
    dialogue_language: str = "chinese"
    # 分析数据（章节信息提取和页面规划结果）
    analysis_data: Optional[Dict[str, Any]] = None
    # 增量更新状态字段
    is_complete: bool = True  # 是否已全部完成
    completed_pages_count: Optional[int] = None  # 已完成的页数（增量生成时使用）
    # 整页提示词列表（用于整页漫画生成）
    page_prompts: List[PagePromptResponse] = []


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
        f"pages={request.min_pages}-{request.max_pages}, force_restart={request.force_restart}"
    )

    # 创建服务
    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
        prompt_service=prompt_service,
    )

    # 获取章节
    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

    if not chapter:
        raise ResourceNotFoundError("章节", f"第{chapter_number}章")

    # 检查是否已有生成记录
    from ....repositories.manga_prompt_repository import MangaPromptRepository
    manga_prompt_repo = MangaPromptRepository(session)
    existing_manga = await manga_prompt_repo.get_by_chapter_id(chapter.id)
    if existing_manga:
        current_status = existing_manga.generation_status
        # 如果状态是 cancelled，无论 force_restart 是什么，都需要重置状态
        # 因为用户明显想要重新开始生成
        if current_status == "cancelled":
            logger.info(
                f"重置已取消的任务: project={project_id}, chapter={chapter_number}, "
                f"cancelled -> pending"
            )
            existing_manga.generation_status = "pending"
            existing_manga.generation_progress = {}
            await session.flush()
        # 如果是进行中状态（非 pending/completed/cancelled）
        elif current_status not in (None, "pending", "completed"):
            if request.force_restart:
                # 用户选择强制重新开始，重置状态
                logger.info(
                    f"强制重新生成，重置状态: project={project_id}, chapter={chapter_number}, "
                    f"{current_status} -> pending"
                )
                existing_manga.generation_status = "pending"
                existing_manga.generation_progress = {}
                await session.flush()
            else:
                # 用户选择继续生成（断点续传）
                logger.info(
                    f"继续未完成的生成任务: project={project_id}, chapter={chapter_number}, "
                    f"当前状态={current_status}"
                )

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
            resume=not request.force_restart,
            start_from_stage=request.start_from_stage,
            auto_generate_page_images=request.auto_generate_page_images,
            page_prompt_concurrency=request.page_prompt_concurrency,
        )

        await session.commit()
        return _convert_to_response(result)

    except AFNException as e:
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
    # 直接使用 repository 获取原始数据（包含 analysis_data）
    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

    if not chapter:
        raise HTTPException(
            status_code=404,
            detail=f"章节 {chapter_number} 不存在"
        )

    from ....repositories.manga_prompt_repository import MangaPromptRepository
    manga_prompt_repo = MangaPromptRepository(session)
    data = await manga_prompt_repo.get_result(chapter.id)

    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"章节 {chapter_number} 尚未生成漫画分镜"
        )

    # 添加章节号
    data["chapter_number"] = chapter_number

    # 将字典数据转换为API响应格式
    return _convert_dict_to_response(data)


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


@router.post("/novels/{project_id}/chapters/{chapter_number}/manga-prompts/cancel")
async def cancel_manga_prompt_generation(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    取消漫画分镜生成

    将生成状态设置为 cancelled，正在进行的生成任务会在下次检查点时停止。

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        取消结果
    """
    from ....repositories.manga_prompt_repository import MangaPromptRepository

    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

    if not chapter:
        return {"success": False, "message": "章节不存在"}

    manga_prompt_repo = MangaPromptRepository(session)
    manga_prompt = await manga_prompt_repo.get_by_chapter_id(chapter.id)

    if not manga_prompt:
        return {"success": False, "message": "没有正在进行的生成任务"}

    # 检查当前状态是否为生成中
    if manga_prompt.generation_status in ("completed", "pending", "cancelled"):
        return {"success": False, "message": f"当前状态为 {manga_prompt.generation_status}，无法取消"}

    # 设置为取消状态
    manga_prompt.generation_status = "cancelled"
    manga_prompt.generation_progress = {
        "stage": "cancelled",
        "message": "用户取消生成"
    }
    await session.commit()

    logger.info(f"取消漫画分镜生成: project={project_id}, chapter={chapter_number}")
    return {"success": True, "message": "已发送取消请求"}


@router.get("/novels/{project_id}/chapters/{chapter_number}/manga-prompts/progress")
async def get_manga_prompt_progress(
    project_id: str,
    chapter_number: int,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    获取漫画分镜生成进度

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        进度信息
    """
    from ....repositories.manga_prompt_repository import MangaPromptRepository

    # 直接查询数据库获取状态
    chapter_repo = ChapterRepository(session)
    chapter = await chapter_repo.get_by_project_and_number(project_id, chapter_number)

    if not chapter:
        return {
            "status": "pending",
            "stage": "pending",
            "stage_label": "未开始",
            "current": 0,
            "total": 0,
            "message": "章节不存在",
            "can_resume": False,
        }

    manga_prompt_repo = MangaPromptRepository(session)
    manga_prompt = await manga_prompt_repo.get_by_chapter_id(chapter.id)

    if not manga_prompt:
        return {
            "status": "pending",
            "stage": "pending",
            "stage_label": "未开始",
            "current": 0,
            "total": 0,
            "message": "等待生成",
            "can_resume": False,
        }

    status = manga_prompt.generation_status or "pending"
    progress = manga_prompt.generation_progress or {}

    # 状态标签映射
    stage_labels = {
        "pending": "未开始",
        "extracting": "提取信息中",
        "planning": "规划页面中",
        "storyboard": "设计分镜中",
        "generating": "生成中",
        "generating_portraits": "生成角色立绘中",
        "prompt_building": "生成提示词中",
        "page_prompt_building": "生成整页提示词中",
        "page_image_generation": "生成整页图片中",
        "completed": "已完成",
        "cancelled": "已取消",
    }

    stage = progress.get("stage", status)
    stage_label = stage_labels.get(stage, stage_labels.get(status, "处理中"))

    if status == "completed":
        return {
            "status": "completed",
            "stage": "completed",
            "stage_label": "已完成",
            "current": manga_prompt.total_panels or 0,
            "total": manga_prompt.total_panels or 0,
            "message": "生成完成",
            "can_resume": False,
        }

    if status == "cancelled":
        return {
            "status": "cancelled",
            "stage": "cancelled",
            "stage_label": "已取消",
            "current": 0,
            "total": 0,
            "message": "生成已取消",
            "can_resume": True,  # 允许从断点继续
        }

    if status == "pending":
        return {
            "status": "pending",
            "stage": "pending",
            "stage_label": "未开始",
            "current": 0,
            "total": 0,
            "message": "等待生成",
            "can_resume": False,
        }

    # 中间状态（extracting, planning, storyboard, generating等）
    # 返回analysis_data供前端实时更新详细信息Tab
    return {
        "status": status,
        "stage": stage,
        "stage_label": stage_label,
        "current": progress.get("current", 0),
        "total": progress.get("total", 0),
        "message": progress.get("message", ""),
        "can_resume": True,
        "analysis_data": manga_prompt.analysis_data,  # 实时返回分析数据
    }


# ============================================================
# 辅助函数
# ============================================================

def _convert_to_response(result: MangaPromptResult) -> GenerateResponse:
    """将生成结果转换为API响应格式"""
    pages = []
    scenes = []
    for page in result.pages:
        panel_count = len(page.panels)
        pages.append(PageResponse(
            page_number=page.page_number,
            panel_count=panel_count,
            layout_description=page.layout_description,
            gutter_horizontal=page.gutter_horizontal,
            gutter_vertical=page.gutter_vertical,
        ))
        scenes.append(SceneResponse(
            scene_id=page.page_number,
            page_number=page.page_number,
            panel_count=panel_count,
            layout_description=page.layout_description,
            reading_flow="right_to_left",
            gutter_horizontal=page.gutter_horizontal,
            gutter_vertical=page.gutter_vertical,
        ))

    panels = []
    for prompt in result.get_all_prompts():
        panels.append(PanelResponse(
            panel_id=prompt.panel_id,
            page_number=prompt.page_number,
            panel_number=prompt.panel_number,
            scene_id=prompt.page_number,
            shape=prompt.shape,
            shot_type=prompt.shot_type,
            row_id=prompt.row_id,
            row_span=prompt.row_span,
            width_ratio=prompt.width_ratio,
            aspect_ratio=prompt.aspect_ratio,
            prompt=prompt.prompt,
            negative_prompt=prompt.negative_prompt,
            dialogues=prompt.dialogues,
            characters=prompt.characters,
            reference_image_paths=prompt.reference_image_paths or [],
            dialogue_language=result.dialogue_language,
        ))

    # 转换整页提示词
    page_prompts = []
    for pp in result.page_prompts or []:
        page_prompts.append(PagePromptResponse(
            page_number=pp.page_number,
            layout_template=pp.layout_template or "",
            layout_description=pp.layout_description or "",
            full_page_prompt=pp.full_page_prompt or "",
            negative_prompt=pp.negative_prompt or "",
            aspect_ratio=pp.aspect_ratio or "3:4",
            panel_summaries=pp.panel_summaries or [],
            reference_image_paths=pp.reference_image_paths or [],
        ))

    return GenerateResponse(
        chapter_number=result.chapter_number,
        style=result.style,
        character_profiles=result.character_profiles,
        total_pages=result.total_pages,
        total_panels=result.total_panels,
        pages=pages,
        scenes=scenes,
        panels=panels,
        dialogue_language=result.dialogue_language,
        # 从完整结果转换时，总是已完成状态
        is_complete=True,
        completed_pages_count=result.total_pages,
        page_prompts=page_prompts,
    )


def _convert_dict_to_response(data: Dict[str, Any]) -> GenerateResponse:
    """将存储的字典数据转换为API响应格式"""
    pages = []
    scenes = []
    all_panels = []  # 收集所有页面中的画格
    dialogue_language = data.get("dialogue_language", "chinese")

    for page_data in data.get("pages", []):
        page_panels = page_data.get("panels", [])
        panel_count = len(page_panels)
        pages.append(PageResponse(
            page_number=page_data.get("page_number", 0),
            panel_count=panel_count,
            layout_description=page_data.get("layout_description", ""),
            gutter_horizontal=page_data.get("gutter_horizontal", 8),
            gutter_vertical=page_data.get("gutter_vertical", 8),
        ))
        scenes.append(SceneResponse(
            scene_id=page_data.get("page_number", 0),
            page_number=page_data.get("page_number", 0),
            panel_count=panel_count,
            layout_description=page_data.get("layout_description", ""),
            reading_flow=page_data.get("reading_flow", "right_to_left"),
            gutter_horizontal=page_data.get("gutter_horizontal", 8),
            gutter_vertical=page_data.get("gutter_vertical", 8),
        ))
        # 收集画格到扁平列表
        all_panels.extend(page_panels)

    # 如果没有从 pages 中提取到画格，尝试从顶层 panels 获取（兼容旧格式）
    if not all_panels:
        all_panels = data.get("panels", [])

    panels = []
    for p in all_panels:
        # 兼容旧数据：优先读取 prompt，如果没有则尝试 prompt_en 或 prompt_zh
        prompt_value = p.get("prompt") or p.get("prompt_en") or p.get("prompt_zh") or ""
        scene_id = p.get("scene_id") or p.get("page_number") or 0
        panels.append(PanelResponse(
            panel_id=p.get("panel_id") or "",
            page_number=p.get("page_number") or 0,
            panel_number=p.get("panel_number") or 0,
            scene_id=scene_id,
            shape=p.get("shape") or "horizontal",
            shot_type=p.get("shot_type") or "medium",
            row_id=p.get("row_id") or 1,
            row_span=p.get("row_span") or 1,
            width_ratio=p.get("width_ratio") or "half",
            aspect_ratio=p.get("aspect_ratio") or "4:3",
            prompt=prompt_value,
            negative_prompt=p.get("negative_prompt") or "",
            dialogues=p.get("dialogues") or [],
            characters=p.get("characters") or [],
            reference_image_paths=p.get("reference_image_paths") or [],
            dialogue_language=p.get("dialogue_language") or dialogue_language,
        ))

    # 转换整页提示词
    page_prompts = []
    for pp in data.get("page_prompts", []):
        page_prompts.append(PagePromptResponse(
            page_number=pp.get("page_number", 0),
            layout_template=pp.get("layout_template", ""),
            layout_description=pp.get("layout_description", ""),
            full_page_prompt=pp.get("full_page_prompt", ""),
            negative_prompt=pp.get("negative_prompt", ""),
            aspect_ratio=pp.get("aspect_ratio", "3:4"),
            panel_summaries=pp.get("panel_summaries", []),
            reference_image_paths=pp.get("reference_image_paths", []),
        ))

    return GenerateResponse(
        chapter_number=data.get("chapter_number", 0),
        style=data.get("style", "manga"),
        character_profiles=data.get("character_profiles", {}),
        total_pages=data.get("total_pages", 0),
        total_panels=data.get("total_panels", 0),
        pages=pages,
        scenes=scenes,
        panels=panels,
        dialogue_language=dialogue_language,
        analysis_data=data.get("analysis_data"),
        # 增量更新状态
        is_complete=data.get("is_complete", True),
        completed_pages_count=data.get("completed_pages_count"),
        page_prompts=page_prompts,
    )
