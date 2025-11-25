# Schemas - 数据传输对象层

## 概述

Schema层使用Pydantic定义数据传输对象(DTO)，负责：
- API请求/响应的数据验证
- 数据序列化/反序列化
- 数据格式转换和掩码处理

## Schema文件列表

### 1. **config.py** - 系统配置Schema
- `SystemConfigBase` - 基础配置模型
- `SystemConfigCreate` - 创建配置
- `SystemConfigUpdate` - 更新配置（部分更新）
- `SystemConfigRead` - 读取配置

### 2. **llm_config.py** - LLM配置Schema
- `LLMConfigBase` - LLM配置基础
- `LLMConfigCreate` - 创建配置
- `LLMConfigUpdate` - 更新配置
- `LLMConfigRead` - 读取配置（API Key自动掩码）
- `LLMConfigTestResponse` - 测试结果
- `LLMConfigExport/Import` - 导入导出

**特殊功能**：
```python
def mask_api_key(api_key: str) -> str:
    """API Key掩码：sk-abc***xyz"""
    return f"{api_key[:8]}{'*' * (len(api_key) - 12)}{api_key[-4:]}"
```

### 3. **novel.py** - 小说项目Schema (312行)
最复杂的Schema文件，包含：

**核心模型**：
- `Blueprint` - 蓝图（世界观、角色、大纲）
- `Chapter` - 章节（含多版本）
- `PartOutline` - 分层大纲（长篇小说）
- `NovelProject` - 完整项目

**请求模型**：
- `GenerateChapterRequest` - 生成章节
- `GeneratePartOutlinesRequest` - 生成部分大纲
- `BatchGenerateChaptersRequest` - 批量并发生成
- `BlueprintRefineRequest` - 蓝图优化

**枚举类型**：
- `ChapterGenerationStatus` - 章节状态
- `PartOutlineStatus` - 部分大纲状态
- `NovelSectionType` - 章节类型

### 4. **prompt.py** - 提示词Schema
- `PromptBase` - 基础提示词
- `PromptCreate` - 创建提示词
- `PromptUpdate` - 更新提示词
- `PromptRead` - 读取提示词（自动处理标签分割）

**特殊处理**：
```python
# 标签自动分割：字符串 -> 列表
"tag1,tag2,tag3" -> ["tag1", "tag2", "tag3"]
```

### 5. **user.py** - 用户Schema
- `UserBase` - 用户基础
- `UserCreate` - 创建用户
- `UserUpdate` - 更新用户
- `User` - 用户信息
- `UserInDB` - 数据库用户（含密码哈希）
- `Token` - JWT令牌
- `UserRegistration` - 注册（含验证码）
- `PasswordChangeRequest` - 修改密码
- `AuthOptions` - 认证选项

## 设计模式

### 1. 基础模型 + 继承

```python
class UserBase(BaseModel):
    username: str
    email: Optional[EmailStr]

class UserCreate(UserBase):
    password: str  # 新增字段

class User(UserBase):
    id: int  # 新增字段
    is_admin: bool
```

### 2. 部分更新模式

```python
class SystemConfigUpdate(BaseModel):
    value: Optional[str] = None  # 所有字段可选
    description: Optional[str] = None
```

### 3. 数据掩码

```python
class LLMConfigRead(BaseModel):
    llm_provider_api_key_masked: Optional[str]  # 掩码后的Key
    
    @classmethod
    def from_orm_with_mask(cls, config):
        return cls(
            llm_provider_api_key_masked=mask_api_key(config.llm_provider_api_key)
        )
```

### 4. 自定义验证

```python
class PromptRead(PromptBase):
    @classmethod
    def model_validate(cls, obj):
        # 自定义标签处理逻辑
        if isinstance(obj.tags, str):
            processed = obj.tags.split(",")
        return super().model_validate(data)
```

## 使用示例

### API端点使用

```python
@router.post("/configs", response_model=SystemConfigRead)
async def create_config(payload: SystemConfigCreate):
    # payload自动验证
    config = await config_service.upsert_config(payload)
    return config  # 自动序列化为SystemConfigRead
```

### 数据验证

```python
# 自动验证
try:
    user = UserCreate(
        username="john",
        email="invalid-email",  # 错误的邮箱格式
        password="123"  # 太短
    )
except ValidationError as e:
    print(e.errors())
```

### ORM转换

```python
# from_attributes = True 支持ORM对象
user_orm = await user_repo.get(id=1)
user_schema = User.model_validate(user_orm)
```

## 字段验证规则

### 字符串长度

```python
username: str = Field(..., min_length=3, max_length=50)
password: str = Field(..., min_length=6)
```

### 数值范围

```python
total_chapters: int = Field(..., ge=10, le=10000)  # 10-10000
max_concurrent: int = Field(default=5, ge=1, le=10)  # 1-10
```

### 邮箱验证

```python
from pydantic import EmailStr

email: EmailStr  # 自动验证邮箱格式
```

### 可选字段

```python
description: Optional[str] = None
tags: Optional[List[str]] = Field(default=None)
```

## 响应模型配置

### from_attributes

```python
class SystemConfigRead(BaseModel):
    class Config:
        from_attributes = True  # 支持ORM对象转换
```

### 自定义序列化

```python
class LLMConfigRead(BaseModel):
    @classmethod
    def from_orm_with_mask(cls, config):
        # 自定义ORM转换逻辑
        return cls(...)
```

## 最佳实践

### 1. 使用继承减少重复

```python
# 好的做法
class UserBase(BaseModel):
    username: str
    email: Optional[str]

class UserCreate(UserBase):
    password: str

# 不推荐：重复定义
class UserCreate(BaseModel):
    username: str
    email: Optional[str]
    password: str
```

### 2. 敏感数据处理

```python
# 好的做法：掩码敏感信息
llm_provider_api_key_masked: Optional[str]

# 不推荐：直接暴露
llm_provider_api_key: Optional[str]
```

### 3. 明确的字段描述

```python
# 好的做法
total_chapters: int = Field(
    ...,
    description="小说总章节数",
    ge=10,
    le=10000
)

# 不推荐：无描述
total_chapters: int
```

### 4. 使用枚举类型

```python
# 好的做法
class ChapterGenerationStatus(str, Enum):
    NOT_GENERATED = "not_generated"
    GENERATING = "generating"

status: ChapterGenerationStatus

# 不推荐：字符串
status: str
```

## 相关文档

- **数据模型**: [`backend/app/models/`](../models/)
- **API路由**: [`backend/app/api/routers/`](../api/routers/)
- **服务层**: [`backend/app/services/`](../services/)