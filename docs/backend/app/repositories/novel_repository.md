# Novel Repository - 小说项目仓储

## 文件概述

**文件路径**: `backend/app/repositories/novel_repository.py`  
**代码行数**: 56行  
**核心职责**: 小说项目数据访问，支持关联数据预加载

## 核心功能

### 1. 按ID查询（预加载所有关联）

```python
async def get_by_id(self, project_id: str) -> Optional[NovelProject]
```

**预加载的关联数据**：
- blueprint（蓝图）
- characters（角色列表）
- relationships_（关系列表）
- outlines（大纲列表）
- conversations（对话列表）
- part_outlines（分层大纲）
- chapters（章节列表）
  - versions（章节版本）
  - evaluations（评估结果）
  - selected_version（选中版本）

**使用示例**：
```python
novel_repo = NovelRepository(session)

# 获取完整项目数据
project = await novel_repo.get_by_id("uuid-xxx")
if project:
    print(f"项目: {project.title}")
    print(f"角色数: {len(project.characters)}")
    print(f"章节数: {len(project.chapters)}")
    
    # 直接访问关联数据，无需额外查询
    for chapter in project.chapters:
        print(f"章节: {chapter.title}")
        if chapter.selected_version:
            print(f"选中版本: {chapter.selected_version.content[:100]}")
```

### 2. 按用户查询项目列表

```python
async def list_by_user(self, user_id: int) -> Iterable[NovelProject]
```

**特性**：
- 按更新时间降序排列
- 预加载blueprint、outlines、chapters及选中版本

**使用示例**：
```python
# 获取用户的所有项目
projects = await novel_repo.list_by_user(user_id=1)

for project in projects:
    print(f"{project.title} - 最后更新: {project.updated_at}")
    print(f"章节数: {len(project.chapters)}")
```

### 3. 查询所有项目（管理后台）

```python
async def list_all(self) -> Iterable[NovelProject]
```

**特性**：
- 包含owner（用户信息）
- 按更新时间降序排列

**使用示例**：
```python
# 管理后台查看所有项目
all_projects = await novel_repo.list_all()

for project in all_projects:
    print(f"{project.title} - 作者: {project.owner.username}")
```

## 性能优化

### selectinload策略

使用SQLAlchemy的selectinload避免N+1查询问题：

```python
.options(
    selectinload(NovelProject.chapters)
        .selectinload(Chapter.versions)
)
```

## 相关文档

- **数据模型**: [`backend/app/models/novel.py`](../models/novel.md)
- **服务层**: [`backend/app/services/novel_service.py`](../services/novel_service.md)