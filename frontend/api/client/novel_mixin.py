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
            title: 项目标题
            initial_prompt: 初始提示词（自由创作模式时可为空）
            skip_inspiration: 是否跳过灵感对话（自由创作模式）

        Returns:
            项目信息
        """
        return self._request_api('POST', 'novels', data={
            'title': title,
            'initial_prompt': initial_prompt,
            'skip_inspiration': skip_inspiration
        })

    def get_novels(self) -> List[Dict[str, Any]]:
        """获取项目列表"""
        return self._request_api('GET', 'novels')

    def get_novel(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详细信息
        """
        return self._request_api('GET', 'novels', project_id)

    def get_section(self, project_id: str, section_type: str) -> Dict[str, Any]:
        """
        获取小说的特定section数据

        Args:
            project_id: 项目ID
            section_type: section类型（overview, world_setting, characters等）

        Returns:
            section数据
        """
        return self._request_api(
            'GET',
            'novels',
            project_id,
            'sections',
            section_type
        )

    def get_chapter(self, project_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        获取章节详情

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节详细信息
        """
        return self._request_api(
            'GET',
            'novels',
            project_id,
            'chapters',
            chapter_number
        )

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
        return self._request_api('PATCH', 'novels', project_id, data=data)

    def delete_novels(self, project_ids: List[str]) -> Dict[str, Any]:
        """
        删除项目

        Args:
            project_ids: 项目ID列表

        Returns:
            删除结果
        """
        # 后端使用 Body(...) 不带 embed=True,期望裸JSON数组
        return self._request_api('DELETE', 'novels', data=project_ids)

    # ==================== RAG入库管理 ====================

    def check_rag_completeness(self, project_id: str) -> Dict[str, Any]:
        """
        检查项目RAG入库完整性

        返回各数据类型的入库状态。

        Args:
            project_id: 项目ID

        Returns:
            完整性检查结果：
            {
                "project_id": "xxx",
                "complete": true/false,
                "total_db_count": 100,
                "total_vector_count": 95,
                "total_new": 5,
                "total_modified": 0,
                "total_deleted": 0,
                "types": {
                    "inspiration": {
                        "display_name": "灵感对话",
                        "db_count": 10,
                        "vector_count": 10,
                        "complete": true,
                        ...
                    },
                    ...
                }
            }
        """
        return self._request_rag(
            'novels',
            project_id,
            'completeness',
            method='GET',
            timeout=120
        )

    def ingest_all_rag(self, project_id: str, force: bool = False) -> Dict[str, Any]:
        """
        完整入库项目RAG数据

        Args:
            project_id: 项目ID
            force: 是否强制全量重建（默认False）

        Returns:
            入库结果：
            {
                "project_id": "xxx",
                "success": true,
                "is_complete_before": true,
                "total_added": 50,
                "total_updated": 0,
                "total_skipped": 5,
                "results": {
                    "inspiration": {...},
                    ...
                }
            }
        """
        params = {'force': force} if force else None
        return self._request_rag(
            'novels',
            project_id,
            'ingest-all',
            method='POST',
            params=params,
            timeout=300  # 完整入库可能需要较长时间
        )

    def ingest_rag_by_type(self, project_id: str, data_type: str) -> Dict[str, Any]:
        """
        按类型入库RAG数据

        Args:
            project_id: 项目ID
            data_type: 数据类型（如inspiration, synopsis, character等）

        Returns:
            入库结果：
            {
                "data_type": "inspiration",
                "display_name": "灵感对话",
                "success": true,
                "added_count": 10,
                "updated_count": 0,
                "skipped": false,
                "error_message": null
            }
        """
        return self._request_rag(
            'novels',
            project_id,
            'ingest',
            method='POST',
            params={'data_type': data_type},
            timeout=120
        )

    def diagnose_rag(self, project_id: str) -> Dict[str, Any]:
        """
        RAG诊断

        返回详细的RAG系统状态。

        Args:
            project_id: 项目ID

        Returns:
            诊断结果：
            {
                "project_id": "xxx",
                "vector_store_enabled": true,
                "embedding_service_enabled": true,
                "completeness": {...},
                "data_type_list": [...]
            }
        """
        return self._request_rag(
            'novels',
            project_id,
            'diagnose',
            method='GET',
            timeout=120
        )
