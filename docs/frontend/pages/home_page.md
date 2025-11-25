
# frontend/pages/home_page.py

## 模块概述

首页模块，作为应用的主入口页面，采用现代柔和的新中式禅意风格设计。该页面为用户提供两个核心功能入口：灵感涌现模式和小说工作台，通过精美的卡片式布局和流畅的动画效果营造舒适的使用体验。

**设计风格：**
- 温暖浅米白色背景
- 沉静灰绿色点缀
- 水墨纹理渐变
- 超大圆角、细微长投影、漂浮感
- 淡入浮现动画

**核心功能：**
- 灵感模式入口（概念对话）
- 工作台入口（项目管理）
- LLM设置快捷入口

## 主要类

### 1. ZenEntryCard

禅意风格入口卡片组件，用于主页的功能入口展示。

#### 特点

- 超大圆角（32px）
- 灰绿色细微长投影（漂浮感）
- 毛玻璃磨砂质感
- 淡入浮现动画
- 点击时颜色填充动画
- hover时微妙的上浮效果

#### 信号定义

```python
clicked = pyqtSignal()  # 卡片被点击
```

#### 初始化方法

```python
def __init__(self, icon_text, title, description, accent_color="#8B9A8A", parent=None):
    """
    初始化卡片
    
    Args:
        icon_text: 图标文字（Unicode字符）
        title: 卡片标题
        description: 卡片描述
        accent_color: 强调色（默认灰绿色）
        parent: 父组件
    """
```

#### 核心方法

**setupUI() - 初始化UI**

创建卡片的UI结构：
- 圆形图标容器（80x80px）
- 标题（26px，字重700）
- 描述（15px，字重400）
- 超大圆角卡片外框（32px）

**updateCardStyle() - 更新卡片样式**

```python
def updateCardStyle(self, is_hover):
    """更新卡片样式
    
    Args:
        is_hover: 是否为hover状态
    """
```

根据hover状态动态更新：
- 背景透明度（默认0.65，hover时0.85）
- 边框颜色（默认浅灰，hover时强调色）
- 投影大小（默认20px，hover时25px）
- 投影透明度（默认35，hover时50）

**fadeIn() - 淡入浮现动画**

```python
def fadeIn(self):
    """淡入浮现动画"""
    self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
    self.fade_animation.setDuration(800)
    self.fade_animation.setStartValue(0.0)
    self.fade_animation.setEndValue(1.0)
    self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    self.fade_animation.start()
```

**事件处理**

```python
def mousePressEvent(self, event):
    """鼠标点击 - 颜色填充动画"""
    # 点击时短暂变色，150ms后发射clicked信号

def enterEvent(self, event):
    """鼠标进入 - 微妙的上浮动画（4px）"""
    # 400ms缓动动画

def leaveEvent(self, event):
    """鼠标离开 - 恢复位置"""
    # 400ms缓动动画
```

### 2. HomePage

首页主类，继承自 `BasePage`。

#### 布局结构

```
HomePage
└── 主容器（渐变背景）
    ├── 头部（右上角LLM设置按钮）
    └── 中央内容区（最大宽度1100px）
        ├── 主标题（"拯救小说家"，52px）
        ├── 副标题（"灵感如潮 落笔成章"，20px）
        ├── 分隔线（120px宽，灰绿色）
        ├── 引导文字（"择一而始"）
        └── 卡片容器（最大宽度900px）
            ├── 灵感涌现卡片
            └── 工作台卡片
```

#### setupUI() - 初始化UI

创建完整的首页布局：

**背景渐变：**
```python
background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #FAF7F0,   # 温暖米白色
    stop:0.3 #F5F1E8,
    stop:0.6 #F0ECE3,
    stop:1 #EBE7DD);
```

**LLM设置按钮：**
- 位置：右上角
- 样式：半透明灰绿色背景，圆角20px
- 功能：导航到设置页面

**灵感涌现卡片：**
- 图标：◐（阴阳符号）
- 标题：灵感涌现
- 描述：与AI对话，让创意自然流淌，构建故事的初章
- 强调色：#8B9A8A（灰绿色1）

**工作台卡片：**
- 图标：◑（阴阳符号）
- 标题：工作台
- 描述：沉浸创作，精雕细琢，打磨你的世界
- 强调色：#9BAA99（灰绿色2）

## 使用示例

### 1. 基本使用

```python
from pages.home_page import HomePage

# 创建首页
home_page = HomePage()

# 连接导航信号
home_page.navigateRequested.connect(lambda page_type, params: 
    print(f"导航到: {page_type}, 参数: {params}")
)

# 显示页面
home_page.show()
```

### 2. 在主窗口中集成

```python
from PyQt6.QtWidgets import QMainWindow, QStackedWidget
from pages.home_page import HomePage
from windows.inspiration_mode import InspirationModeWindow
from windows.novel_workspace import NovelWorkspaceWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # 添加首页
        self.home_page = HomePage()
        self.home_page.navigateRequested.connect(self.handle_navigation)
        self.stack.addWidget(self.home_page)
        
        # 显示首页
        self.stack.setCurrentWidget(self.home_page)
    
    def handle_navigation(self, page_type, params):
        """处理页面导航"""
        if page_type == 'INSPIRATION':
            # 打开灵感模式窗口
            inspiration_window = InspirationModeWindow(self)
            inspiration_window.show()
        
        elif page_type == 'WORKSPACE':
            # 打开工作台窗口
            workspace_window = NovelWorkspaceWindow(self)
            workspace_window.show()
        
        elif page_type == 'SETTINGS':
            # 导航到设置页面
            self.show_settings_page()
```

### 3. 自定义卡片

```python
from pages.home_page import ZenEntryCard

# 创建自定义卡片
custom_card = ZenEntryCard(
    icon_text="✦",
    title="数据分析",
    description="深入了解你的创作数据",
    accent_color="#7A8B7A"  # 深灰绿色
)

# 连接点击事件
custom_card.clicked.connect(lambda: print("卡片被点击"))

# 添加到布局
layout.addWidget(custom_card)
```

### 4. 动态修改卡片

```python
class DynamicCard(ZenEntryCard):
    def __init__(self):
        super().__init__(
            icon_text="◉",
            title="动态卡片",
            description="点击更新内容",
            accent_color="#8B9A8A"
        )
        self.click_count = 0
        self.clicked.connect(self.on_clicked)
    
    def on_clicked(self):
        """点击时更新内容"""
        self.click_count += 1
        
        # 更新标题
        title_label = self.findChild(QLabel)
        if title_label:
            title_label.setText(f"点击次数: {self.click_count}")
```

## 设计理念

### 1. 禅意美学

**极简主义：**
- 只保留必要元素
- 大量留白营造呼吸感
- 去除多余装饰

**诗意表达：**
- 主标题："拯救小说家"（体现产品使命）
- 副标题："灵感如潮 落笔成章"（意境优美）
- 引导文字："择一而始"（简洁有力）

**自然色彩：**
- 温暖的米白色系（舒适、宁静）
- 灰绿色强调（源于自然、低饱和度）
- 水墨渐变（东方美学）

### 2. 视觉层次

**字重对比：**
- 主标题：300（极细，诗意）
- 卡片标题：700（加粗，强调）
- 描述文字：400（正常，易读）

**字间距对比：**
- 主标题：8px（宽松，气度）
- 副标题：4px（适中）
- 引导文字：3px（紧凑）

**圆角对比：**
- 卡片：32px（超大，柔和）
- 图标容器：40px（圆形）
- 设置按钮：20px（中等）

### 3. 动画设计

**淡入动画：**
- 时长：800ms
- 缓动：OutCubic（柔和减速）
- 延迟：100ms（避免闪烁）

**hover动画：**
- 上浮距离：4px（微妙）
- 时长：400ms
- 缓动：OutCubic

**点击动画：**
- 颜色填充：150ms
- 立即视觉反馈

### 4. 用户体验

**明确的视觉反馈：**
- hover：边框变色、投影增强、上浮
- press：背景填充强调色
- cursor：指针变为手型

**无缝导航：**
- 点击卡片直接进入对应功能
- 设置按钮始终可见
- 无需额外操作

**性能优化：**
- 动画使用QPropertyAnimation（硬件加速）
- 延迟启动淡入动画（避免卡顿）
- 复用QGraphicsEffect对象

## 技术亮点

### 1. 毛玻璃效果

```python
background-color: rgba(255, 255, 255, 0.65);  # 半透明白色
```

通过rgba透明度实现毛玻璃质感，配合渐变背景形成层次感。

### 2. 灰绿色投影

```python
shadow.setColor(QColor(139, 154, 138, 35))  # 灰绿色，透明度约15%
shadow.setOffset(0, 6)  # Y轴偏移6px
```

使用灰绿色投影而非传统黑色，保持禅意风格统一。

### 3. 动态样式更新

```python
def updateCardStyle(self, is_hover):
    