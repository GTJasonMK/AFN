"""
通用配置列表基类

抽取 LLM/嵌入/图片配置页的公共 UI 与 CRUD/导入导出/测试逻辑。
"""

from typing import Any, Dict, List, Tuple
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api.manager import APIClientManager
from themes.theme_manager import theme_manager
from utils.async_worker import AsyncAPIWorker
from utils.dpi_utils import dp
from utils.message_service import MessageService, confirm
from .dialogs import TestResultDialog


class BaseConfigListWidget(QWidget):
    """配置列表页通用基类"""

    config_name_required_message = "配置名称不能为空"
    delete_confirm_title = "确认删除"
    delete_confirm_template = "确定要删除配置 \"{name}\" 吗？"
    activate_success_template = "已激活配置：{name}"
    test_button_text = "测试连接"
    test_loading_text = "测试中..."

    error_message_templates = {
        "load": "加载配置失败：{error}",
        "create": "创建失败：{error}",
        "update": "更新失败：{error}",
        "delete": "删除失败：{error}",
        "activate": "激活失败：{error}",
        "export": "导出失败：{error}",
        "import": "导入失败：{error}",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_client = APIClientManager.get_client()
        self.configs: List[Dict[str, Any]] = []
        self._test_worker = None
        self._create_ui_structure()
        self._apply_styles()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self, theme_name: str):
        """主题切换时更新样式"""
        self._apply_styles()

    def _create_ui_structure(self):
        """创建UI结构"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(16))

        top_bar = QHBoxLayout()
        top_bar.setSpacing(dp(12))

        self.add_btn = QPushButton("+ 新增配置")
        self.add_btn.setObjectName("primary_btn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.createConfig)
        top_bar.addWidget(self.add_btn)

        self.import_btn = QPushButton("导入")
        self.import_btn.setObjectName("secondary_btn")
        self.import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.import_btn.clicked.connect(self.importConfigs)
        top_bar.addWidget(self.import_btn)

        self.export_all_btn = QPushButton("导出全部")
        self.export_all_btn.setObjectName("secondary_btn")
        self.export_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_all_btn.clicked.connect(self.exportAll)
        top_bar.addWidget(self.export_all_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.config_list = QListWidget()
        self.config_list.setObjectName("config_list")
        self.config_list.setMinimumHeight(dp(240))
        layout.addWidget(self.config_list, stretch=1)

        action_bar = QHBoxLayout()
        action_bar.setSpacing(dp(12))

        self.test_btn = QPushButton(self.test_button_text)
        self.test_btn.setObjectName("secondary_btn")
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self.testSelectedConfig)
        action_bar.addWidget(self.test_btn)

        self.activate_btn = QPushButton("激活")
        self.activate_btn.setObjectName("secondary_btn")
        self.activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.activate_btn.clicked.connect(self.activateSelectedConfig)
        action_bar.addWidget(self.activate_btn)

        self.edit_btn = QPushButton("编辑")
        self.edit_btn.setObjectName("secondary_btn")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_btn.clicked.connect(self.editSelectedConfig)
        action_bar.addWidget(self.edit_btn)

        self.export_btn = QPushButton("导出")
        self.export_btn.setObjectName("secondary_btn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self.exportSelectedConfig)
        action_bar.addWidget(self.export_btn)

        action_bar.addStretch()

        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("danger_btn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(self.deleteSelectedConfig)
        action_bar.addWidget(self.delete_btn)

        layout.addLayout(action_bar)

        self.updateActionButtons()
        self.config_list.itemSelectionChanged.connect(self.updateActionButtons)

    def _apply_styles(self):
        raise NotImplementedError

    def fetch_configs(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def formatConfigText(self, config: Dict[str, Any]) -> str:
        raise NotImplementedError

    def create_config_dialog(self, config: Dict[str, Any] = None):
        raise NotImplementedError

    def create_config(self, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def update_config(self, config_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def delete_config(self, config_id: int) -> Any:
        raise NotImplementedError

    def activate_config(self, config_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    def test_config(self, config_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    def export_config(self, config_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    def export_configs(self) -> Dict[str, Any]:
        raise NotImplementedError

    def import_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_export_all_filename(self) -> str:
        raise NotImplementedError

    def build_test_dialog_payload(self, result: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        return (
            result.get("success", False),
            result.get("message", ""),
            result.get("details", {}),
        )

    def handle_test_success(self, result: Dict[str, Any]):
        success, message, details = self.build_test_dialog_payload(result)
        TestResultDialog(success, message, details, parent=self).exec()

    def handle_test_error(self, error_msg: str):
        TestResultDialog(False, f"连接失败: {error_msg}", parent=self).exec()

    def after_test_success(self, result: Dict[str, Any]):
        """测试成功后的额外处理"""

    def handle_import_success(self, result: Dict[str, Any]):
        MessageService.show_success(self, result.get("message", "导入成功"))

    def get_delete_confirm_text(self, config: Dict[str, Any]) -> str:
        return self.delete_confirm_template.format(name=config.get("config_name", ""))

    def _format_error_message(self, action: str, error: Exception) -> str:
        template = self.error_message_templates.get(action, "{error}")
        return template.format(error=str(error))

    def _set_test_loading(self):
        self.test_btn.setEnabled(False)
        self.test_btn.setText(self.test_loading_text)

    def _reset_test_button(self):
        self.test_btn.setEnabled(True)
        self.test_btn.setText(self.test_button_text)

    def loadConfigs(self):
        """加载配置列表"""
        try:
            self.configs = self.fetch_configs()
            self.renderConfigs()
        except Exception as e:
            MessageService.show_error(self, self._format_error_message("load", e), "错误")

    def renderConfigs(self):
        """渲染配置列表"""
        self.config_list.clear()
        for config in self.configs:
            item_text = self.formatConfigText(config)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, config)
            self.config_list.addItem(item)

    def updateActionButtons(self):
        """更新操作按钮状态"""
        has_selection = len(self.config_list.selectedItems()) > 0
        self.test_btn.setEnabled(has_selection)
        self.activate_btn.setEnabled(has_selection)
        self.edit_btn.setEnabled(has_selection)
        self.export_btn.setEnabled(has_selection)

        if has_selection:
            selected_item = self.config_list.selectedItems()[0]
            config = selected_item.data(Qt.ItemDataRole.UserRole)
            is_active = config.get("is_active", False)
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
        dialog = self.create_config_dialog()
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get("config_name"):
                MessageService.show_warning(self, self.config_name_required_message, "提示")
                return
            try:
                self.create_config(data)
                MessageService.show_success(self, "配置创建成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, self._format_error_message("create", e), "错误")

    def editSelectedConfig(self):
        """编辑选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return

        dialog = self.create_config_dialog(config=config)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.getData()
            if not data.get("config_name"):
                MessageService.show_warning(self, self.config_name_required_message, "提示")
                return
            try:
                self.update_config(config["id"], data)
                MessageService.show_success(self, "配置更新成功")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, self._format_error_message("update", e), "错误")

    def deleteSelectedConfig(self):
        """删除选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return
        if confirm(self, self.get_delete_confirm_text(config), self.delete_confirm_title):
            try:
                self.delete_config(config["id"])
                MessageService.show_success(self, "配置已删除")
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, self._format_error_message("delete", e), "错误")

    def activateSelectedConfig(self):
        """激活选中的配置"""
        config = self.getSelectedConfig()
        if not config:
            return
        try:
            self.activate_config(config["id"])
            MessageService.show_success(
                self,
                self.activate_success_template.format(name=config.get("config_name", "")),
            )
            self.loadConfigs()
        except Exception as e:
            MessageService.show_error(self, self._format_error_message("activate", e), "错误")

    def testSelectedConfig(self):
        """测试选中的配置（异步）"""
        config = self.getSelectedConfig()
        if not config:
            return
        self._cleanup_test_worker()
        self._set_test_loading()
        self._test_worker = AsyncAPIWorker(self.test_config, config["id"])
        self._test_worker.success.connect(self._on_test_success)
        self._test_worker.error.connect(self._on_test_error)
        self._test_worker.start()

    def _on_test_success(self, result: Dict[str, Any]):
        self._reset_test_button()
        self.handle_test_success(result)
        self.after_test_success(result)

    def _on_test_error(self, error_msg: str):
        self._reset_test_button()
        self.handle_test_error(error_msg)

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
            f"{config.get('config_name', 'config')}.json",
            "JSON文件 (*.json)",
        )
        if file_path:
            try:
                export_data = self.export_config(config["id"])
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, self._format_error_message("export", e), "错误")

    def exportAll(self):
        """导出所有配置"""
        if not self.configs:
            MessageService.show_warning(self, "没有可导出的配置", "提示")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出所有配置",
            self.get_export_all_filename(),
            "JSON文件 (*.json)",
        )
        if file_path:
            try:
                export_data = self.export_configs()
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                config_count = len(export_data.get("configs", []))
                MessageService.show_operation_success(
                    self,
                    "导出",
                    f"已导出 {config_count} 个配置到：{file_path}",
                )
            except Exception as e:
                MessageService.show_error(self, self._format_error_message("export", e), "错误")

    def importConfigs(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入配置",
            "",
            "JSON文件 (*.json)",
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    import_data = json.load(f)
                if not isinstance(import_data, dict):
                    MessageService.show_warning(self, "导入文件格式不正确", "格式错误")
                    return
                if "configs" not in import_data:
                    MessageService.show_warning(self, "导入文件缺少 'configs' 字段", "格式错误")
                    return
                result = self.import_configs(import_data)
                self.handle_import_success(result)
                self.loadConfigs()
            except Exception as e:
                MessageService.show_error(self, self._format_error_message("import", e), "错误")

    def __del__(self):
        """析构时断开主题信号连接并清理worker"""
        self._cleanup_test_worker()
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
