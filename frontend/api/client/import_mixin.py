"""
导入分析 Mixin

提供外部小说导入和分析功能。
"""

import logging
from typing import Any, Dict, Optional

import requests

from api.exceptions import APIError, create_api_error

logger = logging.getLogger(__name__)


class ImportMixin:
    """导入分析方法 Mixin"""

    def import_txt_file(
        self,
        project_id: str,
        file_path: str,
    ) -> Dict[str, Any]:
        """
        导入TXT文件到项目

        Args:
            project_id: 项目ID
            file_path: TXT文件路径

        Returns:
            导入结果，包含章节数量、解析信息等
        """
        url = f"{self.base_url}/api/novels/{project_id}/import-txt"

        try:
            with open(file_path, 'rb') as f:
                # 获取文件名
                import os
                filename = os.path.basename(file_path)
                files = {'file': (filename, f, 'text/plain; charset=utf-8')}

                # 文件上传使用独立的requests.post，避免session的Content-Type干扰
                response = requests.post(
                    url,
                    files=files,
                    proxies=self.session.proxies,
                    timeout=(10, 120),  # 上传可能需要较长时间
                )
                response.raise_for_status()
                return response.json()

        except FileNotFoundError:
            raise APIError(message=f"文件不存在: {file_path}")
        except requests.HTTPError as e:
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

            logger.error(f"导入TXT失败: {error_msg}")
            raise create_api_error(
                status_code=status_code,
                message=error_msg,
                response_data=response_data,
                original_error=e
            )
        except Exception as e:
            logger.error(f"导入TXT发生错误: {e}")
            raise APIError(message=f"导入失败: {str(e)}", original_error=e)

    def start_import_analysis(self, project_id: str) -> Dict[str, Any]:
        """
        启动导入项目的分析任务

        Args:
            project_id: 项目ID

        Returns:
            启动状态
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/analyze',
            timeout=30,
        )

    def get_import_analysis_status(self, project_id: str) -> Dict[str, Any]:
        """
        获取分析进度

        Args:
            project_id: 项目ID

        Returns:
            分析状态和进度信息
        """
        return self._request(
            'GET',
            f'/api/novels/{project_id}/analyze/status',
        )

    def cancel_import_analysis(self, project_id: str) -> Dict[str, Any]:
        """
        取消分析任务

        Args:
            project_id: 项目ID

        Returns:
            取消状态
        """
        return self._request(
            'POST',
            f'/api/novels/{project_id}/analyze/cancel',
        )
