# LLM Config Service - LLM配置管理服务

## 文件概述

**文件路径**: `backend/app/services/llm_config_service.py`  
**代码行数**: 436行  
**核心职责**: 用户自定义LLM配置的CRUD管理、配置测试、激活切换、导入导出等完整配置生命周期管理

## 核心功能

### 1. 配置列表管理

```python
async def list_configs(self, user_id: int) -> list[LLMConfigRead]
async def get_config(self, config_id: int, user_id: int) -> LLMConfigRead
async def get_active_config(self, user_id: int) -> Optional[LLMConfigRead]
```

**使用示例**：
```python
config_service = LLMConfigService(session)

# 获取所有配置
configs = await config_service.list_configs(user_id=1)

# 获取激活配置
active = await config_service.get_active_config(user_id=1)
```

### 2. 配置创建与更新

```python
async def create_config(self, user_id: int, payload: LLMConfigCreate) -> LLMConfigRead
async def update_config(self, config_id: int, user_id: int, payload: LLMConfigUpdate) -> LLMConfigRead
```

**特性**：
- 第一个配置自动激活
- 更新关键字段后重置验证状态
- 自动检查配置名重复

### 3. 配置测试

```python
async def test_config(self, config_id: int, user_id: int) -> LLMConfigTestResponse
```

**测试特性**：
- 严格模式，不回退到环境变量
- 浏览器模拟，绕过Cloudflare
- WITH_REASONING模式兼容DeepSeek R1
- 详细日志记录

**使用示例**：
```python
result = await config_service.test_config(config_id=1, user_id=1)
if result.success:
    print(f"响应时间: {result.response_time_ms} ms")
```

### 4. 配置导入导出

```python
async def export_config(self, config_id: int, user_id: int) -> dict
async def export_all_configs(self, user_id: int) -> dict
async def import_configs(self, user_id: int, import_data: dict) -> dict
```

**导入特性**：
- 自动处理重名（添加数字后缀）
- 导入的配置默认不激活
- 需要重新测试验证

## 完整使用流程

### 首次配置

```python
# 1. 创建配置（自动激活）
config = await config_service.create_config(
    user_id=1,
    payload=LLMConfigCreate(
        config_name="OpenAI GPT-4",
        llm_provider_url="https://api.openai.com/v1",
        llm_provider_api_key="sk-xxxx",
        llm_provider_model="gpt-4"
    )
)

# 2. 测试配置
test_result = await config_service.test_config(config.id, user_id=1)
```

### 多配置管理

```python
# 添加第二个配置
config2 = await config_service.create_config(user_id=1, payload=...)

# 切换配置
await config_service.activate_config(config_id=config2.id, user_id=1)

# 删除旧配置
await config_service.delete_config(config_id=config1.id, user_id=1)
```

### 配置迁移

```python
# 导出
export_data = await config_service.export_all_configs(user_id=1)

# 导入到新账户
result = await config_service.import_configs(user_id=2, import_data=export_data)
```

## 依赖关系

- [`LLMConfigRepository`](../repositories/llm_config_repository.md) - 数据库操作
- [`LLMClient`](../utils/llm_tool.md) - LLM调用工具
- [`LLMConfig`](../models/llm_config.md) - 数据模型

## 相关文件

- **数据模型**: `backend/app/models/llm_config.py`
- **仓储层**: `backend/app/repositories/llm_config_repository.py`
- **Schema**: `backend/app/schemas/llm_config.py`
- **API路由**: `backend/app/api/routers/llm_config.py`