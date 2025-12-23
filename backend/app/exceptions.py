"""
统一异常体系

提供业务逻辑层的异常定义，避免直接使用HTTPException。
所有异常都会被全局异常处理器捕获并转换为HTTP响应。
"""

from typing import Optional


class AFNException(Exception):
    """
    AFN基础异常类

    所有业务异常的基类，会被全局异常处理器捕获。

    Attributes:
        message: 错误消息（面向用户）
        status_code: HTTP状态码
        detail: 详细错误信息（可选，用于日志）
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


# ==================== 4xx 客户端错误 ====================


class ResourceNotFoundError(AFNException):
    """资源不存在（404）"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource}不存在",
            status_code=404,
            detail=f"{resource}不存在: {identifier}"
        )


class PermissionDeniedError(AFNException):
    """权限不足（403）"""

    def __init__(self, message: str = "无权访问该资源"):
        super().__init__(message=message, status_code=403)


class InvalidParameterError(AFNException):
    """参数错误（400）"""

    def __init__(self, message: str, parameter: Optional[str] = None):
        detail = f"参数错误: {parameter} - {message}" if parameter else message
        super().__init__(
            message=message,
            status_code=400,
            detail=detail
        )


class InvalidStateTransitionError(AFNException):
    """非法状态转换（400）

    支持两种调用方式:
    1. InvalidStateTransitionError(message) - 简单消息
    2. InvalidStateTransitionError(current, target, allowed) - 详细状态转换信息
    """

    def __init__(
        self,
        current_status: str,
        target_status: Optional[str] = None,
        allowed: Optional[str] = None
    ):
        if target_status is None:
            # 简单消息模式
            message = current_status
            detail = current_status
        else:
            # 详细状态转换模式
            message = f"非法的状态转换: {current_status} → {target_status}"
            detail = f"{message}. 当前状态只能转换到: {allowed}"
        super().__init__(
            message=message,
            status_code=400,
            detail=detail
        )


class ConflictError(AFNException):
    """资源冲突（409）"""

    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


# ==================== 5xx 服务端错误 ====================


class LLMServiceError(AFNException):
    """LLM服务错误（503）"""

    def __init__(self, message: str, provider: Optional[str] = None):
        detail = f"LLM服务错误 [{provider}]: {message}" if provider else f"LLM服务错误: {message}"
        super().__init__(
            message="AI服务暂时不可用，请稍后重试",
            status_code=503,
            detail=detail
        )


class LLMConfigurationError(AFNException):
    """LLM配置错误（500）"""

    def __init__(self, message: str):
        super().__init__(
            message="LLM配置错误",
            status_code=500,
            detail=message
        )


class VectorStoreError(AFNException):
    """向量库错误（503）"""

    def __init__(self, message: str):
        super().__init__(
            message="向量检索服务暂时不可用",
            status_code=503,
            detail=f"向量库错误: {message}"
        )


class DatabaseError(AFNException):
    """数据库错误（500）"""

    def __init__(self, message: str):
        super().__init__(
            message="数据库操作失败",
            status_code=500,
            detail=message
        )


class JSONParseError(AFNException):
    """JSON解析错误（500）"""

    def __init__(self, context: str, detail_msg: Optional[str] = None):
        message = f"{context}: 格式错误"
        detail = f"JSON解析失败: {context}"
        if detail_msg:
            detail = f"{detail} - {detail_msg}"
        super().__init__(
            message=message,
            status_code=500,
            detail=detail
        )


# ==================== 业务逻辑异常 ====================


class GenerationCancelledError(AFNException):
    """生成任务被取消（400）"""

    def __init__(self, task_name: str, task_id: Optional[str] = None):
        detail = f"{task_name}（{task_id}）已被取消" if task_id else f"{task_name}已被取消"
        super().__init__(
            message=f"{task_name}已取消",
            status_code=400,
            detail=detail
        )


class DailyLimitExceededError(AFNException):
    """超出每日限额（429）

    注意：此异常在桌面版中未使用（桌面版无每日限额功能）。
    保留此定义是为了与Web版代码保持一致，便于未来可能的功能扩展。
    """

    def __init__(self, limit: int, used: int):
        super().__init__(
            message=f"已达到每日LLM调用限额（{used}/{limit}）",
            status_code=429,
            detail=f"每日限额: {limit}, 已使用: {used}"
        )


class BlueprintNotReadyError(AFNException):
    """蓝图未生成（400）"""

    def __init__(self, project_id: str):
        super().__init__(
            message="项目蓝图尚未生成，请先完成灵感对话",
            status_code=400,
            detail=f"项目 {project_id} 蓝图未生成"
        )


class ChapterNotGeneratedError(AFNException):
    """章节未生成（400）"""

    def __init__(self, project_id: str, chapter_number: int):
        super().__init__(
            message=f"第{chapter_number}章尚未生成",
            status_code=400,
            detail=f"项目 {project_id} 第 {chapter_number} 章未生成"
        )


class PromptTemplateNotFoundError(AFNException):
    """提示词模板不存在（500）"""

    def __init__(self, prompt_type: str):
        super().__init__(
            message=f"缺少{prompt_type}提示词模板",
            status_code=500,
            detail=f"提示词模板不存在: {prompt_type}"
        )


class ConversationExtractionError(AFNException):
    """对话历史提取失败（400）"""

    def __init__(self, project_id: str, reason: str = "无法从历史对话中提取有效内容"):
        super().__init__(
            message="对话历史格式错误，请重新开始对话",
            status_code=400,
            detail=f"项目 {project_id}: {reason}"
        )
