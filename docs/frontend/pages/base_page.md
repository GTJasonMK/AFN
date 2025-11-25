
# frontend/pages/base_page.py

## 模块概述

基础页面类模块，为应用中的所有页面提供统一的父类。该模块定义了页面的基本接口和生命周期钩子，实现了导航信号机制，确保页面之间的通信和切换符合统一规范。

**核心功能：**
- 统一的导航信号（页面跳转、返回）
- 页面刷新接口
- 页面生命周期钩子（显示、隐藏）
- 便捷的导航方法

## 主要类

### BasePage

所有页面的基类，继承自 `QWidget`。

#### 信号定义

```python
# 导航信号
navigateRequested = pyqtSignal(str, dict)  # (page_type, params)
goBackRequested = pyqtSignal()
```

**信号说明：**
- **navigateRequested**: 请求导航到其他页面
  - 参数1：页面类型字符串（如 'WORKSPACE', 'DETAIL' 等）
  - 参数2：页面参数字典（如 {'project_id': '123'}）
- **goBackRequested**: 请求返回上一页

#### 核心方法

**refresh() - 刷新页面数据**

```python
def refresh(self, **params):
    """刷新页面数据

    当页面已存在且被重新导航到时调用
    子类应该重写此方法以更新页面内容

    Args:
        **params: 页面参数（如project_id等）
    """
    pass
```

**设计理念：**
- 当用户导航到已存在的页面时调用
- 避免重复创建页面实例，提高性能
- 子类重写此方法以实现特定的刷新逻辑

**onShow() - 页面显示时的钩子**

```python
def onShow(self):
    """页面显示时的钩子

    当页面被切换为当前页面时调用
    子类可以重写此方法执行初始化逻辑
    """
    pass
```

**使用场景：**
- 启动定时器
- 加载最新数据
- 恢复页面状态
- 注册事件监听器

**onHide() - 页面隐藏时的钩子**

```python
def onHide(self):
    """页面隐藏时的钩子

    当页面被切换离开时调用
    子类可以重写此方法执行清理逻辑
    """
    pass
```

**使用场景：**
- 停止定时器
- 保存页面状态
- 取消未完成的请求
- 移除事件监听器

**navigateTo() - 导航到其他页面的便捷方法**

```python
def navigateTo(self, page_type, **params):
    """导航到其他页面的便捷方法

    Args:
        page_type: 页面类型（如'WORKSPACE', 'DETAIL'等）
        **params: 页面参数
    """
    self.navigateRequested.emit(page_type, params)
```

**goBack() - 返回上一页的便捷方法**

```python
def goBack(self):
    """返回上一页的便捷方法"""
    self.goBackRequested.emit()
```

## 使用示例

### 1. 创建自定义页面

```python
from pages.base_page import BasePage
from PyQt6.QtWidgets import QVBoxLayout, QLabel, QPushButton

class CustomPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_id = None
        self.setupUI()
    
    def setupUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel("自定义页面")
        layout.addWidget(self.title_label)
        
        # 导航按钮
        btn = QPushButton("前往工作台")
        btn.clicked.connect(lambda: self.navigateTo('WORKSPACE', project_id='123'))
        layout.addWidget(btn)
        
        # 返回按钮
        back_btn = QPushButton("返回")
        back_btn.clicked.connect(self.goBack)
        layout.addWidget(back_btn)
    
    def refresh(self, **params):
        """刷新页面"""
        self.project_id = params.get('project_id')
        self.title_label.setText(f"项目: {self.project_id}")
    
    def onShow(self):
        """页面显示时"""
        print("页面显示")
        # 可以在这里启动定时器、加载数据等
    
    def onHide(self):
        """页面隐藏时"""
        print("页面隐藏")
        # 可以在这里停止定时器、保存状态等
```

### 2. 在主窗口中管理页面

```python
from PyQt6.QtWidgets import QMainWindow, QStackedWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 页面容器
        self.pages = {}
        self.page_stack = QStackedWidget()
        self.setCentralWidget(self.page_stack)
        
        # 创建页面
        self.create_page('CUSTOM', CustomPage)
        self.create_page('WORKSPACE', WorkspacePage)
    
    def create_page(self, page_type, page_class):
        """创建页面并连接信号"""
        page = page_class(self)
        
        # 连接导航信号
        page.navigateRequested.connect(self.navigate_to_page)
        page.goBackRequested.connect(self.go_back)
        
        # 保存页面
        self.pages[page_type] = page
        self.page_stack.addWidget(page)
    
    def navigate_to_page(self, page_type, params):
        """导航到指定页面"""
        if page_type in self.pages:
            page = self.pages[page_type]
            
            # 隐藏当前页面
            current_page = self.page_stack.currentWidget()
            if current_page and hasattr(current_page, 'onHide'):
                current_page.onHide()
            
            # 刷新目标页面
            page.refresh(**params)
            
            # 切换页面
            self.page_stack.setCurrentWidget(page)
            
            # 显示新页面
            if hasattr(page, 'onShow'):
                page.onShow()
    
    def go_back(self):
        """返回上一页"""
        # 实现返回逻辑
        pass
```

### 3. 页面间通信

```python
class PageA(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        btn = QPushButton("前往 Page B")
        btn.clicked.connect(self.go_to_page_b)
        
        layout = QVBoxLayout(self)
        layout.addWidget(btn)
    
    def go_to_page_b(self):
        """导航到 Page B 并传递参数"""
        self.navigateTo('PAGE_B', 
                       project_id='123',
                       chapter_number=5,
                       mode='edit')

class PageB(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
    
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        back_btn = QPushButton("返回")
        back_btn.clicked.connect(self.goBack)
        layout.addWidget(back_btn)
    
    def refresh(self, **params):
        """接收并处理参数"""
        project_id = params.get('project_id')
        chapter_number = params.get('chapter_number')
        mode = params.get('mode')
        
        self.info_label.setText(
            f"项目: {project_id}\n"
            f"章节: {chapter_number}\n"
            f"模式: {mode}"
        )
```

### 4. 生命周期管理

```python
class DataPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.setupUI()
    
    def setupUI(self):
        layout = QVBoxLayout(self)
        self.data_label = QLabel("数据将自动更新...")
        layout.addWidget(self.data_label)
    
    def onShow(self):
        """页面显示时启动定时器"""
        print("页面显示，启动自动刷新")
        self.timer.start(5000)  # 每5秒刷新一次
        self.update_data()  # 立即刷新一次
    
    def onHide(self):
        """页面隐藏时停止定时器"""
        print("页面隐藏，停止自动刷新")
        self.timer.stop()
    
    def update_data(self):
        """更新数据"""
        # 从API获取最新数据
        data = self.fetch_data()
        self.data_label.setText(f"最新数据: {data}")
    
    def fetch_data(self):
        """获取数据（示例）"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
```

### 5. 状态保存与恢复

```python
class StatefulPage(BasePage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_position = 0
        self.selected_item = None
        self.setupUI()
    
    def setupUI(self):
        layout = QVBoxLayout(self)
        
        # 滚动区域
        self.scroll_area = QScrollArea()
        layout.addWidget(self.scroll_area)
        
        # 列表
        self.list_widget = QListWidget()
        for i in range(100):
            self.list_widget.addItem(f"项目 {i}")
        self.scroll_area.setWidget(self.list_widget)
    
    def onHide(self):
        """保存页面状态"""
        # 保存滚动位置
        self.scroll_position = self.scroll_area.verticalScrollBar().value()
        
        # 保存选中项
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_item = current_item.text()
        
        print(f"保存状态: 滚动位置={self.scroll_position}, 选中项={self.selected_item}")
    
    def onShow(self):
        """恢复页面状态"""
        # 恢复滚动位置
        if self.scroll_position:
            self.scroll_area.verticalScrollBar().setValue(self.scroll_position)
        
        # 恢复选中项
        if self.selected_item:
            items = self.list_widget.findItems(self.selected_item, Qt.MatchFlag.MatchExactly)
            if items:
                self.list_widget.setCurrentItem(items[0])
        
        print(f"恢复状态: 滚动位置={self.scroll_position}, 选中项={self.selected_item}")
```

## 设计模式与最佳实践

### 1. 模板方法模式

BasePage 定义了页面的骨架，子类重写钩子方法实现具体逻辑：

```python
# 基类定义接口
class BasePage(QWidget):
    def refresh(self, **params):
        pass  # 子类实现
    
    def onShow(self):
        pass  # 子类实现
    
    def onHide(self):
        pass  # 子类实现

# 子类实现具体逻辑
class ConcretePage(BasePage):
    def refresh(self, **params):
        # 具体的刷新逻辑
        pass
    
    def onShow(self):
        # 具体的显示逻辑
        pass
```

### 2. 观察者模式

使用 PyQt 信号槽机制实现页面间通信：

```python
# 页面发出信号
self.navigateRequested.emit('TARGET_PAGE', {'param': 'value'})

# 主窗口监听信号
page.navigateRequested.connect(self.navigate_to_page)
```

### 3. 单一职责原则

BasePage 只负责：
- 定义页面接口
- 提供导航机制
- 管理生命周期

具体业务逻辑由子类实现。

### 4. 依赖倒置原则

主窗口依赖 BasePage 抽象，而非具体页面类：

```python
def navigate_to_page(self, page_type, params):
    page = self.pages[page_type]  # page 是 BasePage 类型
    page.refresh(**params)  # 调用基类方法
```

## 技术亮点

### 1. 灵活的参数传递

使用 `**params` 支持任意数量和类型的参数：

```python
# 传递不同参数
self.navigateTo('PAGE_A', project_id='123')
self.navigateTo('PAGE_B', project_id='123', chapter=5, mode='edit')
```

### 2. 生命周期钩子

清晰的生命周期管理：
- **创建阶段**：`__init__()` 和 `setupUI()`
- **显示阶段**：`onShow()`
- **刷新阶段**：`refresh()`
- **隐藏阶段**：`onHide()`

### 3. 便捷方法

封装信号发射，简化代码：

```python
# 使用便捷方法
self.navigateTo('WORKSPACE', project_id='123')

# 等价于
self.navigateRequested.emit('WORKSPACE', {'project_id': '123'})
```

## 与其他组件的关系

```
BasePage（抽象基类）
├── 被所有页面类继承
│   ├── HomePage
│   ├── WorkspacePage
│   ├── NovelDetailPage
│   └── WritingDeskPage
├── 信号被 MainWindow 监听
└── 定义统一的页面接口
```

## 注意事项

### 1. 必须连接信号

创建页面后必须连接导航信号，否则导航功能无法工作：

```python
page.navigateRequested.connect(self.navigate_to_page)
page.goBackRequested.connect(self.go_back)
```

### 2. 避免在构造函数中加载数据

数据加载应在 `refresh()` 或 `onShow()` 中进行：

```python
# 不推荐
def __init__(self, parent=None):
    super().__init__(parent)
    self.load_data()  # 构造时就加载

# 推荐
def __init__(self, parent=None):
    super().__init__(parent)
    self.setupUI()

def onShow(self):
    self.load_data()  # 显示时才加载
```

### 3. 清理资源

在 `onHide()` 中清理资源，避免内存泄漏：

```python
def onHide(self):
    # 停止定时器
    if hasattr(self, 'timer'):
        self.timer.stop()
    
    # 取消网络请求
    if hasattr(self, 'request'):
        self.request.cancel()
    
    # 断开信号连接（如果是临时连接）
    # ...
```

### 4. 页面类型命名规范

使用全大写字符串作为页面类型：

```python
PAGE_TYPES = {
    'HOME': HomePage,
    'WORKSPACE': WorkspacePage,
    'DETAIL': NovelDetailPage,
    'WRITING_DESK': 