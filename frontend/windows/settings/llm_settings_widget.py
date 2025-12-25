"""
LLM配置管理 - 书籍风格
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QFileDialog, QFrame
)
from PyQt6.QtCore import Qt
from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.dpi_utils import dp, sp
from utils.message_service import MessageService, confirm
from utils.async_worker import AsyncAPIWorker
from .config_dialog import LLMConfigDialog
from .test_result_dialog import TestResultDialog
import json


class LLMSettingsWidget(QWidget):
    """LLM配置管理 - 书籍风格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.configs = []
        self.testing_config_id = None
        self._test_worker = None  # 异步测试Worker
        self._create_ui_structure()
        self._apply_styles()
        self.loadConfigs()

        # 连接主题切换信号
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        # 顶部操作栏
        top_bar = QHBoxLayout()
        top_bar.setSpacing(dp(12))

        # 新增按钮（主要操作）
        self.add_btn = QPushButton("+ 新增配置")
        self.add_btn.setObjectName("primary_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.createConfig)
        top_bar.addWidget(self.add_btn)

        # 导入按钮
        self.import_btn = QPushButton("导入")
        self.import_btn.setObjectName("secondary_btn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self.importConfigs)
        top_bar.addWidget(self.import_btn)

        # 导出全部按钮
        self.export_all_btn = QPushButton("导出全部")
        self.export_all_btn.setObjectName("secondary_btn")
        self.export_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_all_btn.clicked.connect(self.exportAll)
        top_bar.addWidget(self.export_all_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # 配置列表
        self.config_list = QListWidget()
        self.config_list.setObjectName("config_list")
        self.config_list.setMinimumHeight(dp(240))
        layout.addWidget(self.config_list, stretch=1)

        # 底部操作按钮栏
        action_bar = QHBoxLayout()
        action_bar.setSpacing(dp(12))

        # 测试按钮
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setObjectName("secondary_btn")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self.testSelectedConfig)
        action_bar.addWidget(self.test_btn)

        # 激活按钮
        self.activate_btn = QPushButton("激活")
        self.activate_btn.setObjectName("secondary_btn")
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.clicked.connect(self.activateSelectedConfig)
        action_bar.addWidget(self.activate_btn)

        # 编辑按钮
        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setObjectName("secondary_btn")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self.editSelectedConfig)
        action_bar.addWidget(self.edit_btn)

        # 导出按钮
        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("secondary_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.exportSelectedConfig)
        action_bar.addWidget(self.export_btn)

        action_bar.addStretch()

        # 删除按钮（放右侧，危险操作）
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("danger_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.deleteSelectedConfig)
        action_bar.addWidget(self.delete_btn)

        layout.addLayout(action_bar)

        # 初始状态禁用操作按钮
        self.updateActionButtons()

        # 连接选择变化信号
        self.config_list.itemSelectionChanged.connect(self.updateActionButtons)

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 主要按钮（新增配置）
        self.add_btn.setStyleSheet(f"""
            QPushButton#primary_btn {{
                font-family: {palette.ui_font};
                background-color: {palette.accent_color};
                color: {palette.bg_primary};
                border: none;
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(24)}px;  /* 修正：10和20不符合8pt网格 */
                font-size: {sp(13)}px;
                font-weight: 600;
            }}
            QPushButton#primary_btn:hover {{
                background-color: {palette.text_primary};
            }}
            QPushButton#primary_btn:pressed {{
                background-color: {palette.accent_light};
            }}
        """)

        # 次要按钮样式
        secondary_style = f"""
            QPushButton#secondary_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {palette.text_secondary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton#secondary_btn:hover {{
                color: {palette.accent_color};
                border-color: {palette.accent_color};
                background-color: {palette.bg_primary};
            }}
            QPushButton#secondary_btn:disabled {{
                color: {palette.border_color};
                border-color: {palette.border_color};
            }}
        """

        for btn in [self.import_btn, self.export_all_btn, self.test_btn,
                    self.activate_btn, self.edit_btn, self.export_btn]:
            btn.setStyleSheet(secondary_style)

        # 删除按钮样式（危险操作）
        self.delete_btn.setStyleSheet(f"""
            QPushButton#danger_btn {{
                font-family: {palette.ui_font};
                background-color: transparent;
                color: {theme_manager.ERROR};
                border: 1px solid {theme_manager.ERROR_LIGHT};
                border-radius: {dp(6)}px;
                padding: {dp(8)}px {dp(16)}px;
                font-size: {sp(13)}px;
                font-weight: 500;
            }}
            QPushButton#danger_btn:hover {{
                background-color: {theme_manager.ERROR};
                color: {theme_manager.BUTTON_TEXT};
                border-color: {theme_manager.ERROR};
            }}
            QPushButton#danger_btn:disabled {{
                color: {palette.border_color};
                border-color: {palette.border_color};
            }}
        """)

        # 配置列表样式 - 优化质感
        self.config_list.setStyleSheet(f"""
            QListWidget#config_list {{
                font-family: {palette.ui_font};
                background-color: {palette.bg_primary};
                border: 1px solid {palette.border_color};
                border-radius: {dp(8)}px;
                padding: {dp(8)}px;
                outline: none;
            }}
            QListWidget#config_list::item {{
                background-color: transparent;
                border: none;
                border-left: 3px solid transparent;
                border-radius: 0;
                padding: {dp(16)}px {dp(12)}px;  /* 修正：14不符合8pt网格，改为16 */
                margin: 0;
                color: {palette.text_primary};
                border-bottom: 1px solid {palette.border_color};
            }}
            QListWidget#config_list::item:last-child {{
                border-bottom: none;
            }}
            QListWidget#config_list::item:hover {{
                background-color: {palette.bg_secondary};
                border-left: 3px solid {palette.accent_light};
            }}
            QListWidget#config_list::item:selected {{
                background-color: {palette.bg_secondary};
                border-left: 3px solid {palette.accent_color};
                color: {palette.text_primary};
            }}
            QScrollBar:vertical {{
                background-color: transparent;
                width: {dp(6)}px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background-color: {palette.border_color};
                border-radius: {dp(3)}px;
                min-height: {dp(30)}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {palette.text_secondary};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        # 强制刷新样式缓存
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

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
        """测试选中的配置（异步）"""
        config = self.getSelectedConfig()
        if not config:
            return

        # 清理之前的worker
        self._cleanup_test_worker()

        # 禁用按钮，显示测试中状态
        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")

        # 异步调用API测试
        self._test_worker = AsyncAPIWorker(
            self.api_client.test_llm_config,
            config['id']
        )
        self._test_worker.success.connect(self._on_test_success)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.start()

    def _on_test_success(self, result: dict):
        """测试成功回调"""
        # 恢复按钮状态
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")

        # 解析结果
        success = result.get('success', False)
        message = result.get('message', '')
        details = result.get('details', {})

        # 显示结果对话框
        dialog = TestResultDialog(success, message, details, parent=self)
        dialog.exec()

    def _on_test_error(self, error_msg: str):
        """测试失败回调"""
        # 恢复按钮状态
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")

        # 显示错误对话框
        TestResultDialog(False, f"连接失败: {error_msg}", parent=self).exec()

    def _cleanup_test_worker(self):
        """清理测试Worker"""
        if self._test_worker is not None:
            try:
                if self._test_worker.isRunning():
                    self._test_worker.cancel()
                    self._test_worker.quit()
                    self._test_worker.wait(3000)
            except RuntimeError:
                pass
            finally:
                self._test_worker = None

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

    def __del__(self):
        """析构时断开主题信号连接并清理worker"""
        self._cleanup_test_worker()
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
