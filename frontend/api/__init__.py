"""
API 客户端模块

提供与后端 API 交互的客户端封装。

用法:
    # 推荐：使用单例管理器（自动管理资源）
    from api import APIClientManager
    client = APIClientManager.get_client()
    data = client.get_novels()

    # 或者直接创建客户端（需手动管理生命周期）
    from api import AFNAPIClient
    with AFNAPIClient() as client:
        data = client.get_novels()

异常处理:
    from api import (
        NotFoundError, BlueprintNotReadyError,
        LLMServiceError, APIError
    )

    try:
        result = client.generate_blueprint(project_id)
    except BlueprintNotReadyError:
        # 蓝图未准备好
        pass
    except LLMServiceError:
        # LLM服务错误
        pass
    except APIError as e:
        # 其他API错误
        print(f"错误: {e.message}")
"""

from api.client import AFNAPIClient
from api.manager import APIClientManager
from api.exceptions import (
    # 基础异常
    APIError,
    ClientError,
    ServerError,
    NetworkError,
    # 通用HTTP错误
    NotFoundError,
    BadRequestError,
    ConflictError,
    ValidationError,
    InternalServerError,
    ServiceUnavailableError,
    # 业务异常
    InvalidStateTransitionError,
    BlueprintNotReadyError,
    ChapterNotGeneratedError,
    ConversationExtractionError,
    GenerationCancelledError,
    LLMServiceError,
    # 网络异常
    ConnectionError,
    TimeoutError,
)

__all__ = [
    # 客户端
    'AFNAPIClient',
    'APIClientManager',
    # 基础异常
    'APIError',
    'ClientError',
    'ServerError',
    'NetworkError',
    # 通用HTTP错误
    'NotFoundError',
    'BadRequestError',
    'ConflictError',
    'ValidationError',
    'InternalServerError',
    'ServiceUnavailableError',
    # 业务异常
    'InvalidStateTransitionError',
    'BlueprintNotReadyError',
    'ChapterNotGeneratedError',
    'ConversationExtractionError',
    'GenerationCancelledError',
    'LLMServiceError',
    # 网络异常
    'ConnectionError',
    'TimeoutError',
]
