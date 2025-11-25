# loading_spinner.py - 加载动画组件

## 文件路径
`frontend/components/loading_spinner.py`

## 模块概述
提供多种样式的加载动画组件，用于显示异步操作的加载状态。包含圆形旋转动画、点状跳动动画、全屏遮罩和内联加载等多种样式。

## 主要类

### 1. CircularSpinner - 圆形旋转加载动画
**继承**: `QWidget`

Material Design风格的圆形进度指示器。

#### 初始化参数
- `size: int = 40` - 动画尺寸（像素）
- `color: str = "#4f46e5"` - 动画颜色（十六进制）
- `parent: QWidget = None` - 父组件

#### 核心属性
- `size: int` - 动画尺寸
- `color: QColor` - 动画颜色
- `angle: int` - 当前旋转角度（0-360）
- `timer: QTimer` - 动画定时器（60 FPS）

#### 核心方法

##### rotate()
```python
def rotate(self):
    """旋转动画
    
    每次调用增加6度，实现平滑旋转
    """
```

##### paintEvent(event)
```python
def paintEvent(self, event):
    """绘制旋转的圆弧
    
    使用QPainter绘制270度圆弧，模拟加载动画
    """
```

##### start() / stop()
```python
def start(self):
    """启动动画"""

def stop(self):
    """停止动画"""
```

---

### 2. DotsSpinner - 点状加载动画
**继承**: `QWidget`

三个点依次跳动的动画效果。

#### 初始化参数
- `color: str = "#4f46e5"` - 点的颜色
- `parent: QWidget = None` - 父组件

#### 核心属性
- `color: QColor` - 点的颜色
- `step: int` - 当前动画步骤（0-3）
- `timer: QTimer` - 动画定时器（200ms间隔）

#### 核心方法

##### animate()
```python
def animate(self):
    """切换动画状态
    
    每200ms切换一次，循环显示三个点的跳动
    """
```

##### paintEvent(event)
```python
def paintEvent(self, event):
    """绘制三个点
    
    根据step值调整每个点的Y位置和透明度：
    - 活动点：上移3px，透明度255
    - 非活动点：正常位置，透明度100
    """
```

---

### 3. LoadingOverlay - 全屏半透明加载遮罩
**继承**: `QWidget`

覆盖在内容上方，显示加载动画和提示文字。

#### 初始化参数
- `text: str = "加载中..."` - 提示文字
- `spinner_type: str = "circular"` - 动画类型（circular/dots）
- `parent: QWidget = None` - 父组件

#### 核心属性
- `spinner: CircularSpinner | DotsSpinner` - 加载动画实例
- `label: QLabel` - 提示文字标签

#### 样式特点
```python
# 遮罩层样式
background-color: rgba(255, 255, 255, 0.9)  # 90%白色半透明

# 文字样式
font-size: 15px
color: #64748b
font-weight: 500
```

#### 核心方法

##### setText(text)
```python
def setText(self, text: str):
    """更新显示文字"""
```

##### show() / hide()
```python
def show(self):
    """显示遮罩并启动动画"""

def hide(self):
    """隐藏遮罩并停止动画"""
```

---

### 4. InlineSpinner - 内联加载动画
**继承**: `QWidget`

用于按钮或行内显示的小型加载指示器。

#### 初始化参数
- `text: str = "处理中..."` - 提示文字
- `size: int = 16` - 动画尺寸
- `parent: QWidget = None` - 父组件

#### 核心属性
- `spinner: CircularSpinner` - 小型圆形动画（灰色）
- `label: QLabel` - 文字标签

#### 布局特点
```python
layout.setContentsMargins(0, 0, 0, 0)
layout.setSpacing(8)
# 水平布局：[spinner] [text]
```

#### 样式特点
```python
# 小型spinner
size: 16px
color: #6b7280

# 文字
font-size: 13px
color: #6b7280
```

## 设计模式与特点

### 1. 动画实现机制
```python
# 使用QTimer实现动画循环
timer = QTimer(self)
timer.timeout.connect(self.rotate)  # 连接到动画函数
timer.start(16)  # 约60 FPS
```

### 2. 自定义绘制
```python
def paintEvent(self, event):
    painter = QPainter(self)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 抗锯齿
    
    # 绘制圆弧
    painter.drawArc(rect, self.angle * 16, 270 * 16)  # Qt使用1/16度单位
```

### 3. 生命周期管理
- **显示时自动启动**: `show()` → `spinner.start()`
- **隐藏时自动停止**: `hide()` → `spinner.stop()`
- **防止重复启动**: `if not self.timer.isActive()`

## 使用示例

### 1. 圆形旋转动画
```python
from components.loading_spinner import CircularSpinner

# 创建动画
spinner = CircularSpinner(size=48, color="#4f46e5")
layout.addWidget(spinner)

# 控制动画
spinner.start()
spinner.stop()
```

### 2. 全屏加载遮罩
```python
from components.loading_spinner import LoadingOverlay

# 创建遮罩
overlay = LoadingOverlay(
    text="正在加载数据...",
    spinner_type="circular",
    parent=self
)

# 显示遮罩
overlay.show()

# 更新文字
overlay.setText("正在处理...")

# 隐藏遮罩
overlay.hide()
```

### 3. 内联加载指示器
```python
from components.loading_spinner import InlineSpinner

# 创建内联动画
inline_spinner = InlineSpinner(text="正在保存...", size=16)
button_layout.addWidget(inline_spinner)

# 显示/隐藏
inline_spinner.show()
inline_spinner.hide()
```

### 4. 点状动画
```python
from components.loading_spinner import DotsSpinner

# 创建点状动画
dots = DotsSpinner(color="#4f46e5")
layout.addWidget(dots)

dots.start()
dots.stop()
```

## 性能优化

### 1. 定时器频率
```python
# 圆形动画: 60 FPS
self.timer.start(16)  # 16ms ≈ 60 FPS

# 点状动画: 5 FPS  
self.timer.start(200)  # 200ms = 5 FPS
```

### 2. 资源清理
```python
def stop(self):
    """停止动画时释放定时器资源"""
    self.timer.stop()
```

## 最佳实践

### 1. 选择合适的动画类型
- **CircularSpinner**: 通用场景，专业感强
- **DotsSpinner**: 轻量级操作，友好感强
- **LoadingOverlay**: 全页面加载，阻止交互
- **InlineSpinner**: 按钮内嵌，局部反馈

### 2. 动画颜色选择
```python
# 主题色（强调）
spinner = CircularSpinner(color="#4f46e5")

# 中性色（低调）
spinner = CircularSpinner(color="#6b7280")

# 成功色
spinner = CircularSpinner(color="#10b981")
```

### 3. 自动启停管理
```python
class MyWidget(QWidget):
    def start_loading(self):
        self.overlay = LoadingOverlay(parent=self)
        self.overlay.show()  # 自动启动动画
    
    def stop_loading(self):
        self.overlay.hide()  # 自动停止动画
```

## 与其他组件的关系
- **TaskProgressDialog**: 使用LoadingOverlay显示任务进度
- **AsyncWorker**: 配合异步任务显示加载状态
- **Toast**: 可在Toast中使用InlineSpinner
- **Skeleton**: 骨架屏与加载动画互补使用

## 注意事项

1. **定时器清理**: 确保在隐藏或删除组件时停止定时器
2. **父组件尺寸**: LoadingOverlay需要正确的父组件尺寸才能居中
3. **透明度设置**: 使用`WA_TranslucentBackground`属性支持半透明
4. **性能考虑**: 大量动画同时运行可能影响性能
5. **线程安全**: 在异步任务中更新UI需使用信号槽机制

## 技术亮点

1. **平滑动画**: 使用QTimer实现流畅的60 FPS动画
2. **自定义绘制**: QPainter实现完全自定义的动画效果
3. **灵活配置**: 支持自定义尺寸、颜色和文字
4. **自动管理**: 显示/隐藏时自动启停动画
5. **多种样式**: 提供4种不同场景的加载组件