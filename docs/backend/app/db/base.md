# backend/app/db/base.py - SQLAlchemy ORM 基类

## 文件概述

定义 SQLAlchemy 2.0 的声明式基类（Declarative Base），为所有数据模型提供统一的基础结构。该基类实现了自动表名生成功能，简化了模型定义流程。

**文件路径：** `backend/app/db/base.py`  
**代码行数：** 9 行  
**复杂度：** ⭐ 简单

## 核心类定义

### Base 类

继承自 `DeclarativeBase`，是所有 ORM 模型的基类。

```python
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    """SQLAlchemy 基类，自动根据类名生成表名。"""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
```

**核心功能：**
- **声明式基类**：使用 SQLAlchemy 2.0 的 `DeclarativeBase`
- **自动表名**：根据模型类名自动生成小写的表名
- **类型提示**：支持完整的类型检查

## 功能详解

### 1. 自动表名生成

**实现机制：**
```python
@declared_attr.directive
def __tablename__(cls) -> str:
    return cls.__name__.lower()
```

**表名映射规则：**
- `Novel` → `novel` 表
- `User` → `user` 表
- `PartOutline` → `partoutline` 表
- `LLMConfig` → `llmconfig` 表

**注意事项：**
- 表名全部转为小写
- 不会自动添加下划线分隔（如 `PartOutline` → `partoutline` 而非 `part_outline`）
- 如果需要自定义表名，可在模型中显式指定 `__tablename__`

### 2. 声明式 ORM

使用 SQLAlchemy 2.0 的声明式基类：

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**优势：**
- **类型安全**：完整的类型提示支持
- **简洁语法**：使用 Python 类定义数据模型
- **自动映射**：类属性自动映射到数据库列
- **关系定义**：支持声明式的关系定义

## 使用示例

### 1. 创建数据模型

```python
from sqlalchemy import Column, Integer, String
from backend.app.db.base import Base

class Novel(Base):
    """小说模型 - 表名自动为 'novel'"""
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    author = Column(String(100))
```

**生成的表结构：**
```sql
CREATE TABLE novel (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    author VARCHAR(100)
);
```

### 2. 自定义表名

如果需要自定义表名，可以显式指定：

```python
class PartOutline(Base):
    """部分大纲模型 - 自定义表名"""
    
    __tablename__ = "part_outlines"  # 显式指定表名
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
```

### 3. 创建所有表

```python
from sqlalchemy import create_engine
from backend.app.db.base import Base

# 创建引擎
engine = create_engine("sqlite:///database.db")

# 创建所有继承自 Base 的表
Base.metadata.create_all(engine)
```

## SQLAlchemy 2.0 特性

### 1. DeclarativeBase

SQLAlchemy 2.0 引入的新基类：

```python
# 旧版本 (1.x)
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# 新版本 (2.0)
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass
```

**新版本优势：**
- 更好的类型提示
- 更清晰的继承结构
- 支持 Python 类型注解

### 2. declared_attr.directive

装饰器用于定义类级别的属性：

```python
@declared_attr.directive
def __tablename__(cls) -> str:
    return cls.__name__.lower()
```

**特点：**
- 在类定义时执行
- 接收类本身作为参数
- 返回值作为属性值
- 支持动态计算

## 与项目集成

### 1. 导入使用

所有模型都应该继承此基类：

```python
# backend/app/models/novel.py
from ..db.base import Base

class Novel(Base):
    # 模型定义
    pass
```

### 2. 元数据管理

Base 类管理所有表的元数据：

```python
from backend.app.db.base import Base

# 访问所有表的元数据
print(Base.metadata.tables.keys())
# 输出: dict_keys(['novel', 'user', 'llmconfig', ...])
```

### 3. 表创建

通过 Base.metadata 创建所有表：

```python
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

## 设计模式

### 1. 单一职责原则

Base 类只负责：
- 提供 ORM 基础功能
- 自动生成表名
- 管理表元数据

### 2. 开闭原则

- **对扩展开放**：可以继承 Base 创建新模型
- **对修改封闭**：Base 类本身无需修改

### 3. 依赖倒置原则

所有模型依赖抽象的 Base 类，而不是具体实现：

```python
# 所有模型都依赖 Base 抽象
class Novel(Base): pass
class User(Base): pass
class LLMConfig(Base): pass
```

## 相关文件

### 数据库相关
- [`backend/app/db/session.py`](session.md) - 数据库会话管理
- [`backend/app/db/init_db.py`](init_db.md) - 数据库初始化

### 模型定义
- [`backend/app/models/novel.py`](../models/novel.md) - 小说模型
- [`backend/app/models/user.py`](../models/user.md) - 用户模型
- [`backend/app/models/llm_config.py`](../models/llm_config.md) - LLM 配置模型
- [`backend/app/models/prompt.py`](../models/prompt.md) - 提示词模型

### 配置相关
- [`backend/app/core/config.py`](../core/config.md) - 数据库配置

## 注意事项

### 1. 表名规范

⚠️ **自动表名是全小写的**

```python
class PartOutline(Base):
    pass
# 表名: partoutline (不是 part_outline)

class LLMConfig(Base):
    pass
# 表名: llmconfig (不是 llm_config)
```

**解决方案：**

如果需要下划线分隔的表名，显式指定：

```python
class PartOutline(Base):
    __tablename__ = "part_outlines"
```

### 2. 循环导入

避免在 base.py 中导入其他模型：

```python
# ❌ 错误：会导致循环导入
from ..models.novel import Novel

# ✅ 正确：只在需要时导入
# 在其他文件中：from ..db.base import Base
```

### 3. 元数据管理

所有表共享同一个 metadata 对象：

```python
# 获取所有表
Base.metadata.tables

# 删除所有表
Base.metadata.drop_all(engine)

# 创建所有表
Base.metadata.create_all(engine)
```

## 最佳实践

### 1. 模型定义规范

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from backend.app.db.base import Base

class Novel(Base):
    """小说模型
    
    表名: novel
    """
    
    # 主键
    id = Column(Integer, primary_key=True, index=True)
    
    # 基础字段
    title = Column(String(200), nullable=False, index=True)
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### 2. 类型提示

使用 SQLAlchemy 2.0 的类型注解：

```python
from typing import Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

class Novel(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[Optional[str]] = mapped_column(String(100))
```

### 3. 文档字符串

为每个模型添加清晰的文档：

```python
class Novel(Base):
    """小说项目模型
    
    存储小说的基础信息，包括标题、作者、大纲等。
    
    表名: novel
    索引: title, created_at
    """
    pass
```

## 技术细节

### 1. DeclarativeBase 源码分析

```python
class DeclarativeBase:
    """SQLAlchemy 2.0 声明式基类
    
    提供：
    - metadata: 元数据对象
    - registry: 类注册表
    - __mapper__: ORM 映射器
    """
    pass
```

### 2. declared_attr 工作原理

```python
@declared_attr.directive
def __tablename__(cls) -> str:
    # cls 是正在定义的模型类
    # 在类定义完成时被调用
    # 返回值赋给 __tablename__ 属性
    return cls.__name__.lower()
```

### 3. 表名生成时机

```python
# 1. 定义模型类
class Novel(Base):
    id = Column(Integer, primary_key=True)

# 2. Python 解释器创建类对象
# 3. 触发 __tablename__ 的 declared_attr
# 4. 调用 cls.__name__.lower()
# 5. 设置 Novel.__tablename__ = "novel"
```

## 总结

`base.py` 是 SQLAlchemy ORM 的核心基础文件，虽然代码简洁（仅 9 行），但承担了重要职责：

**核心价值：**
1. ✅ 提供统一的 ORM 基类
2. ✅ 自动生成表名
3. ✅ 管理表元数据
4. ✅ 支持类型提示

**使用建议：**
- 所有数据模型都应继承 `Base`
- 注意自动生成的表名是全小写
- 需要自定义表名时显式指定 `__tablename__`
- 避免在 base.py 中导入其他模型

**扩展方向：**
- 可以添加公共字段（如 created_at、updated_at）
- 可以添加公共方法（如 to_dict()）
- 可以添加混入类（Mixin）提供通用功能

---

**文件信息：**
- 创建日期：2025-11-06
- 文档版本：v1.0.0
- 维护者：Arboris-Novel Team