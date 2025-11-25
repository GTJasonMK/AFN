# backend/app/core/constants.py - 核心常量定义

## 文件概述

定义项目中使用的枚举类型和常量值，确保类型安全和代码一致性。使用 Python 的 `Enum` 类型实现。

## 枚举类

### ProjectStatus 枚举（第10-72行）

小说项目状态枚举，继承自 `str` 和 `Enum`，支持字符串比较。

#### 状态值定义

```python
class ProjectStatus(str, Enum):
    DRAFT = "draft"                                    # 灵感对话阶段
    BLUEPRINT_READY = "blueprint_ready"                # 蓝图生成完成
    PART_OUTLINES_READY = "part_outlines_ready"       # 部分大纲完成（长篇）
    CHAPTER_OUTLINES_READY = "chapter_outlines_ready" # 章节大纲完成
    WRITING = "writing"                                # 写作进行中
    COMPLETED = "completed"                            # 项目完成
```

#### 状态流转路径

**短篇流程（≤50章）：**
```
draft → blueprint_ready → chapter_outlines_ready → writing → completed
```

**长篇流程（>50章）：**
```
draft → blueprint_ready → part_outlines_ready → chapter_outlines_ready → writing → completed
```

#### 状态说明

| 状态 | 英文名 | 中文名 | 说明 |
|------|--------|--------|------|
| DRAFT | draft | 灵感收集中 | 与 AI 进行创意对话，收集创作要素 |
| BLUEPRINT_READY | blueprint_ready | 蓝图完成 | 基础设定生成完成，包含世界观、角色等 |
| PART_OUTLINES_READY | part_outlines_ready | 部分大纲完成 | 仅长篇小说，将整体分为多个部分 |
| CHAPTER_OUTLINES_READY | chapter_outlines_ready | 章节大纲完成 | 详细章节大纲生成，可开始写作 |
| WRITING | writing | 写作中 | 至少有一章已生成 |
| COMPLETED | completed | 已完成 | 所有章节完成，项目结束 |

### 类方法

#### 1. `__str__()`（第37-39行）

```python
def __str__(self) -> str:
    """返回枚举值的字符串形式，方便与数据库字段比较"""
    return self.value
```

**功能：** 支持枚举与字符串的直接比较

**使用示例：**
```python
if project.status == ProjectStatus.DRAFT:
    # 等价于 project.status == "draft"
```

#### 2. `get_display_name()`（第41-52行）

```python
@classmethod
def get_display_name(cls, status: str) -> str:
    """获取状态的中文显示名称"""
```

**映射关系：**
```python
{
    "draft": "灵感收集中",
    "blueprint_ready": "蓝图完成",
    "part_outlines_ready": "部分大纲完成",
    "chapter_outlines_ready": "章节大纲完成",
    "writing": "写作中",
    "completed": "已完成"
}
```

**使用示例：**
```python
display = ProjectStatus.get_display_name(project.status)
# 返回：如 "写作中"
```

#### 3. `can_generate_blueprint()`（第54-57行）

```python
@classmethod
def can_generate_blueprint(cls, status: str) -> bool:
    """判断是否可以生成蓝图"""
    return status == cls.DRAFT
```

**规则：** 仅在 `DRAFT` 状态可生成蓝图

#### 4. `can_generate_part_outlines()`（第59-62行）

```python
@classmethod
def can_generate_part_outlines(cls, status: str) -> bool:
    """判断是否可以生成部分大纲"""
    return status == cls.BLUEPRINT_READY
```

**规则：** 仅在 `BLUEPRINT_READY` 状态可生成部分大纲

#### 5. `can_generate_chapter_outlines()`（第64-67行）

```python
@classmethod
def can_generate_chapter_outlines(cls, status: str) -> bool:
    """判断是否可以生成章节大纲"""
    return status in [cls.BLUEPRINT_READY, cls.PART_OUTLINES_READY]
```

**规则：** 
- 短篇：`BLUEPRINT_READY` → 直接生成章节大纲
- 长篇：`PART_OUTLINES_READY` → 基于部分大纲生成章节大纲

#### 6. `can_start_writing()`（第69-72行）

```python
@classmethod
def can_start_writing(cls, status: str) -> bool:
    """判断是否可以开始写作"""
    return status in [cls.CHAPTER_OUTLINES_READY, cls.WRITING]
```

**规则：** 章节大纲完成后即可开始写作，写作中也可继续生成

## 使用场景

### 1. 状态判断

```python
from backend.app.core.constants import ProjectStatus

# 判断项目状态
if project.status == ProjectStatus.DRAFT:
    print("项目处于灵感对话阶段")

# 判断是否可以执行操作
if ProjectStatus.can_generate_blueprint(project.status):
    # 可以生成蓝图
    await generate_blueprint(project)
```

### 2. 状态显示

```python
# 获取中文显示名称
status_display = ProjectStatus.get_display_name(project.status)
print(f"当前状态：{status_display}")
```

### 3. 状态转换验证

```python
# 在状态机中使用
from backend.app.core.state_machine import ProjectStateMachine

state_machine = ProjectStateMachine(project.status)
if state_machine.can_transition_to(ProjectStatus.BLUEPRINT_READY):
    # 可以转换到蓝图完成状态
```

### 4. API 响应

```python
# 在 API 响应中返回状态信息
return {
    "status": project.status,
    "status_display": ProjectStatus.get_display_name(project.status),
    "can_generate_blueprint": ProjectStatus.can_generate_blueprint(project.status)
}
```

## 设计模式

### 1. 字符串枚举

继承自 `str` 和 `Enum`，支持：
- 与字符串直接比较
- JSON 序列化/反序列化
- 数据库存储为字符串类型

### 2. 类方法模式

使用 `@classmethod` 实现业务逻辑判断：
- 集中管理状态相关逻辑
- 避免逻辑分散在多处
- 便于单元测试

### 3. 状态机友好

与 `state_machine.py` 配合使用：
- `constants.py`：定义状态值和基础判断
- `state_machine.py`：管理状态转换规则和验证

## 扩展建议

如需添加新状态：

```python
class ProjectStatus(str, Enum):
    # ... 现有状态 ...
    REVIEWING = "reviewing"  # 新增：审核中状态
    
    @classmethod
    def can_submit_review(cls, status: str) -> bool:
        """判断是否可以提交审核"""
        return status == cls.COMPLETED
```

同时更新：
1. `get_display_name()` 中的映射
2. `state_machine.py` 中的转换规则
3. 相关的业务逻辑

## 相关文件

- `backend/app/core/state_machine.py` - 状态机管理
- `backend/app/models/novel.py` - NovelProject.status 字段
- `backend/app/services/novel_service.py` - 状态转换业务逻辑
- `backend/app/api/routers/novels.py` - 状态相关的 API 接口