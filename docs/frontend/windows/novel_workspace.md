
# frontend/windows/novel_workspace.py - 项目列表工作台

## 文件概述

项目列表页面，展示所有小说项目，支持创建、查看、编辑和删除项目。采用禅意风格设计。

**文件路径**: `frontend/windows/novel_workspace.py`  
**行数**: 567行

## 核心组件

### 1. NovelWorkspace - 主页面类

```python
class NovelWorkspace(BasePage):
    """项目列表页面 - 禅意风格"""
```

**功能**:
- 展示所有小说项目
- 创建新项目入口
- 项目卡片交互（查看、编辑、删除）
- 3列网格布局

### 2. ProjectCard - 项目卡片

```python
class ProjectCard(QFrame):
    """禅意风格项目卡片"""
    
    viewDetailsClicked = pyqtSignal(str)      # 查看详情
    continueWritingClicked = pyqtSignal(str)  # 继续创作
    deleteClicked = pyqtSignal(str)           # 删除项目
```

**设计特点**:
- **大圆角**: 24px，柔和视觉
- **灰绿色系**: 禅意配色
- **细微投影**: 层次感
- **Hover动画**: 上移4px + 投影增强

#### 卡片结构

```
┌─────────────────────────────────┐
│ 📖 [图标]  项目标题              │
│            类型 · 状态            │
│            最后编辑时间           │
│                                  │
│ [进度条] 完成进度 60%             │
│                                  │
│ [类型标签] [章节标签]              │
│                                  │
│ [Hover显示]                      │
│ [查看详情] [🗑] [继续创作]        │
└─────────────────────────────────┘
```

#### 卡片数据

```python
project_data = {
    'id': 'abc123',
    'title': '项目标题',
    'status': 'writing',
    'total_chapters': 50,
    'completed_chapters': 30,
    'updated_at': '2025-01-15T12:00:00',
    'blueprint': {
        'genre': '科幻'
    }
}
```

### 3. CreateProjectCard - 创建项目卡片

```python
class CreateProjectCard(QFrame):
    """创建新项目卡片 - 禅意风格"""
    
    clicked = pyqtSignal()
```

**样式**:
- 虚线边框（3px dashed）
- 半透明背景
- 大号"+"图标（72px）
- Hover变色

## 项目卡片详解

### 卡片状态映射

```python
def getStatusText(self, status):
    status_map = {
        'draft': '草稿',
        'blueprint_ready': '蓝图就绪',
        'part_outlines_ready': '分卷大纲就绪',
        'chapter_outlines_ready': '章节大纲就绪',
        'writing': '写作中',
        'completed': '已完成'
    }
    return status_map.get(status, '未知状态')
```

### 进度条实现

```python
progress_percent = int((completed_chapters / total_chapters * 100) 
                       if total_chapters > 0 else 0)

# 进度条背景
progress_bar_bg.setStyleSheet(f"""
    background-color: {ZenTheme.BG_TERTIARY};
    border-radius: 5px;
""")

# 进度条填充（灰绿色渐变）
progress_bar_fill.setStyleSheet(f"""
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ZenTheme.ACCENT_PRIMARY},
        stop:1 {ZenTheme.ACCENT_SECONDARY});
    border-radius: 5px;
""")
```

### Hover动画

```python
def enterEvent(self, event):
    """鼠标进入 - 触发动画"""
    
    # 1. 按钮渐显（透明度 0 → 1）
    self.opacity_animation = QPropertyAnimation(self.buttons_opacity, b"opacity")
    self.opacity_animation.setDuration(350)
    self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    # 2. 卡片上移4px
    self.move_animation = QPropertyAnimation(self, b"geometry")
    current_geo = self.geometry()
    target_geo = QRect(current_geo.x(), current_geo.y() - 4, 
                      current_geo.width(), current_geo.height())
    
    # 3. 边框变色 + 投影增强
    self.setStyleSheet(f"""
        border: 2px solid {ZenTheme.ACCENT_PRIMARY};
    """)
    self.setGraphicsEffect(ZenTheme.get_shadow_effect("LG"))
```

### 标签系统

```python
# 类型标签
genre_tag = QLabel(genre)
genre_tag.setStyleSheet(f"""
    background-color: {ZenTheme.ACCENT_PALE};
    color: {ZenTheme.TEXT_PRIMARY};
    padding: 4px 14px;
    border-radius: 12px;
    font-size: 13px;
""")

# 章节标签
chapter_tag = QLabel(f"{completed_chapters}/{total_chapters} 章")
chapter_tag.setStyleSheet(f"""
    background-color: {ZenTheme.SUCCESS_BG};
    color: {ZenTheme.TEXT_PRIMARY};
    padding: 4px 14px;
    border-radius: 12px;
""")
```

## NovelWorkspace 主页面

### UI布局

```python
def setupUI(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(48, 48, 48, 48)
    layout.setSpacing(32)
    
    # 1. 顶部标题栏
    header_layout = QHBoxLayout()
    title = QLabel("我的小说项目")
    title.setStyleSheet(f"""
        font-size: 36px;
        font-weight: 300;
        letter-spacing: 4px;
    """)
    
    # 2. 项目网格（滚动区域）
    scroll_area = QScrollArea()
    self.grid_layout = QGridLayout()
    self.grid_layout.setSpacing(32)  # 卡片间距
    
    # 3. 背景样式
    self.setStyleSheet(ZenTheme.background_gradient())
```

### 项目加载

```python
def loadProjects(self):
    """加载项目列表"""
    try:
        response = self.api_client.get_all_novels()
        self.projects = response
        self.renderProjects()
    except Exception as e:
        QMessageBox.critical(self, "错误", f"加载项目失败：{str(e)}")
```

### 项目渲染

```python
def renderProjects(self):
    """渲染项目卡片（3列网格）"""
    
    # 第一个位置：创建新项目卡片
    create_card = CreateProjectCard()
    create_card.clicked.connect(self.onCreateProject)
    self.grid_layout.addWidget(create_card, 0, 0)
    
    # 渲染项目卡片
    for idx, project in enumerate(self.projects):
        row = (idx + 1) // 3
        col = (idx + 1) % 3
        
        card = ProjectCard(project)
        card.viewDetailsClicked.connect(self.onViewDetails)
        card.continueWritingClicked.connect(self.onContinueWriting)
        card.deleteClicked.connect(self.onDeleteProject)
        
        self.grid_layout.addWidget(card, row, col)
```

## 交互功能

### 1. 创建新项目

```python
def onCreateProject(self):
    """创建新项目 - 导航到灵感模式"""
    self.navigateTo('INSPIRATION')
```

### 2. 查看项目详情

```python
def onViewDetails(self, project_id):
    """查看项目详情"""
    self.navigateTo('DETAIL', project_id=project_id)
```

### 3. 继续创作

```python
def onContinueWriting(self, project_id):
    """继续创作 - 打开写作台"""
    self.navigateTo('WRITING_DESK', project_id=project_id)
```

### 4. 删除项目

```python
def onDeleteProject(self, project_id):
    """删除项目"""
    reply = QMessageBox.question(
        self,
        "确认删除",
        "确定要删除此项目吗？此操作不可恢复！",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        try:
            self.api_client.delete_novels([project_id])
            QMessageBox.information(self, "成功", "项目已删除")
            self.loadProjects()  # 刷新列表
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除失败：{str(e)}")
```

## 禅意设计特点

### 1. 配色方案

```python
# 主色调
ACCENT_PRIMARY = "#9BAA99"      # 沉静灰绿
ACCENT_SECONDARY = "#B5C4B3"    # 浅灰绿
ACCENT_TERTIARY = "#7A8C78"     # 深灰绿

# 背景色
BG_CARD = "#FFFFFF"             # 卡片背景
BG_SECONDARY = "#F8F9F8"        # 次要背景
BG_TERTIARY = "#F0F2F0"         # 三级背景

# 文本色
TEXT_PRIMARY = "#2C3E2C"        # 主文本
TEXT_SECONDARY = "#6B7B6A"      # 次要文本
```

### 2. 圆角系统

```python
RADIUS_SM = "8px"   # 小圆角（按钮、标签）
RADIUS_MD = "12px"  # 中圆角（输入框）
RADIUS_LG = "24px"  # 大圆角（卡片）
```

### 3. 投影效果

```python
# 小投影（悬停前）
ZenTheme.get_shadow_effect("MD")
# → 0px 2px 8px rgba(0,0,0,0.1)

# 大投影（悬停后）
ZenTheme.get_shadow_effect("LG")
# → 0px 8px 24px rgba(0,0,0,0.15)
```

### 4. 渐变背景

```python
ZenTheme.background_gradient()
# → 温暖浅米白色渐变
```

## 网格布局

### 3列响应式网格

```python
# 网格计算
for idx, project in enumerate(projects):
    row = (idx + 1) // 3  # 行号
    col = (idx + 1) % 3   # 列号
    
    grid_layout.addWidget(card, row, col)
```

**示例布局**:
```
Row 0: [创建项目]  [项目1]     [项目2]
Row 1: [项目3]     [项目4]     [项目5]
Row 2: [项目6]     [项目7]     [项目8]
```

### 间距设置

```python
self.grid_layout.setSpacing(32)  # 32px 卡片间距
layout.setContentsMargins(48, 48, 48, 48)  # 页面边距
```

## 性能优化

### 1. 卡片动画优化

```python
# 使用 QEasingCurve.Type.OutCubic 缓动
self.opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

# 动画时长 350ms（流畅但不拖沓）
self.opacity_animation.setDuration(350)
```

### 2. 图片延迟加载

```python
# 使用emoji图标代替图片（📖）
icon_label = QLabel("📖")
icon_label.setStyleSheet("font-size: 28px;")
```

### 3. 滚动优化

```python
scroll_area = QScrollArea()
scroll_area.setWidgetResizable(True)
scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
```

## API集成

### API客户端使用

```python
self.api_client = ArborisAPIClient()

# 获取所有项目
response = self.api_client.get_all_novels()

# 删除项目
self.api_client.delete_novels([project_id])
```

## 最佳实践

### 1. 卡片数据校验

```python
# 安全获取嵌套数据
genre = self.project_data.get('blueprint', {}).get('genre', '未知类型')

# 处理空值
updated_at = self.project_data.get('updated_at', '')[:10] if self.project_data.get('updated_at') else '未知'
```

### 2. 进度计算保护

```python
# 避免除零错误
progress_percent = int((completed_chapters / total_chapters * 100) 
                       if total_chapters > 0 else 0)

# 进度条宽度保护
fill_width = max(int(bar_width * progress_percent / 100), 0)
```

### 3. 动画状态管理

```python
class ProjectCard(QFrame):
    def __init__(self):
        self.is_hovering = False  # 跟踪悬停状态
        
    def enterEvent(self, event):
        self.is_hovering = True
        # 启动动画
        
    def leaveEvent(self, event):
        self.is_hovering = False
        # 反向动画
```

## 用户体验优化

### 1. 加载状态

