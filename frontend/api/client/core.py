"""
AFN API 客户端核心类

提供HTTP请求基础功能和Session管理。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from api.exceptions import (
    APIError,
    ConnectionError as APIConnectionError,
    TimeoutError as APITimeoutError,
    create_api_error,
)

from .constants import TimeoutConfig
from .novel_mixin import NovelMixin
from .inspiration_mixin import InspirationMixin
from .blueprint_mixin import BlueprintMixin
from .outline_mixin import OutlineMixin
from .chapter_mixin import ChapterMixin
from .optimization_mixin import OptimizationMixin
from .manga_mixin import MangaMixin
from .config_mixin import ConfigMixin
from .image_mixin import ImageMixin
from .queue_mixin import QueueMixin
from .portrait_mixin import PortraitMixin
from .import_mixin import ImportMixin


logger = logging.getLogger(__name__)


class AFNAPIClient(
    NovelMixin,
    InspirationMixin,
    BlueprintMixin,
    OutlineMixin,
    ChapterMixin,
    OptimizationMixin,
    MangaMixin,
    ConfigMixin,
    ImageMixin,
    QueueMixin,
    PortraitMixin,
    ImportMixin,
):
    """AFN API 客户端

    支持两种使用方式：

    1. 直接使用：
        client = AFNAPIClient()
        data = client.get_novels()
        client.close()  # 需要手动关闭

    2. Context Manager（推荐）：
        with AFNAPIClient() as client:
            data = client.get_novels()
        # 自动关闭

    组合多个 Mixin 提供完整的API功能：
    - NovelMixin: 小说项目管理
    - InspirationMixin: 灵感对话
    - BlueprintMixin: 蓝图生成
    - OutlineMixin: 大纲管理
    - ChapterMixin: 章节生成
    - OptimizationMixin: RAG和正文优化
    - MangaMixin: 漫画提示词
    - ConfigMixin: 配置管理
    - ImageMixin: 图片生成
    - ImportMixin: 外部小说导入和分析
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8123"):
        """
        初始化API客户端

        Args:
            base_url: 后端服务地址
        """
        self.base_url = base_url.rstrip('/')
        self._closed = False
        self.session = self._create_session()
        logger.debug("AFNAPIClient initialized: base_url=%s", self.base_url)

    def _create_session(self) -> requests.Session:
        """创建配置好的 Session

        配置包括：
        - 默认请求头
        - 重试策略（仅对连接错误和特定状态码重试）
        """
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

        # 配置重试策略
        # 仅对连接错误和 502/503/504 状态码重试
        retry_strategy = Retry(
            total=3,                    # 最多重试3次
            backoff_factor=0.5,         # 退避因子：0.5s, 1s, 2s
            status_forcelist=[502, 503, 504],  # 需要重试的状态码
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            raise_on_status=False       # 不在重试时抛出异常
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def __enter__(self):
        """Context Manager 入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context Manager 出口，确保资源被释放"""
        self.close()
        return False  # 不抑制异常

    def __del__(self):
        """析构函数，确保session被关闭"""
        self.close()

    def close(self):
        """显式关闭session，释放资源

        可以多次调用，只有第一次会实际关闭。
        """
        if self._closed:
            return

        self._closed = True
        if hasattr(self, 'session') and self.session:
            try:
                self.session.close()
            except (OSError, RuntimeError, AttributeError) as e:
                # 关闭时可能的预期异常：网络错误、运行时错误、属性错误
                logger.debug("关闭session时发生预期异常: %s", type(e).__name__)

    def _get_timeout(self, timeout: Union[int, Tuple[int, int], None]) -> Tuple[int, int]:
        """解析超时配置

        Args:
            timeout: 超时配置，可以是：
                - int: 读取超时（连接超时使用默认值）
                - tuple: (连接超时, 读取超时)
                - None: 使用默认值

        Returns:
            (连接超时, 读取超时) 元组
        """
        if timeout is None:
            return (TimeoutConfig.CONNECT, TimeoutConfig.READ_DEFAULT)
        elif isinstance(timeout, tuple):
            return timeout
        else:
            return (TimeoutConfig.CONNECT, timeout)

    def _handle_request_exception(
        self,
        exc: Exception,
        method: str,
        url: str,
        connect_timeout: int,
        read_timeout: int,
        silent_status_codes: Optional[List[int]] = None,
    ) -> None:
        """统一处理HTTP请求异常

        将请求异常转换为API异常，并记录日志。
        此方法始终抛出异常，不会正常返回。

        Args:
            exc: 捕获的原始异常
            method: HTTP方法
            url: 请求URL
            connect_timeout: 连接超时（秒）
            read_timeout: 读取超时（秒）
            silent_status_codes: 静默处理的状态码列表

        Raises:
            APIError 及其子类
        """
        silent_status_codes = silent_status_codes or []

        if isinstance(exc, requests.HTTPError):
            error_msg = str(exc)
            status_code = exc.response.status_code if exc.response is not None else None
            response_data = None

            if exc.response is not None:
                try:
                    response_data = exc.response.json()
                    error_detail = response_data.get('detail')
                    if error_detail:
                        error_msg = error_detail
                except (ValueError, AttributeError, KeyError):
                    pass

            if status_code and status_code in silent_status_codes:
                logger.debug(f"API请求返回 {status_code}: {method} {url}")
            else:
                logger.error(f"API请求失败: {method} {url} - {error_msg}")

            raise create_api_error(
                status_code=status_code,
                message=error_msg,
                response_data=response_data,
                original_error=exc
            )

        elif isinstance(exc, requests.exceptions.ConnectionError):
            logger.error(f"API连接失败: {method} {url} - {exc}")
            raise APIConnectionError(
                message="无法连接到后端服务，请确认服务已启动",
                original_error=exc
            )

        elif isinstance(exc, requests.exceptions.ReadTimeout):
            logger.error(f"API读取超时: {method} {url} - {exc}")
            raise APITimeoutError(
                message=f"服务器响应超时（{read_timeout}秒），请稍后重试",
                original_error=exc
            )

        elif isinstance(exc, requests.exceptions.ConnectTimeout):
            logger.error(f"API连接超时: {method} {url} - {exc}")
            raise APITimeoutError(
                message=f"连接服务器超时（{connect_timeout}秒），请检查网络连接",
                original_error=exc
            )

        elif isinstance(exc, requests.exceptions.Timeout):
            logger.error(f"API请求超时: {method} {url} - {exc}")
            raise APITimeoutError(
                message="请求超时，请稍后重试",
                original_error=exc
            )

        elif isinstance(exc, requests.exceptions.SSLError):
            logger.error(f"API SSL错误: {method} {url} - {exc}")
            raise APIConnectionError(
                message="SSL/TLS连接错误，请检查证书配置",
                original_error=exc
            )

        elif isinstance(exc, requests.exceptions.ChunkedEncodingError):
            logger.error(f"API响应编码错误: {method} {url} - {exc}")
            raise APIError(
                message="服务器响应异常中断，请重试",
                original_error=exc
            )

        elif isinstance(exc, requests.RequestException):
            logger.error(f"API请求失败: {method} {url} - {type(exc).__name__}: {exc}")
            raise APIError(
                message=f"请求失败: {str(exc)}",
                original_error=exc
            )

        else:
            # 未知异常类型，记录并重新抛出
            logger.error(f"API请求未知异常: {method} {url} - {type(exc).__name__}: {exc}")
            raise APIError(
                message=f"请求发生未知错误: {type(exc).__name__}",
                original_error=exc
            )

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Union[int, Tuple[int, int], None] = None,
        silent_status_codes: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求体数据
            params: URL参数
            timeout: 超时配置（秒），可以是：
                - int: 读取超时（连接超时使用默认值10秒）
                - tuple: (连接超时, 读取超时)
                - None: 使用默认值 (10, 60)
            silent_status_codes: 静默处理的状态码列表（不记录错误日志）

        Returns:
            响应JSON数据

        Raises:
            APIError 及其子类: 请求失败时抛出对应类型的异常
        """
        if self._closed:
            raise APIError(message="APIClient已关闭，请重新创建实例")

        url = f"{self.base_url}{endpoint}"
        silent_status_codes = silent_status_codes or []
        connect_timeout, read_timeout = self._get_timeout(timeout)

        logger.info(
            "API request start: %s %s (timeout=%d/%ds)",
            method, endpoint, connect_timeout, read_timeout
        )

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=(connect_timeout, read_timeout)
            )

            logger.info(
                "API response received: %s %s -> status=%d, content_length=%s",
                method, endpoint, response.status_code,
                response.headers.get('content-length', 'unknown')
            )

            response.raise_for_status()

            # 处理204 No Content响应（DELETE等操作可能返回空响应）
            if response.status_code == 204 or not response.content:
                logger.info("API request success: %s %s (no content)", method, endpoint)
                return {}

            result = response.json()
            logger.info("API request success: %s %s", method, endpoint)

            return result

        except Exception as e:
            self._handle_request_exception(
                exc=e,
                method=method,
                url=url,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                silent_status_codes=silent_status_codes,
            )

    def _request_raw(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: Union[int, Tuple[int, int], None] = None,
        return_type: str = 'text'
    ) -> Any:
        """
        发送HTTP请求并返回原始数据（text或bytes）

        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            timeout: 超时配置（秒）
            return_type: 返回类型（'text'或'content'）

        Returns:
            响应的text或content（bytes）

        Raises:
            APIError 及其子类: 请求失败时抛出对应类型的异常
        """
        if self._closed:
            raise APIError(message="APIClient已关闭，请重新创建实例")

        url = f"{self.base_url}{endpoint}"
        connect_timeout, read_timeout = self._get_timeout(timeout or TimeoutConfig.READ_NORMAL)

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=(connect_timeout, read_timeout)
            )
            response.raise_for_status()
            return response.text if return_type == 'text' else response.content

        except Exception as e:
            self._handle_request_exception(
                exc=e,
                method=method,
                url=url,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
            )
