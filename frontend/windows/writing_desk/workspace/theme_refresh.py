"""
写作台主工作区 - 主题刷新 Mixin

包含所有主题样式刷新相关的方法。
优化：使用组件缓存减少findChildren调用。
"""

from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QFrame, QLabel, QPushButton, QTextEdit, QScrollArea, QTabWidget,
    QGraphicsDropShadowEffect, QWidget
)
from PyQt6.QtGui import QColor

from themes.theme_manager import theme_manager
from themes.modern_effects import ModernEffects
from themes.button_styles import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.constants import VersionConstants


class ThemeRefreshMixin:
    """主题刷新相关方法的 Mixin

    优化策略：
    - 使用组件缓存减少findChildren遍历
    - 首次刷新时构建缓存，后续刷新复用
    - 内容变化时失效缓存
    """

    # 缓存属性（子类需要初始化）
    _theme_cache_valid: bool = False
    _cached_scroll_areas: List[QScrollArea] = None
    _cached_tab_widgets: List[QTabWidget] = None
    _cached_labels_by_prefix: Dict[str, List[QLabel]] = None
    _cached_frames_by_prefix: Dict[str, List[QFrame]] = None
    # 常用组件直接引用缓存（避免反复findChild）
    _cached_components: Dict[str, QWidget] = None

    def _init_theme_cache(self):
        """初始化主题缓存（在子类__init__中调用）"""
        self._theme_cache_valid = False
        self._cached_scroll_areas = []
        self._cached_tab_widgets = []
        self._cached_labels_by_prefix = {}
        self._cached_frames_by_prefix = {}
        self._cached_components = {}

    def _invalidate_theme_cache(self):
        """失效主题缓存（内容变化时调用）"""
        self._theme_cache_valid = False

    def _build_theme_cache(self):
        """构建组件缓存（一次遍历，分类存储）

        性能优化：
        - 一次遍历收集所有组件，避免多次 findChild/findChildren 调用
        - 按objectName缓存常用组件，后续直接访问
        """
        if self._theme_cache_valid:
            return

        if not hasattr(self, 'content_widget') or not self.content_widget:
            return

        # 初始化缓存容器
        self._cached_scroll_areas = []
        self._cached_tab_widgets = []
        self._cached_labels_by_prefix = {
            "analysis_label_": [],
            "analysis_text_": [],
            "analysis_highlight_": [],
            "other": [],
        }
        self._cached_frames_by_prefix = {
            "char_state_card_": [],
            "event_card_": [],
            "foreshadow_card_": [],
            "version_card_": [],
            "version_info_bar_": [],
            "eval_card_": [],
            "other": [],
        }
        self._cached_components = {}

        # 常用组件的objectName列表（用于直接缓存）
        common_component_names = {
            "chapter_header", "chapter_meta_label", "editor_container",
            "content_toolbar", "word_count_label", "status_label",
            "save_btn", "rag_btn", "summary_info_card", "summary_info_title",
            "summary_info_desc", "summary_content_card", "summary_text_edit",
            "summary_word_count", "analysis_scroll_area", "analysis_info_card",
            "analysis_info_title", "analysis_info_desc", "recommendation_card",
            "reeval_btn", "evaluate_btn"
        }

        # 一次遍历收集所有需要的组件
        for child in self.content_widget.findChildren(QWidget):
            obj_name = child.objectName()

            # 缓存常用组件
            if obj_name in common_component_names:
                self._cached_components[obj_name] = child

            if isinstance(child, QScrollArea):
                self._cached_scroll_areas.append(child)
            elif isinstance(child, QTabWidget):
                self._cached_tab_widgets.append(child)
            elif isinstance(child, QLabel):
                # 按前缀分类
                matched = False
                for prefix in ["analysis_label_", "analysis_text_", "analysis_highlight_"]:
                    if obj_name.startswith(prefix):
                        self._cached_labels_by_prefix[prefix].append(child)
                        matched = True
                        break
                if not matched:
                    self._cached_labels_by_prefix["other"].append(child)
            elif isinstance(child, QFrame):
                # 按前缀分类
                matched = False
                for prefix in ["char_state_card_", "event_card_", "foreshadow_card_",
                              "version_card_", "version_info_bar_", "eval_card_"]:
                    if obj_name.startswith(prefix):
                        self._cached_frames_by_prefix[prefix].append(child)
                        matched = True
                        break
                if not matched:
                    self._cached_frames_by_prefix["other"].append(child)

        self._theme_cache_valid = True

    def _get_cached_component(self, name: str, widget_type=None):
        """从缓存获取组件，如果不存在则使用findChild（兼容回退）"""
        if self._theme_cache_valid and self._cached_components and name in self._cached_components:
            return self._cached_components[name]
        # 回退到findChild
        if self.content_widget:
            return self.content_widget.findChild(widget_type or QWidget, name)
        return None

    def _apply_theme(self):
        """应用主题样式（可多次调用）

        优化：不重建章节内容，只更新样式。
        重建会触发 API 调用（漫画数据、图片等），导致性能问题。
        但漫画Tab由于结构复杂，需要重建以应用新主题。
        """
        # 刷新样式器的缓存值
        self._styler.refresh()

        # 刷新所有 Panel Builders 的样式器缓存
        # 这样在重建章节内容时，Panel Builders 会使用新主题的颜色
        self._analysis_builder.refresh_theme()
        self._version_builder.refresh_theme()
        self._review_builder.refresh_theme()
        self._summary_builder.refresh_theme()
        self._content_builder.refresh_theme()
        self._manga_builder.refresh_theme()

        # 注意：不使用Python类名选择器，Qt不识别Python类名
        # 直接设置透明背景
        self.setStyleSheet("background-color: transparent;")

        # 构建组件缓存（仅在缓存失效时重建）
        self._build_theme_cache()

        # 如果有显示中的章节内容，只更新样式，不重建
        # 重建会触发 _loadMangaDataAsync 等 API 调用，导致性能问题
        if self.current_chapter_data:
            # 保存当前tab索引
            current_tab_index = self.tab_widget.currentIndex() if self.tab_widget else 0

            # 只刷新样式，不重建
            self._refresh_content_styles()

            # 漫画Tab需要重建以应用新主题（结构复杂，无法增量刷新）
            # 使用已缓存的漫画数据重建，不重新调用API
            self._refresh_manga_tab_theme()

            # 恢复tab索引（样式刷新不会改变tab数量，但以防万一）
            if self.tab_widget and current_tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(current_tab_index)

    def _refresh_content_styles(self):
        """刷新内容区域的主题样式（主题切换时调用） - 书香风格

        性能优化：使用缓存组件引用，减少findChild调用
        """
        if not self.content_widget:
            return

        # 使用缓存的样式器属性（避免重复调用theme_manager）
        s = self._styler

        # 渐变背景的动态覆盖色
        # 亮色主题：渐变是深色赭石色，覆盖层使用白色
        # 深色主题：渐变是亮色琥珀色，覆盖层使用深色
        is_dark = theme_manager.is_dark_mode()
        overlay_rgb = "0, 0, 0" if is_dark else "255, 255, 255"

        # 更新章节标题卡片 - 渐变背景设计
        if chapter_header := self._get_cached_component("chapter_header", QFrame):
            # 重新应用渐变背景
            gradient = ModernEffects.linear_gradient(
                theme_manager.PRIMARY_GRADIENT,
                135
            )
            chapter_header.setStyleSheet(f"""
                QFrame#chapter_header {{
                    background: {gradient};
                    border: none;
                    border-radius: {theme_manager.RADIUS_MD};
                    padding: {dp(12)}px;
                }}
            """)
            # 重新添加阴影效果
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(dp(12))
            shadow.setColor(QColor(0, 0, 0, 30))
            shadow.setOffset(0, dp(2))
            chapter_header.setGraphicsEffect(shadow)

        # 更新章节标题文字 - 渐变背景上使用白色文字
        if self.chapter_title:
            self.chapter_title.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(18)}px;
                font-weight: 700;
                color: {theme_manager.BUTTON_TEXT};
            """)

        # 更新章节元信息标签 - 渐变背景上使用白色文字
        if meta_label := self._get_cached_component("chapter_meta_label", QLabel):
            meta_label.setStyleSheet(f"""
                font-family: {s.serif_font};
                font-size: {sp(12)}px;
                color: {theme_manager.BUTTON_TEXT};
                opacity: 0.85;
            """)

        # 更新预览按钮 - 渐变背景上的透明按钮
        if self.preview_btn:
            self.preview_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {s.serif_font};
                    background-color: transparent;
                    color: {theme_manager.BUTTON_TEXT};
                    border: 1px solid rgba({overlay_rgb}, 0.3);
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(12)}px;
                    font-size: {sp(12)}px;
                }}
                QPushButton:hover {{
                    background-color: rgba({overlay_rgb}, 0.15);
                    border-color: rgba({overlay_rgb}, 0.5);
                }}
                QPushButton:pressed {{
                    background-color: rgba({overlay_rgb}, 0.1);
                }}
            """)

        # 更新生成按钮 - 渐变背景上的半透明按钮
        if self.generate_btn:
            self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    font-family: {s.serif_font};
                    background-color: rgba({overlay_rgb}, 0.2);
                    color: {theme_manager.BUTTON_TEXT};
                    border: 1px solid rgba({overlay_rgb}, 0.3);
                    border-radius: {dp(6)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-size: {sp(13)}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: rgba({overlay_rgb}, 0.3);
                    border-color: rgba({overlay_rgb}, 0.5);
                }}
                QPushButton:pressed {{
                    background-color: rgba({overlay_rgb}, 0.15);
                }}
            """)

        # 更新TabWidget
        if self.tab_widget:
            self.tab_widget.setStyleSheet(f"""
                QTabWidget::pane {{
                    border: none;
                    background: transparent;
                }}
                QTabBar::tab {{
                    background: transparent;
                    color: {s.text_secondary};
                    padding: {dp(8)}px {dp(16)}px;
                    font-family: {s.ui_font};
                    border-bottom: 2px solid transparent;
                }}
                QTabBar::tab:selected {{
                    color: {s.accent_color};
                    border-bottom: 2px solid {s.accent_color};
                    font-weight: bold;
                }}
                QTabBar::tab:hover {{
                    color: {s.text_primary};
                }}
            """)

        # 更新文本编辑器 - 与创建时保持一致
        if self.content_text:
            self.content_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {s.bg_card};
                    border: none;
                    padding: {dp(16)}px;
                    font-family: {s.serif_font};
                    font-size: {sp(15)}px;
                    color: {s.text_primary};
                    line-height: 1.8;
                    selection-background-color: {s.accent_color};
                    selection-color: {s.button_text};
                }}
                {s.scrollbar_style()}
            """)

        # 更新编辑器容器 - 与创建时保持一致
        if editor_container := self._get_cached_component("editor_container", QFrame):
            editor_container.setStyleSheet(f"""
                QFrame#editor_container {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(8)}px;
                    padding: {dp(2)}px;
                }}
            """)

        # 更新工具栏样式 - 与创建时保持一致
        if toolbar := self._get_cached_component("content_toolbar", QFrame):
            toolbar.setStyleSheet(f"""
                QFrame#content_toolbar {{
                    background-color: {s.bg_card};
                    border: 1px solid {s.border_light};
                    border-radius: {dp(8)}px;
                    padding: {dp(6)}px {dp(10)}px;
                }}
            """)

        # 更新字数统计标签
        if word_count_label := self._get_cached_component("word_count_label", QLabel):
            word_count_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                color: {s.text_secondary};
            """)

        # 更新状态标签
        if status_label := self._get_cached_component("status_label", QLabel):
            status_label.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(13)}px;
                color: {s.accent_color};
            """)

        # 更新保存按钮 - 使用 ButtonStyles.primary
        if save_btn := self._get_cached_component("save_btn", QPushButton):
            save_btn.setStyleSheet(ButtonStyles.primary('SM'))

        # 更新RAG入库按钮 - 使用 ButtonStyles.secondary
        if rag_btn := self._get_cached_component("rag_btn", QPushButton):
            rag_btn.setStyleSheet(ButtonStyles.secondary('SM'))

        # 更新滚动区域的样式（使用缓存）
        scroll_areas = self._cached_scroll_areas if self._theme_cache_valid else self.content_widget.findChildren(QScrollArea)
        for scroll_area in scroll_areas:
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    border: none;
                    background-color: transparent;
                }}
                {s.scrollbar_style()}
            """)
            # 设置viewport透明背景
            if scroll_area.viewport():
                scroll_area.viewport().setStyleSheet("background-color: transparent;")

        # 更新版本卡片样式
        self._refresh_version_cards_styles()

        # 更新评审卡片样式
        self._refresh_review_styles()

        # 更新摘要标签页样式
        self._refresh_summary_styles()

        # 更新分析标签页样式
        self._refresh_analysis_styles()

    def _refresh_summary_styles(self):
        """刷新摘要标签页的主题样式"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 更新说明卡片
        if info_card := self.content_widget.findChild(QFrame, "summary_info_card"):
            info_card.setStyleSheet(f"""
                QFrame#summary_info_card {{
                    background-color: {s.info_bg};
                    border: 1px solid {s.info};
                    border-left: 4px solid {s.info};
                    border-radius: {dp(4)}px;
                    padding: {dp(12)}px;
                }}
            """)

        # 更新说明标题
        if info_title := self.content_widget.findChild(QLabel, "summary_info_title"):
            info_title.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {s.text_info};
            """)

        # 更新说明描述
        if info_desc := self.content_widget.findChild(QLabel, "summary_info_desc"):
            info_desc.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
            """)

        # 更新摘要内容卡片
        if summary_card := self.content_widget.findChild(QFrame, "summary_content_card"):
            summary_card.setStyleSheet(f"""
                QFrame#summary_content_card {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(2)}px;
                }}
            """)

        # 更新摘要文本编辑器
        if summary_text := self.content_widget.findChild(QTextEdit, "summary_text_edit"):
            summary_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {s.bg_secondary};
                    border: none;
                    padding: {dp(16)}px;
                    font-family: {s.serif_font};
                    font-size: {sp(15)}px;
                    color: {s.text_primary};
                    line-height: 1.8;
                }}
                {s.scrollbar_style()}
            """)

        # 更新字数统计标签
        if word_count := self.content_widget.findChild(QLabel, "summary_word_count"):
            word_count.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
                padding: {dp(4)}px 0;
            """)

    def _refresh_analysis_styles(self):
        """刷新分析标签页的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 更新滚动区域
        if scroll_area := self.content_widget.findChild(QScrollArea, "analysis_scroll_area"):
            scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background-color: transparent;
                    border: none;
                }}
                {s.scrollbar_style()}
            """)

        # 更新分析说明卡片
        if info_card := self.content_widget.findChild(QFrame, "analysis_info_card"):
            info_card.setStyleSheet(f"""
                QFrame#analysis_info_card {{
                    background-color: {s.info_bg};
                    border: 1px solid {s.info};
                    border-left: 4px solid {s.info};
                    border-radius: {dp(4)}px;
                    padding: {dp(12)}px;
                }}
            """)

        # 更新分析说明标题
        if info_title := self.content_widget.findChild(QLabel, "analysis_info_title"):
            info_title.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {s.text_info};
            """)

        # 更新分析说明描述
        if info_desc := self.content_widget.findChild(QLabel, "analysis_info_desc"):
            info_desc.setStyleSheet(f"""
                font-family: {s.ui_font};
                font-size: {sp(12)}px;
                color: {s.text_secondary};
            """)

        # 更新各个分区卡片
        section_names = ["summaries", "metadata", "character_states", "key_events", "foreshadowing"]
        for section_name in section_names:
            if section_card := self.content_widget.findChild(QFrame, f"analysis_section_{section_name}"):
                section_card.setStyleSheet(f"""
                    QFrame#analysis_section_{section_name} {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(6)}px;
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新分区标题
                if title_label := section_card.findChild(QLabel, f"section_title_{section_name}"):
                    title_label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(14)}px;
                        font-weight: 600;
                        color: {s.text_primary};
                    """)

                # 更新分区图标
                if icon_label := section_card.findChild(QLabel, f"section_icon_{section_name}"):
                    icon_label.setStyleSheet(f"""
                        font-size: {sp(16)}px;
                        color: {s.accent_color};
                    """)

        # 更新所有分析标签的样式（使用缓存）
        # 合并处理三类标签：analysis_label_*, analysis_text_*, analysis_highlight_*
        analysis_labels = []
        if self._theme_cache_valid:
            analysis_labels = (
                self._cached_labels_by_prefix.get("analysis_label_", []) +
                self._cached_labels_by_prefix.get("analysis_text_", []) +
                self._cached_labels_by_prefix.get("analysis_highlight_", [])
            )
        else:
            analysis_labels = [
                label for label in self.content_widget.findChildren(QLabel)
                if label.objectName().startswith(("analysis_label_", "analysis_text_", "analysis_highlight_"))
            ]

        for label in analysis_labels:
            obj_name = label.objectName()
            if obj_name.startswith("analysis_label_"):
                # 特殊处理语义标签 - 使用对应的语义文字色
                if obj_name == "analysis_label_planted":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_warning};
                    """)
                elif obj_name == "analysis_label_resolved":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_success};
                        margin-top: {dp(12)}px;
                    """)
                elif obj_name == "analysis_label_tensions":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_error};
                        margin-top: {dp(12)}px;
                    """)
                elif obj_name in ["analysis_label_tone", "analysis_label_timeline"]:
                    # 情感基调和时间标记的小标签使用三级文字色
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(11)}px;
                        color: {s.text_tertiary};
                    """)
                else:
                    # 其他标签使用次要文字色
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                        font-weight: 600;
                        color: {s.text_secondary};
                    """)
            elif obj_name.startswith("analysis_text_"):
                # 特殊处理语义文字
                if obj_name == "analysis_text_tone":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {s.text_warning};
                    """)
                elif obj_name == "analysis_text_timeline":
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(13)}px;
                        font-weight: 600;
                        color: {s.text_info};
                    """)
                else:
                    label.setStyleSheet(f"""
                        font-family: {s.serif_font};
                        font-size: {sp(13)}px;
                        color: {s.text_primary};
                        line-height: 1.6;
                    """)
            elif obj_name.startswith("analysis_highlight_"):
                # 高亮框：透明背景+彩色边框
                label.setStyleSheet(f"""
                    font-family: {s.serif_font};
                    font-size: {sp(14)}px;
                    color: {s.accent_color};
                    font-weight: 500;
                    padding: {dp(10)}px;
                    background-color: transparent;
                    border: 1px solid {s.accent_color};
                    border-left: 3px solid {s.accent_color};
                    border-radius: {dp(4)}px;
                """)

        # 更新角色状态卡片、事件卡片、伏笔卡片（使用缓存）
        char_cards = self._cached_frames_by_prefix.get("char_state_card_", []) if self._theme_cache_valid else [
            f for f in self.content_widget.findChildren(QFrame) if f.objectName().startswith("char_state_card_")
        ]
        for char_card in char_cards:
            char_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(6)}px;
                    padding: {dp(10)}px;
                }}
            """)

        event_cards = self._cached_frames_by_prefix.get("event_card_", []) if self._theme_cache_valid else [
            f for f in self.content_widget.findChildren(QFrame) if f.objectName().startswith("event_card_")
        ]
        for event_card in event_cards:
            event_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.bg_secondary};
                    border-left: 3px solid {s.accent_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px;
                }}
            """)

        fs_cards = self._cached_frames_by_prefix.get("foreshadow_card_", []) if self._theme_cache_valid else [
            f for f in self.content_widget.findChildren(QFrame) if f.objectName().startswith("foreshadow_card_")
        ]
        for fs_card in fs_cards:
            fs_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {s.warning}08;
                    border-left: 2px solid {s.warning};
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px;
                }}
            """)

    def _refresh_version_cards_styles(self):
        """刷新版本卡片的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 查找所有 QTabWidget，排除主TabWidget，应用简约Tab样式（使用缓存）
        tab_widgets = self._cached_tab_widgets if self._theme_cache_valid else self.content_widget.findChildren(QTabWidget)
        for tab_widget in tab_widgets:
            if tab_widget != self.tab_widget:
                tab_widget.setStyleSheet(f"""
                    QTabWidget::pane {{ border: none; background: transparent; }}
                    QTabBar::tab {{
                        background: transparent; color: {s.text_secondary};
                        padding: {dp(6)}px {dp(12)}px; font-family: {s.ui_font};
                        border-bottom: 2px solid transparent;
                    }}
                    QTabBar::tab:selected {{
                        color: {s.accent_color}; border-bottom: 2px solid {s.accent_color};
                    }}
                """)

        # 查找所有版本卡片并更新样式
        for i in range(VersionConstants.MAX_VERSION_CARDS):
            card_name = f"version_card_{i}"
            if version_card := self.content_widget.findChild(QFrame, card_name):
                version_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(2)}px;
                        padding: {dp(2)}px;
                    }}
                """)

                # 更新版本卡片内的文本编辑器
                for text_edit in version_card.findChildren(QTextEdit):
                    text_edit.setStyleSheet(f"""
                        QTextEdit {{
                            background-color: transparent;
                            border: none;
                            padding: {dp(16)}px;
                            font-family: {s.serif_font};
                            font-size: {sp(14)}px;
                            color: {s.text_primary};
                            line-height: 1.6;
                        }}
                        {s.scrollbar_style()}
                    """)

            # 更新版本信息栏
            info_bar_name = f"version_info_bar_{i}"
            if info_bar := self.content_widget.findChild(QFrame, info_bar_name):
                info_bar.setStyleSheet(f"""
                    QFrame {{
                        background-color: transparent;
                        border-top: 1px solid {s.border_color};
                        border-radius: 0;
                        padding: {dp(8)}px {dp(12)}px;
                    }}
                """)

                # 更新信息栏内的标签
                for label in info_bar.findChildren(QLabel):
                    if "info_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.ui_font};
                            font-size: {sp(12)}px;
                            color: {s.text_secondary};
                        """)

                # 更新按钮样式 - 简约风
                btn_style = f"""
                    QPushButton {{
                        background: transparent;
                        color: {s.text_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(4)}px;
                        padding: {dp(4)}px {dp(8)}px;
                        font-family: {s.ui_font};
                        font-size: {sp(12)}px;
                    }}
                    QPushButton:hover {{
                        color: {s.accent_color};
                        border-color: {s.accent_color};
                    }}
                """

                for btn in info_bar.findChildren(QPushButton):
                    if "select_btn" in btn.objectName():
                        if btn.isEnabled():
                            btn.setStyleSheet(btn_style)
                        else:
                            btn.setStyleSheet(f"""
                                QPushButton {{
                                    background: transparent;
                                    color: {s.accent_color};
                                    border: none;
                                    font-family: {s.ui_font};
                                    font-weight: bold;
                                }}
                            """)
                    elif "retry_btn" in btn.objectName():
                        btn.setStyleSheet(btn_style)

    def _refresh_review_styles(self):
        """刷新评审区域的主题样式 - 书香风格"""
        if not self.content_widget:
            return

        s = self._styler  # 使用缓存的样式器属性

        # 更新推荐卡片
        if recommendation_card := self.content_widget.findChild(QFrame, "recommendation_card"):
            recommendation_card.setStyleSheet(f"""
                QFrame#recommendation_card {{
                    background-color: {s.bg_secondary};
                    border: 1px solid {s.accent_color};
                    border-left: 4px solid {s.accent_color};
                    border-radius: {dp(2)}px;
                    padding: {dp(14)}px;
                }}
            """)

            # 更新推荐卡片内的标题
            for label in recommendation_card.findChildren(QLabel):
                if "rec_title" in label.objectName():
                    label.setStyleSheet(f"""
                        font-family: {s.ui_font};
                        font-size: {sp(16)}px;
                        font-weight: bold;
                        color: {s.accent_color};
                    """)
                elif "rec_reason" in label.objectName():
                    label.setStyleSheet(f"""
                        font-family: {s.serif_font};
                        font-size: {sp(14)}px;
                        color: {s.text_primary};
                        line-height: 1.6;
                    """)

        # 更新评审卡片样式
        for i in range(1, 10):
            card_name = f"eval_card_{i}"
            if eval_card := self.content_widget.findChild(QFrame, card_name):
                eval_card.setStyleSheet(f"""
                    QFrame#{card_name} {{
                        background-color: {s.bg_secondary};
                        border: 1px solid {s.border_color};
                        border-radius: {dp(2)}px;
                        padding: {dp(12)}px;
                    }}
                """)

                # 更新评审卡片内的标题
                for label in eval_card.findChildren(QLabel):
                    if "eval_title" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.ui_font};
                            font-size: {sp(14)}px;
                            font-weight: bold;
                            color: {s.text_primary};
                        """)
                    elif "eval_badge" in label.objectName():
                        label.setStyleSheet(f"""
                            background: transparent;
                            color: {s.accent_color};
                            border: 1px solid {s.accent_color};
                            padding: {dp(2)}px {dp(8)}px;
                            border-radius: {dp(2)}px;
                            font-family: {s.ui_font};
                            font-size: {sp(11)}px;
                        """)
                    elif "pros_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.serif_font};
                            font-size: {sp(12)}px;
                            color: {s.text_secondary};
                            padding: {dp(4)}px 0;
                        """)
                    elif "cons_label" in label.objectName():
                        label.setStyleSheet(f"""
                            font-family: {s.serif_font};
                            font-size: {sp(12)}px;
                            color: {s.text_secondary};
                            padding: {dp(4)}px 0;
                        """)

        # 更新重新评审按钮
        if reeval_btn := self.content_widget.findChild(QPushButton, "reeval_btn"):
            reeval_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {s.text_secondary};
                    border: 1px solid {s.border_color};
                    border-radius: {dp(4)}px;
                    padding: {dp(6)}px {dp(12)}px;
                    font-family: {s.ui_font};
                }}
                QPushButton:hover {{
                    color: {s.accent_color};
                    border-color: {s.accent_color};
                }}
            """)

        # 更新开始评审按钮
        if evaluate_btn := self.content_widget.findChild(QPushButton, "evaluate_btn"):
            evaluate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {s.accent_color};
                    color: {s.button_text};
                    border: none;
                    border-radius: {dp(4)}px;
                    padding: {dp(8)}px {dp(16)}px;
                    font-family: {s.ui_font};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {s.text_primary};
                }}
            """)

    def _refresh_manga_tab_theme(self):
        """刷新漫画Tab的主题样式

        漫画Tab结构复杂，无法增量刷新样式。
        使用已缓存的漫画数据重建整个Tab，避免重新调用API。
        """
        if not self.tab_widget or self.tab_widget.count() < 6:
            return

        # 检查是否有缓存的漫画数据
        if not hasattr(self, '_cached_manga_data') or not self._cached_manga_data:
            return

        # 如果正在生成漫画提示词，跳过刷新避免破坏UI状态
        if getattr(self, '_manga_generating_chapter', None) is not None:
            return

        try:
            # 移除旧的漫画Tab
            old_manga_tab = self.tab_widget.widget(5)  # 漫画是第6个Tab（索引5）
            if old_manga_tab:
                self.tab_widget.removeTab(5)
                old_manga_tab.deleteLater()

            # 使用缓存的漫画数据创建新Tab
            new_manga_tab = self._manga_builder.create_manga_tab(self._cached_manga_data, self)
            self.tab_widget.insertTab(5, new_manga_tab, "漫画")
        except Exception:
            # 刷新失败时静默处理，不影响其他功能
            pass
