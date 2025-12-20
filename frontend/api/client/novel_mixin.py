"""
小说项目管理 Mixin

提供小说项目的CRUD操作方法。
"""

from typing import Any, Dict, List


class NovelMixin:
    """小说项目管理方法 Mixin"""

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._request('GET', '/health')

    # ==================== 小说项目管理 ====================

    def create_novel(
        self,
        title: str,
        initial_prompt: str = "",
        skip_inspiration: bool = False
    ) -> Dict[str, Any]:
        """
        创建小说项目

        Args:
            title: 小说标题
            initial_prompt: 初始提示词（自由创作模式时可为空）
            skip_inspiration: 是否跳过灵感对话（自由创作模式）

        Returns:
            项目信息
        """
        return self._request('POST', '/api/novels', {
            'title': title,
            'initial_prompt': initial_prompt,
            'skip_inspiration': skip_inspiration
        })

    def get_novels(self) -> List[Dict[str, Any]]:
        """获取项目列表"""
        return self._request('GET', '/api/novels')

    def get_novel(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详细信息
        """
        return self._request('GET', f'/api/novels/{project_id}')

    def get_section(self, project_id: str, section_type: str) -> Dict[str, Any]:
        """
        获取小说的特定section数据

        Args:
            project_id: 项目ID
            section_type: section类型（overview, world_setting, characters等）

        Returns:
            section数据
        """
        return self._request('GET', f'/api/novels/{project_id}/sections/{section_type}')

    def get_chapter(self, project_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        获取章节详情

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节详细信息
        """
        return self._request('GET', f'/api/novels/{project_id}/chapters/{chapter_number}')

    def export_novel(self, project_id: str, format_type: str = 'txt') -> str:
        """
        导出整本小说

        Args:
            project_id: 项目ID
            format_type: 导出格式（txt或markdown）

        Returns:
            导出的文本内容
        """
        return self._request_raw(
            'GET',
            f'/api/novels/{project_id}/export',
            params={'format': format_type},
            timeout=60,
            return_type='text'
        )

    def update_project(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新项目信息

        Args:
            project_id: 项目ID
            data: 更新数据

        Returns:
            更新后的项目信息
        """
        return self._request('PATCH', f'/api/novels/{project_id}', data)

    def delete_novels(self, project_ids: List[str]) -> Dict[str, Any]:
        """
        删除项目

        Args:
            project_ids: 项目ID列表

        Returns:
            删除结果
        """
        # 后端使用 Body(...) 不带 embed=True,期望裸JSON数组
        return self._request('DELETE', '/api/novels', project_ids)
