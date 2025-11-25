from functools import lru_cache
from pathlib import Path
from typing import Optional
import sys

from pydantic import AliasChoices, AnyUrl, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    """应用全局配置，所有可调参数集中于此，统一加载自环境变量。"""

    # -------------------- 基础应用配置 --------------------
    app_name: str = Field(default="AI Novel Generator API", description="FastAPI 文档标题")
    environment: str = Field(default="development", description="当前环境标识")
    debug: bool = Field(default=True, description="是否开启调试模式")
    logging_level: str = Field(
        default="INFO",
        env="LOGGING_LEVEL",
        description="应用日志级别",
    )

    # -------------------- 安全相关配置 --------------------
    secret_key: str = Field(..., env="SECRET_KEY", description="JWT 加密密钥")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM", description="JWT 加密算法")
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        env="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="访问令牌过期时间，单位分钟"
    )

    # -------------------- 数据库配置 --------------------
    database_url: Optional[str] = Field(
        default=None,
        env="DATABASE_URL",
        description="完整的数据库连接串，填入后覆盖下方数据库配置"
    )
    db_provider: str = Field(
        default="mysql",
        env="DB_PROVIDER",
        description="数据库类型，仅支持 mysql 或 sqlite"
    )
    mysql_host: str = Field(default="localhost", env="MYSQL_HOST", description="MySQL 主机名")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT", description="MySQL 端口")
    mysql_user: str = Field(default="root", env="MYSQL_USER", description="MySQL 用户名")
    mysql_password: str = Field(default="", env="MYSQL_PASSWORD", description="MySQL 密码")
    mysql_database: str = Field(default="arboris", env="MYSQL_DATABASE", description="MySQL 数据库名称")

    # -------------------- LLM 相关配置 --------------------
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY", description="默认的 LLM API Key")
    openai_base_url: Optional[HttpUrl] = Field(
        default=None,
        env="OPENAI_API_BASE_URL",
        validation_alias=AliasChoices("OPENAI_API_BASE_URL", "OPENAI_BASE_URL"),
        description="LLM API Base URL",
    )
    openai_model_name: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL_NAME", description="默认 LLM 模型名称")
    writer_chapter_versions: int = Field(
        default=3,
        ge=1,
        le=5,
        env="WRITER_CHAPTER_VERSION_COUNT",
        validation_alias=AliasChoices("WRITER_CHAPTER_VERSION_COUNT", "WRITER_CHAPTER_VERSIONS"),
        description="每次生成章节的候选版本数量",
    )
    writer_parallel_generation: bool = Field(
        default=True,
        env="WRITER_PARALLEL_GENERATION",
        description="是否启用章节版本并行生成（大幅提升速度）",
    )
    writer_max_parallel_requests: int = Field(
        default=3,
        ge=1,
        le=10,
        env="WRITER_MAX_PARALLEL_REQUESTS",
        description="最大并行请求数（避免 API 限流）",
    )
    part_outline_threshold: int = Field(
        default=50,
        ge=10,
        le=100,
        env="PART_OUTLINE_THRESHOLD",
        description="超过此章节数将生成分部大纲（默认50章，确保至少2个完整部分，每部分25章）",
    )
    embedding_provider: str = Field(
        default="openai",
        env="EMBEDDING_PROVIDER",
        description="嵌入模型提供方，支持 openai 或 ollama",
    )
    embedding_base_url: Optional[AnyUrl] = Field(
        default=None,
        env="EMBEDDING_BASE_URL",
        description="嵌入模型使用的 Base URL",
    )
    embedding_api_key: Optional[str] = Field(
        default=None,
        env="EMBEDDING_API_KEY",
        description="嵌入模型专用 API Key",
    )
    embedding_model: str = Field(
        default="text-embedding-3-large",
        env="EMBEDDING_MODEL",
        validation_alias=AliasChoices("EMBEDDING_MODEL", "VECTOR_EMBEDDING_MODEL"),
        description="默认的嵌入模型名称",
    )
    embedding_model_vector_size: Optional[int] = Field(
        default=None,
        env="EMBEDDING_MODEL_VECTOR_SIZE",
        description="嵌入向量维度，未配置时将自动检测",
    )
    ollama_embedding_base_url: Optional[AnyUrl] = Field(
        default=None,
        env="OLLAMA_EMBEDDING_BASE_URL",
        description="Ollama 嵌入模型服务地址",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text:latest",
        env="OLLAMA_EMBEDDING_MODEL",
        description="Ollama 嵌入模型名称",
    )
    vector_db_url: Optional[str] = Field(
        default=None,
        env="VECTOR_DB_URL",
        description="libsql 向量库连接地址",
    )
    vector_db_auth_token: Optional[str] = Field(
        default=None,
        env="VECTOR_DB_AUTH_TOKEN",
        description="libsql 访问令牌",
    )
    vector_top_k_chunks: int = Field(
        default=5,
        ge=0,
        env="VECTOR_TOP_K_CHUNKS",
        description="剧情 chunk 检索条数",
    )
    vector_top_k_summaries: int = Field(
        default=3,
        ge=0,
        env="VECTOR_TOP_K_SUMMARIES",
        description="章节摘要检索条数",
    )
    vector_chunk_size: int = Field(
        default=480,
        ge=128,
        env="VECTOR_CHUNK_SIZE",
        description="章节分块的目标字数",
    )
    vector_chunk_overlap: int = Field(
        default=120,
        ge=0,
        env="VECTOR_CHUNK_OVERLAP",
        description="章节分块重叠字数",
    )

    # LLM Temperature 配置
    llm_temp_inspiration: float = Field(
        default=0.8,
        ge=0.0,
        le=2.0,
        env="LLM_TEMP_INSPIRATION",
        description="灵感对话的temperature值（创造性高）",
    )
    llm_temp_blueprint: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        env="LLM_TEMP_BLUEPRINT",
        description="蓝图生成的temperature值（结构化）",
    )
    llm_temp_outline: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        env="LLM_TEMP_OUTLINE",
        description="章节大纲生成的temperature值",
    )
    llm_temp_writing: float = Field(
        default=0.75,
        ge=0.0,
        le=2.0,
        env="LLM_TEMP_WRITING",
        description="章节内容生成的temperature值（创造性高）",
    )
    llm_temp_evaluation: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        env="LLM_TEMP_EVALUATION",
        description="章节评审的temperature值（客观性）",
    )
    llm_temp_summary: float = Field(
        default=0.15,
        ge=0.0,
        le=2.0,
        env="LLM_TEMP_SUMMARY",
        description="摘要生成的temperature值（精确性）",
    )

    model_config = SettingsConfigDict(
        env_file=("new-backend/.env", ".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Optional[str]) -> Optional[str]:
        """当环境变量中提供 DATABASE_URL 时，原样返回，便于自定义。"""
        return value.strip() if isinstance(value, str) and value.strip() else value

    @field_validator("db_provider", mode="before")
    @classmethod
    def _normalize_db_provider(cls, value: Optional[str]) -> str:
        """统一数据库类型大小写，并限制为受支持的驱动。"""
        candidate = (value or "mysql").strip().lower()
        if candidate not in {"mysql", "sqlite"}:
            raise ValueError("DB_PROVIDER 仅支持 mysql 或 sqlite")
        return candidate

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def _normalize_embedding_provider(cls, value: Optional[str]) -> str:
        """限制嵌入模型提供方的取值范围。"""
        candidate = (value or "openai").strip().lower()
        if candidate not in {"openai", "ollama"}:
            raise ValueError("EMBEDDING_PROVIDER 仅支持 openai 或 ollama")
        return candidate

    @field_validator("logging_level", mode="before")
    @classmethod
    def _normalize_logging_level(cls, value: Optional[str]) -> str:
        """规范日志级别配置。"""
        candidate = (value or "INFO").strip().upper()
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if candidate not in valid_levels:
            raise ValueError("LOGGING_LEVEL 仅支持 CRITICAL/ERROR/WARNING/INFO/DEBUG/NOTSET")
        return candidate

    @property
    def sqlalchemy_database_uri(self) -> str:
        """生成 SQLAlchemy 兼容的异步连接串，数据库类型由 DB_PROVIDER 控制。"""
        if self.database_url:
            url = make_url(self.database_url)
            database = (url.database or "").strip("/")
            normalized = URL.create(
                drivername=url.drivername,
                username=url.username,
                password=url.password,
                host=url.host,
                port=url.port,
                database=database or None,
                query=url.query,
            )
            return normalized.render_as_string(hide_password=False)

        if self.db_provider == "sqlite":
            # SQLite 固定使用 storage/arboris.db，并转换为绝对路径以避免运行目录差异
            project_root = Path(__file__).resolve().parents[2]
            db_path = (project_root / "storage" / "arboris.db").resolve()
            return f"sqlite+aiosqlite:///{db_path}"

        # MySQL 分支：统一对密码进行 URL 编码，避免特殊字符破坏连接串
        from urllib.parse import quote_plus

        encoded_password = quote_plus(self.mysql_password)
        database = (self.mysql_database or "").strip("/")
        return (
            f"mysql+asyncmy://{self.mysql_user}:{encoded_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{database}"
        )

    @property
    def is_sqlite_backend(self) -> bool:
        """辅助属性：判断当前连接串是否指向 SQLite，用于差异化初始化流程。"""
        return make_url(self.sqlalchemy_database_uri).get_backend_name() == "sqlite"

    @property
    def vector_store_enabled(self) -> bool:
        """是否已经配置向量库，用于在业务逻辑中快速判断。"""
        return bool(self.vector_db_url)


@lru_cache
def get_settings() -> Settings:
    """使用 LRU 缓存确保配置只初始化一次，减少 IO 与解析开销。"""
    return Settings()


def reload_settings() -> Settings:
    """重新加载配置，清除缓存并返回新的配置实例。

    用于热更新场景，当.env文件被修改后调用此函数可立即生效。
    同时会更新当前模块中的全局settings变量。
    """
    get_settings.cache_clear()
    new_settings = get_settings()

    # 更新当前模块的全局settings变量
    current_module = sys.modules[__name__]
    setattr(current_module, 'settings', new_settings)

    return new_settings


settings = get_settings()
