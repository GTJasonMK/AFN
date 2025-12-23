"""
漫画提示词API路由 V2

基于新的专业漫画分镜架构重写的API。
"""

import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError
from ....schemas.user import UserInDB
from ....services.manga_prompt import (
    MangaPromptServiceV2,
    MangaGenerationResult,
    MangaStyle,
    ALL_TEMPLATES,
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
    min_scenes: int = Field(default=5, ge=3, le=10, description="最少场景数")
    max_scenes: int = Field(default=15, ge=5, le=25, description="最多场景数")
    language: str = Field(default="chinese", description="对话/音效语言: chinese/japanese/english/korean")
    use_portraits: bool = Field(default=True, description="是否使用角色立绘作为参考图（img2img）")


class PanelResponse(BaseModel):
    """画格响应"""
    panel_id: str
    scene_id: int
    page_number: int
    slot_id: int
    aspect_ratio: str
    composition: str
    camera_angle: str
    prompt_en: str
    prompt_zh: str
    negative_prompt: str
    # 文字元素 - 基础字段
    dialogue: Optional[str] = None
    dialogue_speaker: Optional[str] = None
    narration: Optional[str] = None
    sound_effects: List[str] = []
    # 文字元素 - 扩展字段
    dialogue_bubble_type: str = "normal"
    dialogue_position: str = "top-right"
    dialogue_emotion: str = ""
    narration_position: str = "top"
    sound_effect_details: List[Dict[str, Any]] = []
    # 视觉信息
    characters: List[str] = []
    is_key_panel: bool = False
    # 参考图（用于 img2img）
    reference_image_paths: List[str] = []


class SceneResponse(BaseModel):
    """场景响应"""
    scene_id: int
    scene_summary: str
    mood: str
    importance: str
    pages: List[Dict[str, Any]]


class GenerateResponse(BaseModel):
    """生成响应"""
    chapter_number: int
    style: str
    character_profiles: Dict[str, str]
    total_pages: int
    total_panels: int
    scenes: List[SceneResponse]
    panels: List[PanelResponse]


class TemplateInfo(BaseModel):
    """模板信息"""
    id: str
    name: str
    name_zh: str
    description: str
    panel_count: int
    suitable_moods: List[str]
    intensity: int


# ============================================================
# API端点
# ============================================================

@router.get("/templates")
async def list_templates() -> List[TemplateInfo]:
    """
    获取所有可用的页面模板

    返回所有预设的专业漫画页面布局模板信息。
    """
    templates = []
    for template in ALL_TEMPLATES.values():
        templates.append(TemplateInfo(
            id=template.id,
            name=template.name,
            name_zh=template.name_zh,
            description=template.description,
            panel_count=template.get_panel_count(),
            suitable_moods=[m.value for m in template.suitable_moods],
            intensity=template.intensity,
        ))
    return templates


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

    基于专业漫画分镜理念，将章节内容转化为：
    1. 多个叙事场景
    2. 每个场景展开为页面+画格
    3. 每个画格生成专属提示词

    Args:
        project_id: 项目ID
        chapter_number: 章节号
        request: 生成请求
            - style: 漫画风格 (manga/anime/comic/webtoon)
            - min_scenes: 最少场景数 (3-10)
            - max_scenes: 最多场景数 (5-25)
            - use_portraits: 是否使用角色立绘作为参考图

    Returns:
        漫画分镜结果，包含场景、页面、画格及提示词
    """
    logger.info(
        f"生成漫画分镜: project={project_id}, chapter={chapter_number}, "
        f"style={request.style}, language={request.language}, use_portraits={request.use_portraits}"
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
        # 优先使用选中的版本
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

    # 获取角色立绘（如果启用）
    character_portraits = {}
    if request.use_portraits:
        portrait_repo = CharacterPortraitRepository(session)
        portraits = await portrait_repo.get_all_active_by_project(project_id)
        if portraits:
            # 构建角色名到立绘路径的映射
            character_portraits = {
                p.character_name: p.image_path
                for p in portraits
                if p.image_path
            }
            logger.info(f"加载了 {len(character_portraits)} 个角色立绘用于 img2img")

    try:
        result = await service.generate(
            project_id=project_id,
            chapter_number=chapter_number,
            chapter_content=content,
            style=request.style,
            min_scenes=request.min_scenes,
            max_scenes=request.max_scenes,
            user_id=desktop_user.id,
            dialogue_language=request.language,
            character_portraits=character_portraits,
        )

        # 注意：generate内部已经在各个阶段commit了checkpoint
        # 这里只需要确保最终结果被提交
        await session.commit()

        # 转换为响应格式
        return _convert_to_response(result)

    except Exception as e:
        logger.exception(f"漫画分镜生成失败: {e}")
        # 注意：不需要rollback，因为checkpoint已经在各阶段被commit
        # 保持checkpoint状态允许下次断点续传
        raise HTTPException(status_code=500, detail=str(e))


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

    # 将存储的字典转换为响应格式
    return _convert_dict_to_response(result)


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

    删除已完成的分镜数据和任何未完成的断点数据。
    如果生成任务卡住，可以用此接口清除状态后重新开始。

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        删除结果
    """
    logger.info(
        f"删除漫画分镜: project={project_id}, chapter={chapter_number}"
    )

    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
    )

    success = await service.delete_result(project_id, chapter_number)
    await session.commit()

    if not success:
        # 即使没有完成的分镜，也尝试清除可能存在的checkpoint
        cleared = await service.manga_prompt_repo.clear_checkpoint(project_id, chapter_number)
        await session.commit()
        if cleared:
            return {"success": True, "message": "已清除未完成的生成状态"}
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

    用于前端轮询显示生成进度，支持断点续传状态查询。

    Args:
        project_id: 项目ID
        chapter_number: 章节号

    Returns:
        进度信息，包含 status, progress, can_resume, stage_label 等字段
    """
    service = MangaPromptServiceV2(
        session=session,
        llm_service=llm_service,
    )

    # 首先检查是否已完成（优先级最高）
    result = await service.get_result(project_id, chapter_number)
    if result:
        return {
            "status": "completed",
            "stage": "completed",
            "stage_label": "已完成",
            "current": result.get("total_panels", 0),
            "total": result.get("total_panels", 0),
            "message": "生成完成",
            "can_resume": False,
        }

    # 获取断点信息
    checkpoint = await service.manga_prompt_repo.get_checkpoint(
        project_id, chapter_number
    )

    if checkpoint:
        progress = checkpoint.get("progress", {})
        status = checkpoint["status"]
        stage = progress.get("stage", status)

        # 根据阶段返回更精确的信息
        stage_labels = {
            "extracting": "提取场景中",
            "expanding": "展开场景中",
            "prompt_building": "生成提示词中",
        }
        stage_label = stage_labels.get(stage, "处理中")

        # 计算是否可以继续（只要有断点数据就可以继续）
        can_resume = True

        return {
            "status": status,
            "stage": stage,
            "stage_label": stage_label,
            "current": progress.get("current", 0),
            "total": progress.get("total", 0),
            "message": progress.get("message", ""),
            "can_resume": can_resume,
        }

    # 未开始
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

def _convert_to_response(result: MangaGenerationResult) -> GenerateResponse:
    """将生成结果转换为API响应格式"""
    scenes = []
    for scene in result.scenes:
        scenes.append(SceneResponse(
            scene_id=scene.scene_id,
            scene_summary=scene.scene_summary,
            mood=scene.mood.value,
            importance=scene.importance,
            pages=[
                {
                    "page_number": page.page_number,
                    "template_id": page.template.id,
                    "template_name": page.template.name_zh,
                    "panel_count": len(page.panels),
                }
                for page in scene.pages
            ],
        ))

    panels = []
    for p in result.panel_prompts:
        # 处理可能是列表的dialogue字段（可能是字典列表或字符串列表）
        dialogue = p.dialogue
        if isinstance(dialogue, list):
            dialogue_parts = []
            for item in dialogue:
                if isinstance(item, dict):
                    dialogue_parts.append(item.get('content', item.get('text', '')))
                elif isinstance(item, str):
                    dialogue_parts.append(item)
            dialogue = " / ".join(filter(None, dialogue_parts)) if dialogue_parts else None
        elif isinstance(dialogue, dict):
            dialogue = dialogue.get('content', dialogue.get('text', str(dialogue)))
        elif dialogue is not None and not isinstance(dialogue, str):
            dialogue = str(dialogue)

        # 处理可能是列表的dialogue_speaker字段
        dialogue_speaker = p.dialogue_speaker
        if isinstance(dialogue_speaker, list):
            speaker_parts = []
            for item in dialogue_speaker:
                if isinstance(item, dict):
                    speaker_parts.append(item.get('speaker', item.get('name', '')))
                elif isinstance(item, str):
                    speaker_parts.append(item)
            dialogue_speaker = ", ".join(filter(None, speaker_parts)) if speaker_parts else None
        elif isinstance(dialogue_speaker, dict):
            dialogue_speaker = dialogue_speaker.get('speaker', dialogue_speaker.get('name', str(dialogue_speaker)))
        elif dialogue_speaker is not None and not isinstance(dialogue_speaker, str):
            dialogue_speaker = str(dialogue_speaker)

        # 处理可能是字典或列表的narration字段
        narration = p.narration
        if isinstance(narration, list):
            narration_parts = []
            for item in narration:
                if isinstance(item, dict):
                    narration_parts.append(item.get('content', item.get('text', '')))
                elif isinstance(item, str):
                    narration_parts.append(item)
            narration = " / ".join(filter(None, narration_parts)) if narration_parts else None
        elif isinstance(narration, dict):
            narration = narration.get('content', narration.get('text', str(narration)))
        elif narration is not None and not isinstance(narration, str):
            narration = str(narration)

        # 处理sound_effects - 确保是字符串列表
        sound_effects = p.sound_effects or []
        if isinstance(sound_effects, list):
            processed_sfx = []
            for sfx in sound_effects:
                if isinstance(sfx, dict):
                    # 从字典中提取text字段
                    sfx_text = sfx.get('text', sfx.get('content', ''))
                    if sfx_text:
                        processed_sfx.append(str(sfx_text))
                elif isinstance(sfx, str):
                    processed_sfx.append(sfx)
                elif sfx is not None:
                    processed_sfx.append(str(sfx))
            sound_effects = processed_sfx
        else:
            sound_effects = []

        panels.append(PanelResponse(
            panel_id=p.panel_id,
            scene_id=p.scene_id,
            page_number=p.page_number,
            slot_id=p.slot_id,
            aspect_ratio=p.aspect_ratio,
            composition=p.composition,
            camera_angle=p.camera_angle,
            prompt_en=p.prompt_en,
            prompt_zh=p.prompt_zh,
            negative_prompt=p.negative_prompt,
            # 文字元素 - 基础字段
            dialogue=dialogue,
            dialogue_speaker=dialogue_speaker,
            narration=narration,
            sound_effects=sound_effects,
            # 文字元素 - 扩展字段
            dialogue_bubble_type=getattr(p, 'dialogue_bubble_type', 'normal') or 'normal',
            dialogue_position=getattr(p, 'dialogue_position', 'top-right') or 'top-right',
            dialogue_emotion=getattr(p, 'dialogue_emotion', '') or '',
            narration_position=getattr(p, 'narration_position', 'top') or 'top',
            sound_effect_details=getattr(p, 'sound_effect_details', []) or [],
            # 视觉信息
            characters=p.characters or [],
            is_key_panel=p.is_key_panel,
            # 参考图（用于 img2img）
            reference_image_paths=getattr(p, 'reference_image_paths', []) or [],
        ))

    return GenerateResponse(
        chapter_number=result.chapter_number,
        style=result.style,
        character_profiles=result.character_profiles,
        total_pages=result.get_total_pages(),
        total_panels=result.get_total_panels(),
        scenes=scenes,
        panels=panels,
    )


def _convert_dict_to_response(data: Dict[str, Any]) -> GenerateResponse:
    """将存储的字典数据转换为API响应格式

    Args:
        data: 从数据库读取的字典数据

    Returns:
        API响应格式
    """
    scenes = []
    for scene_data in data.get("scenes", []):
        scenes.append(SceneResponse(
            scene_id=scene_data.get("scene_id", 0),
            scene_summary=scene_data.get("scene_summary", ""),
            mood=scene_data.get("mood", "calm"),
            importance=scene_data.get("importance", "normal"),
            pages=scene_data.get("pages", []),
        ))

    panels = []
    for p in data.get("panels", []):
        # 处理可能是列表或字典的dialogue字段
        dialogue = p.get("dialogue")
        if isinstance(dialogue, list):
            dialogue_parts = []
            for item in dialogue:
                if isinstance(item, dict):
                    dialogue_parts.append(item.get('content', item.get('text', '')))
                elif isinstance(item, str):
                    dialogue_parts.append(item)
            dialogue = " / ".join(filter(None, dialogue_parts)) if dialogue_parts else None
        elif isinstance(dialogue, dict):
            dialogue = dialogue.get('content', dialogue.get('text', str(dialogue)))
        elif dialogue is not None and not isinstance(dialogue, str):
            dialogue = str(dialogue)

        # 处理可能是列表或字典的dialogue_speaker字段
        dialogue_speaker = p.get("dialogue_speaker")
        if isinstance(dialogue_speaker, list):
            speaker_parts = []
            for item in dialogue_speaker:
                if isinstance(item, dict):
                    speaker_parts.append(item.get('speaker', item.get('name', '')))
                elif isinstance(item, str):
                    speaker_parts.append(item)
            dialogue_speaker = ", ".join(filter(None, speaker_parts)) if speaker_parts else None
        elif isinstance(dialogue_speaker, dict):
            dialogue_speaker = dialogue_speaker.get('speaker', dialogue_speaker.get('name', str(dialogue_speaker)))
        elif dialogue_speaker is not None and not isinstance(dialogue_speaker, str):
            dialogue_speaker = str(dialogue_speaker)

        # 处理可能是列表或字典的narration字段
        narration = p.get("narration")
        if isinstance(narration, list):
            narration_parts = []
            for item in narration:
                if isinstance(item, dict):
                    narration_parts.append(item.get('content', item.get('text', '')))
                elif isinstance(item, str):
                    narration_parts.append(item)
            narration = " / ".join(filter(None, narration_parts)) if narration_parts else None
        elif isinstance(narration, dict):
            narration = narration.get('content', narration.get('text', str(narration)))
        elif narration is not None and not isinstance(narration, str):
            narration = str(narration)

        # 处理sound_effects - 确保是字符串列表
        sound_effects = p.get("sound_effects") or []
        if isinstance(sound_effects, list):
            processed_sfx = []
            for sfx in sound_effects:
                if isinstance(sfx, dict):
                    sfx_text = sfx.get('text', sfx.get('content', ''))
                    if sfx_text:
                        processed_sfx.append(str(sfx_text))
                elif isinstance(sfx, str):
                    processed_sfx.append(sfx)
                elif sfx is not None:
                    processed_sfx.append(str(sfx))
            sound_effects = processed_sfx
        else:
            sound_effects = []

        panels.append(PanelResponse(
            panel_id=p.get("panel_id", ""),
            scene_id=p.get("scene_id", 0),
            page_number=p.get("page_number", 0),
            slot_id=p.get("slot_id", 0),
            aspect_ratio=p.get("aspect_ratio", "16:9"),
            composition=p.get("composition", ""),
            camera_angle=p.get("camera_angle", ""),
            prompt_en=p.get("prompt_en", ""),
            prompt_zh=p.get("prompt_zh", ""),
            negative_prompt=p.get("negative_prompt", ""),
            # 文字元素 - 基础字段
            dialogue=dialogue,
            dialogue_speaker=dialogue_speaker,
            narration=narration,
            sound_effects=sound_effects,
            # 文字元素 - 扩展字段
            dialogue_bubble_type=p.get("dialogue_bubble_type", "normal") or "normal",
            dialogue_position=p.get("dialogue_position", "top-right") or "top-right",
            dialogue_emotion=p.get("dialogue_emotion", "") or "",
            narration_position=p.get("narration_position", "top") or "top",
            sound_effect_details=p.get("sound_effect_details") or [],
            # 视觉信息
            characters=p.get("characters") or [],
            is_key_panel=p.get("is_key_panel", False),
            # 参考图（用于 img2img）
            reference_image_paths=p.get("reference_image_paths") or [],
        ))

    return GenerateResponse(
        chapter_number=data.get("chapter_number", 0),
        style=data.get("style", "manga"),
        character_profiles=data.get("character_profiles", {}),
        total_pages=data.get("total_pages", 0),
        total_panels=data.get("total_panels", 0),
        scenes=scenes,
        panels=panels,
    )
