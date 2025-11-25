
# inspiration_mode.py - 灵感模式窗口

## 文件路径
`frontend/windows/inspiration_mode.py`

## 功能概述
灵感模式窗口，通过AI对话收集创意并生成小说蓝图。

**对应Web组件**: `src/views/InspirationMode.vue`

## 主要组件

### 1. ChatBubble - 对话气泡组件
**行数**: 30-117

三种类型的消息气泡：
- **user**: 用户消息（灰绿色背景，右下尖角）
- **assistant**: AI消息（浅灰背景，左下尖角）
- **error**: 错误消息（红色边框）

**样式特点**:
```python
# 用户消息
background-color: {ZenTheme.ACCENT_PRIMARY}
color: white
border-bottom-right-radius: 5px  # 尖角效果

# AI消息
background-color: {ZenTheme.BG_SECONDARY}
border-bottom-left-radius: 5px
```

### 2. ConversationInput - 对话输入组件
**行数**: 119-417

支持两种输入模式：

#### 单选模式 (single_choice)
**行数**: 168-327

- **4列网格布局**：所有选项 + "我要输入"按钮
- **选项按钮**：点击直接提交
- **"我要输入"按钮**：切换到手动输入
- **文本框**：初始禁用，点击"我要输入"后启用
- **发送按钮**：初始禁用

**关键逻辑**:
```python
def onManualInputClicked(self):
    self.is_manual_input = True
    self.text_input.setEnabled(True)
    self.submit_btn.setEnabled(True)
    self.text_input.setFocus()
```

#### 纯文本输入模式 (text_input)
**行数**: 329-389

- 文本输入框直接可用
- 发送按钮始终启用

**输入信号**:
```python
submitted = pyqtSignal(object)  # 发射 {'id': str, 'value': str}
```

### 3. BlueprintConfirmation - 蓝图确认界面
**行数**: 419-541

显示在对话完成后：
- 标题："信息收集完成"
- AI提示消息
- **"开始创建蓝图"按钮**（灰绿色渐变）
- **"重新进行灵感对话"按钮**

**信号**:
```python
generateRequested = pyqtSignal()  # 生成蓝图
restartConversationRequested = pyqtSignal()  # 重新开始
```

### 4. BlueprintDisplay - 蓝图展示界面
**行数**: 543-698

显示生成的蓝图：
- **标题**: "蓝图已生成"
- **滚动区域**: 显示蓝图内容（HTML格式）
- **操作按钮**:
  - 重新生成
  - 优化蓝图（弹出输入框）
  - 确认并保存（绿色渐变）

**蓝图内容渲染**:
```python
def renderBlueprintText(self):
    return f"""
    <h2>标题：{bp.get('title')}</h2>
    <p><strong>类型：</strong>{bp.get('genre')}</p>
    <p><strong>风格：</strong>{bp.get('style')}</p>
    <p><strong>目标读者：</strong>{bp.get('target_audience')}</p>
    <h3>故事简介</h3>
    <p>{bp.get('full_synopsis')}</p>
    """
```

**信号**:
```python
refineRequested = pyqtSignal(str)  # 优化指令
regenerateRequested = pyqtSignal()  # 重新生成
saveRequested = pyqtSignal()  # 保存
```

### 5. InspirationMode - 主页面类
**行数**: 700-1583

#### 核心属性
```python
self.project_id: str  # 项目ID
self.conversation_state: dict  # 对话状态
self.conversation_history: list  # 对话历史
self.is_complete: bool  # 对话是否完成
self.ready_for_blueprint: bool  # 是否准备生成蓝图
self.current_worker: AsyncAPIWorker  # 当前异步任务
self.task_monitor_manager: TaskMonitorManager  # 任务管理
```

#### UI结构
```
┌───────────────────────────────────────┐
│ Status Bar (状态、轮次、手动生成按钮) │
├───────────────────────────────────────┤
│                                       │
│  Content Stack (QStackedWidget):     │
│  1. 对话视图                          │
│  2. 蓝图确认视图                      │
│  3. 蓝图展示视图                      │
│                                       │
└───────────────────────────────────────┘
```

#### 状态栏组件
**行数**: 769-906

- **Ping动画**: 双层圆点（外层扩散，内层静态）
- **状态文字**: '与"文思"对话中...'
- **轮次徽章**: "第 N 轮"
- **手动生成按钮**: ≥5轮时显示
- **重启按钮**: 重新开始对话
- **退出按钮**: 返回首页

**Ping动画实现**:
```python
def animatePing(self):
    # 外层透明度: 0.75 → 0 → 0.75 循环
    self.ping_opacity += self.ping_direction
    if self.ping_opacity <= 0:
        self.ping_direction = 0.02
    elif self.ping_opacity >= 0.75:
        self.ping_direction = -0.02
```

## 核心流程

### 1. 启动流程
**行数**: 732-1107

```
应用启动
  → checkAndResumeProject()
    ├─ 有保存的项目ID？
    │   ├─ 是 → 询问用户是否恢复
    │   │   ├─ 是 → onResumeProjectSuccess()
    │   │   │       ├─ 蓝图已完成？→ 跳转详情页
    │   │   │       ├─ 有历史记录？→ 渲染历史
    │   │   │       │   ├─ 有保存状态？→ 直接恢复UI
    │   │   │       │   └─ 无保存状态？→ 调用API恢复
    │   │   │       └─ 无历史记录？→ 显示开场白
    │   │   └─ 否 → startConversation()
    │   └─ onResumeProjectError() → startConversation()
    └─ 无 → startConversation()
```

### 2. 开始对话
**行数**: 1109-1154

```python
def startConversation(self):
    # 异步创建项目
    self.current_worker = AsyncAPIWorker(
        self.api_client.create_novel,
        "未命名灵感",
        "开始灵感模式"
    )
    self.current_worker.success.connect(self.onCreateProjectSuccess)
    self.current_worker.start()

def onCreateProjectSuccess(self, response):
    self.project_id = response['id']
    # 保存项目ID
    self.config_manager.set_last_inspiration_project(self.project_id)
    # 显示硬编码开场白（无需API调用）
    self.addChatBubble('assistant', '你好！我是文思...')
    # 显示文本输入控件
    self.conversation_input.setUIControl({
        'type': 'text_input',
        'placeholder': '请输入您的故事灵感...'
    })
```

### 3. 对话循环
**行数**: 1155-1256

```python
def sendMessage(self, user_input, show_loading=True):
    # 显示用户消息
    self.addChatBubble('user', user_input.get('value'))
    
    # 异步发送消息
    self.current_worker = AsyncAPIWorker(
        self.api_client.novel_concept_converse,
        self.project_id,
        user_input=user_input,
        conversation_state=self.conversation_state
    )
    self.current_worker.success.connect(self.onMessageSuccess)
    self.current_worker.start()

def onMessageSuccess(self, response):
    # 更新状态
    self.conversation_state = response.get('conversation_state')
    self.is_complete = response.get('is_complete')
    self.ready_for_blueprint = response.get('ready_for_blueprint')
    
    # 显示AI回复
    self.addChatBubble('assistant', response.get('ai_message'))
    
    # 更新轮次徽章
    user_turns = len([b for b in self.conversation_history if b[0] == 'user'])
    self.round_badge.setText(f"第 {user_turns} 轮")
    
    # 检查是否完成
    if self.is_complete and self.ready_for_blueprint:
        # 切换到蓝图确认界面
        self.content_stack.setCurrentWidget(self.blueprint_confirmation)
    else:
        # 更新输入UI
        ui_control = response.get('ui_control', {})
        self.conversation_input.setUIControl(ui_control)
```

### 4. 生成蓝图（异步任务系统）
**行数**: 1258-1338

```python
def onGenerateBlueprint(self):
    # 调用异步API
    response = self.api_client.generate_blueprint_async(
        project_id=self.project_id,
        async_mode=True
    )
    
    # 创建任务进度对话框
    progress_dialog = TaskProgressDialog(
        task_id=task_id,
        task_name="生成蓝图",
        api_client=self.api_client,
        monitor_manager=self.task_monitor_manager,
        parent=self,
        can_cancel=True
    )
    
    # 连接完成信号
    progress_dialog.task_completed.connect(self.onGenerateBlueprintSuccess)
    progress_dialog.task_failed.connect(self.onGenerateBlueprintError)
    
    # 显示模态对话框
    progress_dialog.exec()

def onGenerateBlueprintSuccess(self, result_data):
    # 重新加载项目数据
    project = self.api_client.get_novel(self.project_id)
    blueprint_data = project.get('blueprint', {})
    
    # 创建并显示蓝图展示视图
    blueprint_display = BlueprintDisplay(blueprint_data)
    blueprint_display.refineRequested.connect(self.onRefineBlueprint)
    blueprint_display.regenerateRequested.connect(self.onRegenerateBlueprint)
    blueprint_display.saveRequested.connect(self.onSaveBlueprint)
    
    self.content_stack.addWidget(blueprint_display)
    self.content_stack.setCurrentWidget(blueprint_display)
```

### 5. 优化蓝图（异步非阻塞）
**行数**: 1340-1389

```python
def onRefineBlueprint(self, instruction):
    self.showLoading("正在优化蓝图...")
    
    self.current_worker = AsyncAPIWorker(
        self.api_client.refine_blueprint,
        self.project_id,
        instruction
    )
    self.current_worker.success.connect(self.onRefineBlueprintSuccess)
    self.current_worker.start()

def onRefineBlueprintSuccess(self, response):
    self.hideLoading()
    blueprint_data = response.get('blueprint', {})
    
    # 重新创建蓝图展示视图
    blueprint_display = BlueprintDisplay(blueprint_data)
    # ... 连接信号 ...
    
    # 替换当前视图
    current_index = self.content_stack.currentIndex()
    old_widget = self.content_stack.currentWidget()
    self.content_stack.insertWidget(current_index, blueprint_display)
    self.content_stack.setCurrentWidget(blueprint_display)
    self.content_stack.removeWidget(old_widget)
    old_widget.deleteLater()
```

### 6. 重新生成蓝图（异步任务系统）
**行数**: 1391-1484

```python
def 