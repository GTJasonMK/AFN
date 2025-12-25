"""
主角档案 Mixin

提供主角档案管理、属性操作、章节同步、历史查询等API方法。
"""

from typing import Any, Dict, List, Optional

from .constants import TimeoutConfig


class ProtagonistMixin:
    """主角档案方法 Mixin"""

    # ==================== 档案CRUD ====================

    def get_protagonist_profiles(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目下所有主角档案列表

        Args:
            project_id: 项目ID

        Returns:
            档案摘要列表
        """
        return self._request('GET', f'/api/novels/{project_id}/protagonist-profiles')

    def create_protagonist_profile(
        self,
        project_id: str,
        character_name: str,
        explicit_attributes: Optional[Dict] = None,
        implicit_attributes: Optional[Dict] = None,
        social_attributes: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        创建主角档案

        Args:
            project_id: 项目ID
            character_name: 角色名称
            explicit_attributes: 初始显性属性
            implicit_attributes: 初始隐性属性
            social_attributes: 初始社会属性

        Returns:
            创建的档案信息
        """
        data = {
            'character_name': character_name,
        }
        if explicit_attributes:
            data['explicit_attributes'] = explicit_attributes
        if implicit_attributes:
            data['implicit_attributes'] = implicit_attributes
        if social_attributes:
            data['social_attributes'] = social_attributes

        return self._request('POST', f'/api/novels/{project_id}/protagonist-profiles', data)

    def get_protagonist_profile(
        self,
        project_id: str,
        character_name: str,
    ) -> Dict[str, Any]:
        """
        获取单个主角档案详情

        Args:
            project_id: 项目ID
            character_name: 角色名称

        Returns:
            档案详情
        """
        return self._request(
            'GET',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}'
        )

    def delete_protagonist_profile(
        self,
        project_id: str,
        character_name: str,
    ) -> Dict[str, Any]:
        """
        删除主角档案

        Args:
            project_id: 项目ID
            character_name: 角色名称

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}'
        )

    # ==================== 属性操作 ====================

    def add_protagonist_attribute(
        self,
        project_id: str,
        character_name: str,
        category: str,
        key: str,
        value: Any,
        event_cause: str,
        evidence: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        添加属性

        Args:
            project_id: 项目ID
            character_name: 角色名称
            category: 属性类别（explicit/implicit/social）
            key: 属性键名
            value: 属性值
            event_cause: 触发事件描述
            evidence: 原文引用（证据）
            chapter_number: 章节号

        Returns:
            属性变更记录
        """
        data = {
            'category': category,
            'key': key,
            'value': value,
            'event_cause': event_cause,
            'evidence': evidence,
            'chapter_number': chapter_number,
        }
        return self._request(
            'POST',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/attributes',
            data
        )

    def modify_protagonist_attribute(
        self,
        project_id: str,
        character_name: str,
        category: str,
        key: str,
        new_value: Any,
        event_cause: str,
        evidence: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        修改属性

        Args:
            project_id: 项目ID
            character_name: 角色名称
            category: 属性类别（explicit/implicit/social）
            key: 属性键名
            new_value: 新属性值
            event_cause: 触发事件描述
            evidence: 原文引用（证据）
            chapter_number: 章节号

        Returns:
            属性变更记录
        """
        data = {
            'new_value': new_value,
            'event_cause': event_cause,
            'evidence': evidence,
            'chapter_number': chapter_number,
        }
        return self._request(
            'PUT',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/attributes/{category}/{key}',
            data
        )

    def request_protagonist_attribute_deletion(
        self,
        project_id: str,
        character_name: str,
        category: str,
        key: str,
        reason: str,
        evidence: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        请求删除属性（标记删除，需连续5次标记才能真正删除）

        Args:
            project_id: 项目ID
            character_name: 角色名称
            category: 属性类别（explicit/implicit/social）
            key: 属性键名
            reason: 删除原因
            evidence: 原文引用（证据）
            chapter_number: 章节号

        Returns:
            删除标记记录
        """
        data = {
            'reason': reason,
            'evidence': evidence,
            'chapter_number': chapter_number,
        }
        return self._request(
            'DELETE',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/attributes/{category}/{key}',
            data
        )

    # ==================== 章节同步 ====================

    def sync_protagonist_from_chapter(
        self,
        project_id: str,
        character_name: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        从章节同步更新档案

        Args:
            project_id: 项目ID
            character_name: 角色名称
            chapter_number: 章节号

        Returns:
            同步结果，包含 changes_applied, behaviors_recorded, deletions_marked
        """
        data = {
            'chapter_number': chapter_number,
        }
        return self._request(
            'POST',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/sync',
            data,
            timeout=TimeoutConfig.READ_GENERATION
        )

    # ==================== 历史查询 ====================

    def get_protagonist_change_history(
        self,
        project_id: str,
        character_name: str,
        start_chapter: Optional[int] = None,
        end_chapter: Optional[int] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取属性变更历史

        Args:
            project_id: 项目ID
            character_name: 角色名称
            start_chapter: 起始章节（可选）
            end_chapter: 结束章节（可选）
            category: 属性类别过滤（可选）

        Returns:
            变更历史列表
        """
        params = {}
        if start_chapter is not None:
            params['start_chapter'] = start_chapter
        if end_chapter is not None:
            params['end_chapter'] = end_chapter
        if category:
            params['category'] = category

        return self._request(
            'GET',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/history',
            params=params
        )

    def get_protagonist_behavior_records(
        self,
        project_id: str,
        character_name: str,
        chapter: Optional[int] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        获取行为记录

        Args:
            project_id: 项目ID
            character_name: 角色名称
            chapter: 指定章节（可选）
            limit: 返回数量限制

        Returns:
            行为记录列表
        """
        params = {'limit': limit}
        if chapter is not None:
            params['chapter'] = chapter

        return self._request(
            'GET',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/behaviors',
            params=params
        )

    # ==================== 删除标记管理 ====================

    def get_protagonist_deletion_marks(
        self,
        project_id: str,
        character_name: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取删除标记列表

        Args:
            project_id: 项目ID
            character_name: 角色名称
            category: 属性类别过滤（可选）

        Returns:
            删除标记列表
        """
        params = {}
        if category:
            params['category'] = category

        return self._request(
            'GET',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/deletion-marks',
            params=params
        )

    def execute_protagonist_deletion(
        self,
        project_id: str,
        character_name: str,
        category: str,
        key: str,
    ) -> Dict[str, Any]:
        """
        手动执行删除（需满足5次标记条件）

        Args:
            project_id: 项目ID
            character_name: 角色名称
            category: 属性类别
            key: 属性键名

        Returns:
            执行结果
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/deletion-marks/{category}/{key}/execute'
        )

    def reset_protagonist_deletion_marks(
        self,
        project_id: str,
        character_name: str,
        category: str,
        key: str,
    ) -> Dict[str, Any]:
        """
        重置删除标记（用户决定保留该属性）

        Args:
            project_id: 项目ID
            character_name: 角色名称
            category: 属性类别
            key: 属性键名

        Returns:
            重置结果
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/deletion-marks/{category}/{key}/reset'
        )

    # ==================== 隐性属性分析 ====================

    def get_protagonist_implicit_stats(
        self,
        project_id: str,
        character_name: str,
        attribute_key: str,
        window: int = 10,
    ) -> Dict[str, Any]:
        """
        获取隐性属性的符合/不符合统计

        Args:
            project_id: 项目ID
            character_name: 角色名称
            attribute_key: 属性键名
            window: 统计窗口大小（章节数）

        Returns:
            统计结果，包含 total, conform_count, non_conform_count, conform_rate, threshold_reached
        """
        params = {
            'attribute_key': attribute_key,
            'window': window,
        }
        return self._request(
            'GET',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/implicit-stats',
            params=params
        )

    def check_protagonist_implicit_update(
        self,
        project_id: str,
        character_name: str,
        attribute_key: str,
    ) -> Dict[str, Any]:
        """
        检查是否需要更新某个隐性属性（LLM建议）

        Args:
            project_id: 项目ID
            character_name: 角色名称
            attribute_key: 属性键名

        Returns:
            检查结果，包含 decision, reasoning, suggested_new_value, evidence_summary
        """
        data = {
            'attribute_key': attribute_key,
        }
        return self._request(
            'POST',
            f'/api/novels/{project_id}/protagonist-profiles/{character_name}/implicit-check',
            data,
            timeout=TimeoutConfig.READ_NORMAL
        )
