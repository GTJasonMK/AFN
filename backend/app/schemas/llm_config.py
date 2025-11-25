from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl, Field


def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    """遮蔽API Key，仅显示前8位和后4位。"""
    if not api_key or len(api_key) <= 12:
        return "***" if api_key else None
    return f"{api_key[:8]}{'*' * (len(api_key) - 12)}{api_key[-4:]}"


class LLMConfigBase(BaseModel):
    """LLM配置基础模型。"""

    config_name: str = Field(default="默认配置", description="配置名称", max_length=100)
    llm_provider_url: Optional[str] = Field(default=None, description="自定义 LLM 服务地址")
    llm_provider_api_key: Optional[str] = Field(default=None, description="自定义 LLM API Key")
    llm_provider_model: Optional[str] = Field(default=None, description="自定义模型名称")


class LLMConfigCreate(LLMConfigBase):
    """创建LLM配置的请求模型。"""

    pass


class LLMConfigUpdate(BaseModel):
    """更新LLM配置的请求模型（所有字段可选）。"""

    config_name: Optional[str] = Field(default=None, description="配置名称", max_length=100)
    llm_provider_url: Optional[str] = Field(default=None, description="自定义 LLM 服务地址")
    llm_provider_api_key: Optional[str] = Field(default=None, description="自定义 LLM API Key")
    llm_provider_model: Optional[str] = Field(default=None, description="自定义模型名称")


class LLMConfigRead(BaseModel):
    """LLM配置的响应模型。"""

    id: int
    user_id: int
    config_name: str
    llm_provider_url: Optional[str] = None
    llm_provider_api_key_masked: Optional[str] = Field(default=None, description="遮蔽后的API Key")
    llm_provider_model: Optional[str] = None
    is_active: bool
    is_verified: bool
    last_test_at: Optional[datetime] = None
    test_status: Optional[str] = None  # success, failed, pending
    test_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_mask(cls, config):
        """从ORM对象创建，并遮蔽API Key。"""
        return cls(
            id=config.id,
            user_id=config.user_id,
            config_name=config.config_name,
            llm_provider_url=config.llm_provider_url,
            llm_provider_api_key_masked=mask_api_key(config.llm_provider_api_key),
            llm_provider_model=config.llm_provider_model,
            is_active=config.is_active,
            is_verified=config.is_verified,
            last_test_at=config.last_test_at,
            test_status=config.test_status,
            test_message=config.test_message,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )


class LLMConfigTestRequest(BaseModel):
    """测试LLM配置的请求模型。"""

    config_id: int = Field(..., description="要测试的配置ID")


class LLMConfigTestResponse(BaseModel):
    """测试LLM配置的响应模型。"""

    success: bool
    message: str
    response_time_ms: Optional[float] = None  # 响应时间（毫秒）
    model_info: Optional[str] = None  # 模型信息（如果测试成功）


class LLMConfigExport(BaseModel):
    """导出的LLM配置数据（不包含运行时状态）。"""

    config_name: str
    llm_provider_url: Optional[str] = None
    llm_provider_api_key: Optional[str] = None
    llm_provider_model: Optional[str] = None


class LLMConfigExportData(BaseModel):
    """导出文件的完整数据结构。"""

    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    export_type: str = Field(..., description="导出类型：single 或 batch")
    configs: list[LLMConfigExport] = Field(..., description="配置列表")


class LLMConfigImportRequest(BaseModel):
    """导入LLM配置的请求模型。"""

    data: LLMConfigExportData = Field(..., description="导入的配置数据")


class LLMConfigImportResult(BaseModel):
    """导入结果。"""

    success: bool
    message: str
    imported_count: int = 0  # 成功导入的配置数量
    skipped_count: int = 0  # 跳过的配置数量
    failed_count: int = 0  # 失败的配置数量
    details: list[str] = []  # 详细信息
