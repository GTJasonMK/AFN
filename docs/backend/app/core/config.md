# backend/app/core/config.py - 应用全局配置

## 文件概述

这是 Arboris-Novel 的全局配置模块，采用 Pydantic Settings 实现类型安全的环境变量管理。所有可调参数集中于此，支持从环境变量和 `.env` 文件加载配置。

## 核心类

### Settings 类（第10-273行）

继承自 `pydantic_settings.BaseSettings`，提供类型安全的配置管理。

## 配置分类

### 1. 基础应用配置（第13-31行）

```python
app_name: str = "AI Novel Generator API"
environment: str = "development"
debug: bool = True
allow_registration: bool = True
logging_level: str = "INFO"
enable_linuxdo_login: bool = False
```

**字段说明：**
- `app_name`：FastAPI 文档标题
- `environment`：当前环境标识（development/production）
- `debug`：调试模式开关
- `allow_registration`：是否允许用户自助注册
- `logging_level`：应用日志级别（支持 CRITICAL/ERROR/WARNING/INFO/DEBUG/NOTSET）
- `enable_linuxdo_login`：是否启用 Linux.do OAuth 登录

### 2. 安全相关配置（第33-40行）

```python
secret_key: str = Field(..., env="SECRET_KEY")
jwt_algorithm: str = "HS256"
access_token_expire_minutes: int = 60 * 24 * 7  # 7天
```

**字段说明：**
- `secret_key`：**必填**，JWT 加密密钥
- `jwt_algorithm`：JWT 加密算法
- `access_token_expire_minutes`：访问令牌过期时间（分钟）

### 3. 数据库配置（第42-57行）

```python
database_url: Optional[str] = None  # 完整连接串
db_provider: str = "mysql"  # mysql 或 sqlite
mysql_host: str = "localhost"
mysql_port: int = 3306
mysql_user: str = "root"
mysql_password: str = ""
mysql_database: str = "arboris"
```

**配置逻辑：**
1. 优先使用 `database_url`（如果提供）
2. 否则根据 `db_provider` 选择：
   - `mysql`：使用 MySQL 配置参数
   - `sqlite`：使用固定路径 `storage/arboris.db`

### 4. 管理员初始化配置（第59-62行）

```python
admin_default_username: str = "admin"
admin_default_password: str = "ChangeMe123!"
admin_default_email: Optional[str] = None
```

用于首次启动时创建默认管理员账户（桌面版使用 `desktop_user`）。

### 5. LLM 相关配置（第64-161行）

#### 基础 LLM 配置
```python
openai_api_key: Optional[str] = None
openai_base_url: Optional[HttpUrl] = None
openai_model_name: str = "gpt-4o-mini"
```

#### 写作配置
```python
writer_chapter_versions: int = 2  # 每次生成的候选版本数
writer_parallel_generation: bool = True  # 是否并行生成
writer_max_parallel_requests: int = 3  # 最大并发数
```

#### 嵌入模型配置
```python
embedding_provider: str = "openai"  # openai 或 ollama
embedding_base_url: Optional[AnyUrl] = None
embedding_api_key: Optional[str] = None
embedding_model: str = "text-embedding-3-large"
embedding_model_vector_size: Optional[int] = None  # 自动检测
```

#### Ollama 配置
```python
ollama_embedding_base_url: Optional[AnyUrl] = None
ollama_embedding_model: str = "nomic-embed-text:latest"
```

#### 向量数据库配置
```python
vector_db_url: Optional[str] = None  # libsql 连接地址
vector_db_auth_token: Optional[str] = None
vector_top_k_chunks: int = 5  # 剧情检索数量
vector_top_k_summaries: int = 3  # 摘要检索数量
vector_chunk_size: int = 480  # 分块字数
vector_chunk_overlap: int = 120  # 重叠字数
```

### 6. Linux.do OAuth 配置（第163-179行）

```python
linuxdo_client_id: Optional[str] = None
linuxdo_client_secret: Optional[str] = None
linuxdo_redirect_uri: Optional[HttpUrl] = None
linuxdo_auth_url: Optional[HttpUrl] = None
linuxdo_token_url: Optional[HttpUrl] = None
linuxdo_user_info_url: Optional[HttpUrl] = None
```

### 7. 邮件配置（第181-186行）

```python
smtp_server: Optional[str] = None
smtp_port: int = 587
smtp_username: Optional[str] = None
smtp_password: Optional[str] = None
email_from: Optional[str] = None
```

## 验证器（Validators）

### 1. `_normalize_database_url`（第194-197行）

验证并规范化 `database_url`，去除首尾空格。

### 2. `_normalize_db_provider`（第199-205行）

**功能：**
- 统一数据库类型大小写
- 限制为 `mysql` 或 `sqlite`
- 抛出异常如果值无效

### 3. `_normalize_embedding_provider`（第206-212行）

**功能：**
- 限制嵌入模型提供方为 `openai` 或 `ollama`

### 4. `_normalize_logging_level`（第214-221行）

**功能：**
- 规范日志级别为大写
- 验证值在有效范围内：`CRITICAL`、`ERROR`、`WARNING`、`INFO`、`DEBUG`、`NOTSET`

## 属性方法（Properties）

### 1. `sqlalchemy_database_uri`（第223-254行）

**功能：** 生成 SQLAlchemy 兼容的异步连接串

**逻辑流程：**
```python
if self.database_url:
    # 使用提供的完整连接串（规范化后）
    return normalized_url
elif self.db_provider == "sqlite":
    # SQLite: storage/arboris.db (绝对路径)
    return f"sqlite+aiosqlite:///{db_path}"
else:
    # MySQL: 对密码进行 URL 编码
    return f"mysql+asyncmy://{user}:{encoded_pwd}@{host}:{port}/{db}"
```

**重要特性：**
- 自动对 MySQL 密码进行 URL 编码（避免特殊字符问题）
- SQLite 使用绝对路径（避免工作目录差异）
- 统一使用异步驱动（`aiosqlite`、`asyncmy`）

### 2. `is_sqlite_backend`（第256-259行）

**功能：** 判断当前数据库是否为 SQLite

```python
return make_url(self.sqlalchemy_database_uri).get_backend_name() == "sqlite"
```

用于差异化初始化流程（如连接池配置）。

### 3. `vector_store_enabled`（第261-264行）

**功能：** 判断是否已配置向量库

```python
return bool(self.vector_db_url)
```

## 配置加载

### `get_settings()` 函数（第267-270行）

```python
@lru_cache
def get_settings() -> Settings:
    """使用 LRU 缓存确保配置只初始化一次，减少 IO 与解析开销。"""
    return Settings()
```

**特性：**
- 使用 `@lru_cache` 装饰器
- 确保单例模式
- 减少重复解析开销

### 全局实例（第273行）

```python
settings = get_settings()
```

应用中通过 `from backend.app.core.config import settings` 导入使用。

## Pydantic 配置（第188-192行）

```python
model_config = SettingsConfigDict(
    env_file=("new-backend/.env", ".env", "backend/.env"),
    env_file_encoding="utf-8",
    extra="ignore"
)
```

**说明：**
- `env_file`：按顺序查找环境变量文件
- `env_file_encoding`：UTF-8 编码
- `extra="ignore"`：忽略未定义的字段

## 使用示例

### 1. 基础使用

```python
from backend.app.core.config import settings

# 获取配置
api_key = settings.openai_api_key
debug_mode = settings.debug
db_uri = settings.sqlalchemy_database_uri
```

### 2. 判断功能开关

```python
# 判断向量库是否启用
if settings.vector_store_enabled:
    vector_store = VectorStoreService()
```

### 3. 数据库类型判断

```python
# 根据数据库类型调整配置
if settings.is_sqlite_backend:
    engine_kwargs.update(poolclass=NullPool)
else:
    engine_kwargs.update(pool_pre_ping=True)
```

## 环境变量示例

```.env
# 基础配置
APP_NAME=My Novel Generator
DEBUG=true
LOGGING_LEVEL=DEBUG

# 安全配置
SECRET_KEY=your-secret-key-here

# 数据库配置（方式1：使用完整URL）
DATABASE_URL=mysql+asyncmy://user:pass@localhost:3306/arboris

# 数据库配置（方式2：使用独立参数）
DB_PROVIDER=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-password
MYSQL_DATABASE=arboris

# LLM 配置
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o-mini

# 写作配置
WRITER_CHAPTER_VERSION_COUNT=3
WRITER_PARALLEL_GENERATION=true
WRITER_MAX_PARALLEL_REQUESTS=5

# 向量库配置
VECTOR_DB_URL=libsql://your-db-url
VECTOR_DB_AUTH_TOKEN=your-token
```

## 注意事项

1. **SECRET_KEY 必填：** 应用启动时会验证，未提供将抛出异常
2. **数据库密码编码：** MySQL 密码会自动 URL 编码，支持特殊字符
3. **SQLite 路径：** 使用绝对路径，确保多进程一致性
4. **配置缓存：** 配置对象使用单例模式，修改配置需重启应用
5. **类型安全：** 所有配置项都有明确的类型注解和验证
6. **向量库可选：** 未配置时自动降级为非 RAG 模式

## 相关文件

- `backend/.env.example` - 环境变量模板
- `backend/app/db/session.py` - 使用数据库配置
- `backend/app/main.py` - 应用启动时加载配置
- `backend/app/services/llm_service.py` - 使用 LLM 配置