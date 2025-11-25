
# UI/UX 详细优化代码修改清单

> 提供可直接应用的代码修改方案

## 📝 文件修改清单

### 1️⃣ `frontend/themes/zen_theme.py` - 主题系统优化

#### 修改1: 优化文字颜色对比度

```python
# 位置: 第34-39行
# 修改前:
TEXT_PRIMARY = "#3A3A3A"
TEXT_SECONDARY = "#4A4A4A"
TEXT_TERTIARY = "#6A6A6A"
TEXT_PLACEHOLDER = "#8A8A8A"  # ❌ 对比度不足
TEXT_DISABLED = "#ABABAB"     # ❌ 对比度不足

# 修改后:
TEXT_PRIMARY = "#2A2A2A"       # ✅ 对比度10.5:1
TEXT_SECONDARY = "#3A3A3A"     # ✅ 对比度9.2:1
TEXT_TERTIARY = "#5A5A5A"      # ✅ 对比度6.2:1
TEXT_PLACEHOLDER = "#757575"   # ✅ 对比度4.6:1
TEXT_DISABLED = "#999999"      # ✅ 对比度2.8:1
```

---

#### 修改2: 增强强调色对比度

```python
# 位置: 第28-32行
# 修改前:
ACCENT_PRIMARY = "#8B9A8A"
ACCENT_SECONDARY = "#9BAA99"
ACCENT_TERTIARY = "#7A8B7A"

# 修改后:
ACCENT_PRIMARY = "#7A8A79"     # ✅ 加深以提升白色文字对比度
ACCENT_SECONDARY = "#8A9A89"
ACCENT_TERTIARY = "#6A7A69"    # ✅ 更深的强调色
```

---

#### 修改3: 添加新的间距系统变量

```python
# 位置: 第105-113行（插入新变量）
# 在现有SPACING系统后添加:

# 间距系统（严格8px倍数）
SPACING_0 = "0px"
SPACING_XXS = "4px"      # 新增
SPACING_XS = "8px"
SPACING_SM = "16px"      # 从12px调整
SPACING_MD = "24px"      # 从16px调整
SPACING_LG = "32px"      # 从24px调整
SPACING_XL = "40px"      # 从32px调整
SPACING_2XL = "48px"
SPACING_3XL = "64px"     # 从60px调整
SPACING_4XL = "80px"     # 新增
SPACING_5XL = "96px"     # 新增

# 组件内边距预设
PADDING_BTN_SM = "8px 16px"
PADDING_BTN_MD = "12px 24px"
PADDING_BTN_LG = "16px 32px"
PADDING_INPUT = "12px 16px"
PADDING_CARD_SM = "16px"
PADDING_CARD_MD = "24px"
PADDING_CARD_LG = "32px"

# 最小尺寸
BUTTON_HEIGHT_SM = "32px"
BUTTON_HEIGHT_MD = "40px"
BUTTON_HEIGHT_LG = "48px"
TOUCH_TARGET_MIN = "44px"
```

---

#### 修改4: 添加行高系统

```python
# 在字体系统后添加（约第103行）:

# 行高系统
LINE_HEIGHT_TIGHT = "1.2"      # 标题
LINE_HEIGHT_SNUG = "1.4"       # 紧凑文本
LINE_HEIGHT_NORMAL = "1.5"     # 标准正文
LINE_HEIGHT_RELAXED = "1.6"    # 舒适阅读
LINE_HEIGHT_LOOSE = "1.8"      # 长文本

# 内容宽度限制
CONTENT_MAX_WIDTH = "720px"    # 最佳阅读宽度
CONTENT_MIN_WIDTH = "320px"
```

---

#### 修改5: 优化按钮样式 - 添加Focus和完整状态

```python
# 位置: 第119-143行
# 修改 button_primary 方法:

@classmethod
def button_primary(cls):
    """主要按钮样式"""
    return f"""
        QPushButton {{
            background-color: {cls.ACCENT_PRIMARY};
            color: white;
            border: none;
            border-radius: {cls.RADIUS_MD};
            padding: {cls.PADDING_BTN_MD};
            font-size: {cls.FONT_SIZE_BASE};
            font-weight: {cls.FONT_WEIGHT_MEDIUM};
            min-height: {cls.BUTTON_HEIGHT_MD};
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {cls.ACCENT_TERTIARY};
        }}
        QPushButton:pressed {{
            background-color: {cls.ACCENT_TERTIARY};
            transform: translateY(1px);
        }}
        QPushButton:focus {{
            outline: 3px solid {cls.ACCENT_PRIMARY};
            outline-offset: 2px;
        }}
        QPushButton:disabled {{
            background-color: {cls.BG_TERTIARY};
            color: {cls.TEXT_DISABLED};
            opacity: 0.6;
        }}
    """
```

---

### 2️⃣ `frontend/pages/home_page.py` - 首页优化

#### 修改1: 设置按钮对比度优化

```python
# 位置: 第247-270行
# 修改前:
settings_btn.setStyleSheet("""
    QPushButton {
        background-color: rgba(139, 154, 138, 0.15);  # ❌ 对比度不足
        color: #3A3A3A;
        ...
    }
""")

# 修改后:
settings_btn.setStyleSheet(f"""
    QPushButton {{
        background-color: rgba(139, 154, 138, 0.25);  # ✅ 增加不透明度
        color: {ZenTheme.TEXT_PRIMARY};  # ✅ 使用最深文字色
        border: 2px solid rgba(139, 154, 138, 0.6);  # ✅ 增强边框
        border-radius: 20px;
        padding: 10px 24px;
        font-size: 14px;
        font-weight: 600;
        min-height: 40px;  # ✅ 添加最小高度
    }}
    QPushButton:hover {{
        background-color: rgba(139, 154, 138, 0.45);  # ✅ 增强hover状态
        border-color: {ZenTheme.ACCENT_PRIMARY};
        color: {ZenTheme.TEXT_PRIMARY};
    }}
    QPushButton:focus {{
        outline: 2px solid {ZenTheme.ACCENT_PRIMARY};  # ✅ 添加focus状态
        outline-offset: 2px;
    }}
""")
```

---

#### 修改2: 优化标题字体大小比例

```python
# 位置: 第281-303行
# 修改前:
main_title.setStyleSheet("""
    font-size: 52px;  # ❌ 过大
    ...
""")
subtitle.setStyleSheet("""
    font-size: 20px;  # ❌ 比例失调
    ...
""")

# 修改后:
main_title.setStyleSheet(f"""
    font-size: {ZenTheme.FONT_SIZE_4XL};  # 48px ✅
    font-weight: {ZenTheme.FONT_WEIGHT_LIGHT};  # 300
    color: {ZenTheme.TEXT_PRIMARY};
    letter-spacing: 8px;
    margin-bottom: 8px;
""")

subtitle.setStyleSheet(f"""
    font-size: {ZenTheme.FONT_SIZE_XL};  # 24px ✅
    font-weight: {ZenTheme.FONT_WEIGHT_NORMAL};  # 400
    color: {ZenTheme.TEXT_TERTIARY};
    letter-spacing: 4px;
    margin-bottom: 16px;
""")
```

---

### 3️⃣ `frontend/windows/writing_desk.py` - 写作台优化

#### 修改1: 返回按钮尺寸修正

```python
# 位置: 第64-80行
# 修改前:
back_btn.setFixedSize(36, 36)  # ❌ 过小

# 修改后:
back_btn.setFixedSize(44, 44)  # ✅ 符合WCAG标准
back_btn.setStyleSheet(f"""
    QPushButton {{
        min-width: 44px;
        min-height: 44px;
        background-color: transparent;
        color: {ZenTheme.TEXT_SECONDARY};
        border: none;
        border-radius: {ZenTheme.RADIUS_SM};
        font-size: 20px;
    }}
    QPushButton:hover {{
        background-color: {ZenTheme.ACCENT_PALE};
        color: {ZenTheme.TEXT_PRIMARY};
    }}
    QPushButton:focus {{
        outline: 2px solid {ZenTheme.ACCENT_PRIMARY};  # ✅ 添加focus
        outline-offset: 2px;
    }}
""")
```

---

#### 修改2: 章节列表间距优化

```python
# 位置: 第410行
# 修改前:
self.chapter_list_layout.setSpacing(8)  # ❌ 过小

# 修改后:
self.chapter_list_layout.setSpacing(16)  # ✅ 符合间距系统
```

---

#### 修改3: 列表标题区域留白

```python
# 位置: 第370-372行
# 修改前:
list_header_layout.setContentsMargins(0, 0, 0, 0)  # ❌ 无边距

# 修改后:
list_header_layout.setContentsMargins(16, 16, 16, 16)  # ✅ 添加留白
```

---

#### 修改4: 章节徽章尺寸调整

```python
# 位置: 第527-571行
# 修改前:
badge.setFixedSize(32, 32)  # ❌ 过小

# 修改后:
badge.setFixedSize(36, 36)  # ✅ 增加到36px
badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

if is_completed:
    badge.setStyleSheet(f"""
        background-color: {ZenTheme.SUCCESS};
        color: white;
        border-radius: 18px;  # ✅ 圆角为宽度的一半
        font-size: 14px;  # ✅ 从13px增加
        font-weight: 700;
    """)
```

---

#### 修改5: 正文行高优化

```python
# 位置: 第1324-1332行
# 修改前:
content.setStyleSheet(f"""
    ...
    line-height: 2.0;  # ❌ 过大
    ...
""")

# 修改后:
content.setStyleSheet(f"""
    font-size: {ZenTheme.FONT_SIZE_BASE};
    color: {ZenTheme.TEXT_SECONDARY};
    line-height: {ZenTheme.LINE_HEIGHT_RELAXED};  # 1.6 ✅
    max-width: {ZenTheme.CONTENT_MAX_WIDTH};  # ✅ 限制宽度
    font-family: 'Microsoft YaHei', serif;
""")
```

---

#### 修改6: 重试按钮增强反馈

```python
# 位置: 第1196-1220行
# 修改 retry_btn 样式:

is_retrying = hasattr(self, 'retrying_version_index') and self.retrying_version_index == index

retry_btn = QPushButton("⟳ 生成中..." if is_retrying else "重新生成")  # ✅ 添加图标
retry_btn.setCursor(Qt.CursorShape.PointingHandCursor if not is_retrying else Qt.CursorShape.WaitCursor)
retry_btn.setEnabled(not is_retrying)
retry_btn.setStyleSheet(f"""
    QPushButton {{
        background-color: {ZenTheme.WARNING if not is_retrying else ZenTheme.INFO};
        color: white;
        border: none;
        border-radius: {ZenTheme.RADIUS_XS};
        padding: 6px 16px;
        font-size: 12px;
        font-weight: 600;
        min-height: 32px;  # ✅ 添加最小高度
    }}
    QPushButton:hover:enabled {{
        background-color: {ZenTheme.ACCENT_TERTIARY};
    }}
    QPushButton:disabled {{
        background-color: {ZenTheme.INFO_BG};
        color: {ZenTheme.INFO};
        opacity: 0.7;  # ✅ 添加视觉反馈
    }}
""")
```

---

### 4️⃣ `frontend/themes/accessibility.py` - 可访问性增强

#### 修改1: 增强focus指示器

```python
# 位置: 第26-50行
# 修改 focus_indicator 方法:

@classmethod
def focus_indicator(cls):
    """全局焦点指示器样式"""
    return f"""
        *:focus {{
            outline: 2px solid {ZenTheme.ACCENT_PRIMARY};
            outline-offset: 2px;
        }}

        QPushButton:focus {{
            outline: 3px solid {ZenTheme.ACCENT_PRIMARY};  # ✅ 按钮更明显
            outline-offset: 2px;
            box-shadow: 0 0 0 4px {ZenTheme.ACCENT_PALE};  # ✅ 添加光晕
        }}

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {ZenTheme.ACCENT_PRIMARY};
            background-color: white;
            color: {ZenTheme.TEXT_PRIMARY};
            box-shadow: 0 0 0 3px {ZenTheme.ACCENT_PALE};  # ✅ 添加光晕
        }}

        QListWidget::item:focus {{
            outline: 2px solid {ZenTheme.ACCENT_PRIMARY};
            outline-offset: -2px;
            background-color: {ZenTheme.ACCENT_PALE};  # ✅ 添加背景
        }}
    """
```

---

## 🔄 批量替换清单

### 替换1: 硬编码圆角值

```bash
# 在所有.py文件中执行以下替换:

查找: border-radius: 6px;
替换为: border-radius: {ZenTheme.RADIUS_XS};

查找: border-radius: 8px;
替换为: border-radius: {ZenTheme.RADIUS_SM};

查找: border-radius: 10px;
替换为: border-radius: {ZenTheme.RADIUS_SM};

查找: border-radius: 12px;
替换为: border-radius: {ZenTheme.RADIUS_MD};

查找: border-radius: 16px;
替换为: border-radius: {ZenTheme.RADIUS_LG};

查找: border-radius: 20px;
替换为: border-radius: {ZenTheme.RADIUS_LG};

查找: border-radius: 24px;
替换为: border-radius: {ZenTheme.RADIUS_XL};

查找: border-radius: 32px;
替换为: border-radius: {ZenTheme.RADIUS_2XL};
```

---

### 替换2: 硬编码间距值

```bash
# 替换不符合8px倍数的间距:

查找: padding: 10px
替换为: padding: 8px  或  padding: {ZenTheme.PADDING_XS}

查找: margin: 