"""
嵌入模型配置服务

提供嵌入模型配置的业务逻辑，包括 CRUD 操作和连接测试。
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..exceptions import ResourceNotFoundError, ConflictError, InvalidParameterError
from ..models import EmbeddingConfig
from ..repositories.embedding_config_repository import EmbeddingConfigRepository
from ..schemas.embedding_config import (
    EmbeddingConfigCreate,
    EmbeddingConfigRead,
    EmbeddingConfigUpdate,
    EmbeddingConfigTestResponse,
)
from ..utils.encryption import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)


class EmbeddingConfigService:
    """
    嵌入模型配置服务，支持多配置管理和测试。

    架构说明：
    此Service是配置管理层，与业务逻辑层有本质区别：
    - 配置CRUD操作是独立的原子操作，每个方法内部commit是合理的
    - 路由层与Service 1:1映射，不存在组合调用场景
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = EmbeddingConfigRepository(session)

    def _encrypt_key(self, api_key: Optional[str]) -> Optional[str]:
        """加密API密钥"""
        return encrypt_api_key(api_key, settings.secret_key)

    def _decrypt_key(self, encrypted_key: Optional[str]) -> Optional[str]:
        """解密API密钥"""
        return decrypt_api_key(encrypted_key, settings.secret_key)

    async def list_configs(self, user_id: int) -> list[EmbeddingConfigRead]:
        """获取用户的所有嵌入模型配置列表。"""
        configs = await self.repo.list_by_user(user_id)
        return [EmbeddingConfigRead.from_orm_with_mask(config) for config in configs]

    async def get_config(self, config_id: int, user_id: int) -> EmbeddingConfigRead:
        """获取指定ID的配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("嵌入模型配置", f"ID={config_id}")
        return EmbeddingConfigRead.from_orm_with_mask(config)

    async def get_active_config(self, user_id: int) -> Optional[EmbeddingConfigRead]:
        """获取用户当前激活的配置。"""
        config = await self.repo.get_active_config(user_id)
        return EmbeddingConfigRead.from_orm_with_mask(config) if config else None

    async def get_active_config_raw(self, user_id: int) -> Optional[EmbeddingConfig]:
        """获取用户当前激活的配置（原始ORM对象，用于内部使用）。"""
        return await self.repo.get_active_config(user_id)

    async def create_config(self, user_id: int, payload: EmbeddingConfigCreate) -> EmbeddingConfigRead:
        """创建新的嵌入模型配置。"""
        # 检查配置名称是否重复
        existing = await self.repo.get_by_name(user_id, payload.config_name)
        if existing:
            raise ConflictError(f"配置名称 '{payload.config_name}' 已存在")

        data = payload.model_dump(exclude_unset=True)

        # 处理 URL
        if "api_base_url" in data and data["api_base_url"] is not None:
            data["api_base_url"] = str(data["api_base_url"])

        # 加密API密钥
        if "api_key" in data and data["api_key"]:
            data["api_key"] = self._encrypt_key(data["api_key"])
            logger.debug("API Key已加密存储")

        # 如果用户没有任何配置，则将新配置设为激活
        configs = await self.repo.list_by_user(user_id)
        is_first_config = len(configs) == 0

        instance = EmbeddingConfig(
            user_id=user_id,
            is_active=is_first_config,  # 第一个配置自动激活
            **data,
        )
        await self.repo.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return EmbeddingConfigRead.from_orm_with_mask(instance)

    async def update_config(self, config_id: int, user_id: int, payload: EmbeddingConfigUpdate) -> EmbeddingConfigRead:
        """更新嵌入模型配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("嵌入模型配置", f"ID={config_id}")

        data = payload.model_dump(exclude_unset=True)

        # 检查配置名称是否与其他配置重复
        if "config_name" in data:
            existing = await self.repo.get_by_name(user_id, data["config_name"])
            if existing and existing.id != config_id:
                raise ConflictError(f"配置名称 '{data['config_name']}' 已被其他配置使用")

        if "api_base_url" in data and data["api_base_url"] is not None:
            data["api_base_url"] = str(data["api_base_url"])

        # 加密API密钥
        if "api_key" in data and data["api_key"]:
            data["api_key"] = self._encrypt_key(data["api_key"])
            logger.debug("API Key已加密存储")

        # 如果更新了配置信息，则重置验证状态
        if any(key in data for key in ["api_base_url", "api_key", "model_name", "provider"]):
            data["is_verified"] = False
            data["test_status"] = None
            data["test_message"] = None

        await self.repo.update_fields(config, **data)
        await self.session.commit()
        await self.session.refresh(config)
        return EmbeddingConfigRead.from_orm_with_mask(config)

    async def activate_config(self, config_id: int, user_id: int) -> EmbeddingConfigRead:
        """激活指定配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("嵌入模型配置", f"ID={config_id}")

        await self.repo.activate_config(config_id, user_id)
        await self.session.commit()
        await self.session.refresh(config)
        return EmbeddingConfigRead.from_orm_with_mask(config)

    async def delete_config(self, config_id: int, user_id: int) -> bool:
        """删除嵌入模型配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("嵌入模型配置", f"ID={config_id}")

        # 不允许删除激活的配置
        if config.is_active:
            raise ConflictError("无法删除当前激活的配置，请先切换到其他配置")

        await self.repo.delete(config)
        await self.session.commit()
        return True

    async def test_config(self, config_id: int, user_id: int) -> EmbeddingConfigTestResponse:
        """测试嵌入模型配置是否可用。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("嵌入模型配置", f"ID={config_id}")

        provider = config.provider or "openai"
        model_name = config.model_name

        # 设置默认模型名称
        if not model_name:
            if provider == "ollama":
                model_name = "nomic-embed-text:latest"
            elif provider == "local":
                model_name = "BAAI/bge-base-zh-v1.5"
            else:
                model_name = "text-embedding-3-small"

        try:
            start_time = time.time()

            if provider == "ollama":
                # 测试 Ollama 嵌入
                vector_dimension = await self._test_ollama_embedding(config, model_name)
            elif provider == "local":
                # 测试本地 sentence-transformers 嵌入
                vector_dimension = await self._test_local_embedding(config, model_name)
            else:
                # 测试 OpenAI 兼容 API
                vector_dimension = await self._test_openai_embedding(config, model_name)

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            # 更新配置的测试状态和向量维度
            await self.repo.update_fields(
                config,
                is_verified=True,
                test_status="success",
                test_message="连接测试成功",
                last_test_at=datetime.now(timezone.utc),
                vector_size=vector_dimension,
            )
            await self.session.commit()

            logger.info(
                "用户 %s 的嵌入配置 %s 测试成功，向量维度: %d，响应时间: %.2f ms",
                user_id, config.config_name, vector_dimension, response_time_ms
            )

            return EmbeddingConfigTestResponse(
                success=True,
                message="连接测试成功",
                response_time_ms=round(response_time_ms, 2),
                vector_dimension=vector_dimension,
                model_info=model_name,
            )

        except Exception as exc:
            error_message = str(exc)
            logger.error(
                "用户 %s 的嵌入配置 %s 测试失败: %s",
                user_id, config.config_name, error_message, exc_info=True
            )

            # 更新配置的测试状态
            await self.repo.update_fields(
                config,
                is_verified=False,
                test_status="failed",
                test_message=error_message[:500],
                last_test_at=datetime.now(timezone.utc),
            )
            await self.session.commit()

            return EmbeddingConfigTestResponse(
                success=False,
                message=f"连接测试失败: {error_message}",
            )

    async def _test_openai_embedding(self, config: EmbeddingConfig, model_name: str) -> int:
        """测试 OpenAI 兼容 API 嵌入模型。"""
        from openai import AsyncOpenAI

        # 解密 API Key
        decrypted_key = self._decrypt_key(config.api_key)
        if not decrypted_key or not decrypted_key.strip():
            raise ValueError("配置缺少 API Key")

        api_key = decrypted_key.strip()
        if len(api_key) < 10:
            raise ValueError("API Key 格式不正确（长度过短）")

        base_url = config.api_base_url.strip() if config.api_base_url else None

        # 自动补全 /v1 后缀（OpenAI SDK 需要）
        if base_url:
            base_url = base_url.rstrip("/")
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"

        logger.info(
            "测试 OpenAI 嵌入配置: config_name=%s, base_url=%s, model=%s",
            config.config_name, base_url, model_name
        )

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        # 发送测试请求
        response = await client.embeddings.create(
            input="测试嵌入向量",
            model=model_name,
        )

        if not response.data:
            raise ValueError("嵌入模型未返回有效数据")

        embedding = response.data[0].embedding
        vector_dimension = len(embedding)

        if vector_dimension == 0:
            raise ValueError("嵌入向量维度为0")

        return vector_dimension

    async def _test_ollama_embedding(self, config: EmbeddingConfig, model_name: str) -> int:
        """测试 Ollama 本地嵌入模型。"""
        try:
            from ollama import AsyncClient as OllamaAsyncClient
        except ImportError:
            raise ValueError("未安装 Ollama 依赖，请先安装: pip install ollama")

        base_url = config.api_base_url.strip() if config.api_base_url else "http://localhost:11434"

        logger.info(
            "测试 Ollama 嵌入配置: config_name=%s, base_url=%s, model=%s",
            config.config_name, base_url, model_name
        )

        client = OllamaAsyncClient(host=base_url)

        # 发送测试请求
        response = await client.embeddings(model=model_name, prompt="测试嵌入向量")

        # 提取嵌入向量
        if isinstance(response, dict):
            embedding = response.get("embedding")
        else:
            embedding = getattr(response, "embedding", None)

        if not embedding:
            raise ValueError("Ollama 未返回有效的嵌入向量")

        vector_dimension = len(embedding)

        if vector_dimension == 0:
            raise ValueError("嵌入向量维度为0")

        return vector_dimension

    async def _test_local_embedding(self, config: EmbeddingConfig, model_name: str) -> int:
        """
        测试本地 sentence-transformers 嵌入模型。

        Args:
            config: 嵌入配置对象
            model_name: 模型名称（如 BAAI/bge-small-zh-v1.5）

        Returns:
            向量维度
        """
        import asyncio

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ValueError(
                "未安装 sentence-transformers 依赖，请先安装: pip install sentence-transformers"
            )

        logger.info(
            "测试本地嵌入配置: config_name=%s, model=%s",
            config.config_name, model_name
        )

        # 在线程池中执行模型加载和推理（避免阻塞事件循环）
        loop = asyncio.get_event_loop()

        def _load_and_test():
            # 加载模型（首次可能需要下载）
            logger.info("加载本地嵌入模型: %s（首次加载可能需要下载模型文件）", model_name)
            # 显式指定设备，避免 meta tensor 兼容性问题
            import torch
            if torch.cuda.is_available():
                device = 'cuda'
                logger.info("使用 CUDA GPU: %s", torch.cuda.get_device_name(0))
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = 'mps'
                logger.info("使用 Apple MPS GPU")
            else:
                device = 'cpu'
                logger.info("使用 CPU")
            model = SentenceTransformer(model_name, device=device)

            # 生成测试嵌入
            embedding = model.encode("测试嵌入向量", normalize_embeddings=True)
            return len(embedding)

        try:
            vector_dimension = await loop.run_in_executor(None, _load_and_test)
        except Exception as exc:
            error_msg = str(exc)
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise ValueError(f"模型 '{model_name}' 不存在或无法下载，请检查模型名称")
            raise ValueError(f"本地嵌入模型测试失败: {error_msg}")

        if vector_dimension == 0:
            raise ValueError("嵌入向量维度为0")

        logger.info("本地嵌入模型测试成功: model=%s, dimension=%d", model_name, vector_dimension)
        return vector_dimension

    # ------------------------------------------------------------------
    # 导入导出功能
    # ------------------------------------------------------------------

    async def export_config(self, config_id: int, user_id: int) -> dict:
        """
        导出单个嵌入配置为JSON格式。

        Args:
            config_id: 配置ID
            user_id: 用户ID（权限验证）

        Returns:
            包含配置信息的字典
        """
        from datetime import datetime, timezone
        from ..schemas.embedding_config import EmbeddingConfigExport, EmbeddingConfigExportData

        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("嵌入配置", f"ID={config_id}")

        export_data = EmbeddingConfigExportData(
            version="1.0",
            export_time=datetime.now(timezone.utc).isoformat(),
            export_type="embedding",
            configs=[
                EmbeddingConfigExport(
                    config_name=config.config_name,
                    provider=config.provider,
                    api_base_url=config.api_base_url,
                    api_key=self._decrypt_key(config.api_key),
                    model_name=config.model_name,
                    vector_size=config.vector_size,
                )
            ],
        )

        return export_data.model_dump()

    async def export_all_configs(self, user_id: int) -> dict:
        """
        导出用户的所有嵌入配置为JSON格式。

        Args:
            user_id: 用户ID

        Returns:
            包含所有配置的字典
        """
        from datetime import datetime, timezone
        from ..schemas.embedding_config import EmbeddingConfigExport, EmbeddingConfigExportData

        configs = await self.repo.list_by_user(user_id)
        if not configs:
            raise ResourceNotFoundError("嵌入配置", f"用户ID={user_id}无配置可导出")

        export_data = EmbeddingConfigExportData(
            version="1.0",
            export_time=datetime.now(timezone.utc).isoformat(),
            export_type="embedding",
            configs=[
                EmbeddingConfigExport(
                    config_name=config.config_name,
                    provider=config.provider,
                    api_base_url=config.api_base_url,
                    api_key=self._decrypt_key(config.api_key),
                    model_name=config.model_name,
                    vector_size=config.vector_size,
                )
                for config in configs
            ],
        )

        return export_data.model_dump()

    async def import_configs(self, user_id: int, import_data: dict) -> dict:
        """
        导入嵌入配置。

        Args:
            user_id: 用户ID
            import_data: 导入的配置数据

        Returns:
            导入结果统计
        """
        from ..schemas.embedding_config import EmbeddingConfigExportData, EmbeddingConfigImportResult

        # 验证导入数据格式
        try:
            data = EmbeddingConfigExportData(**import_data)
        except Exception as exc:
            raise InvalidParameterError(
                f"导入数据格式错误: {str(exc)}",
                parameter="import_data"
            )

        # 检查版本兼容性
        if data.version != "1.0":
            raise InvalidParameterError(
                f"不支持的导出格式版本: {data.version}，当前仅支持 1.0",
                parameter="version"
            )

        # 获取用户现有的配置名称
        existing_configs = await self.repo.list_by_user(user_id)
        existing_names = {config.config_name for config in existing_configs}

        imported_count = 0
        skipped_count = 0
        failed_count = 0
        details = []

        for config_data in data.configs:
            try:
                # 处理重名
                original_name = config_data.config_name
                config_name = original_name
                suffix = 1

                while config_name in existing_names:
                    config_name = f"{original_name} ({suffix})"
                    suffix += 1

                if config_name != original_name:
                    details.append(
                        f"配置 '{original_name}' 已重命名为 '{config_name}'（避免重名）"
                    )

                # 创建新配置
                new_config = EmbeddingConfig(
                    user_id=user_id,
                    config_name=config_name,
                    provider=config_data.provider,
                    api_base_url=config_data.api_base_url,
                    api_key=self._encrypt_key(config_data.api_key),
                    model_name=config_data.model_name,
                    vector_size=config_data.vector_size,
                    is_active=False,
                    is_verified=False,
                )

                await self.repo.add(new_config)
                existing_names.add(config_name)
                imported_count += 1
                details.append(f"成功导入配置 '{config_name}'")

            except Exception as exc:
                failed_count += 1
                details.append(
                    f"导入配置 '{config_data.config_name}' 失败: {str(exc)}"
                )
                logger.error(
                    "导入嵌入配置失败: user_id=%s, config_name=%s, error=%s",
                    user_id,
                    config_data.config_name,
                    str(exc),
                    exc_info=True,
                )

        await self.session.commit()

        return EmbeddingConfigImportResult(
            success=imported_count > 0,
            message=f"导入完成：成功 {imported_count} 个，失败 {failed_count} 个",
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            details=details,
        ).model_dump()
