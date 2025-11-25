
# config_manager.py - 配置管理工具

## 文件路径
`frontend/utils/config_manager.py`

## 模块概述
用于保存和加载应用配置的工具类，使用QSettings实现配置的持久化存储。支持保存窗口状态、API配置、用户偏好等信息。

## 设计目标
- **持久化存储**: 配置保存到本地INI文件
- **简单易用**: 提供便捷的getter/setter方法
- **跨平台**: 使用QSettings自动适配不同操作系统
- **类型安全**: 支持多种数据类型的存储

## 主要类

### ConfigManager - 应用配置管理器

使用QSettings保存配置到本地INI文件。

#### 初始化参数
- `organization: str = "ArborisNovel"` - 组织名称
- `application: str = "PyQtClient"` - 应用名称

#### 配置文件位置
```python
# Windows
C:/Users/{username}/AppData/Roaming/ArborisNovel/PyQtClient.ini

# Linux
~/.config/ArborisNovel/PyQtClient.conf

# macOS
~/Library/Preferences/com.ArborisNovel.PyQtClient.plist
```

#### 核心属性
- `settings: QSettings` - Qt设置对象

## 配置项方法

### 1. 灵感模式项目配置

#### get_last_inspiration_project()
```python
def get_last_inspiration_project(self):
    """获取上次灵感模式使用的项目ID
    
    Returns:
        str | None: 项目ID，如果不存在返回None
    
    配置键: inspiration/last_project_id
    """
```

#### set_last_inspiration_project(project_id)
```python
def set_last_inspiration_project(self, project_id: str):
    """保存灵感模式使用的项目ID
    
    Args:
        project_id: 项目ID
    
    配置键: inspiration/last_project_id
    
    用途: 下次打开灵感模式时自动恢复该项目
    """
```

#### clear_last_inspiration_project()
```python
def clear_last_inspiration_project(self):
    """清除保存的灵感模式项目ID
    
    配置键: inspiration/last_project_id
    
    用途: 项目删除时清除引用
    """
```

### 2. 窗口几何配置

#### get_window_geometry()
```python
def get_window_geometry(self):
    """获取窗口几何信息
    
    Returns:
        QByteArray | None: 窗口几何信息（位置、大小、状态）
    
    配置键: window/geometry
    
    包含信息:
        - 窗口位置 (x, y)
        - 窗口尺寸 (width, height)
        - 窗口状态 (最大化/最小化等)
    """
```

#### set_window_geometry(geometry)
```python
def set_window_geometry(self, geometry: QByteArray):
    """保存窗口几何信息
    
    Args:
        geometry: QByteArray 窗口几何信息
    
    配置键: window/geometry
    
    用途: 应用关闭时保存窗口状态，下次启动时恢复
    """
```

### 3. API配置

#### get_api_base_url()
```python
def get_api_base_url(self):
    """获取API基础URL
    
    Returns:
        str: API基础URL，默认为 http://127.0.0.1:8123
    
    配置键: api/base_url
    """
```

#### set_api_base_url(url)
```python
def set_api_base_url(self, url: str):
    """保存API基础URL
    
    Args:
        url: API基础URL
    
    配置键: api/base_url
    
    用途: 支持配置不同的后端服务器地址
    """
```

## 使用示例

### 1. 基础使用
```python
from utils.config_manager import ConfigManager

# 创建配置管理器
config = ConfigManager()

# 保存配置
config.set_last_inspiration_project("project_123")

# 读取配置
project_id = config.get_last_inspiration_project()
print(f"上次项目: {project_id}")

# 清除配置
config.clear_last_inspiration_project()
```

### 2. 窗口状态保存与恢复
```python
from PyQt6.QtWidgets import QMainWindow
from utils.config_manager import ConfigManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        
        # 恢复窗口状态
        self.restore_window_state()
    
    def restore_window_state(self):
        """恢复窗口状态"""
        geometry = self.config.get_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # 默认窗口大小
            self.resize(1200, 800)
            self.center_on_screen()
    
    def center_on_screen(self):
        """窗口居中"""
        screen = self.screen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
    
    def closeEvent(self, event):
        """关闭时保存窗口状态"""
        self.config.set_window_geometry(self.saveGeometry())
        event.accept()
```

### 3. 灵感模式项目记忆
```python
from utils.config_manager import ConfigManager

class InspirationMode(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        
        # 尝试恢复上次项目
        self.restore_last_project()
    
    def restore_last_project(self):
        """恢复上次使用的项目"""
        last_project_id = self.config.get_last_inspiration_project()
        
        if last_project_id:
            try:
                # 加载项目
                project = self.api_client.get_novel_detail(last_project_id)
                self.load_project(project)
                toast.info(f"已恢复项目: {project['title']}")
            except Exception as e:
                # 项目不存在，清除配置
                self.config.clear_last_inspiration_project()
                self.show_project_selector()
        else:
            self.show_project_selector()
    
    def on_project_selected(self, project_id):
        """项目选择后保存"""
        self.config.set_last_inspiration_project(project_id)
        self.load_project(project_id)
    
    def on_project_deleted(self, project_id):
        """项目删除后清除配置"""
        last_project = self.config.get_last_inspiration_project()
        if last_project == project_id:
            self.config.clear_last_inspiration_project()
```

### 4. API服务器配置
```python
from utils.config_manager import ConfigManager
from api.client import ArborisAPIClient

class SettingsView(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.setup_ui()
    
    def setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # API URL输入框
        self.url_input = QLineEdit()
        self.url_input.setText(self.config.get_api_base_url())
        self.url_input.setPlaceholderText("http://127.0.0.1:8123")
        layout.addWidget(QLabel("API服务器地址:"))
        layout.addWidget(self.url_input)
        
        # 保存按钮
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        # 测试连接按钮
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
    
    def save_settings(self):
        """保存设置"""
        url = self.url_input.text().strip()
        
        if not url:
            toast.error("请输入API地址")
            return
        
        # 保存配置
        self.config.set_api_base_url(url)
        
        # 更新API客户端
        self.update_api_client(url)
        
        toast.success("设置已保存")
    
    def test_connection(self):
        """测试连接"""
        url = self.url_input.text().strip()
        
        try:
            # 创建临时客户端测试
            test_client = ArborisAPIClient(base_url=url)
            result = test_client.health_check()
            
            if result.get('status') == 'healthy':
                toast.success("连接成功！")
            else:
                toast.warning("服务器响应异常")
                
        except Exception as e:
            toast.error(f"连接失败: {str(e)}")
```

### 5. 自定义配置项
```python
from utils.config_manager import ConfigManager

class ExtendedConfigManager(ConfigManager):
    """扩展的配置管理器"""
    
    def get_theme(self):
        """获取主题"""
        return self.settings.value("ui/theme", "light")
    
    def set_theme(self, theme):
        """保存主题"""
        self.settings.setValue("ui/theme", theme)
    
    def get_font_size(self):
        """获取字体大小"""
        return self.settings.value("ui/font_size", 14, type=int)
    
    def set_font_size(self, size):
        """保存字体大小"""
        self.settings.setValue("ui/font_size", size)
    
    def get_auto_save(self):
        """获取自动保存设置"""
        return self.settings.value("editor/auto_save", True, type=bool)
    
    def set_auto_save(self, enabled):
        """保存自动保存设置"""
        self.settings.setValue("editor/auto_save", enabled)
    
    def get_recent_files(self):
        """获取最近文件列表"""
        return self.settings.value("recent/files", [], type=list)
    
    def add_recent_file(self, file_path):
        """添加最近文件"""
        recent = self.get_recent_files()
        
        # 移除重复项
        if file_path in recent:
            recent.remove(file_path)
        
        # 添加到开头
        recent.insert(0, file_path)
        
        # 限制数量
        recent = recent[:10]
        
        self.settings.setValue("recent/files", recent)
```

### 6. 配置导入导出
```python
import json
from utils.config_manager import ConfigManager

class ConfigBackup:
    """配置备份工具"""
    
    def __init__(self):
        self.config = ConfigManager()
    
    def export_config(self, file_path):
        """导出配置到JSON文件"""
        config_data = {
            'inspiration_project': self.config.get_last_inspiration_project(),
            'api_base_url': self.config.get_api_base_url(),
            # 添加其他配置项...
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
        
        toast.success(f"配置已导出到: {file_path}")
    
    def import_config(self, file_path):
        """从JSON文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 导入各项配置
            if 'inspiration_project' in config_data:
                self.config.set_last_inspiration_project(
                    config_data['inspiration_project']
                )
            
            if 'api_base_url' in config_data:
                self.config.set_api_base_url(
                    config_data['api_base_url']
                )
            
            toast.success("配置导入成功")
            
        except Exception as e:
            toast.error(f"配置导入失败: {str(e)}")
```

## QSettings支持的数据类型

### 基本类型
```python
# 字符串
settings.setValue("key", "value")
value = settings.value("key", default="", type=str)

# 整数
settings.setValue("key", 42)
value = settings.value("key", default=0, type=int)

# 浮点数
settings.setValue("key", 3.14)
value = settings.value("key", default=0.0, type=float)

# 布尔值
settings.setValue("key", True)
value = settings.value("key", default=False, type=bool)
```

### 复杂类型
```python
# 列表
settings.setValue("key", [1, 2, 3])
value = settings.value("key", default=[], type=list)

# 字典（需要转换）
import json
settings.setValue("key", json.dumps({"a": 1}))
value = json.loads(settings.value("key", default="{}"))

# QByteArray
settings.setValue("key", byte_array)
value = settings.value("key", type=QByteArray)
```

## 最佳实践

### 1. 使用类型参数
```python
# ✓ 推荐：指定类型
font_size = config.settings.value("ui/font_size", 14, type=int)

# ✗ 不推荐：不指定类型（可能返回字符串）
font_size = config.settings.value("ui/font_size", 14)
```

### 2. 提供默认值
```python
# ✓ 推荐：总是提供默认值
url = config.get_api_base_url()  # 方法内已提供默认值

# ✓ 推荐：直接使用时提供默认值
theme = config.settings.value("ui/theme", "light")
```

### 3. 配置键命名规范
```python
# 使用分组/层级结构
"window/geometry"
"window/state"
"api/base_url"
"api/timeout"
"ui/theme"
"ui/font_size"
"editor/auto_save"
"editor/tab_size"
```

### 4. 配置变更通知
```python
from PyQt6.QtCore import QObject, pyqtSignal

class ObservableConfig(ConfigManager):
    """可观察的配置管理器"""
    
    config_changed = pyqtSignal(str, object)  # (key, value)
    
    def set_value(self, key, value):
        """设置配置并发出信号"""
        old_value = self.settings.value(key)
        
        if old_value != value:
            self.settings.setValue(key, value)
            self.config_changed.emit(key, value)
```

## 注意事项

1. **单例模式**: 通常在应用中创建单个ConfigManager实例
2. **类型转换**: 使用type参数确保返回正确的数据类型
3. **默认值**: 总是提供合理的默认值
4. **跨平台**: QSettings自动处理不同操作系统的配置文件格式
5. **即时保存**: setValue()立即写入磁盘，无需手动保存
6. **线程安全**: QSettings不是线程安全的，在主线程中使用

## 与其他组件的关系
- **MainWindow**: 保存和恢复窗口状态
- **InspirationMode**: 记住上次使用的项目
- **SettingsView**: 配置API服务器地址
- **API Client**: 读取API基础URL配置

## 技术亮点

1. **跨平台支持**: 自动适配不同操作系统的配置存储方式
2. **即时持久化**: 配置立即保存到磁盘
3. **类型安全**: 支持type参数确保类型正确
4. **简单易用**: 封装QSettings提供便捷接口
5. **可扩展**: 