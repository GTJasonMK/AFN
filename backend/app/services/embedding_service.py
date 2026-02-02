"""
嵌入向量服务

负责文本嵌入向量的生成，支持 OpenAI 兼容 API、本地 Ollama 和本地 sentence-transformers。
从 LLMService 拆分出来，遵循单一职责原则。
"""

import asyncio
import logging
import threading
from enum import Enum
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


def _get_package_version(package_name: str) -> Optional[str]:
    """获取已安装包的版本号（用于问题诊断）"""
    try:
        from importlib.metadata import version

        return version(package_name)
    except Exception:
        return None


def _is_meta_tensor_error(exc: Exception) -> bool:
    """
    判断是否为“meta tensor”相关的兼容性错误。

    典型表现：
    - Cannot copy out of meta tensor; no data!
    - Please use torch.nn.Module.to_empty() instead of torch.nn.Module.to()
    """
    message = str(exc) or ""
    message_lower = message.lower()
    return (
        "meta tensor" in message_lower
        or "cannot copy out of meta tensor" in message_lower
        or "to_empty" in message_lower
    )


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


def _resolve_hf_hub_snapshot(hub_cache_dir: str) -> Optional[str]:
    """
    解析 HuggingFace Hub 缓存目录，找到实际的模型 snapshot 路径

    HF Hub 缓存结构:
    models--BAAI--bge-base-zh-v1.5/
    ├── blobs/
    ├── refs/
    │   └── main  (内容是 commit hash)
    └── snapshots/
        └── {commit_hash}/
            ├── config.json
            ├── pytorch_model.bin
            └── ...

    Args:
        hub_cache_dir: HF Hub 缓存目录路径

    Returns:
        snapshot 目录路径，如果未找到返回 None
    """
    import os

    snapshots_dir = os.path.join(hub_cache_dir, "snapshots")
    if not os.path.exists(snapshots_dir):
        return None

    # 尝试从 refs/main 读取当前 commit hash
    refs_main = os.path.join(hub_cache_dir, "refs", "main")
    if os.path.exists(refs_main):
        try:
            with open(refs_main, "r") as f:
                commit_hash = f.read().strip()
            snapshot_path = os.path.join(snapshots_dir, commit_hash)
            if os.path.exists(snapshot_path):
                return snapshot_path
        except Exception:
            pass

    # 如果 refs/main 不存在，取 snapshots 目录下的第一个子目录
    try:
        subdirs = [d for d in os.listdir(snapshots_dir)
                   if os.path.isdir(os.path.join(snapshots_dir, d))]
        if subdirs:
            return os.path.join(snapshots_dir, subdirs[0])
    except Exception:
        pass

    return None


def _find_local_model_path(model_name: str) -> Optional[str]:
    """
    查找本地模型路径

    Args:
        model_name: 模型名称（如 BAAI/bge-base-zh-v1.5）

    Returns:
        本地模型路径，如果未找到返回 None
    """
    import os
    from pathlib import Path

    # 优先检查 SENTENCE_TRANSFORMERS_HOME；若未设置，则回退到项目默认目录 storage/models（与 run_app.py 保持一致）
    st_home = os.environ.get("SENTENCE_TRANSFORMERS_HOME")
    fallback_models_dir = str((settings.storage_dir / "models").resolve())

    st_home_candidates = [p for p in [st_home, fallback_models_dir] if p]
    for candidate_home in st_home_candidates:
        # 格式1: {ST_HOME}/{model_name.replace('/', '_')}
        st_cache_dir = os.path.join(candidate_home, model_name.replace("/", "_"))
        if os.path.exists(st_cache_dir):
            # 检查是否是 HF Hub 格式（有 snapshots 子目录）
            snapshot_path = _resolve_hf_hub_snapshot(st_cache_dir)
            if snapshot_path:
                logger.debug("模型在 ST_HOME (HF Hub格式): %s", snapshot_path)
                return snapshot_path
            # 否则检查是否直接是模型目录（有 config.json）
            if os.path.exists(os.path.join(st_cache_dir, "config.json")):
                logger.debug("模型在 ST_HOME (直接格式): %s", st_cache_dir)
                return st_cache_dir

            # 部分 SentenceTransformer 模型根目录可能没有 config.json，但包含 modules.json 等文件
            if os.path.exists(os.path.join(st_cache_dir, "modules.json")):
                logger.debug("模型在 ST_HOME (SentenceTransformer格式): %s", st_cache_dir)
                return st_cache_dir

        # 格式2: {ST_HOME}/{model_name}
        # 注意：model_name 可能包含 "/"，在 Windows 下会被当作子目录
        st_cache_dir2 = os.path.join(candidate_home, model_name)
        if os.path.exists(st_cache_dir2):
            snapshot_path = _resolve_hf_hub_snapshot(st_cache_dir2)
            if snapshot_path:
                logger.debug("模型在 ST_HOME (HF Hub格式): %s", snapshot_path)
                return snapshot_path
            if os.path.exists(os.path.join(st_cache_dir2, "config.json")):
                logger.debug("模型在 ST_HOME (直接格式): %s", st_cache_dir2)
                return st_cache_dir2
            if os.path.exists(os.path.join(st_cache_dir2, "modules.json")):
                logger.debug("模型在 ST_HOME (SentenceTransformer格式): %s", st_cache_dir2)
                return st_cache_dir2

    # 检查 HF_HOME（HuggingFace Hub 使用的目录）
    hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    model_cache_dir = os.path.join(hf_home, "hub", f"models--{model_name.replace('/', '--')}")
    if os.path.exists(model_cache_dir):
        snapshot_path = _resolve_hf_hub_snapshot(model_cache_dir)
        if snapshot_path:
            logger.debug("模型在 HF_HOME (HF Hub格式): %s", snapshot_path)
            return snapshot_path

    logger.debug(
        "模型未找到，已检查目录: SENTENCE_TRANSFORMERS_HOME=%s, fallback_models_dir=%s, HF_HOME=%s",
        st_home,
        fallback_models_dir,
        hf_home,
    )
    return None


def _load_sentence_transformer(model_name: str, device: str) -> Any:
    """
    加载 SentenceTransformer 模型（仅从本地加载）

    Args:
        model_name: 模型名称
        device: 设备类型

    Returns:
        加载的模型实例

    Raises:
        FileNotFoundError: 模型不在本地缓存目录
    """
    import os

    # 查找本地模型路径
    local_path = _find_local_model_path(model_name)

    if not local_path:
        st_home = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "")
        hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        fallback_models_dir = str((settings.storage_dir / "models").resolve())
        expected_paths = []
        if st_home:
            expected_paths.append(os.path.join(st_home, model_name.replace("/", "_")))
        expected_paths.append(os.path.join(fallback_models_dir, model_name.replace("/", "_")))
        expected_paths.append(os.path.join(hf_home, "hub", f"models--{model_name.replace('/', '--')}"))
        raise FileNotFoundError(
            f"本地嵌入模型不存在: {model_name}\n"
            f"请将模型下载到以下任一目录（任选其一即可）:\n"
            + "\n".join(f"- {p}" for p in expected_paths)
        )

    # 使用本地路径直接加载（不会触发网络请求）
    logger.info("从本地路径加载模型: %s", local_path)
    old_offline = os.environ.get("HF_HUB_OFFLINE")
    old_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        import inspect

        def _try_load(*, load_device: str, safer_model_kwargs: bool) -> Any:
            """
            尝试加载 SentenceTransformer。

            - load_device: 传给 SentenceTransformer 的 device 参数（若支持）。
            - safer_model_kwargs: 若 SentenceTransformer 支持 model_kwargs，则显式关闭
              transformers 的 low_cpu_mem_usage / device_map，规避 meta tensor 兼容性问题。
            """
            kwargs: Dict[str, Any] = {}

            # 兼容不同版本 sentence-transformers：按 __init__ 参数动态传参
            try:
                init_params = inspect.signature(_SentenceTransformer.__init__).parameters
            except Exception:
                init_params = {}

            if "device" in init_params:
                kwargs["device"] = load_device

            # 双保险：即使设置 HF_HUB_OFFLINE，也尽量显式 local_files_only
            if "local_files_only" in init_params:
                kwargs["local_files_only"] = True

            if safer_model_kwargs and "model_kwargs" in init_params:
                kwargs["model_kwargs"] = {
                    # 避免 init_empty_weights(meta) + .to(device) 的组合触发报错
                    "low_cpu_mem_usage": False,
                    # 禁用 accelerate 分片/dispatch，避免 device_map 触发 meta 行为
                    "device_map": None,
                }

            # 直接传入本地路径，而不是模型名称
            return _SentenceTransformer(local_path, **kwargs)

        # 1) 优先按目标 device 直接加载（保持既有行为）
        try:
            model = _try_load(load_device=device, safer_model_kwargs=False)
            logger.info("本地模型加载成功: %s", local_path)
            return model
        except Exception as exc:
            if not _is_meta_tensor_error(exc):
                raise

            # 2) 兼容性回退：CPU 加载 + 再迁移到目标设备
            torch_version = _get_package_version("torch")
            st_version = _get_package_version("sentence-transformers")
            transformers_version = _get_package_version("transformers")
            accelerate_version = _get_package_version("accelerate")
            logger.warning(
                "加载本地嵌入模型触发 meta tensor 兼容性问题，将尝试回退策略: "
                "model=%s device=%s torch=%s sentence-transformers=%s transformers=%s accelerate=%s error=%s",
                model_name,
                device,
                torch_version,
                st_version,
                transformers_version,
                accelerate_version,
                exc,
            )

            # 2.1) 先尝试最保守的“CPU + safer model_kwargs”
            model = _try_load(load_device="cpu", safer_model_kwargs=True)

            # 2.2) 再迁移到目标设备（失败则保持 CPU，保证功能可用）
            if device != "cpu":
                try:
                    model.to(device)
                    # 部分版本 sentence-transformers 会缓存 target_device，尽量同步
                    if hasattr(model, "_target_device"):
                        try:
                            import torch

                            model._target_device = torch.device(device)
                        except Exception:
                            model._target_device = device
                except Exception as move_exc:
                    logger.warning(
                        "本地模型已在 CPU 加载成功，但迁移到 %s 失败，将保持 CPU: error=%s",
                        device,
                        move_exc,
                    )

            logger.info("本地模型加载成功（回退策略）: %s", local_path)
            return model
    finally:
        if old_offline is None:
            os.environ.pop("HF_HUB_OFFLINE", None)
        else:
            os.environ["HF_HUB_OFFLINE"] = old_offline
        if old_transformers_offline is None:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        else:
            os.environ["TRANSFORMERS_OFFLINE"] = old_transformers_offline


class PreloadState(Enum):
    """预加载状态枚举"""
    NOT_STARTED = "not_started"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


class EmbeddingPreloader:
    """
    嵌入模型预加载器（单例模式）

    在应用启动时异步预加载本地嵌入模型，避免首次使用时的长时间等待。

    使用方式：
        # 启动时触发预加载（非阻塞）
        await EmbeddingPreloader.instance().start_preload("BAAI/bge-base-zh-v1.5")

        # 使用时等待预加载完成
        await EmbeddingPreloader.instance().wait_until_ready()
    """

    _instance: Optional["EmbeddingPreloader"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._state = PreloadState.NOT_STARTED
        self._model_name: Optional[str] = None
        self._error: Optional[str] = None
        self._ready_event = asyncio.Event()
        self._preload_task: Optional[asyncio.Task] = None

    @classmethod
    def instance(cls) -> "EmbeddingPreloader":
        """获取单例实例"""
        return cls()

    @property
    def state(self) -> PreloadState:
        """获取当前预加载状态"""
        return self._state

    @property
    def is_ready(self) -> bool:
        """模型是否已加载完成"""
        return self._state == PreloadState.LOADED

    @property
    def is_loading(self) -> bool:
        """是否正在加载中"""
        return self._state == PreloadState.LOADING

    async def start_preload(self, model_name: str) -> None:
        """
        启动异步预加载（非阻塞）

        Args:
            model_name: 要预加载的模型名称（如 BAAI/bge-base-zh-v1.5）
        """
        if self._state in (PreloadState.LOADING, PreloadState.LOADED):
            logger.debug("嵌入模型预加载已在进行中或已完成，跳过")
            return

        if not _check_sentence_transformers():
            logger.warning("sentence-transformers 未安装，跳过预加载")
            self._state = PreloadState.FAILED
            self._error = "sentence-transformers 未安装"
            self._ready_event.set()  # 标记完成（虽然失败）
            return

        self._model_name = model_name
        self._state = PreloadState.LOADING
        logger.info("开始异步预加载嵌入模型: %s", model_name)

        # 在后台任务中加载模型
        self._preload_task = asyncio.create_task(self._do_preload())

    async def _do_preload(self) -> None:
        """执行实际的模型加载（在后台运行）"""
        try:
            loop = asyncio.get_event_loop()

            def _load_model():
                global _local_model_cache
                if self._model_name in _local_model_cache:
                    logger.info("嵌入模型已在缓存中: %s", self._model_name)
                    return True

                logger.info("预加载嵌入模型: %s", self._model_name)
                device = _get_torch_device()
                logger.info("预加载使用设备: %s", device)

                # 使用智能加载函数（优先离线模式）
                model = _load_sentence_transformer(self._model_name, device)
                _local_model_cache[self._model_name] = model
                logger.info("嵌入模型预加载成功: %s", self._model_name)
                return True

            await loop.run_in_executor(None, _load_model)
            self._state = PreloadState.LOADED
            logger.info("嵌入模型预加载完成: %s", self._model_name)

        except Exception as exc:
            self._state = PreloadState.FAILED
            self._error = str(exc)
            logger.error("嵌入模型预加载失败: %s, error=%s", self._model_name, exc)

        finally:
            self._ready_event.set()  # 通知等待者

    async def wait_until_ready(self, timeout: Optional[float] = None) -> bool:
        """
        等待预加载完成

        Args:
            timeout: 最大等待时间（秒），None 表示无限等待

        Returns:
            True 如果加载成功，False 如果加载失败或超时
        """
        if self._state == PreloadState.NOT_STARTED:
            # 未启动预加载，直接返回
            return False

        if self._state == PreloadState.LOADED:
            return True

        if self._state == PreloadState.FAILED:
            return False

        # 等待加载完成
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            return self._state == PreloadState.LOADED
        except asyncio.TimeoutError:
            logger.warning("等待嵌入模型预加载超时: %s", self._model_name)
            return False

    def get_cached_model(self, model_name: str) -> Optional[Any]:
        """
        获取已缓存的模型

        Args:
            model_name: 模型名称

        Returns:
            缓存的模型实例，如果未缓存则返回 None
        """
        return _local_model_cache.get(model_name)


# 全局预加载器实例（方便外部访问）
embedding_preloader = EmbeddingPreloader.instance()


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
        provider = (embedding_config.get("provider") or "openai").lower()
        target_model = (model or embedding_config.get("model") or "").strip()
        if not target_model:
            # 与配置测试逻辑保持一致：模型名缺省时使用默认值
            if provider == "ollama":
                target_model = "nomic-embed-text:latest"
            elif provider == "local":
                target_model = "BAAI/bge-base-zh-v1.5"
            else:
                target_model = "text-embedding-3-small"
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

        如果预加载器正在加载模型，会等待其完成。
        如果模型已预加载，直接使用缓存的模型。

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

        # 如果预加载器正在加载，等待其完成（最多等待120秒）
        preloader = embedding_preloader
        if preloader.is_loading:
            logger.info("等待嵌入模型预加载完成: %s", target_model)
            await preloader.wait_until_ready(timeout=120.0)

        # 从缓存获取或加载模型（在线程池中执行以避免阻塞）
        loop = asyncio.get_event_loop()

        def _load_and_encode():
            global _local_model_cache

            if target_model not in _local_model_cache:
                logger.info("加载本地嵌入模型: %s", target_model)
                try:
                    device = _get_torch_device()
                    logger.info("使用设备: %s", device)
                    # 使用智能加载函数（优先离线模式）
                    model = _load_sentence_transformer(target_model, device)
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
