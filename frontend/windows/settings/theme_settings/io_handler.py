"""
主题配置导入导出Mixin

负责主题配置的导入和导出功能。
"""

import json
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog

from utils.async_worker import AsyncWorker
from utils.message_service import MessageService

if TYPE_CHECKING:
    from .widget import ThemeSettingsWidget


class ThemeIOHandlerMixin:
    """
    主题配置导入导出Mixin

    负责：
    - 导出所有主题配置到JSON文件
    - 从JSON文件导入主题配置
    """

    def _export_configs(self: "ThemeSettingsWidget"):
        """导出主题配置"""
        # 选择保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出主题配置",
            "theme_configs.json",
            "JSON文件 (*.json)"
        )
        if not file_path:
            return

        def do_export():
            return self.api_client.export_all_theme_configs()

        def on_success(export_data):
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                MessageService.show_success(self, f"已导出到：{file_path}")
            except Exception as e:
                MessageService.show_error(self, f"保存文件失败：{e}")

        def on_error(error):
            MessageService.show_error(self, f"导出失败：{error}")

        self._worker = AsyncWorker(do_export)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _import_configs(self: "ThemeSettingsWidget"):
        """导入主题配置"""
        # 选择文件
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入主题配置",
            "",
            "JSON文件 (*.json)"
        )
        if not file_path:
            return

        # 读取文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
        except json.JSONDecodeError as e:
            MessageService.show_error(self, f"JSON格式错误：{e}")
            return
        except Exception as e:
            MessageService.show_error(self, f"读取文件失败：{e}")
            return

        # 确认导入
        config_count = len(import_data.get('configs', []))
        if config_count == 0:
            MessageService.show_warning(self, "文件中没有可导入的配置")
            return

        if not MessageService.confirm(
            self,
            f"即将导入 {config_count} 个主题配置。\n\n"
            "同名配置将被跳过，是否继续？",
            "确认导入"
        ):
            return

        def do_import():
            return self.api_client.import_theme_configs(import_data)

        def on_success(result):
            imported = result.get('imported_count', 0)
            skipped = result.get('skipped_count', 0)
            msg = f"成功导入 {imported} 个配置"
            if skipped > 0:
                msg += f"，跳过 {skipped} 个同名配置"
            MessageService.show_success(self, msg)
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"导入失败：{error}")

        self._worker = AsyncWorker(do_import)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()


__all__ = [
    "ThemeIOHandlerMixin",
]
