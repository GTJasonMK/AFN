# async_worker.py - 异步工作线程工具

## 文件路径
`frontend/utils/async_worker.py`

## 模块概述
提供QThread包装器，用于在后台执行耗时的API调用，避免UI冻结。实现简单易用的异步任务执行机制。

## 设计目标
- **避免UI冻结**: 耗时操作在后台线程执行
- **简单易用**: 一行代码启动异步任务
- **信号驱动**: 使用PyQt信号机制返回结果
- **错误处理**: 自动捕获异常并提供详细错误信息

## 主要类

### AsyncAPIWorker - 异步API调用工作线程
**继承**: `QThread`

用于在后台线程执行API调用或其他耗时操作。

#### 初始化参数
- `func: Callable` - 要执行的函数（通常是API客户端方法）
- `*args` - 函数的位置参数
- `**kwargs` - 函数的关键字参数

#### 信号
```python
success = pyqtSignal(object)  # 成功时发射结果
error = pyqtSignal(str)       # 失败时发射错误信息
```

#### 核心属性
- `func: Callable` - 待执行的函数
- `args: tuple` - 函数位置参数
- `kwargs: dict` - 函数关键字参数
- `_is_cancelled: bool` - 取消标志

#### 核心方法

##### run()
```python
def run(self):
    """线程执行入口
    
    执行流程:
        1. 检查是否已取消
        2. 调用函数 func(*args, **kwargs)
        3. 成功: 发射success信号，传递结果
        4. 失败: 捕获异常，发射error信号，包含堆栈信息
    
    异常处理:
        - 捕获所有异常
        - 提供完整的traceback信息
        - 格式: "{错误消息}\n\n详细信息:\n{traceback}"
    """
```

##### cancel()
```python
def cancel(self):
    """取消任务
    
    注意: 
        - 只能阻止结果的发射，无法中断已开始的API调用
        - 设置_is_cancelled标志
        - 适用于快速取消还未开始或刚完成的任务
    """
```

## 使用示例

### 1. 基础使用
```python
from utils.async_worker import AsyncAPIWorker
from api.client import ArborisAPIClient

api_client = ArborisAPIClient()

# 创建工作线程
worker = AsyncAPIWorker(
    api_client.get_novels  # 要执行的函数
)

# 连接信号
worker.success.connect(self.on_success)
worker.error.connect(self.on_error)

# 启动线程
worker.start()

def on_success(self, result):
    """成功回调"""
    print(f"获取到 {len(result)} 个小说")
    self.display_novels(result)

def on_error(self, error_msg):
    """错误回调"""
    print(f"错误: {error_msg}")
    toast.error(f"加载失败: {error_msg}")
```

### 2. 带参数的API调用
```python
# 传递位置参数
worker = AsyncAPIWorker(
    api_client.get_novel_detail,
    novel_id  # 位置参数
)

# 传递关键字参数
worker = AsyncAPIWorker(
    api_client.generate_chapter,
    novel_id=123,
    chapter_number=1,
    style="古典"
)

# 混合参数
worker = AsyncAPIWorker(
    api_client.update_chapter,
    novel_id,  # 位置参数
    chapter_id,
    content="新内容",  # 关键字参数
    title="新标题"
)
```

### 3. 完整的加载流程
```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.load_data()
    
    def load_data(self):
        """加载数据"""
        # 显示加载状态
        self.show_loading()
        
        # 创建并启动工作线程
        self.worker = AsyncAPIWorker(
            self.api_client.get_chapters,
            self.novel_id
        )
        self.worker.success.connect(self.on_load_success)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()
    
    def on_load_success(self, chapters):
        """加载成功"""
        self.hide_loading()
        
        if chapters:
            self.display_chapters(chapters)
        else:
            self.show_empty_state()
    
    def on_load_error(self, error_msg):
        """加载失败"""
        self.hide_loading()
        self.show_error_state()
        toast.error(f"加载失败: {error_msg}")
    
    def show_loading(self):
        """显示加载状态"""
        self.skeleton = SkeletonPresets.chapter_list(parent=self)
        self.layout.addWidget(self.skeleton)
    
    def hide_loading(self):
        """隐藏加载状态"""
        if self.skeleton:
            self.skeleton.deleteLater()
            self.skeleton = None
```

### 4. 取消任务
```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
    
    def start_task(self):
        """启动任务"""
        self.worker = AsyncAPIWorker(
            self.api_client.long_running_task
        )
        self.worker.success.connect(self.on_success)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def cancel_task(self):
        """取消任务"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # 等待线程结束
            toast.info("任务已取消")
    
    def closeEvent(self, event):
        """窗口关闭时取消任务"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
        event.accept()
```

### 5. 多个并发任务
```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.workers = []
    
    def load_multiple_data(self):
        """加载多个数据源"""
        # 任务1: 加载小说列表
        worker1 = AsyncAPIWorker(self.api_client.get_novels)
        worker1.success.connect(self.on_novels_loaded)
        worker1.start()
        self.workers.append(worker1)
        
        # 任务2: 加载配置
        worker2 = AsyncAPIWorker(self.api_client.get_config)
        worker2.success.connect(self.on_config_loaded)
        worker2.start()
        self.workers.append(worker2)
        
        # 任务3: 加载统计数据
        worker3 = AsyncAPIWorker(self.api_client.get_stats)
        worker3.success.connect(self.on_stats_loaded)
        worker3.start()
        self.workers.append(worker3)
    
    def on_novels_loaded(self, novels):
        print(f"小说加载完成: {len(novels)}")
    
    def on_config_loaded(self, config):
        print(f"配置加载完成")
    
    def on_stats_loaded(self, stats):
        print(f"统计加载完成")
```

### 6. 错误处理最佳实践
```python
def on_error(self, error_msg):
    """统一错误处理"""
    # 解析错误类型
    if "ConnectionError" in error_msg:
        toast.error("无法连接到服务器，请检查网络")
        self.show_connection_error_state()
    elif "TimeoutError" in error_msg:
        toast.error("请求超时，请重试")
        self.show_retry_button()
    elif "404" in error_msg:
        toast.error("资源不存在")
        self.show_not_found_state()
    else:
        toast.error(f"操作失败: {error_msg}")
        self.show_generic_error_state()
    
    # 记录详细日志
    logger.error(f"API调用失败: {error_msg}")
```

## 线程安全注意事项

### 1. UI更新必须在主线程
```python
# ✓ 正确：通过信号槽更新UI
worker.success.connect(self.update_ui)

def update_ui(self, data):
    """在主线程中更新UI"""
    self.label.setText(str(data))

# ✗ 错误：在工作线程中直接更新UI
def run(self):
    result = self.func()
    self.parent.label.setText(str(result))  # 危险！
```

### 2. 共享数据需要加锁
```python
from PyQt6.QtCore import QMutex

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data_mutex = QMutex()
        self.shared_data = []
    
    def on_data_received(self, new_data):
        """线程安全地更新共享数据"""
        self.data_mutex.lock()
        try:
            self.shared_data.extend(new_data)
        finally:
            self.data_mutex.unlock()
```

## 设计模式与最佳实践

### 1. 保持worker引用
```python
# ✓ 正确：保持引用
self.worker = AsyncAPIWorker(...)
self.worker.start()

# ✗ 错误：worker可能被垃圾回收
AsyncAPIWorker(...).start()  # 危险！
```

### 2. 清理工作线程
```python
def cleanup(self):
    """清理工作线程"""
    if self.worker:
        if self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # 等待线程结束
        self.worker.deleteLater()
        self.worker = None
```

### 3. 避免嵌套工作线程
```python
# ✗ 不推荐：嵌套创建worker
def on_success(self, data):
    # 在回调中创建新的worker
    worker2 = AsyncAPIWorker(...)
    worker2.start()

# ✓ 推荐：顺序执行或使用任务队列
def on_first_success(self, data):
    self.start_second_task(data)

def start_second_task(self, data):
    self.worker2 = AsyncAPIWorker(...)
    self.worker2.start()
```

## 与其他组件的关系
- **TaskProgressDialog**: 长时间任务使用TaskProgressDialog，短任务使用AsyncAPIWorker
- **LoadingSpinner**: 配合显示加载动画
- **Skeleton**: 配合显示骨架屏
- **Toast**: 配合显示操作结果提示
- **API Client**: 通常执行ArborisAPIClient的方法

## 性能优化

### 1. 避免频繁创建线程
```python
# 使用线程池或复用worker
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.worker_pool = []
        self.init_worker_pool(size=3)
    
    def init_worker_pool(self, size):
        """初始化线程池"""
        for _ in range(size):
            worker = AsyncAPIWorker(None)
            self.worker_pool.append(worker)
```

### 2. 超时控制
```python
from PyQt6.QtCore import QTimer

def start_with_timeout(self):
    """带超时的任务启动"""
    self.worker = AsyncAPIWorker(self.api_client.slow_task)
    self.worker.success.connect(self.on_success)
    self.worker.start()
    
    # 设置超时
    self.timeout_timer = QTimer()
    self.timeout_timer.setSingleShot(True)
    self.timeout_timer.timeout.connect(self.on_timeout)
    self.timeout_timer.start(30000)  # 30秒超时

def on_success(self, result):
    self.timeout_timer.stop()
    # 处理结果...

def on_timeout(self):
    """超时处理"""
    if self.worker.isRunning():
        self.worker.cancel()
        toast.error("请求超时")
```

## 注意事项

1. **保持worker引用**: 避免被垃圾回收
2. **线程清理**: closeEvent中等待线程结束
3. **UI更新**: 只在信号槽中更新UI
4. **错误处理**: 连接error信号，提供用户友好的错误提示
5. **取消限制**: cancel()无法中断正在执行的API调用
6. **避免阻塞**: func不应执行UI操作或耗时的同步操作

## 技术亮点

1. **简单封装**: 一行代码启动异步任务
2. **信号驱动**: 符合PyQt编程规范
3. **错误详情**: 提供完整的traceback信息
4. **类型灵活**: 支持任何可调用对象
5. **参数透传**: 完整支持*args和**kwargs