
# frontend/themes/accessibility.py

## 模块概述

可访问性主题扩展模块，符合2025年桌面应用最佳实践和WCAG 2.1 AA级标准。该模块为禅意主题提供可访问性增强，包括明显的焦点指示器、键盘导航样式、高对比度模式支持和屏幕阅读器友好的语义化标签。

**核心功能：**
- 明显的焦点指示器
- 键盘导航样式
- 高对比度模式支持
- 屏幕阅读器友好的语义化标签
- 键盘快捷键定义
- ARIA标签定义

## 主要类

### 1. AccessibilityTheme

可访问性主题扩展类，提供符合WCAG标准的样式增强。

#### focus_indicator() - 全局焦点指示器样式

```python
@classmethod
def focus_indicator(cls):
    """全局焦点指示器样式
    
    符合WCAG 2.1 AA级标准
    - 2px实线边框
    - 高对比度颜色
    - 明显的视觉反馈
    """
    return f"""
        *:focus {{
            outline: 2px solid {ZenTheme.ACCENT_PRIMARY};
            outline-offset: 2px;
        }}

        QPushButton:focus {{
            outline: 3px solid {ZenTheme.ACCENT_PRIMARY};
            outline-offset: 2px;
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {ZenTheme.ACCENT_PRIMARY};
            background-color: white;
        }}

        QListWidget::item:focus {{
            outline: 2px solid {ZenTheme.ACCENT_PRIMARY};
            outline-offset: -2px;
        }}

        QTabBar::tab:focus {{
            border: 2px solid {ZenTheme.ACCENT_PRIMARY};
        }}
    """
```

**设计特点：**
- 按钮焦点使用3px边框，其他元素使用2px
- outline-offset 提供视觉间隔
- 使用主题强调色保持风格统一

#### keyboard_navigation() - 键盘导航增强样式

```python
@classmethod
def keyboard_navigation(cls):
    """键盘导航增强样式"""
    return f"""
        /* Tab键导航高亮 */
        QWidget[accessibleName="keyboard-focus"] {{
            border: 2px solid {ZenTheme.ACCENT_SECONDARY};
            background-color: {ZenTheme.ACCENT_PALE};
        }}

        /* 选中项强调 */
        QListWidget::item:selected:active {{
            background-color: {ZenTheme.ACCENT_PRIMARY};
            color: white;
        }}

        /* 禁用状态明显标识 */
        QPushButton:disabled {{
            opacity: 0.5;
        }}

        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {ZenTheme.BG_TERTIARY};
            color: {ZenTheme.TEXT_DISABLED};
            border-style: dashed;
        }}
    """
```

**设计特点：**
- 键盘焦点使用特殊背景色高亮
- 选中项使用强调色和白色文字
- 禁用状态使用半透明和虚线边框

#### high_contrast_mode() - 高对比度模式

```python
@classmethod
def high_contrast_mode(cls):
    """高对比度模式（可选）"""
    return f"""
        /* 高对比度文本 */
        QLabel, QPushButton, QLineEdit {{
            color: #000000;
        }}

        /* 高对比度边框 */
        QFrame, QWidget {{
            border: 2px solid #000000;
        }}

        /* 高对比度按钮 */
        QPushButton {{
            background-color: #FFFFFF;
            border: 3px solid #000000;
            color: #000000;
        }}

        QPushButton:hover {{
            background-color: {ZenTheme.ACCENT_PRIMARY};
            color: #FFFFFF;
        }}

        QPushButton:pressed {{
            background-color: {ZenTheme.ACCENT_TERTIARY};
            color: #FFFFFF;
        }}
    """
```

**设计特点：**
- 纯黑色文字和边框
- 纯白色背景
- hover和pressed状态保留主题色

#### tooltips() - 优化的工具提示样式

```python
@classmethod
def tooltips(cls):
    """优化的工具提示样式"""
    return f"""
        QToolTip {{
            background-color: {ZenTheme.TEXT_PRIMARY};
            color: white;
            border: 1px solid {ZenTheme.ACCENT_PRIMARY};
            border-radius: {ZenTheme.RADIUS_SM};
            padding: 8px 12px;
            font-size: {ZenTheme.FONT_SIZE_SM};
            font-weight: {ZenTheme.FONT_WEIGHT_MEDIUM};
        }}
    """
```

#### get_all_accessibility_styles() - 获取所有可访问性样式

```python
@classmethod
def get_all_accessibility_styles(cls):
    """获取所有可访问性样式"""
    return f"""
        {cls.focus_indicator()}
        {cls.keyboard_navigation()}
        {cls.tooltips()}
    """
```

### 2. KeyboardShortcuts

键盘快捷键定义类，符合桌面应用常见约定。

#### 全局快捷键

```python
SAVE = 'Ctrl+S'         # 保存
REFRESH = 'F5'          # 刷新
SEARCH = 'Ctrl+F'       # 搜索
CLOSE = 'Ctrl+W'        # 关闭当前窗口
QUIT = 'Ctrl+Q'         # 退出应用
FULLSCREEN = 'F11'      # 全屏/退出全屏
```

#### 导航快捷键

```python
NEXT_TAB = 'Ctrl+Tab'           # 下一个标签页
PREV_TAB = 'Ctrl+Shift+Tab'     # 上一个标签页
GO_BACK = 'Alt+Left'            # 返回
GO_FORWARD = 'Alt+Right'        # 前进
```

#### 编辑快捷键

```python
UNDO = 'Ctrl+Z'         # 撤销
REDO = 'Ctrl+Y'         # 重做
CUT = 'Ctrl+X'          # 剪切
COPY = 'Ctrl+C'         # 复制
PASTE = 'Ctrl+V'        # 粘贴
SELECT_ALL = 'Ctrl+A'   # 全选
```

#### 应用特定快捷键

```python
NEW_PROJECT = 'Ctrl+N'          # 新建项目
OPEN_PROJECT = 'Ctrl+O'         # 打开项目
EXPORT = 'Ctrl+E'               # 导出
GENERATE_CHAPTER = 'Ctrl+G'     # 生成章节
START_WRITING = 'Ctrl+Enter'    # 开始创作
```

#### get_all_shortcuts() - 获取所有快捷键说明

```python
@classmethod
def get_all_shortcuts(cls):
    """获取所有快捷键说明"""
    return {
        '全局操作': {
            cls.SAVE: '保存',
            cls.REFRESH: '刷新',
            cls.SEARCH: '搜索',
            cls.CLOSE: '关闭当前窗口',
            cls.QUIT: '退出应用',
            cls.FULLSCREEN: '全屏/退出全屏'
        },
        '导航': {
            cls.NEXT_TAB: '下一个标签页',
            cls.PREV_TAB: '上一个标签页',
            cls.GO_BACK: '返回',
            cls.GO_FORWARD: '前进'
        },
        '编辑': {
            cls.UNDO: '撤销',
            cls.REDO: '重做',
            cls.CUT: '剪切',
            cls.COPY: '复制',
            cls.PASTE: '粘贴',
            cls.SELECT_ALL: '全选'
        },
        '应用功能': {
            cls.NEW_PROJECT: '新建项目',
            cls.OPEN_PROJECT: '打开项目',
            cls.EXPORT: '导出',
            cls.GENERATE_CHAPTER: '生成章节',
            cls.START_WRITING: '开始创作'
        }
    }
```

### 3. ARIALabels

ARIA标签定义类，为未来屏幕阅读器支持做准备。

#### 标签生成方法

```python
@staticmethod
def button(action):
    """按钮ARIA标签"""
    return f"按钮: {action}"

@staticmethod
def input_field(label):
    """输入框ARIA标签"""
    return f"输入框: {label}"

@staticmethod
def list_item(index, total, content):
    """列表项ARIA标签"""
    return f"第{index}项，共{total}项: {content}"

@staticmethod
def navigation(section):
    """导航区域ARIA标签"""
    return f"导航: {section}"

@staticmethod
def status(message):
    """状态信息ARIA标签"""
    return f"状态: {message}"

@staticmethod
def progress(current, total):
    """进度信息ARIA标签"""
    percentage = int((current / total) * 100) if total > 0 else 0
    return f"进度: {current}/{total} ({percentage}%)"
```

## 使用示例

### 1. 应用可访问性样式

```python
from PyQt6.QtWidgets import QApplication, QMainWindow
from themes.accessibility import AccessibilityTheme
from themes.zen_theme import ZenTheme

app = QApplication([])
main_window = QMainWindow()

# 应用基础主题
main_window.setStyleSheet(ZenTheme.background_gradient())

# 叠加可访问性样式
main_window.setStyleSheet(
    main_window.styleSheet() + 
    AccessibilityTheme.get_all_accessibility_styles()
)
```

### 2. 启用高对比度模式

```python
from themes.accessibility import AccessibilityTheme

class SettingsManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.high_contrast_enabled = False
    
    def toggle_high_contrast(self):
        """切换高对比度模式"""
        self.high_contrast_enabled = not self.high_contrast_enabled
        
        if self.high_contrast_enabled:
            # 应用高对比度样式
            self.main_window.setStyleSheet(
                AccessibilityTheme.high_contrast_mode()
            )
        else:
            # 恢复默认主题
            self.main_window.setStyleSheet(
                ZenTheme.background_gradient() +
                AccessibilityTheme.get_all_accessibility_styles()
            )
```

### 3. 配置键盘快捷键

```python
from PyQt6.QtGui import QAction, QKeySequence
from themes.accessibility import KeyboardShortcuts

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        # 保存快捷键
        save_action = QAction("保存", self)
        save_action.setShortcut(QKeySequence(KeyboardShortcuts.SAVE))
        save_action.triggered.connect(self.save_project)
        self.addAction(save_action)
        
        # 刷新快捷键
        refresh_action = QAction("刷新", self)
        refresh_action.setShortcut(QKeySequence(KeyboardShortcuts.REFRESH))
        refresh_action.triggered.connect(self.refresh_data)
        self.addAction(refresh_action)
        
        # 搜索快捷键
        search_action = QAction("搜索", self)
        search_action.setShortcut(QKeySequence(KeyboardShortcuts.SEARCH))
        search_action.triggered.connect(self.show_search_dialog)
        self.addAction(search_action)
```

### 4. 使用ARIA标签

```python
from themes.accessibility import ARIALabels

class AccessibleButton(QPushButton):
    def __init__(self, text, action_description):
        super().__init__(text)
        
        # 设置ARIA标签
        aria_label = ARIALabels.button(action_description)
        self.setAccessibleName(aria_label)
        self.setAccessibleDescription(action_description)

class AccessibleListWidget(QListWidget):
    def update_item_labels(self):
        """更新列表项的ARIA标签"""
        total = self.count()
        for i in range(total):
            item = self.item(i)
            content = item.text()
            aria_label = ARIALabels.list_item(i + 1, total, content)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, aria_label)
```

### 5. 显示键盘快捷键帮助

```python
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from themes.accessibility import KeyboardShortcuts

class ShortcutsHelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("键盘快捷键")
        
        layout = QVBoxLayout(self)
        
        # 获取所有快捷键
        shortcuts = KeyboardShortcuts.get_all_shortcuts()
        
        for category, shortcuts_dict in shortcuts.items():
            # 分类标题
            category_label = QLabel(f"<b>{category}</b>")
            layout.addWidget(category_label)
            
            # 快捷键列表
            for shortcut, description in shortcuts_dict.items():
                shortcut_label = QLabel(f"  {shortcut}: {description}")
                layout.addWidget(shortcut_label)
            
            layout.addSpacing(10)
```

### 6. 焦点管理

```python
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

class FocusManager:
    @staticmethod
    def set_keyboard_focus(widget: QWidget):
        """设置键盘焦点并高亮"""
        widget.setFocus(Qt.FocusReason.TabFocusReason)
        widget.setProperty("accessibleName", "keyboard-focus")
        widget.style().unpolish(widget)
        widget.style().polish(widget)
    
    @staticmethod
    def clear_keyboard_focus(widget: QWidget):
        """清除键盘焦点高亮"""
        widget.setProperty("accessibleName", "")
        widget.style().unpolish(widget)
        widget.style().polish(widget)
```

## 设计模式与最佳实践

### 1. 渐进增强

可访问性样式作为增强层，不影响基础功能：
```python
# 基础样式
widget.setStyleSheet(ZenTheme.button_primary())

# 叠加可访问性增强
widget.setStyleSheet(
    widget.styleSheet() + 
    AccessibilityTheme.focus_indicator()
)
```

### 2. 语义化设计

使用Qt的可访问性属性：
```python
button.setAccessibleName(ARIALabels.button("保存项目"))
button.setAccessibleDescription("点击保存当前项目到本地")
```

### 3. 键盘优先

确保所有功能都可以通过键盘访问：
```python
# 设置Tab顺序
self.setTabOrder(input1, input2)
self.setTabOrder(input2, button)

# 启用键盘导航
list_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
```

### 4. 状态反馈

明确的视觉和语义反馈：
```python
def on_save_success(self):
    # 视觉反馈
    self.status_label.setText("保存成功")
    self.status_label.setStyleSheet(f"color: {ZenTheme.SUCCESS};")
    
    # 语义反馈
    aria_message = ARIALabels.status("保存成功")
    self.status_label.setAccessibleDescription(aria_message)
```

## WCAG 2.1 合规性

### 