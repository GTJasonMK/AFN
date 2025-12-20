"""
队列API混入类

提供队列状态查询和配置管理的API调用。
"""

from typing import Dict, Any, Optional


class QueueMixin:
    """队列管理API混入类"""

    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取所有队列的当前状态

        Returns:
            {
                "llm": {"active": int, "waiting": int, "max_concurrent": int, "total_processed": int},
                "image": {"active": int, "waiting": int, "max_concurrent": int, "total_processed": int}
            }
        """
        return self._request('GET', "/api/queue/status")

    def get_queue_config(self) -> Dict[str, int]:
        """
        获取队列配置

        Returns:
            {"llm_max_concurrent": int, "image_max_concurrent": int}
        """
        return self._request('GET', "/api/queue/config")

    def update_queue_config(
        self,
        llm_max_concurrent: Optional[int] = None,
        image_max_concurrent: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        更新队列配置

        Args:
            llm_max_concurrent: LLM最大并发数（1-10），None表示不修改
            image_max_concurrent: 图片最大并发数（1-5），None表示不修改

        Returns:
            更新后的配置 {"llm_max_concurrent": int, "image_max_concurrent": int}
        """
        payload = {}
        if llm_max_concurrent is not None:
            payload["llm_max_concurrent"] = llm_max_concurrent
        if image_max_concurrent is not None:
            payload["image_max_concurrent"] = image_max_concurrent

        return self._request('PUT', "/api/queue/config", payload)
