
# LLM Service - LLM交互服务

## 文件概述

**文件路径**: `backend/app/services/llm_service.py`  
**代码行数**: 406行  
**核心职责**: 封装与大语言模型（LLM）的所有交互逻辑，包括配额控制、配置选择、流式响应收集、向量生成等功能

## 核心功能

### 1. LLM响应获取

提供统一的LLM调用接口，支持流式收集、自动重试、配额管理：

```python
async def get_llm_response(
    self,
    system_prompt: str,
    conversation_history: List[Dict[str, str]],
    *,
    temperature: float = 0.7,
    user_id: Optional[int] = None,
    timeout: float = 300.0,
    response_format: Optional[str] = "json_object",
    max_tokens: Optional[int] = None,
    skip_usage_tracking: bool = False,
    skip_daily_limit_check: bool = False,
    cached_config: Optional[Dict[str, Optional[str]]] = None,
) -> str
```

**功能特点**：
- 支持系统提示词和对话历史
- 可自定义温度、超时、响应格式
- 支持跳过使用量统计（用于并发模式）
- 支持缓存配置（避免并发数据库查询）

**使用示例**：
```python
# 基本用法
response = await llm_service.get_llm_response(
    system_prompt="你是一个专业的小说写作助手",
    conversation_history=[
        {"role": "user", "content": "请帮我写一个开头"}
    ],
    temperature=0.8,
    user_id=user_id
)

# 并发模式（使用缓存配置）
config = await llm_service._resolve_llm_config(user_id)
tasks = [
    llm_service.get_llm_response(
        system_prompt=prompt,
        conversation_history=history,
        skip_usage_tracking=True,
        skip_daily_limit_check=True,
        cached_config=config
    )
    for prompt, history in batch_data
]
results = await asyncio.gather(*tasks)
```

### 2. 流式响应收集（核心实现）

[`_stream_and_collect()`](backend/app/services/llm_service.py:85) 是LLM调用的核心方法，实现了流式收集和自动重试机制：

```python
async def _stream_and_collect(
    self,
    messages: List[Dict[str, str]],
    *,
    temperature: float,
    user_id: Optional[int],
    timeout: float,
    response_format: Optional[str] = None,
    max_tokens: Optional[int] = None,
    max_retries: int = 2,
    skip_usage_tracking: bool = False,
    skip_daily_limit_check: bool = False,
    cached_config: Optional[Dict[str, Optional[str]]] = None,
) -> str
```

**重试机制**：
- 默认最多重试2次（总共3次尝试）
- 指数退避：第1次等待2秒，第2次等待4秒
- 仅对网络错误重试，内部错误直接抛出

**错误处理**：
```python
# 内部错误（不重试）
except InternalServerError as exc:
    detail = "AI 服务内部错误，请稍后重试"
    raise HTTPException(status_code=503, detail=detail)

# 网络错误（自动重试）
except (httpx.RemoteProtocolError, httpx.ReadTimeout, APIConnectionError, APITimeoutError) as exc:
    if attempt < max_retries:
        wait_time = 2 ** (attempt + 1)
        await asyncio.sleep(wait_time)
        continue
    raise HTTPException(status_code=503, detail=f"{detail}，请稍后重试")
```

**响应收集模式**：
```python
# 使用LLMClient统一收集
result = await client.stream_and_collect(
    messages=chat_messages,
    model=config.get("model"),
    temperature=temperature,
    timeout=int(timeout),
    response_format=response_format,
    max_tokens=max_tokens,
    collect_mode=ContentCollectMode.CONTENT_ONLY,  # 仅收集内容，过滤思考过程
)

# 检查完成原因
if result.finish_reason == "length":
    raise HTTPException(status_code=500, detail="AI 响应被截断，请缩短输入或调整参数")

if not result.content:
    raise HTTPException(status_code=500, detail="AI 未返回有效内容")
```

### 3. 章节摘要生成

专门用于生成章节摘要的方法，使用较低温度确保摘要质量：

```python
async def get_summary(
    self,
    chapter_content: str,
    *,
    temperature: float = 0.2,
    user_id: Optional[int] = None,
    timeout: float = 180.0,
    system_prompt: Optional[str] = None,
) -> str
```

**使用示例**：
```python
# 使用默认提示词
summary = await llm_service.get_summary(
    chapter_content="第一章内容...",
    user_id=user_id
)

# 使用自定义提示词
custom_summary = await llm_service.get_summary(
    chapter_content="第一章内容...",
    system_prompt="请用100字以内概括以下内容的核心要点：",
    temperature=0.1
)
```

### 4. LLM配置解析

[`_resolve_llm_config()`](backend/app/services/llm_service.py:267) 负责解析用户或系统的LLM配置：

```python
async def _resolve_llm_config(
    self, 
    user_id: Optional[int], 
    skip_daily_limit_check: bool = False
) -> Dict[str, Optional[str]]
```

**配置优先级**：
1. **用户自定义配置**（如果存在且有效）
2. **系统默认配置**（从数据库读取）
3. **环境变量**（兼容旧版本）

**实现逻辑**：
```python
if user_id:
    # 1. 尝试获取用户的激活配置
    config = await self.llm_repo.get_active_config(user_id)
    
    if config and config.llm_provider_api_key:
        return {
            "api_key": config.llm_provider_api_key,
            "base_url": config.llm_provider_url,
            "model": config.llm_provider_model,
        }

# 2. 检查每日使用次数限制（仅在非跳过模式下）
if user_id and not skip_daily_limit_check:
    await self._enforce_daily_limit(user_id)

# 3. 使用系统默认配置
api_key = await self._get_config_value("llm.api_key")
base_url = await self._get_config_value("llm.base_url")
model = await self._get_config_value("llm.model")

return {"api_key": api_key, "base_url": base_url, "model": model}
```

### 5. 向量生成（RAG支持）

支持OpenAI和Ollama两种向量生成方式：

```python
async def get_embedding(
    self,
    text: str,
    *,
    user_id: Optional[int] = None,
    model: Optional[str] = None,
) -> List[float]
```

**双提供商支持**：
```python
provider = settings.embedding_provider

if provider == "ollama":
    # Ollama本地嵌入
    client = OllamaAsyncClient(host=base_url)
    response = await client.embeddings(model=target_model, prompt=text)
    embedding = response.get("embedding") or getattr(response, "embedding", None)
else:
    # OpenAI API嵌入
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    response = await client.embeddings.create(
        input=text,
        model=target_model,
    )
    embedding = response.data[0].embedding

# 缓存向量维度
dimension = len(embedding)
if dimension:
    self._embedding_dimensions[target_model] = dimension
```

**使用示例**：
```python
# OpenAI向量生成
embedding = await llm_service.get_embedding(
    text="第一章内容摘要...",
    user_id=user_id
)

# Ollama本地向量生成
# 配置: EMBEDDING_PROVIDER=ollama
# OLLAMA_EMBEDDING_MODEL=nomic-embed-text
embedding = await llm_service.get_embedding(
    text="章节内容",
    model="nomic-embed-text"
)

# 获取向量维度
dimension = llm_service.get_embedding_dimension()  # 从缓存或配置获取
```

### 6. 每日限额管理

[`_enforce_daily_limit()`](backend/app/services/llm_service.py:388) 实现每日请求次数限制：

```python
async def _enforce_daily_limit(self, user_id: int) -> None:
    # 从管理员设置中获取限额
    limit_str = await self.admin_setting_service.get("daily_request_limit", "100")
    limit = int(limit_str or 10)
    
    # 获取今日已使用次数
    used = await self.user_repo.get_daily_request(user_id)
    
    # 检查是否超限
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="今日请求次数已达上限，请明日再试或设置自定义 API Key。",
        )
    
    # 增加使用次数
    await self.user_repo.increment_daily_request(user_id)
    await self.session.commit()
```

**绕过限额的方式**：
1. 用户配置自己的API Key
2. 在并发模式下使用 `skip_daily_limit_check=True`

## 依赖关系

### 内部依赖
- [`LLMConfigRepository`](backend/app/repositories/llm_config_repository.py) - 用户LLM配置管理
- [`SystemConfigRepository`](backend/app/repositories/system_config_repository.py) - 系统配置管理
- [`UserRepository`](backend/app/repositories/user_repository.py) - 用户数据管理
- [`AdminSettingService`](backend/app/services/admin_setting_service.py) - 管理员设置
- [`PromptService`](backend/app/services/prompt_service.py) - 提示词服务
- [`UsageService`](backend/app/services/usage_service.py) - 使用统计服务

### 外部依赖
- `openai.AsyncOpenAI` - OpenAI官方SDK
- `ollama.AsyncClient` - Ollama本地模型客户端（可选）
- `httpx` - HTTP客户端（用于错误处理）
- [`LLMClient`](backend/app/utils/llm_tool.py) - 统一的LLM客户端工具

### 工具类
- [`ChatMessage`](backend/app/utils/llm_tool.py) - 聊天消息格式转换
- [`ContentCollectMode`](backend/app/utils/llm_tool.py) - 内容收集模式枚举

## 配置管理

### 系统配置键
```python
# 从数据库或环境变量读取
api_key = await self._get_config_value("llm.api_key")      # LLM_API_KEY
base_url = await self._get_config_value("llm.base_url")    # LLM_BASE_URL
model = await self._get_config_value("llm.model")          # LLM_MODEL
```

### 向量配置
```python
# 从settings读取
provider = settings.embedding_provider                      # openai/ollama
embedding_model = settings.embedding_model                  # text-embedding-3-small
ollama_model = settings.ollama_embedding_model              # nomic-embed-text
embedding_api_key = settings.embedding_api_key              # 向量API Key
embedding_base_url = settings.embedding_base_url            # 向量API URL
vector_size = settings.embedding_model_vector_size          # 向量维度
```

## 并发优化

### 并发调用最佳实践

在批量生成章节时，可以使用配置缓存和跳过标志来优化性能：

```python
# 1. 预先获取配置（避免重复数据库查询）
config = await llm_service._resolve_llm_config(
    user_id, 
    skip_daily_limit_check=True
)

# 2. 只检查一次每日限额
await llm_service._enforce_daily_limit(user_id)

# 3. 并发生成（使用缓存配置）
tasks = []
for version_idx in range(num_versions):
    task = llm_service.get_llm_response(
        system_prompt=writing_prompt,
        conversation_history=history,
        temperature=0.7,
        user_id=user_id,
        skip_usage_tracking=True,        # 跳过API计数（避免并发session冲突）
        skip_daily_limit_check=True,     # 