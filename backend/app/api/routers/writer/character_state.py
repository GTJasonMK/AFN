"""
角色状态追踪 API

提供角色状态查询功能，包括：
- 获取指定章节的所有角色状态
- 获取角色的状态时间线
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user
from ....db.session import get_session
from ....schemas.user import UserInDB
from ....services.incremental_indexer import IncrementalIndexer
from ....services.novel_service import NovelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/novels/{project_id}/character-states", tags=["character-state"])


# ==================== 响应模型 ====================

class CharacterStateResponse(BaseModel):
    """单个角色状态"""
    character_name: str = Field(..., description="角色名")
    location: Optional[str] = Field(default=None, description="位置")
    status: Optional[str] = Field(default=None, description="状态描述")
    changes: List[str] = Field(default_factory=list, description="本章变化")
    emotional_state: Optional[str] = Field(default=None, description="情绪状态")


class ChapterCharacterStatesResponse(BaseModel):
    """章节角色状态响应"""
    project_id: str
    chapter_number: int
    character_states: dict = Field(default_factory=dict, description="角色状态字典")


class CharacterTimelineItem(BaseModel):
    """角色时间线项"""
    chapter_number: int = Field(..., description="章节号")
    location: Optional[str] = Field(default=None, description="位置")
    status: Optional[str] = Field(default=None, description="状态描述")
    changes: List[str] = Field(default_factory=list, description="本章变化")


class CharacterTimelineResponse(BaseModel):
    """角色时间线响应"""
    project_id: str
    character_name: str
    timeline: List[CharacterTimelineItem] = Field(default_factory=list)


# ==================== API 端点 ====================

@router.get(
    "/chapter/{chapter_number}",
    response_model=ChapterCharacterStatesResponse,
    summary="获取章节的角色状态",
    description="获取指定章节结束时所有角色的状态快照",
)
async def get_chapter_character_states(
    project_id: str,
    chapter_number: int,
    character_name: Optional[str] = Query(default=None, description="可选：指定角色名筛选"),
    session: AsyncSession = Depends(get_session),
    current_user: UserInDB = Depends(get_default_user),
):
    """获取指定章节的角色状态"""
    await NovelService(session).ensure_project_owner(project_id, current_user.id)

    indexer = IncrementalIndexer(session)
    states = await indexer.get_character_state_at_chapter(
        project_id=project_id,
        chapter_number=chapter_number,
        character_name=character_name,
    )

    return ChapterCharacterStatesResponse(
        project_id=project_id,
        chapter_number=chapter_number,
        character_states=states,
    )


@router.get(
    "/timeline/{character_name}",
    response_model=CharacterTimelineResponse,
    summary="获取角色状态时间线",
    description="获取指定角色在各章节的状态变化历程",
)
async def get_character_timeline(
    project_id: str,
    character_name: str,
    from_chapter: int = Query(default=1, ge=1, description="起始章节"),
    to_chapter: Optional[int] = Query(default=None, ge=1, description="结束章节（不指定则到最新）"),
    session: AsyncSession = Depends(get_session),
    current_user: UserInDB = Depends(get_default_user),
):
    """获取角色的状态时间线"""
    await NovelService(session).ensure_project_owner(project_id, current_user.id)

    indexer = IncrementalIndexer(session)
    timeline = await indexer.get_character_timeline(
        project_id=project_id,
        character_name=character_name,
        from_chapter=from_chapter,
        to_chapter=to_chapter,
    )

    return CharacterTimelineResponse(
        project_id=project_id,
        character_name=character_name,
        timeline=[CharacterTimelineItem(**item) for item in timeline],
    )


@router.get(
    "/characters",
    summary="获取项目中所有有状态记录的角色",
    description="列出项目中所有在角色状态索引中有记录的角色名称",
)
async def list_tracked_characters(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserInDB = Depends(get_default_user),
):
    """获取所有有状态记录的角色列表"""
    from sqlalchemy import select, distinct
    from ....models.novel import CharacterStateIndex

    await NovelService(session).ensure_project_owner(project_id, current_user.id)

    stmt = select(distinct(CharacterStateIndex.character_name)).where(
        CharacterStateIndex.project_id == project_id
    ).order_by(CharacterStateIndex.character_name)

    result = await session.execute(stmt)
    characters = [row[0] for row in result.fetchall()]

    return {
        "project_id": project_id,
        "characters": characters,
        "count": len(characters),
    }
