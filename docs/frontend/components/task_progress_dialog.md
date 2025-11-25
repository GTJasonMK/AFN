
# task_progress_dialog.py - 任务进度对话框

## 文件路径
`frontend/components/task_progress_dialog.py`

## 模块概述
显示异步任务执行进度和状态的模态对话框组件，支持任务取消、进度更新、详细日志查看等功能。

## 主要类

### TaskProgressDialog - 任务进度对话框
**继承**: `QDialog`

用于显示异步任务的执行进度，支持取消任务和查看详细日志。

#### 初始化参数
- `task_id: str` - 任务ID
- `task_name: str` - 任务名称（显示用）
- `api_client: ArborisAPIClient` - API客户端实例
- `monitor_manager: TaskMonitorManager` - 任务监控管理器
- `parent: QWidget = None` - 父窗口
- `can_cancel: bool = True` - 是否允许取消任务

#### 信号
```python
task_completed = pyqtSignal(dict)  # 任务完成，参数：任务结果
task_failed = pyqtSignal(str)      # 任务失败，参数：错误消息
```

#### 核心属性
- `task_id: str` - 任务唯一标识
- `task_name: str` - 任务显示名称
- `api_client: ArborisAPIClient` - API客户端
- `monitor_manager: TaskMonitorManager` - 监控管理器
- `can_cancel: bool` - 是否可取消
- `_monitor: TaskMonitor` - 任务监控器实例
- `_is_completed: bool` - 是否已完成
- `_is_cancelled: bool` - 是否已取消

#### UI组件
- `progress_bar: QProgressBar` - 进度条（0-100）
- `status_label: QLabel` - 状态描述文字
- `log_text: QTextEdit` - 详细日志（可展开）
- `toggle_log_button: QPushButton` - 显示/隐藏日志按钮
- `cancel_button: QPushButton` - 取消任务按钮
- `close_button: QPushButton` - 关闭按钮（初始禁用）

#### 窗口特性
```python
# 模态对话框
self.setModal(True)

# 禁止关闭按钮（必须等待完成或取消）
Qt.WindowType.WindowCloseButtonHint  # 移除关闭按钮

# 最小尺寸
self.setMinimumWidth(500)
self.setMinimumHeight(250)
```

## 核心方法

### 1. 初始化与UI

#### _setup_ui()
```python
def _setup_ui(self):
    """设置UI
    
    布局结构:
        [Dialog (500×250)]
        ├── Task Label (任务名称)
        ├── Progress Bar (0-100%)
        ├── Status Label (状态描述)
        ├── Log Text (详细日志，可展开)
        └── Buttons
            ├── Toggle Log (显示/隐藏详情)
            ├── Cancel (取消任务)
            └── Close (关闭对话框，初始禁用)
    """
```

### 2. 任务监控

#### _start_monitoring()
```python
def _start_monitoring(self):
    """开始监控任务
    
    流程:
        1. 创建TaskMonitor实例
        2. 注册回调函数:
           - on_progress: 进度更新
           - on_completed: 任务完成
           - on_failed: 任务失败
        3. 记录日志
    """
```

#### _on_progress_updated(progress, description)
```python
def _on_progress_updated(self, progress: int, description: str):
    """进度更新回调
    
    Args:
        progress: 进度值 (0-100)
        description: 进度描述文字
    
    操作:
        1. 更新进度条值
        2. 更新状态标签文字
        3. 添加日志记录
    """
```

### 3. 任务完成处理

#### _on_task_completed(result_data)
```python
def _on_task_completed(self, result_data: Dict[str, Any]):
    """任务完成回调
    
    Args:
        result_data: 任务结果数据
    
    操作:
        1. 设置完成标志
        2. 进度条设为100%
        3. 更新状态为"已完成"（绿色）
        4. 禁用取消按钮
        5. 启用关闭按钮
        6. 记录日志
        7. 发射task_completed信号
    """
```

#### _on_task_failed(error_message, error_details)
```python
def _on_task_failed(self, error_message: str, error_details: Dict[str, Any]):
    """任务失败回调
    
    Args:
        error_message: 错误消息
        error_details: 错误详情字典
    
    操作:
        1. 设置完成标志
        2. 进度条变红色
        3. 更新状态为"失败"（红色）
        4. 禁用取消按钮
        5. 启用关闭按钮
        6. 记录错误日志
        7. 发射task_failed信号
    """
```

### 4. 任务控制

#### _cancel_task()
```python
def _cancel_task(self):
    """取消任务
    
    流程:
        1. 检查任务状态（已完成或已取消则返回）
        2. 更新状态为"正在取消..."
        3. 禁用取消按钮
        4. 调用API取消任务
        5. 处理取消结果:
           - 成功: 更新状态，启用关闭按钮，停止监控
           - 失败: 恢复取消按钮，显示错误
    
    异常处理:
        捕获所有异常，记录日志并显示错误信息
    """
```

### 5. UI交互

#### _toggle_log()
```python
def _toggle_log(self):
    """切换日志显示
    
    操作:
        - 隐藏状态: 
          - 显示日志文本框
          - 按钮文字改为"隐藏详情"
          - 对话框高度增加到400px
        - 显示状态:
          - 隐藏日志文本框
          - 按钮文字改为"显示详情"
          - 对话框高度减少到250px
    """
```

#### _log(message)
```python
def _log(self, message: str):
    """添加日志
    
    在日志文本框末尾追加消息
    """
```

### 6. 生命周期

#### closeEvent(event)
```python
def closeEvent(self, event):
    """关闭事件处理
    
    逻辑:
        - 如果任务仍在运行: 阻止关闭 (event.ignore())
        - 如果任务已完成或取消: 
          - 停止监控
          - 允许关闭 (event.accept())
    """
```

## 状态流转图

```
[创建] → [监控中]
           │
           ├─→ [进度更新] ─→ (循环)
           │
           ├─→ [完成] ─→ [可关闭]
           │
           ├─→ [失败] ─→ [可关闭]
           │
           └─→ [取消中] ─→ [已取消] ─→ [可关闭]
```

## 样式配置

### 进度条样式
```python
# 正常状态
QProgressBar::chunk {
    background-color: #4f46e5;  # 主题色
}

# 失败状态
QProgressBar::chunk {
    background-color: #f44336;  # 红色
}
```

### 状态标签样式
```python
# 正常/处理中
color: #666;
font-size: 12px;

# 完成
color: #4CAF50;  # 绿色
font-size: 12px;
font-weight: bold;

# 失败
color: #f44336;  # 红色
font-size: 12px;
font-weight: bold;

# 已取消
color: #FF9800;  # 橙色
font-size: 12px;
```

## 使用示例

### 1. 基础使用
```python
from components.task_progress_dialog import TaskProgressDialog
from api.client import ArborisAPIClient
from utils.task_monitor import TaskMonitorManager

# 创建对话框
dialog = TaskProgressDialog(
    task_id="task_123",
    task_name="生成章节大纲",
    api_client=api_client,
    monitor_manager=monitor_manager,
    parent=self,
    can_cancel=True
)

# 连接信号
dialog.task_completed.connect(self.on_task_success)
dialog.task_failed.connect(self.on_task_error)

# 显示对话框（模态）
dialog.exec()
```

### 2. 处理任务结果
```python
def on_task_success(self, result_data):
    """任务完成回调"""
    print(f"任务完成: {result_data}")
    # 刷新数据
    self.refresh_data()

def on_task_error(self, error_message):
    """任务失败回调"""
    print(f"任务失败: {error_message}")
    # 显示错误提示
    toast.error(f"操作失败: {error_message}")
```

### 3. 不可取消的任务
```python
# 创建不可取消的对话框
dialog = TaskProgressDialog(
    task_id="critical_task",
    task_name="数据库迁移",
    api_client=api_client,
    monitor_manager=monitor_manager,
    parent=self,
    can_cancel=False  # 不显示取消按钮
)
```

### 4. 在异步任务中使用
```python
async def generate_outline(self):
    """生成大纲"""
    try:
        # 启动任务
        result = await api_client.start_outline_generation(novel_id)
        task_id = result['task_id']
        
        # 显示进度对话框
        dialog = TaskProgressDialog(
            task_id=task_id,
            task_name="生成大纲",
            api_client=api_client,
            monitor_manager=monitor_manager,
            parent=self
        )
        
        dialog.task_completed.connect(self.on_outline_generated)
        dialog.exec()
        
    except Exception as e:
        toast.error(f"启动任务失败: {str(e)}")
```

## 与TaskMonitor的交互

### 监控器回调注册
```python
self._monitor = self.monitor_manager.monitor_task(
    task_id=self.task_id,
    on_progress=self._on_progress_updated,     # 进度更新
    on_completed=self._on_task_completed,      # 完成
    on_failed=self._on_task_failed             # 失败
)
```

### 进度数据流
```
API Server
    ↓ (轮询)
TaskMonitor
    ↓ (回调)
TaskProgressDialog
    ↓ (UI更新)
Progress Bar / Status Label
```

## 最佳实践

### 1. 任务命名
```python
# 清晰的任务名称
dialog = TaskProgressDialog(
    task_name="生成第1-5章大纲",  # ✓ 具体
    # 而不是 "生成大纲"           # ✗ 模糊
)
```

### 2. 错误处理
```python
dialog.task_failed.connect(lambda msg: 
    toast.error(f"操作失败: {msg}", duration=0)  # 不自动关闭
)
```

### 3. 完成后刷新
```python
def on_task_completed(self, result_data):
    """任务完成后刷新相关数据"""
    self.refresh_outline_list()
    self.reload_chapter_data()
    toast.success("大纲生成完成！")
```

### 4. 资源清理
```python
# 对话框会自动处理监控器的清理
# closeEvent中会调用: monitor_manager.stop_monitoring(task_id)
```

## 性能优化

### 1. 日志按需加载
```python
# 初始隐藏日志，减少渲染
self.log_text.setVisible(False)

# 只在用户点击时显示
def _toggle_log(self):
    self.log_text.setVisible(not self.log_text.isVisible())
```

### 2. 进度更新节流
```python
# TaskMonitor层面控制更新频率
# 避免频繁的UI刷新
```

## 注意事项

1. **模态对话框**: 阻止用户操作其他窗口，确保任务完成
2. **禁止关闭**: 运行中的任务不允许通过窗口关闭按钮关闭
3. **取消机制**: 取消任务是异步的，可能需要时间
4. **错误恢复**: 取消失败时恢复取消按钮，允许重试
5. **信号连接**: 记得连接completed和failed信号处理结果
6. **资源清理**: 对话框关闭时自动停止监控器

## 与其他组件的关系
- **TaskMonitor**: 提供任务状态轮询和回调
- **TaskMonitorManager**: 