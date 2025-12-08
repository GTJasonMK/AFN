"""
LLM配置管理 - 极简版本
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog
)
from PyQt6.QtCore import Qt
from api.client import ArborisAPIClient
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService, confirm
from .config_dialog import LLMConfigDialog
from .test_result_dialog import TestResultDialog
import json


class LLMSettingsWidget(QWidget):
    """LLM配置管理 - 极简风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = ArborisAPIClient()
        self.configs = []
        self.testing_config_id = None
        self.setupUI()
        self.loadConfigs()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def setupUI(self):
        """初始化极简UI"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(dp(20), dp(20), dp(20), dp(20))
        layout.setSpacing(dp(20))

        # 标题
        self.title_label = QLabel("LLM 配置")
        layout.addWidget(self.title_label)

        # 按钮栏
        button_layout = QHBoxLayout()
        button_layout.setSpacing(dp(10))

        # 新增按钮
        self.add_btn = QPushButton("新增")
        self.add_btn.clicked.connect(self.createConfig)
        button_layout.addWidget(self.add_btn)

        # 导入按钮
        self.import_btn = QPushButton("导入")
        self.import_btn.clicked.connect(self.importConfigs)
        button_layout.addWidget(self.import_btn)

        # 导出全部按钮
        self.export_all_btn = QPushButton("导出全部")
        self.export_all_btn.clicked.connect(self.exportAll)
        button_layout.addWidget(self.export_all_btn)

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

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self.exportSelectedConfig)
        action_layout.addWidget(self.export_btn)

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
        """应用主题样式（主题切换时调用）"""
        ui_font = theme_manager.ui_font()

        # 标题样式
        self.title_label.setStyleSheet(f"""
            font-family: {ui_font};
            font-size: {sp(24)}px;
            font-weight: bold;
            color: {theme_manager.TEXT_PRIMARY};
        """)

        # 按钮样式
        btn_style = self.getButtonStyle()
        self.add_btn.setStyleSheet(btn_style)
        self.import_btn.setStyleSheet(btn_style)
        self.export_all_btn.setStyleSheet(btn_style)
        self.test_btn.setStyleSheet(btn_style)
        self.activate_btn.setStyleSheet(btn_style)
        self.edit_btn.setStyleSheet(btn_style)
        self.export_btn.setStyleSheet(btn_style)
        self.delete_btn.setStyleSheet(self.getDeleteButtonStyle())

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

    def getButtonStyle(self):
        """获取标准按钮样式"""
        return ButtonStyles.secondary()

    def getDeleteButtonStyle(self):
        """获取删除按钮样式"""
        return ButtonStyles.outline_danger()

    def loadConfigs(self):
        """加载配置列表"""
        try:
            self.configs = self.api_client.get_llm_configs()
            self.renderConfigs()
        except Exception as e:
            MessageService.show_error(self, f"加载配置失败：{str(e)}", "错误")

    def renderConfigs(self):
        """渲染配置列表"""
        self.config_list.clear()

        for config in self.configs:
            # 创建列表项
            item_text = self.formatConfigText(config)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, config)
            self.config_list.addItem(item)

    def formatConfigText(self, config):
        """格式化配置显示文本"""
        name = config.get('config_name', '未命名')
        is_active = config.get('is_active', False)
        url = config.get('llm_provider_url', '(默认)')
        model = config.get('llm_provider_model', '(默认)')

        status = " [当前激活]" if is_active else ""
        return f"{name}{status}\n{url}\n模型: {model}"

    def updateActionButtons(self):
        """更新操作按钮状态"""
        has_selection = len(self.config_list.selectedItems()) > 0

        self.test_btn.setEnabled(has_selection)
        self.activate_btn.setEnabled(has_selection)
        self.edit_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)

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
        dialog = LLMConfigDialog(parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                MessageService.show_warning(self, "配置名称不能为空", "提示")
                return

            try:
                self.api_client.create_llm_config(data)
                MessageService.show_success(self, "配置创建成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"创建失败：{str(e)}", "错误")

    def editSelectedConfig(self):
        """编辑选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        dialog = LLMConfigDialog(config=config, parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get('config_name'):
                MessageService.show_warning(self, "配置名称不能为空", "提示")
                return

            try:
                self.api_client.update_llm_config(config['id'], data)
                MessageService.show_success(self, "配置更新成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"更新失败：{str(e)}", "错误")

    def deleteSelectedConfig(self):
        """删除选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        if confirm(self, f"确定要删除配置 \"{config['config_name']}\" 吗？", "确认删除"):
            try:
                self.api_client.delete_llm_config(config['id'])
                MessageService.show_success(self, "配置已删除")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"删除失败：{str(e)}", "错误")

    def activateSelectedConfig(self):
        """激活选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        try:
            self.api_client.activate_llm_config(config['id'])
            MessageService.show_success(self, f"已激活配置：{config['config_name']}")
            self.loadConfigs()
        except Exception as e:
            MessageService.show_error(self, f"激活失败：{str(e)}", "错误")

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
            result = self.api_client.test_llm_config(config['id'])

            # 解析结果
            success = result.get('success', False)
            message = result.get('message', '')
            details = result.get('details', {})

            # 显示结果对话框
            dialog = TestResultDialog(success, message, details, parent=self)
            dialog.exec()

        except Exception as e:
            TestResultDialog(False, f"连接失败：{str(e)}", parent=self).exec()

        finally:
            # 恢复按钮
            self.test_btn.setEnabled(True)
            self.test_btn.setText("测试连接")

    def exportSelectedConfig(self):
        """导出选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出配置",
            f"{config['config_name']}.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                export_data = self.api_client.export_llm_config(config['id'])
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"导出失败：{str(e)}", "错误")

    def exportAll(self):
        """导出所有配置"""
        if not self.configs:
            MessageService.show_warning(self, "没有可导出的配置", "提示")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出所有配置",
            "llm_configs.json",
            "JSON文件 (*.json)"
        )

        if file_path:
            try:
                export_data = self.api_client.export_llm_configs()
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                config_count = len(export_data.get('configs', []))
                MessageService.show_operation_success(self, "导出", f"已导出 {config_count} 个配置到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"导出失败：{str(e)}", "错误")

    def importConfigs(self):
        """导入置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
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

                if 'configs' not in import_data:
                    MessageService.show_warning(self, "导入文件缺少 'configs' 字段", "格式错误")
                    return

                result = self.api_client.import_llm_configs(import_data)
                MessageService.show_success(self, "成功导入配置")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, f"导入失败：{str(e)}", "错误")
