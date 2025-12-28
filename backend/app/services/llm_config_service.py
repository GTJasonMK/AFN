import logging
import time
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..exceptions import ResourceNotFoundError, ConflictError, InvalidParameterError
from ..models import LLMConfig
from ..repositories.llm_config_repository import LLMConfigRepository
from ..schemas.llm_config import LLMConfigCreate, LLMConfigRead, LLMConfigUpdate, LLMConfigTestResponse
from ..utils.llm_tool import ChatMessage, ContentCollectMode, LLMClient
from ..utils.encryption import encrypt_api_key, decrypt_api_key

logger = logging.getLogger(__name__)

# 延迟导入缓存，避免循环依赖
_config_cache = None


async def _invalidate_llm_config_cache(user_id: int) -> None:
    """使LLM配置缓存失效（延迟导入避免循环依赖）

    当用户更新、激活、删除或导入LLM配置时调用此函数，
    确保下次LLM调用使用最新的配置。
    """
    global _config_cache
    if _config_cache is None:
        from .llm_service import _config_cache as cache
        _config_cache = cache
    await _config_cache.invalidate(user_id)
    logger.debug("LLM配置缓存已失效: user_id=%s", user_id)


class LLMConfigService:
    """
    用户自定义 LLM 配置服务，支持多配置管理和测试。

    架构说明：
    此Service是配置管理层，与业务逻辑层（NovelService等）有本质区别：
    - 配置CRUD操作是独立的原子操作，每个方法内部commit是合理的
    - 路由层与Service 1:1映射，不存在组合调用场景
    - 符合配置管理的常见模式，保持代码简洁性
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LLMConfigRepository(session)

    def _encrypt_key(self, api_key: Optional[str]) -> Optional[str]:
        """加密API密钥"""
        return encrypt_api_key(api_key, settings.secret_key)

    def _decrypt_key(self, encrypted_key: Optional[str]) -> Optional[str]:
        """解密API密钥"""
        return decrypt_api_key(encrypted_key, settings.secret_key)

    async def list_configs(self, user_id: int) -> list[LLMConfigRead]:
        """获取用户的所有LLM配置列表。"""
        configs = await self.repo.list_by_user(user_id)
        return [LLMConfigRead.from_orm_with_mask(config) for config in configs]

    async def get_config(self, config_id: int, user_id: int) -> LLMConfigRead:
        """获取指定ID的配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("LLM配置", f"ID={config_id}")
        return LLMConfigRead.from_orm_with_mask(config)

    async def get_active_config(self, user_id: int) -> Optional[LLMConfigRead]:
        """获取用户当前激活的配置。"""
        config = await self.repo.get_active_config(user_id)
        return LLMConfigRead.from_orm_with_mask(config) if config else None

    async def create_config(self, user_id: int, payload: LLMConfigCreate) -> LLMConfigRead:
        """创建新的LLM配置。"""
        # 检查配置名称是否重复
        existing = await self.repo.get_by_name(user_id, payload.config_name)
        if existing:
            raise ConflictError(f"配置名称 '{payload.config_name}' 已存在")

        data = payload.model_dump(exclude_unset=True)
        if "llm_provider_url" in data and data["llm_provider_url"] is not None:
            data["llm_provider_url"] = str(data["llm_provider_url"])

        # 加密API密钥
        if "llm_provider_api_key" in data and data["llm_provider_api_key"]:
            data["llm_provider_api_key"] = self._encrypt_key(data["llm_provider_api_key"])
            logger.debug("API Key已加密存储")

        # 如果用户没有任何配置，则将新配置设为激活
        configs = await self.repo.list_by_user(user_id)
        is_first_config = len(configs) == 0

        instance = LLMConfig(
            user_id=user_id,
            is_active=is_first_config,  # 第一个配置自动激活
            **data,
        )
        await self.repo.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return LLMConfigRead.from_orm_with_mask(instance)

    async def update_config(self, config_id: int, user_id: int, payload: LLMConfigUpdate) -> LLMConfigRead:
        """更新LLM配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("LLM配置", f"ID={config_id}")

        data = payload.model_dump(exclude_unset=True)

        # 检查配置名称是否与其他配置重复
        if "config_name" in data:
            existing = await self.repo.get_by_name(user_id, data["config_name"])
            if existing and existing.id != config_id:
                raise ConflictError(f"配置名称 '{data['config_name']}' 已被其他配置使用")

        if "llm_provider_url" in data and data["llm_provider_url"] is not None:
            data["llm_provider_url"] = str(data["llm_provider_url"])

        # 加密API密钥
        if "llm_provider_api_key" in data and data["llm_provider_api_key"]:
            data["llm_provider_api_key"] = self._encrypt_key(data["llm_provider_api_key"])
            logger.debug("API Key已加密存储")

        # 如果更新了配置信息，则重置验证状态
        if any(key in data for key in ["llm_provider_url", "llm_provider_api_key", "llm_provider_model"]):
            data["is_verified"] = False
            data["test_status"] = None
            data["test_message"] = None

        await self.repo.update_fields(config, **data)
        await self.session.commit()
        # 更新配置后使缓存失效，确保下次LLM调用使用新配置
        if config.is_active:
            await _invalidate_llm_config_cache(user_id)
        await self.session.refresh(config)
        return LLMConfigRead.from_orm_with_mask(config)

    async def activate_config(self, config_id: int, user_id: int) -> LLMConfigRead:
        """激活指定配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("LLM配置", f"ID={config_id}")

        await self.repo.activate_config(config_id, user_id)
        await self.session.commit()
        # 切换激活配置后使缓存失效
        await _invalidate_llm_config_cache(user_id)
        await self.session.refresh(config)
        return LLMConfigRead.from_orm_with_mask(config)

    async def delete_config(self, config_id: int, user_id: int) -> bool:
        """删除LLM配置。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("LLM配置", f"ID={config_id}")

        # 不允许删除激活的配置
        if config.is_active:
            raise ConflictError("无法删除当前激活的配置，请先切换到其他配置")

        await self.repo.delete(config)
        await self.session.commit()
        # 删除配置后使缓存失效（防止缓存中引用已删除配置）
        await _invalidate_llm_config_cache(user_id)
        return True

    async def test_config(self, config_id: int, user_id: int) -> LLMConfigTestResponse:
        """测试LLM配置是否可用。"""
        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("LLM配置", f"ID={config_id}")

        # 解密API密钥用于测试
        decrypted_key = self._decrypt_key(config.llm_provider_api_key)

        # 检查必需字段
        if not decrypted_key or not decrypted_key.strip():
            return LLMConfigTestResponse(
                success=False,
                message="配置缺少 API Key",
            )

        # 验证 API Key 格式（基本检查）
        api_key = decrypted_key.strip()
        if len(api_key) < 10:
            return LLMConfigTestResponse(
                success=False,
                message="API Key 格式不正确（长度过短）",
            )

        # 使用配置进行测试调用
        try:
            start_time = time.time()

            # 准备测试配置
            test_config = {
                "api_key": api_key,
                "base_url": config.llm_provider_url.strip() if config.llm_provider_url and config.llm_provider_url.strip() else None,
                "model": config.llm_provider_model.strip() if config.llm_provider_model and config.llm_provider_model.strip() else "gpt-3.5-turbo",
            }

            logger.info("测试配置 %s: api_key长度=%d, base_url=%s, model=%s",
                       config.config_name, len(api_key), test_config["base_url"], test_config["model"])

            # 使用工厂方法创建客户端
            client = LLMClient.create_from_config(
                test_config,
                strict_mode=True,  # 启用严格模式，不回退到环境变量
                simulate_browser=True,  # 启用浏览器模拟，绕过 Cloudflare 检测
            )

            # 发送简单的测试请求，并使用统一的流式收集方法
            messages = [ChatMessage(role="user", content="测试连接，请回复'连接成功'")]

            logger.info("开始流式请求测试: base_url=%s, model=%s", test_config["base_url"], test_config["model"])

            # 使用 WITH_REASONING 模式，兼容 DeepSeek R1 等模型
            result = await client.stream_and_collect(
                messages=messages,
                model=test_config["model"],
                temperature=0.1,
                max_tokens=50,
                timeout=30,
                collect_mode=ContentCollectMode.WITH_REASONING,
                log_chunks=True,  # 记录前3个chunk用于调试
            )

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000

            logger.info("流式请求完成: chunk_count=%d, content_length=%d, reasoning_length=%d",
                       result.chunk_count, len(result.content), len(result.reasoning))

            # 检查是否收到了有效响应（content或reasoning任一非空即可）
            total_content = result.content.strip() + result.reasoning.strip()
            if result.chunk_count == 0 or not total_content:
                error_msg = f"未收到有效响应 (chunks={result.chunk_count}, content_len={len(result.content)}, reasoning_len={len(result.reasoning)})"
                if test_config["base_url"] and not test_config["base_url"].endswith('/v1'):
                    error_msg += "。提示：Base URL 可能缺少 /v1 后缀"
                raise ValueError(error_msg)

            # 更新配置的测试状态
            await self.repo.update_fields(
                config,
                is_verified=True,
                test_status="success",
                test_message="连接测试成功",
                last_test_at=datetime.now(timezone.utc),
            )
            await self.session.commit()

            logger.info("用户 %s 的配置 %s 测试成功，响应时间: %.2f ms", user_id, config.config_name, response_time_ms)

            return LLMConfigTestResponse(
                success=True,
                message="连接测试成功",
                response_time_ms=round(response_time_ms, 2),
                model_info=config.llm_provider_model or "默认模型",
            )

        except UnicodeDecodeError as exc:
            # 特殊处理编码错误：通常意味着 API 返回了非标准响应（错误页面或非 UTF-8 编码）
            error_message = (
                "服务器返回了无法解析的响应（编码错误）。"
                "可能原因：1) API Key 无效 2) 模型名称错误 3) Base URL 不正确。"
                "请检查配置是否正确，或联系服务提供商确认。"
            )
            logger.error(
                "用户 %s 的配置 %s 测试失败（编码错误）: %s，原始错误: %s",
                user_id,
                config.config_name,
                error_message,
                str(exc),
                exc_info=True
            )

            # 更新配置的测试状态
            await self.repo.update_fields(
                config,
                is_verified=False,
                test_status="failed",
                test_message=error_message,
                last_test_at=datetime.now(timezone.utc),
            )
            await self.session.commit()

            return LLMConfigTestResponse(
                success=False,
                message=error_message,
            )

        except Exception as exc:
            error_message = str(exc)
            logger.error("用户 %s 的配置 %s 测试失败: %s", user_id, config.config_name, error_message, exc_info=True)

            # 更新配置的测试状态
            await self.repo.update_fields(
                config,
                is_verified=False,
                test_status="failed",
                test_message=error_message[:500],  # 限制错误信息长度
                last_test_at=datetime.now(timezone.utc),
            )
            await self.session.commit()

            return LLMConfigTestResponse(
                success=False,
                message=f"连接测试失败: {error_message}",
            )

    # 保留旧方法以兼容现有代码
    async def upsert_config(self, user_id: int, payload: LLMConfigCreate) -> LLMConfigRead:
        """兼容旧API：创建或更新用户的第一个配置。"""
        configs = await self.repo.list_by_user(user_id)
        if configs:
            # 更新第一个配置
            return await self.update_config(configs[0].id, user_id, LLMConfigUpdate(**payload.model_dump()))
        else:
            # 创建新配置
            return await self.create_config(user_id, payload)

    # ------------------------------------------------------------------
    # 导入导出功能
    # ------------------------------------------------------------------

    async def export_config(self, config_id: int, user_id: int) -> dict:
        """
        导出单个LLM配置为JSON格式。

        Args:
            config_id: 配置ID
            user_id: 用户ID（权限验证）

        Returns:
            包含配置信息的字典
        """
        from datetime import datetime, timezone
        from ..schemas.llm_config import LLMConfigExport, LLMConfigExportData

        config = await self.repo.get_by_id(config_id, user_id)
        if not config:
            raise ResourceNotFoundError("LLM配置", f"ID={config_id}")

        export_data = LLMConfigExportData(
            version="1.0",
            export_time=datetime.now(timezone.utc).isoformat(),
            export_type="single",
            configs=[
                LLMConfigExport(
                    config_name=config.config_name,
                    llm_provider_url=config.llm_provider_url,
                    # 导出时解密API密钥
                    llm_provider_api_key=self._decrypt_key(config.llm_provider_api_key),
                    llm_provider_model=config.llm_provider_model,
                )
            ],
        )

        return export_data.model_dump()

    async def export_all_configs(self, user_id: int) -> dict:
        """
        导出用户的所有LLM配置为JSON格式。

        Args:
            user_id: 用户ID

        Returns:
            包含所有配置的字典
        """
        from datetime import datetime, timezone
        from ..schemas.llm_config import LLMConfigExport, LLMConfigExportData

        configs = await self.repo.list_by_user(user_id)
        if not configs:
            raise ResourceNotFoundError("LLM配置", f"用户ID={user_id}无配置可导出")

        export_data = LLMConfigExportData(
            version="1.0",
            export_time=datetime.now(timezone.utc).isoformat(),
            export_type="batch",
            configs=[
                LLMConfigExport(
                    config_name=config.config_name,
                    llm_provider_url=config.llm_provider_url,
                    # 导出时解密API密钥
                    llm_provider_api_key=self._decrypt_key(config.llm_provider_api_key),
                    llm_provider_model=config.llm_provider_model,
                )
                for config in configs
            ],
        )

        return export_data.model_dump()

    async def import_configs(self, user_id: int, import_data: dict) -> dict:
        """
        导入LLM配置。

        Args:
            user_id: 用户ID
            import_data: 导入的配置数据

        Returns:
            导入结果统计
        """
        from ..schemas.llm_config import LLMConfigExportData, LLMConfigImportResult

        # 验证导入数据格式
        try:
            data = LLMConfigExportData(**import_data)
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
                # 处理重名：如果配置名已存在，添加后缀
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
                new_config = LLMConfig(
                    user_id=user_id,
                    config_name=config_name,
                    llm_provider_url=config_data.llm_provider_url,
                    # 导入时加密API密钥
                    llm_provider_api_key=self._encrypt_key(config_data.llm_provider_api_key),
                    llm_provider_model=config_data.llm_provider_model,
                    is_active=False,  # 导入的配置默认不激活
                    is_verified=False,  # 需要重新测试
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
                    "导入配置失败: user_id=%s, config_name=%s, error=%s",
                    user_id,
                    config_data.config_name,
                    str(exc),
                    exc_info=True,
                )

        # 提交所有更改
        await self.session.commit()
        # 导入配置后使缓存失效
        if imported_count > 0:
            await _invalidate_llm_config_cache(user_id)

        return LLMConfigImportResult(
            success=imported_count > 0,
            message=f"导入完成：成功 {imported_count} 个，失败 {failed_count} 个",
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            details=details,
        ).model_dump()

