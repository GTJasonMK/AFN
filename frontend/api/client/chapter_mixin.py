"""
章节生成 Mixin

提供章节生成和管理的API方法。
"""

from typing import Any, Dict, Optional


class ChapterMixin:
    """章节生成方法 Mixin"""

    def generate_chapter(
        self,
        project_id: str,
        chapter_number: int,
        writing_notes: Optional[str] = None,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        生成章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            writing_notes: 写作指令（可选）
            async_mode: 是否使用异步模式（默认False）

        Returns:
            同步模式：生成结果（包含多个版本）
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        """
        data = {
            'chapter_number': chapter_number,
            'writing_notes': writing_notes or ''
        }
        params = {'async_mode': async_mode}
        # 同步模式需要较长超时，异步模式只需等待任务启动
        timeout = 30 if async_mode else 600
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/generate',
            data,
            params=params,
            timeout=timeout
        )

    def preview_chapter_prompt(
        self,
        project_id: str,
        chapter_number: int,
        writing_notes: Optional[str] = None,
        is_retry: bool = False,
        use_rag: bool = True
    ) -> Dict[str, Any]:
        """
        预览章节生成的提示词（用于测试RAG效果）

        此方法只构建提示词，不调用LLM生成内容。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            writing_notes: 写作备注/优化方向（可选）
            is_retry: 是否为重新生成模式（使用简化提示词，不含完整前情摘要）
            use_rag: 是否启用RAG检索

        Returns:
            提示词预览数据，包含：
            - system_prompt: 系统提示词
            - user_prompt: 用户提示词
            - rag_statistics: RAG检索统计
            - prompt_sections: 各部分内容
            - total_length: 总长度
            - estimated_tokens: 估算token数
        """
        data = {
            'chapter_number': chapter_number,
            'is_retry': is_retry,
            'use_rag': use_rag,
        }
        if writing_notes:
            data['writing_notes'] = writing_notes

        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/preview-prompt',
            data,
            timeout=120
        )

    def select_chapter_version(
        self,
        project_id: str,
        chapter_number: int,
        version_index: int
    ) -> Dict[str, Any]:
        """
        选择章节版本

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            version_index: 版本索引

        Returns:
            选择结果
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/select',
            {
                'chapter_number': chapter_number,
                'version_index': version_index
            }
        )

    def evaluate_chapter(
        self,
        project_id: str,
        chapter_number: int
    ) -> Dict[str, Any]:
        """
        评审章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            评审结果
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/evaluate',
            {'chapter_number': chapter_number},
            timeout=300
        )

    def retry_chapter_version(
        self,
        project_id: str,
        chapter_number: int,
        version_index: int,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新生成指定章节的某个版本

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            version_index: 版本索引
            custom_prompt: 自定义优化提示词（可选）

        Returns:
            更新后的项目数据
        """
        data = {
            'chapter_number': chapter_number,
            'version_index': version_index
        }
        if custom_prompt:
            data['custom_prompt'] = custom_prompt

        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/retry-version',
            data,
            timeout=600
        )

    def update_chapter(
        self,
        project_id: str,
        chapter_number: int,
        content: str,
        trigger_rag: bool = False
    ) -> Dict[str, Any]:
        """
        更新章节内容

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            content: 新内容
            trigger_rag: 是否触发RAG处理（摘要、分析、索引、向量入库），默认False仅保存内容

        Returns:
            更新结果
        """
        return self._request(
            'PUT',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}',
            {'content': content, 'trigger_rag': trigger_rag},
            timeout=300 if trigger_rag else 30  # RAG处理需要较长超时
        )

    def import_chapter(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        content: str
    ) -> Dict[str, Any]:
        """
        导入章节内容

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: 章节标题
            content: 章节内容

        Returns:
            更新后的项目数据
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/import',
            {
                'chapter_number': chapter_number,
                'title': title,
                'content': content
            }
        )

    def export_chapters(
        self,
        project_id: str,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> bytes:
        """
        导出章节为TXT文件

        Args:
            project_id: 项目ID
            start: 起始章节号
            end: 结束章节号

        Returns:
            文件内容（字节）
        """
        params = {}
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end

        return self._request_raw(
            'GET',
            f'/api/writer/novels/{project_id}/chapters/export',
            params=params,
            timeout=60,
            return_type='content'
        )
