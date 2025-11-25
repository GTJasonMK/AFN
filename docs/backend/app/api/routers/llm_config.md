
# backend/app/api/routers/llm_config.py - LLM 配置管理 API

## 文件概述

提供 LLM（大语言模型）配置的完整管理接口，包括配置的增删改查、激活切换、连接测试、导入导出等功能。用户可以管理多个 LLM 配置并在它们之间切换。

**文件路径：** `backend/app/api/routers/llm_config.py`  
**代码行数：** 167 行  
**复杂度：** ⭐⭐⭐ 中等

## 核心功能

### 1. 路由定义

```python
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/llm-configs",
    tags=["LLM Configuration"]
)
```

**路由前缀：** `/api/llm-configs`  
**标签：** LLM Configuration

### 2. 依赖注入

```python
def get_llm_config_service(
    session: AsyncSession = Depends(get_session)
) -> LLMConfigService:
    return LLMConfigService(session)
```

## API 端点列表

### 配置管理接口

| 方法 | 路径 | 功能 | 响应模型 |
|------|------|------|----------|
| GET | `/api/llm-configs` | 获取配置列表 | `list[LLMConfigRead]` |
| GET | `/api/llm-configs/active` | 获取激活的配置 | `LLMConfigRead` |
| GET | `/api/llm-configs/{config_id}` | 获取单个配置 | `LLMConfigRead` |
| POST | `/api/llm-configs` | 创建新配置 | `LLMConfigRead` |
| PUT | `/api/llm-configs/{config_id}` | 更新配置 | `LLMConfigRead` |
| POST | `/api/llm-configs/{config_id}/activate` | 激活配置 | `LLMConfigRead` |
| DELETE | `/api/llm-configs/{config_id}` | 删除配置 | `204 No Content` |
| POST | `/api/llm-configs/{config_id}/test` | 测试配置 | `LLMConfigTestResponse` |

### 导入导出接口

| 方法 | 路径 | 功能 | 响应 |
|------|------|------|------|
| GET | `/api/llm-configs/{config_id}/export` | 导出单个配置 | JSON 文件下载 |
| GET | `/api/llm-configs/export` | 导出所有配置 | `list[dict]` |
| POST | `/api/llm-configs/import` | 导入配置 | 导入结果 |

## API 详解

### 1. 获取配置列表

```python
@router.get("", response_model=list[LLMConfigRead])
async def list_llm_configs(
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> list[LLMConfigRead]:
    """获取用户的所有LLM配置列表。"""
    return await service.list_configs(desktop_user.id)
```

**请求示例：**
```bash
GET /api/llm-configs
```

**响应示例：**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "config_name": "OpenAI GPT-4",
    "llm_provider_url": "https://api.openai.com/v1",
    "llm_provider_model": "gpt-4",
    "is_active": true,
    "is_verified": true,
    "test_status": "success",
    "created_at": "2025-01-01T00:00:00Z"
  },
  {
    "id": 2,
    "config_name": "Claude 3",
    "is_active": false,
    "is_verified": false
  }
]
```

### 2. 获取激活的配置

```python
@router.get("/active", response_model=LLMConfigRead)
async def get_active_config(
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """获取用户当前激活的LLM配置。"""
    config = await service.get_active_config(desktop_user.id)
    if not config:
        raise HTTPException(status_code=404, detail="没有激活的配置")
    return config
```

**请求示例：**
```bash
GET /api/llm-configs/active
```

**响应示例：**
```json
{
  "id": 1,
  "config_name": "OpenAI GPT-4",
  "llm_provider_url": "https://api.openai.com/v1",
  "llm_provider_api_key": "sk-***",
  "llm_provider_model": "gpt-4",
  "is_active": true,
  "is_verified": true
}
```

**错误响应：**
```json
{
  "detail": "没有激活的配置"
}
```

### 3. 获取指定配置

```python
@router.get("/{config_id}", response_model=LLMConfigRead)
async def get_llm_config_by_id(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """获取指定ID的LLM配置。"""
    return await service.get_config(config_id, desktop_user.id)
```

**请求示例：**
```bash
GET /api/llm-configs/1
```

### 4. 创建配置

```python
@router.post("", response_model=LLMConfigRead, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    payload: LLMConfigCreate,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """创建新的LLM配置。"""
    return await service.create_config(desktop_user.id, payload)
```

**请求示例：**
```bash
POST /api/llm-configs
Content-Type: application/json

{
  "config_name": "我的 GPT-4 配置",
  "llm_provider_url": "https://api.openai.com/v1",
  "llm_provider_api_key": "sk-xxxxxxxxxxxx",
  "llm_provider_model": "gpt-4"
}
```

**响应示例：**
```json
{
  "id": 3,
  "user_id": 1,
  "config_name": "我的 GPT-4 配置",
  "llm_provider_url": "https://api.openai.com/v1",
  "llm_provider_model": "gpt-4",
  "is_active": false,
  "is_verified": false,
  "created_at": "2025-01-01T12:00:00Z"
}
```

### 5. 更新配置

```python
@router.put("/{config_id}", response_model=LLMConfigRead)
async def update_llm_config(
    config_id: int,
    payload: LLMConfigUpdate,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """更新指定ID的LLM配置。"""
    return await service.update_config(config_id, desktop_user.id, payload)
```

**请求示例：**
```bash
PUT /api/llm-configs/3
Content-Type: application/json

{
  "config_name": "更新后的配置名称",
  "llm_provider_model": "gpt-4-turbo"
}
```

### 6. 激活配置

```python
@router.post("/{config_id}/activate", response_model=LLMConfigRead)
async def activate_llm_config(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigRead:
    """激活指定ID的LLM配置。"""
    return await service.activate_config(config_id, desktop_user.id)
```

**功能说明：**
- 激活指定配置
- 自动停用其他配置（同一用户只能有一个激活配置）
- 后续 AI 调用将使用此配置

**请求示例：**
```bash
POST /api/llm-configs/3/activate
```

**响应示例：**
```json
{
  "id": 3,
  "config_name": "我的配置",
  "is_active": true,
  "is_verified": true
}
```

### 7. 删除配置

```python
@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_llm_config_by_id(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> None:
    """删除指定ID的LLM配置。"""
    await service.delete_config(config_id, desktop_user.id)
```

**请求示例：**
```bash
DELETE /api/llm-configs/3
```

**响应：**
- 状态码：`204 No Content`
- 无响应体

### 8. 测试配置

```python
@router.post("/{config_id}/test", response_model=LLMConfigTestResponse)
async def test_llm_config(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> LLMConfigTestResponse:
    """测试指定ID的LLM配置是否可用。"""
    return await service.test_config(config_id, desktop_user.id)
```

**功能说明：**
- 测试 API 连接是否正常
- 验证 API Key 是否有效
- 检查模型是否可用

**请求示例：**
```bash
POST /api/llm-configs/1/test
```

**成功响应：**
```json
{
  "success": true,
  "message": "连接成功",
  "test_time": "2025-01-01T12:00:00Z",
  "response_time_ms": 234
}
```

**失败响应：**
```json
{
  "success": false,
  "message": "API Key 无效",
  "error": "Incorrect API key provided"
}
```

## 导入导出功能

### 1. 导出单个配置

```python
@router.get("/{config_id}/export")
async def export_llm_config(
    config_id: int,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出单个LLM配置为JSON文件。"""
    export_data = await service.export_config(config_id, desktop_user.id)
    
    from fastapi.responses import JSONResponse
    filename = f"llm_config_{config_id}.json"
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
```

**请求示例：**
```bash
GET /api/llm-configs/1/export
```

**响应：**
- 自动下载 `llm_config_1.json` 文件
- Content-Type: `application/json`
- Content-Disposition: `attachment; filename="llm_config_1.json"`

**导出格式：**
```json
{
  "version": "1.0",
  "config_name": "OpenAI GPT-4",
  "llm_provider_url": "https://api.openai.com/v1",
  "llm_provider_api_key": "sk-***",
  "llm_provider_model": "gpt-4",
  "exported_at": "2025-01-01T12:00:00Z"
}
```

### 2. 导出所有配置

```python
@router.get("/export", response_model=list[dict])
async def export_all_llm_configs(
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导出用户的所有LLM配置为JSON列表。"""
    return await service.export_all_configs(desktop_user.id)
```

**请求示例：**
```bash
GET /api/llm-configs/export
```

**响应示例：**
```json
[
  {
    "config_name": "OpenAI GPT-4",
    "llm_provider_url": "https://api.openai.com/v1",
    "llm_provider_model": "gpt-4"
  },
  {
    "config_name": "Claude 3",
    "llm_provider_url": "https://api.anthropic.com/v1",
    "llm_provider_model": "claude-3-opus-20240229"
  }
]
```

### 3. 导入配置

```python
@router.post("/import")
async def import_llm_configs(
    import_data: dict,
    service: LLMConfigService = Depends(get_llm_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """导入LLM配置数据（需符合LLMConfigExportData格式）。"""
    return await service.import_configs(desktop_user.id, import_data)
```

**请求示例：**
```bash
POST /api/llm-configs/import
Content-Type: application/json

{
  "version": "1.0",
  "configs": [
    {
      "config_name": "导入的配置",
      "llm_provider_url": "https://api.openai.com/v1",
      "llm_provider_api_key": "sk-xxx",
      "llm_provider_model": "gpt-4"
    }
  ]
}
```

**响应示例：**
```json
{
  "success": true,
  "imported_count": 1,
  "message": "成功导入 1 个配置"
}
```

## 使用场景

### 场景 1：初次配置 LLM

```python
# 1. 创建配置
response = await client.post("/api/llm-configs", json={
    "config_name": "我的 GPT-4",
    "llm_provider_url": "https://api.openai.com/v1",
    "llm_provider_api_key": "sk-xxx",
    "llm_provider_model": "gpt-4"
})
config_id = response.json()["id"]

# 2. 测试配置
test_result = await client.post(f"/api/llm-configs/{config_id}/test")
if test_result.json()["success"]:
    # 3. 激活配置
    await client.post(f"/api/llm-configs/{config_id}/activate")
```

### 场景 2：切换 LLM 配置

```python
# 1. 查看所有配置
configs = await client.get("/api/llm-configs")

# 2. 选择并激活
await client.post(f"/api/llm-configs/{selected_id}/activate")

# 3. 验证激活
active_config = await client.get("/api/llm-configs/active")
```

### 场景 3：备份和恢复配置

```python
# 导出所有配置
configs = await client.get("/api/llm-configs/export")
save_to_file("backup.json", configs.json())

# 导入配置
with open("backup.json") as f:
    data = json.load(f)
await client.post("/api/llm-configs/import", json=data)
```

## 数据模型

### LLMConfigCreate

```python
class LLMConfigCreate(BaseModel):
    config_name: str
    llm_provider_url: Optional[str] = None
    llm_provider_api_key: Optional[str] = None
    llm_provider_model: Optional[str] = None
```

### LLMConfigUpdate

```python
class LLMConfigUpdate(BaseModel):
    config_name: Optional[str] = None
    llm_provider_url: Optional[str] = None
    llm_provider_api_key: Optional[str] = None
    llm_provider_model: Optional[str] = None
```

### LLMConfigRead

```python
class LLMConfigRead(BaseModel):
    id: int
    user_id: int
    config_name: str
    llm_provider_url: Optional[str]
    llm_provider_model: Optional[str]
    is_active: bool
    is_verified: bool
    test_status: Optional[str]
    created_at: datetime
```

### LLMConfigTestResponse

```python
class LLMConfigTestResponse(BaseModel):
    success: bool
    message: str
    test_time: Optional[datetime]
    response_time_ms: Optional[int]
    error: Optional[str]
```

## 日志记录

所有操作都会记录日志：

```python
logger.info("用户 %s 查询 LLM 配置列表", desktop_user.id)
logger.info("用户 %s 创建 LLM 配置: %s", desktop_user.id, payload.config_name)
logger.info("用户 %s 激活 LLM 配置 ID=%s", desktop_user.id, config_id)
logger.warning("用户 %s 没有激活的 LLM 配置", desktop_user.id)
```

## 相关文件

### 服务层
- [`backend/app/services/llm_config_service.py`](../../services/llm_config_service.md) - LLM 配置业务逻辑

### 数据模型
- [`backend/app/models/llm_config.py`](../../models/llm_config.md) - LLM 配置模型
- [`backend/app/schemas/llm_config.py`](../../schemas/llm_config.md) - LLM 配置 Schema

### 依赖注入
- [`backend/app/core/dependencies.py`](../../core/dependencies.md) - 默认用户获取
- [`backend/app/db/session.py`](../../db/session.md) - 数据库会话

### 路由聚合
- [`backend/app/api/routers/__init__.py`](__init__.md) - API 路由聚合

## 注意事项

