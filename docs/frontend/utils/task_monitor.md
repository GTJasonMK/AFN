# frontend/utils/task_monitor.py

## 模块概述

异步任务监控管理器模块，提供对后端异步任务的轮询和状态监控功能。该模块实现了基于 QTimer 的定时轮询机制，通过 PyQt6 的信号槽机制实时通知任务状态变化。

**核心功能：**
- 单个任务的状态监控（TaskMonitor）
- 多任务集中管理（TaskMonitorManager）
- 自动轮询与状态变化通知
- 任务生命周期管理

## 主要类

### 1. TaskMonitor

单个任务的监控器，负责轮询单个任务的状态并在状态变化时发出信号。

#### 信号定义

```python
# 任务状态变化信号
status_changed = pyqtSignal(str)  # 状态: pending, running, completed, failed, cancelled

# 任务进度更新信号
progress_updated = pyqtSignal(int, str)  # (进度百分比, 当前步骤描述)

# 任务完成信号
completed = pyqtSignal(dict)  # 任务结果数据

# 任务失败信号
failed = pyqtSignal(str, dict)  # (错误消息, 错误详情)
```

#### 初始化方法

```python
def __init__(
    self,
    task_id: str,
    api_client: ArborisAPIClient,
    poll_interval: int = 2000,  # 默认2秒轮询一次
    parent: Optional[QObject] = None
):
    """
    初始化任务监控器

    Args:
        task_id: 任务ID
        api_client: API客户端实例
        poll_interval: 轮询间隔（毫秒）
        parent: 父对象
    """
```

#### 核心方法

**start() - 开始监控任务**

```python
def start(self):
    """开始监控任务"""
    if self._is_monitoring:
        logger.warning(f"任务 {self.task_id} 已在监控中")
        return

    logger.info(f"开始监控任务: {self.task_id}")
    self._is_monitoring = True
    self._timer.start(self.poll_interval)

    # 立即执行一次查询
    self._poll_task_status()
```

**stop() - 停止监控任务**

```python
def stop(self):
    """停止监控任务"""
    if not self._is_monitoring:
        return

    logger.info(f"停止监控任务: {self.task_id}")
    self._is_monitoring = False
    self._timer.stop()
```

**_poll_task_status() - 轮询任务状态（内部方法）**

```python
def _poll_task_status(self):
    """轮询任务状态"""
    try:
        task_data = self.api_client.get_task(self.task_id)

        status = task_data.get('status')
        progress = task_data.get('progress', 0)
        step_description = task_data.get('step_description', '')

        # 检查状态变化
        if status != self._last_status:
            logger.info(f"任务 {self.task_id} 状态变化: {self._last_status} -> {status}")
            self._last_status = status
            self.status_changed.emit(status)

        # 检查进度变化
        if progress != self._last_progress:
            self._last_progress = progress
            self.progress_updated.emit(progress, step_description)

        # 处理终态
        if status == 'completed':
            logger.info(f"任务 {self.task_id} 已完成")
            self.stop()
            result_data = task_data.get('result_data', {})
            self.completed.emit(result_data)

        elif status == 'failed':
            logger.error(f"任务 {self.task_id} 失败: {task_data.get('error_message')}")
            self.stop()
            error_message = task_data.get('error_message', '未知错误')
            error_details = task_data.get('error_details', {})
            self.failed.emit(error_message, error_details)

        elif status == 'cancelled':
            logger.info(f"任务 {self.task_id} 已取消")
            self.stop()
            self.status_changed.emit('cancelled')

    except Exception as e:
        logger.exception(f"轮询任务 {self.task_id} 状态时出错: {e}")
        # 网络错误等不停止监控，继续尝试
```

### 2. TaskMonitorManager

任务监控管理器，统一管理多个异步任务的监控。

#### 初始化方法

```python
def __init__(
    self,
    api_client: ArborisAPIClient,
    parent: Optional[QObject] = None
):
    """
    初始化任务监控管理器

    Args:
        api_client: API客户端实例
        parent: 父对象
    """
```

#### 核心方法

**monitor_task() - 开始监控一个任务**

```python
def monitor_task(
    self,
    task_id: str,
    on_progress: Optional[Callable[[int, str], None]] = None,
    on_completed: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_failed: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    poll_interval: int = 2000
) -> TaskMonitor:
    """
    开始监控一个任务

    Args:
        task_id: 任务ID
        on_progress: 进度更新回调
        on_completed: 完成回调
        on_failed: 失败回调
        poll_interval: 轮询间隔（毫秒）

    Returns:
        TaskMonitor实例
    """
```

**stop_monitoring() - 停止监控指定任务**

```python
def stop_monitoring(self, task_id: str):
    """
    停止监控指定任务

    Args:
        task_id: 任务ID
    """
    if task_id in self._monitors:
        self._monitors[task_id].stop()
        self._monitors[task_id].deleteLater()
        del self._monitors[task_id]
        logger.info(f"停止监控任务: {task_id}")
```

**stop_all() - 停止所有任务监控**

```python
def stop_all(self):
    """停止所有任务监控"""
    task_ids = list(self._monitors.keys())
    for task_id in task_ids:
        self.stop_monitoring(task_id)
    logger.info("停止所有任务监控")
```

**get_monitor() - 获取指定任务的监控器**

```python
def get_monitor(self, task_id: str) -> Optional[TaskMonitor]:
    """
    获取指定任务的监控器

    Args:
        task_id: 任务ID

    Returns:
        TaskMonitor实例，如果不存在则返回None
    """
    return self._monitors.get(task_id)
```

**is_monitoring() - 检查是否正在监控指定任务**

```python
def is_monitoring(self, task_id: str) -> bool:
    """
    检查是否正在监控指定任务

    Args:
        task_id: 任务ID

    Returns:
        是否正在监控
    """
    return task_id in self._monitors
```

**get_monitoring_count() - 获取正在监控的任务数量**

```python
def get_monitoring_count(self) -> int:
    """获取正在监控的任务数量"""
    return len(self._monitors)
```

## 使用示例

### 1. 单个任务监控

```python
from PyQt6.QtWidgets import QApplication
from api.client import ArborisAPIClient
from utils.task_monitor import TaskMonitor

# 创建API客户端
api_client = ArborisAPIClient("http://127.0.0.1:8123")

# 创建任务监控器
monitor = TaskMonitor(
    task_id="task_123",
    api_client=api_client,
    poll_interval=2000  # 每2秒轮询一次
)

# 连接信号
monitor.status_changed.connect(lambda status: print(f"状态变化: {status}"))
monitor.progress_updated.connect(lambda progress, desc: print(f"进度: {progress}% - {desc}"))
monitor.completed.connect(lambda result: print(f"任务完成: {result}"))
monitor.failed.connect(lambda error, details: print(f"任务失败: {error}"))

# 开始监控
monitor.start()
```

### 2. 使用管理器监控多个任务

```python
from utils.task_monitor import TaskMonitorManager

# 创建管理器
manager = TaskMonitorManager(api_client)

# 监控任务1
monitor1 = manager.monitor_task(
    task_id="task_1",
    on_progress=lambda progress, desc: print(f"任务1进度: {progress}%"),
    on_completed=lambda result: print(f"任务1完成: {result}"),
    on_failed=lambda error, details: print(f"任务1失败: {error}")
)

# 监控任务2
monitor2 = manager.monitor_task(
    task_id="task_2",
    on_progress=lambda progress, desc: print(f"任务2进度: {progress}%"),
    on_completed=lambda result: print(f"任务2完成: {result}"),
    on_failed=lambda error, details: print(f"任务2失败: {error}")
)

# 检查监控状态
print(f"正在监控 {manager.get_monitoring_count()} 个任务")

# 停止特定任务监控
manager.stop_monitoring("task_1")

# 停止所有监控
manager.stop_all()
```

### 3. 在窗口中集成任务监控

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from utils.task_monitor import TaskMonitorManager

class TaskMonitorWidget(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.manager = TaskMonitorManager(api_client, parent=self)
        
        # UI组件
        self.status_label = QLabel("等待任务...")
        self.progress_bar = QProgressBar()
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
    
    def start_monitoring_task(self, task_id: str):
        """开始监控任务"""
        self.manager.monitor_task(
            task_id=task_id,
            on_progress=self._on_progress,
            on_completed=self._on_completed,
            on_failed=self._on_failed
        )
    
    def _on_progress(self, progress: int, description: str):
        """进度更新回调"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"进行中: {description}")
    
    def _on_completed(self, result: dict):
        """完成回调"""
        self.progress_bar.setValue(100)
        self.status_label.setText("任务完成！")
    
    def _on_failed(self, error: str, details: dict):
        """失败回调"""
        self.status_label.setText(f"任务失败: {error}")
```

## 设计模式与最佳实践

### 1. 观察者模式

TaskMonitor 使用 PyQt6 的信号槽机制实现观察者模式：
- **被观察者（Subject）**：TaskMonitor
- **观察者（Observer）**：连接到信号的任何对象
- **好处**：解耦任务监控逻辑和UI更新逻辑

### 2. 轮询机制

使用 QTimer 实现定时轮询：
- 默认间隔：2秒（可配置）
- 立即执行：启动监控时立即查询一次
- 自动停止：任务达到终态时停止轮询

### 3. 资源管理

TaskMonitorManager 实现自动资源清理：
- 任务完成或失败后自动清理监控器
- 使用 `deleteLater()` 安全删除 QObject
- 提供 `stop_all()` 批量清理方法

### 4. 错误处理

健壮的错误处理机制：
- 网络错误不停止监控，继续重试
- 记录详细的日志信息
- 提供错误详情给上层调用者

## 技术亮点

### 1. 状态管理

精确追踪任务状态变化：
```python
# 检查状态变化
if status != self._last_status:
    self._last_status = status
    self.status_changed.emit(status)
```

### 2. 进度跟踪

支持进度百分比和步骤描述：
```python
# 检查进度变化
if progress != self._last_progress:
    self._last_progress = progress
    self.progress_updated.emit(progress, step_description)
```

### 3. 终态处理

自动识别并处理任务终态：
- **completed**：发出 `completed` 信号并停止监控
- **failed**：发出 `failed` 信号并停止监控
- **cancelled**：发出 `status_changed` 信号并停止监控

### 4. 回调灵活性

支持多种回调连接方式：
```python
# 方式1：信号连接
monitor.completed.connect(on_completed_handler)

# 方式2：管理器便捷方法
manager.monitor_task(
    task_id="task_1",
    on_completed=lambda result: print(result)
)
```

## 与其他组件的关系

```
TaskMonitorManager
├── 依赖 ArborisAPIClient（API通信）
├── 管理多个 TaskMonitor 实例
└── 被窗口类使用（MainWindow, WritingDesk等）

TaskMonitor
├── 依赖 ArborisAPIClient（轮询任务状态）
├── 使用 QTimer（定时轮询）
└── 发出信号通知UI组件
```

## 注意事项

### 1. 内存泄漏防范

```python
# 正确：任务完成后自动清理
def cleanup():
    if task_id in self._monitors:
        del self._monitors[task_id]

monitor.completed.connect(cleanup)
monitor.failed.connect(lambda *args: cleanup())
```

### 2. 轮询间隔选择

- **短间隔（1-2秒）**：适合快速任务，实时性要求高
- **长间隔（5-10秒）**：适合长时间任务，减少服务器压力

### 3. 网络异常处理

```python
except Exception as e:
    logger.exception(f"轮询任务 {self.task_id} 状态时出错: {e}")
    # 网络错误等不停止监控，继续尝试
```

### 4. 线程安全

所有操作在主线程进行，通过信号槽机制保证线程安全。

## 性能优化建议

1. **批量监控**：使用 TaskMonitorManager 统一管理多个任务
2. **动态间隔**：根据任务类型调整轮询间隔
3. **及时清理**：任务完成后立即停止监控并清理资源
4. **日志级别**：生产环境使用 INFO 级别，避免过多 DEBUG 日志

## 扩展建议

1. **指数退避**：网络错误时逐渐增加轮询间隔
2. **WebSocket支持**：支持 WebSocket 推送通知，减少轮询
3. **任务优先级**：支持不同优先级任务的差异化轮询策略
4. **历史记录**：保存任务状态变化历史供分析使用