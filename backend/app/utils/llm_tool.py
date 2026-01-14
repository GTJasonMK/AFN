# -*- coding: utf-8 -*-
"""LLM 工具封装，提供统一的请求、收集、重试机制。

支持：
1. OpenAI Chat Completions API格式（GPT、通义千问、DeepSeek等）
2. Anthropic Messages API格式（Claude系列模型）

自动检测：根据模型名称自动选择API格式
- 模型名包含'claude' -> 使用Anthropic格式 (/v1/messages)
- 其他模型 -> 使用OpenAI格式 (/v1/chat/completions)
"""

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional

import httpx
from openai import AsyncOpenAI

# 从拆分后的模块导入
from .llm_request_logger import LLMRequestLogger, get_request_logger
from .api_format_utils import (
    APIFormat,
    detect_api_format,
    fix_base_url,
    build_anthropic_endpoint,
    build_openai_endpoint,
    get_browser_headers,
)

logger = logging.getLogger(__name__)


class ContentCollectMode(Enum):
    """流式响应收集模式"""
    CONTENT_ONLY = "content_only"  # 仅收集最终答案（用于结构化输出）
    WITH_REASONING = "with_reasoning"  # 收集答案+思考过程
    REASONING_ONLY = "reasoning_only"  # 仅收集思考过程


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "ChatMessage":
        """从字典创建消息"""
        return cls(role=data["role"], content=data["content"])

    @classmethod
    def from_list(cls, messages: List[Dict[str, str]]) -> List["ChatMessage"]:
        """批量转换消息列表"""
        return [cls.from_dict(msg) for msg in messages]


@dataclass
class StreamCollectResult:
    """流式收集结果"""
    content: str  # 最终答案
    reasoning: str  # 思考过程（如有）
    finish_reason: Optional[str]  # 完成原因
    chunk_count: int  # 收到的chunk数量


class LLMClient:
    """异步流式调用封装，支持OpenAI和Anthropic API格式。"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        strict_mode: bool = False,
        simulate_browser: bool = False
    ):
        """
        初始化 LLM 客户端。

        Args:
            api_key: API Key，如果为 None 且非严格模式，会回退到环境变量
            base_url: API Base URL，如果为 None 且非严格模式，会回退到环境变量
            strict_mode: 严格模式，为 True 时不回退到环境变量（用于测试配置）
            simulate_browser: 是否模拟浏览器请求头，用于绕过 Cloudflare 检测
        """
        if strict_mode:
            # 严格模式：不回退到环境变量，必须明确提供参数
            if not api_key:
                raise ValueError("严格模式下必须提供 API Key")
            key = api_key
            url = base_url  # 可以是 None，由 OpenAI SDK 使用默认值
        else:
            # 兼容模式：回退到环境变量
            key = api_key or os.environ.get("OPENAI_API_KEY")
            if not key:
                raise ValueError("缺少 OPENAI_API_KEY 配置，请在数据库或环境变量中补全。")
            url = base_url or os.environ.get("OPENAI_API_BASE")

        # 保存api_key和base_url供直接HTTP调用使用（Anthropic格式需要）
        self._api_key = key
        self._base_url = url
        self._simulate_browser = simulate_browser

        # 如果需要模拟浏览器，添加浏览器请求头
        default_headers = {}
        if simulate_browser:
            default_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            }

        self._client = AsyncOpenAI(
            api_key=key,
            base_url=url,
            default_headers=default_headers if default_headers else None
        )

    def _get_anthropic_headers(self) -> Dict[str, str]:
        """获取Anthropic API请求头"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self._api_key}',
            'anthropic-version': '2023-06-01',  # Anthropic API版本头
        }

        if self._simulate_browser:
            headers.update(get_browser_headers())

        return headers

    async def _stream_chat_anthropic(
        self,
        messages: List[ChatMessage],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        使用Anthropic Messages API进行流式聊天请求

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）

        Yields:
            字典格式的流式响应
        """
        # 构建Anthropic API端点
        endpoint = build_anthropic_endpoint(self._base_url)
        headers = self._get_anthropic_headers()

        # 将ChatMessage转换为Anthropic格式
        # Anthropic格式：[{"role": "user/assistant", "content": "..."}]
        # 注意：Anthropic不支持system role在messages中，需要单独传递
        system_content = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        # 构建请求体
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "stream": True,
            "max_tokens": max_tokens or 4096,
        }

        if system_content:
            payload["system"] = system_content

        if temperature is not None:
            payload["temperature"] = temperature

        # 创建请求日志
        request_id = str(uuid.uuid4())[:8]
        req_logger = get_request_logger()
        all_messages = [{"role": "system", "content": system_content}] if system_content else []
        all_messages.extend(anthropic_messages)
        log_entry = req_logger.log_request(
            request_id=request_id,
            api_format="anthropic",
            endpoint=endpoint,
            model=model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            base_url=self._base_url,
            api_key=self._api_key,
        )

        logger.info(
            "Anthropic API请求[%s]: endpoint=%s, model=%s",
            request_id, endpoint, model
        )

        # 用于收集响应信息
        collected_content = ""
        chunk_count = 0

        try:
            # 使用更细粒度的超时配置，提高连接稳定性
            # connect: 建立连接的超时时间
            # read: 读取响应的超时时间（流式响应需要较长时间）
            # write: 发送请求的超时时间
            # pool: 从连接池获取连接的超时时间
            timeout_config = httpx.Timeout(
                connect=30.0,
                read=float(timeout),
                write=30.0,
                pool=10.0
            )
            # 配置连接限制，避免连接耗尽
            limits = httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0
            )
            async with httpx.AsyncClient(
                timeout=timeout_config,
                limits=limits,
                http2=True,  # 启用HTTP/2，更稳定的连接复用
            ) as client:
                async with client.stream(
                    'POST',
                    endpoint,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_msg = error_text.decode('utf-8', errors='replace')[:500]
                        logger.error(
                            "Anthropic API错误[%s]: status=%d, response=%s",
                            request_id, response.status_code, error_msg
                        )
                        req_logger.log_error(
                            log_entry,
                            error_type="HTTPError",
                            error_message=error_msg,
                            status_code=response.status_code,
                        )
                        raise Exception(f"Anthropic API错误({response.status_code}): {error_msg}")

                    # 解析SSE流式响应
                    async for line in response.aiter_lines():
                        if not line or not line.startswith('data: '):
                            continue

                        data_str = line[6:]  # 移除 "data: " 前缀

                        if data_str == '[DONE]':
                            break

                        try:
                            chunk = json.loads(data_str)

                            # Anthropic流式响应格式解析
                            event_type = chunk.get('type', '')

                            if event_type == 'content_block_delta':
                                delta = chunk.get('delta', {})
                                if delta.get('type') == 'text_delta':
                                    text = delta.get('text', '')
                                    if text:
                                        chunk_count += 1
                                        collected_content += text
                                        yield {
                                            "content": text,
                                            "finish_reason": None,
                                        }
                            elif event_type == 'message_delta':
                                # 消息结束
                                stop_reason = chunk.get('delta', {}).get('stop_reason')
                                if stop_reason:
                                    yield {
                                        "content": None,
                                        "finish_reason": stop_reason,
                                    }
                            elif event_type == 'message_stop':
                                # 流结束
                                yield {
                                    "content": None,
                                    "finish_reason": "stop",
                                }

                        except json.JSONDecodeError:
                            continue

            # 请求成功，记录日志
            req_logger.log_success(
                log_entry,
                response_length=len(collected_content),
                chunk_count=chunk_count,
                response_preview=collected_content,
            )
            logger.info(
                "Anthropic API成功[%s]: chunks=%d, length=%d",
                request_id, chunk_count, len(collected_content)
            )

        except httpx.TimeoutException:
            logger.error("Anthropic API请求超时[%s]: model=%s, timeout=%d", request_id, model, timeout)
            req_logger.log_error(
                log_entry,
                error_type="TimeoutError",
                error_message=f"请求超时({timeout}秒)",
            )
            raise
        except Exception as e:
            # 如果不是已经记录过的HTTP错误
            if "Anthropic API错误" not in str(e):
                req_logger.log_error(
                    log_entry,
                    error_type=type(e).__name__,
                    error_message=str(e),
                )
            logger.error(
                "Anthropic API请求失败[%s]: model=%s, error_type=%s, error=%s",
                request_id, model, type(e).__name__, str(e),
                exc_info=True
            )
            raise

    async def _stream_chat_openai(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        使用OpenAI Chat Completions API进行流式聊天请求

        Args:
            messages: 消息列表
            model: 模型名称
            response_format: 响应格式（如 "json_object"）
            temperature: 温度参数
            top_p: Top-P 参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）

        Yields:
            字典格式的流式响应
        """
        actual_model = model or os.environ.get("MODEL", "gpt-3.5-turbo")
        payload = {
            "model": actual_model,
            "messages": [msg.to_dict() for msg in messages],
            "stream": True,
            **kwargs,
        }
        if response_format:
            payload["response_format"] = {"type": response_format}
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["top_p"] = top_p
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        # 创建请求日志
        request_id = str(uuid.uuid4())[:8]
        req_logger = get_request_logger()
        endpoint = build_openai_endpoint(self._base_url) if self._base_url else "https://api.openai.com/v1/chat/completions"
        log_entry = req_logger.log_request(
            request_id=request_id,
            api_format="openai",
            endpoint=endpoint,
            model=actual_model,
            messages=[msg.to_dict() for msg in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            base_url=self._base_url or "https://api.openai.com",
            api_key=self._api_key,
            extra_params={"top_p": top_p, "response_format": response_format} if (top_p or response_format) else None,
        )

        # 用于收集响应信息
        collected_content = ""
        chunk_count = 0

        try:
            # 调试日志
            http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
            https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            all_proxy = os.environ.get("ALL_PROXY") or os.environ.get("all_proxy")
            logger.info(
                "OpenAI API请求[%s]: base_url=%s, model=%s, HTTP_PROXY=%s, HTTPS_PROXY=%s, ALL_PROXY=%s",
                request_id,
                self._client.base_url,
                actual_model,
                http_proxy,
                https_proxy,
                all_proxy
            )
            stream = await self._client.with_options(timeout=float(timeout)).chat.completions.create(**payload)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]

                # 支持DeepSeek R1等模型的reasoning_content字段
                result = {
                    "content": choice.delta.content,
                    "finish_reason": choice.finish_reason,
                }

                # 收集响应内容
                if choice.delta.content:
                    chunk_count += 1
                    collected_content += choice.delta.content

                # 检查是否有reasoning_content（DeepSeek R1特有）
                if hasattr(choice.delta, 'reasoning_content') and choice.delta.reasoning_content:
                    result["reasoning_content"] = choice.delta.reasoning_content

                yield result

            # 请求成功，记录日志
            req_logger.log_success(
                log_entry,
                response_length=len(collected_content),
                chunk_count=chunk_count,
                response_preview=collected_content,
            )
            logger.info(
                "OpenAI API成功[%s]: chunks=%d, length=%d",
                request_id, chunk_count, len(collected_content)
            )

        except Exception as e:
            req_logger.log_error(
                log_entry,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            logger.error(
                "OpenAI API请求失败[%s]: model=%s, error_type=%s, error=%s",
                request_id,
                actual_model,
                type(e).__name__,
                str(e),
                exc_info=True
            )
            raise

    async def stream_chat(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        **kwargs,
    ) -> AsyncGenerator[Dict[str, str], None]:
        """
        流式聊天请求（自动检测API格式）

        根据模型名称自动选择API格式：
        - Claude模型 -> Anthropic Messages API
        - 其他模型 -> OpenAI Chat Completions API

        Args:
            messages: 消息列表
            model: 模型名称
            response_format: 响应格式（如 "json_object"）- 仅OpenAI格式支持
            temperature: 温度参数
            top_p: Top-P 参数 - 仅OpenAI格式支持
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            **kwargs: 其他参数

        Yields:
            字典格式的流式响应，包含 content、reasoning_content、finish_reason
        """
        actual_model = model or os.environ.get("MODEL", "gpt-3.5-turbo")
        api_format = detect_api_format(actual_model)

        logger.info(
            "LLM请求: model=%s, api_format=%s",
            actual_model, api_format.value
        )

        if api_format == APIFormat.ANTHROPIC:
            # 使用Anthropic Messages API
            async for chunk in self._stream_chat_anthropic(
                messages=messages,
                model=actual_model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs,
            ):
                yield chunk
        else:
            # 使用OpenAI Chat Completions API
            async for chunk in self._stream_chat_openai(
                messages=messages,
                model=actual_model,
                response_format=response_format,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs,
            ):
                yield chunk

    async def stream_and_collect(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: int = 120,
        collect_mode: ContentCollectMode = ContentCollectMode.CONTENT_ONLY,
        log_chunks: bool = False,
        **kwargs,
    ) -> StreamCollectResult:
        """
        流式请求并收集完整响应（便捷方法）。

        Args:
            messages: 消息列表
            model: 模型名称
            response_format: 响应格式
            temperature: 温度参数
            top_p: Top-P 参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            collect_mode: 收集模式
            log_chunks: 是否记录chunk日志（仅前3个）
            **kwargs: 其他参数

        Returns:
            StreamCollectResult: 收集结果
        """
        content = ""
        reasoning = ""
        finish_reason = None
        chunk_count = 0

        try:
            async for chunk in self.stream_chat(
                messages=messages,
                model=model,
                response_format=response_format,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs,
            ):
                chunk_count += 1

                # 可选的日志记录
                if log_chunks and chunk_count <= 3:
                    logger.debug("收到第 %d 个 chunk: %s", chunk_count, chunk)

                # 根据收集模式决定收集哪些内容
                if collect_mode in (ContentCollectMode.CONTENT_ONLY, ContentCollectMode.WITH_REASONING):
                    if chunk.get("content"):
                        content += chunk["content"]

                if collect_mode in (ContentCollectMode.WITH_REASONING, ContentCollectMode.REASONING_ONLY):
                    if chunk.get("reasoning_content"):
                        reasoning += chunk["reasoning_content"]

                if chunk.get("finish_reason"):
                    finish_reason = chunk["finish_reason"]
        except Exception as e:
            logger.error(
                "stream_and_collect error after %d chunks: model=%s error_type=%s error=%s",
                chunk_count,
                model,
                type(e).__name__,
                str(e),
                exc_info=True
            )
            raise

        return StreamCollectResult(
            content=content,
            reasoning=reasoning,
            finish_reason=finish_reason,
            chunk_count=chunk_count,
        )

    @classmethod
    def create_from_config(
        cls,
        config: Dict[str, Optional[str]],
        strict_mode: bool = False,
        simulate_browser: bool = True,
    ) -> "LLMClient":
        """
        从配置字典创建客户端（工厂方法）。

        Args:
            config: 配置字典，包含 api_key、base_url、model
            strict_mode: 是否启用严格模式
            simulate_browser: 是否模拟浏览器请求头

        Returns:
            LLMClient 实例
        """
        return cls(
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            strict_mode=strict_mode,
            simulate_browser=simulate_browser,
        )
