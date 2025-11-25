
# writing_desk_modals.py - 写作台精美Modal对话框组件

## 文件路径
`frontend/components/writing_desk_modals.py`

## 模块概述
禅意风格的写作台专用对话框组件集合，完全照抄Vue3的UI设计规范，替代系统原生对话框。提供编辑章节、查看评审、查看版本详情、生成大纲等功能的精美对话框。

## 设计理念
- **禅意风格**: 遵循ZenTheme设计规范
- **Vue3迁移**: 与原Vue3组件保持一致的UI和交互
- **无边框设计**: 自定义边框和阴影效果
- **遮罩层**: 半透明背景增强焦点
- **响应式尺寸**: 固定最大宽度，内容自适应

## 主要组件

### 1. WDEditChapterModal - 编辑章节大纲对话框
**继承**: `QDialog`  
**对应Vue3**: `WDEditChapterModal.vue`

编辑章节标题和摘要的对话框。

#### UI规范
- **遮罩层**: 30%黑色半透明
- **最大宽度**: 512px (max-w-lg)
- **圆角**: 16px
- **输入框**: 标题input + 摘要textarea(5行)
- **按钮**: 取消(灰色) + 保存(灰绿色渐变)

#### 初始化参数
- `chapter_data: dict = None` - 章节数据 `{'title': str, 'summary': str}`
- `parent: QWidget = None` - 父窗口

#### 信号
```python
saved = pyqtSignal(dict)  # 保存时发射: {'title': str, 'summary': str}
```

#### 布局结构
```python
[Dialog Container (512px)]
├── Header
│   ├── Title: "编辑章节大纲" (24px, 700)
│   └── Close Button: "✕"
├── Form
│   ├── 章节标题
│   │   ├── Label: "章节标题"
│   │   └── Input: QLineEdit (placeholder)
│   └── 章节摘要
│       ├── Label: "章节摘要"
│       └── Textarea: QTextEdit (120px height, ~5行)
└── Footer Buttons
    ├── Cancel: "取消" (secondary style)
    └── Save: "保存更改" (gradient primary)
```

#### 核心方法
```python
def onSave(self):
    """保存更改
    
    检查是否有更改:
        - 有更改: 发射saved信号，关闭对话框
        - 无更改: 直接关闭对话框
    """
```

---

### 2. WDEvaluationDetailModal - 评审详情对话框
**继承**: `QDialog`  
**对应Vue3**: `WDEvaluationDetailModal.vue`

显示AI评审结果的详情对话框，支持JSON和Markdown格式。

#### UI规范
- **遮罩层**: 50%黑色半透明 + 背景模糊
- **最大宽度**: 896px (max-w-4xl)
- **最大高度**: 80vh
- **特色图标**: 灰绿色圆形 + "◑"符号
- **内容**: JSON解析显示或Markdown渲染

#### 初始化参数
- `evaluation_text: str = ''` - 评审文本（JSON或Markdown）
- `parent: QWidget = None` - 父窗口

#### 布局结构
```python
[Dialog (896px × 80vh)]
├── Header
│   ├── Icon: "◑" (40px circle, accent color)
│   ├── Title: "AI 评审详情"
│   └── Close Button: "✕"
├── Scrollable Content
│   ├── Best Choice Card (如果有)
│   │   ├── Title: "◐ 最佳选择：版本 X"
│   │   └── Reason
│   └── Version Evaluations (循环)
│       ├── Version Title
│       ├── Overall Review
│       ├── Pros (优点列表)
│       └── Cons (缺点列表)
└── Footer
    └── Close Button: "关闭" (gradient primary)
```

#### 评审数据结构
```python
{
    "best_choice": 1,                    # 最佳版本号
    "reason_for_choice": "原因说明",
    "evaluation": {
        "version1": {
            "overall_review": "综合评价",
            "pros": ["优点1", "优点2"],
            "cons": ["缺点1", "缺点2"]
        },
        "version2": { ... }
    }
}
```

#### 核心方法
```python
def parseEvaluation(self):
    """解析评审JSON
    
    Returns:
        dict | None: 解析后的评审数据，失败返回None
    """

def renderStructuredEvaluation(self, layout, parsed_eval):
    """渲染结构化评审结果
    
    渲染内容:
        1. 最佳选择卡片（高亮显示）
        2. 各版本评估卡片（循环）
    """
```

---

### 3. WDVersionDetailModal - 版本详情对话框
**继承**: `QDialog`  
**对应Vue3**: `WDVersionDetailModal.vue`

显示单个版本的详细内容，支持版本选择。

#### UI规范
- **遮罩层**: 50%黑色半透明 + 背景模糊
- **最大宽度**: 896px
- **最大高度**: 80vh
- **头部信息**: 版本号、风格、字数统计
- **内容**: whitespace-pre-wrap显示正文
- **底部**: 当前版本标记 + 选择按钮

#### 初始化参数
- `version_index: int = 0` - 版本索引
- `version_data: dict = None` - 版本数据 `{'content': str, 'style': str}`
- `is_current: bool = False` - 是否为当前版本
- `parent: QWidget = None` - 父窗口

#### 信号
```python
versionSelected = pyqtSignal()  # 选择版本时发射
```

#### 布局结构
```python
[Dialog (896px × 80vh)]
├── Header
│   ├── Title: "版本详情"
│   ├── Meta: "版本 X • 风格 • 约 N 字"
│   └── Close Button: "✕"
├── Scrollable Content
│   └── Content Text (plain text, word wrap)
└── Footer
    ├── Current Badge (如果is_current)
    │   └── "✓ 当前选中版本" (green badge)
    ├── Or Placeholder: "未选中版本"
    ├── Close Button: "关闭" (ghost)
    └── Select Button: "选择此版本" (gradient, 仅未选中时)
```

#### 核心方法
```python
def cleanVersionContent(self, content):
    """清理版本内容
    
    处理:
        1. 尝试解析JSON，提取content字段
        2. 清理转义字符: \n, \", \t, \\
        3. 去除首尾引号
    
    Returns:
        str: 清理后的纯文本内容
    """

def onSelectVersion(self):
    """选择版本
    
    发射versionSelected信号并关闭对话框
    """
```

---

### 4. WDGenerateOutlineModal - 生成大纲对话框
**继承**: `QDialog`  
**对应Vue3**: `WDGenerateOutlineModal.vue`

输入生成章节数量的对话框，带快捷按钮。

#### UI规范
- **遮罩层**: 灰色75%透明
- **最大宽度**: 512px
- **特色**: 灰绿色圆形图标 + 数字输入 + 快捷按钮(1/2/5/10章)
- **按钮**: 生成(主要) + 取消(次要)

#### 初始化参数
- `parent: QWidget = None` - 父窗口

#### 信号
```python
generated = pyqtSignal(int)  # 生成时发射章节数
```

#### 布局结构
```python
[Dialog (512px)]
├── Content
│   ├── Header
│   │   ├── Icon: "◐" (48px circle, pale accent)
│   │   └── Title Block
│   │       ├── Title: "生成后续大纲"
│   │       └── Description: "请输入或选择..."
│   └── Form
│       ├── Label: "生成数量"
│       ├── SpinBox: 1-20 (default 5)
│       └── Quick Buttons
│           ├── "1 章"
│           ├── "2 章"
│           ├── "5 章"
│           └── "10 章"
└── Footer
    ├── Cancel: "取消"
    └── Generate: "生成" (gradient primary)
```

#### 核心方法
```python
def onGenerate(self):
    """生成大纲
    
    验证章节数 > 0，发射generated信号
    """
```

## 通用设计模式

### 1. 无边框窗口
```python
self.setWindowFlags(
    Qt.WindowType.FramelessWindowHint |  # 无边框
    Qt.WindowType.Dialog                  # 对话框类型
)
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 半透明背景
```

### 2. 遮罩层模式
```python
# 遮罩层作为主容器
overlay = QWidget(self)
overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.5);")

# 点击遮罩关闭对话框
overlay.mousePressEvent = lambda e: self.reject() if e.button() == Qt.MouseButton.LeftButton else None
```

### 3. 对话框居中
```python
container_layout = QVBoxLayout(overlay)
container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

# 添加对话框widget
container_layout.addWidget(dialog_widget)
```

### 4. 阴影效果
```python
# 使用ZenTheme提供的阴影
dialog_widget.setGraphicsEffect(ZenTheme.get_shadow_effect("LG"))
```

### 5. 渐变按钮
```python
# 主要操作按钮使用渐变
background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
    stop:0 {ZenTheme.ACCENT_PRIMARY},
    stop:1 {ZenTheme.ACCENT_SECONDARY});
```

## 使用示例

### 1. 编辑章节
```python
from components.writing_desk_modals import WDEditChapterModal

# 创建对话框
modal = WDEditChapterModal(
    chapter_data={'title': '第一章', 'summary': '章节摘要'},
    parent=self
)

# 连接信号
modal.saved.connect(self.on_chapter_saved)

# 显示对话框
if modal.exec() == QDialog.DialogCode.Accepted:
    print("用户点击了保存")

def on_chapter_saved(self, data):
    """保存回调"""
    print(f"标题: {data['title']}")
    print(f"摘要: {data['summary']}")
    # 更新章节
    self.update_chapter(data)
```

### 2. 查看评审详情
```python
from components.writing_desk_modals import WDEvaluationDetailModal
import json

# 准备评审数据
evaluation = {
    "best_choice": 2,
    "reason_for_choice": "版本2在情节和文笔上更胜一筹",
    "evaluation": {
        "version1": {
            "overall_review": "整体不错",
            "pros": ["情节流畅", "人物生动"],
            "cons": ["节奏略慢"]
        }
    }
}

# 创建对话框
modal = WDEvaluationDetailModal(
    evaluation_text=json.dumps(evaluation, ensure_ascii=False),
    parent=self
)

# 显示对话框
modal.exec()
```

### 3. 选择版本
```python
from components.writing_desk_modals import WDVersionDetailModal

# 创建版本详情对话框
modal = WDVersionDetailModal(
    version_index=0,
    version_data={
        'content': '章节内容...',
        'style': '古典风格'
    },
    is_current=False,
    parent=self
)

# 连接信号
modal.versionSelected.connect(self.on_version_selected)

# 显示对话框
