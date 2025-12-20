"""
AFN API 客户端模块

提供与后端API交互的所有方法，无需认证。

特性：
- 支持 Context Manager（with 语句）自动管理资源
- 分离连接超时和读取超时
- 内置指数退避重试机制
- 细化的异常处理

主要导出:
    - AFNAPIClient: API客户端类
    - TimeoutConfig: 超时配置常量
"""

from .core import AFNAPIClient
from .constants import TimeoutConfig

__all__ = [
    'AFNAPIClient',
    'TimeoutConfig',
]
