
# novel_detail.py - 项目详情窗口

## 文件路径
`frontend/windows/novel_detail.py`

## 功能概述
项目详情窗口，展示小说蓝图的完整信息，包括6个主要部分的内容展示和编辑功能。

**对应Web组件**: `src/views/NovelDetail.vue` + `src/components/shared/NovelDetailShell.vue`

## 主要组件

### 1. OverviewSection - 项目概览组件
**行数**: 27-196

显示小说的核心信息：
- **核心摘要**: 一句话概括故事
- **目标受众、类型、风格、基调**: 网格卡片展示
- **完整剧情梗概**: 详细故事描述
- 支持编辑功能（通过 `editRequested` 信号）

**关键特性**:
```python
editRequested = pyqtSignal(str, str, object)  # field, title, value
```

### 2. WorldSettingSection - 世界设定组件
**行数**: 198-367

展示故事的世界观设定：
- **核心规则**: 世界的基本法则
- **关键地点**: 重要场所列表
- **主要阵营**: 势力组织信息

使用 `createListCard()` 方法渲染列表项。

### 3. CharactersSection - 主要角色组件
**行数**: 369-502

展示角色信息：
- 角色网格布局（2列）
- 每个角色卡片包含：
  - 圆形头像（显示首字）
  - 身份、性格、目标、能力
  - 与主角关系

### 4. RelationshipsSection - 人物关系组件
**行数**: 504-630

展示角色之间的关系：
- 关系卡片：角色A → 关系类型 → 角色B
- 使用箭头和标签可视化关系链

### 5. ChapterOutlineSection - 章节大纲组件
**行数**: 632-1310

**最复杂的组件**，支持长篇和短篇两种流程：

#### 长篇小说流程（>50章）
1. 显示"生成部分大纲"按钮
2. 生成并显示部分大纲卡片
3. 灵活生成章节大纲

**关键方法**:
```python
onGeneratePartOutlines()  # 生成部分大纲
checkPartOutlineGenerationStatus()  # 检查生成状态
startPartOutlineProgressPolling()  # 轮询进度
```

#### 短篇小说流程（≤50章）
1. 直接生成章节大纲
2. 使用异步任务系统

**关键功能**:
- **生成大纲**: 使用 `TaskProgressDialog` 显示进度
- **灵活生成**: 生成指定数量的章节
- **删除章节**: 删除最后N个章节

### 6. ChaptersSection - 章节内容组件
**行数**: 1312-2205

**双面板布局**: 左侧章节列表 + 右侧详情

#### 左侧：章节列表
- 显示所有章节（标题、摘要、状态）
- 支持选择章节

#### 右侧：章节详情（3个标签页）
1. **正文标签页**: 
   - 计划大纲摘要
   - 实际内容概要
   - 章节正文
   
2. **版本标签页**:
   - 显示所有生成的版本
   - 点击查看详情（模态对话框）
   
3. **评审标签页**:
   - 解析JSON格式评审数据
   - 显示最佳版本选择
   - 各版本的优缺点分析

**状态徽章样式**:
```python
def getStatusBadgeStyle(self, status):
    # 'not_generated', 'generating', 'evaluating', 
    # 'selecting', 'failed', 'successful'
```

### 7. NovelDetail - 主页面类
**行数**: 2207-2882

#### 核心属性
```python
self.project_id: str  # 项目ID
self.project_data: dict  # 项目数据
self.section_data: dict  # 各section数据缓存
self.active_section: str  # 当前激活的section
self.section_widgets: dict  # section组件映射
self.task_monitor_manager: TaskMonitorManager  # 任务管理
```

#### UI结构
```
┌─────────────────────────────────────┐
│ Header (标题、导出、返回、开始创作) │
├──────────┬──────────────────────────┤
│          │                          │
│ Sidebar  │  Content Stack           │
│ (导航)   │  (6个section)            │
│          │                          │
└──────────┴──────────────────────────┘
```

#### 侧边栏导航
6个section选项：
1. 项目概览
2. 世界设定
3. 主要角色
4. 人物关系
5. 章节大纲
6. 章节内容

#### 关键方法

**数据加载**:
```python
loadProjectBasicInfo()  # 加载基本信息
loadSection(section_key)  # 异步加载section数据
_loadSectionData()  # 实际加载逻辑
createSectionWidget()  # 创建section组件
```

**编辑功能**:
```python
onSectionEdit(field, title, value)  # 编辑请求
saveSectionEdit(field, content)  # 保存编辑
```

**导出功能**:
```python
showExportMenu()  # 显示导出菜单
exportNovel(format_type)  # 导出为TXT/Markdown
```

**项目标题编辑**:
```python
editProjectTitle()  # 编辑项目标题
```

## 数据流

### 1. 页面初始化
```
__init__() 
  → setupUI() 
  → loadProjectBasicInfo()  # 只加载基本信息
  → loadSection('overview')  # 加载概览section
```

### 2. Section切换
```
switchSection(section_key)
  → 更新按钮样式
  → loadSection(section_key)
    → 检查缓存
    → _loadSectionData()  # 异步加载
      → api_client.get_section()
      → createSectionWidget()
      → 添加到content_stack
```

### 3. 编辑流程
```
用户点击编辑按钮
  → section.editRequested.emit()
  → onSectionEdit()  # 显示编辑对话框
  → 用户确认
  → saveSectionEdit()
    → api_client.update_blueprint()
    → 重新加载section
```

## 样式系统

使用 `ZenTheme` 提供的禅意风格：

**卡片样式**:
```python
background-color: {ZenTheme.BG_CARD}
border: 1px solid {ZenTheme.BORDER_LIGHT}
border-radius: {ZenTheme.RADIUS_LG}
```

**按钮样式**:
```python
# 主按钮：灰绿色渐变
background: qlineargradient(
    stop:0 {ZenTheme.ACCENT_PRIMARY}, 
    stop:1 {ZenTheme.ACCENT_SECONDARY}
)

# 次级按钮
ZenTheme.button_secondary()
```

**状态标签颜色**:
- 成功: `ZenTheme.SUCCESS` / `SUCCESS_BG`
- 失败: `ZenTheme.ERROR` / `ERROR_BG`
- 进行中: `ZenTheme.INFO` / `INFO_BG`
- 警告: `ZenTheme.WARNING` / `WARNING_BG`

## API交互

### 使用的API端点
```python
# 获取项目信息
api_client.get_novel(project_id)

# 获取section数据
api_client.get_section(project_id, section_key)

# 更新蓝图
api_client.update_blueprint(project_id, payload)

# 生成章节大纲（异步）
api_client.generate_chapter_outlines_async(project_id)

# 生成部分大纲
api_client.generate_part_outlines(project_id, total_chapters, chapters_per_part)

# 灵活生成大纲
api_client.generate_chapter_outlines_by_count(project_id, count)

# 删除章节大纲
api_client.delete_chapter_outlines(project_id, count)

# 获取章节详情
api_client.get_chapter(project_id, chapter_number)

# 导出小说
api_client.export_novel(project_id, format_type)

# 更新项目标题
api_client.update_project(project_id, payload)
```

## 异步任务管理

使用 `TaskProgressDialog` 进行长时间任务：

```python
# 创建任务进度对话框
progress_dialog = TaskProgressDialog(
    task_id=task_id,
    task_name="生成章节大纲",
    api_client=self.api_client,
    monitor_manager=self.task_monitor_manager,
    parent=self,
    can_cancel=True
)

# 连接信号
progress_dialog.task_completed.connect(on_completed)
progress_dialog.task_failed.connect(on_failed)

# 显示模态对话框
progress_dialog.exec()
```

## 特殊功能

### 1. 部分大纲生成（长篇小说）
**行数**: 1071-1201

用于超过50章的长篇小说，分步骤生成：
1. 先规划整体结构（部分大纲）
2. 再生成详细章节大纲

**进度轮询**:
```python
startPartOutlineProgressPolling()  # 开始轮询
pollPartOutlineProgress()  # 每2秒查询一次
stopPartOutlineProgressPolling()  # 停止轮询
```

### 2. 章节状态管理
使用 `generation_status` 字段：
- `not_generated`: 未生成
- `generating`: 生成中
- `evaluating`: 评审中
- `selecting`: 选择中
- `failed`: 生成失败
- `evaluation_failed`: 评审失败
- `waiting_for_confirm`: 待确认
- `successful`: 已完成

### 3. 版本详情展示
**行数**: 1736-1889

支持多版本对比：
- 版本卡片预览（前200字）
- 点击查看完整版本（模态对话框）
- 显示字数统计

### 4. 评审结果可视化
**行数**: 1890-2146

解析JSON格式的评审数据：
```python
{
  "best_choice": 1,
  "reason_for_choice": "...",
  "evaluation": {
    "版本1": {
      "pros": [...],
      "cons": [...],
      "overall_review": "..."
    }
  }
}
```

显示：
- 最佳版本高亮
- 各版本优缺点列表
- 总体评价

## 字数统计

```python
def 