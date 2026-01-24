"""
工作流基类

提供统一的执行入口，减少同步与流式逻辑重复。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional


class GenerationWorkflowBase(ABC):
    """通用生成工作流基类"""

    def __init__(self) -> None:
        self._final_result: Optional[Any] = None

    async def execute(self) -> Any:
        """同步执行工作流"""
        async for _ in self._run_generation(streaming=False):
            pass
        return self._final_result

    async def execute_with_progress(self) -> AsyncIterator[dict]:
        """流式执行工作流并返回进度"""
        async for event in self._run_generation(streaming=True):
            yield event

    def _set_final_result(self, result: Any) -> None:
        """记录最终结果"""
        self._final_result = result

    @abstractmethod
    async def _run_generation(self, streaming: bool) -> AsyncIterator[dict]:
        """执行工作流（子类实现）"""


__all__ = ["GenerationWorkflowBase"]
