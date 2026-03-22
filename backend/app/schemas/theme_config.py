"""
主题配置Schema模块

定义主题配置的请求/响应模型。
支持两种配置格式：
- V1（旧版）：面向常量的配置
- V2（新版）：面向组件的配置
"""

from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


# ==================== 请求/响应模型 ====================

class ThemeConfigBase(BaseModel):
    """主题配置基础模型"""
    config_name: str = Field(default="自定义主题", description="配置名称", max_length=100)
    parent_mode: Literal["light", "dark"] = Field(..., description="顶级主题模式")


class ThemeConfigCreate(ThemeConfigBase):
    """创建主题配置的请求模型"""
    # 各组配置（可选，不提供则使用默认值）
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None


class ThemeConfigUpdate(BaseModel):
    """更新主题配置的请求模型（所有字段可选）"""
    config_name: Optional[str] = Field(default=None, max_length=100)
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None


class ThemeConfigRead(BaseModel):
    """主题配置的响应模型"""
    id: int
    user_id: int
    config_name: str
    parent_mode: str
    is_active: bool
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThemeConfigListItem(BaseModel):
    """主题配置列表项（简化版，用于列表显示）"""
    id: int
    config_name: str
    parent_mode: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThemeDefaultsResponse(BaseModel):
    """获取默认主题值的响应"""
    mode: str
    primary_colors: dict[str, Any]
    accent_colors: dict[str, Any]
    semantic_colors: dict[str, Any]
    text_colors: dict[str, Any]
    background_colors: dict[str, Any]
    border_effects: dict[str, Any]
    button_colors: dict[str, Any]
    typography: dict[str, Any]
    border_radius: dict[str, Any]
    spacing: dict[str, Any]
    animation: dict[str, Any]
    button_sizes: dict[str, Any]


class ThemeConfigExport(BaseModel):
    """导出的主题配置数据"""
    config_name: str
    parent_mode: str
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None


class ThemeConfigExportData(BaseModel):
    """导出文件的完整数据结构"""
    version: str = Field(default="1.0", description="导出格式版本")
    export_time: str = Field(..., description="导出时间（ISO 8601格式）")
    configs: list[ThemeConfigExport] = Field(..., description="配置列表")


class ThemeConfigImportRequest(BaseModel):
    """导入主题配置的请求模型"""
    data: ThemeConfigExportData


class ThemeConfigImportResult(BaseModel):
    """导入结果"""
    success: bool
    message: str
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    details: list[str] = []


# ==================== V2: 面向组件的配置模型 ====================

class ThemeConfigV2Create(BaseModel):
    """创建V2格式主题配置的请求模型"""
    config_name: str = Field(default="自定义主题", description="配置名称", max_length=100)
    parent_mode: Literal["light", "dark"] = Field(..., description="顶级主题模式")

    # V2 设计令牌
    token_colors: Optional[dict[str, Any]] = None
    token_typography: Optional[dict[str, Any]] = None
    token_spacing: Optional[dict[str, Any]] = None
    token_radius: Optional[dict[str, Any]] = None

    # V2 组件配置
    comp_button: Optional[dict[str, Any]] = None
    comp_card: Optional[dict[str, Any]] = None
    comp_input: Optional[dict[str, Any]] = None
    comp_sidebar: Optional[dict[str, Any]] = None
    comp_header: Optional[dict[str, Any]] = None
    comp_dialog: Optional[dict[str, Any]] = None
    comp_scrollbar: Optional[dict[str, Any]] = None
    comp_tooltip: Optional[dict[str, Any]] = None
    comp_tabs: Optional[dict[str, Any]] = None
    comp_text: Optional[dict[str, Any]] = None
    comp_semantic: Optional[dict[str, Any]] = None

    # V2 效果配置
    effects: Optional[dict[str, Any]] = None


class ThemeConfigV2Update(BaseModel):
    """更新V2格式主题配置的请求模型（所有字段可选）"""
    config_name: Optional[str] = Field(default=None, max_length=100)

    # V2 设计令牌
    token_colors: Optional[dict[str, Any]] = None
    token_typography: Optional[dict[str, Any]] = None
    token_spacing: Optional[dict[str, Any]] = None
    token_radius: Optional[dict[str, Any]] = None

    # V2 组件配置
    comp_button: Optional[dict[str, Any]] = None
    comp_card: Optional[dict[str, Any]] = None
    comp_input: Optional[dict[str, Any]] = None
    comp_sidebar: Optional[dict[str, Any]] = None
    comp_header: Optional[dict[str, Any]] = None
    comp_dialog: Optional[dict[str, Any]] = None
    comp_scrollbar: Optional[dict[str, Any]] = None
    comp_tooltip: Optional[dict[str, Any]] = None
    comp_tabs: Optional[dict[str, Any]] = None
    comp_text: Optional[dict[str, Any]] = None
    comp_semantic: Optional[dict[str, Any]] = None

    # V2 效果配置
    effects: Optional[dict[str, Any]] = None


class ThemeConfigV2Read(BaseModel):
    """V2格式主题配置的响应模型"""
    id: int
    user_id: int
    config_name: str
    parent_mode: str
    is_active: bool
    config_version: int = 2

    # V2 设计令牌
    token_colors: Optional[dict[str, Any]] = None
    token_typography: Optional[dict[str, Any]] = None
    token_spacing: Optional[dict[str, Any]] = None
    token_radius: Optional[dict[str, Any]] = None

    # V2 组件配置
    comp_button: Optional[dict[str, Any]] = None
    comp_card: Optional[dict[str, Any]] = None
    comp_input: Optional[dict[str, Any]] = None
    comp_sidebar: Optional[dict[str, Any]] = None
    comp_header: Optional[dict[str, Any]] = None
    comp_dialog: Optional[dict[str, Any]] = None
    comp_scrollbar: Optional[dict[str, Any]] = None
    comp_tooltip: Optional[dict[str, Any]] = None
    comp_tabs: Optional[dict[str, Any]] = None
    comp_text: Optional[dict[str, Any]] = None
    comp_semantic: Optional[dict[str, Any]] = None

    # V2 效果配置
    effects: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThemeV2DefaultsResponse(BaseModel):
    """获取V2格式默认主题值的响应"""
    mode: str
    config_version: int = 2

    # 设计令牌
    token_colors: dict[str, Any]
    token_typography: dict[str, Any]
    token_spacing: dict[str, Any]
    token_radius: dict[str, Any]

    # 组件配置
    comp_button: dict[str, Any]
    comp_card: dict[str, Any]
    comp_input: dict[str, Any]
    comp_sidebar: dict[str, Any]
    comp_header: dict[str, Any]
    comp_dialog: dict[str, Any]
    comp_scrollbar: dict[str, Any]
    comp_tooltip: dict[str, Any]
    comp_tabs: dict[str, Any]
    comp_text: dict[str, Any]
    comp_semantic: dict[str, Any]

    # 效果配置
    effects: dict[str, Any]


class ThemeConfigUnifiedRead(BaseModel):
    """统一的主题配置响应模型（支持V1和V2）"""
    id: int
    user_id: int
    config_name: str
    parent_mode: str
    is_active: bool
    config_version: int = 1

    # V1 配置（面向常量）
    primary_colors: Optional[dict[str, Any]] = None
    accent_colors: Optional[dict[str, Any]] = None
    semantic_colors: Optional[dict[str, Any]] = None
    text_colors: Optional[dict[str, Any]] = None
    background_colors: Optional[dict[str, Any]] = None
    border_effects: Optional[dict[str, Any]] = None
    button_colors: Optional[dict[str, Any]] = None
    typography: Optional[dict[str, Any]] = None
    border_radius: Optional[dict[str, Any]] = None
    spacing: Optional[dict[str, Any]] = None
    animation: Optional[dict[str, Any]] = None
    button_sizes: Optional[dict[str, Any]] = None

    # V2 配置（面向组件）
    token_colors: Optional[dict[str, Any]] = None
    token_typography: Optional[dict[str, Any]] = None
    token_spacing: Optional[dict[str, Any]] = None
    token_radius: Optional[dict[str, Any]] = None
    comp_button: Optional[dict[str, Any]] = None
    comp_card: Optional[dict[str, Any]] = None
    comp_input: Optional[dict[str, Any]] = None
    comp_sidebar: Optional[dict[str, Any]] = None
    comp_header: Optional[dict[str, Any]] = None
    comp_dialog: Optional[dict[str, Any]] = None
    comp_scrollbar: Optional[dict[str, Any]] = None
    comp_tooltip: Optional[dict[str, Any]] = None
    comp_tabs: Optional[dict[str, Any]] = None
    comp_text: Optional[dict[str, Any]] = None
    comp_semantic: Optional[dict[str, Any]] = None
    effects: Optional[dict[str, Any]] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
