
# frontend/windows/main_window.py - 主窗口与页面导航

## 文件概述

主窗口容器，使用 [`QStackedWidget`](frontend/windows/main_window.py:27) 实现单页面应用（SPA）风格的页面管理和导航系统。

**文件路径**: `frontend/windows/main_window.py`  
**行数**: 203行

## 核心功能

### 1. MainWindow类

主窗口容器，负责页面切换和导航管理。

```python
class MainWindow(QMainWindow):
    """主窗口 - 页面导航容器
    
    使用QStackedWidget实现单页面应用风格的页面切换
    """
```

**核心特性**:
- **页面缓存**: 缓存已创建的页面实例，避免重复创建
- **导航历史栈**: 支持返回上一页功能
- **统一导航接口**: 所有页面通过统一的信号系统通信

### 2. 页面管理系统

#### 页面缓存机制

```python
# 页面缓存：{page_type: page_widget}
self.pages: Dict[str, any] = {}
```

**缓存策略**:
- 单实例页面（HOME, INSPIRATION, WORKSPACE, SETTINGS）: 直接缓存
- 多实例页面（DETAIL, WRITING_DESK）: 使用 `page_type_project_id` 作为缓存键

**示例**:
```python
# DETAIL页面缓存键
cache_key = f"DETAIL_{project_id}"  # 例如: "DETAIL_abc123"
```

#### 导航历史栈

```python
# 导航历史栈：[(page_type, params)]
self.navigation_history: List[Tuple[str, dict]] = []
```

**用途**:
- 支持 [`goBack()`](frontend/windows/main_window.py:70) 返回上一页
- 保持导航上下文
- 记录页面参数

### 3. 页面类型定义

支持的页面类型:

| 页面类型 | 说明 | 是否多实例 | 必需参数 |
|---------|------|-----------|---------|
| `HOME` | 首页 | ❌ | - |
| `INSPIRATION` | 灵感模式（创建项目） | ❌ | - |
| `WORKSPACE` | 项目列表 | ❌ | - |
| `DETAIL` | 项目详情 | ✅ | `project_id` |
| `WRITING_DESK` | 写作台 | ✅ | `project_id` |
| `SETTINGS` | 设置页面 | ❌ | - |

## 核心方法

### 1. navigateTo() - 页面导航

```python
def navigateTo(self, page_type: str, params: dict = None):
    """导航到指定页面
    
    Args:
        page_type: 页面类型（HOME, INSPIRATION, WORKSPACE等）
        params: 页面参数（如project_id等）
    """
```

**执行流程**:

```
1. 获取或创建页面实例
   ↓
2. 调用页面的refresh()方法
   ↓
3. 切换到目标页面
   ↓
4. 调用页面的onShow()钩子
   ↓
5. 添加到导航历史栈
```

**使用示例**:
```python
# 导航到首页
self.navigateTo('HOME')

# 导航到项目详情（带参数）
self.navigateTo('DETAIL', {'project_id': 'abc123'})
```

### 2. goBack() - 返回上一页

```python
def goBack(self):
    """返回上一页"""
    if len(self.navigation_history) <= 1:
        return  # 已经是第一页
    
    # 移除当前页
    current_page_info = self.navigation_history.pop()
    
    # 获取上一页信息
    prev_page_type, prev_params = self.navigation_history[-1]
```

**生命周期钩子**:
- 调用当前页面的 `onHide()` - 页面隐藏前
- 调用上一页面的 `onShow()` - 页面显示后

### 3. getOrCreatePage() - 页面获取/创建

```python
def getOrCreatePage(self, page_type: str, params: dict):
    """获取或创建页面实例"""
```

**缓存逻辑**:

```python
# 对于需要多实例的页面
if page_type in ['DETAIL', 'WRITING_DESK']:
    project_id = params.get('project_id', '')
    cache_key = f"{page_type}_{project_id}"
```

**信号连接**:
```python
# 连接导航信号
if hasattr(page, 'navigateRequested'):
    page.navigateRequested.connect(self.onNavigateRequested)

if hasattr(page, 'goBackRequested'):
    page.goBackRequested.connect(self.goBack)
```

### 4. createPage() - 页面实例化

```python
def createPage(self, page_type: str, params: dict):
    """创建页面实例"""
```

**页面创建映射**:

```python
if page_type == 'HOME':
    from pages.home_page import HomePage
    return HomePage(self)

elif page_type == 'DETAIL':
    from windows.novel_detail import NovelDetail
    project_id = params.get('project_id')
    return NovelDetail(project_id, self)
```

**错误处理**:
- 参数校验（必需参数检查）
- 异常捕获（创建失败）
- 友好错误提示

## 页面生命周期

### 页面钩子方法

页面可以实现以下钩子方法：

```python
class BasePage(QWidget):
    def refresh(self, **params):
        """页面刷新（每次导航到此页面时调用）"""
        pass
    
    def onShow(self):
        """页面显示后"""
        pass
    
    def onHide(self):
        """页面隐藏前"""
        pass
```

### 调用时机

```
navigateTo() 调用
    ↓
refresh(**params)  # 刷新页面数据
    ↓
setCurrentWidget()  # 切换显示
    ↓
onShow()  # 页面已显示

---

goBack() 调用
    ↓
onHide()  # 当前页面隐藏
    ↓
refresh(**params)  # 刷新目标页面
    ↓
setCurrentWidget()  # 切换显示
    ↓
onShow()  # 目标页面显示
```

## 信号系统

### 页面发出的信号

页面通过信号请求导航：

```python
class BasePage(QWidget):
    # 导航请求信号
    navigateRequested = pyqtSignal(str, dict)  # (page_type, params)
    
    # 返回请求信号
    goBackRequested = pyqtSignal()
```

### 使用示例

```python
class MyPage(BasePage):
    def openDetail(self, project_id):
        # 请求导航到详情页
        self.navigateRequested.emit('DETAIL', {'project_id': project_id})
    
    def goBack(self):
        # 请求返回上一页
        self.goBackRequested.emit()
```

## 架构设计

### 1. 单页面应用模式

```
┌─────────────────────────────────┐
│       MainWindow (QMainWindow)   │
│  ┌───────────────────────────┐  │
│  │  QStackedWidget           │  │
│  │  ┌─────────────────────┐  │  │
│  │  │  HomePage           │  │  │
│  │  ├─────────────────────┤  │  │
│  │  │  InspirationMode    │  │  │
│  │  ├─────────────────────┤  │  │
│  │  │  NovelWorkspace     │  │  │
│  │  ├─────────────────────┤  │  │
│  │  │  NovelDetail (多实例)│  │  │
│  │  ├─────────────────────┤  │  │
│  │  │  WritingDesk (多实例)│  │  │
│  │  ├─────────────────────┤  │  │
│  │  │  SettingsView       │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 2. 导航流程

```
用户操作
  ↓
页面发出 navigateRequested 信号
  ↓
MainWindow.onNavigateRequested()
  ↓
MainWindow.navigateTo()
  ↓
页面切换完成
```

### 3. 页面缓存策略

```python
# 伪代码
if page_type in cache:
    return cached_page
else:
    new_page = create_page(page_type)
    cache[page_type] = new_page
    return new_page
```

## 最佳实践

### 1. 页面参数传递

```python
# ✅ 推荐：通过params字典传递
self.navigateTo('DETAIL', {'project_id': project_id})

# ❌ 不推荐：直接传递给构造函数
detail_page = NovelDetail(project_id)  # 绕过了缓存机制
```

### 2. 导航历史管理

```python
# 导航历史栈示例
[
    ('HOME', {}),
    ('WORKSPACE', {}),
    ('DETAIL', {'project_id': 'abc123'}),  # 当前页
]

# 调用goBack()后
[
    ('HOME', {}),
    ('WORKSPACE', {}),  # 返回到此页
]
```

### 3. 多实例页面缓存

```python
# DETAIL页面缓存
pages = {
    'HOME': HomePage实例,
    'DETAIL_abc123': NovelDetail实例1,
    'DETAIL_def456': NovelDetail实例2,
    'WRITING_DESK_abc123': WritingDesk实例1,
}
```

## 错误处理

### 1. 页面创建失败

```python
def createPage(self, page_type: str, params: dict):
    try:
        # 创建页面
        if page_type == 'DETAIL':
            project_id = params.get('project_id')
            if not project_id:
                print("错误：DETAIL页面缺少project_id参数")
                return None
            return NovelDetail(project_id, self)
    except Exception as e:
        print(f"创建页面 {page_type} 失败：{e}")
        import traceback
        traceback.print_exc()
        return None
```

### 2. 参数校验

```python
# DETAIL和WRITING_DESK页面必须提供project_id
if page_type in ['DETAIL', 'WRITING_DESK']:
    if not params.get('project_id'):
        print(f"错误：{page_type}页面缺少project_id参数")
        return None
```

## 依赖关系

### 导入的页面类

```python
from pages.home_page import HomePage
from windows.inspiration_mode import InspirationMode
from windows.novel_workspace import NovelWorkspace
from windows.novel_detail import NovelDetail
from windows.writing_desk import WritingDesk
from windows.settings_view import SettingsView
```

### 核心依赖

- **PyQt6.QtWidgets**: QMainWindow, QStackedWidget
- **typing**: Dict, List, Tuple（类型提示）

## 使用示例

### 完整导航流程

```python
# 1. 应用启动，显示首页
window = MainWindow()  # 自动导航到 HOME
window.show()

# 2. 用户从首页进入项目列表
# HomePage 内部调用:
self.navigateRequested.emit('WORKSPACE', {})

# 3. 用户查看项目详情
# NovelWorkspace 内部调用:
self.navigateRequested.emit('DETAIL', {'project_id': 'abc123'})

# 4. 用户返回项目列表
# NovelDetail 内部调用:
self.goBackRequested.emit()
```

### 自定义页面集成

```python
# 1. 在 MainWindow.createPage() 中添加新页面类型
def createPage(self, page_type: str, params: dict):
    # ... 现有代码
    
    elif page_type == 'MY_NEW_PAGE':
        from pages.my_new_page import MyNewPage
        return MyNewPage(self)

# 2. 在其他页面中导航到新页面
self.navigateRequested.emit('MY_NEW_PAGE', {})
```

## 性能优化

### 1. 页面缓存

**优点**:
- 避免重复创建页面实例
- 保持页面状态
- 提升导航速度

**缺点**:
- 占用内存
- 需要手动刷新数据

### 2. 延迟加载

```python
# 页面类在 createPage() 时才导入
if page_type == 'DETAIL':
    from windows.novel_detail import NovelDetail  # 延迟导入
    return NovelDetail(project_id, self)
```

**好处**:
- 减少启动时间
- 降低内存占用
- 模块化加载

## 注意事项

1. **页面缓存键**: 多实例页面必须包含唯一标识（如project_id）
2. **导航历史**: 不要手动修改 `navigation_history`，使用 `navigateTo()` 和 `goBack()`
3. **页面刷新**: 使用 `refresh()` 方法更新页面数据，而非重新创建页面
4. **信号连接**: 页面必须定义 `navigateRequested` 和 `goBackRequested` 信号
5. **错误处理**: `createPage()` 返回 `None` 时，`navigateTo()` 会安全退出

## 相关文件

- [`frontend/main.py`](frontend/main.py) - 应用入口
- [`frontend/pages/base_page.py`](frontend/pages/base_page.py) - 页面基类
- [`frontend/pages/home_page.py`](frontend/pages/home_page.py) - 首页实现
- [`frontend/windows/novel_detail.py`](frontend/windows/novel_detail.py) - 项目详情页
- [`frontend/windows/writing_desk.py`](frontend/windows/writing_desk.py) - 写作台

## 总结

