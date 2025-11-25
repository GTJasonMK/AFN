
# toast.py - Toast通知组件

## 文件路径
`frontend/components/toast.py`

## 模块概述
禅意风格的现代化非阻塞式通知系统，替代传统QMessageBox。符合2025年桌面UI最佳实践，提供优雅的动画效果和多种通知类型。

## 设计理念
- **非阻塞式通知**: 不中断用户操作
- **自动消失**: 可配置的显示时长
- **类型多样**: 成功、错误、警告、信息四种类型
- **优雅动画**: 淡入淡出过渡效果
- **可堆叠显示**: 多个通知自动排列

## 主要类

### 1. Toast - 单个Toast通知组件
**继承**: `QWidget`

单个Toast通知的实现，包含图标、消息和关闭按钮。

#### 初始化参数
- `message: str` - 消息内容
- `toast_type: str = 'info'` - 类型（success/error/warning/info）
- `duration: int = 3000` - 显示时长（毫秒），0表示不自动关闭
- `parent: QWidget = None` - 父组件

#### 信号
- `closed: pyqtSignal()` - Toast关闭时发射

#### 窗口特性
```python
# 无边框、工具窗口、置顶
Qt.WindowType.FramelessWindowHint
Qt.WindowType.Tool
Qt.WindowType.WindowStaysOnTopHint

# 半透明背景
WA_TranslucentBackground
WA_ShowWithoutActivating  # 显示时不激活
```

#### 核心属性
- `message: str` - 消息文本
- `toast_type: str` - 通知类型
- `duration: int` - 显示时长
- `opacity_effect: QGraphicsOpacityEffect` - 透明度效果
- `animation: QPropertyAnimation` - 淡入淡出动画

#### 布局结构
```python
[Toast Container (400px fixed width)]
├── Icon Label (40px × 40px)
├── Message Label (自动换行)
└── Close Button (24px × 24px, "×")
```

#### 颜色方案

##### Success (成功)
```python
{
    'bg': ZenTheme.SUCCESS_BG,      # 浅绿色背景
    'border': ZenTheme.SUCCESS,     # 绿色边框
    'icon': ZenTheme.SUCCESS,       # 绿色图标
    'text': ZenTheme.TEXT_PRIMARY,  # 主文本色
    'close': ZenTheme.SUCCESS       # 绿色关闭按钮
}
```

##### Error (错误)
```python
{
    'bg': ZenTheme.ERROR_BG,        # 浅红色背景
    'border': ZenTheme.ERROR,       # 红色边框
    'icon': ZenTheme.ERROR,         # 红色图标
    'text': ZenTheme.TEXT_PRIMARY,
    'close': ZenTheme.ERROR
}
```

##### Warning (警告)
```python
{
    'bg': ZenTheme.WARNING_BG,      # 浅黄色背景
    'border': ZenTheme.WARNING,     # 黄色边框
    'icon': ZenTheme.WARNING,       # 黄色图标
    'text': ZenTheme.TEXT_PRIMARY,
    'close': ZenTheme.WARNING
}
```

##### Info (信息)
```python
{
    'bg': ZenTheme.INFO_BG,         # 浅蓝色背景
    'border': ZenTheme.INFO,        # 蓝色边框
    'icon': ZenTheme.INFO,          # 蓝色图标
    'text': ZenTheme.TEXT_PRIMARY,
    'close': ZenTheme.INFO
}
```

#### 图标映射
```python
icons = {
    'success': '✓',  # 对勾
    'error': '✗',    # 叉号
    'warning': '⚠',  # 警告三角
    'info': 'ℹ'      # 信息圆圈
}
```

#### 核心方法

##### show()
```python
def show(self):
    """显示Toast（带淡入动画）"""
    super().show()
    self.fadeIn()
```

##### fadeIn()
```python
def fadeIn(self):
    """淡入动画
    
    - 时长: 300ms
    - 从透明到不透明 (0.0 → 1.0)
    - 缓动曲线: OutCubic（快速开始，缓慢结束）
    """
```

##### fadeOut()
```python
def fadeOut(self):
    """淡出动画
    
    - 时长: 300ms
    - 从不透明到透明 (1.0 → 0.0)
    - 缓动曲线: InCubic（缓慢开始，快速结束）
    - 完成后触发: onFadeOutFinished()
    """
```

##### onFadeOutFinished()
```python
def onFadeOutFinished(self):
    """淡出完成后关闭
    
    1. 发射closed信号
    2. 关闭窗口
    3. 标记为待删除
    """
```

---

### 2. ToastManager - Toast管理器
**单例模式**

管理多个Toast的显示位置和生命周期。

#### 单例实现
```python
class ToastManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.toasts = []
            cls._instance.spacing = 12
            cls._instance.margin_bottom = 80
            cls._instance.margin_right = 24
        return cls._instance
```

#### 核心属性
- `toasts: List[Toast]` - 当前显示的Toast列表
- `spacing: int = 12` - Toast之间的间距
- `margin_bottom: int = 80` - 距离屏幕底部的边距
- `margin_right: int = 24` - 距离屏幕右侧的边距

#### 核心方法

##### show(message, toast_type, duration, parent)
```python
def show(self, message, toast_type='info', duration=3000, parent=None):
    """显示Toast通知
    
    Args:
        message: 消息内容
        toast_type: 类型（success/error/warning/info）
        duration: 显示时长（毫秒），0表示不自动关闭
        parent: 父窗口
    
    Returns:
        Toast: 创建的Toast实例
    
    流程:
        1. 创建Toast实例
        2. 连接closed信号
        3. 添加到列表
        4. 更新所有Toast位置
        5. 显示Toast
    """
```

##### removeToast(toast)
```python
def removeToast(self, toast):
    """移除Toast
    
    从列表中移除指定Toast，并更新其他Toast的位置
    """
```

##### updatePositions()
```python
def updatePositions(self):
    """更新所有Toast的位置（右下角堆叠）
    
    布局策略:
        - 获取主屏幕尺寸
        - 从下往上堆叠
        - 右对齐，距离右边margin_right
        - Toast之间间距spacing
    
    示例位置计算:
        y_offset = screen.height() - margin_bottom
        for toast in reversed(toasts):
            x = screen.width() - toast.width() - margin_right
            y = y_offset - toast.height()
            toast.move(x, y)
            y_offset = y - spacing
    """
```

##### 便捷方法
```python
def success(self, message, duration=3000, parent=None):
    """显示成功提示"""
    return self.show(message, 'success', duration, parent)

def error(self, message, duration=4000, parent=None):
    """显示错误提示（默认4秒）"""
    return self.show(message, 'error', duration, parent)

def warning(self, message, duration=3500, parent=None):
    """显示警告提示（默认3.5秒）"""
    return self.show(message, 'warning', duration, parent)

def info(self, message, duration=3000, parent=None):
    """显示信息提示"""
    return self.show(message, 'info', duration, parent)
```

---

### 3. toast - 全局实例
```python
# 全局Toast实例，可直接导入使用
toast = ToastManager()
```

## 使用示例

### 1. 基础使用
```python
from components.toast import toast

# 显示成功提示
toast.success("保存成功！")

# 显示错误提示
toast.error("保存失败，请重试")

# 显示警告提示
toast.warning("该操作不可撤销")

# 显示信息提示
toast.info("正在处理您的请求...")
```

### 2. 自定义时长
```python
# 5秒后自动关闭
toast.success("操作成功", duration=5000)

# 不自动关闭（需要手动点击关闭按钮）
toast.error("严重错误", duration=0)
```

### 3. 在窗口中使用
```python
class MyWindow(QWidget):
    def save_data(self):
        try:
            # 执行保存操作
            self.do_save()
            
            # 显示成功提示
            toast.success("数据保存成功！")
        except Exception as e:
            # 显示错误提示
            toast.error(f"保存失败: {str(e)}")
```

### 4. 异步操作反馈
```python
def on_async_complete(self, success, message):
    """异步操作完成回调"""
    if success:
        toast.success(message, duration=3000)
    else:
        toast.error(message, duration=4000)
```

### 5. 多个Toast同时显示
```python
# 自动堆叠显示
toast.info("开始处理...")
toast.success("第一步完成")
toast.success("第二步完成")
toast.success("全部完成！")
```

### 6. 获取Toast实例
```python
# 可以保存Toast实例以便手动控制
my_toast = toast.info("正在处理...", duration=0)

# 稍后手动关闭
my_toast.fadeOut()
```

## 动画实现原理

### 1. 淡入动画（OutCubic）
```python
animation = QPropertyAnimation(opacity_effect, b"opacity")
animation.setDuration(300)
animation.setStartValue(0.0)
animation.setEndValue(1.0)
animation.setEasingCurve(QEasingCurve.Type.OutCubic)
animation.start()
```

**效果**: 快速出现，然后缓慢停止，给人干脆利落的感觉。

### 2. 淡出动画（InCubic）
```python
animation = QPropertyAnimation(opacity_effect, b"opacity")
animation.setDuration(300)
animation.setStartValue(1.0)
animation.setEndValue(0.0)
animation.setEasingCurve(QEasingCurve.Type.InCubic)
animation.finished.connect(self.onFadeOutFinished)
animation.start()
```

**效果**: 缓慢开始消失，然后快速结束，给人优雅退场的感觉。

### 3. 自动关闭定时器
```python
if duration > 0:
    QTimer.singleShot(duration, self.fadeOut)
```

## 位置布局策略

### 右下角堆叠布局
```
Screen (1920×1080)
                                    ┌────────────────┐
                                    │  Toast 3       │ ← 最新
                                    └────────────────┘
                              spacing (12px)
                                    ┌────────────────┐
                                    │  Toast 2       │
                                    └────────────────┘
                              spacing (12px)
                                    ┌────────────────┐
                                    │  Toast 1       │ ← 最旧
                                    └────────────────┘
                              margin_bottom (80px)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                              margin_right (24px) →│
```

### 位置计算公式
```python
x = screen_width - toast_width - margin_right
y = y_offset - toast_height
y_offset = y - spacing  # 为下一个Toast留出空间
```

## 设计模式与最佳实践

### 1. 单例模式
```python
# ToastManager使用单例模式
# 确保全局只有一个管理器实例
toast = ToastManager()  # 全局唯一
```

### 2. 信号槽机制
```python
# Toast关闭时通知管理器
toast.closed.connect(lambda: manager.removeToast(toast))
```

### 3. 自动资源清理
```python
def onFadeOutFinished(self):
    self.closed.emit()
    self.close()
    self.deleteLater()  # 自动清理内存
```

### 4. 选择合适的类型
```python
# 成功操作
toast.success("保存成功")

# 错误反馈
toast.error("网络连接失败")

# 警告提示
toast.warning("磁盘空间不足")

# 一般信息
toast.info("新消息到达")
```

### 5. 时长选择建议
```python
# 成功提示: 3秒（快速确认）
toast.success("操作成功", duration=3000)

# 错误提示: 4秒（需要阅读）
toast.error("错误信息较长...", duration=4000)

# 警告提示: 3.5秒（中等重要）
toast.warning("请注意", duration=3500)

# 重要错误: 不自动关闭
toast.error("严重错误，请联系管理员", duration=0)
```

## 性能优化

### 1. 限制Toast数量
```python
# 可以在ToastManager中添加最大数量限制
MAX_TOASTS = 5

def show(self, message, toast_type='info', duration=3000, parent=None):
    if len(self.toasts) >= self.MAX_TOASTS:
        # 移除最旧的Toast
        oldest = self.toasts[0]
        oldest.fadeOut()
```

### 2. 批量更新位置
```python
# updatePositions()一次性更新所有Toast位置
# 避免多次重复计算
```

### 3. 及时清理
```python
# 使用deleteLater()确保资源释放
# closed信号确保从管理器列表中移除
```

## 与传统QMessageBox对比

| 特性 | Toast | QMessageBox |
|------|-------|-------------|
| 阻塞性 | 非阻塞 | 阻塞式 |
| 自动消失 | ✓ | ✗ |
| 堆叠显示 | ✓ | ✗ |
| 动画效果 | ✓ | ✗ |
| 用户操作 | 