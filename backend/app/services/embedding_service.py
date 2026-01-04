"""
嵌入向量服务

负责文本嵌入向量的生成，支持 OpenAI 兼容 API、本地 Ollama 和本地 sentence-transformers。
从 LLMService 拆分出来，遵循单一职责原则。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..exceptions import LLMConfigurationError, InvalidParameterError
from ..repositories.embedding_config_repository import EmbeddingConfigRepository
from ..utils.encryption import decrypt_api_key

logger = logging.getLogger(__name__)

try:  # pragma: no cover - 运行环境未安装时兼容
    from ollama import AsyncClient as OllamaAsyncClient
except ImportError:  # pragma: no cover - Ollama 为可选依赖
    OllamaAsyncClient = None

# 本地嵌入模型支持（延迟导入，避免启动时加载 PyTorch）
# sentence-transformers 依赖 PyTorch，首次导入需要 10-60 秒
_sentence_transformers_checked = False
_sentence_transformers_available = False
_SentenceTransformer = None

# 本地模型缓存（避免每次请求都重新加载模型）
_local_model_cache: Dict[str, Any] = {}


def _check_sentence_transformers():
    """延迟检查 sentence-transformers 是否可用"""
    global _sentence_transformers_checked, _sentence_transformers_available, _SentenceTransformer
    if _sentence_transformers_checked:
        return _sentence_transformers_available

    try:
        from sentence_transformers import SentenceTransformer
        _SentenceTransformer = SentenceTransformer
        _sentence_transformers_available = True
        logger.info("sentence-transformers 加载成功")
    except ImportError:
        _sentence_transformers_available = False
        logger.debug("sentence-transformers 未安装")

    _sentence_transformers_checked = True
    return _sentence_transformers_available


def _get_torch_device() -> str:
    """获取最佳可用设备（GPU优先）"""
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            logger.info("检测到 CUDA GPU: %s", device_name)
            return 'cuda'
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            # Apple Silicon GPU
            logger.info("检测到 Apple MPS GPU")
            return 'mps'
    except Exception as e:
        logger.debug("GPU 检测失败: %s", e)
    return 'cpu'


class EmbeddingService:
    """嵌入向量服务，负责文本向量化"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._embedding_repo = EmbeddingConfigRepository(session)
        self._dimension_cache: Dict[str, int] = {}

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
        embedding_config = await self._resolve_config(user_id)

        if not embedding_config:
            logger.error("未配置嵌入模型，请在设置页面添加并激活嵌入模型配置")
            raise LLMConfigurationError(
                "未配置嵌入模型。请在「设置 - 嵌入模型」中添加并激活一个嵌入模型配置。"
            )

        # 使用数据库配置
        provider = embedding_config.get("provider", "openai")
        target_model = model or embedding_config.get("model")
        api_key = embedding_config.get("api_key")
        base_url = embedding_config.get("base_url")

        # 重试逻辑
        last_error: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                if provider == "ollama":
                    embedding = await self._get_ollama_embedding(
                        text=text,
                        target_model=target_model,
                        base_url=base_url,
                    )
                elif provider == "local":
                    embedding = await self._get_local_embedding(
                        text=text,
                        target_model=target_model,
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
                    if attempt > 0:
                        logger.info(
                            "嵌入请求在第 %d 次重试后成功: model=%s",
                            attempt,
                            target_model,
                        )
                    return embedding
                else:
                    return []

            except LLMConfigurationError:
                raise
            except Exception as exc:
                last_error = exc
                if not self._is_retryable_error(exc):
                    logger.error(
                        "嵌入请求失败（不可重试）: model=%s error=%s",
                        target_model,
                        exc,
                        exc_info=True,
                    )
                    return []

                if attempt < max_retries:
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
                    logger.error(
                        "嵌入请求失败，已达到最大重试次数 (%d): model=%s error=%s",
                        max_retries,
                        target_model,
                        exc,
                    )

        return []

    async def _get_ollama_embedding(
        self,
        text: str,
        target_model: str,
        base_url: Optional[str],
    ) -> List[float]:
        """调用 Ollama 生成嵌入向量"""
        if OllamaAsyncClient is None:
            logger.error("未安装 ollama 依赖，无法调用本地嵌入模型。")
            raise LLMConfigurationError("缺少 Ollama 依赖，请先安装 ollama 包")

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
            self._dimension_cache[target_model] = dimension

        return embedding

    async def _get_local_embedding(
        self,
        text: str,
        target_model: str,
    ) -> List[float]:
        """
        使用 sentence-transformers 在本地生成嵌入向量

        Args:
            text: 要嵌入的文本
            target_model: 模型名称（如 BAAI/bge-small-zh-v1.5）

        Returns:
            嵌入向量列表
        """
        if not _check_sentence_transformers():
            logger.error("未安装 sentence-transformers 依赖，无法使用本地嵌入模型")
            raise LLMConfigurationError(
                "缺少 sentence-transformers 依赖，请先安装: pip install sentence-transformers"
            )

        # 使用默认模型（如果未指定）
        if not target_model:
            target_model = "BAAI/bge-base-zh-v1.5"

        # 从缓存获取或加载模型（在线程池中执行以避免阻塞）
        loop = asyncio.get_event_loop()

        def _load_and_encode():
            global _local_model_cache

            if target_model not in _local_model_cache:
                logger.info("首次加载本地嵌入模型: %s（可能需要下载）", target_model)
                try:
                    # 显式指定设备，避免 meta tensor 兼容性问题
                    device = _get_torch_device()
                    logger.info("使用设备: %s", device)
                    model = _SentenceTransformer(target_model, device=device)
                    _local_model_cache[target_model] = model
                    logger.info("本地嵌入模型加载成功: %s", target_model)
                except Exception as exc:
                    logger.error("加载本地嵌入模型失败: %s, error=%s", target_model, exc)
                    raise

            model = _local_model_cache[target_model]
            # 生成嵌入向量
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()

        try:
            embedding = await loop.run_in_executor(None, _load_and_encode)
        except Exception as exc:
            logger.error("本地嵌入生成失败: model=%s, error=%s", target_model, exc)
            raise LLMConfigurationError(f"本地嵌入模型调用失败: {str(exc)}") from exc

        if not embedding:
            logger.warning("本地模型返回空向量: model=%s", target_model)
            return []

        # 缓存向量维度
        dimension = len(embedding)
        if dimension:
            self._dimension_cache[target_model] = dimension

        logger.debug("本地嵌入生成成功: model=%s, dimension=%d", target_model, dimension)
        return embedding

    async def _get_openai_embedding(
        self,
        text: str,
        target_model: str,
        api_key: Optional[str],
        base_url: Optional[str],
        user_id: Optional[int],
    ) -> List[float]:
        """调用 OpenAI 兼容 API 生成嵌入向量"""
        if not api_key:
            raise LLMConfigurationError(
                "嵌入模型配置缺少 API Key。请在「设置 - 嵌入模型」中检查配置。"
            )

        # 自动补全 /v1 后缀（OpenAI SDK 需要）
        if base_url:
            base_url = base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"

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
            self._dimension_cache[target_model] = dimension

        return embedding

    async def _resolve_config(self, user_id: Optional[int]) -> Optional[Dict[str, Any]]:
        """
        解析嵌入模型配置

        Args:
            user_id: 用户ID

        Returns:
            嵌入配置字典，包含 provider, model, api_key, base_url 等字段
        """
        if not user_id:
            return None

        try:
            config = await self._embedding_repo.get_active_config(user_id)

            if not config:
                return None

            decrypted_key = decrypt_api_key(config.api_key, settings.secret_key) if config.api_key else None

            return {
                "provider": config.provider or "openai",
                "model": config.model_name,
                "api_key": decrypted_key,
                "base_url": config.api_base_url,
                "vector_size": config.vector_size,
            }
        except Exception as exc:
            logger.warning("获取嵌入模型配置失败: %s", exc)
            return None

    def get_dimension(self, model: Optional[str] = None) -> Optional[int]:
        """获取嵌入向量维度，优先返回缓存结果"""
        target_model = model or (
            settings.ollama_embedding_model if settings.embedding_provider == "ollama" else settings.embedding_model
        )
        if target_model in self._dimension_cache:
            return self._dimension_cache[target_model]
        return settings.embedding_model_vector_size

    def _is_retryable_error(self, exc: Exception) -> bool:
        """判断异常是否可重试"""
        retryable_types = (
            httpx.ReadTimeout,
            httpx.RemoteProtocolError,
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
        )
        return isinstance(exc, retryable_types)
