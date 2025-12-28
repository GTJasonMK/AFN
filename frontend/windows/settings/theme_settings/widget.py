"""
主题配置设置Widget

提供用户自定义主题的完整编辑界面。

架构说明：
- ThemeSettingsWidget: 主Widget类，负责UI布局
- ThemeStylesMixin: 样式应用
- ThemeConfigEditorMixin: 配置CRUD操作
- ThemeIOHandlerMixin: 导入导出功能
"""

from typing import Dict, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QListWidget, QStackedWidget, QScrollArea,
    QTabWidget, QLineEdit, QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt

from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from api.manager import APIClientManager
from components.inputs import (
    ColorPickerWidget, SizeInputWidget, FontFamilySelector,
    SliderInputWidget, SwitchWidget
)

from .config_groups import CONFIG_GROUPS
from .styles import ThemeStylesMixin
from .config_editor import ThemeConfigEditorMixin
from .io_handler import ThemeIOHandlerMixin


class ThemeSettingsWidget(ThemeStylesMixin, ThemeConfigEditorMixin, ThemeIOHandlerMixin, QWidget):
    """主题配置设置Widget

    布局：
    +-----------------------------------------------------------------+
    | [浅色主题] [深色主题]                              顶部Tab切换    |
    +---------------+----------------------------------------------- -+
    | 子主题列表     | 配置编辑区（可滚动）                            |
    | +------------+ | +--------------------------------------------- |
    | | + 新建     | | | > 主色调                                    |
    | +------------+ | |   PRIMARY        [#8B4513] [选择]           |
    | | 书香浅色 * | | |   ...                                       |
    | | 我的主题   | | +---------------------------------------------+|
    | +------------+ |                                                 |
    +----------------+------------------------------------------------+
    | [重置为默认]                    [预览] [保存] [激活]             |
    +-----------------------------------------------------------------+
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()

        # 状态
        self._current_mode = "light"  # 当前选中的顶级主题模式
        self._current_config_id = None  # 当前选中的配置ID
        self._configs: List[Dict] = []  # 配置列表缓存
        self._field_widgets: Dict[str, Dict[str, QWidget]] = {}  # 字段编辑器映射
        self._is_modified = False  # 是否有未保存的修改
        self._worker = None  # AsyncWorker实例，防止垃圾回收
        self._is_destroyed = False  # 标记widget是否已销毁

        self._create_ui()
        self._apply_theme()
        # 注意：_load_configs() 由 SettingsView._load_page_data() 通过 refresh() 延迟调用

        # 监听主题变化
        theme_manager.theme_changed.connect(self._apply_theme)

    def closeEvent(self, event):
        """关闭事件：清理异步工作线程"""
        self._cleanup_worker()
        super().closeEvent(event)

    def _cleanup_worker(self):
        """清理异步工作线程"""
        self._is_destroyed = True
        if self._worker is not None:
            try:
                if hasattr(self._worker, 'cancel'):
                    self._worker.cancel()
                try:
                    self._worker.success.disconnect()
                    self._worker.error.disconnect()
                except (TypeError, RuntimeError):
                    pass
                if self._worker.isRunning():
                    self._worker.wait(100)
            except RuntimeError:
                pass
            self._worker = None

    def _create_ui(self):
        """创建UI结构"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(dp(16))

        # 顶部Tab切换
        self.mode_tabs = QTabWidget()
        self.mode_tabs.setObjectName("mode_tabs")
        self.mode_tabs.addTab(QWidget(), "浅色主题")
        self.mode_tabs.addTab(QWidget(), "深色主题")
        self.mode_tabs.currentChanged.connect(self._on_mode_changed)
        main_layout.addWidget(self.mode_tabs)

        # 内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(dp(16))

        # 左侧：子主题列表
        left_panel = self._create_left_panel()
        content_layout.addWidget(left_panel)

        # 右侧：配置编辑区
        right_panel = self._create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)

        main_layout.addLayout(content_layout, stretch=1)

        # 底部操作按钮
        bottom_bar = self._create_bottom_bar()
        main_layout.addWidget(bottom_bar)

    def _create_left_panel(self) -> QWidget:
        """创建左侧子主题列表面板"""
        panel = QFrame()
        panel.setObjectName("left_panel")
        panel.setFixedWidth(dp(200))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(dp(8), dp(8), dp(8), dp(8))
        layout.setSpacing(dp(8))

        # 新建按钮
        self.new_btn = QPushButton("+ 新建子主题")
        self.new_btn.setObjectName("new_theme_btn")
        self.new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_btn.clicked.connect(self._create_new_config)
        layout.addWidget(self.new_btn)

        # 子主题列表
        self.config_list = QListWidget()
        self.config_list.setObjectName("config_list")
        self.config_list.setFrameShape(QFrame.Shape.NoFrame)
        self.config_list.currentRowChanged.connect(self._on_config_selected)
        layout.addWidget(self.config_list, stretch=1)

        # 列表操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(8))

        self.duplicate_btn = QPushButton("复制")
        self.duplicate_btn.setObjectName("list_action_btn")
        self.duplicate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.duplicate_btn.clicked.connect(self._duplicate_config)
        btn_layout.addWidget(self.duplicate_btn)

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("list_action_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self._delete_config)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

        return panel

    def _create_right_panel(self) -> QWidget:
        """创建右侧配置编辑区"""
        panel = QFrame()
        panel.setObjectName("right_panel")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setObjectName("config_scroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 滚动内容
        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        self.config_layout = QVBoxLayout(scroll_content)
        self.config_layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        self.config_layout.setSpacing(dp(16))

        # 配置名称编辑
        name_layout = QHBoxLayout()
        name_label = QLabel("配置名称：")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入配置名称")
        self.name_input.textChanged.connect(lambda: self._mark_modified())
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input, stretch=1)
        self.config_layout.addLayout(name_layout)

        # 创建各配置组
        self._create_config_groups()

        self.config_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        return panel

    def _create_config_groups(self):
        """创建配置分组"""
        for group_key, group_def in CONFIG_GROUPS.items():
            group_box = QGroupBox(group_def["label"])
            group_box.setObjectName(f"group_{group_key}")

            # 设置分组的工具提示
            group_description = group_def.get("description", "")
            if group_description:
                group_box.setToolTip(group_description)

            grid = QGridLayout(group_box)
            grid.setContentsMargins(dp(12), dp(16), dp(12), dp(12))
            grid.setSpacing(dp(8))
            grid.setColumnStretch(1, 1)

            self._field_widgets[group_key] = {}

            row = 0
            for field_key, field_info in group_def["fields"].items():
                # 解析字段信息
                if isinstance(field_info, tuple):
                    field_type = field_info[0]
                    field_label = field_info[1] if len(field_info) > 1 else field_key
                    # 第三个参数可能是tooltip字符串或slider的options字典
                    field_extra = field_info[2] if len(field_info) > 2 else None
                else:
                    field_type = "text"
                    field_label = field_key
                    field_extra = None

                # switch和slider自带标签，跨两列显示
                if field_type == "switch":
                    # 解析描述文字
                    description = field_extra if isinstance(field_extra, str) else ""
                    widget = SwitchWidget(
                        label=field_label,
                        default=False,
                        description=description
                    )
                    widget.toggled.connect(lambda checked: self._mark_modified())
                    # 跨两列
                    grid.addWidget(widget, row, 0, 1, 2)
                elif field_type == "slider":
                    # 解析slider选项
                    options = field_extra if isinstance(field_extra, dict) else {}
                    widget = SliderInputWidget(
                        label=field_label,
                        min_value=options.get("min", 0),
                        max_value=options.get("max", 100),
                        step=options.get("step", 1),
                        default_value=options.get("default", 50),
                        value_format="{:.0f}"  # 显示为整数
                    )
                    widget.value_changed.connect(lambda v: self._mark_modified())
                    # 跨两列
                    grid.addWidget(widget, row, 0, 1, 2)
                else:
                    # 普通字段：左侧标签 + 右侧输入
                    field_tooltip = field_extra if isinstance(field_extra, str) else ""

                    label = QLabel(f"{field_label}:")
                    label.setObjectName("field_label")
                    if field_tooltip:
                        label.setToolTip(field_tooltip)
                        label.setCursor(Qt.CursorShape.WhatsThisCursor)
                    grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight)

                    if field_type == "color":
                        widget = ColorPickerWidget()
                        widget.color_changed.connect(lambda: self._mark_modified())
                    elif field_type == "size":
                        widget = SizeInputWidget(allowed_units=["px", "em", "rem", "%", "ms"])
                        widget.value_changed.connect(lambda: self._mark_modified())
                    elif field_type == "font":
                        widget = FontFamilySelector()
                        widget.value_changed.connect(lambda: self._mark_modified())
                    else:  # text
                        widget = QLineEdit()
                        widget.setObjectName("text_field_input")
                        widget.textChanged.connect(lambda: self._mark_modified())

                    if field_tooltip:
                        widget.setToolTip(field_tooltip)

                    grid.addWidget(widget, row, 1)

                self._field_widgets[group_key][field_key] = widget
                row += 1

            self.config_layout.addWidget(group_box)

    def _create_bottom_bar(self) -> QWidget:
        """创建底部操作栏"""
        bar = QFrame()
        bar.setObjectName("bottom_bar")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(dp(16), dp(12), dp(16), dp(12))
        layout.setSpacing(dp(12))

        # 重置按钮
        self.reset_btn = QPushButton("重置为默认")
        self.reset_btn.setObjectName("reset_btn")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._reset_config)
        layout.addWidget(self.reset_btn)

        # 导入按钮
        self.import_btn = QPushButton("导入")
        self.import_btn.setObjectName("import_btn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self._import_configs)
        layout.addWidget(self.import_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_configs)
        layout.addWidget(self.export_btn)

        layout.addStretch()

        # 保存按钮
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_config)
        layout.addWidget(self.save_btn)

        # 激活按钮
        self.activate_btn = QPushButton("激活")
        self.activate_btn.setObjectName("activate_btn")
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.clicked.connect(self._activate_config)
        layout.addWidget(self.activate_btn)

        return bar

    def refresh(self):
        """刷新配置列表"""
        self._load_configs()
        # 确保透明度配置始终从本地加载显示
        self._load_transparency_config()

    def _load_transparency_config(self):
        """加载透明度配置到UI

        透明度配置保存在本地，不依赖后端，需要独立加载。
        """
        from themes.theme_manager import theme_manager

        transparency_config = theme_manager.get_transparency_config()
        transparency_fields = self._convert_transparency_to_fields(transparency_config)

        transparency_widgets = self._field_widgets.get("transparency", {})
        for field_key, widget in transparency_widgets.items():
            value = transparency_fields.get(field_key)
            if isinstance(widget, SwitchWidget):
                widget.setChecked(bool(value))
            elif isinstance(widget, SliderInputWidget):
                if value is not None:
                    widget.set_value(float(value), emit_signal=False)


__all__ = [
    "ThemeSettingsWidget",
]
