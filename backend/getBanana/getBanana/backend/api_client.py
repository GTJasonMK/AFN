# -*- coding: utf-8 -*-
"""
API客户端模块
负责与图像生成API进行通信
"""

import re
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass


@dataclass
class GenerationResult:
    """生成结果数据类"""
    success: bool
    image_urls: List[str] = None
    error_message: str = ""

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []


class ApiClient:
    """API客户端类"""

    def __init__(self, base_url: str = "http://localhost:8000", retries: int = 3):
        """
        初始化API客户端

        Args:
            base_url: API基础URL（不含 /v1）
            retries: 重试次数
        """
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """创建带重试机制的session"""
        session = requests.Session()
        retry = Retry(
            total=self.retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504, 520, 521, 522, 523, 524]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def generate_images(
        self,
        api_key: str,
        prompt: str,
        model: str = "nano-banana-pro",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        count: int = 1,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """
        调用API生成图片

        Args:
            api_key: API密钥
            prompt: 提示词
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            count: 生成数量
            progress_callback: 进度回调函数

        Returns:
            GenerationResult: 生成结果
        """
        if not api_key:
            return GenerationResult(success=False, error_message="API Key为空")

        if not prompt:
            return GenerationResult(success=False, error_message="提示词为空")

        # 模型名称转小写（API 要求小写）
        model = model.lower()

        # 尝试请求，如果代理失败则绕过代理重试
        resp = None
        for attempt in range(2):
            try:
                proxies = None if attempt == 0 else {"http": None, "https": None}

                if attempt == 1 and progress_callback:
                    progress_callback("代理失败,重试中...")

                resp = self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "n": count
                    },
                    timeout=180,
                    proxies=proxies
                )
                break
            except (requests.exceptions.ProxyError, requests.exceptions.ConnectionError) as e:
                if attempt == 0:
                    continue
                return GenerationResult(
                    success=False,
                    error_message=f"网络连接失败: {str(e)}"
                )
            except requests.exceptions.Timeout:
                return GenerationResult(
                    success=False,
                    error_message="请求超时"
                )
            except Exception as e:
                return GenerationResult(
                    success=False,
                    error_message=f"请求异常: {str(e)}"
                )

        if resp is None:
            return GenerationResult(
                success=False,
                error_message="请求失败，请检查网络"
            )

        if resp.status_code != 200:
            # 针对常见错误码提供更友好的提示
            error_messages = {
                401: "API Key 无效或已过期",
                403: "访问被拒绝，请检查API Key权限",
                429: "请求过于频繁，请稍后再试",
                500: "服务器内部错误，请稍后再试",
                502: "服务器网关错误，请稍后再试",
                503: "服务器暂时不可用，请稍后再试",
                504: "服务器响应超时，请简化提示词后重试",
                524: "服务器处理超时（请求过于复杂），建议简化提示词，如减少帧数"
            }
            error_msg = error_messages.get(
                resp.status_code,
                f"API错误({resp.status_code})"
            )
            try:
                error_data = resp.json()
                server_msg = error_data.get("error", {}).get("message", "")
                if not server_msg:
                    server_msg = error_data.get("detail", "")
                if server_msg:
                    error_msg = f"{error_msg}: {server_msg}"
            except:
                pass
            return GenerationResult(success=False, error_message=error_msg)

        # 解析响应
        try:
            result = resp.json()
            content = result["choices"][0]["message"]["content"]

            # 从Markdown格式中提取图片URL
            # 支持两种格式：
            # 1. 完整URL: ![xxx](https://xxx.xxx/xxx.png)
            # 2. 本地路径: ![xxx](/images/xxx/xxx.png)
            urls = []

            # 提取完整 URL
            full_urls = re.findall(r'!\[.*?\]\((https?://[^\s\)]+)\)', content)
            urls.extend(full_urls)

            # 提取本地路径并转换为完整 URL
            local_paths = re.findall(r'!\[.*?\]\((/images/[^\s\)]+)\)', content)
            for path in local_paths:
                urls.append(f"{self.base_url}{path}")

            if not urls:
                # 如果没找到图片，返回文本内容作为错误信息
                return GenerationResult(
                    success=False,
                    error_message=f"未获取到图片URL，响应内容: {content[:200]}"
                )

            return GenerationResult(success=True, image_urls=urls)

        except (KeyError, IndexError) as e:
            return GenerationResult(
                success=False,
                error_message=f"解析响应失败: {str(e)}"
            )
        except json.JSONDecodeError as e:
            return GenerationResult(
                success=False,
                error_message=f"JSON解析失败: {str(e)}"
            )

    def download_image(self, url: str, timeout: int = 60) -> Optional[bytes]:
        """
        下载图片

        Args:
            url: 图片URL
            timeout: 超时时间

        Returns:
            图片二进制数据，失败返回None
        """
        try:
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                return resp.content
        except Exception as e:
            print(f"下载图片失败: {e}")
        return None
