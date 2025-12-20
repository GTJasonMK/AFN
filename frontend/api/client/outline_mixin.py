"""
大纲管理 Mixin

提供部分大纲和章节大纲的管理方法。
"""

from typing import Any, Dict, Optional

from utils.constants import NovelConstants


class OutlineMixin:
    """大纲管理方法 Mixin"""

    # ==================== 部分大纲 ====================

    def generate_part_outlines(
        self,
        project_id: str,
        total_chapters: int,
        chapters_per_part: int = NovelConstants.CHAPTERS_PER_PART
    ) -> Dict[str, Any]:
        """
        生成部分大纲

        Args:
            project_id: 项目ID
            total_chapters: 小说总章节数
            chapters_per_part: 每个部分的章节数

        Returns:
            大纲数据
        """
        data = {
            'total_chapters': total_chapters,
            'chapters_per_part': chapters_per_part
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/parts/generate',
            data=data,
            timeout=300
        )

    def get_part_outline_generation_status(self, project_id: str) -> Dict[str, Any]:
        """
        查询部分大纲生成状态（实际调用parts/progress接口）

        Args:
            project_id: 项目ID

        Returns:
            状态数据：
            {
                "parts": [...],  # 所有部分大纲列表
                "total_parts": int,  # 总部分数
                "completed_parts": int,  # 已完成部分数
                "status": "pending|partial|completed"  # 整体状态
            }
        """
        import requests
        try:
            return self._request(
                'GET',
                f'/api/writer/novels/{project_id}/parts/progress',
                silent_status_codes=[404]  # 静默处理 404 错误
            )
        except requests.exceptions.HTTPError as e:
            # 404 表示后端不支持此功能或项目没有部分大纲，返回默认空闲状态
            if e.response.status_code == 404:
                return {
                    "parts": [],
                    "total_parts": 0,
                    "completed_parts": 0,
                    "status": "pending"
                }
            # 其他错误继续抛出
            raise

    def regenerate_part_outlines(
        self,
        project_id: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新生成所有部分大纲（会删除所有章节大纲）

        Args:
            project_id: 项目ID
            prompt: 优化提示（可选）

        Returns:
            新的部分大纲
        """
        data = {'prompt': prompt} if prompt else {}
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/part-outlines/regenerate',
            data,
            timeout=300
        )

    def regenerate_last_part_outline(
        self,
        project_id: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新生成最后一个部分大纲

        Args:
            project_id: 项目ID
            prompt: 优化提示（可选）

        Returns:
            新的部分大纲
        """
        data = {'prompt': prompt} if prompt else {}
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/part-outlines/regenerate-last',
            data,
            timeout=300
        )

    def regenerate_specific_part_outline(
        self,
        project_id: str,
        part_number: int,
        prompt: Optional[str] = None,
        cascade_delete: bool = False
    ) -> Dict[str, Any]:
        """
        重新生成指定部分大纲（串行生成原则）

        Args:
            project_id: 项目ID
            part_number: 部分编号
            prompt: 优化提示（可选）
            cascade_delete: 是否级联删除后续部分和章节大纲

        Returns:
            新的部分大纲
        """
        data = {
            'prompt': prompt,
            'cascade_delete': cascade_delete
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/part-outlines/{part_number}/regenerate',
            data,
            timeout=300
        )

    def delete_part_outlines(
        self,
        project_id: str,
        count: int
    ) -> Dict[str, Any]:
        """
        删除最后N个部分大纲

        Args:
            project_id: 项目ID
            count: 要删除的数量

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/writer/novels/{project_id}/parts/delete-latest',
            params={'count': count},
            timeout=60
        )

    # ==================== 章节大纲 ====================

    def generate_chapter_outlines_by_count(
        self,
        project_id: str,
        count: int
    ) -> Dict[str, Any]:
        """
        灵活生成指定数量的章节大纲

        Args:
            project_id: 项目ID
            count: 生成数量

        Returns:
            生成结果
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapter-outlines/generate-by-count',
            {'count': count},
            timeout=600
        )

    def regenerate_chapter_outline(
        self,
        project_id: str,
        chapter_number: int,
        prompt: Optional[str] = None,
        cascade_delete: bool = False
    ) -> Dict[str, Any]:
        """
        重新生成指定章节大纲（串行生成原则）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            prompt: 优化提示（可选）
            cascade_delete: 是否级联删除后续章节大纲

        Returns:
            新的章节大纲
        """
        data = {
            'prompt': prompt,
            'cascade_delete': cascade_delete
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapter-outlines/{chapter_number}/regenerate',
            data,
            timeout=180
        )

    def update_chapter_outline(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        summary: str
    ) -> Dict[str, Any]:
        """
        更新章节大纲

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: 章节标题
            summary: 章节摘要

        Returns:
            更新后的项目信息
        """
        data = {
            'chapter_number': chapter_number,
            'title': title,
            'summary': summary
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/update-outline',
            data
        )

    def delete_chapters(
        self,
        project_id: str,
        count: int
    ) -> Dict[str, Any]:
        """
        删除最新的N章大纲

        Args:
            project_id: 项目ID
            count: 删除数量

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/writer/novels/{project_id}/chapter-outlines/delete-latest',
            {'count': count}
        )

    def generate_all_chapter_outlines(
        self,
        project_id: str,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        生成所有章节大纲（首次生成/短篇小说）

        用于项目初始化阶段一次性生成全部章节大纲，
        适合短篇小说（章节数<=50）。

        Args:
            project_id: 项目ID
            async_mode: 是否使用异步模式（默认False）

        Returns:
            同步模式：完整大纲数据
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        """
        params = {'async_mode': async_mode}
        timeout = 30 if async_mode else 400
        return self._request(
            'POST',
            f'/api/novels/{project_id}/chapter-outlines/generate',
            params=params,
            timeout=timeout
        )
