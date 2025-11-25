# empty_state.py - 空状态组件

## 文件路径
`frontend/components/empty_state.py`

## 模块概述
禅意风格的空状态显示组件，提供友好、有指引性的空状态界面。符合2025年UX最佳实践，通过清晰的视觉层次、明确的行动指引和情感化设计提升用户体验。

## 设计理念
- **清晰的视觉层次**: 图标 → 标题 → 描述 → 操作按钮
- **明确的行动指引**: 提供具体的操作建议
- **情感化设计**: 使用图标/插画传递友好感
- **可自定义内容**: 灵活适配不同场景

## 主要类

### 1. EmptyState - 空状态组件基类
**继承**: `QWidget`

基础空状态组件，包含图标、标题、描述和行动按钮。

#### 初始化参数
- `icon: str = '◐'` - 图标字符（Unicode或Emoji）
- `title: str = '暂无内容'` - 标题文字
- `description: str = ''` - 描述文字
- `action_text: str = ''` - 行动按钮文字
- `parent: QWidget = None` - 父组件

#### 信号
```python
actionClicked = pyqtSignal()  # 行动按钮点击时发射
```

#### 布局结构
```python
[Container - Vertical Center Aligned]
├── Icon (96px, accent color)
├── Title (2XL, bold, primary color)
├── Description (base, secondary color, max-width 480px)
└── Action Button (gradient, min-width 160px)
```

#### 样式配置
```python
# 图标
font-size: 96px
color: {ZenTheme.ACCENT_PRIMARY}

# 标题
font-size: {ZenTheme.FONT_SIZE_2XL}
font-weight: {ZenTheme.FONT_WEIGHT_BOLD}
color: {ZenTheme.TEXT_PRIMARY}
letter-spacing: {ZenTheme.LETTER_SPACING_TIGHT}

# 描述
font-size: {ZenTheme.FONT_SIZE_BASE}
color: {ZenTheme.TEXT_SECONDARY}
line-height: 1.7
max-width: 480px

# 按钮
background: gradient (primary → secondary)
padding: 14px 32px
min-width: 160px
border-radius: {ZenTheme.RADIUS_MD}
```

---

### 2. EmptyStateWithIllustration - 带插画的空状态
**继承**: `QWidget`

高级版空状态组件，包含圆形插画容器和双按钮支持。

#### 初始化参数
- `illustration_char: str = '📖'` - 插画字符
- `title: str = ''` - 标题
- `description: str = ''` - 描述
- `action_text: str = ''` - 主按钮文字
- `secondary_action_text: str = ''` - 次要按钮文字
- `parent: QWidget = None` - 父组件

#### 信号
```python
actionClicked = pyqtSignal()  # 主按钮点击时发射
```

#### 布局结构
```python
[Container - Vertical Center Aligned]
├── Illustration Container (200×200 circle)
│   └── Character (96px)
├── Title (3XL, bold)
├── Description (MD, max-width 520px)
└── Button Group (horizontal)
    ├── Secondary Button (optional)
    └── Primary Button (optional)
```

#### 插画容器样式
```python
# 圆形虚线边框
QFrame {
    background-color: transparent;
    border: 2px dashed {ZenTheme.BORDER_LIGHT};
    border-radius: 100px;  # 圆形
    width: 200px;
    height: 200px;
}
```

---

### 3. EmptyStatePresets - 空状态预设模板
**静态类**

提供常用场景的预设空状态组件。

#### 预设方法

##### no_projects(parent)
```python
@staticmethod
def no_projects(parent=None):
    """无项目状态
    
    使用场景: 首次使用，没有创建任何项目
    组件类型: EmptyStateWithIllustration
    插画: 📝
    标题: "还没有创作项目"
    描述: "开始你的第一个小说创作..."
    主按钮: "创建新项目"
    次要按钮: "查看示例"
    """
```

##### no_chapters(parent)
```python
@staticmethod
def no_chapters(parent=None):
    """无章节状态
    
    使用场景: 项目已创建，但未生成章节
    组件类型: EmptyState
    图标: 📖
    标题: "还未生成章节"
    描述: "点击下方按钮开始生成你的第一个章节"
    按钮: "生成章节"
    """
```

##### no_search_results(parent)
```python
@staticmethod
def no_search_results(parent=None):
    """无搜索结果状态
    
    使用场景: 搜索无结果
    组件类型: EmptyState
    图标: 🔍
    标题: "未找到匹配结果"
    描述: "请尝试使用其他关键词搜索"
    按钮: "清除搜索"
    """
```

##### no_data(parent)
```python
@staticmethod
def no_data(parent=None):
    """无数据状态（通用）
    
    使用场景: 通用空数据场景
    组件类型: EmptyState
    图标: ◐
    标题: "暂无数据"
    无描述和按钮
    """
```

##### error_state(parent)
```python
@staticmethod
def error_state(parent=None):
    """错误状态
    
    使用场景: 数据加载失败
    组件类型: EmptyState
    图标: ⚠
    标题: "加载失败"
    描述: "数据加载出现问题，请稍后重试"
    按钮: "重新加载"
    """
```

##### connection_error(parent)
```python
@staticmethod
def connection_error(parent=None):
    """连接错误状态
    
    使用场景: 网络连接失败
    组件类型: EmptyStateWithIllustration
    插画: 🔌
    标题: "无法连接服务器"
    描述: "请检查网络连接后重试"
    按钮: "重新连接"
    """
```

##### permission_denied(parent)
```python
@staticmethod
def permission_denied(parent=None):
    """权限不足状态
    
    使用场景: 无访问权限
    组件类型: EmptyState
    图标: 🔒
    标题: "权限不足"
    描述: "你没有权限访问此内容"
    无按钮
    """
```

##### coming_soon(parent)
```python
@staticmethod
def coming_soon(parent=None):
    """即将推出状态
    
    使用场景: 功能开发中
    组件类型: EmptyStateWithIllustration
    插画: 🚀
    标题: "即将推出"
    描述: "这个功能正在开发中，敬请期待"
    无按钮
    """
```

## 使用示例

### 1. 基础空状态
```python
from components.empty_state import EmptyState

# 创建空状态
empty = EmptyState(
    icon='📖',
    title='暂无章节',
    description='点击下方按钮生成第一个章节',
    action_text='生成章节',
    parent=self
)

# 连接信号
empty.actionClicked.connect(self.on_generate_chapter)

# 添加到布局
layout.addWidget(empty)
```

### 2. 带插画的空状态
```python
from components.empty_state import EmptyStateWithIllustration

# 创建高级空状态
empty = EmptyStateWithIllustration(
    illustration_char='📝',
    title='还没有项目',
    description='开始你的第一个小说创作',
    action_text='创建新项目',
    secondary_action_text='查看示例',
    parent=self
)

# 连接主按钮
empty.actionClicked.connect(self.on_create_project)

# 添加到布局
layout.addWidget(empty)
```

### 3. 使用预设模板
```python
from components.empty_state import EmptyStatePresets

# 无项目状态
empty = EmptyStatePresets.no_projects(parent=self)
empty.actionClicked.connect(self.on_create_project)
layout.addWidget(empty)

# 错误状态
error = EmptyStatePresets.error_state(parent=self)
error.actionClicked.connect(self.on_retry_load)
layout.addWidget(error)

# 连接错误
conn_error = EmptyStatePresets.connection_error(parent=self)
conn_error.actionClicked.connect(self.on_reconnect)
layout.addWidget(conn_error)
```

### 4. 动态切换状态
```python
class MyListWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.empty_state = None
        
        self.load_data()
    
    def load_data(self):
        """加载数据"""
        try:
            data = self.api_client.get_chapters()
            
            if data:
                # 有数据，显示列表
                self.show_list(data)
            else:
                # 无数据，显示空状态
                self.show_empty_state()
                
        except Exception as e:
            # 错误，显示错误状态
            self.show_error_state()
    
    def show_list(self, data):
        """显示列表"""
        if self.empty_state:
            self.empty_state.deleteLater()
            self.empty_state = None
        
        self.list_widget.show()
        # 填充数据...
    
    def show_empty_state(self):
        """显示空状态"""
        self.list_widget.hide()
        
        if self.empty_state:
            self.empty_state.deleteLater()
        
        self.empty_state = EmptyStatePresets.no_chapters(parent=self)
        self.empty_state.actionClicked.connect(self.on_generate)
        self.layout.addWidget(self.empty_state)
    
    def show_error_state(self):
        """显示错误状态"""
        self.list_widget.hide()
        
        if self.empty_state:
            self.empty_state.deleteLater()
        
        self.empty_state = EmptyStatePresets.error_state(parent=self)
        self.empty_state.actionClicked.connect(self.load_data)
        self.layout.addWidget(self.empty_state)
```

## 设计模式与最佳实践

### 1. 选择合适的组件类型
```python
# 简单场景 → EmptyState
empty = EmptyState(icon='📖', title='暂无数据')

# 重要场景 → EmptyStateWithIllustration
empty = EmptyStateWithIllustration(
    illustration_char='📝',
    title='欢迎使用'
)
```

### 2. 提供明确的行动指引
```python
# ✓ 好的做法：明确的操作
EmptyState(
    title='还未生成章节',
    description='点击下方按钮生成第一个章节',
    action_text='生成章节'
)

# ✗ 不好的做法：模糊的提示
EmptyState(
    title='无内容',
    description='暂无'
)
```

### 3. 适当的情感化设计
```python
# 友好的图标选择
no_projects = '📝'      # 创作相关
no_chapters = '📖'      # 阅读相关
error = '⚠'            # 警告
success = '✓'          # 成功
connection = '🔌'      # 连接
loading = '◐'         # 加载
```

### 4. 及时清理旧状态
```python
def switch_to_list(self):
    """切换到列表视图时清理空状态"""
    if self.empty_state:
        self.empty_state.deleteLater()  # 释放资源
        self.empty_state = None
    
    self.list_widget.show()
```

## 与其他组件的关系
- **Skeleton**: 加载中使用骨架屏，加载完成后切换到列表或空状态
- **LoadingSpinner**: 短时间加载用Spinner，长时间无数据用EmptyState
- **Toast**: 操作失败后可结合Toast提示和EmptyState显示
- **各种Page**: 所有页面在无数据时都应显示友好的空状态

## 注意事项

1. **选择合适的图标**: 使用与场景相关的图标或Emoji
2. **文案清晰**: 标题简洁，描述具体，按钮文字明确
3. **及时清理**: 切换状态时使用`deleteLater()`释放资源
4. **响应式设计**: 描述文字设置`max-width`和`word-wrap`
5. **信号连接**: 记得连接`actionClicked`信号处理用户操作

## 技术亮点

1. **禅意风格**: 遵循ZenTheme设计规范，视觉统一
2. **情感化设计**: 通过图标和文案传递友好感
3. **灵活配置**: 支持自定义所有文本和图标
4. **预设模板**: 常用场景开箱即用
5. **清晰层次**: 图标→标题→描述→按钮的视觉引导