"""
角色立绘 Mixin

提供角色立绘生成和管理的API方法。
"""

from typing import Any, Dict, List, Optional

from .constants import TimeoutConfig


class PortraitMixin:
    """角色立绘方法 Mixin"""

    # ==================== 立绘查询 ====================

    def get_project_portraits(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目的所有角色立绘

        Args:
            project_id: 项目ID

        Returns:
            立绘列表，包含 portraits 和 total 字段
        """
        return self._request('GET', f'/api/novels/{project_id}/character-portraits')

    def get_active_portraits(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目所有角色的激活立绘

        Args:
            project_id: 项目ID

        Returns:
            激活立绘列表
        """
        return self._request('GET', f'/api/novels/{project_id}/character-portraits/active')

    def get_character_portraits(
        self,
        project_id: str,
        character_name: str,
    ) -> Dict[str, Any]:
        """
        获取指定角色的所有立绘

        Args:
            project_id: 项目ID
            character_name: 角色名称

        Returns:
            角色的立绘列表
        """
        return self._request(
            'GET',
            f'/api/novels/{project_id}/character-portraits/{character_name}'
        )

    # ==================== 立绘生成 ====================

    def generate_portrait(
        self,
        project_id: str,
        character_name: str,
        style: str = "anime",
        character_description: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成角色立绘

        Args:
            project_id: 项目ID
            character_name: 角色名称
            style: 立绘风格（anime/manga/realistic）
            character_description: 角色外貌描述（可选，不提供则从蓝图获取）
            custom_prompt: 自定义提示词（可选）

        Returns:
            生成结果，包含 success 和 portrait 字段
        """
        data = {
            'character_name': character_name,
            'style': style,
        }
        if character_description:
            data['character_description'] = character_description
        if custom_prompt:
            data['custom_prompt'] = custom_prompt

        return self._request(
            'POST',
            f'/api/novels/{project_id}/character-portraits/generate',
            data,
            timeout=TimeoutConfig.READ_GENERATION
        )

    def regenerate_portrait(
        self,
        project_id: str,
        portrait_id: str,
        style: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        重新生成立绘

        Args:
            project_id: 项目ID
            portrait_id: 立绘ID
            style: 新的风格（可选，不提供则使用原风格）
            custom_prompt: 新的自定义提示词（可选）

        Returns:
            生成结果，包含 success 和 portrait 字段
        """
        data = {}
        if style:
            data['style'] = style
        if custom_prompt:
            data['custom_prompt'] = custom_prompt

        return self._request(
            'POST',
            f'/api/novels/{project_id}/character-portraits/{portrait_id}/regenerate',
            data if data else None,
            timeout=TimeoutConfig.READ_GENERATION
        )

    # ==================== 立绘管理 ====================

    def set_active_portrait(
        self,
        project_id: str,
        portrait_id: str,
    ) -> Dict[str, Any]:
        """
        设置立绘为激活状态

        Args:
            project_id: 项目ID
            portrait_id: 立绘ID

        Returns:
            更新后的立绘信息
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/character-portraits/{portrait_id}/set-active'
        )

    def delete_portrait(
        self,
        project_id: str,
        portrait_id: str,
    ) -> Dict[str, Any]:
        """
        删除立绘

        Args:
            project_id: 项目ID
            portrait_id: 立绘ID

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/novels/{project_id}/character-portraits/{portrait_id}'
        )

    # ==================== 立绘风格 ====================

    def get_portrait_styles(self) -> List[Dict[str, Any]]:
        """
        获取可用的立绘风格列表

        Returns:
            风格列表，每个风格包含 style, name, description, prompt_prefix 字段
        """
        return self._request('GET', '/api/character-portrait-styles')

    # ==================== 批量生成 ====================

    def auto_generate_portraits(
        self,
        project_id: str,
        character_profiles: Dict[str, str],
        style: str = "anime",
        exclude_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        自动批量生成缺失的角色立绘

        Args:
            project_id: 项目ID
            character_profiles: 角色外观描述字典 {角色名: 外观描述}
            style: 立绘风格（anime/manga/realistic）
            exclude_existing: 是否排除已有立绘的角色

        Returns:
            生成的立绘列表，包含 portraits 和 total 字段
        """
        data = {
            'character_profiles': character_profiles,
            'style': style,
            'exclude_existing': exclude_existing,
        }
        return self._request(
            'POST',
            f'/api/novels/{project_id}/character-portraits/auto-generate',
            data,
            timeout=TimeoutConfig.READ_GENERATION * 5  # 批量生成需要更长时间
        )

    def get_missing_portraits(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目中缺失立绘的角色列表

        Args:
            project_id: 项目ID

        Returns:
            包含 missing_characters, total_characters, missing_count 字段
        """
        return self._request(
            'GET',
            f'/api/novels/{project_id}/character-portraits/missing'
        )

    # ==================== 辅助方法 ====================

    def get_portrait_image_url(self, image_path: str) -> str:
        """
        获取立绘图片的完整URL

        Args:
            image_path: 图片相对路径（从API响应的image_path字段）

        Returns:
            图片完整URL
        """
        if not image_path:
            return ""
        return f"{self.base_url}/api/images/{image_path}"
