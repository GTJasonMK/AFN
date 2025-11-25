
# Arboris 小说创作系统 - 设计规范文档

## 设计理念

本系统遵循**极简、现代、中国风**的设计理念，追求：
- **极简主义**：去除视觉噪音，保留核心功能
- **现代感**：扁平化设计，清晰的视觉层次
- **中国风**：禅意美学，留白艺术，柔和配色

---

## 一、色彩系统

### 1.1 主色调（Accent Colors）
```python
ACCENT_PRIMARY = "#8B9A8A"      # 主色：灰绿色
ACCENT_SECONDARY = "#9BAA99"    # 辅助色：浅灰绿
ACCENT_TERTIARY = "#6B7A6B"     # 深色：深灰绿
ACCENT_LIGHT = "#A5B4A5"        # 亮色
ACCENT_PALE = "rgba(139, 154, 138, 0.1)"  # 极淡背景
```

**用途**：
- 主按钮背景色
- 激活状态边框
- 强调文本
- 品牌识别

### 1.2 语义化颜色
```python
# 成功状态（绿色系）
SUCCESS = "#8BBB8B"
SUCCESS_BG = "rgba(139, 187, 139, 0.15)"

# 信息状态（蓝灰色系）
INFO = "#7A9AB4"
INFO_BG = "rgba(122, 154, 180, 0.15)"

# 警告状态（橙色系）
WARNING = "#D9A66B"
WARNING_BG = "rgba(217, 166, 107, 0.15)"

# 错误状态（红色系）
ERROR = "#D98B8B"
ERROR_BG = "rgba(217, 139, 139, 0.15)"
```

### 1.3 中性色系统
```python
# 文本颜色
TEXT_PRIMARY = "#2C3E2E"        # 主文本：深灰绿
TEXT_SECONDARY = "#5A6B5A"      # 次要文本
TEXT_TERTIARY = "#8A9B8A"       # 辅助文本
TEXT_DISABLED = "#C5D0C5"       # 禁用文本

# 背景颜色
BG_PRIMARY = "#FAFCFA"          # 主背景：极淡绿
BG_SECONDARY = "#F5F8F5"        # 次要背景
BG_TERTIARY = "#EEF2EE"         # 三级背景
BG_CARD = "#FFFFFF"             # 卡片背景

# 边框颜色
BORDER_LIGHT = "rgba(139, 154, 138, 0.15)"    # 浅边框
BORDER_DEFAULT = "rgba(139, 154, 138, 0.3)"   # 默认边框
BORDER_STRONG = "rgba(139, 154, 138, 0.5)"    # 强边框
```

### 1.4 渐变背景（仅用于页面背景）
```python
# 禅意渐变背景（从左上到右下）
GRADIENT_ZEN = """
qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #FAF7F0,
    stop:0.3 #F5F1E8,
    stop:0.6 #F0ECE3,
    stop:1 #EBE7DD)
"""
```

**重要原则**：
- ✅ **渐变仅用于页面背景**，营造整体氛围
- ❌ **禁止在按钮、卡片上使用渐变**，保持扁平化

---

## 二、间距系统（8px网格）

### 2.1 基础间距
```python
# 所有间距必须是8的倍数
SPACING_UNIT = 8

# 标准间距值
SPACING_XS = 8      # 极小间距
SPACING_SM = 16     # 小间距
SPACING_MD = 24     # 中等间距
SPACING_LG = 32     # 大间距
SPACING_XL = 48     # 超大间距
```

### 2.2 组件内边距（Padding）
```python
# 卡片内边距
PADDING_CARD_SM = "16px"
PADDING_CARD_MD = "24px"
PADDING_CARD_LG = "32px"

# 按钮内边距
PADDING_BUTTON_SM = "8px 16px"
PADDING_BUTTON_MD = "10px 20px"
PADDING_BUTTON_LG = "12px 24px"
```

### 2.3 布局外边距（Margin）
```python
# 页面边距
PAGE_MARGIN = 32

# 组件之间间距
COMPONENT_GAP_SM = 16
COMPONENT_GAP_MD = 24
COMPONENT_GAP_LG = 32
```

---

## 三、圆角系统

### 3.1 圆角规格（3个标准值）
```python
RADIUS_XS = "4px"    # 极小圆角：标签、badge
RADIUS_SM = "8px"    # 小圆角：按钮、输入框
RADIUS_MD = "12px"   # 中圆角：卡片
RADIUS_LG = "12px"   # 大圆角：对话框（同MD）
```

### 3.2 特殊圆角
```python
RADIUS_FULL = "50%"  # 圆形：头像、图标背景
```

**使用原则**：
- 按钮、输入框：8px
- 卡片、容器：12px
- 小标签：4px
- 圆形图标：50%

---

## 四、字体系统

### 4.1 字体族
```python
FONT_FAMILY = "'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', sans-serif"
```

### 4.2 字号规范（4个标准值）
```python
FONT_SIZE_XS = "12px"   # 极小：辅助说明、标签
FONT_SIZE_SM = "14px"   # 小号：正文、按钮
FONT_SIZE_BASE = "14px" # 基准：默认文本
FONT_SIZE_MD = "16px"   # 中号：副标题
FONT_SIZE_LG = "20px"   # 大号：卡片标题
FONT_SIZE_XL = "28px"   # 超大：页面主标题
```

### 4.3 字重规范
```python
FONT_WEIGHT_NORMAL = "400"    # 常规
FONT_WEIGHT_MEDIUM = "500"    # 中等
FONT_WEIGHT_SEMIBOLD = "600"  # 半粗
FONT_WEIGHT_BOLD = "700"      # 粗体
```

### 4.4 行高规范
```python
LINE_HEIGHT_TIGHT = "1.25"    # 紧凑：标题
LINE_HEIGHT_NORMAL = "1.5"    # 正常：正文
LINE_HEIGHT_RELAXED = "1.75"  # 宽松：长文本
```

---

## 五、阴影系统

### 5.1 原则
**禁止使用阴影效果**，改用细边框增强层次感：
```python
border: 2px solid {BORDER_DEFAULT}
```

### 5.2 例外情况
仅在以下场景保留极浅阴影：
- Modal对话框（提升层级感）
- 下拉菜单（分离感）

```python
# Modal阴影（如必须使用）
box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1)
```

---

## 六、按钮系统

### 6.1 主按钮（Primary Button）
```python
background-color: {ACCENT_PRIMARY}
color: white
border: none
border-radius: {RADIUS_SM}
padding: 10px 20px
font-size: {FONT_SIZE_SM}
font-weight: {FONT_WEIGHT_SEMIBOLD}

# Hover状态
background-color: {ACCENT_TERTIARY}
```

**特点**：
- ✅ 纯色背景，无渐变
- ✅ Hover时变深色
- ❌ 禁止使用渐变色

### 6.2 次要按钮（Secondary Button）
```python
background-color: {BG_SECONDARY}
color: {TEXT_PRIMARY}
border: 1px solid {BORDER_DEFAULT}
border-radius: {RADIUS_SM}
padding: 10px 20px

# Hover状态
background-color: {ACCENT_PALE}
border-color: {ACCENT_PRIMARY}
```

### 6.3 幽灵按钮（Ghost Button）
```python
background-color: transparent
color: {TEXT_SECONDARY}
border: 1px solid {BORDER_DEFAULT}
border-radius: {RADIUS_SM}
padding: 8px 16px

# Hover状态
background-color: {ACCENT_PALE}
color: {TEXT_PRIMARY}
```

### 6.4 语义化按钮
```python
# 成功按钮
background-color: {SUCCESS_BG}
color: {SUCCESS}
border: 1px solid {SUCCESS}

# Hover
background-color: {SUCCESS}
color: white

# 警告/删除按钮
background-color: {ERROR_BG}
color: {ERROR}
border: 1px solid {ERROR}

# Hover
background-color: {ERROR}
color: white
```

---

## 七、卡片系统

### 7.1 标准卡片
```python
background-color: white
border: 2px solid {BORDER_DEFAULT}
border-radius: {RADIUS_MD}
padding: 32px

# Hover状态
border-color: {ACCENT_SECONDARY}
background-color: {BG_SECONDARY}
```

### 7.2 激活卡片
```python
background-color: {ACCENT_PALE}
border: 2px solid {ACCENT_PRIMARY}
border-radius: {RADIUS_MD}
padding: 32px
```

### 7.3 信息卡片
```python
background-color: {SUCCESS_BG}
border: 1px solid {SUCCESS}
border-radius: {RADIUS_SM}
padding: 16px
```

**原则**：
- ❌ 禁止使用box-shadow
- ✅ 用2px边框增强层次
- ✅ 统一12px圆角

---

## 八、输入框系统

### 8.1 文本输入框
```python
padding: 8px 16px
border: 1px solid {BORDER_DEFAULT}
border-radius: {RADIUS_SM}
font-size: {FONT_SIZE_SM}
background-color: white

# Focus状态
border: 2px solid {ACCENT_PRIMARY}
outline: none
```

### 8.2 文本域
```python
padding: 12px 16px
border: 1px solid {BORDER_DEFAULT}
border-radius: {RADIUS_SM}
font-size: {FONT_SIZE_SM}
line-height: {LINE_HEIGHT_NORMAL}
min-height: 120px
```

---

## 九、徽章与标签

### 9.1 状态徽章
```python
# 成功状态
background-color: {SUCCESS_BG}
color: {SUCCESS}
padding: 4px 12px
border-radius: {RADIUS_SM}
font-size: {FONT_SIZE_XS}
font-weight: {FONT_WEIGHT_SEMIBOLD}

# 其他状态类似，使用对应语义色
```

### 9.2 标签
```python
background-color: {BG_TERTIARY}
color: {TEXT_SECONDARY}
padding: 2px 8px
border-radius: {RADIUS_XS}
font-size: {FONT_SIZE_XS}
```

---

## 十、图标系统

### 10.1 原则
- ✅ 优先使用文字而非emoji
- ✅ 图标大小：16px / 20px / 24px
- ✅ 图标颜色与文本保持一致

### 10.2 圆形图标背景
```python
width: 40px
height: 40px
background-color: {ACCENT_PRIMARY}
color: white
border-radius: 50%
font-size: 24px
text-align: center
line-height: 40px
```

---

## 十一、动画与过渡

### 11.1 过渡时长
```python
TRANSITION_FAST = "150ms"
TRANSITION_BASE = "200ms"
TRANSITION_SLOW = "300ms"
```

### 11.2 标准过渡
```python
transition: all 200ms ease-in-out

# 常用属性
transition: background-color 200ms ease-in-out
transition: border-color 200ms ease-in-out
transition: opacity 200ms ease-in-out
```

### 11.3 原则
- ✅ 简化动画效果
- ❌ 禁止复杂的3D变换
- ✅ 保持流畅的用户体验

---

## 十二、响应式设计

### 12.1 断点
```python
BREAKPOINT_SM = 640    # 手机
BREAKPOINT_MD = 768    # 平板
BREAKPOINT_LG = 1024   # 桌面
BREAKPOINT_XL = 1280   # 大屏
```

### 12.2 容器最大宽度
```python
CONTENT_MAX_WIDTH = "1200px"
CARD_MAX_WIDTH = "896px"
MODAL_SM_WIDTH = "512px"
MODAL_LG_WIDTH = "896px"
```

---

## 十三、可访问性

### 13.1 焦点状态
```python
# 键盘焦点样式
outline: 2px solid {ACCENT_PRIMARY}
outline-offset: 2px
```

### 13.2 对比度
- 正文文本：至少4.5:1
- 大号文本：至少3:1
- 图标与背景：至少3:1

### 13.3 交互目标
- 最小点击区域：44x44px
- 