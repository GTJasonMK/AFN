import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    InternalServerError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from ..core.config import settings
from ..core.constants import LLMConstants
from ..exceptions import (
    LLMServiceError,
    LLMConfigurationError,
    PromptTemplateNotFoundError,
    VectorStoreError,
    InvalidParameterError,
)
from ..repositories.llm_config_repository import LLMConfigRepository
from ..services.prompt_service import PromptService
from ..utils.llm_tool import ChatMessage, ContentCollectMode, LLMClient
from ..utils.encryption import decrypt_api_key
from ..utils.exception_helpers import log_exception

logger = logging.getLogger(__name__)

try:  # pragma: no cover - 运行环境未安装时兼容
    from ollama import AsyncClient as OllamaAsyncClient
except ImportError:  # pragma: no cover - Ollama 为可选依赖
    OllamaAsyncClient = None


class LLMService:
    """封装与大模型交互的所有逻辑，包括配额控制与配置选择。"""

    def __init__(self, session):
        self.session = session
        self.llm_repo = LLMConfigRepository(session)
        self._embedding_dimensions: Dict[str, int] = {}

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

    def _validate_llm_response(
        self,
        result: Any,
        config: Dict[str, Optional[str]],
        user_id: Optional[int],
    ) -> None:
        """
        验证LLM响应结果

        Args:
            result: LLM响应结果对象
            config: LLM配置字典
            user_id: 用户ID

        Raises:
            LLMServiceError: 如果响应无效
        """
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
        """
        从InternalServerError中提取错误详情

        Args:
            exc: InternalServerError异常对象
            default_detail: 默认错误信息

        Returns:
            str: 提取的错误详情
        """
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                payload = response.json()
                error_data = payload.get("error", {}) if isinstance(payload, dict) else {}
                return error_data.get("message_zh") or error_data.get("message") or default_detail
            except Exception:
                return str(exc) or default_detail
        return str(exc) or default_detail

    async def get_summary(
        self,
        chapter_content: str,
        *,
        temperature: float = 0.2,
        user_id: Optional[int] = None,
        timeout: float = 180.0,
        system_prompt: Optional[str] = None,
    ) -> str:
        if not system_prompt:
            prompt_service = PromptService(self.session)
            system_prompt = await prompt_service.get_prompt("extraction")
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
        """流式收集 LLM 响应，支持自动重试网络错误

        Args:
            max_retries: 最大重试次数（默认2次，总共最多3次尝试）
            skip_usage_tracking: 跳过 API 请求计数（用于并行模式）
            skip_daily_limit_check: 跳过每日限额检查（用于并行模式）
            cached_config: 缓存的 LLM 配置（用于并行模式，避免并发数据库查询）
        """
        # 使用缓存配置或实时查询配置
        if cached_config:
            config = cached_config
        else:
            config = await self._resolve_llm_config(user_id, skip_daily_limit_check=skip_daily_limit_check)

        last_error: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                # 使用工厂方法创建客户端，统一配置浏览器模拟
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

                # 使用统一的流式收集方法
                # 对于结构化输出（如蓝图生成），只收集最终答案，忽略思考过程以避免JSON解析错误
                result = await client.stream_and_collect(
                    messages=chat_messages,
                    model=config.get("model"),
                    temperature=temperature,
                    timeout=int(timeout),
                    response_format=response_format,
                    max_tokens=max_tokens,
                    collect_mode=ContentCollectMode.CONTENT_ONLY,
                )

                # 成功完成，跳出重试循环
                logger.debug(
                    "LLM response collected: model=%s user_id=%s finish_reason=%s chunks=%d preview=%s",
                    config.get("model"),
                    user_id,
                    result.finish_reason,
                    result.chunk_count,
                    result.content[:500],
                )

                # 验证响应有效性
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
                # 内部错误不重试，直接抛出
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

                # 如果还有重试机会，继续重试
                if attempt < max_retries:
                    import asyncio
                    # 指数退避：第1次重试等待2秒，第2次等待4秒
                    wait_time = 2 ** (attempt + 1)
                    logger.info("Waiting %d seconds before retry...", wait_time)
                    await asyncio.sleep(wait_time)
                    continue

                # 已达到最大重试次数，抛出错误
                retry_hint = f"（已尝试 {max_retries + 1} 次）"
                raise LLMServiceError(
                    f"{detail}，请稍后重试 {retry_hint}",
                    config.get("model")
                ) from exc

            except Exception as exc:
                # 捕获所有其他未预期的异常，防止进程崩溃
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

        # 理论上不应该到达这里，但为了代码完整性保留
        if last_error:
            raise LLMServiceError(
                "AI 服务连接失败，请检查网络或稍后重试",
                config.get("model")
            ) from last_error

        raise LLMServiceError("未知错误")

    async def _resolve_llm_config(self, user_id: Optional[int], skip_daily_limit_check: bool = False) -> Dict[str, Optional[str]]:
        """
        解析LLM配置

        Args:
            user_id: 用户ID
            skip_daily_limit_check: 是否跳过每日限额检查

        Returns:
            LLM配置字典
        """
        if user_id:
            try:
                # 使用激活的配置而不是第一个配置
                config = await self.llm_repo.get_active_config(user_id)
            except Exception as exc:
                log_exception(exc, "查询用户LLM配置", user_id=user_id)
                raise

            if config and config.llm_provider_api_key:
                # 解密API密钥
                decrypted_key = decrypt_api_key(config.llm_provider_api_key, settings.secret_key)
                if decrypted_key:
                    logger.debug("使用用户自定义 LLM 配置: user_id=%s", user_id)
                    return {
                        "api_key": decrypted_key,
                        "base_url": config.llm_provider_url,
                        "model": config.llm_provider_model,
                    }

        # 检���每日使用次数限制（仅在非跳过模式下）
        if user_id and not skip_daily_limit_check:
            await self._enforce_daily_limit(user_id)

        api_key = await self._get_config_value("llm.api_key")
        base_url = await self._get_config_value("llm.base_url")
        model = await self._get_config_value("llm.model")

        if not api_key:
            raise LLMConfigurationError("未配置默认 LLM API Key")

        return {"api_key": api_key, "base_url": base_url, "model": model}

    async def get_embedding(
        self,
        text: str,
        *,
        user_id: Optional[int] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
    ) -> List[float]:
        """
        生成文本向量，用于章节 RAG 检索。

        只使用数据库中激活的嵌入配置，不再回退到环境变量。
        支持 OpenAI 兼容 API 和本地 Ollama 两种提供方。
        对于可重试错误（网络/超时/限流），会进行最多 max_retries 次重试。

        Args:
            text: 要嵌入的文本
            user_id: 用户ID
            model: 可选的模型名称覆盖
            max_retries: 最大重试次数，默认3次

        Returns:
            嵌入向量列表，失败时返回空列表

        Raises:
            LLMConfigurationError: 当没有配置激活的嵌入模型时抛出
        """
        # 从数据库获取激活的嵌入配置（唯一配置来源）
        embedding_config = await self._resolve_embedding_config(user_id)

        if not embedding_config:
            logger.error("未配置嵌入模型，请在设置页面添加并激活嵌入模型配置")
            raise LLMConfigurationError(
                "未配置嵌入模型。请在「设置 → 嵌入模型」中添加并激活一个嵌入模型配置。"
            )

        # 使用数据库配置
        provider = embedding_config.get("provider", "openai")
        target_model = model or embedding_config.get("model")
        api_key = embedding_config.get("api_key")
        base_url = embedding_config.get("base_url")

        # 重试逻辑
        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):  # 0 到 max_retries，共 max_retries+1 次尝试
            try:
                if provider == "ollama":
                    embedding = await self._get_ollama_embedding(
                        text=text,
                        target_model=target_model,
                        base_url=base_url,
                    )
                else:
                    embedding = await self._get_openai_embedding(
                        text=text,
                        target_model=target_model,
                        api_key=api_key,
                        base_url=base_url,
                        user_id=user_id,
                    )

                if embedding:
                    # 成功获取嵌入向量
                    if attempt > 0:
                        logger.info(
                            "嵌入请求在第 %d 次重试后成功: model=%s",
                            attempt,
                            target_model,
                        )
                    return embedding
                else:
                    # 返回空向量（非异常情况）
                    return []

            except LLMConfigurationError:
                # 配置错误不重试，直接抛出
                raise
            except Exception as exc:
                last_error = exc
                if not self._is_retryable_error(exc):
                    # 不可重试的错误，直接返回空列表
                    logger.error(
                        "嵌入请求失败（不可重试）: model=%s error=%s",
                        target_model,
                        exc,
                        exc_info=True,
                    )
                    return []

                # 可重试错误
                if attempt < max_retries:
                    # 指数退避延迟：1s, 2s, 4s...
                    delay = 2 ** attempt
                    logger.warning(
                        "嵌入请求失败，将在 %d 秒后重试 (%d/%d): model=%s error=%s",
                        delay,
                        attempt + 1,
                        max_retries,
                        target_model,
                        exc,
                    )
                    await asyncio.sleep(delay)
                else:
                    # 超过最大重试次数
                    logger.error(
                        "嵌入请求失败，已达到最大重试次数 (%d): model=%s error=%s",
                        max_retries,
                        target_model,
                        exc,
                    )

        # 所有重试都失败了
        return []

    async def _get_ollama_embedding(
        self,
        text: str,
        target_model: str,
        base_url: Optional[str],
    ) -> List[float]:
        """调用 Ollama 生成嵌入向量（内部方法）"""
        if OllamaAsyncClient is None:
            logger.error("未安装 ollama 依赖，无法调用本地嵌入模型。")
            raise LLMConfigurationError("缺少 Ollama 依赖，请先安装 ollama 包")

        # Ollama base_url 回退
        if not base_url:
            base_url_any = settings.ollama_embedding_base_url or settings.embedding_base_url
            base_url = str(base_url_any) if base_url_any else None

        client = OllamaAsyncClient(host=base_url)
        response = await client.embeddings(model=target_model, prompt=text)

        embedding: Optional[List[float]]
        if isinstance(response, dict):
            embedding = response.get("embedding")
        else:
            embedding = getattr(response, "embedding", None)

        if not embedding:
            logger.warning("Ollama 返回空向量: model=%s", target_model)
            return []

        if not isinstance(embedding, list):
            embedding = list(embedding)

        # 缓存向量维度
        dimension = len(embedding)
        if dimension:
            self._embedding_dimensions[target_model] = dimension

        return embedding

    async def _get_openai_embedding(
        self,
        text: str,
        target_model: str,
        api_key: Optional[str],
        base_url: Optional[str],
        user_id: Optional[int],
    ) -> List[float]:
        """调用 OpenAI 兼容 API 生成嵌入向量（内部方法）"""
        if not api_key:
            raise LLMConfigurationError(
                "嵌入模型配置缺少 API Key。请在「设置 → 嵌入模型」中检查配置。"
            )

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        try:
            response = await client.embeddings.create(
                input=text,
                model=target_model,
            )
        except AuthenticationError as exc:
            logger.error(
                "OpenAI 嵌入认证失败: model=%s user_id=%s",
                target_model,
                user_id,
                exc_info=True,
            )
            raise LLMConfigurationError("AI服务认证失败，请检查API密钥配置") from exc
        except BadRequestError as exc:
            logger.error(
                "OpenAI 嵌入请求无效: model=%s user_id=%s error=%s",
                target_model,
                user_id,
                exc,
                exc_info=True,
            )
            raise InvalidParameterError(f"嵌入请求无效: {str(exc)}") from exc

        if not response.data:
            logger.warning("OpenAI 嵌入请求返回空数据: model=%s user_id=%s", target_model, user_id)
            return []

        embedding = response.data[0].embedding

        if not isinstance(embedding, list):
            embedding = list(embedding)

        # 缓存向量维度
        dimension = len(embedding)
        if dimension:
            self._embedding_dimensions[target_model] = dimension

        return embedding

    async def _resolve_embedding_config(self, user_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        解析嵌入模型配置

        优先从数据库获取激活的嵌入配置，如果没有则返回 None。

        Args:
            user_id: 用户ID

        Returns:
            嵌入配置字典，包含 provider, model, api_key, base_url 等字段
        """
        if not user_id:
            return None

        try:
            from ..repositories.embedding_config_repository import EmbeddingConfigRepository
            from ..utils.encryption import decrypt_api_key

            repo = EmbeddingConfigRepository(self.session)
            config = await repo.get_active_config(user_id)

            if not config:
                return None

            # 解密 API Key
            decrypted_key = decrypt_api_key(config.api_key, settings.secret_key) if config.api_key else None

            return {
                "provider": config.provider or "openai",
                "model": config.model_name,
                "api_key": decrypted_key,
                "base_url": config.api_base_url,
                "vector_size": config.vector_size,
            }
        except Exception as exc:
            logger.warning("获取嵌入模型配置失败，将使用环境变量配置: %s", exc)
            return None

    def get_embedding_dimension(self, model: Optional[str] = None) -> Optional[int]:
        """获取嵌入向量维度，优先返回缓存结果，其次读取配置。"""
        target_model = model or (
            settings.ollama_embedding_model if settings.embedding_provider == "ollama" else settings.embedding_model
        )
        if target_model in self._embedding_dimensions:
            return self._embedding_dimensions[target_model]
        return settings.embedding_model_vector_size

    def _is_retryable_error(self, exc: Exception) -> bool:
        """
        判断异常是否可重试

        可重试的错误类型：
        - 网络超时：httpx.ReadTimeout, APITimeoutError
        - 连接错误：APIConnectionError, httpx.RemoteProtocolError
        - 限流错误：RateLimitError

        不可重试的错误类型：
        - 认证失败：AuthenticationError (401)
        - 请求无效：BadRequestError (400, 404)
        - 服务内部错误：InternalServerError (500)

        Args:
            exc: 异常对象

        Returns:
            bool: True表示可重试，False表示不可重试
        """
        # 可重试的错误类型
        retryable_types = (
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            APIConnectionError,
            APITimeoutError,
            RateLimitError,  # 限流错误可以重试（配合指数退避）
        )

        return isinstance(exc, retryable_types)

    async def _enforce_daily_limit(self, user_id: int) -> None:
        """桌面版不需要限流，直接跳过"""
        pass

    # 公共方法：供路由层调用
    async def enforce_daily_limit(self, user_id: int) -> None:
        """
        执行每日限额检查（公共接口）

        Args:
            user_id: 用户ID
        """
        await self._enforce_daily_limit(user_id)

    async def resolve_llm_config_cached(
        self,
        user_id: Optional[int],
        skip_daily_limit_check: bool = False
    ) -> Dict[str, Optional[str]]:
        """
        解析LLM配置（公共接口）

        Args:
            user_id: 用户ID
            skip_daily_limit_check: 是否跳过每日限额检查

        Returns:
            LLM配置字典
        """
        return await self._resolve_llm_config(user_id, skip_daily_limit_check)

    async def _get_config_value(self, key: str) -> Optional[str]:
        """从环境变量读取配置"""
        env_key = key.upper().replace(".", "_")
        return os.getenv(env_key)
