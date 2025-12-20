"""
灵感对话 Mixin

提供灵感对话相关的API方法。
"""

from typing import Any, Dict, List


class InspirationMixin:
    """灵感对话方法 Mixin"""

    def inspiration_converse(
        self,
        project_id: str,
        user_input: str
    ) -> Dict[str, Any]:
        """
        灵感对话（推荐使用）

        Args:
            project_id: 项目ID
            user_input: 用户输入文本

        Returns:
            AI响应
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/inspiration/converse',
            {
                'user_input': {'message': user_input},
                'conversation_state': {}
            },
            timeout=240
        )

    def get_conversation_history(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目的灵感对话历史

        Args:
            project_id: 项目ID

        Returns:
            对话历史列表，每条包含role、content、created_at等字段
        """
        return self._request(
            'GET',
            f'/api/novels/{project_id}/inspiration/history'
        )
