"""
目录结构Section - 详细展示和编辑项目目录结构

显示实际的项目文件树结构，每个节点直接展示详细信息，支持编辑目录和文件的描述信息。
Agent规划功能仅在工作台中可用。
"""

import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QFrame, QWidget, QPushButton,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QDialog, QLineEdit,
    QTextEdit, QComboBox, QFormLayout, QDialogButtonBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal

from windows.base.sections import BaseSection
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class DirectoryEditDialog(QDialog):
    """目录编辑对话框"""

    def __init__(self, node_data: Dict, parent=None):
        super().__init__(parent)
        self.node_data = node_data
        self.setWindowTitle("编辑目录")
        self.setMinimumWidth(dp(400))
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(16))

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(dp(12))

        # 名称（只读）
        self.name_edit = QLineEdit(self.node_data.get('name', ''))
        self.name_edit.setReadOnly(True)
        self.name_edit.setStyleSheet(f"background-color: {theme_manager.BG_TERTIARY};")
        form_layout.addRow("名称:", self.name_edit)

        # 路径（只读）
        path = self.node_data.get('path', '')
        if path:
            self.path_edit = QLineEdit(path)
            self.path_edit.setReadOnly(True)
            self.path_edit.setStyleSheet(f"background-color: {theme_manager.BG_TERTIARY};")
            form_layout.addRow("路径:", self.path_edit)

        # 描述（可编辑）
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.node_data.get('description', ''))
        self.description_edit.setMaximumHeight(dp(100))
        self.description_edit.setPlaceholderText("输入目录描述...")
        form_layout.addRow("描述:", self.description_edit)

        layout.addLayout(form_layout)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QLabel {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
            }}
            QLineEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
            }}
            QTextEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
            }}
            QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(13)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY}DD;
            }}
        """)

    def get_data(self) -> Dict:
        """获取编辑后的数据"""
        return {
            'description': self.description_edit.toPlainText().strip()
        }


class FileEditDialog(QDialog):
    """文件编辑对话框"""

    def __init__(self, file_data: Dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.setWindowTitle("编辑文件")
        self.setMinimumWidth(dp(450))
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(16))

        # 表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(dp(12))

        # 文件名（只读）
        self.filename_edit = QLineEdit(self.file_data.get('filename', ''))
        self.filename_edit.setReadOnly(True)
        self.filename_edit.setStyleSheet(f"background-color: {theme_manager.BG_TERTIARY};")
        form_layout.addRow("文件名:", self.filename_edit)

        # 路径（只读）
        path = self.file_data.get('file_path', '')
        if path:
            self.path_edit = QLineEdit(path)
            self.path_edit.setReadOnly(True)
            self.path_edit.setStyleSheet(f"background-color: {theme_manager.BG_TERTIARY};")
            form_layout.addRow("路径:", self.path_edit)

        # 描述（可编辑）
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.file_data.get('description', ''))
        self.description_edit.setMaximumHeight(dp(80))
        self.description_edit.setPlaceholderText("输入文件描述...")
        form_layout.addRow("描述:", self.description_edit)

        # 用途（可编辑）
        self.purpose_edit = QTextEdit()
        self.purpose_edit.setPlainText(self.file_data.get('purpose', ''))
        self.purpose_edit.setMaximumHeight(dp(80))
        self.purpose_edit.setPlaceholderText("输入文件用途...")
        form_layout.addRow("用途:", self.purpose_edit)

        # 优先级（可编辑）
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(['high', 'medium', 'low'])
        current_priority = self.file_data.get('priority', 'medium')
        index = self.priority_combo.findText(current_priority)
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)
        form_layout.addRow("优先级:", self.priority_combo)

        layout.addLayout(form_layout)

        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            QLabel {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(13)}px;
            }}
            QLineEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
            }}
            QTextEdit {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
            }}
            QComboBox {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(8)}px;
                font-size: {dp(13)}px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme_manager.BG_SECONDARY};
                color: {theme_manager.TEXT_PRIMARY};
                selection-background-color: {theme_manager.PRIMARY};
            }}
            QPushButton {{
                background-color: {theme_manager.PRIMARY};
                color: white;
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {dp(13)}px;
            }}
            QPushButton:hover {{
                background-color: {theme_manager.PRIMARY}DD;
            }}
        """)

    def get_data(self) -> Dict:
        """获取编辑后的数据"""
        return {
            'description': self.description_edit.toPlainText().strip(),
            'purpose': self.purpose_edit.toPlainText().strip(),
            'priority': self.priority_combo.currentText()
        }


class DirectoryNodeWidget(QWidget):
    """目录节点内容组件 - 显示目录详细信息"""

    editClicked = pyqtSignal(int, dict)  # node_id, node_data

    def __init__(self, node_data: Dict, parent=None):
        super().__init__(parent)
        self.node_data = node_data
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        layout.setSpacing(dp(2))

        # 第一行：目录名
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        node_type = self.node_data.get('node_type', 'directory')
        name = self.node_data.get('name', '')

        # 目录名标签
        name_label = QLabel(f"[D] {name}/")
        name_label.setStyleSheet(f"""
            color: {theme_manager.TEXT_PRIMARY};
            font-weight: 600;
            font-size: {dp(13)}px;
        """)
        header_layout.addWidget(name_label)

        # 类型标签
        type_display = self._get_type_display(node_type)
        type_label = QLabel(type_display)
        type_label.setStyleSheet(f"""
            color: {theme_manager.TEXT_TERTIARY};
            font-size: {dp(11)}px;
            background-color: {theme_manager.BG_TERTIARY};
            padding: {dp(2)}px {dp(6)}px;
            border-radius: {dp(3)}px;
        """)
        header_layout.addWidget(type_label)

        header_layout.addStretch()

        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("edit_btn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton#edit_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(3)}px;
                padding: {dp(2)}px {dp(8)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#edit_btn:hover {{
                background-color: {theme_manager.PRIMARY}20;
            }}
        """)
        edit_btn.clicked.connect(self._on_edit_clicked)
        header_layout.addWidget(edit_btn)

        layout.addLayout(header_layout)

        # 第二行：描述
        description = self.node_data.get('description', '')
        if description:
            desc_label = QLabel(f"描述: {description}")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(11)}px;
                padding-left: {dp(16)}px;
            """)
            layout.addWidget(desc_label)

    def _get_type_display(self, node_type: str) -> str:
        mapping = {
            'root': '项目根目录',
            'directory': '目录',
            'module': '模块',
            'package': '包',
            'config': '配置',
        }
        return mapping.get(node_type, node_type)

    def _on_edit_clicked(self):
        node_id = self.node_data.get('id')
        if node_id:
            self.editClicked.emit(node_id, self.node_data)


class FileNodeWidget(QWidget):
    """文件节点内容组件 - 显示文件详细信息"""

    editClicked = pyqtSignal(int, dict)  # file_id, file_data

    def __init__(self, file_data: Dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(4), dp(4), dp(4), dp(4))
        layout.setSpacing(dp(2))

        # 第一行：文件名 + 类型 + 优先级 + 编辑按钮
        header_layout = QHBoxLayout()
        header_layout.setSpacing(dp(8))

        filename = self.file_data.get('filename', '')
        file_type = self.file_data.get('file_type', 'source')
        priority = self.file_data.get('priority', 'medium')
        status = self.file_data.get('status', 'pending')

        # 文件名
        name_label = QLabel(f"    {filename}")
        name_label.setStyleSheet(f"""
            color: {theme_manager.TEXT_PRIMARY};
            font-size: {dp(12)}px;
        """)
        header_layout.addWidget(name_label)

        # 类型标签
        type_display = self._get_file_type_display(file_type)
        type_label = QLabel(type_display)
        type_label.setStyleSheet(f"""
            color: {theme_manager.TEXT_TERTIARY};
            font-size: {dp(10)}px;
            background-color: {theme_manager.BG_TERTIARY};
            padding: {dp(1)}px {dp(4)}px;
            border-radius: {dp(2)}px;
        """)
        header_layout.addWidget(type_label)

        # 优先级标签
        priority_colors = {
            'high': theme_manager.ERROR,
            'medium': theme_manager.WARNING,
            'low': theme_manager.SUCCESS,
        }
        priority_color = priority_colors.get(priority, theme_manager.TEXT_TERTIARY)
        priority_display = {'high': '高', 'medium': '中', 'low': '低'}.get(priority, priority)
        priority_label = QLabel(priority_display)
        priority_label.setStyleSheet(f"""
            color: {priority_color};
            font-size: {dp(10)}px;
            background-color: {priority_color}20;
            padding: {dp(1)}px {dp(4)}px;
            border-radius: {dp(2)}px;
        """)
        header_layout.addWidget(priority_label)

        # 状态标签
        status_display = self._get_status_display(status)
        status_label = QLabel(status_display)
        status_label.setStyleSheet(f"""
            color: {theme_manager.TEXT_TERTIARY};
            font-size: {dp(10)}px;
        """)
        header_layout.addWidget(status_label)

        header_layout.addStretch()

        # 编辑按钮
        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("file_edit_btn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet(f"""
            QPushButton#file_edit_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(3)}px;
                padding: {dp(2)}px {dp(8)}px;
                font-size: {dp(11)}px;
            }}
            QPushButton#file_edit_btn:hover {{
                background-color: {theme_manager.PRIMARY}20;
            }}
        """)
        edit_btn.clicked.connect(self._on_edit_clicked)
        header_layout.addWidget(edit_btn)

        layout.addLayout(header_layout)

        # 第二行：描述
        description = self.file_data.get('description', '')
        if description:
            desc_label = QLabel(f"描述: {description}")
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {dp(11)}px;
                padding-left: {dp(32)}px;
            """)
            layout.addWidget(desc_label)

        # 第三行：用途
        purpose = self.file_data.get('purpose', '')
        if purpose:
            purpose_label = QLabel(f"用途: {purpose}")
            purpose_label.setWordWrap(True)
            purpose_label.setStyleSheet(f"""
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(11)}px;
                padding-left: {dp(32)}px;
            """)
            layout.addWidget(purpose_label)

    def _get_file_type_display(self, file_type: str) -> str:
        mapping = {
            'source': '源代码',
            'config': '配置',
            'test': '测试',
            'doc': '文档',
            'resource': '资源',
        }
        return mapping.get(file_type, file_type)

    def _get_status_display(self, status: str) -> str:
        mapping = {
            'pending': '待生成',
            'generating': '生成中',
            'generated': '已生成',
            'reviewed': '已审查',
            'error': '失败',
        }
        return mapping.get(status, status)

    def _on_edit_clicked(self):
        file_id = self.file_data.get('id')
        if file_id:
            self.editClicked.emit(file_id, self.file_data)


class DirectorySection(BaseSection):
    """目录结构Section - 详细展示和编辑

    展示项目的实际文件树结构，每个节点直接显示详细信息，支持编辑。
    Agent规划功能已移至工作台。
    """

    # 信号
    loadingRequested = pyqtSignal(str)
    loadingFinished = pyqtSignal()
    fileClicked = pyqtSignal(int)  # file_id - 用于跳转到文件Prompt生成页面

    def __init__(
        self,
        modules: List[Dict] = None,
        directory_tree: Dict[str, Any] = None,
        project_id: str = None,
        editable: bool = True,
        parent=None
    ):
        self.project_id = project_id
        self.modules = modules or []
        self.directory_tree = directory_tree or {}
        self.api_client = APIClientManager.get_client()
        self._data_loaded = False

        super().__init__([], editable, parent)
        self.setupUI()

        # 初始化后自动加载目录树数据
        if self.project_id:
            if not self.directory_tree.get('root_nodes'):
                self._load_directory_tree()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 标题栏
        stats_text = self._build_stats_text(self.directory_tree)

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.setObjectName("refresh_btn")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._on_refresh)

        # 展开/折叠按钮：用于快速核对“总计统计”与实际展开看到的节点
        expand_btn = QPushButton("展开全部")
        expand_btn.setObjectName("expand_btn")
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.clicked.connect(self._on_expand_all)

        collapse_btn = QPushButton("折叠全部")
        collapse_btn.setObjectName("collapse_btn")
        collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        collapse_btn.clicked.connect(self._on_collapse_all)

        header, labels = self._build_section_header(
            "目录结构",
            stat_items=[(stats_text, "stats_label")],
            right_widgets=[collapse_btn, expand_btn, refresh_btn],
        )
        self.stats_label = labels.get("stats_label")
        layout.addWidget(header)

        # 目录树容器
        tree_container = QWidget()
        tree_container.setObjectName("tree_container")
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(0)

        # 创建目录树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setObjectName("directory_tree")
        self.tree_widget.setHeaderHidden(True)  # 隐藏表头，因为使用自定义widget
        self.tree_widget.setColumnCount(1)
        self.tree_widget.setRootIsDecorated(True)
        self.tree_widget.setAnimated(True)
        self.tree_widget.setExpandsOnDoubleClick(False)  # 禁用双击展开，使用双击跳转
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        # 设置列宽
        header_view = self.tree_widget.header()
        header_view.setStretchLastSection(True)

        tree_layout.addWidget(self.tree_widget)
        layout.addWidget(tree_container, 1)  # 让树占用剩余空间

        # 填充目录树
        self._populate_tree()

        self._apply_styles()

    def _compute_tree_stats(self, directory_tree: Dict[str, Any]) -> Dict[str, int]:
        """基于目录树数据递归统计目录/文件数量（以实际展示为准）。"""
        root_nodes = directory_tree.get("root_nodes") or []

        def walk(nodes: List[Dict[str, Any]]) -> tuple[int, int, int]:
            total_dirs = 0
            total_files = 0
            init_files = 0

            for node in nodes:
                if not isinstance(node, dict):
                    continue

                total_dirs += 1
                files = node.get("files") or []
                if isinstance(files, list):
                    valid_files = [f for f in files if isinstance(f, dict)]
                    total_files += len(valid_files)
                    init_files += sum(1 for f in valid_files if f.get("filename") == "__init__.py")

                children = node.get("children") or []
                if isinstance(children, list) and children:
                    child_dirs, child_files, child_inits = walk(children)
                    total_dirs += child_dirs
                    total_files += child_files
                    init_files += child_inits

            return total_dirs, total_files, init_files

        dirs, files, init_files = walk(root_nodes)
        return {
            "total_directories": dirs,
            "total_files": files,
            "init_files": init_files,
        }

    def _build_stats_text(self, directory_tree: Dict[str, Any]) -> str:
        """构建统计文案：优先使用树结构递归统计，避免与实际展示不一致。"""
        computed = self._compute_tree_stats(directory_tree)
        computed_dirs = computed["total_directories"]
        computed_files = computed["total_files"]
        init_files = computed["init_files"]

        backend_dirs = directory_tree.get("total_directories", 0)
        backend_files = directory_tree.get("total_files", 0)

        # 若后端字段与树结构不一致，优先展示“实际树结构统计”，并在日志中记录差异。
        if (backend_dirs, backend_files) != (computed_dirs, computed_files):
            logger.warning(
                "目录树统计不一致：tree=%d/%d, backend=%d/%d",
                computed_dirs,
                computed_files,
                backend_dirs,
                backend_files,
            )

        extra_parts = []
        if init_files:
            non_init_files = max(0, computed_files - init_files)
            extra_parts.append(f"__init__.py: {init_files}")
            extra_parts.append(f"非__init__.py: {non_init_files}")

        extra = f"（{'，'.join(extra_parts)}）" if extra_parts else ""
        return f"总计 {computed_dirs} 目录 / {computed_files} 文件{extra}"

    def _populate_tree(self):
        """填充目录树"""
        self.tree_widget.clear()

        root_nodes = self.directory_tree.get('root_nodes', [])

        if not root_nodes:
            # 空状态
            empty_item = QTreeWidgetItem(self.tree_widget)
            empty_widget = QLabel("暂无目录结构，请在工作台中使用 Agent 生成")
            empty_widget.setStyleSheet(f"""
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                padding: {dp(20)}px;
            """)
            empty_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tree_widget.setItemWidget(empty_item, 0, empty_widget)
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # 递归添加节点
        for node in root_nodes:
            self._add_tree_node(self.tree_widget.invisibleRootItem(), node)

        # 展开第一层
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                item.setExpanded(True)

    def _add_tree_node(self, parent_item, node_data: Dict):
        """递归添加目录节点"""
        item = QTreeWidgetItem(parent_item)
        item.setData(0, Qt.ItemDataRole.UserRole, node_data)

        # 创建目录节点组件
        node_widget = DirectoryNodeWidget(node_data)
        node_widget.editClicked.connect(self._on_edit_directory)
        self.tree_widget.setItemWidget(item, 0, node_widget)

        # 设置适当的高度
        item.setSizeHint(0, node_widget.sizeHint())

        # 添加该目录下的文件
        files = node_data.get('files', [])
        for file_data in files:
            self._add_file_node(item, file_data)

        # 递归添加子目录
        children = node_data.get('children', [])
        for child in children:
            self._add_tree_node(item, child)

    def _add_file_node(self, parent_item, file_data: Dict):
        """添加文件节点"""
        item = QTreeWidgetItem(parent_item)
        item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'file', 'data': file_data})

        # 创建文件节点组件
        file_widget = FileNodeWidget(file_data)
        file_widget.editClicked.connect(self._on_edit_file)
        self.tree_widget.setItemWidget(item, 0, file_widget)

        # 设置适当的高度
        item.setSizeHint(0, file_widget.sizeHint())

    def _on_edit_directory(self, node_id: int, node_data: Dict):
        """编辑目录"""
        logger.info(f"编辑目录: node_id={node_id}")

        dialog = DirectoryEditDialog(node_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._save_directory(node_id, data)

    def _on_edit_file(self, file_id: int, file_data: Dict):
        """编辑文件"""
        logger.info(f"编辑文件: file_id={file_id}")

        dialog = FileEditDialog(file_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            self._save_file(file_id, data)

    def _save_directory(self, node_id: int, data: Dict):
        """保存目录修改"""
        self.loadingRequested.emit("正在保存...")

        worker = AsyncAPIWorker(
            self.api_client.update_directory,
            self.project_id,
            node_id,
            description=data.get('description')
        )
        worker.success.connect(self._on_directory_saved)
        worker.error.connect(self._on_save_error)
        self._register_worker(worker)
        worker.start()

    def _save_file(self, file_id: int, data: Dict):
        """保存文件修改"""
        self.loadingRequested.emit("正在保存...")

        worker = AsyncAPIWorker(
            self.api_client.update_source_file,
            self.project_id,
            file_id,
            description=data.get('description'),
            purpose=data.get('purpose'),
            priority=data.get('priority')
        )
        worker.success.connect(self._on_file_saved)
        worker.error.connect(self._on_save_error)
        self._register_worker(worker)
        worker.start()

    def _on_directory_saved(self, result):
        """目录保存成功"""
        self.loadingFinished.emit()
        MessageService.show_success(self, "目录信息已保存")
        # 刷新显示
        self._load_directory_tree()

    def _on_file_saved(self, result):
        """文件保存成功"""
        self.loadingFinished.emit()
        MessageService.show_success(self, "文件信息已保存")
        # 刷新显示
        self._load_directory_tree()

    def _on_save_error(self, error_msg: str):
        """保存失败"""
        self.loadingFinished.emit()
        logger.error(f"保存失败: {error_msg}")
        MessageService.show_error(self, f"保存失败: {error_msg}")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """双击项目 - 如果是文件节点，跳转到编辑"""
        node_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not node_data:
            return

        # 如果是文件节点，跳转到Prompt生成页面
        if isinstance(node_data, dict) and node_data.get('type') == 'file':
            file_data = node_data.get('data', {})
            file_id = file_data.get('id')
            if file_id:
                self.fileClicked.emit(file_id)

    def _apply_styles(self):
        """应用样式"""
        self.setStyleSheet(f"""
            QLabel#section_title {{
                color: {theme_manager.TEXT_PRIMARY};
                font-size: {dp(18)}px;
                font-weight: 600;
            }}
            QLabel#stats_label {{
                color: {theme_manager.TEXT_TERTIARY};
                font-size: {dp(13)}px;
                margin-left: {dp(12)}px;
            }}
            QPushButton#refresh_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#refresh_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QPushButton#expand_btn, QPushButton#collapse_btn {{
                background-color: transparent;
                color: {theme_manager.PRIMARY};
                border: 1px solid {theme_manager.PRIMARY};
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(12)}px;
                font-size: {dp(12)}px;
            }}
            QPushButton#expand_btn:hover, QPushButton#collapse_btn:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QTreeWidget#directory_tree {{
                background-color: {theme_manager.book_bg_secondary()};
                color: {theme_manager.book_text_primary()};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(8)}px;
                padding: {dp(8)}px;
            }}
            QTreeWidget#directory_tree::item {{
                border-radius: {dp(4)}px;
                padding: {dp(2)}px 0;
            }}
            QTreeWidget#directory_tree::item:hover {{
                background-color: {theme_manager.PRIMARY}10;
            }}
            QTreeWidget#directory_tree::item:selected {{
                background-color: {theme_manager.PRIMARY}20;
            }}
            QTreeWidget#directory_tree::branch {{
                background-color: transparent;
            }}
        """)

    def _apply_theme(self):
        """应用主题"""
        self._apply_styles()

    def _on_refresh(self):
        """刷新"""
        self._load_directory_tree()

    def _on_expand_all(self):
        """展开全部目录节点（用于快速核对目录/文件数量）"""
        if hasattr(self, "tree_widget") and self.tree_widget:
            self.tree_widget.expandAll()

    def _on_collapse_all(self):
        """折叠全部目录节点（保留顶层展开）"""
        if not hasattr(self, "tree_widget") or not self.tree_widget:
            return

        self.tree_widget.collapseAll()
        # 保留第一层展开，避免“空白树”的错觉
        for i in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(i)
            if item:
                item.setExpanded(True)

    def _load_directory_tree(self):
        """加载目录树数据"""
        if not self.project_id:
            return

        logger.info(f"加载目录树: project_id={self.project_id}")

        worker = AsyncAPIWorker(
            self.api_client.get_directory_tree,
            self.project_id
        )
        worker.success.connect(self._on_directory_tree_loaded)
        worker.error.connect(self._on_directory_tree_error)
        self._register_worker(worker)
        worker.start()

    def _on_directory_tree_loaded(self, result):
        """目录树加载成功"""
        computed = self._compute_tree_stats(result)
        non_init_files = max(0, computed["total_files"] - computed["init_files"])
        logger.info(
            "目录树加载成功: %d 目录, %d 文件（__init__.py=%d, 非__init__.py=%d）",
            computed["total_directories"],
            computed["total_files"],
            computed["init_files"],
            non_init_files,
        )
        self.directory_tree = result
        self._data_loaded = True

        # 更新统计
        if hasattr(self, 'stats_label') and self.stats_label:
            stats_text = self._build_stats_text(result)
            self.stats_label.setText(stats_text)

        # 重新填充目录树
        self._populate_tree()

    def _on_directory_tree_error(self, error_msg: str):
        """目录树加载失败"""
        logger.warning(f"目录树加载失败: {error_msg}")
        # 不显示错误，可能只是还没有生成目录结构

    def updateData(
        self,
        modules: List[Dict] = None,
        directory_tree: Dict[str, Any] = None
    ):
        """更新数据"""
        if modules is not None:
            self.modules = modules
        if directory_tree is not None:
            self.directory_tree = directory_tree

        # 更新统计
        if hasattr(self, 'stats_label') and self.stats_label:
            stats_text = self._build_stats_text(self.directory_tree)
            self.stats_label.setText(stats_text)

        self._populate_tree()

    def cleanup(self):
        """清理资源"""
        self._cleanup_workers()


__all__ = ["DirectorySection"]
