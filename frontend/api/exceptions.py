"""
API 异常定义

提供分层的异常体系，让前端能够区分不同类型的API错误。

异常层次：
- APIError (基类)
  - ClientError (4xx 客户端错误)
    - NotFoundError (404)
    - BadRequestError (400)
    - ConflictError (409)
    - ValidationError (422)
    - InvalidStateTransitionError (400) - 状态机错误
    - BlueprintNotReadyError (400) - 蓝图未准备
    - ChapterNotGeneratedError (400) - 章节未生成
    - ConversationExtractionError (400) - 对话提取错误
    - GenerationCancelledError (400) - 生成已取消
  - ServerError (5xx 服务端错误)
    - InternalServerError (500)
    - ServiceUnavailableError (503)
    - LLMServiceError (503) - LLM服务错误
  - NetworkError (网络/连接错误)
    - ConnectionError (连接失败)
    - TimeoutError (请求超时)

用法示例：
    from api.exceptions import NotFoundError, ServerError, BlueprintNotReadyError

    try:
        result = api_client.get_novel(project_id)
    except NotFoundError:
        MessageService.show_warning(self, "项目不存在")
    except BlueprintNotReadyError:
        MessageService.show_warning(self, "请先完成灵感对话")
    except ServerError as e:
        MessageService.show_error(self, f"服务器错误: {e.message}")
    except APIError as e:
        MessageService.show_error(self, f"请求失败: {e.message}")
"""


class APIError(Exception):
    """API 错误基类

    所有 API 相关的异常都继承自此类。

    Attributes:
        message: 错误消息（用户友好）
        status_code: HTTP 状态码（如果有）
        response_data: 原始响应数据（如果有）
        original_error: 原始异常（如果有）
    """

    def __init__(
        self,
        message: str,
        status_code: int = None,
        response_data: dict = None,
        original_error: Exception = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        self.original_error = original_error

    def __str__(self):
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


# ==================== 客户端错误 (4xx) ====================

class ClientError(APIError):
    """客户端错误基类 (4xx)

    表示由于客户端请求问题导致的错误。
    """
    pass


class BadRequestError(ClientError):
    """错误请求 (400)

    请求参数无效或格式错误。
    """

    def __init__(self, message: str = "请求参数无效", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class NotFoundError(ClientError):
    """资源不存在 (404)

    请求的资源不存在。
    """

    def __init__(self, message: str = "资源不存在", **kwargs):
        super().__init__(message, status_code=404, **kwargs)


class ConflictError(ClientError):
    """资源冲突 (409)

    操作与现有资源状态冲突。
    """

    def __init__(self, message: str = "资源冲突", **kwargs):
        super().__init__(message, status_code=409, **kwargs)


class ValidationError(ClientError):
    """验证错误 (422)

    请求数据验证失败。
    """

    def __init__(self, message: str = "数据验证失败", **kwargs):
        super().__init__(message, status_code=422, **kwargs)


# ==================== 业务逻辑错误 (400) ====================
# 以下异常与后端 app/exceptions.py 中的业务异常对应


class InvalidStateTransitionError(ClientError):
    """非法状态转换 (400)

    项目状态机不允许的状态转换。
    例如：从 draft 直接跳到 writing 状态。
    """

    def __init__(self, message: str = "非法的状态转换", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class BlueprintNotReadyError(ClientError):
    """蓝图未准备好 (400)

    尝试执行需要蓝图的操作，但蓝图尚未生成。
    """

    def __init__(self, message: str = "项目蓝图尚未生成，请先完成灵感对话", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class ChapterNotGeneratedError(ClientError):
    """章节未生成 (400)

    尝试访问或操作尚未生成的章节。
    """

    def __init__(self, message: str = "章节尚未生成", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class ConversationExtractionError(ClientError):
    """对话提取错误 (400)

    无法从对话历史中提取有效内容。
    """

    def __init__(self, message: str = "对话历史格式错误，请重新开始对话", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


class GenerationCancelledError(ClientError):
    """生成任务已取消 (400)

    生成任务被用户或系统取消。
    """

    def __init__(self, message: str = "生成任务已取消", **kwargs):
        super().__init__(message, status_code=400, **kwargs)


# ==================== 服务端错误 (5xx) ====================

class ServerError(APIError):
    """服务端错误基类 (5xx)

    表示服务端处理请求时发生的错误。
    """
    pass


class InternalServerError(ServerError):
    """内部服务器错误 (500)

    服务端发生未知错误。
    """

    def __init__(self, message: str = "服务器内部错误", **kwargs):
        super().__init__(message, status_code=500, **kwargs)


class ServiceUnavailableError(ServerError):
    """服务不可用 (503)

    服务暂时不可用（如 LLM 服务故障）。
    """

    def __init__(self, message: str = "服务暂时不可用", **kwargs):
        super().__init__(message, status_code=503, **kwargs)


class LLMServiceError(ServerError):
    """LLM服务错误 (503)

    LLM API调用失败，可能是配置错误、网络问题或服务端故障。
    """

    def __init__(self, message: str = "AI服务暂时不可用，请稍后重试", **kwargs):
        super().__init__(message, status_code=503, **kwargs)


# ==================== 网络错误 ====================

class NetworkError(APIError):
    """网络错误基类

    表示网络层面的错误，如连接失败、超时等。
    """
    pass


class ConnectionError(NetworkError):
    """连接错误

    无法连接到服务器。
    """

    def __init__(self, message: str = "无法连接到服务器，请检查网络连接", **kwargs):
        super().__init__(message, **kwargs)


class TimeoutError(NetworkError):
    """超时错误

    请求超时。
    """

    def __init__(self, message: str = "请求超时，请稍后重试", **kwargs):
        super().__init__(message, **kwargs)


# ==================== 工具函数 ====================

def create_api_error(status_code: int, message: str, **kwargs) -> APIError:
    """根据状态码和错误消息创建对应的异常

    此函数会尝试从错误消息中识别业务异常类型，
    如果无法识别则根据HTTP状态码返回通用异常。

    Args:
        status_code: HTTP 状态码
        message: 错误消息
        **kwargs: 其他参数（response_data, original_error等）

    Returns:
        对应类型的 APIError 子类实例
    """
    # 先尝试从消息内容识别业务异常（400错误）
    if status_code == 400:
        business_error = _detect_business_error(message, **kwargs)
        if business_error:
            return business_error

    # 503错误：尝试识别LLM服务错误
    if status_code == 503:
        if _is_llm_service_error(message):
            return LLMServiceError(message, **kwargs)

    # 通用状态码映射
    error_map = {
        400: BadRequestError,
        404: NotFoundError,
        409: ConflictError,
        422: ValidationError,
        500: InternalServerError,
        503: ServiceUnavailableError,
    }

    error_class = error_map.get(status_code)

    if error_class:
        return error_class(message, **kwargs)

    # 根据状态码范围返回基类
    if 400 <= status_code < 500:
        return ClientError(message, status_code=status_code, **kwargs)
    elif 500 <= status_code < 600:
        return ServerError(message, status_code=status_code, **kwargs)

    return APIError(message, status_code=status_code, **kwargs)


def _detect_business_error(message: str, **kwargs) -> ClientError:
    """从错误消息中检测业务异常类型

    Args:
        message: 错误消息
        **kwargs: 其他参数

    Returns:
        识别出的业务异常，如果无法识别返回None
    """
    message_lower = message.lower() if message else ""

    # 状态转换错误
    if "状态转换" in message or "state transition" in message_lower:
        return InvalidStateTransitionError(message, **kwargs)

    # 蓝图未准备错误
    if "蓝图" in message and ("未生成" in message or "尚未" in message):
        return BlueprintNotReadyError(message, **kwargs)

    # 章节未生成错误
    if "章" in message and ("未生成" in message or "尚未生成" in message):
        return ChapterNotGeneratedError(message, **kwargs)

    # 对话提取错误
    if "对话" in message and ("提取" in message or "格式错误" in message):
        return ConversationExtractionError(message, **kwargs)

    # 生成任务取消
    if "取消" in message or "cancelled" in message_lower:
        return GenerationCancelledError(message, **kwargs)

    return None


def _is_llm_service_error(message: str) -> bool:
    """检测是否为LLM服务错误

    Args:
        message: 错误消息

    Returns:
        True如果是LLM相关错误
    """
    if not message:
        return False

    llm_keywords = ["ai服务", "llm", "openai", "api key", "模型", "服务不可用"]
    message_lower = message.lower()

    return any(kw in message_lower for kw in llm_keywords)
