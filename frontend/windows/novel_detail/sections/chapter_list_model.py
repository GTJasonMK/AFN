"""
章节列表虚拟化模型和代理

使用 QAbstractListModel + QStyledItemDelegate 实现高性能的列表渲染：
- Model: 只存储数据，不创建Widget
- Delegate: 直接绘制，避免创建大量Widget对象
- View: 只渲染可见区域的项目

性能优势：
- O(1) 内存使用（不随列表长度增长）
- 快速滚动（无Widget创建/销毁开销）
- 快速数据更新（增量更新而非全量重建）
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtCore import (
    Qt, QAbstractListModel, QModelIndex, QSize, QRect, QRectF
)
from PyQt6.QtWidgets import QStyledItemDelegate, QStyle, QApplication
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.formatters import format_word_count


# 自定义角色
class ChapterRoles:
    ChapterNumberRole = Qt.ItemDataRole.UserRole + 1
    TitleRole = Qt.ItemDataRole.UserRole + 2
    WordCountRole = Qt.ItemDataRole.UserRole + 3
    HasContentRole = Qt.ItemDataRole.UserRole + 4
    ChapterDataRole = Qt.ItemDataRole.UserRole + 5


class ChapterListModel(QAbstractListModel):
    """章节列表数据模型

    只存储数据引用，不创建任何Widget。
    支持增量更新，避免全量重建。
    """

    def __init__(self, chapters: List[Dict] = None, parent=None):
        super().__init__(parent)
        self._chapters: List[Dict] = chapters or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._chapters)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._chapters):
            return None

        chapter = self._chapters[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return chapter.get('title', f"第{chapter.get('chapter_number', index.row() + 1)}章")
        elif role == ChapterRoles.ChapterNumberRole:
            return chapter.get('chapter_number', index.row() + 1)
        elif role == ChapterRoles.TitleRole:
            return chapter.get('title', '')
        elif role == ChapterRoles.WordCountRole:
            return chapter.get('word_count', 0)
        elif role == ChapterRoles.HasContentRole:
            return bool(chapter.get('selected_version') or chapter.get('content'))
        elif role == ChapterRoles.ChapterDataRole:
            return chapter

        return None

    def setChapters(self, chapters: List[Dict]):
        """更新章节数据（增量更新优化）"""
        self.beginResetModel()
        self._chapters = chapters or []
        self.endResetModel()

    def getChapter(self, row: int) -> Optional[Dict]:
        """获取指定行的章节数据"""
        if 0 <= row < len(self._chapters):
            return self._chapters[row]
        return None

    def getChapterCount(self) -> int:
        """获取章节数量"""
        return len(self._chapters)


class ChapterItemDelegate(QStyledItemDelegate):
    """章节列表项绘制代理

    直接使用QPainter绘制，避免创建Widget。
    所有样式从theme_manager获取，支持主题切换。
    """

    # 缓存字体和颜色，避免重复创建
    _cached_fonts: Dict[str, QFont] = {}
    _cached_colors: Dict[str, QColor] = {}
    _cache_valid: bool = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._invalidate_cache()

    def _invalidate_cache(self):
        """失效样式缓存（主题切换时调用）"""
        ChapterItemDelegate._cache_valid = False
        ChapterItemDelegate._cached_fonts.clear()
        ChapterItemDelegate._cached_colors.clear()

    def _ensure_cache(self):
        """确保缓存有效"""
        if ChapterItemDelegate._cache_valid:
            return

        # 缓存字体
        ui_font_family = theme_manager.ui_font()

        title_font = QFont(ui_font_family)
        title_font.setPixelSize(sp(14))
        title_font.setWeight(QFont.Weight.Medium)
        ChapterItemDelegate._cached_fonts['title'] = title_font

        badge_font = QFont(ui_font_family)
        badge_font.setPixelSize(sp(12))
        badge_font.setWeight(QFont.Weight.Bold)
        ChapterItemDelegate._cached_fonts['badge'] = badge_font

        word_font = QFont(ui_font_family)
        word_font.setPixelSize(sp(11))
        ChapterItemDelegate._cached_fonts['word'] = word_font

        # 缓存颜色
        ChapterItemDelegate._cached_colors['text_primary'] = QColor(theme_manager.TEXT_PRIMARY)
        ChapterItemDelegate._cached_colors['text_tertiary'] = QColor(theme_manager.TEXT_TERTIARY)
        ChapterItemDelegate._cached_colors['success'] = QColor(theme_manager.SUCCESS)
        ChapterItemDelegate._cached_colors['button_text'] = QColor(theme_manager.BUTTON_TEXT)
        ChapterItemDelegate._cached_colors['bg_card'] = QColor(theme_manager.BG_CARD)
        ChapterItemDelegate._cached_colors['primary_pale'] = QColor(theme_manager.PRIMARY_PALE)
        ChapterItemDelegate._cached_colors['border_light'] = QColor(theme_manager.BORDER_LIGHT)

        ChapterItemDelegate._cache_valid = True

    def sizeHint(self, option, index: QModelIndex) -> QSize:
        """返回项目尺寸"""
        word_count = index.data(ChapterRoles.WordCountRole) or 0
        # 有字数时高度更大
        height = dp(60) if word_count > 0 else dp(48)
        return QSize(option.rect.width(), height)

    def paint(self, painter: QPainter, option, index: QModelIndex):
        """绘制列表项"""
        self._ensure_cache()

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = option.rect
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hover = option.state & QStyle.StateFlag.State_MouseOver

        # 绘制背景
        if is_selected:
            painter.fillRect(rect, self._cached_colors['primary_pale'])
        elif is_hover:
            painter.fillRect(rect, self._cached_colors['bg_card'])

        # 绘制底部边框
        painter.setPen(QPen(self._cached_colors['border_light'], 1))
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())

        # 获取数据
        chapter_num = index.data(ChapterRoles.ChapterNumberRole) or (index.row() + 1)
        title = index.data(ChapterRoles.TitleRole) or f"第{chapter_num}章"
        word_count = index.data(ChapterRoles.WordCountRole) or 0

        # 布局参数
        padding_h = dp(16)
        padding_v = dp(12)
        badge_size = dp(28)
        spacing = dp(10)

        # 绘制章节编号徽章
        badge_rect = QRect(
            rect.left() + padding_h,
            rect.top() + (rect.height() - badge_size) // 2 - (dp(8) if word_count > 0 else 0),
            badge_size,
            badge_size
        )
        painter.setBrush(QBrush(self._cached_colors['success']))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(badge_rect)

        # 绘制编号文字
        painter.setPen(self._cached_colors['button_text'])
        painter.setFont(self._cached_fonts['badge'])
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(chapter_num))

        # 绘制标题
        title_left = badge_rect.right() + spacing
        title_rect = QRect(
            title_left,
            badge_rect.top(),
            rect.width() - title_left - padding_h,
            badge_size
        )
        painter.setPen(self._cached_colors['text_primary'])
        painter.setFont(self._cached_fonts['title'])
        # 文字省略
        metrics = painter.fontMetrics()
        elided_title = metrics.elidedText(title, Qt.TextElideMode.ElideRight, title_rect.width())
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_title)

        # 绘制字数（如果有）
        if word_count > 0:
            word_rect = QRect(
                title_left,
                badge_rect.bottom() + dp(4),
                rect.width() - title_left - padding_h,
                dp(16)
            )
            painter.setPen(self._cached_colors['text_tertiary'])
            painter.setFont(self._cached_fonts['word'])
            painter.drawText(word_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, format_word_count(word_count))

        painter.restore()

    def refreshTheme(self):
        """刷新主题（主题切换时调用）"""
        self._invalidate_cache()


__all__ = [
    'ChapterListModel',
    'ChapterItemDelegate',
    'ChapterRoles',
]
