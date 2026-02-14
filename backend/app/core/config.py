from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Optional
import os
import re
import sys

from pydantic import AliasChoices, AnyUrl, Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


def _resolve_env_files() -> tuple[str, ...]:
    """解析 `.env` 文件候选路径（优先保证在任意 cwd 下都能读到项目的 backend/.env）。

    说明：
    - pydantic-settings 支持多个 env_file，会按顺序加载，后者覆盖前者；
    - uvicorn 的 reload 子进程/IDE 启动时 cwd 可能变化，导致相对路径找不到 `.env`；
      因此这里同时提供「相对路径」与「基于项目根目录的绝对路径」两套候选，避免误判为“配置不生效”。
    """
    # 相对路径（兼容从项目根目录或 backend/ 目录启动）
    relative_candidates = (
        "new-backend/.env",
        ".env",
        "backend/.env",
    )

    # 绝对路径（兜底：不依赖当前工作目录）
    try:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parents[3]
    except Exception:
        base_dir = Path.cwd()

    absolute_candidates = (
        str(base_dir / "new-backend" / ".env"),
        str(base_dir / ".env"),
        str(base_dir / "backend" / ".env"),
    )

    # 去重（保持顺序）
    ordered: list[str] = []
    seen: set[str] = set()
    for path in (*relative_candidates, *absolute_candidates):
        if path in seen:
            continue
        seen.add(path)
        ordered.append(path)
    return tuple(ordered)


_YAML_ENV_LINE_RE = re.compile(r"^-\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def _preload_yaml_list_env_lines(env_files: tuple[str, ...]) -> None:
    """预解析 `.env` 内容并写入 os.environ（兼容多种写法）。

    说明：
    - 用户经常把 compose 的 `environment:` 片段（`- KEY=value`）直接粘贴到 `.env`，导致 pydantic-settings 无法识别；
    - Windows 记事本保存的 `.env` 可能带 UTF-8 BOM（首行 key 会变成 `\ufeffKEY`），同样会导致读取失败；
    - 这里在初始化 Settings 前做一次“最小化预解析”，将能识别的 KEY=value 写入 os.environ；
    - 不覆盖“进程已存在”的环境变量（例如系统环境变量或启动脚本注入的 DATABASE_URL 等）；
    - 多个 env_file 之间遵循与 pydantic-settings 一致的覆盖顺序：后者覆盖前者。
    """
    dotenv_key_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=.*$")
    dotenv_line_re = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

    # 记录预解析开始时已存在的环境变量：这些变量被视为“外部注入”，不允许被 .env 覆盖。
    # 这样既能保持 os.environ 的优先级，又能让多个 env_file 之间按顺序覆盖。
    baseline_env_keys = set(os.environ.keys())

    for env_file in env_files:
        try:
            path = Path(str(env_file))
            if not path.is_file():
                continue

            # 使用 utf-8-sig 兼容 Windows 记事本保存的 UTF-8 BOM，避免首行 key 解析失败导致“配置不生效”。
            raw_lines = path.read_text(encoding="utf-8-sig").splitlines()

            # 如果文件同时包含正常 dotenv 写法（KEY=value），优先信任 dotenv 写法，
            # 避免 YAML 列表行（- KEY=value）意外覆盖同名键。
            dotenv_keys: set[str] = set()
            for raw_line in raw_lines:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.lower().startswith("export "):
                    line = line[7:].lstrip()
                if line.startswith("-"):
                    continue
                match = dotenv_key_re.match(line)
                if match:
                    dotenv_keys.add(match.group(1))

            # 先处理标准 dotenv 行：KEY=value
            for raw_line in raw_lines:
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                if line.lower().startswith("export "):
                    line = line[7:].lstrip()

                match = dotenv_line_re.match(line)
                if not match:
                    continue

                key = match.group(1).strip()
                value = match.group(2).strip()
                if not key or key in baseline_env_keys:
                    continue

                if value and not value.startswith(("'", '"')) and "#" in value:
                    value = value.split("#", 1)[0].rstrip()

                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                os.environ[key] = value

            for raw_line in raw_lines:
                line = raw_line.strip()
                if not line.startswith("-"):
                    continue

                match = _YAML_ENV_LINE_RE.match(line)
                if not match:
                    continue

                key = match.group(1).strip()
                value = match.group(2).strip()
                if key in dotenv_keys:
                    continue
                if not key or key in baseline_env_keys:
                    continue

                # 去掉未引用值中的行尾注释：- KEY=value # comment
                if value and not value.startswith(("'", '"')) and "#" in value:
                    value = value.split("#", 1)[0].rstrip()

                # 去掉包裹引号
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]

                os.environ[key] = value
        except Exception:
            # 任何解析问题都不应阻断启动；交由 /api/auth/status?debug=1 排障即可。
            continue


class Settings(BaseSettings):
    """应用全局配置，所有可调参数集中于此，统一加载自环境变量。"""

    # 桌面版与开发环境的默认密钥（便于直接运行后端进行本地调试）
    # 生产环境请务必通过环境变量 SECRET_KEY 显式覆盖
    DEFAULT_DESKTOP_SECRET_KEY: ClassVar[str] = "afn-desktop-secret-key-2024"

    # -------------------- 基础应用配置 --------------------
    app_name: str = Field(default="AI Novel Generator API", description="FastAPI 文档标题")
    environment: str = Field(default="development", description="当前环境标识")
    debug: bool = Field(default=True, description="是否开启调试模式")
    logging_level: str = Field(
        default="DEBUG",
        env="LOGGING_LEVEL",
        description="应用日志级别",
    )

    # -------------------- 安全相关配置 --------------------
    secret_key: str = Field(
        default=DEFAULT_DESKTOP_SECRET_KEY,
        env="SECRET_KEY",
        description="JWT 加密密钥（开发环境有默认值；生产环境必须显式配置）",
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM", description="JWT 加密算法")
    access_token_expire_minutes: int = Field(
        default=60 * 24 * 7,
        env="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="访问令牌过期时间，单位分钟"
    )

    # -------------------- WebUI 用户系统（可选） --------------------
    auth_enabled: bool = Field(
        default=False,
        env="AFN_AUTH_ENABLED",
        validation_alias=AliasChoices("AFN_AUTH_ENABLED", "AUTH_ENABLED"),
        description="是否启用 WebUI 登录认证（开启后将要求登录并启用多用户数据隔离）",
    )
    auth_allow_registration: bool = Field(
        default=True,
        env="AFN_AUTH_ALLOW_REGISTRATION",
        validation_alias=AliasChoices("AFN_AUTH_ALLOW_REGISTRATION", "AUTH_ALLOW_REGISTRATION"),
        description="是否允许 WebUI 自助注册（仅在启用登录时生效）",
    )

    # -------------------- 数据库配置 --------------------
    database_url: Optional[str] = Field(
        default=None,
        env="DATABASE_URL",
        description="完整的数据库连接串，填入后覆盖下方数据库配置"
    )
    db_provider: str = Field(
        default="sqlite",
        env="DB_PROVIDER",
        description="数据库类型，仅支持 mysql 或 sqlite"
    )
    mysql_host: str = Field(default="localhost", env="MYSQL_HOST", description="MySQL 主机名")
    mysql_port: int = Field(default=3306, env="MYSQL_PORT", description="MySQL 端口")
    mysql_user: str = Field(default="root", env="MYSQL_USER", description="MySQL 用户名")
    mysql_password: str = Field(default="", env="MYSQL_PASSWORD", description="MySQL 密码")
    mysql_database: str = Field(default="afn", env="MYSQL_DATABASE", description="MySQL 数据库名称")

    # SQLite 特定配置
    sqlite_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        env="SQLITE_TIMEOUT",
        description="SQLite 连接超时时间（秒），避免 'database is locked' 错误",
    )
    sqlite_busy_timeout: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        env="SQLITE_BUSY_TIMEOUT",
        description="SQLite busy_timeout（毫秒），等待锁释放的最大时间",
    )

    # MySQL 连接池配置
    mysql_pool_recycle: int = Field(
        default=3600,
        ge=60,
        le=86400,
        env="MYSQL_POOL_RECYCLE",
        description="MySQL 连接池回收时间（秒）",
    )

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
        default="file:storage/vectors.db",
        env="VECTOR_DB_URL",
        description="libsql 向量库连接地址（默认使用项目 storage/vectors.db）",
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
        default=320,
        ge=128,
        env="VECTOR_CHUNK_SIZE",
        description="章节分块的目标字数",
    )
    vector_chunk_overlap: int = Field(
        default=80,
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

    # -------------------- LLM Max Tokens 配置 --------------------
    # 小说系统
    llm_max_tokens_blueprint: int = Field(
        default=8192,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_BLUEPRINT",
        description="蓝图生成的最大输出tokens",
    )
    llm_max_tokens_chapter: int = Field(
        default=8192,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_CHAPTER",
        description="章节写作的最大输出tokens",
    )
    llm_max_tokens_outline: int = Field(
        default=4096,
        ge=1024,
        le=16384,
        env="LLM_MAX_TOKENS_OUTLINE",
        description="大纲生成的最大输出tokens",
    )
    llm_max_tokens_manga: int = Field(
        default=8192,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_MANGA",
        description="漫画分镜的最大输出tokens",
    )
    llm_max_tokens_analysis: int = Field(
        default=8192,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_ANALYSIS",
        description="分析任务的最大输出tokens",
    )
    llm_max_tokens_default: int = Field(
        default=4096,
        ge=512,
        le=16384,
        env="LLM_MAX_TOKENS_DEFAULT",
        description="默认最大输出tokens",
    )

    # 编程系统
    llm_max_tokens_coding_blueprint: int = Field(
        default=8192,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_CODING_BLUEPRINT",
        description="编程架构设计的最大输出tokens",
    )
    llm_max_tokens_coding_system: int = Field(
        default=8000,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_CODING_SYSTEM",
        description="编程系统生成的最大输出tokens",
    )
    llm_max_tokens_coding_module: int = Field(
        default=6000,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_CODING_MODULE",
        description="编程模块生成的最大输出tokens",
    )
    llm_max_tokens_coding_feature: int = Field(
        default=4000,
        ge=1024,
        le=16384,
        env="LLM_MAX_TOKENS_CODING_FEATURE",
        description="编程功能大纲的最大输出tokens",
    )
    llm_max_tokens_coding_prompt: int = Field(
        default=16384,
        ge=1024,
        le=32768,
        env="LLM_MAX_TOKENS_CODING_PROMPT",
        description="编程功能Prompt的最大输出tokens",
    )
    llm_max_tokens_coding_directory: int = Field(
        default=20000,
        ge=4096,
        le=32768,
        env="LLM_MAX_TOKENS_CODING_DIRECTORY",
        description="目录结构生成的最大输出tokens（大型项目需要较大值）",
    )

    # -------------------- Agent配置 --------------------
    agent_context_max_chars: int = Field(
        default=128000,
        ge=50000,
        le=500000,
        env="AGENT_CONTEXT_MAX_CHARS",
        description="Agent对话历史最大字符数，超过后触发压缩（基于128k上下文窗口）",
    )

    # -------------------- 功能开关 --------------------
    coding_project_enabled: bool = Field(
        default=False,
        env="CODING_PROJECT_ENABLED",
        description="是否启用编程项目(Prompt工程)功能，默认关闭",
    )

    # -------------------- 请求队列配置 --------------------
    llm_max_concurrent: int = Field(
        default=8,
        ge=1,
        le=20,
        env="LLM_MAX_CONCURRENT",
        description="LLM请求最大并发数（提高默认值以支持章节多版本并行生成）",
    )
    image_max_concurrent: int = Field(
        default=2,
        ge=1,
        le=5,
        env="IMAGE_MAX_CONCURRENT",
        description="图片生成请求最大并发数",
    )

    model_config = SettingsConfigDict(
        env_file=_resolve_env_files(),
        # 使用 utf-8-sig 兼容 Windows 记事本保存的 UTF-8 BOM（否则首行变量名会带 \ufeff，导致无法识别）。
        env_file_encoding="utf-8-sig",
        extra="ignore"
    )

    @model_validator(mode="after")
    def _validate_secret_key_for_production(self) -> "Settings":
        """生产环境强制要求显式 SECRET_KEY，避免误用桌面版默认密钥。"""
        normalized_env = (self.environment or "").strip().lower()
        if normalized_env in {"production", "prod"} and self.secret_key == self.DEFAULT_DESKTOP_SECRET_KEY:
            raise ValueError("生产环境必须通过环境变量 SECRET_KEY 显式配置，不能使用桌面版默认密钥")
        return self

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Optional[str]) -> Optional[str]:
        """当环境变量中提供 DATABASE_URL 时，原样返回，便于自定义。"""
        return value.strip() if isinstance(value, str) and value.strip() else value

    @field_validator("db_provider", mode="before")
    @classmethod
    def _normalize_db_provider(cls, value: Optional[str]) -> str:
        """统一数据库类型大小写，并限制为受支持的驱动。"""
        candidate = (value or "sqlite").strip().lower()
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
            # SQLite 固定使用 storage/afn.db，并转换为绝对路径以避免运行目录差异
            # 注意：parents[3] 指向项目根目录 E:\code\AFN，与 run_app.py 保持一致
            project_root = Path(__file__).resolve().parents[3]
            db_path = (project_root / "storage" / "afn.db").resolve()
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

    @property
    def storage_dir(self) -> Path:
        """存储目录根路径"""
        if getattr(sys, 'frozen', False):
            # 打包环境：存储在 exe 所在目录
            return Path(sys.executable).parent / "storage"
        else:
            # 开发环境：存储在项目根目录的 storage 目录，与 run_app.py 保持一致
            # parents[3] 指向项目根目录 E:\code\AFN
            return Path(__file__).resolve().parents[3] / "storage"

    @property
    def generated_images_dir(self) -> Path:
        """生成图片存储目录"""
        return self.storage_dir / "generated_images"

    @property
    def exports_dir(self) -> Path:
        """导出文件目录"""
        return self.storage_dir / "exports"


def _get_config_file_path() -> Path:
    """获取 config.json 配置文件路径（适配打包环境）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：配置保存到 exe 所在目录的 storage 文件夹
        work_dir = Path(sys.executable).parent
    else:
        # 开发环境：配置保存到项目根目录的 storage 文件夹
        # parents[3] 指向项目根目录 E:\code\AFN，与数据库路径保持一致
        work_dir = Path(__file__).resolve().parents[3]

    return work_dir / 'storage' / 'config.json'


def _load_json_config() -> dict:
    """加载 config.json 中的配置"""
    import json
    config_file = _get_config_file_path()
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _coerce_bool(value: object) -> bool:
    """将 config.json 中可能出现的各种真假值统一解析为 bool。"""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return bool(value)

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(text)


@lru_cache
def get_settings() -> Settings:
    """使用 LRU 缓存确保配置只初始化一次，减少 IO 与解析开销。

    启动时会从 config.json 加载用户保存的高级配置并覆盖默认值。
    """
    _preload_yaml_list_env_lines(_resolve_env_files())
    instance = Settings()

    # 从 config.json 加载用户保存的高级配置
    json_config = _load_json_config()
    if json_config:
        # 覆盖高级配置项（这些配置在设置页面中可修改）
        if 'writer_chapter_version_count' in json_config:
            instance.writer_chapter_versions = json_config['writer_chapter_version_count']
        if 'writer_parallel_generation' in json_config:
            instance.writer_parallel_generation = json_config['writer_parallel_generation']
        if 'part_outline_threshold' in json_config:
            instance.part_outline_threshold = json_config['part_outline_threshold']
        # 队列配置
        if 'llm_max_concurrent' in json_config:
            instance.llm_max_concurrent = json_config['llm_max_concurrent']
        if 'image_max_concurrent' in json_config:
            instance.image_max_concurrent = json_config['image_max_concurrent']

        # LLM Max Tokens 配置 - 小说系统
        if 'llm_max_tokens_blueprint' in json_config:
            instance.llm_max_tokens_blueprint = json_config['llm_max_tokens_blueprint']
        if 'llm_max_tokens_chapter' in json_config:
            instance.llm_max_tokens_chapter = json_config['llm_max_tokens_chapter']
        if 'llm_max_tokens_outline' in json_config:
            instance.llm_max_tokens_outline = json_config['llm_max_tokens_outline']
        if 'llm_max_tokens_manga' in json_config:
            instance.llm_max_tokens_manga = json_config['llm_max_tokens_manga']
        if 'llm_max_tokens_analysis' in json_config:
            instance.llm_max_tokens_analysis = json_config['llm_max_tokens_analysis']
        if 'llm_max_tokens_default' in json_config:
            instance.llm_max_tokens_default = json_config['llm_max_tokens_default']

        # LLM Max Tokens 配置 - 编程系统
        if 'llm_max_tokens_coding_blueprint' in json_config:
            instance.llm_max_tokens_coding_blueprint = json_config['llm_max_tokens_coding_blueprint']
        if 'llm_max_tokens_coding_system' in json_config:
            instance.llm_max_tokens_coding_system = json_config['llm_max_tokens_coding_system']
        if 'llm_max_tokens_coding_module' in json_config:
            instance.llm_max_tokens_coding_module = json_config['llm_max_tokens_coding_module']
        if 'llm_max_tokens_coding_feature' in json_config:
            instance.llm_max_tokens_coding_feature = json_config['llm_max_tokens_coding_feature']
        if 'llm_max_tokens_coding_prompt' in json_config:
            instance.llm_max_tokens_coding_prompt = json_config['llm_max_tokens_coding_prompt']
        if 'llm_max_tokens_coding_directory' in json_config:
            instance.llm_max_tokens_coding_directory = json_config['llm_max_tokens_coding_directory']

        # Agent配置
        if 'agent_context_max_chars' in json_config:
            instance.agent_context_max_chars = json_config['agent_context_max_chars']

        # 功能开关
        if 'coding_project_enabled' in json_config:
            instance.coding_project_enabled = json_config['coding_project_enabled']
        # auth_* 属于“部署/运行时开关”，优先遵循环境变量（含 .env 文件）。
        # 仅当环境中未显式配置时，才允许被 storage/config.json 覆盖。
        fields_set = getattr(instance, "model_fields_set", set()) or set()
        auth_enabled_explicit = (
            "auth_enabled" in fields_set
            or os.environ.get("AFN_AUTH_ENABLED") is not None
            or os.environ.get("AUTH_ENABLED") is not None
        )
        allow_registration_explicit = (
            "auth_allow_registration" in fields_set
            or os.environ.get("AFN_AUTH_ALLOW_REGISTRATION") is not None
            or os.environ.get("AUTH_ALLOW_REGISTRATION") is not None
        )

        if 'auth_enabled' in json_config and not auth_enabled_explicit:
            instance.auth_enabled = _coerce_bool(json_config['auth_enabled'])
        if 'auth_allow_registration' in json_config and not allow_registration_explicit:
            instance.auth_allow_registration = _coerce_bool(json_config['auth_allow_registration'])

    return instance


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
