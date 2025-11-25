
# frontend/models/project_status.py

## 模块概述

项目状态管理模块，参照Web应用的状态机设计，实现严格的串行工作流控制。该模块定义了小说项目的所有状态、状态转换规则和权限检查逻辑，确保用户按照正确的流程进行创作。

**核心功能：**
- 项目状态枚举定义
- 状态权限检查
- 页面访问控制
- 状态显示名称映射
- 工作流入口页面确定

## 主要类

### 1. ProjectStatus

项目状态枚举类，定义了所有可能的项目状态。

#### 状态定义

```python
class ProjectStatus(str, Enum):
    """项目状态枚举"""
    DRAFT = "draft"                              # 草稿
    BLUEPRINT_READY = "blueprint_ready"          # 蓝图就绪
    PART_OUTLINES_READY = "part_outlines_ready"  # 分卷大纲就绪
    CHAPTER_OUTLINES_READY = "chapter_outlines_ready"  # 章节大纲就绪
    WRITING = "writing"                          # 写作中
    COMPLETED = "completed"                      # 已完成
```

#### 工作流说明

```
draft (草稿)
  ↓ 完成概念对话并生成蓝图
blueprint_ready (蓝图就绪)
  ↓ 生成分卷大纲（仅长篇>50章）
part_outlines_ready (分卷大纲就绪)
  ↓ 生成章节大纲
chapter_outlines_ready (章节大纲就绪)
  ↓ 开始写作
writing (写作中)
  ↓ 完成所有章节
completed (已完成)
```

**状态说明：**

- **draft**: 概念对话阶段，用户需要完善世界观和剧情要素
- **blueprint_ready**: 蓝图已生成，可以编辑世界观、角色、章节纲要
- **part_outlines_ready**: 分卷大纲就绪（仅长篇小说>50章），需要进一步细化章节大纲
- **chapter_outlines_ready**: 章节大纲就绪，可以开始写作
- **writing**: 写作进行中，正在生成章节内容
- **completed**: 所有章节已完成

### 2. ProjectStatusHelpers

项目状态权限检查辅助类，提供状态相关的工具方法。

#### 权限检查方法

**can_access_concept_dialogue() - 检查是否可以访问概念对话页**

```python
@staticmethod
def can_access_concept_dialogue(status: str) -> bool:
    """
    检查是否可以访问概念对话页

    规则：任何状态都可以访问（用于查看历史对话）
    """
    return True
```

**can_access_blueprint() - 检查是否可以访问蓝图编辑页**

```python
@staticmethod
def can_access_blueprint(status: str) -> bool:
    """
    检查是否可以访问蓝图编辑页

    规则：必须完成概念对话并生成蓝图后才能访问
    """
    return status in [
        ProjectStatus.BLUEPRINT_READY,
        ProjectStatus.PART_OUTLINES_READY,
        ProjectStatus.CHAPTER_OUTLINES_READY,
        ProjectStatus.WRITING,
        ProjectStatus.COMPLETED
    ]
```

**can_access_writing_desk() - 检查是否可以访问写作台**

```python
@staticmethod
def can_access_writing_desk(status: str) -> bool:
    """
    检查是否可以访问写作台

    规则：必须完成章节大纲后才能开始写作
    """
    return status in [
        ProjectStatus.CHAPTER_OUTLINES_READY,
        ProjectStatus.WRITING,
        ProjectStatus.COMPLETED
    ]
```

**can_generate_blueprint() - 检查是否可以生成蓝图**

```python
@staticmethod
def can_generate_blueprint(status: str) -> bool:
    """
    检查是否可以生成蓝图

    规则：仅在draft状态可以生成蓝图
    """
    return status == ProjectStatus.DRAFT
```

**can_start_writing() - 检查是否可以开始写作**

```python
@staticmethod
def can_start_writing(status: str) -> bool:
    """
    检查是否可以开始写作

    规则：章节大纲就绪或已在写作中
    """
    return status in [
        ProjectStatus.CHAPTER_OUTLINES_READY,
        ProjectStatus.WRITING
    ]
```

#### 页面路由方法

**get_entry_page() - 确定进入项目时应该显示的页面**

```python
@staticmethod
def get_entry_page(status: str) -> int:
    """
    确定进入项目时应该显示的页面

    参数:
        status: 项目状态

    返回:
        页面索引（对应MainWindowV2的PAGE_*常量）
    """
    from ui.main_window_v2 import MainWindowV2

    if status == ProjectStatus.DRAFT:
        # draft状态强制进入概念对话
        return MainWindowV2.PAGE_CONCEPT_DIALOGUE
    elif status in [ProjectStatus.BLUEPRINT_READY, ProjectStatus.PART_OUTLINES_READY]:
        # 蓝图就绪但还未完成章节大纲，进入蓝图编辑页
        return MainWindowV2.PAGE_BLUEPRINT
    else:
        # chapter_outlines_ready, writing, completed 状态进入写作台
        return MainWindowV2.PAGE_WRITING_DESK
```

#### 显示相关方法

**get_status_display_name() - 获取状态的显示名称**

```python
@staticmethod
def get_status_display_name(status: str) -> str:
    """
    获取状态的显示名称

    参数:
        status: 项目状态

    返回:
        中文显示名称
    """
    status_names = {
        ProjectStatus.DRAFT: "草稿",
        ProjectStatus.BLUEPRINT_READY: "蓝图就绪",
        ProjectStatus.PART_OUTLINES_READY: "分卷大纲就绪",
        ProjectStatus.CHAPTER_OUTLINES_READY: "章节大纲就绪",
        ProjectStatus.WRITING: "写作中",
        ProjectStatus.COMPLETED: "已完成"
    }
    return status_names.get(status, "未知状态")
```

**get_status_badge_type() - 获取状态徽章的类型**

```python
@staticmethod
def get_status_badge_type(status: str) -> str:
    """
    获取状态徽章的类型（用于StatusBadge组件）

    参数:
        status: 项目状态

    返回:
        徽章类型：successful, generating, pending, warning, error, info
    """
    if status == ProjectStatus.COMPLETED:
        return 'successful'
    elif status == ProjectStatus.WRITING:
        return 'generating'
    elif status == ProjectStatus.DRAFT:
        return 'pending'
    elif status in [ProjectStatus.CHAPTER_OUTLINES_READY, ProjectStatus.PART_OUTLINES_READY]:
        return 'info'
    else:  # BLUEPRINT_READY
        return 'info'
```

**get_locked_page_message() - 获取页面锁定提示信息**

```python
@staticmethod
def get_locked_page_message(page_name: str, current_status: str) -> str:
    """
    获取页面锁定提示信息

    参数:
        page_name: 页面名称
        current_status: 当前项目状态

    返回:
        提示信息
    """
    if page_name == "蓝图编辑":
        return "请先完成概念对话并生成蓝图"
    elif page_name == "写作台":
        if current_status == ProjectStatus.DRAFT:
            return "请先完成概念对话并生成蓝图"
        elif current_status == ProjectStatus.BLUEPRINT_READY:
            return "请先完成章节大纲"
        elif current_status == ProjectStatus.PART_OUTLINES_READY:
            return "请先完成章节大纲细化"
        else:
            return "暂时无法访问写作台"
    else:
        return "当前状态下无法访问此页面"
```

## 使用示例

### 1. 检查页面访问权限

```python
from models.project_status import ProjectStatus, ProjectStatusHelpers

# 获取项目状态
project = get_project(project_id)
status = project['status']

# 检查是否可以访问写作台
if ProjectStatusHelpers.can_access_writing_desk(status):
    # 允许访问
    show_writing_desk()
else:
    # 显示锁定提示
    message = ProjectStatusHelpers.get_locked_page_message("写作台", status)
    show_error_dialog(message)
```

### 2. 确定入口页面

```python
from models.project_status import ProjectStatusHelpers

def open_project(project_id):
    """打开项目"""
    # 获取项目数据
    project = api_client.get_novel(project_id)
    status = project['status']
    
    # 确定应该显示的页面
    entry_page = ProjectStatusHelpers.get_entry_page(status)
    
    # 切换到对应页面
    self.page_stack.setCurrentIndex(entry_page)
```

### 3. 显示状态徽章

```python
from models.project_status import ProjectStatusHelpers
from PyQt6.QtWidgets import QLabel

def create_status_badge(status: str) -> QLabel:
    """创建状态徽章"""
    # 获取显示名称
    display_name = ProjectStatusHelpers.get_status_display_name(status)
    
    # 获取徽章类型
    badge_type = ProjectStatusHelpers.get_status_badge_type(status)
    
    # 创建标签
    badge = QLabel(display_name)
    
    # 应用样式
    if badge_type == 'successful':
        badge.setStyleSheet("background-color: #88A88E; color: white;")
    elif badge_type == 'generating':
        badge.setStyleSheet("background-color: #8B9A8A; color: white;")
    elif badge_type == 'pending':
        badge.setStyleSheet("background-color: #C8A88B; color: white;")
    else:
        badge.setStyleSheet("background-color: #8A9AA8; color: white;")
    
    return badge
```

### 4. 工作流控制

```python
from models.project_status import ProjectStatus, ProjectStatusHelpers

class ProjectWorkflow:
    def __init__(self, project_id, api_client):
        self.project_id = project_id
        self.api_client = api_client
        self.current_status = None
        self.load_status()
    
    def load_status(self):
        """加载项目状态"""
        project = self.api_client.get_novel(self.project_id)
        self.current_status = project['status']
    
    def can_proceed_to_blueprint(self) -> bool:
        """检查是否可以进入蓝图阶段"""
        return ProjectStatusHelpers.can_generate_blueprint(self.current_status)
    
    def can_proceed_to_writing(self) -> bool:
        """检查是否可以进入写作阶段"""
        return ProjectStatusHelpers.can_start_writing(self.current_status)
    
    def generate_blueprint(self):
        """生成蓝图"""
        if not self.can_proceed_to_blueprint():
            raise ValueError("当前状态不允许生成蓝图")
        
        # 调用API生成蓝图
        result = self.api_client.generate_blueprint(self.project_id)
        
        # 更新状态
        self.load_status()
    
    def start_writing(self, chapter_number: int):
        """开始写作"""
        if not self.can_proceed_to_writing():
            raise ValueError("当前状态不允许开始写作")
        
        # 调用API生成章节
        result = self.api_client.generate_chapter(self.project_id, chapter_number)
        
        # 更新状态
        self.load_status()
```

### 5. UI状态控制

```python
from models.project_status import ProjectStatusHelpers

class ProjectDetailWindow(QMainWindow):
    def __init__(self, project_id):
        super().__init__()
        self.project_id = project_id
        self.project_status = None
        self.setupUI()
        self.load_project()
    
    def setupUI(self):
        """初始化UI"""
        # 创建按钮
        self.blueprint_btn = QPushButton("生成蓝图")
        self.outline_btn = QPushButton("生成大纲")
        self.write_btn = QPushButton("开始写作")
        
        # 连接信号
        self.blueprint_btn.clicked.connect(self.on_generate_blueprint)
        self.write_btn.clicked.connect(self.on_start_writing)
    
    def load_project(self):
        """加载项目并更新UI状态"""
        project = api_client.get_novel(self.project_id)
        self.project_status = project['status']
        self.update_ui_state()
    
    def update_ui_state(self):
        """根据项目状态更新UI"""
        # 蓝图按钮
        can_gen_blueprint = ProjectStatusHelpers.can_generate_blueprint(self.project_status)
        self.blueprint_btn.setEnabled(can_gen_blueprint)
        
        # 写作按钮
        can_write = ProjectStatusHelpers.can_start_writing(self.project_status)
        self.write_btn.setEnabled(can_write)
        
        # 更新提示信息
        if not can_write:
            message = ProjectStatusHelpers.get_locked_page_message("写作台", self.project_status)
            self.write_btn.setToolTip(message)
```

## 设计模式与最佳实践

### 1. 状态机模式

项目状态遵循严格的状态机设计：
- 明确的状态定义
- 清晰的状态转换规则
- 状态相关的权限检查

### 2. 单一职责原则

- **ProjectStatus**: 只负责定义状态枚举
- **ProjectStatusHelpers**: 只负责状态相关的工具方法

### 3. 开闭原则

通过静态方法实现，易于扩展新的状态检查逻辑，无需修改现有代码。

### 4. 防御性编程

所有状态检查都有明确的返回值，避免未定义状态导致的错误。

## 技术亮点

### 1. 字符串枚举

```python
class ProjectStatus(str, Enum):
    DRAFT = "draft"
```

继承自 `str` 和 `Enum`，既有枚举的类型安全，又能直接作为字符串使用。

### 2. 状态映射

使用字典映射实现状态到显示名称的转换，易于维护：

```python
status_names = {
    ProjectStatus.DRAFT: "草稿",
    ProjectStatus.BLUEPRINT_READY: "蓝图就绪",
    # ...
}
```

### 3. 集合成员检查

使用集合检查提高可读性和性能：

```python
return status in [
    ProjectStatus.CHAPTER_OUTLINES_READY,
    ProjectStatus.WRITING,
    ProjectStatus.COMPLETED
]
```

## 与其他组件的关系

```
ProjectStatus & ProjectStatusHelpers
├── 被窗口类使用（MainWindow, NovelDetail等）
├── 