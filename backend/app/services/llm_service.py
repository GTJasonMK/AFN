"""
LLM服务

负责与大语言模型的交互，包括文本生成和配置管理。
嵌入向量功能已拆分到 EmbeddingService。
"""

import asyncio
import json
import logging
import os
import warnings
from typing import Any, Dict, List, Optional

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from ..core.config import settings
from ..core.constants import LLMConstants
from ..exceptions import (
    LLMServiceError,
    LLMConfigurationError,
    PromptTemplateNotFoundError,
)
from ..repositories.llm_config_repository import LLMConfigRepository
from ..services.prompt_service import PromptService
from ..services.queue import LLMRequestQueue
from ..utils.llm_tool import ChatMessage, ContentCollectMode, LLMClient
from ..utils.encryption import decrypt_api_key
from ..utils.exception_helpers import log_exception

logger = logging.getLogger(__name__)


class LLMService:
    """封装与大模型交互的所有逻辑，包括配额控制与配置选择。"""

    def __init__(self, session):
        self.session = session
        self.llm_repo = LLMConfigRepository(session)
        # 延迟初始化服务（按需创建）
        self._embedding_service = None
        self._prompt_service = None

    @property
    def embedding_service(self):
        """获取嵌入服务（延迟初始化）"""
        if self._embedding_service is None:
            from .embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService(self.session)
        return self._embedding_service

    @property
    def prompt_service(self):
        """获取提示词服务（延迟初始化）"""
        if self._prompt_service is None:
            self._prompt_service = PromptService(self.session)
        return self._prompt_service

    # ------------------------------------------------------------------
    # LLM 响应获取
    # ------------------------------------------------------------------
    async def get_llm_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        user_id: Optional[int] = None,
        timeout: float = 300.0,
        response_format: Optional[str] = "json_object",
        max_tokens: Optional[int] = None,
        skip_usage_tracking: bool = False,
        skip_daily_limit_check: bool = False,
        cached_config: Optional[Dict[str, Optional[str]]] = None,
    ) -> str:
        """
        获取LLM响应（非流式）

        Args:
            system_prompt: 系统提示词
            conversation_history: 对话历史
            temperature: 温度参数
            user_id: 用户ID
            timeout: 超时时间
            response_format: 响应格式
            max_tokens: 最大token数
            skip_usage_tracking: 跳过使用量追踪
            skip_daily_limit_check: 跳过每日限额检查
            cached_config: 缓存的LLM配置

        Returns:
            LLM响应文本
        """
        messages = [{"role": "system", "content": system_prompt}, *conversation_history]
        return await self._stream_and_collect(
            messages,
            temperature=temperature,
            user_id=user_id,
            timeout=timeout,
            response_format=response_format,
            max_tokens=max_tokens,
            skip_usage_tracking=skip_usage_tracking,
            skip_daily_limit_check=skip_daily_limit_check,
            cached_config=cached_config,
        )

    async def stream_llm_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        user_id: Optional[int] = None,
        timeout: float = 300.0,
        response_format: Optional[str] = "json_object",
        max_tokens: Optional[int] = None,
    ):
        """
        流式获取LLM响应

        Args:
            system_prompt: 系统提示词
            conversation_history: 对话历史
            temperature: 温度参数
            user_id: 用户ID
            timeout: 超时时间
            response_format: 响应格式
            max_tokens: 最大token数

        Yields:
            Dict[str, str]: 包含content和finish_reason的字典
        """
        config = await self._resolve_llm_config(user_id)
        client = LLMClient.create_from_config(config, simulate_browser=True)

        messages = [{"role": "system", "content": system_prompt}, *conversation_history]
        chat_messages = ChatMessage.from_list(messages)

        logger.info(
            "Streaming LLM response: model=%s user_id=%s messages=%d",
            config.get("model"),
            user_id,
            len(messages),
        )

        # 通过队列控制并发
        queue = LLMRequestQueue.get_instance()
        async with queue.request_slot():
            try:
                async for chunk in client.stream_chat(
                    messages=chat_messages,
                    model=config.get("model"),
                    temperature=temperature,
                    timeout=int(timeout),
                    response_format=response_format,
                    max_tokens=max_tokens,
                ):
                    yield chunk
            except Exception as exc:
                logger.error(
                    "LLM stream error: model=%s user_id=%s error=%s",
                    config.get("model"),
                    user_id,
                    exc,
                )
                raise LLMServiceError(f"流式响应失败: {exc}", config.get("model")) from exc

    async def get_summary(
        self,
        chapter_content: str,
        *,
        temperature: float = 0.2,
        user_id: Optional[int] = None,
        timeout: float = 180.0,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        生成章节摘要

        Args:
            chapter_content: 章节内容
            temperature: 温度参数
            user_id: 用户ID
            timeout: 超时时间
            system_prompt: 自定义系统提示词

        Returns:
            摘要文本
        """
        if not system_prompt:
            system_prompt = await self.prompt_service.get_prompt("extraction")
        if not system_prompt:
            raise PromptTemplateNotFoundError("extraction")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chapter_content},
        ]
        return await self._stream_and_collect(messages, temperature=temperature, user_id=user_id, timeout=timeout)

    async def _stream_and_collect(
        self,
        messages: List[Dict[str, str]],
        *,
        temperature: float,
        user_id: Optional[int],
        timeout: float,
        response_format: Optional[str] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = LLMConstants.MAX_RETRIES,
        skip_usage_tracking: bool = False,
        skip_daily_limit_check: bool = False,
        cached_config: Optional[Dict[str, Optional[str]]] = None,
    ) -> str:
        """
        流式收集LLM响应，支持自动重试网络错误

        Args:
            messages: 消息列表
            temperature: 温度参数
            user_id: 用户ID
            timeout: 超时时间
            response_format: 响应格式
            max_tokens: 最大token数
            max_retries: 最大重试次数
            skip_usage_tracking: 跳过使用量追踪
            skip_daily_limit_check: 跳过每日限额检查
            cached_config: 缓存的LLM配置

        Returns:
            收集到的响应文本
        """
        # 使用缓存配置或实时查询配置
        if cached_config:
            config = cached_config
        else:
            config = await self._resolve_llm_config(user_id, skip_daily_limit_check=skip_daily_limit_check)

        # 通过队列控制并发
        queue = LLMRequestQueue.get_instance()
        async with queue.request_slot():
            return await self._do_stream_and_collect(
                messages=messages,
                config=config,
                temperature=temperature,
                user_id=user_id,
                timeout=timeout,
                response_format=response_format,
                max_tokens=max_tokens,
                max_retries=max_retries,
            )

    async def _do_stream_and_collect(
        self,
        messages: List[Dict[str, str]],
        config: Dict[str, Optional[str]],
        *,
        temperature: float,
        user_id: Optional[int],
        timeout: float,
        response_format: Optional[str] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = LLMConstants.MAX_RETRIES,
    ) -> str:
        """
        实际执行流式收集的内部方法（在队列槽位内执行）
        """
        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                client = LLMClient.create_from_config(config, simulate_browser=True)
                chat_messages = ChatMessage.from_list(messages)

                if attempt > 0:
                    logger.warning(
                        "Retrying LLM request: attempt=%d/%d model=%s user_id=%s",
                        attempt + 1,
                        max_retries + 1,
                        config.get("model"),
                        user_id,
                    )
                else:
                    logger.info(
                        "Streaming LLM response: model=%s user_id=%s messages=%d max_tokens=%s",
                        config.get("model"),
                        user_id,
                        len(messages),
                        max_tokens,
                    )

                result = await client.stream_and_collect(
                    messages=chat_messages,
                    model=config.get("model"),
                    temperature=temperature,
                    timeout=int(timeout),
                    response_format=response_format,
                    max_tokens=max_tokens,
                    collect_mode=ContentCollectMode.CONTENT_ONLY,
                )

                logger.debug(
                    "LLM response collected: model=%s user_id=%s finish_reason=%s chunks=%d preview=%s",
                    config.get("model"),
                    user_id,
                    result.finish_reason,
                    result.chunk_count,
                    result.content[:500],
                )

                self._validate_llm_response(result, config, user_id)

                logger.info(
                    "LLM response success: model=%s user_id=%s chars=%d chunks=%d attempts=%d",
                    config.get("model"),
                    user_id,
                    len(result.content),
                    result.chunk_count,
                    attempt + 1,
                )
                return result.content

            except InternalServerError as exc:
                default_detail = "AI 服务内部错误，请稍后重试"
                detail = self._extract_error_detail(exc, default_detail)
                logger.error(
                    "LLM stream internal error: model=%s user_id=%s attempt=%d/%d detail=%s",
                    config.get("model"),
                    user_id,
                    attempt + 1,
                    max_retries + 1,
                    detail,
                    exc_info=exc,
                )
                raise LLMServiceError(detail, config.get("model"))

            except (httpx.RemoteProtocolError, httpx.ReadTimeout, APIConnectionError, APITimeoutError) as exc:
                last_error = exc

                if isinstance(exc, httpx.RemoteProtocolError):
                    detail = "AI 服务连接被意外中断"
                elif isinstance(exc, (httpx.ReadTimeout, APITimeoutError)):
                    detail = "AI 服务响应超时"
                else:
                    detail = "无法连接到 AI 服务"

                logger.error(
                    "LLM stream failed: model=%s user_id=%s attempt=%d/%d detail=%s",
                    config.get("model"),
                    user_id,
                    attempt + 1,
                    max_retries + 1,
                    detail,
                    exc_info=exc,
                )

                if attempt < max_retries:
                    wait_time = 2 ** (attempt + 1)
                    logger.info("Waiting %d seconds before retry...", wait_time)
                    await asyncio.sleep(wait_time)
                    continue

                retry_hint = f"（已尝试 {max_retries + 1} 次）"
                raise LLMServiceError(
                    f"{detail}，请稍后重试 {retry_hint}",
                    config.get("model")
                ) from exc

            except RateLimitError as exc:
                last_error = exc
                detail = "AI 服务请求过于频繁"

                logger.warning(
                    "LLM rate limited: model=%s user_id=%s attempt=%d/%d",
                    config.get("model"),
                    user_id,
                    attempt + 1,
                    max_retries + 1,
                    exc_info=exc,
                )

                if attempt < max_retries:
                    wait_time = 10 * (attempt + 1)
                    logger.info("Rate limited, waiting %d seconds before retry...", wait_time)
                    await asyncio.sleep(wait_time)
                    continue

                retry_hint = f"（已尝试 {max_retries + 1} 次）"
                raise LLMServiceError(
                    f"{detail}，请稍后重试 {retry_hint}",
                    config.get("model")
                ) from exc

            except Exception as exc:
                logger.critical(
                    "LLM stream unexpected error: model=%s user_id=%s attempt=%d/%d error_type=%s error=%s",
                    config.get("model"),
                    user_id,
                    attempt + 1,
                    max_retries + 1,
                    type(exc).__name__,
                    str(exc),
                    exc_info=True,
                )
                raise LLMServiceError(
                    f"AI 服务发生意外错误: {type(exc).__name__}: {str(exc)}",
                    config.get("model")
                ) from exc

        # 注：此处代码逻辑上不可达，因为循环内所有分支都会 return、raise 或 continue
        # 保留一个兜底异常以满足类型检查器要求
        raise LLMServiceError("LLM 调用未能完成", config.get("model"))

    def _validate_llm_response(
        self,
        result: Any,
        config: Dict[str, Optional[str]],
        user_id: Optional[int],
    ) -> None:
        """验证LLM响应结果"""
        if result.finish_reason == "length":
            logger.warning(
                "LLM response truncated: model=%s user_id=%s",
                config.get("model"),
                user_id,
            )
            raise LLMServiceError("AI 响应被截断，请缩短输入或调整参数", config.get("model"))

        if not result.content:
            logger.error(
                "LLM returned empty response: model=%s user_id=%s chunks=%d",
                config.get("model"),
                user_id,
                result.chunk_count,
            )
            raise LLMServiceError("AI 未返回有效内容", config.get("model"))

    def _extract_error_detail(self, exc: InternalServerError, default_detail: str) -> str:
        """从InternalServerError中提取错误详情"""
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                payload = response.json()
                error_data = payload.get("error", {}) if isinstance(payload, dict) else {}
                return error_data.get("message_zh") or error_data.get("message") or default_detail
            except (json.JSONDecodeError, ValueError, AttributeError):
                return str(exc) or default_detail
        return str(exc) or default_detail

    # ------------------------------------------------------------------
    # 配置解析
    # ------------------------------------------------------------------
    async def _resolve_llm_config(self, user_id: Optional[int], skip_daily_limit_check: bool = False) -> Dict[str, Optional[str]]:
        """解析LLM配置"""
        if user_id is not None:
            try:
                config = await self.llm_repo.get_active_config(user_id)
            except (OSError, asyncio.TimeoutError) as exc:
                # 数据库连接或超时错误
                log_exception(exc, "查询用户LLM配置（数据库连接问题）", user_id=user_id)
                raise LLMConfigurationError(f"数据库访问失败: {type(exc).__name__}") from exc

            if config and config.llm_provider_api_key:
                decrypted_key = decrypt_api_key(config.llm_provider_api_key, settings.secret_key)
                if decrypted_key:
                    logger.debug("使用用户自定义 LLM 配置: user_id=%s", user_id)
                    return {
                        "api_key": decrypted_key,
                        "base_url": config.llm_provider_url,
                        "model": config.llm_provider_model,
                    }

        api_key = await self._get_config_value("llm.api_key")
        base_url = await self._get_config_value("llm.base_url")
        model = await self._get_config_value("llm.model")

        if not api_key:
            raise LLMConfigurationError("未配置默认 LLM API Key")

        return {"api_key": api_key, "base_url": base_url, "model": model}

    async def resolve_llm_config_cached(
        self,
        user_id: Optional[int],
        skip_daily_limit_check: bool = False
    ) -> Dict[str, Optional[str]]:
        """解析LLM配置（公共接口）"""
        return await self._resolve_llm_config(user_id, skip_daily_limit_check)

    async def _get_config_value(self, key: str) -> Optional[str]:
        """从环境变量读取配置"""
        env_key = key.upper().replace(".", "_")
        return os.getenv(env_key)

    # ------------------------------------------------------------------
    # 嵌入向量功能（委托给 EmbeddingService）
    # 已废弃：请直接使用 EmbeddingService
    # ------------------------------------------------------------------
    async def get_embedding(
        self,
        text: str,
        *,
        user_id: Optional[int] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ) -> List[float]:
        """
        生成文本向量（委托给 EmbeddingService）

        .. deprecated::
            此方法已废弃，请直接使用 EmbeddingService.get_embedding()。
            保留此方法仅为向后兼容，将在未来版本中移除。
        """
        warnings.warn(
            "LLMService.get_embedding() 已废弃，请直接使用 EmbeddingService.get_embedding()",
            DeprecationWarning,
            stacklevel=2,
        )
        return await self.embedding_service.get_embedding(
            text,
            user_id=user_id,
            model=model,
            max_retries=max_retries,
        )

    def get_embedding_dimension(self, model: Optional[str] = None) -> Optional[int]:
        """
        获取嵌入向量维度（委托给 EmbeddingService）

        .. deprecated::
            此方法已废弃，请直接使用 EmbeddingService.get_dimension()。
            保留此方法仅为向后兼容，将在未来版本中移除。
        """
        warnings.warn(
            "LLMService.get_embedding_dimension() 已废弃，请直接使用 EmbeddingService.get_dimension()",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.embedding_service.get_dimension(model)
