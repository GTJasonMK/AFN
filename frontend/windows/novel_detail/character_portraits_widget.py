"""
角色立绘管理界面

提供角色立绘的生成、管理和预览功能。
"""

import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QWidget, QScrollArea, QComboBox, QTextEdit, QGridLayout,
    QSizePolicy, QSpacerItem,
)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QImage

from api.client import AFNAPIClient
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.async_worker import AsyncWorker

logger = logging.getLogger(__name__)


class PortraitCard(ThemeAwareWidget):
    """单个角色立绘卡片"""

    generateRequested = pyqtSignal(str)  # character_name
    setActiveRequested = pyqtSignal(str)  # portrait_id
    deleteRequested = pyqtSignal(str)  # portrait_id

    def __init__(
        self,
        character_name: str,
        character_description: str = "",
        portrait_data: Optional[Dict[str, Any]] = None,
        parent=None
    ):
        self.character_name = character_name
        self.character_description = character_description
        self.portrait_data = portrait_data
        self._is_generating = False  # 是否正在生成

        # 组件引用
        self.name_label = None
        self.description_label = None
        self.image_label = None
        self.status_label = None
        self.generate_btn = None
        self.set_active_btn = None
        self.delete_btn = None
        self.style_combo = None
        self._image_worker = None  # 图片加载工作线程

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(8))

        # 角色名称
        self.name_label = QLabel(self.character_name)
        self.name_label.setObjectName("character_name")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        # 图片区域
        image_container = QFrame()
        image_container.setObjectName("image_container")
        image_container.setFixedSize(dp(160), dp(160))
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(dp(150), dp(150))
        self.image_label.setScaledContents(True)
        image_layout.addWidget(self.image_label)

        layout.addWidget(image_container, alignment=Qt.AlignmentFlag.AlignCenter)

        # 状态标签
        self.status_label = QLabel()
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # 风格选择
        style_layout = QHBoxLayout()
        style_layout.setSpacing(dp(8))

        style_label = QLabel("风格:")
        style_layout.addWidget(style_label)

        self.style_combo = QComboBox()
        self.style_combo.addItem("动漫风格", "anime")
        self.style_combo.addItem("漫画风格", "manga")
        self.style_combo.addItem("写实风格", "realistic")
        self.style_combo.setFixedWidth(dp(100))
        style_layout.addWidget(self.style_combo)

        style_layout.addStretch()
        layout.addLayout(style_layout)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(dp(8))

        self.generate_btn = QPushButton("生成")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(
            lambda: self.generateRequested.emit(self.character_name)
        )
        btn_layout.addWidget(self.generate_btn)

        if self.portrait_data:
            if not self.portrait_data.get('is_active', False):
                self.set_active_btn = QPushButton("使用")
                self.set_active_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                self.set_active_btn.clicked.connect(
                    lambda: self.setActiveRequested.emit(self.portrait_data.get('id', ''))
                )
                btn_layout.addWidget(self.set_active_btn)

            self.delete_btn = QPushButton("删除")
            self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.delete_btn.clicked.connect(
                lambda: self.deleteRequested.emit(self.portrait_data.get('id', ''))
            )
            btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

        # 更新显示
        self._update_display()

    def _update_display(self):
        """更新显示状态"""
        if self.portrait_data and self.portrait_data.get('image_url'):
            self.status_label.setText("已生成" + (" (当前使用)" if self.portrait_data.get('is_active') else ""))
            # 图片需要异步加载
            self._load_image(self.portrait_data.get('image_url'))
        else:
            self.status_label.setText("未生成")
            self.image_label.setText("无图片")

    def _load_image(self, image_url: str):
        """异步加载图片"""
        # 构建完整URL
        if not image_url.startswith('http'):
            image_url = f"http://127.0.0.1:8123{image_url}"

        self.image_label.setText("加载中...")

        def fetch_image():
            import requests
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                return response.content
            return None

        self._image_worker = AsyncWorker(fetch_image)
        self._image_worker.success.connect(self._on_image_loaded)
        self._image_worker.error.connect(lambda _: self.image_label.setText("加载失败"))
        self._image_worker.start()

    def _on_image_loaded(self, image_data):
        """图片加载完成回调"""
        if image_data:
            image = QImage()
            if image.loadFromData(image_data):
                pixmap = QPixmap.fromImage(image)
                scaled = pixmap.scaled(
                    dp(150), dp(150),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)
                return
        self.image_label.setText("加载失败")

    def get_selected_style(self) -> str:
        """获取选中的风格"""
        return self.style_combo.currentData() or "anime"

    def setGenerating(self, generating: bool):
        """设置生成状态"""
        self._is_generating = generating

        if generating:
            # 显示生成中状态
            self.status_label.setText("正在生成...")
            self.status_label.setStyleSheet(f"""
                QLabel#status_label {{
                    font-size: {sp(12)}px;
                    color: {theme_manager.PRIMARY};
                    font-weight: bold;
                }}
            """)
            self.image_label.setText("生成中...")

            # 禁用按钮
            if self.generate_btn:
                self.generate_btn.setEnabled(False)
                self.generate_btn.setText("生成中...")
            if self.style_combo:
                self.style_combo.setEnabled(False)
            if self.set_active_btn:
                self.set_active_btn.setEnabled(False)
            if self.delete_btn:
                self.delete_btn.setEnabled(False)
        else:
            # 恢复正常状态
            self.status_label.setStyleSheet(f"""
                QLabel#status_label {{
                    font-size: {sp(12)}px;
                    color: {theme_manager.TEXT_SECONDARY};
                }}
            """)

            # 启用按钮
            if self.generate_btn:
                self.generate_btn.setEnabled(True)
                self.generate_btn.setText("生成")
            if self.style_combo:
                self.style_combo.setEnabled(True)
            if self.set_active_btn:
                self.set_active_btn.setEnabled(True)
            if self.delete_btn:
                self.delete_btn.setEnabled(True)

    def setGenerateSuccess(self):
        """设置生成成功状态"""
        self._is_generating = False
        self.status_label.setText("生成成功!")
        self.status_label.setStyleSheet(f"""
            QLabel#status_label {{
                font-size: {sp(12)}px;
                color: {theme_manager.SUCCESS};
                font-weight: bold;
            }}
        """)

        # 启用按钮
        if self.generate_btn:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("重新生成")
        if self.style_combo:
            self.style_combo.setEnabled(True)

    def setGenerateError(self, error_msg: str = "生成失败"):
        """设置生成失败状态"""
        self._is_generating = False
        self.status_label.setText(error_msg)
        self.status_label.setStyleSheet(f"""
            QLabel#status_label {{
                font-size: {sp(12)}px;
                color: {theme_manager.ERROR};
                font-weight: bold;
            }}
        """)
        self.image_label.setText("生成失败")

        # 启用按钮
        if self.generate_btn:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("重试")
        if self.style_combo:
            self.style_combo.setEnabled(True)
        if self.set_active_btn:
            self.set_active_btn.setEnabled(True)
        if self.delete_btn:
            self.delete_btn.setEnabled(True)

    def _apply_theme(self):
        """应用主题样式"""
        self.setStyleSheet(f"""
            PortraitCard {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {theme_manager.RADIUS_MD};
            }}
            QLabel#character_name {{
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QLabel#status_label {{
                font-size: {sp(12)}px;
                color: {theme_manager.TEXT_SECONDARY};
            }}
            QFrame#image_container {{
                background-color: {theme_manager.BG_TERTIARY};
                border: 1px dashed {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_SM};
            }}
        """)

        if self.generate_btn:
            self.generate_btn.setStyleSheet(ButtonStyles.primary('SM'))
        if self.set_active_btn:
            self.set_active_btn.setStyleSheet(ButtonStyles.secondary('SM'))
        if self.delete_btn:
            self.delete_btn.setStyleSheet(ButtonStyles.danger('SM'))


class CharacterPortraitsWidget(ThemeAwareWidget):
    """角色立绘管理界面"""

    def __init__(self, project_id: str = "", parent=None):
        self.project_id = project_id
        self.characters: List[Dict[str, Any]] = []
        self.portraits: Dict[str, Dict[str, Any]] = {}  # character_name -> portrait_data

        # 组件引用
        self.header_widget = None
        self.count_label = None
        self.refresh_btn = None
        self.scroll_area = None
        self.content_widget = None
        self.content_layout = None
        self.portrait_cards: List[PortraitCard] = []
        self.loading_label = None
        self.status_label = None

        # 工作线程
        self._loading_worker = None
        self._generate_worker = None
        self._generating_character = None  # 当前正在生成的角色名

        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 顶部标题栏
        self._create_header(layout)

        # 状态标签
        self.status_label = QLabel()
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.hide()
        layout.addWidget(self.status_label)

        # 内容区域
        self._create_content_area(layout)

    def _create_header(self, parent_layout):
        """创建标题栏"""
        self.header_widget = QFrame()
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(dp(12))

        # 标题
        title = QLabel("角色立绘")
        title.setObjectName("section_title")
        header_layout.addWidget(title)

        # 数量标签
        self.count_label = QLabel("0 个角色")
        self.count_label.setObjectName("count_label")
        header_layout.addWidget(self.count_label)

        header_layout.addStretch()

        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setObjectName("refresh_btn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._load_data)
        header_layout.addWidget(self.refresh_btn)

        parent_layout.addWidget(self.header_widget)

    def _create_content_area(self, parent_layout):
        """创建内容区域"""
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_layout = QGridLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, dp(8), 0)
        self.content_layout.setSpacing(dp(16))

        # 加载提示
        self.loading_label = QLabel("加载中...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.loading_label, 0, 0)

        self.scroll_area.setWidget(self.content_widget)
        parent_layout.addWidget(self.scroll_area, stretch=1)

    def setProjectId(self, project_id: str):
        """设置项目ID"""
        self.project_id = project_id
        self._load_data()

    def setCharacters(self, characters: List[Dict[str, Any]]):
        """设置角色列表"""
        self.characters = characters
        self._update_display()

    def _load_data(self):
        """加载立绘数据"""
        if not self.project_id:
            return

        self.loading_label.show()
        self.loading_label.setText("加载中...")

        def fetch():
            with AFNAPIClient() as client:
                return client.get_project_portraits(self.project_id)

        self._loading_worker = AsyncWorker(fetch)
        self._loading_worker.success.connect(self._on_data_loaded)
        self._loading_worker.error.connect(self._on_load_error)
        self._loading_worker.start()

    def _on_data_loaded(self, result: Dict[str, Any]):
        """数据加载完成"""
        self.loading_label.hide()
        portraits = result.get('portraits', [])

        # 构建角色名到立绘的映射
        self.portraits = {}
        for p in portraits:
            name = p.get('character_name', '')
            # 只保留激活的立绘
            if p.get('is_active', False) or name not in self.portraits:
                self.portraits[name] = p

        self._update_display()

    def _on_load_error(self, error: str):
        """加载失败"""
        self.loading_label.setText(f"加载失败: {error}")

    def _update_display(self):
        """更新显示"""
        # 清空现有内容
        for card in self.portrait_cards:
            card.deleteLater()
        self.portrait_cards.clear()

        # 隐藏加载标签
        self.loading_label.hide()

        # 更新数量标签
        self.count_label.setText(f"{len(self.characters)} 个角色")

        if not self.characters:
            self.loading_label.setText("暂无角色信息")
            self.loading_label.show()
            return

        # 创建角色卡片
        row, col = 0, 0
        max_cols = 3

        for char in self.characters:
            name = char.get('name', '')
            description = char.get('identity', '') or char.get('personality', '') or ''
            portrait = self.portraits.get(name)

            card = PortraitCard(
                character_name=name,
                character_description=description,
                portrait_data=portrait,
            )
            card.generateRequested.connect(self._on_generate_requested)
            card.setActiveRequested.connect(self._on_set_active_requested)
            card.deleteRequested.connect(self._on_delete_requested)

            self.portrait_cards.append(card)
            self.content_layout.addWidget(card, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # 添加弹性空间
        self.content_layout.setRowStretch(row + 1, 1)
        self.content_layout.setColumnStretch(max_cols, 1)

        self._apply_theme()

    def _find_card_by_name(self, character_name: str) -> Optional[PortraitCard]:
        """根据角色名查找卡片"""
        for card in self.portrait_cards:
            if card.character_name == character_name:
                return card
        return None

    def _on_generate_requested(self, character_name: str):
        """处理生成请求"""
        if not self.project_id:
            return

        # 如果已有生成任务在进行中，提示用户
        if self._generating_character:
            self.status_label.setText(f"请等待 {self._generating_character} 的立绘生成完成")
            self.status_label.show()
            return

        # 找到对应的卡片
        card = self._find_card_by_name(character_name)
        if not card:
            return

        # 获取风格
        style = card.get_selected_style()

        # 设置生成状态
        self._generating_character = character_name
        card.setGenerating(True)

        # 显示全局状态
        self.status_label.setText(f"正在生成 {character_name} 的立绘...")
        self.status_label.show()

        # 找到角色描述
        description = ""
        for char in self.characters:
            if char.get('name') == character_name:
                description = char.get('identity', '') or char.get('personality', '') or ''
                break

        def generate():
            with AFNAPIClient() as client:
                return client.generate_portrait(
                    project_id=self.project_id,
                    character_name=character_name,
                    style=style,
                    character_description=description,
                )

        self._generate_worker = AsyncWorker(generate)
        self._generate_worker.success.connect(self._on_generate_success)
        self._generate_worker.error.connect(self._on_generate_error)
        self._generate_worker.start()

    def _on_generate_success(self, result: Dict[str, Any]):
        """生成成功"""
        character_name = self._generating_character
        self._generating_character = None

        card = self._find_card_by_name(character_name) if character_name else None

        if result.get('success'):
            self.status_label.setText(f"{character_name} 立绘生成成功!")
            if card:
                card.setGenerateSuccess()
            # 延迟刷新数据，让用户看到成功状态
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, self._load_data)
        else:
            error_msg = result.get('error_message', '未知错误')
            self.status_label.setText(f"生成失败: {error_msg}")
            if card:
                card.setGenerateError(f"失败: {error_msg[:20]}...")

    def _on_generate_error(self, error: str):
        """生成失败"""
        character_name = self._generating_character
        self._generating_character = None

        card = self._find_card_by_name(character_name) if character_name else None

        self.status_label.setText(f"生成失败: {error}")
        if card:
            card.setGenerateError("生成失败")

    def _on_set_active_requested(self, portrait_id: str):
        """处理设置激活请求"""
        if not self.project_id or not portrait_id:
            return

        def set_active():
            with AFNAPIClient() as client:
                return client.set_active_portrait(self.project_id, portrait_id)

        worker = AsyncWorker(set_active)
        worker.success.connect(lambda _: self._load_data())
        worker.error.connect(lambda e: self.status_label.setText(f"操作失败: {e}"))
        worker.start()

    def _on_delete_requested(self, portrait_id: str):
        """处理删除请求"""
        if not self.project_id or not portrait_id:
            return

        def delete():
            with AFNAPIClient() as client:
                return client.delete_portrait(self.project_id, portrait_id)

        worker = AsyncWorker(delete)
        worker.success.connect(lambda _: self._load_data())
        worker.error.connect(lambda e: self.status_label.setText(f"删除失败: {e}"))
        worker.start()

    def _apply_theme(self):
        """应用主题样式"""
        from .section_styles import SectionStyles

        self.setStyleSheet(SectionStyles.list_section_stylesheet())
        self.scroll_area.setStyleSheet(SectionStyles.scroll_area_stylesheet())
        self.content_widget.setStyleSheet(SectionStyles.transparent_background())

        if self.refresh_btn:
            self.refresh_btn.setStyleSheet(ButtonStyles.secondary('SM'))

        self.status_label.setStyleSheet(f"""
            QLabel#status_label {{
                color: {theme_manager.TEXT_SECONDARY};
                font-size: {sp(12)}px;
                padding: {dp(8)}px;
            }}
        """)

        for card in self.portrait_cards:
            card.refresh_theme()
