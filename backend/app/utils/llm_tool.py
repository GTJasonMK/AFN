# -*- coding: utf-8 -*-
"""OpenAI 兼容型 LLM 工具封装，提供统一的请求、收集、重试机制。"""

import logging
import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

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
    """异步流式调用封装，兼容 OpenAI SDK。"""

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
        流式聊天请求。

        Args:
            messages: 消息列表
            model: 模型名称
            response_format: 响应格式（如 "json_object"）
            temperature: 温度参数
            top_p: Top-P 参数
            max_tokens: 最大token数
            timeout: 超时时间（秒）
            **kwargs: 其他参数

        Yields:
            字典格式的流式响应，包含 content、reasoning_content、finish_reason
        """
        payload = {
            "model": model or os.environ.get("MODEL", "gpt-3.5-turbo"),
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

        # 使用 with_options() 设置超时，而不是放在payload中
        # 这是OpenAI SDK v1.x的标准做法，兼容newapi等代理服务
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

            # 检查是否有reasoning_content（DeepSeek R1特有）
            if hasattr(choice.delta, 'reasoning_content') and choice.delta.reasoning_content:
                result["reasoning_content"] = choice.delta.reasoning_content

            yield result

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
