"""
队列配置管理 - 书籍风格

提供LLM和图片生成队列的配置调整和状态监控。
"""

import logging
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QFrame, QGridLayout, QGroupBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class QueueSettingsWidget(QWidget):
    """队列配置管理 - 书籍风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()

        # 状态刷新定时器
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_status)
        self._refresh_interval = 2000  # 2秒刷新一次

        self._create_ui_structure()
        self._apply_styles()
        self._load_config()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(24))

        # LLM队列配置卡片
        llm_group = self._create_queue_card(
            title="LLM 请求队列",
            description="控制大语言模型API调用的并发数量。\n增加并发数可以加快生成速度，但可能触发API限流。",
            min_val=1,
            max_val=10,
            default_val=3,
        )
        self.llm_spinbox = llm_group.findChild(QSpinBox, "llm_spinbox")
        self.llm_active_label = llm_group.findChild(QLabel, "llm_active")
        self.llm_waiting_label = llm_group.findChild(QLabel, "llm_waiting")
        self.llm_total_label = llm_group.findChild(QLabel, "llm_total")
        self.llm_apply_btn = llm_group.findChild(QPushButton, "llm_apply")
        self.llm_apply_btn.clicked.connect(self._apply_llm_config)
        layout.addWidget(llm_group)

        # 图片生成队列配置卡片
        image_group = self._create_queue_card(
            title="图片生成队列",
            description="控制图片生成API调用的并发数量。\n图片生成通常较慢，建议保持较低的并发数。",
            min_val=1,
            max_val=5,
            default_val=2,
            prefix="image",
        )
        self.image_spinbox = image_group.findChild(QSpinBox, "image_spinbox")
        self.image_active_label = image_group.findChild(QLabel, "image_active")
        self.image_waiting_label = image_group.findChild(QLabel, "image_waiting")
        self.image_total_label = image_group.findChild(QLabel, "image_total")
        self.image_apply_btn = image_group.findChild(QPushButton, "image_apply")
        self.image_apply_btn.clicked.connect(self._apply_image_config)
        layout.addWidget(image_group)

        # 底部说明
        hint_label = QLabel(
            "提示: 队列状态每2秒自动刷新。修改配置后会立即生效并保存。"
        )
        hint_label.setObjectName("hint_label")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # 导入导出按钮行
        io_bar = QHBoxLayout()
        io_bar.setSpacing(dp(12))

        self.import_btn = QPushButton("导入配置")
        self.import_btn.setObjectName("secondary_btn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self._import_config)
        io_bar.addWidget(self.import_btn)

        self.export_btn = QPushButton("导出配置")
        self.export_btn.setObjectName("secondary_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._export_config)
        io_bar.addWidget(self.export_btn)

        io_bar.addStretch()
        layout.addLayout(io_bar)

        layout.addStretch()

    def _create_queue_card(
        self,
        title: str,
        description: str,
        min_val: int,
        max_val: int,
        default_val: int,
        prefix: str = "llm",
    ) -> QGroupBox:
        """创建队列配置卡片"""
        group = QGroupBox(title)
        group.setObjectName("queue_card")

        layout = QVBoxLayout(group)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        # 描述文本
        desc_label = QLabel(description)
        desc_label.setObjectName("description")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        # 配置行
        config_row = QHBoxLayout()
        config_row.setSpacing(dp(12))

        config_label = QLabel("最大并发数:")
        config_row.addWidget(config_label)

        spinbox = QSpinBox()
        spinbox.setObjectName(f"{prefix}_spinbox")
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default_val)
        spinbox.setMinimumWidth(dp(80))
        config_row.addWidget(spinbox)

        apply_btn = QPushButton("应用")
        apply_btn.setObjectName(f"{prefix}_apply")
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        config_row.addWidget(apply_btn)

        config_row.addStretch()
        layout.addLayout(config_row)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        layout.addWidget(line)

        # 状态显示
        status_label = QLabel("当前状态")
        status_label.setObjectName("status_title")
        layout.addWidget(status_label)

        status_grid = QGridLayout()
        status_grid.setSpacing(dp(8))

        # 执行中
        active_title = QLabel("执行中:")
        active_value = QLabel("0")
        active_value.setObjectName(f"{prefix}_active")
        status_grid.addWidget(active_title, 0, 0)
        status_grid.addWidget(active_value, 0, 1)

        # 等待中
        waiting_title = QLabel("等待中:")
        waiting_value = QLabel("0")
        waiting_value.setObjectName(f"{prefix}_waiting")
        status_grid.addWidget(waiting_title, 0, 2)
        status_grid.addWidget(waiting_value, 0, 3)

        # 已处理
        total_title = QLabel("已处理:")
        total_value = QLabel("0")
        total_value.setObjectName(f"{prefix}_total")
        status_grid.addWidget(total_title, 0, 4)
        status_grid.addWidget(total_value, 0, 5)

        status_grid.setColumnStretch(6, 1)
        layout.addLayout(status_grid)

        return group

    def _apply_styles(self):
        """应用样式"""
        palette = theme_manager.get_book_palette()

        self.setStyleSheet(f"""
            QGroupBox#queue_card {{
                font-family: {palette.ui_font};
                font-size: {sp(14)}px;
                font-weight: bold;
                color: {palette.text_primary};
                background-color: {palette.bg_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                margin-top: {dp(8)}px;
                padding-top: {dp(16)}px;
            }}

            QGroupBox#queue_card::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 {dp(8)}px;
                color: {palette.text_primary};
            }}

            QLabel#description {{
                color: {palette.text_secondary};
                font-size: {sp(12)}px;
                line-height: 1.4;
            }}

            QLabel#status_title {{
                color: {palette.text_primary};
                font-size: {sp(13)}px;
                font-weight: bold;
            }}

            QLabel#hint_label {{
                color: {palette.text_secondary};
                font-size: {sp(11)}px;
                font-style: italic;
            }}

            QSpinBox {{
                background-color: {palette.bg_primary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(4)}px;
                padding: {dp(4)}px {dp(8)}px;
                color: {palette.text_primary};
                font-size: {sp(13)}px;
            }}

            QSpinBox:focus {{
                border-color: {palette.accent_color};
            }}

            QPushButton {{
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(4)}px;
                padding: {dp(6)}px {dp(16)}px;
                font-size: {sp(13)}px;
            }}

            QPushButton:hover {{
                background-color: {palette.text_primary};
            }}

            QPushButton:pressed {{
                background-color: {palette.text_secondary};
            }}

            QPushButton#secondary_btn {{
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
            }}

            QPushButton#secondary_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_primary};
            }}

            QFrame#separator {{
                background-color: {palette.border_color};
                max-height: 1px;
            }}
        """)

    def _load_config(self):
        """加载当前配置"""
        try:
            config = self.api_client.get_queue_config()
            self.llm_spinbox.setValue(config.get("llm_max_concurrent", 3))
            self.image_spinbox.setValue(config.get("image_max_concurrent", 2))
            logger.debug("队列配置加载成功: %s", config)
        except Exception as e:
            logger.warning("加载队列配置失败: %s", e)

        # 加载状态
        self._refresh_status()

    def _refresh_status(self):
        """刷新队列状态"""
        try:
            status = self.api_client.get_queue_status()

            # 更新LLM状态
            llm = status.get("llm", {})
            self.llm_active_label.setText(str(llm.get("active", 0)))
            self.llm_waiting_label.setText(str(llm.get("waiting", 0)))
            self.llm_total_label.setText(str(llm.get("total_processed", 0)))

            # 更新图片状态
            image = status.get("image", {})
            self.image_active_label.setText(str(image.get("active", 0)))
            self.image_waiting_label.setText(str(image.get("waiting", 0)))
            self.image_total_label.setText(str(image.get("total_processed", 0)))

        except Exception as e:
            logger.debug("刷新队列状态失败: %s", e)

    def _apply_llm_config(self):
        """应用LLM队列配置"""
        value = self.llm_spinbox.value()
        try:
            self.api_client.update_queue_config(llm_max_concurrent=value)
            MessageService.show_info(self, f"LLM队列并发数已设置为 {value}")
            logger.info("LLM队列并发数已更新为: %d", value)
        except Exception as e:
            MessageService.show_error(self, f"设置失败: {e}")
            logger.error("更新LLM队列配置失败: %s", e)

    def _apply_image_config(self):
        """应用图片队列配置"""
        value = self.image_spinbox.value()
        try:
            self.api_client.update_queue_config(image_max_concurrent=value)
            MessageService.show_info(self, f"图片队列并发数已设置为 {value}")
            logger.info("图片队列并发数已更新为: %d", value)
        except Exception as e:
            MessageService.show_error(self, f"设置失败: {e}")
            logger.error("更新图片队列配置失败: %s", e)

    def showEvent(self, event):
        """显示时启动定时刷新"""
        super().showEvent(event)
        self._refresh_status()
        self._refresh_timer.start(self._refresh_interval)

    def hideEvent(self, event):
        """隐藏时停止定时刷新"""
        super().hideEvent(event)
        self._refresh_timer.stop()

    def _export_config(self):
        """导出队列配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出队列配置",
            "queue_config.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                export_data = self.api_client.export_queue_config()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                MessageService.show_info(self, f"配置已导出到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"导出失败：{str(e)}")
                logger.error("导出队列配置失败: %s", e)

    def _import_config(self):
        """导入队列配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入队列配置",
            "",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                # 验证数据格式
                if not isinstance(import_data, dict):
                    MessageService.show_warning(self, "导入文件格式不正确", "格式错误")
                    return

                if import_data.get('export_type') != 'queue':
                    MessageService.show_warning(self, "导入文件类型不正确，需要队列配置导出文件", "格式错误")
                    return

                result = self.api_client.import_queue_config(import_data)
                if result.get('success'):
                    MessageService.show_info(self, result.get('message', '导入成功'))
                    self._load_config()  # 重新加载配置到UI
                else:
                    MessageService.show_error(self, result.get('message', '导入失败'))
            except Exception as e:
                MessageService.show_error(self, f"导入失败：{str(e)}")
                logger.error("导入队列配置失败: %s", e)
