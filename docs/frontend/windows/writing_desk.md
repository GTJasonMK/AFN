
# writing_desk.py - 写作台窗口

## 文件路径
`frontend/windows/writing_desk.py`

## 功能概述
写作台窗口，用于章节生成与版本管理，提供完整的章节创作工作流程。

**对应Web组件**: `src/views/WritingDesk.vue`

## 主要组件

### 1. WDHeader - 顶部导航栏
**行数**: 33-192

显示项目信息和操作按钮：
- **返回按钮**: 返回项目详情
- **项目信息**: 标题、类型、进度
- **导出按钮**: 导出为TXT/Markdown
- **项目详情按钮**: 跳转到详情页

**关键信号**:
```python
goBackClicked = pyqtSignal()
viewDetailClicked = pyqtSignal()
exportClicked = pyqtSignal(str)  # format: txt/markdown
```

**项目信息显示**:
```python
def setProject(self, project):
    genre = project.get('blueprint', {}).get('genre', '')
    completed = len([ch for ch in project.get('chapters', []) 
                     if ch.get('content')])
    total = len(project.get('blueprint', {}).get('chapter_outline', []))
    self.meta_label.setText(f"{genre} • {completed}/{total} 章")
```

### 2. WDSidebar - 左侧章节列表
**行数**: 194-737

#### 蓝图预览卡片
显示故事概要信息：
- 故事风格
- 概要文本
- 角色和关系统计

#### 章节列表
- 章节卡片（标题、摘要、状态）
- 状态徽章（未开始、进行中、已完成、失败）
- 编辑大纲按钮（未完成章节）

**关键信号**:
```python
chapterSelected = pyqtSignal(int)  # chapter_number
generateChapter = pyqtSignal(int)
generateOutline = pyqtSignal()
```

#### 章节卡片创建
**行数**: 485-689

根据 `generation_status` 显示不同状态：
```python
is_completed = generation_status == 'successful'
is_generating = generation_status in ['generating', 'evaluating', 'selecting']
is_failed = generation_status in ['failed', 'evaluation_failed']
is_waiting = generation_status == 'waiting_for_confirm'
```

**徽章颜色**:
- ✓ (绿色): 已完成
- ✗ (红色): 失败
- 蓝色: 生成中
- 黄色: 待确认
- 灰色: 未开始

#### 编辑章节大纲
**行数**: 691-720

```python
def onEditChapter(self, outline):
    modal = WDEditChapterModal(chapter_data=outline, parent=self)
    modal.saved.connect(lambda data: self.saveChapterOutline(...))
    modal.exec()
```

### 3. WDWorkspace - 主工作区
**行数**: 739-1388

**核心功能**: 显示章节详情和操作界面

#### 状态切换
使用 `QStackedWidget` 切换不同视图：
1. **空状态**: 未选择章节
2. **未生成视图**: 章节尚未生成
3. **版本选择器**: 多版本待选择
4. **内容视图**: 已完成章节

#### 内容头部
**行数**: 896-1009

显示：
- 章节编号和标题
- 状态徽章
- 章节大纲
- 操作按钮（手动编辑、重新生成）

#### 未生成视图
**行数**: 1011-1075

虚线边框的占位卡片：
- 图标和提示文字
- "开始生成章节"按钮

#### 版本选择器
**行数**: 1077-1144

显示所有生成的版本：
- 版本卡片（预览前200字）
- 重新生成按钮（单个版本）
- 选择此版本按钮
- 查看详情按钮
- 评审所有版本按钮（如果还没评审）

**版本卡片创建**:
```python
def createVersionCard(self, index, version):
    # 显示版本编号、内容预览
    # 重新生成按钮（可以重试失败的版本）
    # 选择按钮
    # 查看详情按钮
```

#### 内容视图
**行数**: 1303-1334

显示已完成章节的正文：
- 章节标题
- 完整内容（支持自动换行）
- 适合阅读的字体和行高

#### 编辑对话框
**行数**: 1336-1384

```python
def openEditDialog(self):
    dialog = QDialog(self)
    text_edit = QTextEdit()
    text_edit.setPlainText(self.selected_chapter.get('content', ''))
    # 保存按钮
    save_btn.clicked.connect(lambda: self.saveEdit(dialog, text_edit.toPlainText()))
```

**关键信号**:
```python
generateChapter = pyqtSignal(int)
selectVersion = pyqtSignal(int)  # version_index
evaluateChapter = pyqtSignal()
editContent = pyqtSignal(str)  # new_content
retryVersion = pyqtSignal(int)  # version_index
```

### 4. WritingDesk - 主页面类
**行数**: 1390-1778

#### 核心属性
```python
self.project_id: str  # 项目ID
self.project: dict  # 项目完整数据
self.selected_chapter_number: int  # 当前选中章节
self.generating_chapter: int  # 正在生成的章节
self.current_worker: AsyncAPIWorker  # 当前异步任务
self.task_monitor_manager: TaskMonitorManager  # 任务管理器
self.loading_overlay: LoadingOverlay  # 加载遮罩
```

#### UI结构
```
┌───────────────────────────────────────┐
│ Header (返回、项目信息、导出、详情)   │
├──────────┬────────────────────────────┤
│          │                            │
│ Sidebar  │  Workspace                 │
│ (蓝图+   │  (章节内容/版本选择/操作)  │
│  章节)   │                            │
│          │                            │
└──────────┴────────────────────────────┘
```

## 核心功能实现

### 1. 生成章节（异步任务系统）
**行数**: 1485-1564

```python
def onGenerateChapter(self, chapter_number):
    # 1. 显示确认对话框
    # 2. 调用异步API获取task_id
    response = self.api_client.generate_chapter_async(
        project_id=self.project_id,
        chapter_number=chapter_number,
        async_mode=True
    )
    
    # 3. 创建任务进度对话框
    progress_dialog = TaskProgressDialog(
        task_id=task_id,
        task_name=f"生成第{chapter_number}章",
        api_client=self.api_client,
        monitor_manager=self.task_monitor_manager,
        parent=self,
        can_cancel=True
    )
    
    # 4. 连接完成/失败信号
    progress_dialog.task_completed.connect(on_completed)
    progress_dialog.task_failed.connect(on_failed)
    
    # 5. 显示模态对话框
    progress_dialog.exec()
```

**生成流程**:
1. 用户确认
2. 启动异步任务
3. 显示进度对话框
4. 轮询任务状态
5. 完成后刷新界面

### 2. 选择版本
**行数**: 1566-1585

```python
def onSelectVersion(self, version_index):
    result = self.api_client.select_chapter_version(
        self.project_id,
        self.selected_chapter_number,
        version_index
    )
    # 重新加载项目
    self.loadProject()
    self.onChapterSelected(self.selected_chapter_number)
```

### 3. 评审章节（异步非阻塞）
**行数**: 1587-1632

```python
def onEvaluateChapter(self):
    # 显示加载动画
    self.showLoading(f"正在评审第{self.selected_chapter_number}章...")
    
    # 创建异步工作线程
    self.current_worker = AsyncAPIWorker(
        self.api_client.evaluate_chapter,
        self.project_id,
        self.selected_chapter_number
    )
    self.current_worker.success.connect(self.onEvaluateSuccess)
    self.current_worker.error.connect(self.onEvaluateError)
    self.current_worker.start()
```

**评审流程**:
1. 显示加载动画
2. 异步调用评审API
3. 成功后显示评审结果
4. 失败显示错误信息
5. 重新加载项目数据

### 4. 编辑章节内容
**行数**: 1634-1652

```python
def onEditContent(self, new_content):
    result = self.api_client.update_chapter(
        self.project_id,
        self.selected_chapter_number,
        new_content
    )
    # 保存成功后重新加载
    self.loadProject()
    self.onChapterSelected(self.selected_chapter_number)
```

### 5. 重试版本（异步非阻塞）
**行数**: 1654-1723

```python
def onRetryVersion(self, version_index):
    # 确认对话框
    # 标记正在重试的版本
    self.workspace.retrying_version_index = version_index
    
    # 显示加载动画
    self.showLoading(f"正在重新生成版本{version_index + 1}...")
    
    # 异步调用重试API
    self.current_worker = AsyncAPIWorker(
        self.api_client.retry_chapter_version,
        self.project_id,
        self.selected_chapter_number,
        version_index
    )
    self.current_worker.start()
```

### 6. 生成后续大纲
**行数**: 1725-1748

```python
def onGenerateOutline(self):
    # 显示输入对话框
    modal = WDGenerateOutlineModal(parent=self)
    modal.generated.connect(self.executeGenerateOutline)
    modal.exec()

def executeGenerateOutline(self, count):
    # 调用API生成指定数量的章节大纲
    self.api_client.generate_chapter_outlines_by_count(
        self.project_id,
        count
    )
```

### 7. 导出小说
**行数**: 1750-1773

```python
def exportNovel(self, format_type):
    content = self.api_client.export_novel(self.project_id, format_type)
    
    # 保存文件对话框
    file_path, _ = QFileDialog.getSaveFileName(...)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
```

## 数据流

### 页面初始化
```
__init__()
  → setupUI()
    → 创建Header、Sidebar、Workspace
    → 连接信号和槽
  → loadProject()
    → api_client.get_novel(project_id)
    → 更新各组件数据
```

### 章节选择流程
```
用户点击章节卡片
  → sidebar.chapterSelected.emit(chapter_number)
  → onChapterSelected()
    → sidebar.setSelectedChapter()  # 更新选中状态
    → workspace.setSelectedChapter()  # 更新工作区
      → 查找章节数据
      → renderContent()  # 渲染对应视图
```

### 章节生成流程
```
用户点击生成按钮
  → workspace.generateChapter.emit(chapter_number)
  → onGenerateChapter()
    → 确认对话框
    → api_client.generate_chapter_async()  # 获取task_id
    → TaskProgressDialog  # 显示进度
      → 轮询任务状态
      → task_completed信号
    → loadProject()  # 重新加载
    → onChapterSelected()  # 刷新显示
```

### 版本选择流程
```
用户点击"选择此版本"
  → workspace.selectVersion.emit(version_index)
  → onSelectVersion()
    → api_client.select_chapter_version()
    → loadProject()
    → onChapterSelected()
```

## 样式系统

### 卡片样式
```python
# 蓝图预览卡片
background: qlineargradient(
    stop:0 {ZenTheme.ACCENT_PALE}, 
    stop:1 rgba(155, 170, 153, 0.1)
)

# 章节卡片
background-color: {ZenTheme.BG_CARD}
border: 2px solid {ZenTheme.ACCENT_PRIMARY}  # 选中时
border-radius: 12px
```

### 按钮样式
```python
# 