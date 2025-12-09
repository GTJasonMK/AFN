"""
嵌入模型配置管理
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt
from api.client import ArborisAPIClient
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService, confirm
from .embedding_config_dialog import EmbeddingConfigDialog
from .test_result_dialog import TestResultDialog


class EmbeddingSettingsWidget(QWidget):
    """嵌入模型配置管理"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = ArborisAPIClient()
        self.configs = []
        self.providers = []
        self.setupUI()
        self.loadConfigs()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def setupUI(self):
        """初始化UI"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(20))

        # 标题和说明
        header_layout = QVBoxLayout()
        header_layout.setSpacing(dp(8))

        self.title_label = QLabel("嵌入模型配置")
        header_layout.addWidget(self.title_label)

        self.desc_label = QLabel("嵌入模型用于生成文本向量，支持 RAG 检索功能。可选择远程 API 或本地 Ollama。")
        header_layout.addWidget(self.desc_label)

        layout.addLayout(header_layout)

        # 按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(10))

        # 新增按钮
        self.add_btn = QPushButton("新增")
        self.add_btn.clicked.connect(self.createConfig)
        button_layout.addWidget(self.add_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # 配置列表
        self.config_list = QListWidget()
        layout.addWidget(self.config_list)

        # 操作按钮栏
        action_layout = QHBoxLayout()
        action_layout.setSpacing(dp(10))

        # 测试按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self.testSelectedConfig)
        action_layout.addWidget(self.test_btn)

        # 激活按钮
        self.activate_btn = QPushButton("激活")
        self.activate_btn.clicked.connect(self.activateSelectedConfig)
        action_layout.addWidget(self.activate_btn)

        # 编辑按钮
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.clicked.connect(self.editSelectedConfig)
        action_layout.addWidget(self.edit_btn)

        # 删除按钮
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.deleteSelectedConfig)
        action_layout.addWidget(self.delete_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # 初始状态禁用操作按钮
        self.updateActionButtons()

        # 连接选择变化信号
        self.config_list.itemSelectionChanged.connect(self.updateActionButtons)

        # 应用样式
        self._apply_styles()

    def _apply_styles(self):
        """应用主题样式"""
        ui_font = theme_manager.ui_font()

        # 标题样式
        self.title_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(24)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)

        # 描述样式
        self.desc_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(13)}px;
            color: {theme_manager.TEXT_SECONDARY};
        """)

        # 按钮样式
        btn_style = ButtonStyles.secondary()
        self.add_btn.setStyleSheet(btn_style)
        self.test_btn.setStyleSheet(btn_style)
        self.activate_btn.setStyleSheet(btn_style)
        self.edit_btn.setStyleSheet(btn_style)
        self.delete_btn.setStyleSheet(ButtonStyles.outline_danger())

        # 配置列表样式
        self.config_list.setStyleSheet(f"""
            QListWidget {{
                font-family: {ui_font};
                background-color: {theme_manager.BG_SECONDARY};
                border: 1px solid {theme_manager.BORDER_DEFAULT};
                border-radius: {dp(4)}px;
                padding: {dp(10)}px;
            }}
            QListWidget::item {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {dp(4)}px;
                padding: {dp(15)}px;
                margin: {dp(5)}px;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {theme_manager.PRIMARY_PALE};
                border-color: {theme_manager.PRIMARY};
            }}
        """)

    def loadConfigs(self):
        """加载配置列表"""
        try:
            self.configs = self.api_client.get_embedding_configs()
            self.renderConfigs()
        except Exception as e:
            MessageService.show_error(self, f"加载配置失败: {str(e)}", "错误")

    def renderConfigs(self):
        """渲染配置列表"""
        self.config_list.clear()

        for config in self.configs:
            item_text = self.formatConfigText(config)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, config)
            self.config_list.addItem(item)

    def formatConfigText(self, config):
        """格式化配置显示文本"""
        name = config.get('config_name', '未命名')
        is_active = config.get('is_active', False)
        provider = config.get('provider', 'openai')
        model = config.get('model_name', '(默认)')
        url = config.get('api_base_url', '(默认)')
        vector_size = config.get('vector_size')

        provider_name = "OpenAI/兼容API" if provider == "openai" else "Ollama本地"
        status = " [当前激活]" if is_active else ""
        dim_info = f" | 维度: {vector_size}" if vector_size else ""

        return f"{name}{status}\n{provider_name} | {model}{dim_info}\n{url}"

    def updateActionButtons(self):
        """更新操作按钮状态"""
        has_selection = len(self.config_list.selectedItems()) > 0

        self.test_btn.setEnabled(has_selection)
        self.activate_btn.setEnabled(has_selection)
        self.edit_btn.setEnabled(has_selection)

        # 删除按钮特殊处理（不能删除激活的配置）
        if has_selection:
            selected_item = self.config_list.selectedItems()[0]
            config = selected_item.data(Qt.ItemDataRole.UserRole)
            is_active = config.get('is_active', False)
            self.delete_btn.setEnabled(not is_active)
        else:
            self.delete_btn.setEnabled(False)

    def getSelectedConfig(self):
        """获取选中的配置"""
        items = self.config_list.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        return None

    def createConfig(self):
        """创建新配置"""
        dialog = EmbeddingConfigDialog(providers=self.providers, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                MessageService.show_warning(self, "配置名称不能为空", "提示")
                return

            try:
                self.api_client.create_embedding_config(data)
                MessageService.show_success(self, "配置创建成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"创建失败: {str(e)}", "错误")

    def editSelectedConfig(self):
        """编辑选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        dialog = EmbeddingConfigDialog(config=config, providers=self.providers, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                MessageService.show_warning(self, "配置名称不能为空", "提示")
                return

            try:
                self.api_client.update_embedding_config(config['id'], data)
                MessageService.show_success(self, "配置更新成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"更新失败: {str(e)}", "错误")

    def deleteSelectedConfig(self):
        """删除选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        if confirm(self, f"确定要删除配置 \"{config['config_name']}\" 吗?", "确认删除"):
            try:
                self.api_client.delete_embedding_config(config['id'])
                MessageService.show_success(self, "配置已删除")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"删除失败: {str(e)}", "错误")

    def activateSelectedConfig(self):
        """激活选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        try:
            self.api_client.activate_embedding_config(config['id'])
            MessageService.show_success(self, f"已激活配置: {config['config_name']}")
            self.loadConfigs()
        except Exception as e:
            MessageService.show_error(self, f"激活失败: {str(e)}", "错误")

    def testSelectedConfig(self):
        """测试选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        try:
            # 禁用按钮
            self.test_btn.setEnabled(False)
            self.test_btn.setText("测试中...")

            # 调用API测试
            result = self.api_client.test_embedding_config(config['id'])

            # 解析结果
            success = result.get('success', False)
            message = result.get('message', '')
            details = {
                'response_time_ms': result.get('response_time_ms'),
                'vector_dimension': result.get('vector_dimension'),
                'model_info': result.get('model_info'),
            }

            # 显示结果对话框
            dialog = TestResultDialog(success, message, details, parent=self)
            dialog.exec()

            # 刷新列表以显示更新的向量维度
            self.loadConfigs()

        except Exception as e:
            TestResultDialog(False, f"连接失败: {str(e)}", parent=self).exec()

        finally:
            # 恢复按钮
            self.test_btn.setEnabled(True)
            self.test_btn.setText("测试连接")
