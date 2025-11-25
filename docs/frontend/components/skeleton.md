
# skeleton.py - 骨架屏加载组件

## 文件路径
`frontend/components/skeleton.py`

## 模块概述
禅意风格的骨架屏加载组件，提供更优雅的加载状态显示，替代简单的Loading文字。符合2025年UI设计趋势，模拟真实内容结构，提供非阻塞式加载提示。

## 设计理念
- **模拟真实结构**: 按照实际内容布局设计骨架屏
- **平滑闪烁动画**: 使用透明度动画展示加载状态
- **可自定义形状**: 支持线条、圆形等多种形状
- **非阻塞式提示**: 不影响用户浏览页面结构

## 主要类

### 1. SkeletonLine - 骨架屏单行元素
**继承**: `QFrame`

模拟文本行或单行内容的骨架屏元素。

#### 初始化参数
- `width: str | int = '100%'` - 宽度（百分比或像素）
- `height: int = 16` - 高度（像素）
- `radius: int = 8` - 圆角半径
- `parent: QWidget = None` - 父组件

#### 核心属性
- `width_percentage: int | None` - 百分比宽度值
- `opacity_effect: QGraphicsOpacityEffect` - 透明度效果
- `animation: QPropertyAnimation` - 闪烁动画

#### 闪烁动画配置
```python
animation.setDuration(1500)        # 1.5秒周期
animation.setStartValue(1.0)       # 完全不透明
animation.setEndValue(0.3)         # 30%透明度
animation.setEasingCurve(QEasingCurve.Type.InOutSine)  # 平滑曲线
animation.setLoopCount(-1)         # 无限循环
```

#### 样式特点
```python
background-color: {ZenTheme.BG_TERTIARY}  # 浅灰色背景
border-radius: {radius}px
```

---

### 2. SkeletonCircle - 骨架屏圆形元素
**继承**: `QFrame`

用于模拟头像等圆形内容的骨架屏。

#### 初始化参数
- `size: int = 64` - 圆形尺寸
- `parent: QWidget = None` - 父组件

#### 核心特点
```python
# 固定宽高为正方形
self.setFixedSize(size, size)

# 圆角半径为尺寸的一半，形成完美圆形
border-radius: {size // 2}px
```

#### 动画效果
与SkeletonLine相同的闪烁动画配置。

---

### 3. SkeletonCard - 骨架屏卡片
**继承**: `QFrame`

模拟卡片内容结构的复合骨架屏组件。

#### 初始化参数
- `has_avatar: bool = False` - 是否包含头像
- `lines: int = 3` - 内容行数
- `parent: QWidget = None` - 父组件

#### 布局结构
```python
# 基础结构
[Card Container]
├── Header (可选)
│   ├── Avatar (SkeletonCircle 48px)
│   └── Title Container
│       ├── Title (SkeletonLine 60% width, 20px height)
│       └── Subtitle (SkeletonLine 40% width, 14px height)
└── Content Lines
    ├── Line 1 (100% width)
    ├── Line 2 (100% width)
    └── Line 3 (70% width, 最后一行较短)
```

#### 样式配置
```python
background-color: {ZenTheme.BG_CARD}
border: 1px solid {ZenTheme.BORDER_LIGHT}
border-radius: {ZenTheme.RADIUS_LG}
padding: 20px
spacing: 12px
```

---

### 4. SkeletonList - 骨架屏列表
**继承**: `QWidget`

多个卡片堆叠的列表骨架屏。

#### 初始化参数
- `card_count: int = 3` - 卡片数量
- `has_avatar: bool = True` - 卡片是否有头像
- `lines: int = 3` - 每个卡片的内容行数
- `parent: QWidget = None` - 父组件

#### 布局特点
```python
layout.setSpacing(16)  # 卡片间距
layout.setContentsMargins(0, 0, 0, 0)

# 垂直排列多个SkeletonCard
for _ in range(card_count):
    card = SkeletonCard(has_avatar, lines)
    layout.addWidget(card)
```

---

### 5. SkeletonTable - 骨架屏表格
**继承**: `QWidget`

模拟表格结构的骨架屏。

#### 初始化参数
- `rows: int = 5` - 数据行数
- `columns: int = 4` - 列数
- `parent: QWidget = None` - 父组件

#### 布局结构
```python
[Table Container]
├── Header Row
│   ├── Column 1 (20px height)
│   ├── Column 2 (20px height)
│   └── ...
└── Data Rows
    ├── Row 1
    │   ├── Cell 1 (16px height)
    │   ├── Cell 2 (16px height)
    │   └── ...
    └── ...
```

#### 样式特点
```python
# 表头
height: 20px
radius: 10px

# 单元格
height: 16px
radius: 8px

# 间距
row_spacing: 12px
column_spacing: 12px
```

---

### 6. SkeletonDetailPage - 骨架屏详情页
**继承**: `QWidget`

模拟完整详情页结构的复合骨架屏。

#### 布局结构
```python
[Detail Page]
├── Title Area
│   ├── Title (300px × 32px)
│   ├── Action Button 1 (100px × 36px)
│   └── Action Button 2 (100px × 36px)
├── Meta Info Row
│   ├── Meta 1 (80px × 14px)
│   ├── Meta 2 (100px × 14px)
│   └── Meta 3 (120px × 14px)
├── Content Card
│   └── Paragraphs (5行)
│       ├── Line 1-4 (100% width)
│       └── Line 5 (85% width)
└── Bottom Row
    ├── Card 1
    └── Card 2
```

#### 样式配置
```python
# 整体
padding: 24px
spacing: 24px

# 内容卡片
background-color: {ZenTheme.BG_CARD}
border: 1px solid {ZenTheme.BORDER_LIGHT}
border-radius: {ZenTheme.RADIUS_LG}
padding: 24px
```

---

### 7. SkeletonPresets - 骨架屏预设模板
**静态类**

提供常用场景的预设骨架屏模板。

#### 预设方法

##### novel_list(parent)
```python
@staticmethod
def novel_list(parent=None):
    """小说列表骨架屏
    
    配置: 4个卡片，有头像，2行内容
    """
    return SkeletonList(card_count=4, has_avatar=True, lines=2, parent=parent)
```

##### chapter_list(parent)
```python
@staticmethod
def chapter_list(parent=None):
    """章节列表骨架屏
    
    配置: 6个卡片，无头像，2行内容
    """
    return SkeletonList(card_count=6, has_avatar=False, lines=2, parent=parent)
```

##### novel_detail(parent)
```python
@staticmethod
def novel_detail(parent=None):
    """小说详情骨架屏
    
    返回: SkeletonDetailPage实例
    """
    return SkeletonDetailPage(parent=parent)
```

##### data_table(parent)
```python
@staticmethod
def data_table(parent=None):
    """数据表格骨架屏
    
    配置: 8行 × 5列
    """
    return SkeletonTable(rows=8, columns=5, parent=parent)
```

##### simple_card(parent)
```python
@staticmethod
def simple_card(parent=None):
    """简单卡片骨架屏
    
    配置: 无头像，3行内容
    """
    return SkeletonCard(has_avatar=False, lines=3, parent=parent)
```

## 动画实现原理

### 1. 透明度动画
```python
# 创建透明度效果
opacity_effect = QGraphicsOpacityEffect(self)
self.setGraphicsEffect(opacity_effect)

# 创建属性动画
animation = QPropertyAnimation(opacity_effect, b"opacity")
animation.setDuration(1500)
animation.setStartValue(1.0)      # 不透明
animation.setEndValue(0.3)        # 半透明
animation.setEasingCurve(QEasingCurve.Type.InOutSine)
animation.setLoopCount(-1)        # 无限循环
animation.start()
```

### 2. 缓动曲线
使用 `InOutSine` 缓动曲线实现平滑的渐变效果：
- **InOut**: 开始和结束都较慢，中间较快
- **Sine**: 正弦曲线，更自然的变化

## 使用示例

### 1. 基础线条
```python
from components.skeleton import SkeletonLine

# 创建标题骨架
title_skeleton = SkeletonLine(width='60%', height=24, radius=12)
layout.addWidget(title_skeleton)

# 创建内容行骨架
content_skeleton = SkeletonLine(width='100%', height=16, radius=8)
layout.addWidget(content_skeleton)
```

### 2. 带头像的卡片
```python
from components.skeleton import SkeletonCard

# 创建卡片骨架
card_skeleton = SkeletonCard(has_avatar=True, lines=3)
layout.addWidget(card_skeleton)
```

### 3. 列表骨架屏
```python
from components.skeleton import SkeletonList

# 创建列表骨架
list_skeleton = SkeletonList(
    card_count=5,
    has_avatar=True,
    lines=2
)
layout.addWidget(list_skeleton)
```

### 4. 使用预设模板
```python
from components.skeleton import SkeletonPresets

# 小说列表骨架屏
novel_skeleton = SkeletonPresets.novel_list(parent=self)
self.layout.addWidget(novel_skeleton)

# 加载完成后替换为真实内容
def on_data_loaded(data):
    novel_skeleton.deleteLater()
    # 显示真实内容
    self.show_real_content(data)
```

### 5. 在页面中集成
```python
class MyPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        
        # 初始显示骨架屏
        self.skeleton = SkeletonPresets.novel_list(parent=self)
        self.layout.addWidget(self.skeleton)
    
    def load_data(self):
        # 异步加载数据
        worker = AsyncWorker(self.fetch_data)
        worker.finished.connect(self.on_data_loaded)
        worker.start()
    
    def on_data_loaded(self, data):
        # 移除骨架屏
        self.skeleton.deleteLater()
        
        # 显示真实内容
        for item in data:
            card = NovelCard(item)
            self.layout.addWidget(card)
```

## 设计模式与最佳实践

### 1. 渐进式替换
```python
# 不推荐：突然切换
skeleton.hide()
real_content.show()

# 推荐：淡入淡出过渡
def smooth_replace():
    # 淡出骨架屏
    fade_out = QPropertyAnimation(skeleton, b"opacity")
    fade_out.setDuration(200)
    fade_out.setEndValue(0)
    fade_out.finished.connect(lambda: self.show_real_content())
    fade_out.start()
```

### 2. 宽度自适应
```python
# 百分比宽度会自动适应父容器
line = SkeletonLine(width='80%')  # 父容器宽度的80%

# 固定宽度不会改变
line = SkeletonLine(width=300)    # 固定300px
```

### 3. 最后一行较短原则
```python
# 模拟真实文本，最后一行通常较短
for i in range(lines):
    width = '70%' if i == lines - 1 else '100%'
    line = SkeletonLine(width=width)
```

### 4. 选择合适的预设
```python
# 根据页面类型选择预设
if page_type == 'list':
    skeleton = SkeletonPresets.novel_list()
elif page_type == 'detail':
    skeleton = SkeletonPresets.novel_detail()
elif page_type == 'table':
    skeleton = SkeletonPresets.data_table()
```

## 性能优化

### 1. 动画复用
所有骨架屏元素共享相同的动画配置，减少资源消耗。

### 2. 按需创建
```python
# 只在需要时创建骨架屏
def show_loading(self):
    if not hasattr(self, 'skeleton'):
        self.skeleton = SkeletonPresets.novel_list(parent=self)
    self.skeleton.show()
```

### 3. 及时清理
```python
def on_loaded(self):
    # 使用deleteLater确保资源释放
    self.skeleton.deleteLater()
    self.skeleton = None
```

## 与其他组件的关系
- **LoadingSpinner**: 骨架屏用于结构化内容，Spinner用于简单操作
- **EmptyState**: 加载失败时可从骨架屏切换到空状态
- **AsyncWorker**: 配合异步数据加载使用
- **Pages**: 各页面集成骨架屏提升用户体验

## 技术亮点

1. **智能宽度**: 支持百分比和固定宽度两种模式
2. **平滑动画**: InOutSine缓动曲线提供自然的视觉效果
3. **模块化设计**: 基础元素可组合成复杂布局
4. **预设模板**: 常用场景开箱即用
5. **禅意风格**: 配色和间距符合ZenTheme设计规范

## 注意事项

1. 