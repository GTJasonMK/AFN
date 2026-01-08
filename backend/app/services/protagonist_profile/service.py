"""主角档案服务

提供主角档案的CRUD操作和属性管理功能。
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...models.protagonist import (
    ProtagonistProfile,
    ProtagonistAttributeChange,
    ProtagonistSnapshot,
)
from ...repositories.protagonist_repository import (
    ProtagonistProfileRepository,
    ProtagonistAttributeChangeRepository,
    ProtagonistSnapshotRepository,
)
from ...schemas.protagonist import (
    ProtagonistProfileCreate,
    AttributeCategory,
    AttributeOperation,
)

logger = logging.getLogger(__name__)


class ProtagonistProfileService:
    """主角档案服务

    提供主角档案的CRUD操作、属性管理和变更历史查询功能。
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.profile_repo = ProtagonistProfileRepository(session)
        self.change_repo = ProtagonistAttributeChangeRepository(session)
        self.snapshot_repo = ProtagonistSnapshotRepository(session)

    # ============== CRUD 操作 ==============

    async def create_profile(
        self,
        project_id: str,
        character_name: str,
        initial_attributes: Optional[ProtagonistProfileCreate] = None
    ) -> ProtagonistProfile:
        """创建主角档案

        Args:
            project_id: 项目ID
            character_name: 角色名称
            initial_attributes: 初始属性（可选）

        Returns:
            创建的主角档案
        """
        # 检查是否已存在同名档案
        existing = await self.profile_repo.get_by_project_and_name(project_id, character_name)
        if existing:
            raise ValueError(f"项目 {project_id} 中已存在角色 {character_name} 的档案")

        profile = ProtagonistProfile(
            project_id=project_id,
            character_name=character_name,
            explicit_attributes=initial_attributes.explicit_attributes if initial_attributes else {},
            implicit_attributes=initial_attributes.implicit_attributes if initial_attributes else {},
            social_attributes=initial_attributes.social_attributes if initial_attributes else {},
            last_synced_chapter=0,
        )

        await self.profile_repo.add(profile)
        logger.info(f"创建主角档案: project={project_id}, character={character_name}")
        return profile

    async def get_profile(
        self,
        project_id: str,
        character_name: str
    ) -> Optional[ProtagonistProfile]:
        """获取主角档案"""
        return await self.profile_repo.get_by_project_and_name(project_id, character_name)

    async def get_profile_by_id(self, profile_id: int) -> Optional[ProtagonistProfile]:
        """根据ID获取主角档案"""
        return await self.profile_repo.get_by_id(profile_id)

    async def get_all_profiles(self, project_id: str) -> List[ProtagonistProfile]:
        """获取项目下所有主角档案"""
        profiles = await self.profile_repo.list_by_project_id(project_id)
        return list(profiles)

    async def delete_profile(self, profile_id: int) -> bool:
        """删除主角档案

        Args:
            profile_id: 档案ID

        Returns:
            是否删除成功
        """
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            return False

        await self.profile_repo.delete(profile)
        logger.info(f"删除主角档案: id={profile_id}")
        return True

    # ============== 属性操作 ==============

    async def add_attribute(
        self,
        profile_id: int,
        category: str,
        key: str,
        value: Any,
        event_cause: str,
        evidence: str,
        chapter_number: int
    ) -> ProtagonistAttributeChange:
        """添加属性

        Args:
            profile_id: 档案ID
            category: 属性类别 (explicit/implicit/social)
            key: 属性键名
            value: 属性值
            event_cause: 触发事件描述
            evidence: 原文引用证据
            chapter_number: 章节号

        Returns:
            属性变更记录
        """
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"档案 {profile_id} 不存在")

        # 获取对应的属性字典
        attr_dict = self._get_attribute_dict(profile, category)

        # 检查是否已存在
        if key in attr_dict:
            raise ValueError(f"属性 {key} 已存在于 {category} 中，请使用modify操作")

        # 更新属性
        attr_dict[key] = value
        self._set_attribute_dict(profile, category, attr_dict)

        # 创建变更记录
        change = ProtagonistAttributeChange(
            profile_id=profile_id,
            chapter_number=chapter_number,
            attribute_category=category,
            attribute_key=key,
            operation=AttributeOperation.ADD.value,
            old_value=None,
            new_value=json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value,
            change_description=f"添加{category}属性: {key}",
            event_cause=event_cause,
            evidence=evidence,
        )

        await self.change_repo.add(change)
        await self.session.flush()

        logger.info(f"添加属性: profile={profile_id}, {category}.{key}")
        return change

    async def modify_attribute(
        self,
        profile_id: int,
        category: str,
        key: str,
        new_value: Any,
        event_cause: str,
        evidence: str,
        chapter_number: int
    ) -> ProtagonistAttributeChange:
        """修改属性

        Args:
            profile_id: 档案ID
            category: 属性类别
            key: 属性键名
            new_value: 新属性值
            event_cause: 触发事件描述
            evidence: 原文引用证据
            chapter_number: 章节号

        Returns:
            属性变更记录
        """
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"档案 {profile_id} 不存在")

        # 获取对应的属性字典
        attr_dict = self._get_attribute_dict(profile, category)

        # 检查是否存在
        if key not in attr_dict:
            raise ValueError(f"属性 {key} 不存在于 {category} 中，请使用add操作")

        old_value = attr_dict[key]

        # 更新属性
        attr_dict[key] = new_value
        self._set_attribute_dict(profile, category, attr_dict)

        # 创建变更记录
        change = ProtagonistAttributeChange(
            profile_id=profile_id,
            chapter_number=chapter_number,
            attribute_category=category,
            attribute_key=key,
            operation=AttributeOperation.MODIFY.value,
            old_value=json.dumps(old_value, ensure_ascii=False) if not isinstance(old_value, str) else old_value,
            new_value=json.dumps(new_value, ensure_ascii=False) if not isinstance(new_value, str) else new_value,
            change_description=f"修改{category}属性: {key}",
            event_cause=event_cause,
            evidence=evidence,
        )

        await self.change_repo.add(change)
        await self.session.flush()

        logger.info(f"修改属性: profile={profile_id}, {category}.{key}")
        return change

    async def delete_attribute(
        self,
        profile_id: int,
        category: str,
        key: str,
        event_cause: str,
        evidence: str,
        chapter_number: int
    ) -> ProtagonistAttributeChange:
        """删除属性（直接删除，非标记删除）

        注意：通常应使用删除保护机制（request_deletion）而非此方法。
        此方法用于达到删除阈值后的实际删除操作。

        Args:
            profile_id: 档案ID
            category: 属性类别
            key: 属性键名
            event_cause: 触发事件描述
            evidence: 原文引用证据
            chapter_number: 章节号

        Returns:
            属性变更记录
        """
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"档案 {profile_id} 不存在")

        # 获取对应的属性字典
        attr_dict = self._get_attribute_dict(profile, category)

        # 检查是否存在
        if key not in attr_dict:
            raise ValueError(f"属性 {key} 不存在于 {category} 中")

        old_value = attr_dict[key]

        # 删除属性
        del attr_dict[key]
        self._set_attribute_dict(profile, category, attr_dict)

        # 创建变更记录
        change = ProtagonistAttributeChange(
            profile_id=profile_id,
            chapter_number=chapter_number,
            attribute_category=category,
            attribute_key=key,
            operation=AttributeOperation.DELETE.value,
            old_value=json.dumps(old_value, ensure_ascii=False) if not isinstance(old_value, str) else old_value,
            new_value=None,
            change_description=f"删除{category}属性: {key}",
            event_cause=event_cause,
            evidence=evidence,
        )

        await self.change_repo.add(change)
        await self.session.flush()

        logger.info(f"删除属性: profile={profile_id}, {category}.{key}")
        return change

    # ============== 查询操作 ==============

    async def get_change_history(
        self,
        profile_id: int,
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[ProtagonistAttributeChange]:
        """获取属性变更历史"""
        return await self.change_repo.list_by_profile(
            profile_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter,
            category=category
        )

    async def get_current_state(self, profile_id: int) -> Dict[str, Any]:
        """获取主角当前状态快照

        Returns:
            包含三类属性的字典
        """
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"档案 {profile_id} 不存在")

        return {
            "explicit": profile.explicit_attributes,
            "implicit": profile.implicit_attributes,
            "social": profile.social_attributes,
            "last_synced_chapter": profile.last_synced_chapter,
        }

    async def update_synced_chapter(self, profile_id: int, chapter_number: int) -> None:
        """更新最后同步的章节号"""
        profile = await self.profile_repo.get_by_id(profile_id)
        if profile:
            await self.profile_repo.update_fields(profile, last_synced_chapter=chapter_number)

    # ============== 辅助方法 ==============

    def _get_attribute_dict(self, profile: ProtagonistProfile, category: str) -> Dict[str, Any]:
        """获取指定类别的属性字典"""
        if category == AttributeCategory.EXPLICIT.value:
            return dict(profile.explicit_attributes or {})
        elif category == AttributeCategory.IMPLICIT.value:
            return dict(profile.implicit_attributes or {})
        elif category == AttributeCategory.SOCIAL.value:
            return dict(profile.social_attributes or {})
        else:
            raise ValueError(f"无效的属性类别: {category}")

    def _set_attribute_dict(self, profile: ProtagonistProfile, category: str, attr_dict: Dict[str, Any]) -> None:
        """设置指定类别的属性字典"""
        if category == AttributeCategory.EXPLICIT.value:
            profile.explicit_attributes = attr_dict
        elif category == AttributeCategory.IMPLICIT.value:
            profile.implicit_attributes = attr_dict
        elif category == AttributeCategory.SOCIAL.value:
            profile.social_attributes = attr_dict
        else:
            raise ValueError(f"无效的属性类别: {category}")

    # ============== 快照操作（类Git节点） ==============

    async def create_snapshot(
        self,
        profile_id: int,
        chapter_number: int,
        changes_in_chapter: int = 0,
        behaviors_in_chapter: int = 0
    ) -> ProtagonistSnapshot:
        """创建章节状态快照

        在章节同步后调用，保存该章节结束时的完整状态。
        类似Git的commit节点。

        Args:
            profile_id: 档案ID
            chapter_number: 章节号
            changes_in_chapter: 本章变更数量
            behaviors_in_chapter: 本章行为记录数

        Returns:
            创建的快照实例
        """
        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"档案 {profile_id} 不存在")

        snapshot = await self.snapshot_repo.create_snapshot(
            profile_id=profile_id,
            chapter_number=chapter_number,
            explicit_attributes=dict(profile.explicit_attributes or {}),
            implicit_attributes=dict(profile.implicit_attributes or {}),
            social_attributes=dict(profile.social_attributes or {}),
            changes_in_chapter=changes_in_chapter,
            behaviors_in_chapter=behaviors_in_chapter,
        )

        logger.info(
            f"创建状态快照: profile={profile_id}, chapter={chapter_number}, "
            f"changes={changes_in_chapter}, behaviors={behaviors_in_chapter}"
        )
        return snapshot

    async def get_snapshot_at_chapter(
        self,
        profile_id: int,
        chapter_number: int
    ) -> Optional[ProtagonistSnapshot]:
        """获取指定章节的快照

        用于时间旅行：查看某章节结束时角色的状态。

        Args:
            profile_id: 档案ID
            chapter_number: 章节号

        Returns:
            快照实例，不存在返回None
        """
        return await self.snapshot_repo.get_snapshot_at_chapter(profile_id, chapter_number)

    async def get_all_snapshots(
        self,
        profile_id: int,
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None
    ) -> List[ProtagonistSnapshot]:
        """获取档案的所有快照

        Args:
            profile_id: 档案ID
            start_chapter: 起始章节（可选）
            end_chapter: 结束章节（可选）

        Returns:
            快照列表（按章节号升序）
        """
        return await self.snapshot_repo.list_by_profile(
            profile_id,
            start_chapter=start_chapter,
            end_chapter=end_chapter
        )

    async def diff_between_chapters(
        self,
        profile_id: int,
        from_chapter: int,
        to_chapter: int
    ) -> Dict[str, Any]:
        """比较两个章节之间的状态差异

        类似Git的diff功能。返回从from_chapter到to_chapter的状态变化。

        Args:
            profile_id: 档案ID
            from_chapter: 起始章节号
            to_chapter: 目标章节号

        Returns:
            差异字典，包含added/modified/deleted三类变化
        """
        from_snapshot = await self.snapshot_repo.get_snapshot_at_chapter(profile_id, from_chapter)
        to_snapshot = await self.snapshot_repo.get_snapshot_at_chapter(profile_id, to_chapter)

        # 如果没有from_snapshot，使用空状态
        from_state = {
            "explicit": from_snapshot.explicit_attributes if from_snapshot else {},
            "implicit": from_snapshot.implicit_attributes if from_snapshot else {},
            "social": from_snapshot.social_attributes if from_snapshot else {},
        }

        # 如果没有to_snapshot，使用当前状态
        if to_snapshot:
            to_state = {
                "explicit": to_snapshot.explicit_attributes,
                "implicit": to_snapshot.implicit_attributes,
                "social": to_snapshot.social_attributes,
            }
        else:
            profile = await self.profile_repo.get_by_id(profile_id)
            if not profile:
                raise ValueError(f"档案 {profile_id} 不存在")
            to_state = {
                "explicit": profile.explicit_attributes or {},
                "implicit": profile.implicit_attributes or {},
                "social": profile.social_attributes or {},
            }

        # 计算差异
        diff = {
            "from_chapter": from_chapter,
            "to_chapter": to_chapter,
            "categories": {}
        }

        for category in ["explicit", "implicit", "social"]:
            from_attrs = from_state.get(category, {})
            to_attrs = to_state.get(category, {})

            category_diff = self._diff_attributes(from_attrs, to_attrs)
            if category_diff["added"] or category_diff["modified"] or category_diff["deleted"]:
                diff["categories"][category] = category_diff

        return diff

    def _diff_attributes(
        self,
        from_attrs: Dict[str, Any],
        to_attrs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算两个属性字典之间的差异

        Args:
            from_attrs: 原属性字典
            to_attrs: 目标属性字典

        Returns:
            差异字典: {added: {}, modified: {}, deleted: {}}
        """
        added = {}
        modified = {}
        deleted = {}

        # 查找新增和修改
        for key, value in to_attrs.items():
            if key not in from_attrs:
                added[key] = value
            elif from_attrs[key] != value:
                modified[key] = {
                    "from": from_attrs[key],
                    "to": value
                }

        # 查找删除
        for key in from_attrs:
            if key not in to_attrs:
                deleted[key] = from_attrs[key]

        return {
            "added": added,
            "modified": modified,
            "deleted": deleted,
        }

    async def rollback_to_chapter(
        self,
        profile_id: int,
        target_chapter: int
    ) -> bool:
        """回滚到指定章节的状态

        类似Git的reset功能。将档案状态恢复到某章节的快照状态。

        Args:
            profile_id: 档案ID
            target_chapter: 目标章节号

        Returns:
            是否成功回滚
        """
        snapshot = await self.snapshot_repo.get_snapshot_at_chapter(profile_id, target_chapter)
        if not snapshot:
            logger.warning(f"无法回滚: 未找到章节 {target_chapter} 的快照")
            return False

        profile = await self.profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError(f"档案 {profile_id} 不存在")

        # 恢复状态
        profile.explicit_attributes = dict(snapshot.explicit_attributes)
        profile.implicit_attributes = dict(snapshot.implicit_attributes)
        profile.social_attributes = dict(snapshot.social_attributes)
        profile.last_synced_chapter = target_chapter

        # 删除目标章节之后的快照
        deleted_count = await self.snapshot_repo.delete_after_chapter(profile_id, target_chapter)

        await self.session.flush()

        logger.info(
            f"状态回滚: profile={profile_id}, target_chapter={target_chapter}, "
            f"deleted_snapshots={deleted_count}"
        )
        return True

    async def get_state_at_chapter(
        self,
        profile_id: int,
        chapter_number: int
    ) -> Dict[str, Any]:
        """获取指定章节的状态（时间旅行）

        如果有快照则返回快照状态，否则返回空状态。

        Args:
            profile_id: 档案ID
            chapter_number: 章节号

        Returns:
            状态字典
        """
        snapshot = await self.snapshot_repo.get_snapshot_at_chapter(profile_id, chapter_number)

        if snapshot:
            return {
                "chapter_number": chapter_number,
                "explicit": snapshot.explicit_attributes,
                "implicit": snapshot.implicit_attributes,
                "social": snapshot.social_attributes,
                "changes_in_chapter": snapshot.changes_in_chapter,
                "behaviors_in_chapter": snapshot.behaviors_in_chapter,
                "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
            }
        else:
            return {
                "chapter_number": chapter_number,
                "explicit": {},
                "implicit": {},
                "social": {},
                "changes_in_chapter": 0,
                "behaviors_in_chapter": 0,
                "created_at": None,
            }
