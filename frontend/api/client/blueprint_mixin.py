"""
蓝图生成 Mixin

提供蓝图生成和管理的API方法。
"""

from typing import Any, Dict, List, Optional

from .constants import TimeoutConfig


class BlueprintMixin:
    """蓝图生成方法 Mixin"""

    def generate_blueprint(
        self,
        project_id: str,
        force_regenerate: bool = False,
        allow_incomplete: bool = False,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        生成蓝图

        Args:
            project_id: 项目ID
            force_regenerate: 是否强制重新生成（会删除已有章节大纲）
            allow_incomplete: 是否允许在灵感对话未完成时生成蓝图（随机生成模式）
            async_mode: 是否使用异步模式（默认False）

        Returns:
            同步模式：完整蓝图数据
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        """
        params = {
            'force_regenerate': force_regenerate,
            'allow_incomplete': allow_incomplete,
            'async_mode': async_mode
        }
        # 异步模式只需等待任务启动，同步模式需要等待完整生成
        timeout = 30 if async_mode else 480
        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/generate',
            params=params,
            timeout=timeout
        )

    def update_blueprint(
        self,
        project_id: str,
        blueprint_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新蓝图

        Args:
            project_id: 项目ID
            blueprint_data: 蓝图数据

        Returns:
            更新结果
        """
        return self._request(
            'PATCH',
            f'/api/novels/{project_id}/blueprint',
            blueprint_data
        )

    def batch_update_blueprint(
        self,
        project_id: str,
        blueprint_updates: Optional[Dict[str, Any]] = None,
        chapter_outline_updates: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        批量更新蓝图字段和章节大纲

        支持同时更新蓝图字段和章节大纲，用于前端批量保存功能。
        所有更新在一个事务中完成，确保数据一致性。

        Args:
            project_id: 项目ID
            blueprint_updates: 蓝图字段更新，如 {"title": "新标题", "genre": "玄幻"}
            chapter_outline_updates: 章节大纲更新列表，如 [
                {"chapter_number": 1, "title": "第一章", "summary": "..."},
                {"chapter_number": 2, "title": "第二章", "summary": "..."}
            ]

        Returns:
            更新后的项目完整信息
        """
        payload = {}
        if blueprint_updates:
            payload["blueprint_updates"] = blueprint_updates
        if chapter_outline_updates:
            payload["chapter_outline_updates"] = chapter_outline_updates

        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/batch-update',
            payload
        )

    def refine_blueprint(
        self,
        project_id: str,
        refinement_instruction: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        优化蓝图

        Args:
            project_id: 项目ID
            refinement_instruction: 优化指令，描述想要改进的方向
            force: 是否强制优化（将删除所有章节大纲、部分大纲、章节内容）

        Returns:
            优化后的蓝图
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/refine',
            {'refinement_instruction': refinement_instruction},
            params={'force': force},
            timeout=480
        )

    # ==================== 小说头像 ====================

    def generate_avatar(self, project_id: str) -> Dict[str, Any]:
        """
        为小说生成SVG头像

        根据小说的类型、风格、氛围，使用LLM生成一个匹配的小动物SVG图标。

        Args:
            project_id: 项目ID

        Returns:
            头像数据：
            {
                "avatar_svg": "<svg>...</svg>",  # 完整SVG代码
                "animal": "fox",                  # 动物英文名
                "animal_cn": "狐狸"               # 动物中文名
            }
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/avatar/generate',
            timeout=TimeoutConfig.READ_GENERATION
        )

    def delete_avatar(self, project_id: str) -> Dict[str, Any]:
        """
        删除小说的头像

        Args:
            project_id: 项目ID

        Returns:
            {"success": True}
        """
        return self._request(
            'DELETE',
            f'/api/novels/{project_id}/avatar'
        )
