"""蓝图相关数据访问层"""

from typing import Dict, Iterable, List, Optional

from sqlalchemy import delete

from .base import BaseRepository
from ..models.novel import NovelBlueprint, BlueprintCharacter, BlueprintRelationship


class NovelBlueprintRepository(BaseRepository[NovelBlueprint]):
    """蓝图主表Repository"""

    model = NovelBlueprint

    async def get_by_project_id(self, project_id: str) -> Optional[NovelBlueprint]:
        """
        根据项目ID获取蓝图

        Args:
            project_id: 项目ID（蓝图表的主键）

        Returns:
            蓝图实例，不存在返回None
        """
        return await self.get(project_id=project_id)

    async def create_or_update(
        self,
        project_id: str,
        blueprint_data: Dict
    ) -> NovelBlueprint:
        """
        创建或更新蓝图

        Args:
            project_id: 项目ID
            blueprint_data: 蓝图数据字典

        Returns:
            蓝图实例
        """
        blueprint = await self.get_by_project_id(project_id)
        if not blueprint:
            blueprint = NovelBlueprint(project_id=project_id)
            self.session.add(blueprint)

        # 更新字段
        for key, value in blueprint_data.items():
            if hasattr(blueprint, key):
                setattr(blueprint, key, value)

        await self.session.flush()
        return blueprint

    async def delete_by_project_id(self, project_id: str) -> int:
        """
        删除项目的蓝图

        Args:
            project_id: 项目ID

        Returns:
            删除的记录数
        """
        # NovelBlueprint使用project_id作为主键，需要特殊处理
        stmt = delete(NovelBlueprint).where(NovelBlueprint.project_id == project_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount


class BlueprintCharacterRepository(BaseRepository[BlueprintCharacter]):
    """蓝图角色Repository"""

    model = BlueprintCharacter

    # list_by_project() 和 delete_by_project_id() 已由 BaseRepository 提供

    async def bulk_create(
        self,
        project_id: str,
        characters_data: List[Dict]
    ) -> None:
        """
        批量创建角色（先删除旧数据）

        Args:
            project_id: 项目ID
            characters_data: 角色数据列表
        """
        await self.delete_by_project_id(project_id)
        for index, data in enumerate(characters_data):
            self.session.add(BlueprintCharacter(
                project_id=project_id,
                name=data.get("name", ""),
                identity=data.get("identity"),
                personality=data.get("personality"),
                appearance=data.get("appearance"),  # 外貌特征
                goals=data.get("goals"),
                abilities=data.get("abilities"),
                relationship_to_protagonist=data.get("relationship_to_protagonist"),
                extra={
                    k: v for k, v in data.items()
                    if k not in {
                        "name", "identity", "personality", "appearance",
                        "goals", "abilities", "relationship_to_protagonist",
                    }
                },
                position=index,
            ))
        await self.session.flush()


class BlueprintRelationshipRepository(BaseRepository[BlueprintRelationship]):
    """蓝图关系Repository"""

    model = BlueprintRelationship

    # list_by_project() 和 delete_by_project_id() 已由 BaseRepository 提供

    async def bulk_create(
        self,
        project_id: str,
        relationships: List
    ) -> None:
        """
        批量创建关系（先删除旧数据）

        Args:
            project_id: 项目ID
            relationships: 关系数据列表
        """
        await self.delete_by_project_id(project_id)
        for index, relation in enumerate(relationships):
            # 支持dict和Pydantic对象
            if hasattr(relation, 'character_from'):
                char_from = relation.character_from
                char_to = relation.character_to
                desc = relation.description
            else:
                char_from = relation.get("character_from")
                char_to = relation.get("character_to")
                desc = relation.get("description")

            self.session.add(BlueprintRelationship(
                project_id=project_id,
                character_from=char_from,
                character_to=char_to,
                description=desc,
                position=index,
            ))
        await self.session.flush()
