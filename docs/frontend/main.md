# frontend/main.py - 应用程序入口

## 文件概述

应用程序的主入口点，负责初始化PyQt6应用、配置全局样式和启动主窗口。

**对应Web应用**: `frontend/src/main.ts`

**文件路径**: `frontend/main.py`  
**行数**: 129行

## 核心功能

### 1. 应用初始化

```python
def main():
    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("Arboris Novel")
    app.setOrganizationName("Arboris")
```

**功能**:
- 启用高DPI缩放支持（适配高分辨率显示器）
- 设置应用名称和组织名称
- 初始化Qt应用实例

### 2. 全局样式设置

#### 系统对话框样式

为 [`QMessageBox`](frontend/main.py:38-77)、[`QInputDialog`](frontend/main.py:78-108) 等系统对话框配置统一样式：

```python
base_style = f"""
    QMessageBox {{
        background-color: white;
        color: {ZenTheme.TEXT_PRIMARY};
    }}
    QMessageBox QPushButton {{
        background-color: {ZenTheme.ACCENT_PRIMARY};
        color: white;
        border: none;
        border-radius: {ZenTheme.RADIUS_SM};
        padding: 8px 20px;
    }}
"""
```

**特点**:
- 确保系统对话框有正确的文本对比度
- 统一按钮样式（主色调、圆角）
- 禅意风格配色

#### 可访问性增强

```python
accessibility_style = AccessibilityTheme.get_all_accessibility_styles()
app.setStyleSheet(base_style + "\n" + accessibility_style)
```

符合 **WCAG 2.1 AA级标准**:
- 明显的焦点指示器
- 键盘导航支持
- 优化的工具提示

### 3. 主窗口启动

```python
window = MainWindow()
window.show()
sys.exit(app.exec())
```

## 主题系统集成

### ZenTheme（禅意主题）

- `ACCENT_PRIMARY`: 主色调（灰绿色）
- `TEXT_PRIMARY`: 主文本颜色
- `RADIUS_SM`: 小圆角尺寸
- 温暖浅米白色背景
- 沉静灰绿色强调

### AccessibilityTheme（无障碍主题）

- 焦点指示器样式
- 高对比度文本
- 键盘导航辅助

## 依赖关系

### 导入模块

```python
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from windows.main_window import MainWindow
from themes import ZenTheme, AccessibilityTheme
```

### 外部依赖

- **PyQt6**: GUI框架
- **MainWindow**: 主窗口类
- **ZenTheme**: 禅意主题系统
- **AccessibilityTheme**: 无障碍增强

## 启动流程

```
1. 设置高DPI支持
   ↓
2. 创建QApplication实例
   ↓
3. 配置应用元数据（名称、组织）
   ↓
4. 应用全局样式（基础 + 可访问性）
   ↓
5. 创建并显示MainWindow
   ↓
6. 进入事件循环（app.exec()）
```

## 设计理念

### 1. 桌面应用最佳实践（2025）

- **高DPI支持**: 自动适配不同分辨率
- **无障碍设计**: WCAG 2.1 AA级合规
- **统一体验**: 全局样式确保一致性

### 2. 1:1迁移Web应用

注释明确标注对应关系：
```python
"""
对应Web应用：frontend/src/main.ts
启动 Arboris Novel 桌面版（1:1照抄Web应用）
"""
```

### 3. 渐进式样式系统

```
基础样式（系统对话框）
    +
可访问性增强样式
    =
完整全局样式
```

## 使用示例

### 启动应用

```bash
python frontend/main.py
```

### 自定义启动参数（扩展）

```python
import sys
from main import main

if __name__ == "__main__":
    # 可在此添加命令行参数处理
    # 例如：--debug, --config-file等
    main()
```

## 最佳实践

### 1. 样式定制

如需修改全局样式，在 [`main()`](frontend/main.py:23) 函数中调整：

```python
# 添加自定义样式
custom_style = """
    QWidget {
        font-family: 'Microsoft YaHei UI', sans-serif;
    }
"""
app.setStyleSheet(base_style + accessibility_style + custom_style)
```

### 2. 调试模式

```python
def main(debug=False):
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    # ... 其余代码
```

### 3. 错误处理

```python
def main():
    try:
        app = QApplication(sys.argv)
        # ... 初始化代码
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"应用启动失败: {e}")
        sys.exit(1)
```

## 注意事项

1. **必须先设置高DPI策略**，再创建QApplication
2. **全局样式优先级**：后应用的样式会覆盖先应用的
3. **系统对话框样式**：使用强选择器确保生效
4. **可访问性**：不要移除AccessibilityTheme，这是无障碍合规的关键

## 相关文件

- [`windows/main_window.py`](frontend/windows/main_window.py) - 主窗口实现
- [`themes/zen_theme.py`](frontend/themes/zen_theme.py) - 禅意主题定义
- [`themes/accessibility.py`](frontend/themes/accessibility.py) - 无障碍样式
- `backend/app/main.py` - 后端应用入口（对比参考）

## 技术特点

### 高DPI支持

```python
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
```

**效果**: 
- 在4K/Retina显示器上自动缩放
- 保持清晰度，避免模糊
- 跨平台一致性

### 样式表级联

```
系统默认样式
    ↓
base_style（覆盖对话框）
    ↓
accessibility_style（增强可访问性）
    ↓
组件自身样式（局部覆盖）
```

## 总结

`main.py` 是应用程序的启动核心，负责：

1. ✅ **环境初始化** - 高DPI、应用元数据
2. ✅ **样式统一** - 全局样式表、主题系统
3. ✅ **无障碍增强** - WCAG 2.1 AA级支持
4. ✅ **主窗口启动** - 进入事件循环

简洁、清晰、符合现代桌面应用开发最佳实践。