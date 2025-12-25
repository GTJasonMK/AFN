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
)
from ...repositories.protagonist_repository import (
    ProtagonistProfileRepository,
    ProtagonistAttributeChangeRepository,
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
