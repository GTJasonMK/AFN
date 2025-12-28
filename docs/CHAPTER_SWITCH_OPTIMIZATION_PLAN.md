# 章节切换性能优化方案

## 一、当前流程分析

```
用户点击章节卡片
    ↓
sidebar._on_chapter_card_clicked()
    ↓ 更新视觉选中状态
    ↓ emit chapterSelected 信号
    ↓
main.onChapterSelected()
    ↓
workspace.loadChapter(chapter_number)
    ↓ 50ms 节流延迟
    ↓ 显示加载动画
    ↓
_do_load_chapter()
    ↓ API调用: GET /api/novels/{id}/chapters/{num}
    ↓ 等待网络响应（主要延迟来源）
    ↓
_onChapterLoaded()
    ↓ 隐藏加载动画
    ↓
displayChapter()
    ↓ 更新标题、元信息
    ↓ 更新正文Tab
    ↓ 分批更新其他Tab（8ms间隔）
    ↓ 漫画Tab异步加载
    ↓ 失效主题缓存
```

## 二、性能瓶颈识别

| 瓶颈 | 影响程度 | 说明 |
|------|---------|------|
| **无章节数据缓存** | 高 | 每次切换都发起API请求，即使刚访问过 |
| **API网络延迟** | 高 | 数据库查询 + HTTP往返，通常50-200ms |
| **Tab组件重建** | 中 | 版本/评审/摘要/分析Tab每次重建 |
| **正文渲染** | 中 | 长章节（>5000字）设置文本较慢 |
| **主题缓存失效** | 低 | 每次切换都重建主题缓存 |

## 三、优化方案

### 方案1: LRU章节数据缓存（优先级：高）

在客户端缓存最近访问的章节数据，避免重复API调用。

```python
# frontend/utils/chapter_cache.py

from collections import OrderedDict
from typing import Optional, Dict, Any
from dataclasses import dataclass
from time import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """缓存条目"""
    data: Dict[str, Any]
    timestamp: float
    version_hash: str  # 用于检测数据是否过期


class ChapterCache:
    """章节数据LRU缓存

    特性：
    - LRU淘汰策略：超出容量时移除最久未访问的
    - 时间过期：超过TTL的数据视为过期
    - 版本校验：检测数据变更
    - 线程安全：使用锁保护

    用法：
        cache = ChapterCache(max_size=20, ttl=300)  # 20章，5分钟过期

        # 获取（命中返回数据，未命中返回None）
        chapter = cache.get(project_id, chapter_number)

        # 存入
        cache.set(project_id, chapter_number, chapter_data)

        # 预取
        cache.prefetch(project_id, [1, 2, 3], fetch_func)

        # 失效
        cache.invalidate(project_id, chapter_number)
    """

    def __init__(self, max_size: int = 20, ttl: float = 300.0):
        """
        Args:
            max_size: 最大缓存章节数
            ttl: 过期时间（秒），默认5分钟
        """
        self._max_size = max_size
        self._ttl = ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = __import__('threading').RLock()

        # 统计
        self._hits = 0
        self._misses = 0

    def _make_key(self, project_id: str, chapter_number: int) -> str:
        """生成缓存键"""
        return f"{project_id}:{chapter_number}"

    def _compute_version_hash(self, data: Dict[str, Any]) -> str:
        """计算数据版本哈希（用于检测变更）"""
        # 使用关键字段生成简单哈希
        content = data.get('content', '')
        versions = data.get('versions', [])
        selected = data.get('selected_version')
        return f"{len(content)}:{len(versions)}:{selected}"

    def get(self, project_id: str, chapter_number: int) -> Optional[Dict[str, Any]]:
        """获取缓存的章节数据

        Returns:
            章节数据，未命中或已过期返回None
        """
        key = self._make_key(project_id, chapter_number)

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if time() - entry.timestamp > self._ttl:
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Chapter cache expired: {key}")
                return None

            # 移到末尾（最近访问）
            self._cache.move_to_end(key)
            self._hits += 1
            logger.debug(f"Chapter cache hit: {key}")
            return entry.data

    def set(self, project_id: str, chapter_number: int, data: Dict[str, Any]):
        """存入章节数据"""
        key = self._make_key(project_id, chapter_number)

        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                del self._cache[key]

            # 添加新条目
            self._cache[key] = CacheEntry(
                data=data,
                timestamp=time(),
                version_hash=self._compute_version_hash(data)
            )

            # LRU淘汰
            while len(self._cache) > self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"Chapter cache evicted: {oldest_key}")

    def invalidate(self, project_id: str, chapter_number: int = None):
        """失效缓存

        Args:
            project_id: 项目ID
            chapter_number: 章节号，为None时失效该项目所有章节
        """
        with self._lock:
            if chapter_number is not None:
                key = self._make_key(project_id, chapter_number)
                if key in self._cache:
                    del self._cache[key]
            else:
                # 失效该项目所有章节
                keys_to_remove = [
                    k for k in self._cache.keys()
                    if k.startswith(f"{project_id}:")
                ]
                for key in keys_to_remove:
                    del self._cache[key]

    def invalidate_all(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()

    def prefetch_adjacent(
        self,
        project_id: str,
        current_chapter: int,
        total_chapters: int,
        fetch_func
    ):
        """预取相邻章节（后台执行）

        Args:
            project_id: 项目ID
            current_chapter: 当前章节号
            total_chapters: 总章节数
            fetch_func: 获取章节的函数 (project_id, chapter_number) -> data
        """
        from concurrent.futures import ThreadPoolExecutor

        # 计算要预取的章节（前后各1章）
        to_prefetch = []
        if current_chapter > 1:
            to_prefetch.append(current_chapter - 1)
        if current_chapter < total_chapters:
            to_prefetch.append(current_chapter + 1)

        # 过滤已缓存的
        to_prefetch = [
            ch for ch in to_prefetch
            if self.get(project_id, ch) is None
        ]

        if not to_prefetch:
            return

        def do_prefetch(chapter_num):
            try:
                data = fetch_func(project_id, chapter_num)
                self.set(project_id, chapter_num, data)
                logger.debug(f"Prefetched chapter {chapter_num}")
            except Exception as e:
                logger.warning(f"Prefetch failed for chapter {chapter_num}: {e}")

        # 使用线程池后台预取
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(do_prefetch, to_prefetch)

    @property
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1%}"
        }


# 全局单例
_chapter_cache: Optional[ChapterCache] = None


def get_chapter_cache() -> ChapterCache:
    """获取全局章节缓存实例"""
    global _chapter_cache
    if _chapter_cache is None:
        _chapter_cache = ChapterCache(max_size=20, ttl=300)
    return _chapter_cache
```

### 方案2: 悬停预加载（优先级：高）

当鼠标悬停在章节卡片上时，提前加载该章节数据。

```python
# 在 ChapterCard 中添加悬停预加载

class ChapterCard(QFrame):
    # 新增信号
    hoverEntered = pyqtSignal(int)  # 鼠标进入，参数为章节号

    def __init__(self, ...):
        ...
        # 悬停预加载定时器
        self._hover_timer = None
        self._hover_delay = 300  # 悬停300ms后触发预加载

    def enterEvent(self, event):
        """鼠标进入"""
        super().enterEvent(event)
        # 延迟发射悬停信号，避免快速滑过时触发
        if self._hover_timer is None:
            self._hover_timer = QTimer()
            self._hover_timer.setSingleShot(True)
            self._hover_timer.timeout.connect(self._emit_hover)
        self._hover_timer.start(self._hover_delay)

    def leaveEvent(self, event):
        """鼠标离开"""
        super().leaveEvent(event)
        if self._hover_timer:
            self._hover_timer.stop()

    def _emit_hover(self):
        chapter_number = self.chapter_data.get('chapter_number')
        if chapter_number:
            self.hoverEntered.emit(chapter_number)


# 在 Sidebar 中处理悬停预加载
class WritingDeskSidebar(ThemeAwareWidget):

    def _on_chapter_hover(self, chapter_number):
        """章节卡片悬停 - 预加载数据"""
        from utils.chapter_cache import get_chapter_cache

        cache = get_chapter_cache()
        # 如果未缓存，触发后台预加载
        if cache.get(self.project_id, chapter_number) is None:
            self._prefetch_chapter(chapter_number)

    def _prefetch_chapter(self, chapter_number):
        """后台预取章节"""
        from utils.async_worker import AsyncAPIWorker

        worker = AsyncAPIWorker(
            self.api_client.get_chapter,
            self.project_id,
            chapter_number
        )
        worker.success.connect(
            lambda data: get_chapter_cache().set(
                self.project_id, chapter_number, data
            )
        )
        # 不处理错误，预取失败静默忽略
        worker.start()
```

### 方案3: 集成缓存到加载流程（优先级：高）

修改 `loadChapter` 方法，优先从缓存获取。

```python
# 在 ChapterDisplayMixin 中修改

def loadChapter(self, chapter_number):
    """异步加载章节（带缓存）"""
    from PyQt6.QtCore import QTimer
    from utils.chapter_cache import get_chapter_cache

    # 如果请求的是当前已加载的章节，直接返回
    if hasattr(self, '_last_loaded_chapter') and self._last_loaded_chapter == chapter_number:
        return

    self._pending_load_chapter = chapter_number
    self.current_chapter = chapter_number

    if not self.project_id:
        return

    # 优先从缓存获取
    cache = get_chapter_cache()
    cached_data = cache.get(self.project_id, chapter_number)

    if cached_data:
        # 缓存命中，直接显示（无需加载动画）
        self._last_loaded_chapter = chapter_number
        self.displayChapter(cached_data)

        # 后台预取相邻章节
        total = len(self.project.get('chapters', []))
        cache.prefetch_adjacent(
            self.project_id, chapter_number, total,
            self.api_client.get_chapter
        )
        return

    # 缓存未命中，走原有的异步加载流程
    self._cancel_chapter_load_worker()
    self._ensure_loading_overlay()
    self._chapter_loading_overlay.show_with_animation("正在加载章节...")

    # 使用节流定时器
    if not hasattr(self, '_load_chapter_timer') or self._load_chapter_timer is None:
        self._load_chapter_timer = QTimer()
        self._load_chapter_timer.setSingleShot(True)
        self._load_chapter_timer.timeout.connect(self._on_throttle_timeout)
    else:
        self._load_chapter_timer.stop()

    self._load_chapter_timer.start(50)


def _onChapterLoaded(self, chapter_data):
    """章节数据加载成功回调"""
    from utils.chapter_cache import get_chapter_cache

    loaded_chapter = chapter_data.get('chapter_number')
    pending_chapter = getattr(self, '_pending_load_chapter', None)

    if pending_chapter is not None and loaded_chapter != pending_chapter:
        return

    # 存入缓存
    cache = get_chapter_cache()
    cache.set(self.project_id, loaded_chapter, chapter_data)

    self._last_loaded_chapter = loaded_chapter

    if hasattr(self, '_chapter_loading_overlay') and self._chapter_loading_overlay:
        self._chapter_loading_overlay.hide_with_animation()

    self.displayChapter(chapter_data)

    # 后台预取相邻章节
    total = len(self.project.get('chapters', []))
    cache.prefetch_adjacent(
        self.project_id, loaded_chapter, total,
        self.api_client.get_chapter
    )
```

### 方案4: 懒加载Tab内容（优先级：中）

只在用户点击Tab时才加载其内容。

```python
# 在 WorkspaceCore 中添加懒加载支持

class LazyTabWidget(QTabWidget):
    """懒加载Tab组件

    只在Tab被激活时才加载其内容，减少初始渲染开销。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab_loaders = {}  # tab_index -> loader_func
        self._tab_loaded = set()  # 已加载的tab索引
        self.currentChanged.connect(self._on_tab_changed)

    def addLazyTab(self, placeholder: QWidget, title: str, loader_func):
        """添加懒加载Tab

        Args:
            placeholder: 占位Widget（显示加载中提示）
            title: Tab标题
            loader_func: 加载函数，返回实际的Tab Widget
        """
        index = self.addTab(placeholder, title)
        self._tab_loaders[index] = loader_func
        return index

    def _on_tab_changed(self, index):
        """Tab切换时加载内容"""
        if index in self._tab_loaders and index not in self._tab_loaded:
            loader = self._tab_loaders[index]
            try:
                actual_widget = loader()
                self.removeTab(index)
                self.insertTab(index, actual_widget, self.tabText(index))
                self.setCurrentIndex(index)
                self._tab_loaded.add(index)
            except Exception as e:
                logger.error(f"Failed to load tab {index}: {e}")

    def invalidate_tab(self, index):
        """标记Tab需要重新加载"""
        self._tab_loaded.discard(index)
```

### 方案5: 禁用UI更新优化（优先级：中）

在批量更新时禁用UI重绘。

```python
def _updateChapterContent(self, chapter_data):
    """更新现有组件的数据 - 优化版"""

    # 禁用UI更新，批量操作完成后统一重绘
    self.setUpdatesEnabled(False)

    try:
        # 1. 更新章节标题
        if self.chapter_title:
            title = chapter_data.get('title', f"第{chapter_data.get('chapter_number', '')}章")
            self.chapter_title.setText(title)

        # 2. 更新元信息
        ...

        # 3. 更新正文
        content = chapter_data.get('content') or ''
        if content:
            self._content_builder.set_content(content)

        # 4. 同步更新所有Tab（不再分批）
        # 由于禁用了UI更新，同步更新不会造成卡顿
        self._update_all_tabs_sync(chapter_data)

    finally:
        # 恢复UI更新，触发一次重绘
        self.setUpdatesEnabled(True)
        self.repaint()
```

## 四、实施计划

### 阶段1: 缓存层（预计收益：50%响应时间减少）
1. 实现 `ChapterCache` 类
2. 集成到 `loadChapter` 流程
3. 添加缓存失效逻辑（章节内容修改时）

### 阶段2: 预加载（预计收益：30%等待时间减少）
1. 添加悬停预加载
2. 添加相邻章节预取
3. 优化预取策略（根据阅读方向）

### 阶段3: UI优化（预计收益：20%渲染时间减少）
1. 实现懒加载Tab
2. 使用 `setUpdatesEnabled` 批量更新
3. 优化长文本渲染

## 五、缓存失效策略

在以下场景需要失效缓存：

1. **章节内容修改**：`onSaveContent` 后失效当前章节
2. **版本选择**：`onSelectVersion` 后失效当前章节
3. **章节生成**：生成完成后失效当前章节
4. **项目切换**：切换项目时清空所有缓存
5. **手动刷新**：用户点击刷新按钮时失效

```python
# 在相关方法中添加缓存失效
def onSaveContent(self, chapter_number, content):
    ...
    # 保存成功后失效缓存
    get_chapter_cache().invalidate(self.project_id, chapter_number)

def onSelectVersion(self, chapter_number, version_id):
    ...
    # 选择版本后失效缓存
    get_chapter_cache().invalidate(self.project_id, chapter_number)

def setProject(self, project):
    ...
    # 切换项目时清空缓存
    get_chapter_cache().invalidate_all()
```

## 六、预期效果

| 场景 | 当前耗时 | 优化后耗时 | 提升 |
|------|---------|-----------|------|
| 首次访问章节 | 200-500ms | 200-500ms | - |
| 再次访问同一章节 | 200-500ms | <50ms | 90%+ |
| 访问相邻章节（预取命中）| 200-500ms | <50ms | 90%+ |
| 悬停预加载命中 | 200-500ms | <50ms | 90%+ |

## 七、监控指标

```python
# 添加性能监控
def log_chapter_switch_metrics():
    cache = get_chapter_cache()
    stats = cache.stats
    logger.info(
        f"Chapter cache stats: "
        f"size={stats['size']}/{stats['max_size']}, "
        f"hit_rate={stats['hit_rate']}"
    )
```
