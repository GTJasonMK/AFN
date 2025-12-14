"""
配置管理模块
- 支持 JSON 配置文件
- 支持环境变量覆盖
- 配置热更新
"""
import os
import json
import secrets
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "config.json"  # 配置文件在根目录
STATIC_DIR = BASE_DIR / "static"
IMAGES_DIR = DATA_DIR / "images"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
API_SESSIONS_DIR = DATA_DIR / "api_sessions"  # 外部 API 一次性会话


class AccountConfig(BaseModel):
    """账号配置"""
    team_id: str = Field(..., description="团队ID (configId)")
    secure_c_ses: str = Field(..., description="__Secure-C_SES cookie")
    host_c_oses: str = Field("", description="__Host-C_OSES cookie")
    csesidx: str = Field(..., description="会话索引")
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        description="User-Agent"
    )
    available: bool = Field(True, description="是否可用")
    note: str = Field("", description="备注")


class ModelConfig(BaseModel):
    """模型配置"""
    id: str
    name: str
    description: str = ""
    context_length: int = 32768
    max_tokens: int = 8192
    enabled: bool = True


class CooldownConfig(BaseModel):
    """冷却时间配置（秒）"""
    auth_error_seconds: int = Field(900, alias="auth_error", description="认证错误冷却时间")
    rate_limit_seconds: int = Field(300, alias="rate_limit", description="限额错误冷却时间")
    generic_error_seconds: int = Field(120, alias="generic_error", description="通用错误冷却时间")

    class Config:
        populate_by_name = True


class AppConfig(BaseModel):
    """应用配置"""
    # 服务设置
    host: str = Field("0.0.0.0", description="监听地址")
    port: int = Field(8000, description="监听端口")

    # 代理设置
    proxy: str = Field("", description="HTTP代理地址")

    # 认证设置
    admin_password: str = Field("admin123", description="管理员密码")
    admin_secret_key: str = Field("", description="管理员密钥")
    api_tokens: List[str] = Field(default_factory=list, description="API访问令牌")

    # 账号列表
    accounts: List[AccountConfig] = Field(default_factory=list)

    # 模型列表
    models: List[ModelConfig] = Field(default_factory=lambda: [
        ModelConfig(id="gemini-2.5-flash", name="Gemini 2.5 Flash", description="快速响应"),
        ModelConfig(id="gemini-2.5-pro", name="Gemini 2.5 Pro", description="更强能力"),
        ModelConfig(id="gemini-3-pro", name="Gemini 3 Pro", description="最新模型"),
    ])

    # 冷却配置
    cooldown: CooldownConfig = Field(default_factory=CooldownConfig)

    # 图片配置
    image_cache_hours: int = Field(24, description="图片缓存时间（小时）")
    image_base_url: str = Field("", description="图片访问基础URL")

    # 日志级别
    log_level: str = Field("INFO", description="日志级别")


class Settings(BaseSettings):
    """环境变量配置"""
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # 可以通过环境变量覆盖
    proxy: str = ""
    log_level: str = "INFO"

    class Config:
        env_prefix = "GEMINI_"
        env_file = ".env"
        extra = "ignore"


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._settings = Settings()
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录存在"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)
        API_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        """加载配置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = AppConfig(**data)
                logger.info(f"配置已加载: {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                self._config = AppConfig()
        else:
            self._config = AppConfig()
            self.save()
            logger.info(f"已创建默认配置: {CONFIG_FILE}")

        # 环境变量覆盖
        if self._settings.proxy:
            self._config.proxy = self._settings.proxy
        if self._settings.log_level:
            self._config.log_level = self._settings.log_level

        # 确保有管理员密钥
        if not self._config.admin_secret_key:
            self._config.admin_secret_key = secrets.token_urlsafe(32)
            self.save()

        return self._config

    def save(self):
        """保存配置"""
        if self._config:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config.model_dump(), f, indent=2, ensure_ascii=False)
            logger.debug("配置已保存")

    # 方法别名，兼容不同调用方式
    def load_config(self) -> AppConfig:
        """load 方法的别名"""
        return self.load()

    def save_config(self):
        """save 方法的别名"""
        self.save()

    @property
    def config(self) -> AppConfig:
        """获取配置"""
        if self._config is None:
            self.load()
        return self._config

    @property
    def settings(self) -> Settings:
        """获取环境变量配置"""
        return self._settings

    def get_account(self, index: int) -> Optional[AccountConfig]:
        """获取指定账号"""
        if 0 <= index < len(self.config.accounts):
            return self.config.accounts[index]
        return None

    def add_account(self, account: AccountConfig) -> int:
        """添加账号，返回索引"""
        self.config.accounts.append(account)
        self.save()
        return len(self.config.accounts) - 1

    def update_account(self, index: int, account: AccountConfig):
        """更新账号"""
        if 0 <= index < len(self.config.accounts):
            self.config.accounts[index] = account
            self.save()

    def remove_account(self, index: int) -> bool:
        """删除账号"""
        if 0 <= index < len(self.config.accounts):
            self.config.accounts.pop(index)
            self.save()
            return True
        return False


# 全局配置管理器
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """获取应用配置"""
    return config_manager.config


def get_settings() -> Settings:
    """获取环境变量配置"""
    return config_manager.settings
