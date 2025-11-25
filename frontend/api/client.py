"""
Arboris Novel API 客户端封装

提供与后端API交互的所有方法，无需认证。
"""

import json
import logging
from typing import Any, Dict, List, Optional
import requests


logger = logging.getLogger(__name__)


class ArborisAPIClient:
    """Arboris Novel API 客户端"""

    def __init__(self, base_url: str = "http://127.0.0.1:8123"):
        """
        初始化API客户端

        Args:
            base_url: 后端服务地址
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 300,
        silent_status_codes: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求体数据
            params: URL参数
            timeout: 超时时间（秒）
            silent_status_codes: 静默处理的状态码列表（不记录错误日志）

        Returns:
            响应JSON数据

        Raises:
            requests.RequestException: 请求失败
        """
        url = f"{self.base_url}{endpoint}"
        silent_status_codes = silent_status_codes or []

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.HTTPError as e:
            # 尝试提取后端返回的详细错误信息
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_detail = e.response.json().get('detail')
                    if error_detail:
                        error_msg = error_detail
                except (ValueError, AttributeError, KeyError):
                    pass

            # 检查是否是需要静默处理的状态码
            if e.response is not None and e.response.status_code in silent_status_codes:
                logger.debug(f"API请求返回 {e.response.status_code}: {method} {url}")
            else:
                logger.error(f"API请求失败: {method} {url} - {error_msg}")

            # 抛出包含详细错误信息的异常
            raise Exception(error_msg) from e
        except requests.RequestException as e:
            logger.error(f"API请求失败: {method} {url} - {e}")
            raise

    def _request_raw(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        timeout: int = 60,
        return_type: str = 'text'
    ) -> Any:
        """
        发送HTTP请求并返回原始数据（text或bytes）

        Args:
            method: HTTP方法
            endpoint: API端点
            params: URL参数
            timeout: 超时时间（秒）
            return_type: 返回类型（'text'或'content'）

        Returns:
            响应的text或content（bytes）

        Raises:
            requests.RequestException: 请求失败
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=timeout
            )
            response.raise_for_status()
            return response.text if return_type == 'text' else response.content

        except requests.HTTPError as e:
            logger.error(f"API请求失败: {method} {url} - {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"API请求失败: {method} {url} - {e}")
            raise

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

    def get_all_novels(self) -> List[Dict[str, Any]]:
        """获取所有项目列表（别名）"""
        return self.get_novels()

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

    def concept_converse(
        self,
        project_id: str,
        user_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        概念对话（已弃用，请使用 inspiration_converse）

        此方法仅为向后兼容保留，将在未来版本移除。
        请使用 inspiration_converse(project_id, message_text) 替代。

        Args:
            project_id: 项目ID
            user_input: 用户输入字典

        Returns:
            AI响应
        """
        import warnings
        warnings.warn(
            "concept_converse已弃用，请使用inspiration_converse方法",
            DeprecationWarning,
            stacklevel=2
        )

        # 提取消息文本并调用新方法
        message = user_input.get('message', '') if isinstance(user_input, dict) else str(user_input)
        return self.inspiration_converse(project_id, message)

    # ==================== 蓝图生成 ====================

    def generate_blueprint(
        self,
        project_id: str,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        生成蓝图

        Args:
            project_id: 项目ID
            force_regenerate: 是否强制重新生成

        Returns:
            蓝图数据
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/generate',
            params={'force_regenerate': 'true' if force_regenerate else 'false'},  # 转换为小写字符串
            timeout=480
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
            params={'force': 'true' if force else 'false'},  # 转换为小写字符串
            timeout=480
        )

    # ==================== 章节大纲 ====================

    def generate_part_outlines(
        self,
        project_id: str,
        total_chapters: int,
        chapters_per_part: int = 25
    ) -> Dict[str, Any]:
        """
        生成部分大纲

        Args:
            project_id: 项目ID
            total_chapters: 小说总章节数
            chapters_per_part: 每个部分的章节数（默认25）

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

    def delete_chapter_outlines(
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
        chapter_number: int
    ) -> Dict[str, Any]:
        """
        生成章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            生成结果（包含多个版本）
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/generate',
            {'chapter_number': chapter_number},
            timeout=600
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

    # ==================== 异步任务管理 ====================

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务信息，包含状态、进度、结果等
        """
        return self._request('GET', f'/tasks/{task_id}')

    def get_project_tasks(
        self,
        project_id: str,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        获取项目的所有任务

        Args:
            project_id: 项目ID
            task_type: 任务类型过滤（可选）
            status: 状态过滤（可选）
            limit: 返回数量限制

        Returns:
            任务列表和总数
        """
        params = {'limit': limit}
        if task_type:
            params['task_type'] = task_type
        if status:
            params['status'] = status

        return self._request('GET', f'/projects/{project_id}/tasks', params=params)

    def get_active_tasks(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目的活动任务（PENDING或RUNNING状态）

        Args:
            project_id: 项目ID

        Returns:
            活动任务列表
        """
        return self._request('GET', f'/projects/{project_id}/tasks/active')

    def get_task_statistics(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目的任务统计信息

        Args:
            project_id: 项目ID

        Returns:
            统计信息
        """
        return self._request('GET', f'/projects/{project_id}/tasks/statistics')

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消正在执行的任务

        Args:
            task_id: 任务ID

        Returns:
            取消结果
        """
        return self._request('POST', f'/tasks/{task_id}/cancel')

    # ==================== 异步生成接口（支持async_mode参数）====================

    def generate_blueprint_async(
        self,
        project_id: str,
        force_regenerate: bool = False,
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """
        异步生成蓝图

        Args:
            project_id: 项目ID
            force_regenerate: 是否强制重新生成
            async_mode: 是否使用异步模式（默认True）

        Returns:
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
            同步模式：完整蓝图数据
        """
        params = {
            'force_regenerate': force_regenerate,
            'async_mode': async_mode
        }
        return self._request(
            'POST',
            f'/api/novels/{project_id}/blueprint/generate',
            params=params,
            timeout=600 if not async_mode else 30
        )

    def generate_all_chapter_outlines_async(
        self,
        project_id: str,
        async_mode: bool = True
    ) -> Dict[str, Any]:
        """
        异步生成所有章节大纲（首次生成/短篇小说）

        用于项目初始化阶段一次性生成全部章节大纲，
        适合短篇小说（章节数≤50）。

        Args:
            project_id: 项目ID
            async_mode: 是否使用异步模式（默认True）

        Returns:
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
            同步模式：完整大纲数据
        """
        params = {'async_mode': async_mode}
        return self._request(
            'POST',
            f'/api/novels/{project_id}/chapter-outlines/generate',
            params=params,
            timeout=400 if not async_mode else 30
        )

    def generate_chapter_async(
        self,
        project_id: str,
        chapter_number: int,
        writing_notes: Optional[str] = None,
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        异步生成章节

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            writing_notes: 写作指令（可选）
            async_mode: 是否使用异步模式（默认False，因为章节生成复杂度较高）

        Returns:
            异步模式：{"task_id": "...", "status": "pending", "message": "..."}
            同步模式：完整项目数据（包含生成的章节）
        """
        data = {
            'chapter_number': chapter_number,
            'writing_notes': writing_notes or ''
        }
        params = {'async_mode': async_mode}
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/generate',
            data=data,
            params=params,
            timeout=900 if not async_mode else 30
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
