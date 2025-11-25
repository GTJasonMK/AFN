# 灵感选项交互功能实现总结

> 实现时间：2025-11-22
> 功能需求：将灵感模式改造为交互式选项选择模式，AI给出多个创意方向供用户选择或自由输入

---

## 功能概述

### 用户体验流程

1. **用户输入灵感** → "我想写一个关于时间的故事"
2. **AI分析并提供选项** → 显示3-5个具体的发展方向卡片
   - 硬科幻时间旅行
   - 奇幻时间魔法
   - 情感时光倒流
   - 时间循环悬疑
3. **用户交互选择**
   - 点击任意选项卡片 → 自动发送选择
   - 或在输入框自由输入 → 提供新想法
4. **AI继续对话** → 基于用户选择深入讨论

### 技术特性

- **动态UI控件**：使用 `inspired_options` 类型，根据对话轮次自动切换
- **渐进式交互**：早期轮次（≤3）提供选项引导，后期改为自由输入
- **向后兼容**：保持与现有 UIControl 机制的兼容
- **主题适配**：完整支持深色/亮色主题切换

---

## 修改的文件清单

### 后端修改（4个文件）

#### 1. `backend/app/schemas/novel.py`

**修改内容**：扩展 `ChoiceOption` 模型

```python
class ChoiceOption(BaseModel):
    """前端选择项描述，用于动态 UI 控件。"""
    id: str
    label: str
    description: Optional[str] = Field(default=None, description="选项详细描述（用于灵感选项卡片）")
    key_elements: Optional[List[str]] = Field(default=None, description="关键要素标签列表（用于灵感选项卡片）")
```

**新增字段**：
- `description` - 选项详细描述（50-100字）
- `key_elements` - 2-3个关键要素标签

---

#### 2. `backend/app/api/routers/novels/inspiration.py`

**修改内容**：更新 `JSON_RESPONSE_INSTRUCTION` 常量

**新增内容**（lines 42-104）：
- 新增 `inspired_options` UI控件类型说明
- 使用时机说明（对话轮次 ≤ 3）
- 完整的JSON响应示例

**关键指令**：
```python
**UI控件类型说明：**
- `inspired_options`: 灵感选项卡片（显示label、description、key_elements）

**何时使用inspired_options：**
- 对话轮次 <= 3 且用户刚提供初步想法
- 需要引导用户选择具体方向时
- 每个选项必须包含：id、label（标题）、description（详细描述50-100字）、key_elements（2-3个关键要素）
- 提供3-5个差异化明显的选项
```

---

#### 3. `backend/prompts/inspiration.md`

**修改内容**：更新灵感对话Prompt模板

**修改位置**：
- Lines 12-17：新增 Guiding Principles 4 & 5
  - Principle 4: Creative Inspired Options（对话前3轮）
  - Principle 5: Flexible Choice Guidance（对话后期）
- Lines 38-91：添加完整的 inspired_options JSON示例

**示例选项结构**：
```json
{
  "id": "opt_1",
  "label": "硬科幻时间旅行",
  "description": "以严谨的物理学为基础，探讨时间悖论和因果律。主角可能是科学家意外发现时间旅行技术，需要修复时间线的裂痕。",
  "key_elements": ["时间悖论", "平行宇宙", "蝴蝶效应"]
}
```

---

### 前端修改（3个文件）

#### 4. `frontend/windows/inspiration_mode/inspired_option_card.py` ⭐ 新建文件

**组件1：InspiredOptionCard**

单个灵感选项卡片，包含：
- **编号标识**：从 option_id 提取（如 "opt_1" → "1"）
- **标题**：label 字段（8-12字，加粗显示）
- **详细描述**：description 字段（自动换行）
- **关键要素标签**：key_elements 列表（#标签形式）

**交互特性**：
- 鼠标悬停：边框变色 + 边框加粗
- 点击选择：高亮显示 + 发射 `clicked` 信号
- 主题适配：深色/亮色模式自动切换

**代码结构**（182行）：
```python
class InspiredOptionCard(ThemeAwareWidget):
    clicked = pyqtSignal(str, str)  # (option_id, label)

    def _create_ui_structure(self):
        # 标题行：编号 + 标题
        # 描述文本
        # 关键要素标签

    def _apply_theme(self):
        # 卡片基础样式
        # 编号标签样式
        # 标题/描述/标签样式
```

---

**组件2：InspiredOptionsContainer**

选项容器，管理多个选项卡片：
- **功能**：显示3-5个选项卡片，支持单选
- **信号**：`option_selected(option_id, label)` - 用户选择事件
- **逻辑**：点击某个卡片后，其他卡片自动取消选中

**代码结构**（52行）：
```python
class InspiredOptionsContainer(ThemeAwareWidget):
    option_selected = pyqtSignal(str, str)

    def _create_ui_structure(self):
        # 创建所有选项卡片
        # 连接点击信号

    def on_card_clicked(self, option_id, label):
        # 取消其他卡片选中
        # 发射选择信号
```

---

#### 5. `frontend/windows/inspiration_mode/main.py`

**修改内容**：集成选项显示功能

**Line 24**：导入组件
```python
from .inspired_option_card import InspiredOptionsContainer
```

**Lines 259-281**：修改 `onConversationSuccess` 方法
```python
def onConversationSuccess(self, response):
    # ... 原有逻辑 ...

    # 检查是否有UI控件（灵感选项）
    ui_control = response.get('ui_control', {})
    control_type = ui_control.get('type')

    if control_type == 'inspired_options':
        # 显示灵感选项卡片
        options_data = ui_control.get('options', [])
        if options_data:
            self._add_inspired_options(options_data)

            # 更新输入框placeholder
            placeholder = ui_control.get('placeholder', '或者输入你的新想法...')
            self.input_widget.setPlaceholder(placeholder)
    else:
        # 恢复默认placeholder
        self.input_widget.setPlaceholder('输入你的想法...')
```

**Lines 404-422**：新增辅助方法
```python
def _add_inspired_options(self, options_data):
    """添加灵感选项卡片"""
    options_container = InspiredOptionsContainer(options_data)
    options_container.option_selected.connect(self._on_option_selected)
    self.chat_layout.insertWidget(self.chat_layout.count() - 1, options_container)

def _on_option_selected(self, option_id, option_label):
    """用户选择了某个灵感选项"""
    message = f"选择：{option_label}"
    self.onMessageSent(message)
```

---

#### 6. `frontend/windows/inspiration_mode/conversation_input.py`

**修改内容**：新增 `setPlaceholder` 方法

**Lines 148-151**：
```python
def setPlaceholder(self, text):
    """设置输入框占位符文本"""
    if self.input_field:
        self.input_field.setPlaceholderText(text)
```

**用途**：动态更新输入框提示文本，引导用户可以选择或自由输入

---

## 技术实现细节

### 1. 组件基类使用规范

所有自定义组件继承 `ThemeAwareWidget`，遵循以下生命周期：

```python
class MyComponent(ThemeAwareWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()  # ✓ 正确调用

    def _create_ui_structure(self):
        # 创建UI结构（只调用一次）
        pass

    def _apply_theme(self):
        # 应用主题样式（每次主题切换都调用）
        pass

    def some_event_handler(self):
        # 需要手动刷新主题时
        self.refresh_theme()  # ✓ 使用公共接口
```

**注意事项**：
- ❌ 不要调用 `self.apply_theme()`
- ❌ 不要调用 `self.update_theme()`
- ✅ 正确调用 `self.setupUI()`
- ✅ 手动刷新使用 `self.refresh_theme()`

---

### 2. 信号槽连接机制

**卡片点击事件流**：
```
用户点击卡片
  ↓
InspiredOptionCard.mousePressEvent()
  ↓
发射 clicked 信号 (option_id, label)
  ↓
InspiredOptionsContainer.on_card_clicked()
  ↓
取消其他卡片选中 + 发射 option_selected 信号
  ↓
InspirationMode._on_option_selected()
  ↓
构造消息 "选择：{label}"
  ↓
调用 onMessageSent() 发送给API
```

---

### 3. UI响应式设计

**选项卡片样式**（inspired_option_card.py:107-120）：

```python
InspiredOptionCard {
    background: #FFFFFF;  # 亮色模式
    border: 1px solid #E5E7EB;  # 默认边框
    border-radius: 8px;
}

InspiredOptionCard:hover {
    background: #F9FAFB;  # 悬停背景
    border-color: #6366f1;  # 主题色边框
    border-width: 2px;  # 边框加粗
}

/* 选中状态 */
border: 2px solid #6366f1;
```

**标签样式**（inspired_option_card.py:156-163）：
```python
QLabel#tagLabel {
    color: #6366f1;  # 主题色文字
    background: #6366f122;  # 半透明背景
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}
```

---

## 测试验证

### 组件单元测试

创建测试脚本验证功能（已完成后删除）：

```python
# frontend/test_inspired_options.py
TEST_OPTIONS = [
    {
        "id": "opt_1",
        "label": "硬科幻时间旅行",
        "description": "以严谨的物理学为基础...",
        "key_elements": ["时间悖论", "因果律", "平行宇宙"]
    },
    # ... 3-4个其他选项
]

options_container = InspiredOptionsContainer(TEST_OPTIONS)
options_container.option_selected.connect(on_option_selected)
```

**测试结果**：✅ 通过
- 组件正确渲染
- 点击事件正常触发
- 信号槽连接工作正常
- 主题切换自动适配

---

### 集成测试清单

- [x] 后端Schema验证（ChoiceOption模型）
- [x] Prompt模板JSON格式验证
- [x] 前端组件导入验证（无ImportError）
- [x] 组件渲染测试（测试脚本）
- [x] 点击事件测试（信号正确发射）
- [ ] 端到端测试（需要启动完整应用 + 配置LLM）

---

## 使用示例

### 后端Prompt响应示例

当用户输入"我想写一个关于时间的故事"时，LLM应返回：

```json
{
  "ai_message": "时间主题真是取之不尽的创意宝库！从科幻到奇幻，从哲学到情感，每个方向都能通向一个独特的故事宇宙。我为你准备了几种不同的探索路径：",
  "ui_control": {
    "type": "inspired_options",
    "options": [
      {
        "id": "opt_1",
        "label": "硬科幻时间旅行",
        "description": "以严谨的物理学为基础，探讨时间悖论和因果律。主角可能是科学家意外发现时间旅行技术，却发现每次干预都会引发蝴蝶效应，必须在修复时间线和保护自己存在之间做出艰难抉择。",
        "key_elements": ["时间悖论", "因果律", "平行宇宙"]
      },
      {
        "id": "opt_2",
        "label": "奇幻时间魔法",
        "description": "在魔法世界中，时间是最稀有也最危险的魔法属性。主角天生拥有时间魔法，但每次使用都要付出生命代价——加速自己的衰老。这是一个关于选择和牺牲的故事。",
        "key_elements": ["时间魔法", "代价机制", "命运抉择"]
      }
    ],
    "placeholder": "或者告诉我你的新想法..."
  },
  "conversation_state": {"round": 1},
  "is_complete": false
}
```

---

### 前端渲染效果

```
┌─────────────────────────────────────────┐
│ ① 硬科幻时间旅行                         │
│                                         │
│ 以严谨的物理学为基础，探讨时间悖论和因   │
│ 果律。主角可能是科学家意外发现时间旅行   │
│ 技术，却发现每次干预都会引发蝴蝶效应...  │
│                                         │
│ #时间悖论 #因果律 #平行宇宙              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ② 奇幻时间魔法                           │
│                                         │
│ 在魔法世界中，时间是最稀有也最危险的魔   │
│ 法属性。主角天生拥有时间魔法，但每次使   │
│ 用都要付出生命代价——加速自己的衰老...    │
│                                         │
│ #时间魔法 #代价机制 #命运抉择            │
└─────────────────────────────────────────┘

[或者输入你的新想法...] [发送]
```

---

## 向后兼容性

### 现有功能不受影响

- ✅ `single_choice` 类型仍然有效
- ✅ `text_input` 类型仍然有效
- ✅ `info_display` 类型仍然有效
- ✅ ChoiceOption 的 `id` 和 `label` 字段保持必需
- ✅ `description` 和 `key_elements` 为可选字段（向后兼容）

### API客户端兼容

前端 `ArborisAPIClient.inspiration_converse()` 方法无需修改，因为：
- 后端返回的JSON结构保持向后兼容
- 前端通过 `ui_control.type` 动态判断渲染方式
- 未识别的控件类型会被忽略（降级到默认行为）

---

## 已知限制和未来改进

### 当前限制

1. **对话轮次判断**：目前基于后端返回的 `ui_control.type`
   - 前端没有独立判断轮次的逻辑
   - 完全依赖后端Prompt的正确性

2. **选项数量**：建议3-5个，但未强制限制
   - 过多选项可能导致UI溢出
   - 建议在Prompt中明确限制

3. **移动端适配**：当前仅针对桌面端设计
   - 卡片宽度固定，未响应式适配
   - 触摸事件未特别优化

### 未来改进方向

1. **动画效果**
   - 选项卡片淡入动画
   - 选择时的视觉反馈增强

2. **可访问性**
   - 键盘导航支持（Tab切换选项）
   - 屏幕阅读器支持

3. **高级功能**
   - 支持多选模式（当前仅单选）
   - 选项卡片折叠/展开（长描述场景）

---

## 相关文档

- [CLAUDE.md](../CLAUDE.md) - 项目开发规范
- [CODE_REVIEW_COMPREHENSIVE.md](CODE_REVIEW_COMPREHENSIVE.md) - 代码审查报告
- [backend/prompts/inspiration.md](../backend/prompts/inspiration.md) - 灵感对话Prompt模板
- [frontend/components/base/theme_aware_widget.py](../frontend/components/base/theme_aware_widget.py) - 主题感知组件基类

---

**开发者**：Claude Code
**完成时间**：2025-11-22
**版本**：1.0.0
**状态**：✅ 已完成并通过测试
