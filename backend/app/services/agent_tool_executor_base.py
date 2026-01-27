"""
Agent工具执行基类

统一工具执行的模板流程，减少重复实现与维护成本。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Type


class BaseToolExecutor(ABC):
    """工具执行器基类（模板方法）"""

    TOOL_RESULT_CLASS: Type[Any]

    def __init__(self) -> None:
        # 使用子类模块名作为日志来源，便于定位
        self._logger = logging.getLogger(self.__class__.__module__)
        if not hasattr(self, "TOOL_RESULT_CLASS"):
            raise RuntimeError("子类必须定义 TOOL_RESULT_CLASS（用于构建工具执行结果）")
        self._handlers = self._build_handlers()

    @abstractmethod
    def _build_handlers(self) -> Dict[Any, Callable]:
        """构建工具处理器映射"""

    @abstractmethod
    def _get_tool_name(self, tool_call: Any) -> Any:
        """获取工具名称（或标识）"""

    @abstractmethod
    def _get_tool_params(self, tool_call: Any) -> Dict[str, Any]:
        """获取工具参数"""

    def _build_result(
        self,
        tool_name: Any,
        success: bool,
        result: Any = None,
        error: Optional[str] = None,
    ) -> Any:
        """构建工具执行结果（默认实现）"""
        return self.TOOL_RESULT_CLASS(
            tool_name=tool_name,
            success=success,
            result=result,
            error=error,
        )

    def _format_unknown_tool_error(self, tool_name: Any) -> str:
        """格式化未知工具错误信息"""
        return f"未知工具: {tool_name}"

    def _log_tool_call(self, tool_call: Any) -> None:
        """记录工具调用日志（子类按需覆盖）"""

    def _log_execute_error(self, tool_name: Any, error: Exception) -> None:
        """记录工具执行错误（子类按需覆盖）"""
        self._logger.error("工具执行失败: %s, 错误: %s", tool_name, error, exc_info=True)

    async def execute(self, tool_call: Any) -> Any:
        """
        执行工具调用（统一模板）

        Args:
            tool_call: 工具调用信息

        Returns:
            工具执行结果
        """
        self._log_tool_call(tool_call)

        tool_name = self._get_tool_name(tool_call)
        handler = self._handlers.get(tool_name)

        if not handler:
            return self._build_result(
                tool_name=tool_name,
                success=False,
                error=self._format_unknown_tool_error(tool_name),
            )

        try:
            params = self._get_tool_params(tool_call)
            if asyncio.iscoroutinefunction(handler):
                result = await handler(params)
            else:
                result = handler(params)
            return self._build_result(
                tool_name=tool_name,
                success=True,
                result=result,
            )
        except Exception as e:
            self._log_execute_error(tool_name, e)
            return self._build_result(
                tool_name=tool_name,
                success=False,
                error=str(e),
            )
