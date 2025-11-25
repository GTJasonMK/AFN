
# frontend/themes/zen_theme.py

## 模块概述

新中式禅意主题全局样式系统，为整个应用提供统一的视觉风格和UI组件样式。该主题以极简、宁静、温暖为核心设计理念，采用毛玻璃磨砂质感、低饱和度配色和超大圆角设计。

**视觉特点：**
- 极简、宁静、毛玻璃磨砂质感
- 温暖浅米白色背景，沉静灰绿色强调
- 超大圆角、细微长投影、漂浮感
- 低饱和度、字重对比、呼吸感布局

## 设计系统

### 颜色系统

#### 背景色系（温暖浅米白色）
- `BG_PRIMARY`: 主背景 (#FAF7F0)
- `BG_SECONDARY`: 次级背景 (#F5F1E8)
- `BG_TERTIARY`: 第三级背景 (#F0ECE3)
- `BG_QUATERNARY`: 第四级背景 (#EBE7DD)
- `BG_CARD`: 卡片背景（毛玻璃效果）
- `BG_CARD_HOVER`: 卡片hover背景

#### 灰绿色系（主要强调色）
- `ACCENT_PRIMARY`: 主强调色 (#8B9A8A)
- `ACCENT_SECONDARY`: 次强调色 (#9BAA99)
- `ACCENT_TERTIARY`: 第三强调色 (#7A8B7A)
- `ACCENT_LIGHT`: 浅灰绿 (#B5C4B3)
- `ACCENT_PALE`: 极浅灰绿背景

#### 文字色系
- `TEXT_PRIMARY`: 主文字 (#3A3A3A)
- `TEXT_SECONDARY`: 次级文字 (#4A4A4A)
- `TEXT_TERTIARY`: 第三级文字 (#6A6A6A)
- `TEXT_PLACEHOLDER`: 占位符 (#8A8A8A)
- `TEXT_DISABLED`: 禁用文字 (#ABABAB)

#### 语义色系（低饱和度）
- `SUCCESS`: 成功绿 (#88A88E)
- `WARNING`: 警告橙 (#C8A88B)
- `ERROR`: 错误红 (#C88B8B)
- `INFO`: 信息蓝 (#8A9AA8)

### 圆角系统
- `RADIUS_XS`: 8px（小按钮）
- `RADIUS_SM`: 12px（输入框）
- `RADIUS_MD`: 16px（普通按钮）
- `RADIUS_LG`: 24px（卡片）
- `RADIUS_XL`: 32px（主要卡片）
- `RADIUS_CIRCLE`: 50%（圆形）

### 阴影系统
- `SHADOW_SM`: 小投影（4px偏移）
- `SHADOW_MD`: 中投影（6px偏移）
- `SHADOW_LG`: 大投影（8px偏移）
- `SHADOW_XL`: 超大投影（10px偏移）

### 字体系统
- 字号：12px - 52px（9个级别）
- 字重：300 - 700（5个级别）
- 字间距：1px - 8px（4个级别）

### 间距系统
- `SPACING_XS`: 8px
- `SPACING_SM`: 12px
- `SPACING_MD`: 16px
- `SPACING_LG`: 24px
- `SPACING_XL`: 32px
- `SPACING_2XL`: 48px
- `SPACING_3XL`: 60px

## 样式生成函数

### 按钮样式

```python
# 主要按钮
ZenTheme.button_primary()

# 次要按钮
ZenTheme.button_secondary()

# 幽灵按钮
ZenTheme.button_ghost()
```

### 输入框样式

```python
# 输入框
ZenTheme.input_field()
```

### 卡片样式

```python
# 默认卡片
ZenTheme.card()

# 超大圆角卡片
ZenTheme.card(radius="XL")
```

### 其他组件样式

```python
# 滚动条
ZenTheme.scrollbar()

# 进度条
ZenTheme.progress_bar()

# 标题
ZenTheme.label_title(size="2XL")

# 副标题
ZenTheme.label_subtitle()

# 正文
ZenTheme.label_body()

# 徽章
ZenTheme.badge(color_type="SUCCESS")

# Modal遮罩
ZenTheme.modal_overlay()

# Modal内容
ZenTheme.modal_content()

# 背景渐变
ZenTheme.background_gradient()
```

### 阴影效果对象

```python
# 获取QGraphicsDropShadowEffect对象
shadow = ZenTheme.get_shadow_effect(size="MD")
widget.setGraphicsEffect(shadow)
```

## 使用示例

### 应用全局样式

```python
from PyQt6.QtWidgets import QApplication, QMainWindow
from themes.zen_theme import ZenTheme

app = QApplication([])

# 应用背景渐变
main_window = QMainWindow()
main_window.setStyleSheet(ZenTheme.background_gradient())

# 应用滚动条样式
main_window.setStyleSheet(main_window.styleSheet() + ZenTheme.scrollbar())
```

### 按钮样式应用

```python
from PyQt6.QtWidgets import QPushButton
from themes.zen_theme import ZenTheme

# 主要按钮
primary_btn = QPushButton("确认")
primary_btn.setStyleSheet(ZenTheme.button_primary())

# 次要按钮
secondary_btn = QPushButton("取消")
secondary_btn.setStyleSheet(ZenTheme.button_secondary())

# 幽灵按钮
ghost_btn = QPushButton("更多")
ghost_btn.setStyleSheet(ZenTheme.button_ghost())
```

### 输入框样式应用

```python
from PyQt6.QtWidgets import QLineEdit, QTextEdit
from themes.zen_theme import ZenTheme

# 单行输入框
line_edit = QLineEdit()
line_edit.setStyleSheet(ZenTheme.input_field())

# 多行输入框
text_edit = QTextEdit()
text_edit.setStyleSheet(ZenTheme.input_field())
```

### 卡片样式应用

```python
from PyQt6.QtWidgets import QFrame
from themes.zen_theme import ZenTheme

# 标准卡片
card = QFrame()
card.setStyleSheet(ZenTheme.card())

# 添加阴影效果
shadow = ZenTheme.get_shadow_effect(size="MD")
card.setGraphicsEffect(shadow)
```

### 标签样式应用

```python
from PyQt6.QtWidgets import QLabel
from themes.zen_theme import ZenTheme

# 大标题
title = QLabel("欢迎使用")
title.setStyleSheet(ZenTheme.label_title(size="3XL"))

# 副标题
subtitle = QLabel("开始你的创作之旅")
subtitle.setStyleSheet(ZenTheme.label_subtitle())

# 正文
body = QLabel("这是一段正文内容")
body.setStyleSheet(ZenTheme.label_body())
```

### 徽章样式应用

```python
from PyQt6.QtWidgets import QLabel
from themes.zen_theme import ZenTheme

# 成功徽章
success_badge = QLabel("已完成")
success_badge.setStyleSheet(ZenTheme.badge(color_type="SUCCESS"))

# 警告徽章
warning_badge = QLabel("注意")
warning_badge.setStyleSheet(ZenTheme.badge(color_type="WARNING"))

# 错误徽章
error_badge = QLabel("错误")
error_badge.setStyleSheet(ZenTheme.badge(color_type="ERROR"))

# 信息徽章
info_badge = QLabel("提示")
info_badge.setStyleSheet(ZenTheme.badge(color_type="INFO"))
```

### 组合使用示例

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from themes.zen_theme import ZenTheme

class StyledWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # 设置背景
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {ZenTheme.BG_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(int(ZenTheme.SPACING_LG.replace('px', '')))
        
        # 标题
        title = QLabel("新中式禅意主题")
        title.setStyleSheet(ZenTheme.label_title())
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("极简、宁静、温暖")
        subtitle.setStyleSheet(ZenTheme.label_subtitle())
        layout.addWidget(subtitle)
        
        # 按钮
        button = QPushButton("开始体验")
        button.setStyleSheet(ZenTheme.button_primary())
        layout.addWidget(button)
        
        # 添加阴影
        shadow = ZenTheme.get_shadow_effect(size="LG")
        self.setGraphicsEffect(shadow)
```

## 设计理念

### 1. 禅意美学

- **极简主义**：去除多余装饰，只保留必要元素
- **留白艺术**：合理的间距营造呼吸感
- **自然色彩**：灰绿色系源自自然，低饱和度减少视觉疲劳

### 2. 温暖舒适

- **米白色背景**：温暖柔和，适合长时间阅读和创作
- **柔和圆角**：超大圆角减少锐利感，营造亲和力
- **细微投影**：漂浮感设计，增加层次但不突兀

### 3. 视觉层次

- **多层次背景**：4个层级的背景色支持复杂界面
- **多层次文字**：5个层级的文字色清晰表达信息重要性
- **多层次强调**：灰绿色系的渐变支持不同交互状态

### 4. 可访问性

- **适度对比度**：避免纯黑纯白，减少视觉疲劳
- **清晰的焦点状态**：明显的hover和pressed状态
- **语义化颜色**：低饱和度语义色保持风格统一

## 技术亮点

### 1. 毛玻璃效果

```python
BG_CARD = "rgba(255, 255, 255, 0.65)"  # 半透明白色
```

使用rgba透明度实现毛玻璃质感，增强视觉深度。

### 2. 渐变进度条

```python
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 {cls.ACCENT_PRIMARY},
    stop:1 {cls.ACCENT_SECONDARY});
```

使用Qt的线性渐变实现平滑的进度条效果。

### 3. 动态圆角

```python
def card(cls, radius="LG"):
    radius_value = getattr(cls, f"RADIUS_{radius}")
    return f"border-radius: {radius_value};"
```

支持动态指定圆角大小，提高灵活性。

### 4. 阴影对象生成

```python
def get_shadow_effect(cls, size="MD"):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setColor(QColor(139, 154, 138, 35))
    shadow.setOffset(0, 6)
    return shadow
```

提供QGraphicsDropShadowEffect对象，可直接应用到组件。

## 与其他组件的关系

```
ZenTheme
├── 被所有窗口类使用（MainWindow, WritingDesk等）
├── 被所有组件使用（Toast, LoadingSpinner等）
├── 配合 AccessibilityTheme 使用（可访问性增强）
└── 提供设计系统常量供其他模块引用
```

## 最佳实践

### 1. 使用设计系统常量

```python
# 好的做法
layout.setSpacing(int(ZenTheme.SPACING_MD.replace('px', '')))

# 避免硬编码
layout.setSpacing(16)  # 不推荐
```

### 2. 组合样式而非覆盖

```python
# 好的做法
widget.setStyleSheet(
    ZenTheme.button_primary() + 
    f"QPushButton {{ min-width: 120px; }}"
)

# 避免完全替换
widget.setStyleSheet("QPushButton { background: red; }")  # 会丢失主题样式
```

### 3. 使用语义化颜色

```python
# 好的做法
success_label.setStyleSheet(f"color: {ZenTheme.SUCCESS};")

# 避免硬编码颜色
success_label.setStyleSheet("color: #88A88E;")  # 不推荐
```

### 4. 合理使用阴影

```python
# 卡片使用中等阴影
card_shadow = ZenTheme.get_shadow_effect(size="MD")

# Modal使用大阴影
modal_shadow = ZenTheme.get_shadow_effect(size="XL")

# 小按钮使用小阴影或无阴影
button_shadow = ZenTheme.get_shadow_effect(size="SM")
```

## 扩展建议

1. **暗色模式**：添加 `ZenThemeDark` 类支持暗色主题
2. **主题切换**：实现运行时主题切换功能
3. **自定义主题**：支持用户自定义颜色方案
4. **动画效果**：添加过渡动画常量（如淡入淡出时长）
5. **响应式设计**：根据窗口大小动态调整字号和间距

## 注意事项

1. **性能考虑**：频繁调用样式生成函数会影响性能，建议缓存样式字符串
2. 