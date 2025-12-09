"""
增量索引服务

负责在章节分析完成后，将提取的结构化信息存入索引表。
支持角色状态索引和伏笔索引的增量更新。
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.novel import CharacterStateIndex, ForeshadowingIndex
from ..schemas.novel import ChapterAnalysisData

logger = logging.getLogger(__name__)


class IncrementalIndexer:
    """增量索引器

    职责：
    1. 从章节分析数据中提取角色状态，更新CharacterStateIndex
    2. 从章节分析数据中提取伏笔信息，更新ForeshadowingIndex
    3. 处理伏笔回收，更新伏笔状态

    使用方式：
        indexer = IncrementalIndexer(session)
        await indexer.index_chapter_analysis(
            project_id=project_id,
            chapter_number=chapter_number,
            analysis_data=analysis_data,
        )
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def index_chapter_analysis(
        self,
        project_id: str,
        chapter_number: int,
        analysis_data: ChapterAnalysisData,
    ) -> Dict[str, int]:
        """索引章节分析数据

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            analysis_data: 章节分析数据

        Returns:
            Dict: 索引结果统计 {"character_states": n, "foreshadowing_planted": n, "foreshadowing_resolved": n}
        """
        stats = {
            "character_states": 0,
            "foreshadowing_planted": 0,
            "foreshadowing_resolved": 0,
        }

        # 1. 索引角色状态
        if analysis_data.character_states:
            stats["character_states"] = await self._index_character_states(
                project_id=project_id,
                chapter_number=chapter_number,
                character_states=analysis_data.character_states,
            )

        # 2. 索引伏笔信息
        if analysis_data.foreshadowing:
            # 2.1 处理新埋下的伏笔
            if analysis_data.foreshadowing.planted:
                stats["foreshadowing_planted"] = await self._index_planted_foreshadowing(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    planted=analysis_data.foreshadowing.planted,
                )

            # 2.2 处理回收的伏笔
            if analysis_data.foreshadowing.resolved:
                stats["foreshadowing_resolved"] = await self._resolve_foreshadowing(
                    project_id=project_id,
                    chapter_number=chapter_number,
                    resolved=analysis_data.foreshadowing.resolved,
                )

        logger.info(
            "章节分析索引完成: project=%s chapter=%d stats=%s",
            project_id,
            chapter_number,
            stats,
        )

        return stats

    async def _index_character_states(
        self,
        project_id: str,
        chapter_number: int,
        character_states: Dict[str, Any],
    ) -> int:
        """索引角色状态

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            character_states: 角色状态字典 {角色名: CharacterState}

        Returns:
            int: 索引的角色数量
        """
        # 先删除该章节的旧状态记录（如果存在）
        await self.session.execute(
            delete(CharacterStateIndex).where(
                CharacterStateIndex.project_id == project_id,
                CharacterStateIndex.chapter_number == chapter_number,
            )
        )

        indexed_count = 0
        for char_name, state in character_states.items():
            # 处理不同的state格式
            if hasattr(state, "location"):
                # Pydantic模型格式
                location = state.location
                status = state.status
                changes = state.changes if hasattr(state, "changes") else []
            elif isinstance(state, dict):
                # 字典格式
                location = state.get("location")
                status = state.get("status")
                changes = state.get("changes", [])
            else:
                continue

            state_record = CharacterStateIndex(
                project_id=project_id,
                chapter_number=chapter_number,
                character_name=char_name,
                location=location,
                status=status,
                changes=changes,
            )
            self.session.add(state_record)
            indexed_count += 1

        await self.session.flush()
        return indexed_count

    async def _index_planted_foreshadowing(
        self,
        project_id: str,
        chapter_number: int,
        planted: List[Any],
    ) -> int:
        """索引新埋下的伏笔

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            planted: 伏笔列表

        Returns:
            int: 索引的伏笔数量
        """
        indexed_count = 0
        for fs in planted:
            # 处理不同的格式
            if hasattr(fs, "description"):
                # Pydantic模型格式
                description = fs.description
                original_text = getattr(fs, "original_text", None)
                category = getattr(fs, "category", "plot_twist")
                priority = getattr(fs, "priority", "medium")
                related_entities = getattr(fs, "related_entities", [])
            elif isinstance(fs, dict):
                # 字典格式
                description = fs.get("description", "")
                original_text = fs.get("original_text")
                category = fs.get("category", "plot_twist")
                priority = fs.get("priority", "medium")
                related_entities = fs.get("related_entities", [])
            else:
                continue

            if not description:
                continue

            fs_record = ForeshadowingIndex(
                project_id=project_id,
                description=description,
                original_text=original_text,
                category=category,
                priority=priority,
                planted_chapter=chapter_number,
                status="pending",
                related_entities=related_entities,
            )
            self.session.add(fs_record)
            indexed_count += 1

        await self.session.flush()
        return indexed_count

    async def _resolve_foreshadowing(
        self,
        project_id: str,
        chapter_number: int,
        resolved: List[Any],
    ) -> int:
        """处理伏笔回收

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            resolved: 回收的伏笔列表

        Returns:
            int: 回收的伏笔数量
        """
        resolved_count = 0
        for item in resolved:
            # 处理不同的格式
            if hasattr(item, "id"):
                fs_id = item.id
                resolution = getattr(item, "resolution", "")
            elif isinstance(item, dict):
                fs_id = item.get("id")
                resolution = item.get("resolution", "")
            else:
                continue

            if not fs_id:
                continue

            # 尝试通过ID查找伏笔
            try:
                fs_id_int = int(fs_id)
                result = await self.session.execute(
                    select(ForeshadowingIndex).where(
                        ForeshadowingIndex.id == fs_id_int,
                        ForeshadowingIndex.project_id == project_id,
                    )
                )
                fs_record = result.scalar_one_or_none()
            except (ValueError, TypeError):
                # 如果ID不是整数，尝试通过描述匹配
                result = await self.session.execute(
                    select(ForeshadowingIndex).where(
                        ForeshadowingIndex.project_id == project_id,
                        ForeshadowingIndex.status == "pending",
                        ForeshadowingIndex.description.contains(str(fs_id)[:50]),
                    )
                )
                fs_record = result.scalar_one_or_none()

            if fs_record:
                fs_record.status = "resolved"
                fs_record.resolved_chapter = chapter_number
                fs_record.resolution = resolution
                resolved_count += 1

        await self.session.flush()
        return resolved_count

    async def get_pending_foreshadowing(
        self,
        project_id: str,
        current_chapter: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """获取待回收的伏笔列表

        Args:
            project_id: 项目ID
            current_chapter: 当前章节号
            limit: 返回数量限制

        Returns:
            List[Dict]: 伏笔列表
        """
        result = await self.session.execute(
            select(ForeshadowingIndex)
            .where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.status == "pending",
                ForeshadowingIndex.planted_chapter < current_chapter,
            )
            .order_by(
                # 高优先级优先
                ForeshadowingIndex.priority.desc(),
                # 埋得越久越优先
                ForeshadowingIndex.planted_chapter.asc(),
            )
            .limit(limit)
        )
        records = result.scalars().all()

        return [
            {
                "id": r.id,
                "description": r.description,
                "category": r.category,
                "priority": r.priority,
                "planted_chapter": r.planted_chapter,
                "related_entities": r.related_entities or [],
                "chapters_since_planted": current_chapter - r.planted_chapter,
            }
            for r in records
        ]

    async def get_character_state_at_chapter(
        self,
        project_id: str,
        chapter_number: int,
        character_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取指定章节的角色状态

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            character_name: 可选的角色名（不指定则返回所有角色）

        Returns:
            Dict: 角色状态字典
        """
        query = select(CharacterStateIndex).where(
            CharacterStateIndex.project_id == project_id,
            CharacterStateIndex.chapter_number == chapter_number,
        )

        if character_name:
            query = query.where(CharacterStateIndex.character_name == character_name)

        result = await self.session.execute(query)
        records = result.scalars().all()

        states = {}
        for r in records:
            states[r.character_name] = {
                "location": r.location,
                "status": r.status,
                "changes": r.changes or [],
                "emotional_state": r.emotional_state,
            }

        return states

    async def get_character_timeline(
        self,
        project_id: str,
        character_name: str,
        from_chapter: int = 1,
        to_chapter: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """获取角色的状态时间线

        Args:
            project_id: 项目ID
            character_name: 角色名
            from_chapter: 起始章节
            to_chapter: 结束章节（不指定则到最新）

        Returns:
            List[Dict]: 角色状态变化列表
        """
        query = select(CharacterStateIndex).where(
            CharacterStateIndex.project_id == project_id,
            CharacterStateIndex.character_name == character_name,
            CharacterStateIndex.chapter_number >= from_chapter,
        )

        if to_chapter:
            query = query.where(CharacterStateIndex.chapter_number <= to_chapter)

        query = query.order_by(CharacterStateIndex.chapter_number)

        result = await self.session.execute(query)
        records = result.scalars().all()

        return [
            {
                "chapter_number": r.chapter_number,
                "location": r.location,
                "status": r.status,
                "changes": r.changes or [],
            }
            for r in records
        ]

    async def cleanup_chapter_indexes(
        self,
        project_id: str,
        chapter_number: int,
    ) -> None:
        """清理指定章节的索引（用于重新生成时）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
        """
        # 删除角色状态
        await self.session.execute(
            delete(CharacterStateIndex).where(
                CharacterStateIndex.project_id == project_id,
                CharacterStateIndex.chapter_number == chapter_number,
            )
        )

        # 删除该章节埋下的伏笔（但不删除之前章节的）
        await self.session.execute(
            delete(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.planted_chapter == chapter_number,
            )
        )

        # 重置该章节回收的伏笔状态
        result = await self.session.execute(
            select(ForeshadowingIndex).where(
                ForeshadowingIndex.project_id == project_id,
                ForeshadowingIndex.resolved_chapter == chapter_number,
            )
        )
        for fs in result.scalars().all():
            fs.status = "pending"
            fs.resolved_chapter = None
            fs.resolution = None

        await self.session.flush()
        logger.info(
            "清理章节索引完成: project=%s chapter=%d",
            project_id,
            chapter_number,
        )
