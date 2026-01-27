"""
嵌入模型配置 Schema

定义嵌入模型配置的请求和响应模型。
"""

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field

from .config_runtime_status import ConfigRuntimeStatus
from .schema_utils import mask_api_key


class EmbeddingConfigBase(BaseModel):
    """嵌入模型配置基础模型。"""

    config_name: str = Field(default="默认嵌入配置", description="配置名称", max_length=100)
    provider: Literal["openai", "ollama", "local"] = Field(default="openai", description="提供方类型")
    api_base_url: Optional[str] = Field(default=None, description="API Base URL")
    api_key: Optional[str] = Field(default=None, description="API Key（仅 openai 需要）")
    model_name: Optional[str] = Field(default=None, description="模型名称")
    vector_size: Optional[int] = Field(default=None, description="向量维度（可选，自动检测）")


class EmbeddingConfigCreate(EmbeddingConfigBase):
    """创建嵌入模型配置的请求模型。"""

    pass


class EmbeddingConfigUpdate(BaseModel):
    """更新嵌入模型配置的请求模型（所有字段可选）。"""

    config_name: Optional[str] = Field(default=None, description="配置名称", max_length=100)
    provider: Optional[Literal["openai", "ollama", "local"]] = Field(default=None, description="提供方类型")
    api_base_url: Optional[str] = Field(default=None, description="API Base URL")
    api_key: Optional[str] = Field(default=None, description="API Key")
    model_name: Optional[str] = Field(default=None, description="模型名称")
    vector_size: Optional[int] = Field(default=None, description="向量维度")


class EmbeddingConfigRead(ConfigRuntimeStatus):
    """嵌入模型配置的响应模型。"""

    id: int
    user_id: int
    config_name: str
    provider: str
    api_base_url: Optional[str] = None
    api_key_masked: Optional[str] = Field(default=None, description="遮蔽后的API Key")
    model_name: Optional[str] = None
    vector_size: Optional[int] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_mask(cls, config):
        """从ORM对象创建，并遮蔽API Key。"""
        return cls(
            id=config.id,
            user_id=config.user_id,
            config_name=config.config_name,
            provider=config.provider,
            api_base_url=config.api_base_url,
            api_key_masked=mask_api_key(config.api_key),
            model_name=config.model_name,
            vector_size=config.vector_size,
            is_active=config.is_active,
            is_verified=config.is_verified,
            last_test_at=config.last_test_at,
            test_status=config.test_status,
            test_message=config.test_message,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )


class EmbeddingConfigTestResponse(BaseModel):
    """测试嵌入模型配置的响应模型。"""

    success: bool
    message: str
    response_time_ms: Optional[float] = None  # 响应时间（毫秒）
    vector_dimension: Optional[int] = None  # 向量维度（如果测试成功）
    model_info: Optional[str] = None  # 模型信息


class EmbeddingProviderInfo(BaseModel):
    """嵌入模型提供方信息。"""

    provider: str
    name: str
    description: str
    default_model: str
    requires_api_key: bool
    default_base_url: Optional[str] = None


# 预定义的提供方信息
EMBEDDING_PROVIDERS = [
    EmbeddingProviderInfo(
        provider="openai",
        name="OpenAI / 兼容 API",
        description="支持 OpenAI 官方 API 及所有兼容接口（如中转站）",
        default_model="text-embedding-3-small",
        requires_api_key=True,
        default_base_url="https://api.openai.com/v1",
    ),
    EmbeddingProviderInfo(
        provider="ollama",
        name="Ollama 本地模型",
        description="使用本地运行的 Ollama 服务",
        default_model="nomic-embed-text:latest",
        requires_api_key=False,
        default_base_url="http://localhost:11434",
    ),
    EmbeddingProviderInfo(
        provider="local",
        name="本地嵌入模型",
        description="使用 sentence-transformers 在本地运行嵌入模型，无需网络连接",
        default_model="BAAI/bge-base-zh-v1.5",
        requires_api_key=False,
        default_base_url=None,
    ),
]


# ------------------------------------------------------------------
# 导入导出相关
# ------------------------------------------------------------------

class EmbeddingConfigExport(BaseModel):
    """导出的嵌入配置数据（不包含运行时状态）。"""

    config_name: str
    provider: str = "openai"
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    vector_size: Optional[int] = None


class EmbeddingConfigExportData(BaseModel):
    """导出文件的完整数据结构。"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(default="embedding", description="导出类型")
    configs: list[EmbeddingConfigExport] = Field(..., description="配置列表")


class EmbeddingConfigImportResult(BaseModel):
    """导入结果。"""

    success: bool
    message: str
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    details: list[str] = []
