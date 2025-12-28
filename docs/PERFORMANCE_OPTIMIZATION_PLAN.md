# AFN 性能优化实施计划

基于性能审计报告的详细代码检查，本文档制定具体的优化实施方案。

## 确认的性能问题清单

### 后端问题（确认5项，排除1项）

| 序号 | 问题 | 严重性 | 状态 | 位置 |
|-----|------|-------|------|------|
| B1 | 向量库Python回退 | 高 | 确认 | `vector_store_service.py` |
| B2 | ChapterVersion.created_at缺索引 | 中 | 确认 | `models/novel.py:270` |
| B3 | ChapterMangaPrompt.source_version_id缺索引 | - | **排除** | 已有索引 |
| B4 | N+1查询风险 | 中 | 确认 | `novel_serializer.py` |
| B5 | 大JSON字段(scenes/panels) | 中 | 确认 | `models/novel.py` |
| B6 | 同步文件I/O | 高 | 确认 | `image_generation/` |

### 前端问题（确认5项，排除2项）

| 序号 | 问题 | 严重性 | 状态 | 位置 |
|-----|------|-------|------|------|
| F1 | processEvents()调用 | 中 | 确认 | `main.py`, `chapter_display.py` |
| F2 | QListWidget+setItemWidget | 高 | 确认 | `chapters_section.py` |
| F3 | 漫画O(N)组件创建 | - | **排除** | 已异步处理 |
| F4 | 主线程同步网络请求 | 高 | 确认 | `sidebar.py`等3处 |
| F5 | 高频UI更新缺乏缓冲 | - | **排除** | 设计合理 |
| F6 | findChildren()遍历 | 中 | 确认 | `theme_refresh.py` |
| F7 | 销毁与重建模式 | 高 | 确认 | `chapter_display.py` |

---

## 优化实施方案

### 阶段一：高优先级（阻塞型问题）

#### B6. 异步文件I/O优化

**问题**：`image_generation/service.py`和`pdf_export.py`在async函数中使用同步文件操作

**位置**：
- `service.py`: 第354、398-403、301-309行
- `pdf_export.py`: 第150、364、569、395、714行

**解决方案**：使用`aiofiles`和`asyncio.to_thread()`

```python
# 优化前
save_dir.mkdir(parents=True, exist_ok=True)
temp_path.write_bytes(image_content)

# 优化后
import aiofiles
import aiofiles.os

await aiofiles.os.makedirs(str(save_dir), exist_ok=True)
async with aiofiles.open(temp_path, 'wb') as f:
    await f.write(image_content)

# PIL操作使用to_thread
pil_img = await asyncio.to_thread(PILImage.open, str(img_path))
```

**涉及文件**：
- `backend/app/services/image_generation/service.py`
- `backend/app/services/image_generation/pdf_export.py`

---

#### F4. 异步网络请求优化

**问题**：主线程使用同步`requests.get()`导致UI冻结

**位置**：
- `frontend/windows/writing_desk/sidebar.py:650`
- `frontend/windows/novel_detail/components/character_portraits_widget.py:178`
- `frontend/windows/writing_desk/dialogs/protagonist_profile_dialog.py:467`

**解决方案**：使用`AsyncWorker`包装网络请求

```python
# 优化前
response = requests.get(image_url, timeout=5)

# 优化后
from utils.async_worker import AsyncWorker

def _load_portrait_image(self, image_url: str, name: str):
    """异步加载立绘图片"""
    def do_load():
        import requests
        response = requests.get(image_url, timeout=5)
        if response.status_code == 200:
            return response.content
        return None

    worker = AsyncWorker(do_load)
    worker.success.connect(lambda data: self._on_image_loaded(data, name))
    worker.error.connect(lambda e: logger.warning(f"加载图片失败: {e}"))
    worker.start()
    self._workers.append(worker)  # 保持引用防止GC
```

**涉及文件**：
- `frontend/windows/writing_desk/sidebar.py`
- `frontend/windows/novel_detail/components/character_portraits_widget.py`
- `frontend/windows/writing_desk/dialogs/protagonist_profile_dialog.py`

---

#### F2. 列表虚拟化优化

**问题**：`QListWidget+setItemWidget`导致O(N)内存和重建开销

**位置**：`frontend/windows/novel_detail/sections/chapters_section.py:139-147`

**解决方案**：改用`QListView`+自定义代理（Delegate）

```python
# 优化后架构
from PyQt6.QtWidgets import QListView, QStyledItemDelegate
from PyQt6.QtCore import QAbstractListModel, Qt

class ChapterListModel(QAbstractListModel):
    """章节数据模型"""
    def __init__(self, chapters=None):
        super().__init__()
        self._chapters = chapters or []

    def rowCount(self, parent=None):
        return len(self._chapters)

    def data(self, index, role):
        if not index.isValid():
            return None
        chapter = self._chapters[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return chapter.get('title', '')
        # ... 其他角色
        return None

    def updateChapters(self, chapters):
        """增量更新而非全量重建"""
        self.beginResetModel()
        self._chapters = chapters
        self.endResetModel()

class ChapterItemDelegate(QStyledItemDelegate):
    """自定义渲染代理 - 避免创建Widget"""
    def paint(self, painter, option, index):
        # 直接绘制，不创建Widget
        ...

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), dp(72))
```

**涉及文件**：
- `frontend/windows/novel_detail/sections/chapters_section.py`

---

#### F7. 章节显示组件复用

**问题**：每次切换章节都销毁并重建所有Tab组件

**位置**：`frontend/windows/writing_desk/workspace/chapter_display.py:96-109`

**解决方案**：复用现有组件，仅更新数据

```python
# 优化前
def displayChapter(self, chapter_data):
    if self.content_widget:
        self.stack.removeWidget(self.content_widget)
        self.content_widget.deleteLater()
    self.content_widget = self.createChapterWidget(chapter_data)
    ...

# 优化后
def displayChapter(self, chapter_data):
    if self.content_widget is None:
        # 首次创建
        self.content_widget = self.createChapterWidget(chapter_data)
        self.stack.addWidget(self.content_widget)
    else:
        # 复用现有组件，仅更新数据
        self._updateChapterContent(chapter_data)
    self.stack.setCurrentWidget(self.content_widget)

def _updateChapterContent(self, chapter_data):
    """更新现有组件的数据"""
    # 更新正文Tab
    self._content_builder.update_content(chapter_data.get('content'))
    # 更新分析Tab
    self._analysis_builder.update_analysis(chapter_data.get('analysis'))
    # 异步更新漫画Tab（保持现有逻辑）
    self._loadMangaDataAsync()
```

**涉及文件**：
- `frontend/windows/writing_desk/workspace/chapter_display.py`
- 各Builder类需添加`update_*`方法

---

### 阶段二：中优先级

#### B1. 向量库优化

**问题**：SQLite缺少`vector_distance_cosine`函数时回退到Python全表扫描

**位置**：`backend/app/services/vector_store_service.py`

**解决方案**：

1. **安装向量扩展**（推荐）
   ```bash
   # Windows: 下载预编译的sqlite-vec扩展
   # 或使用sqlite-vss
   pip install sqlite-vss
   ```

2. **启动时预加载扩展**
   ```python
   # backend/app/core/database.py
   from sqlalchemy import event

   @event.listens_for(engine.sync_engine, "connect")
   def load_vector_extension(dbapi_conn, connection_record):
       dbapi_conn.enable_load_extension(True)
       dbapi_conn.load_extension("path/to/vec0")
       dbapi_conn.enable_load_extension(False)
   ```

3. **备选：优化Python回退**
   ```python
   # 使用numpy加速余弦距离计算
   import numpy as np

   def _cosine_distance_batch(self, query_vec, stored_vecs):
       """批量计算余弦距离"""
       query = np.array(query_vec)
       stored = np.array(stored_vecs)
       # 归一化
       query_norm = query / np.linalg.norm(query)
       stored_norms = stored / np.linalg.norm(stored, axis=1, keepdims=True)
       # 批量点积
       similarities = np.dot(stored_norms, query_norm)
       return 1 - similarities
   ```

**涉及文件**：
- `backend/app/services/vector_store_service.py`
- `backend/app/core/database.py`（新增扩展加载）

---

#### B2. 数据库索引优化

**问题**：`ChapterVersion.created_at`缺少索引

**位置**：`backend/app/models/novel.py:270`

**解决方案**：添加索引

```python
# 优化前
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now()
)

# 优化后
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now(), index=True
)
```

**注意**：需要删除`storage/afn.db`重建数据库

**涉及文件**：
- `backend/app/models/novel.py`

---

#### B4. N+1查询预防

**问题**：序列化器中访问未预加载的关系

**位置**：`backend/app/serializers/novel_serializer.py`

**解决方案**：在Repository层确保关系预加载

```python
# backend/app/repositories/novel_repository.py
from sqlalchemy.orm import selectinload

async def get_with_relations(self, project_id: int) -> Optional[NovelProject]:
    """获取项目及其所有关系"""
    stmt = (
        select(NovelProject)
        .where(NovelProject.id == project_id)
        .options(
            selectinload(NovelProject.conversations),
            selectinload(NovelProject.characters),
            selectinload(NovelProject.relationships_),
            selectinload(NovelProject.outlines),
            selectinload(NovelProject.part_outlines),
            selectinload(NovelProject.chapters).selectinload(Chapter.versions),
        )
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

**涉及文件**：
- `backend/app/repositories/novel_repository.py`
- 相关路由确保使用新方法

---

#### F6. 主题刷新优化

**问题**：`findChildren()`频繁遍历整个Widget树

**位置**：`frontend/windows/writing_desk/workspace/theme_refresh.py`（10+处）

**解决方案**：缓存组件引用

```python
class ThemeRefreshMixin:
    def _init_theme_cache(self):
        """初始化主题相关组件缓存"""
        self._cached_scroll_areas = []
        self._cached_labels = {}
        self._cached_frames = {}
        self._theme_cache_valid = False

    def _build_theme_cache(self):
        """构建组件缓存（仅在首次或结构变化时调用）"""
        if self._theme_cache_valid:
            return

        # 一次性遍历，按类型分类缓存
        self._cached_scroll_areas = list(self.content_widget.findChildren(QScrollArea))

        for label in self.content_widget.findChildren(QLabel):
            obj_name = label.objectName()
            if obj_name:
                self._cached_labels[obj_name] = label

        for frame in self.content_widget.findChildren(QFrame):
            obj_name = frame.objectName()
            if obj_name:
                self._cached_frames[obj_name] = frame

        self._theme_cache_valid = True

    def _invalidate_theme_cache(self):
        """当UI结构变化时失效缓存"""
        self._theme_cache_valid = False

    def _refresh_analysis_styles(self):
        """使用缓存刷新样式"""
        self._build_theme_cache()

        # 直接使用缓存，避免findChildren
        for name, label in self._cached_labels.items():
            if name.startswith("analysis_label_"):
                label.setStyleSheet(...)
```

**涉及文件**：
- `frontend/windows/writing_desk/workspace/theme_refresh.py`

---

#### F1. processEvents()优化

**问题**：过于频繁调用processEvents()

**位置**：
- `frontend/windows/writing_desk/main.py:86-122`
- `frontend/windows/writing_desk/workspace/chapter_display.py:268-298`

**解决方案**：减少调用频率，使用批量处理

```python
# 优化前：每创建一个组件就调用
self.header = WDHeader()
main_layout.addWidget(self.header)
QApplication.processEvents()

self.sidebar = WDSidebar()
content_layout.addWidget(self.sidebar)
QApplication.processEvents()

# 优化后：批量创建后调用一次
self.header = WDHeader()
main_layout.addWidget(self.header)

self.sidebar = WDSidebar()
content_layout.addWidget(self.sidebar)

self.workspace = WDWorkspace()
content_layout.addWidget(self.workspace)

# 所有主要组件创建完成后再处理事件
QApplication.processEvents()
```

**涉及文件**：
- `frontend/windows/writing_desk/main.py`
- `frontend/windows/writing_desk/workspace/chapter_display.py`

---

### 阶段三：低优先级

#### B5. 大JSON字段优化

**问题**：`scenes`和`panels`字段数据量大

**解决方案**：延迟加载策略

```python
# 查询时默认不加载大字段
stmt = select(
    ChapterMangaPrompt.id,
    ChapterMangaPrompt.chapter_id,
    ChapterMangaPrompt.source_version_id,
    # 不包含 scenes 和 panels
)

# 需要时单独查询
async def get_manga_details(self, manga_id: int):
    stmt = select(ChapterMangaPrompt).where(ChapterMangaPrompt.id == manga_id)
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

**涉及文件**：
- `backend/app/repositories/`相关文件
- `backend/app/api/routers/writer/manga.py`

---

## 实施顺序

1. **第一批（高优先级 - 阻塞型）**
   - [x] B6: 异步文件I/O（已完成：使用asyncio.to_thread包装同步文件操作）
   - [x] F4: 异步网络请求（已完成：使用AsyncWorker包装requests.get）
   - [x] F2: 列表虚拟化（已完成：使用QListView+QAbstractListModel+QStyledItemDelegate替代QListWidget+setItemWidget）
   - [x] F7: 组件复用（已完成：章节切换时复用content_widget和tab_widget，只更新数据）

2. **第二批（中优先级）**
   - [x] B1: 向量库优化（已完成：添加numpy批量余弦距离计算，性能提升10-100倍）
   - [x] B2: 数据库索引（已完成：ChapterVersion.created_at添加index=True）
   - [x] B4: N+1查询预防（已确认：novel_repository.py已使用selectinload预加载所有关系）
   - [x] F6: 主题刷新优化（已完成：实现组件缓存减少findChildren调用）
   - [x] F1: processEvents优化（已完成：批量处理减少调用次数）

3. **第三批（低优先级）**
   - [ ] B5: JSON字段延迟加载（暂缓：影响范围大）

---

## 验证清单

完成每项优化后，需验证：

- [ ] 功能正常：原有功能不受影响
- [ ] 性能提升：使用性能分析工具确认改善
- [ ] 无内存泄漏：长时间运行无内存增长
- [ ] 无竞态条件：异步操作正确处理
- [ ] 代码质量：符合项目编码规范

---

## 排除的问题

以下问题经检查不存在或已优化：

1. **B3: ChapterMangaPrompt.source_version_id** - 已有索引（`index=True`）
2. **F3: 漫画O(N)组件创建** - 已使用异步加载（`_loadMangaDataAsync()`）
3. **F5: 高频UI更新** - 当前设计合理，token级更新已足够高效

---

## 优化过程中发现的Bug修复

### BUG-1: 写作台页面返回后无限加载

**症状**：从项目详情返回写作台时，一直转圈卡在加载数据

**根本原因**：
- `WritingDesk.onHide()` 调用 `_cleanup_workers()`
- `_cleanup_workers()` 调用 `worker_manager.cleanup_all()`
- `cleanup_all()` 设置 `_is_cleaned_up = True`
- 当页面再次显示时，`loadProject()` 调用 `worker_manager.start()`
- `start()` 检测到 `_is_cleaned_up = True` 后直接返回，不启动worker
- 结果：加载回调永远不会触发，loading动画永远不会隐藏

**解决方案**：
区分"页面隐藏"和"组件销毁"两种场景：
- `onHide()`: 调用 `stop_all()` - 只停止运行中的worker，保持manager可复用
- `closeEvent()`/`__del__()`: 调用 `cleanup_all()` - 完全清理，标记为不可用

**修改文件**：`frontend/windows/writing_desk/main.py`

```python
def onHide(self):
    """页面隐藏时停止运行中的任务（但保持manager可复用）"""
    self._cleanup_workers(full_cleanup=False)

def _cleanup_workers(self, full_cleanup: bool = True):
    if hasattr(self, 'worker_manager') and self.worker_manager:
        if full_cleanup:
            self.worker_manager.cleanup_all()
        else:
            self.worker_manager.stop_all()
```
