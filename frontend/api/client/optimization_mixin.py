"""
RAG和正文优化 Mixin

提供RAG检索和正文优化的API方法。
"""

from typing import Any, Dict

from .constants import TimeoutConfig


class OptimizationMixin:
    """RAG和正文优化方法 Mixin"""

    # ==================== RAG检索 ====================

    def query_rag(
        self,
        project_id: str,
        query: str,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        执行RAG检索查询

        对指定项目执行向量检索，返回与查询文本最相关的剧情片段和章节摘要。
        用于测试和验证RAG检索效果。

        Args:
            project_id: 项目ID
            query: 查询文本
            top_k: 返回结果数量（默认10）

        Returns:
            RAG检索结果：
            {
                "query": "查询文本",
                "chunks": [
                    {
                        "content": "片段内容",
                        "chapter_number": 1,
                        "chapter_title": "章节标题",
                        "score": 0.123,  # 越小越相似
                        "metadata": {}
                    },
                    ...
                ],
                "summaries": [
                    {
                        "chapter_number": 1,
                        "title": "章节标题",
                        "summary": "章节摘要",
                        "score": 0.123
                    },
                    ...
                ],
                "embedding_dimension": 1536,
                "message": "提示信息（可选）"
            }
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/rag/query',
            {
                'query': query,
                'top_k': top_k
            },
            timeout=TimeoutConfig.READ_NORMAL
        )

    # ==================== 正文优化 ====================

    def get_optimize_chapter_url(
        self,
        project_id: str,
        chapter_number: int
    ) -> str:
        """
        获取章节优化的SSE流URL

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            SSE流URL
        """
        return f"{self.base_url}/api/writer/novels/{project_id}/chapters/{chapter_number}/optimize"

    def preview_paragraphs(
        self,
        project_id: str,
        content: str
    ) -> Dict[str, Any]:
        """
        预览段落分割结果

        用于在开始优化前预览段落分割效果。

        Args:
            project_id: 项目ID
            content: 章节内容

        Returns:
            段落预览数据：
            {
                "paragraphs": [
                    {
                        "index": 0,
                        "text": "段落内容",
                        "length": 100
                    },
                    ...
                ],
                "total_paragraphs": 10,
                "total_characters": 5000
            }
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/preview-paragraphs',
            {'content': content},
            timeout=TimeoutConfig.READ_QUICK
        )

    def continue_optimization_session(self, session_id: str) -> Dict[str, Any]:
        """
        继续暂停的优化会话

        在Review模式下，用户处理完建议后调用此方法让后端继续分析。

        Args:
            session_id: 会话ID（从workflow_start事件获取）

        Returns:
            操作结果: {"success": bool, "message": str}
        """
        return self._request(
            'POST',
            f'/api/writer/optimization-sessions/{session_id}/continue',
        )

    def cancel_optimization_session(self, session_id: str) -> Dict[str, Any]:
        """
        取消优化会话

        取消正在进行的优化分析。

        Args:
            session_id: 会话ID

        Returns:
            操作结果: {"success": bool, "message": str}
        """
        return self._request(
            'POST',
            f'/api/writer/optimization-sessions/{session_id}/cancel',
        )

    def get_optimization_session(self, session_id: str) -> Dict[str, Any]:
        """
        获取优化会话状态

        Args:
            session_id: 会话ID

        Returns:
            会话状态信息
        """
        return self._request(
            'GET',
            f'/api/writer/optimization-sessions/{session_id}',
        )
