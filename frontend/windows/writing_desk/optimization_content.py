"""
正文优化内容组件 - 兼容层

此模块已拆分到 optimization/ 子目录，保留此文件以保持向后兼容。

实际实现位于：
    - optimization/content.py: 主组件
    - optimization/models.py: OptimizationMode枚举
    - optimization/sse_handler.py: SSE事件处理
    - optimization/suggestion_handler.py: 建议处理
    - optimization/mode_control.py: 模式控制
"""

# 从新位置导入并重新导出
from .optimization import (
    OptimizationContent,
    OptimizationMode,
)

__all__ = [
    "OptimizationContent",
    "OptimizationMode",
]
