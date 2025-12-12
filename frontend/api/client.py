"""
AFN (Agents for Novel) API 客户端封装

提供与后端API交互的所有方法，无需认证。

特性：
- 支持 Context Manager（with 语句）自动管理资源
- 分离连接超时和读取超时
- 内置指数退避重试机制
- 细化的异常处理
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from api.exceptions import (
    APIError,
    NotFoundError,
    BadRequestError,
    ConflictError,
    ValidationError,
    InternalServerError,
    ServiceUnavailableError,
    ConnectionError as APIConnectionError,
    TimeoutError as APITimeoutError,
    create_api_error,
)

from utils.constants import NovelConstants


logger = logging.getLogger(__name__)


# 超时配置常量（秒）
class TimeoutConfig:
    """超时配置"""
    # 连接超时：建立TCP连接的超时时间
    CONNECT = 10
    # 读取超时配置（根据操作类型）
    READ_DEFAULT = 60       # 默认读取超时
    READ_QUICK = 30         # 快速操作（健康检查、获取配置等）
    READ_NORMAL = 120       # 普通操作（获取数据、更新等）
    READ_GENERATION = 300   # 生成操作（蓝图、大纲生成）
    READ_LONG = 600         # 长时间操作（章节生成、批量操作）


class AFNAPIClient:
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

            result = response.json()
            logger.info("API request success: %s %s", method, endpoint)

            return result

        except requests.HTTPError as e:
            # 尝试提取后端返回的详细错误信息
            error_msg = str(e)
            status_code = e.response.status_code if e.response is not None else None
            response_data = None

            if e.response is not None:
                try:
                    response_data = e.response.json()
                    error_detail = response_data.get('detail')
                    if error_detail:
                        error_msg = error_detail
                except (ValueError, AttributeError, KeyError):
                    pass

            # 检查是否是需要静默处理的状态码
            if status_code and status_code in silent_status_codes:
                logger.debug(f"API请求返回 {status_code}: {method} {url}")
            else:
                logger.error(f"API请求失败: {method} {url} - {error_msg}")

            # 抛出具体类型的异常
            raise create_api_error(
                status_code=status_code,
                message=error_msg,
                response_data=response_data,
                original_error=e
            )

        except requests.exceptions.ConnectError as e:
            logger.error(f"API连接失败: {method} {url} - {e}")
            raise APIConnectionError(
                message="无法连接到后端服务，请确认服务已启动",
                original_error=e
            )

        except requests.exceptions.ReadTimeout as e:
            # 读取超时单独处理
            logger.error(f"API读取超时: {method} {url} - {e}")
            raise APITimeoutError(
                message=f"服务器响应超时（{read_timeout}秒），请稍后重试",
                original_error=e
            )

        except requests.exceptions.ConnectTimeout as e:
            # 连接超时单独处理
            logger.error(f"API连接超时: {method} {url} - {e}")
            raise APITimeoutError(
                message=f"连接服务器超时（{connect_timeout}秒），请检查网络连接",
                original_error=e
            )

        except requests.exceptions.Timeout as e:
            # 其他超时
            logger.error(f"API请求超时: {method} {url} - {e}")
            raise APITimeoutError(
                message=f"请求超时，请稍后重试",
                original_error=e
            )

        except requests.exceptions.SSLError as e:
            logger.error(f"API SSL错误: {method} {url} - {e}")
            raise APIConnectionError(
                message="SSL/TLS连接错误，请检查证书配置",
                original_error=e
            )

        except requests.exceptions.ChunkedEncodingError as e:
            logger.error(f"API响应编码错误: {method} {url} - {e}")
            raise APIError(
                message="服务器响应异常中断，请重试",
                original_error=e
            )

        except requests.RequestException as e:
            logger.error(f"API请求失败: {method} {url} - {type(e).__name__}: {e}")
            raise APIError(
                message=f"请求失败: {str(e)}",
                original_error=e
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

        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            logger.error(f"API请求失败: {method} {url} - {e}")
            raise create_api_error(
                status_code=status_code,
                message=str(e),
                original_error=e
            )

        except requests.exceptions.ConnectError as e:
            logger.error(f"API连接失败: {method} {url} - {e}")
            raise APIConnectionError(
                message="无法连接到后端服务",
                original_error=e
            )

        except requests.exceptions.Timeout as e:
            logger.error(f"API请求超时: {method} {url} - {e}")
            raise APITimeoutError(
                message=f"请求超时（{read_timeout}秒）",
                original_error=e
            )

        except requests.RequestException as e:
            logger.error(f"API请求失败: {method} {url} - {type(e).__name__}: {e}")
            raise APIError(
                message=f"请求失败: {str(e)}",
                original_error=e
            )

    # ==================== 健康检查 ====================

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return self._request('GET', '/health')

    # ==================== 小说项目管理 ====================

    def create_novel(self, title: str, initial_prompt: str) -> Dict[str, Any]:
        """
        创建小说项目

        Args:
            title: 小说标题
            initial_prompt: 初始提示词

        Returns:
            项目信息
        """
        return self._request('POST', '/api/novels', {
            'title': title,
            'initial_prompt': initial_prompt
        })

    def get_novels(self) -> List[Dict[str, Any]]:
        """获取项目列表"""
        return self._request('GET', '/api/novels')

    def get_novel(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详细信息
        """
        return self._request('GET', f'/api/novels/{project_id}')

    def get_section(self, project_id: str, section_type: str) -> Dict[str, Any]:
        """
        获取小说的特定section数据

        Args:
            project_id: 项目ID
            section_type: section类型（overview, world_setting, characters等）

        Returns:
            section数据
        """
        return self._request('GET', f'/api/novels/{project_id}/sections/{section_type}')

    def get_chapter(self, project_id: str, chapter_number: int) -> Dict[str, Any]:
        """
        获取章节详情

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            章节详细信息
        """
        return self._request('GET', f'/api/novels/{project_id}/chapters/{chapter_number}')

    def export_novel(self, project_id: str, format_type: str = 'txt') -> str:
        """
        导出整本小说

        Args:
            project_id: 项目ID
            format_type: 导出格式（txt或markdown）

        Returns:
            导出的文本内容
        """
        return self._request_raw(
            'GET',
            f'/api/novels/{project_id}/export',
            params={'format': format_type},
            timeout=60,
            return_type='text'
        )

    def update_project(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新项目信息

        Args:
            project_id: 项目ID
            data: 更新数据

        Returns:
            更新后的项目信息
        """
        return self._request('PATCH', f'/api/novels/{project_id}', data)

    def delete_novels(self, project_ids: List[str]) -> Dict[str, Any]:
        """
        删除项目

        Args:
            project_ids: 项目ID列表

        Returns:
            删除结果
        """
        # 后端使用 Body(...) 不带 embed=True,期望裸JSON数组
        return self._request('DELETE', '/api/novels', project_ids)

    # ==================== 灵感对话 ====================

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

    # ==================== 蓝图生成 ====================

    def generate_blueprint(
        self,
        project_id: str,
        force_regenerate: bool = False,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        生成蓝图

        Args:
            project_id: 项目ID
            force_regenerate: 是否强制重新生成
            async_mode: 是否使用异步模式（默认False）

        Returns:
            同步模式：完整蓝图数据
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        """
        params = {
            'force_regenerate': force_regenerate,
            'async_mode': async_mode
        }
        # 异步模式只需等待任务启动，同步模式需要等待完整生成
        timeout = 30 if async_mode else 480
        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/generate',
            params=params,
            timeout=timeout
        )

    def update_blueprint(
        self,
        project_id: str,
        blueprint_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新蓝图

        Args:
            project_id: 项目ID
            blueprint_data: 蓝图数据

        Returns:
            更新结果
        """
        return self._request(
            'PATCH',
            f'/api/novels/{project_id}/blueprint',
            blueprint_data
        )

    def refine_blueprint(
        self,
        project_id: str,
        refinement_instruction: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        优化蓝图

        Args:
            project_id: 项目ID
            refinement_instruction: 优化指令，描述想要改进的方向
            force: 是否强制优化（将删除所有章节大纲、部分大纲、章节内容）

        Returns:
            优化后的蓝图
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/refine',
            {'refinement_instruction': refinement_instruction},
            params={'force': force},
            timeout=480
        )

    # ==================== 小说头像 ====================

    def generate_avatar(self, project_id: str) -> Dict[str, Any]:
        """
        为小说生成SVG头像

        根据小说的类型、风格、氛围，使用LLM生成一个匹配的小动物SVG图标。

        Args:
            project_id: 项目ID

        Returns:
            头像数据：
            {
                "avatar_svg": "<svg>...</svg>",  # 完整SVG代码
                "animal": "fox",                  # 动物英文名
                "animal_cn": "狐狸"               # 动物中文名
            }
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/avatar/generate',
            timeout=TimeoutConfig.READ_GENERATION
        )

    def delete_avatar(self, project_id: str) -> Dict[str, Any]:
        """
        删除小说的头像

        Args:
            project_id: 项目ID

        Returns:
            {"success": True}
        """
        return self._request(
            'DELETE',
            f'/api/novels/{project_id}/avatar'
        )

    # ==================== 章节大纲 ====================

    def generate_part_outlines(
        self,
        project_id: str,
        total_chapters: int,
        chapters_per_part: int = NovelConstants.CHAPTERS_PER_PART
    ) -> Dict[str, Any]:
        """
        生成部分大纲

        Args:
            project_id: 项目ID
            total_chapters: 小说总章节数
            chapters_per_part: 每个部分的章节数

        Returns:
            大纲数据
        """
        data = {
            'total_chapters': total_chapters,
            'chapters_per_part': chapters_per_part
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/parts/generate',
            data=data,
            timeout=300
        )

    def get_part_outline_generation_status(self, project_id: str) -> Dict[str, Any]:
        """
        查询部分大纲生成状态（实际调用parts/progress接口）

        Args:
            project_id: 项目ID

        Returns:
            状态数据：
            {
                "parts": [...],  # 所有部分大纲列表
                "total_parts": int,  # 总部分数
                "completed_parts": int,  # 已完成部分数
                "status": "pending|partial|completed"  # 整体状态
            }
        """
        try:
            return self._request(
                'GET',
                f'/api/writer/novels/{project_id}/parts/progress',
                silent_status_codes=[404]  # 静默处理 404 错误
            )
        except requests.exceptions.HTTPError as e:
            # 404 表示后端不支持此功能或项目没有部分大纲，返回默认空闲状态
            if e.response.status_code == 404:
                return {
                    "parts": [],
                    "total_parts": 0,
                    "completed_parts": 0,
                    "status": "pending"
                }
            # 其他错误继续抛出
            raise

    def regenerate_part_outlines(
        self,
        project_id: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新生成所有部分大纲（会删除所有章节大纲）

        Args:
            project_id: 项目ID
            prompt: 优化提示（可选）

        Returns:
            新的部分大纲
        """
        data = {'prompt': prompt} if prompt else {}
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/part-outlines/regenerate',
            data,
            timeout=300
        )

    def regenerate_last_part_outline(
        self,
        project_id: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新生成最后一个部分大纲

        Args:
            project_id: 项目ID
            prompt: 优化提示（可选）

        Returns:
            新的部分大纲
        """
        data = {'prompt': prompt} if prompt else {}
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/part-outlines/regenerate-last',
            data,
            timeout=300
        )

    def regenerate_specific_part_outline(
        self,
        project_id: str,
        part_number: int,
        prompt: Optional[str] = None,
        cascade_delete: bool = False
    ) -> Dict[str, Any]:
        """
        重新生成指定部分大纲（串行生成原则）

        Args:
            project_id: 项目ID
            part_number: 部分编号
            prompt: 优化提示（可选）
            cascade_delete: 是否级联删除后续部分和章节大纲

        Returns:
            新的部分大纲
        """
        data = {
            'prompt': prompt,
            'cascade_delete': cascade_delete
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/part-outlines/{part_number}/regenerate',
            data,
            timeout=300
        )

    def delete_part_outlines(
        self,
        project_id: str,
        count: int
    ) -> Dict[str, Any]:
        """
        删除最后N个部分大纲

        Args:
            project_id: 项目ID
            count: 要删除的数量

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/writer/novels/{project_id}/parts/delete-latest',
            params={'count': count},
            timeout=60
        )

    def generate_chapter_outlines_by_count(
        self,
        project_id: str,
        count: int
    ) -> Dict[str, Any]:
        """
        灵活生成指定数量的章节大纲

        Args:
            project_id: 项目ID
            count: 生成数量

        Returns:
            生成结果
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapter-outlines/generate-by-count',
            {'count': count},
            timeout=600
        )

    def regenerate_chapter_outline(
        self,
        project_id: str,
        chapter_number: int,
        prompt: Optional[str] = None,
        cascade_delete: bool = False
    ) -> Dict[str, Any]:
        """
        重新生成指定章节大纲（串行生成原则）

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            prompt: 优化提示（可选）
            cascade_delete: 是否级联删除后续章节大纲

        Returns:
            新的章节大纲
        """
        data = {
            'prompt': prompt,
            'cascade_delete': cascade_delete
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapter-outlines/{chapter_number}/regenerate',
            data,
            timeout=180
        )

    def update_chapter_outline(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        summary: str
    ) -> Dict[str, Any]:
        """
        更新章节大纲

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: 章节标题
            summary: 章节摘要

        Returns:
            更新后的项目信息
        """
        data = {
            'chapter_number': chapter_number,
            'title': title,
            'summary': summary
        }
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/update-outline',
            data
        )

    def delete_chapters(
        self,
        project_id: str,
        count: int
    ) -> Dict[str, Any]:
        """
        删除最新的N章大纲

        Args:
            project_id: 项目ID
            count: 删除数量

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/writer/novels/{project_id}/chapter-outlines/delete-latest',
            {'count': count}
        )

    # ==================== 章节生成 ====================

    def generate_chapter(
        self,
        project_id: str,
        chapter_number: int,
        writing_notes: Optional[str] = None,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        生成章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            writing_notes: 写作指令（可选）
            async_mode: 是否使用异步模式（默认False）

        Returns:
            同步模式：生成结果（包含多个版本）
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        """
        data = {
            'chapter_number': chapter_number,
            'writing_notes': writing_notes or ''
        }
        params = {'async_mode': async_mode}
        # 同步模式需要较长超时，异步模式只需等待任务启动
        timeout = 30 if async_mode else 600
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/generate',
            data,
            params=params,
            timeout=timeout
        )

    def preview_chapter_prompt(
        self,
        project_id: str,
        chapter_number: int,
        writing_notes: Optional[str] = None,
        is_retry: bool = False
    ) -> Dict[str, Any]:
        """
        预览章节生成的提示词（用于测试RAG效果）

        此方法只构建提示词，不调用LLM生成内容。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            writing_notes: 写作备注/优化方向（可选）
            is_retry: 是否为重新生成模式（使用简化提示词，不含完整前情摘要）

        Returns:
            提示词预览数据，包含：
            - system_prompt: 系统提示词
            - user_prompt: 用户提示词
            - rag_statistics: RAG检索统计
            - prompt_sections: 各部分内容
            - total_length: 总长度
            - estimated_tokens: 估算token数
        """
        data = {
            'chapter_number': chapter_number,
            'is_retry': is_retry,
        }
        if writing_notes:
            data['writing_notes'] = writing_notes

        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/preview-prompt',
            data,
            timeout=120
        )

    def select_chapter_version(
        self,
        project_id: str,
        chapter_number: int,
        version_index: int
    ) -> Dict[str, Any]:
        """
        选择章节版本

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            version_index: 版本索引

        Returns:
            选择结果
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/select',
            {
                'chapter_number': chapter_number,
                'version_index': version_index
            }
        )

    def evaluate_chapter(
        self,
        project_id: str,
        chapter_number: int
    ) -> Dict[str, Any]:
        """
        评审章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            评审结果
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/evaluate',
            {'chapter_number': chapter_number},
            timeout=300
        )

    def retry_chapter_version(
        self,
        project_id: str,
        chapter_number: int,
        version_index: int,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新生成指定章节的某个版本

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            version_index: 版本索引
            custom_prompt: 自定义优化提示词（可选）

        Returns:
            更新后的项目数据
        """
        data = {
            'chapter_number': chapter_number,
            'version_index': version_index
        }
        if custom_prompt:
            data['custom_prompt'] = custom_prompt

        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/retry-version',
            data,
            timeout=600
        )

    def update_chapter(
        self,
        project_id: str,
        chapter_number: int,
        content: str
    ) -> Dict[str, Any]:
        """
        更新章节内容

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            content: 新内容

        Returns:
            更新结果
        """
        return self._request(
            'PUT',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}',
            {'content': content}
        )

    def import_chapter(
        self,
        project_id: str,
        chapter_number: int,
        title: str,
        content: str
    ) -> Dict[str, Any]:
        """
        导入章节内容

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: 章节标题
            content: 章节内容

        Returns:
            更新后的项目数据
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/import',
            {
                'chapter_number': chapter_number,
                'title': title,
                'content': content
            }
        )

    def export_chapters(
        self,
        project_id: str,
        start: Optional[int] = None,
        end: Optional[int] = None
    ) -> bytes:
        """
        导出章节为TXT文件

        Args:
            project_id: 项目ID
            start: 起始章节号
            end: 结束章节号

        Returns:
            文件内容（字节）
        """
        params = {}
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end

        return self._request_raw(
            'GET',
            f'/api/writer/novels/{project_id}/chapters/export',
            params=params,
            timeout=60,
            return_type='content'
        )

    # ==================== LLM配置 ====================

    def get_llm_configs(self) -> List[Dict[str, Any]]:
        """获取LLM配置列表"""
        return self._request('GET', '/api/llm-configs')

    def create_llm_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建LLM配置

        Args:
            config_data: 配置数据

        Returns:
            创建的配置
        """
        return self._request('POST', '/api/llm-configs', config_data)

    def update_llm_config(
        self,
        config_id: int,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新LLM配置

        Args:
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置
        """
        return self._request('PUT', f'/api/llm-configs/{config_id}', config_data)

    def delete_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        删除LLM配置

        Args:
            config_id: 配置ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/llm-configs/{config_id}')

    def activate_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        激活LLM配置

        Args:
            config_id: 配置ID

        Returns:
            激活结果
        """
        return self._request('POST', f'/api/llm-configs/{config_id}/activate')

    def test_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试LLM配置连接

        Args:
            config_id: 配置ID

        Returns:
            测试结果
        """
        return self._request('POST', f'/api/llm-configs/{config_id}/test', timeout=30)

    def import_llm_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入LLM配置

        Args:
            import_data: LLMConfigExportData格式的导入数据
                        {"version": "1.0", "export_time": "...", "export_type": "...", "configs": [...]}

        Returns:
            导入结果
        """
        return self._request('POST', '/api/llm-configs/import', import_data)

    def export_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        导出单个LLM配置

        Args:
            config_id: 配置ID

        Returns:
            LLMConfigExportData格式的导出数据
            {"version": "1.0", "export_time": "...", "export_type": "single", "configs": [...]}
        """
        return self._request('GET', f'/api/llm-configs/{config_id}/export')

    def export_llm_configs(self) -> Dict[str, Any]:
        """
        导出所有LLM配置

        Returns:
            LLMConfigExportData格式的导出数据
            {"version": "1.0", "export_time": "...", "export_type": "batch", "configs": [...]}
        """
        return self._request('GET', '/api/llm-configs/export')

    # ==================== 嵌入模型配置 ====================

    def get_embedding_configs(self) -> List[Dict[str, Any]]:
        """获取嵌入模型配置列表"""
        return self._request('GET', '/api/embedding-configs')

    def get_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        获取指定嵌入模型配置

        Args:
            config_id: 配置ID

        Returns:
            配置详情
        """
        return self._request('GET', f'/api/embedding-configs/{config_id}')

    def create_embedding_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建嵌入模型配置

        Args:
            config_data: 配置数据

        Returns:
            创建的配置
        """
        return self._request('POST', '/api/embedding-configs', config_data)

    def update_embedding_config(
        self,
        config_id: int,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新嵌入模型配置

        Args:
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置
        """
        return self._request('PUT', f'/api/embedding-configs/{config_id}', config_data)

    def delete_embedding_config(self, config_id: int) -> None:
        """
        删除嵌入模型配置

        Args:
            config_id: 配置ID
        """
        self._request('DELETE', f'/api/embedding-configs/{config_id}')

    def activate_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        激活嵌入模型配置

        Args:
            config_id: 配置ID

        Returns:
            激活后的配置
        """
        return self._request('POST', f'/api/embedding-configs/{config_id}/activate')

    def test_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试嵌入模型配置连接

        Args:
            config_id: 配置ID

        Returns:
            测试结果
        """
        return self._request('POST', f'/api/embedding-configs/{config_id}/test', timeout=60)

    # ==================== 章节大纲批量生成 ====================

    def generate_all_chapter_outlines(
        self,
        project_id: str,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        生成所有章节大纲（首次生成/短篇小说）

        用于项目初始化阶段一次性生成全部章节大纲，
        适合短篇小说（章节数<=50）。

        Args:
            project_id: 项目ID
            async_mode: 是否使用异步模式（默认False）

        Returns:
            同步模式：完整大纲数据
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
        """
        params = {'async_mode': async_mode}
        timeout = 30 if async_mode else 400
        return self._request(
            'POST',
            f'/api/novels/{project_id}/chapter-outlines/generate',
            params=params,
            timeout=timeout
        )

    # ==================== 高级配置管理 ====================

    def get_advanced_config(self) -> Dict[str, Any]:
        """
        获取高级配置

        Returns:
            当前配置值
        """
        return self._request('GET', '/api/settings/advanced-config')

    def update_advanced_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新高级配置

        Args:
            config: 配置更新数据

        Returns:
            更新结果
        """
        return self._request('PUT', '/api/settings/advanced-config', data=config)
