"""
主题配置编辑器Mixin

负责配置的CRUD操作和编辑器数据管理。
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt

from utils.async_worker import AsyncWorker
from utils.message_service import MessageService
from components.dialogs import InputDialog
from components.inputs import (
    ColorPickerWidget, SizeInputWidget, FontFamilySelector,
    SliderInputWidget, SwitchWidget
)

from .config_groups import CONFIG_GROUPS

if TYPE_CHECKING:
    from .widget import ThemeSettingsWidget

logger = logging.getLogger(__name__)


def update_theme_config_list(config_list, configs, current_mode, on_empty):
    """更新主题配置列表显示

    Args:
        config_list: QListWidget 实例
        configs: 配置列表
        current_mode: 当前主题模式（light/dark）
        on_empty: 列表为空时的回调
    """
    from PyQt6.QtWidgets import QListWidgetItem

    config_list.clear()

    mode_configs = [c for c in configs if c.get("parent_mode") == current_mode]

    for config in mode_configs:
        item = QListWidgetItem()
        name = config.get("config_name", "未命名")
        if config.get("is_active"):
            name = f"{name} *"
        item.setText(name)
        item.setData(Qt.ItemDataRole.UserRole, config.get("id"))
        config_list.addItem(item)

    if config_list.count() > 0:
        config_list.setCurrentRow(0)
    else:
        on_empty()


class ThemeEditorBaseMixin:
    """主题编辑器通用Mixin

    负责：
    - 配置列表加载与选择逻辑
    - CRUD 操作的异步执行模板
    """

    _worker_key_prefix = "theme_config"

    def _get_worker_key(self, action: str) -> str:
        """获取 WorkerManager key"""
        return f"{self._worker_key_prefix}_{action}"

    def _request_config_list(self):
        """请求配置列表（子类实现）"""
        raise NotImplementedError

    def _request_config_detail(self, config_id: int):
        """请求配置详情（子类实现）"""
        raise NotImplementedError

    def _request_create_config(self, payload: Dict[str, Any]):
        """请求创建配置（子类实现）"""
        raise NotImplementedError

    def _request_duplicate_config(self, config_id: int):
        """请求复制配置（子类实现）"""
        raise NotImplementedError

    def _request_delete_config(self, config_id: int):
        """请求删除配置（子类实现）"""
        raise NotImplementedError

    def _request_save_config(self, config_id: int, payload: Dict[str, Any]):
        """请求保存配置（子类实现）"""
        raise NotImplementedError

    def _request_activate_config(self, config_id: int):
        """请求激活配置（子类实现）"""
        raise NotImplementedError

    def _request_reset_config(self, config_id: int):
        """请求重置配置（子类实现）"""
        raise NotImplementedError

    def _before_save_config(self) -> bool:
        """保存前置处理（子类可覆盖）"""
        return True

    def _handle_save_without_config(self) -> bool:
        """无配置时保存处理（子类可覆盖）"""
        MessageService.show_warning(self, "请先选择一个配置")
        return True

    def _load_configs(self):
        """加载配置列表"""
        if getattr(self, '_is_destroyed', False):
            return

        def do_load():
            return self._request_config_list()

        def on_success(configs):
            if getattr(self, '_is_destroyed', False):
                return
            self._configs = configs
            self._update_config_list()

        def on_error(error):
            if getattr(self, '_is_destroyed', False):
                return
            logger.error(f"加载主题配置失败: {error}")

        worker = AsyncWorker(do_load)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("list"))

    def _update_config_list(self):
        """更新配置列表显示"""
        update_theme_config_list(
            self.config_list,
            self._configs,
            self._current_mode,
            self._clear_editor,
        )

    def _on_mode_changed(self, index: int):
        """模式切换处理"""
        self._current_mode = "light" if index == 0 else "dark"
        self._update_config_list()

    def _on_config_selected(self, row: int):
        """配置选中处理"""
        if row < 0:
            self._current_config_id = None
            self._clear_editor()
            return

        item = self.config_list.item(row)
        if item:
            config_id = item.data(Qt.ItemDataRole.UserRole)
            self._current_config_id = config_id
            self._load_config_detail(config_id)

    def _load_config_detail(self, config_id: int):
        """加载配置详情"""
        if getattr(self, '_is_destroyed', False):
            return

        def do_load():
            return self._request_config_detail(config_id)

        def on_success(config):
            if getattr(self, '_is_destroyed', False):
                return
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            if getattr(self, '_is_destroyed', False):
                return
            logger.error(f"加载配置详情失败: {error}")

        worker = AsyncWorker(do_load)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("detail"))

    def _create_new_config(self):
        """创建新配置"""
        default_name = f"我的{'浅色' if self._current_mode == 'light' else '深色'}主题"
        name, ok = InputDialog.getTextStatic(
            parent=self,
            title="新建子主题",
            label="请输入子主题名称：",
            text=default_name
        )
        if not ok or not name.strip():
            return

        def do_create():
            return self._request_create_config({
                "config_name": name.strip(),
                "parent_mode": self._current_mode
            })

        def on_success(config):
            MessageService.show_success(self, f"已创建子主题：{config.get('config_name')}")
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"创建失败：{error}")

        worker = AsyncWorker(do_create)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("create"))

    def _duplicate_config(self):
        """复制当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_duplicate():
            return self._request_duplicate_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已复制为：{config.get('config_name')}")
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"复制失败：{error}")

        worker = AsyncWorker(do_duplicate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("duplicate"))

    def _delete_config(self):
        """删除当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        if not MessageService.confirm(
            self,
            "确定要删除此配置吗？此操作不可恢复。",
            "确认删除",
            confirm_text="删除",
            cancel_text="取消"
        ):
            return

        def do_delete():
            return self._request_delete_config(self._current_config_id)

        def on_success(result):
            MessageService.show_success(self, "配置已删除")
            self._current_config_id = None
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"删除失败：{error}")

        worker = AsyncWorker(do_delete)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("delete"))

    def _save_config(self):
        """保存当前配置"""
        if not self._before_save_config():
            return

        if not self._current_config_id:
            if self._handle_save_without_config():
                return

        data = self._collect_config_data()

        def do_save():
            return self._request_save_config(self._current_config_id, data)

        def on_success(config):
            MessageService.show_success(self, "配置已保存")
            self._is_modified = False
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"保存失败：{error}")

        worker = AsyncWorker(do_save)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("save"))

    def _activate_config(self):
        """激活当前配置（应用主题和透明效果）"""
        from themes.theme_manager import theme_manager

        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_activate():
            return self._request_activate_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已激活：{config.get('config_name')}")
            self._load_configs()
            theme_manager.begin_batch_update()
            try:
                self._apply_active_theme(config)
            finally:
                theme_manager.end_batch_update()

        def on_error(error):
            MessageService.show_error(self, f"激活失败：{error}")

        worker = AsyncWorker(do_activate)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("activate"))

    def _reset_config(self):
        """重置配置为默认值"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        if not MessageService.confirm(
            self,
            "确定要将此配置重置为默认值吗？",
            "确认重置",
            confirm_text="重置",
            cancel_text="取消"
        ):
            return

        def do_reset():
            return self._request_reset_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, "配置已重置为默认值")
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            MessageService.show_error(self, f"重置失败：{error}")

        worker = AsyncWorker(do_reset)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, self._get_worker_key("reset"))

    def _apply_active_theme(self, config: Dict[str, Any]):
        """应用激活的主题配置到主题管理器"""
        from themes.theme_manager import theme_manager

        config_version = config.get("config_version", 1)

        if config_version == 2 and config.get("effects"):
            if hasattr(theme_manager, 'apply_v2_config'):
                theme_manager.apply_v2_config(config)
        else:
            flat_config = {}
            for group_key in CONFIG_GROUPS:
                group_values = config.get(group_key, {}) or {}
                flat_config.update(group_values)

            if flat_config and hasattr(theme_manager, 'apply_custom_theme'):
                theme_manager.apply_custom_theme(flat_config)


class ThemeConfigEditorMixin(ThemeEditorBaseMixin):
    """
    主题配置编辑器Mixin

    负责：
    - 加载和更新配置列表
    - 配置的CRUD操作（创建、复制、删除、保存、激活、重置）
    - 编辑器数据的填充和收集
    """

    _worker_key_prefix = "theme_config"

    def _request_config_list(self):
        return self.api_client.get_theme_configs()

    def _request_config_detail(self, config_id: int):
        return self.api_client.get_theme_config(config_id)

    def _request_create_config(self, payload: Dict[str, Any]):
        return self.api_client.create_theme_config(payload)

    def _request_duplicate_config(self, config_id: int):
        return self.api_client.duplicate_theme_config(config_id)

    def _request_delete_config(self, config_id: int):
        return self.api_client.delete_theme_config(config_id)

    def _request_save_config(self, config_id: int, payload: Dict[str, Any]):
        return self.api_client.update_theme_config(config_id, payload)

    def _request_activate_config(self, config_id: int):
        return self.api_client.activate_theme_config(config_id)

    def _request_reset_config(self, config_id: int):
        return self.api_client.reset_theme_config(config_id)

    def _populate_editor(self: "ThemeSettingsWidget", config: Dict[str, Any]):
        """填充编辑器"""
        from themes.theme_manager import theme_manager

        self.name_input.setText(config.get("config_name", ""))

        for group_key, group_data in CONFIG_GROUPS.items():
            # 透明度配置从本地获取
            if group_key == "transparency":
                transparency_config = theme_manager.get_transparency_config()
                config_values = self._convert_transparency_to_fields(transparency_config)
            else:
                config_values = config.get(group_key, {}) or {}

            for field_key in group_data["fields"]:
                widget = self._field_widgets.get(group_key, {}).get(field_key)
                if widget is None:
                    continue

                value = config_values.get(field_key, "")

                if isinstance(widget, ColorPickerWidget):
                    widget.set_color(value or "")
                elif isinstance(widget, SizeInputWidget):
                    widget.set_value(value or "")
                elif isinstance(widget, FontFamilySelector):
                    widget.set_value(value or "")
                elif isinstance(widget, SwitchWidget):
                    widget.setChecked(bool(value))
                elif isinstance(widget, SliderInputWidget):
                    if value != "" and value is not None:
                        widget.set_value(float(value), emit_signal=False)
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value) if value else "")

    def _convert_transparency_to_fields(self, config: dict) -> dict:
        """将透明度配置转换为字段格式（0-1 转为 0-100）"""
        return {
            "TRANSPARENCY_ENABLED": config.get("enabled", False),
            "SYSTEM_BLUR": config.get("system_blur", False),
            "MASTER_OPACITY": int(config.get("master_opacity", 1.0) * 100),
            "SIDEBAR_OPACITY": int(config.get("sidebar_opacity", 0.85) * 100),
            "HEADER_OPACITY": int(config.get("header_opacity", 0.90) * 100),
            "CONTENT_OPACITY": int(config.get("content_opacity", 0.95) * 100),
            "DIALOG_OPACITY": int(config.get("dialog_opacity", 0.95) * 100),
            "MODAL_OPACITY": int(config.get("modal_opacity", 0.92) * 100),
            "DROPDOWN_OPACITY": int(config.get("dropdown_opacity", 0.95) * 100),
            "TOOLTIP_OPACITY": int(config.get("tooltip_opacity", 0.90) * 100),
            "POPOVER_OPACITY": int(config.get("popover_opacity", 0.92) * 100),
            "CARD_OPACITY": int(config.get("card_opacity", 0.95) * 100),
            "CARD_GLASS_OPACITY": int(config.get("card_glass_opacity", 0.85) * 100),
            "OVERLAY_OPACITY": int(config.get("overlay_opacity", 0.50) * 100),
            "LOADING_OPACITY": int(config.get("loading_opacity", 0.85) * 100),
            "TOAST_OPACITY": int(config.get("toast_opacity", 0.95) * 100),
            "INPUT_OPACITY": int(config.get("input_opacity", 0.98) * 100),
            "BUTTON_OPACITY": int(config.get("button_opacity", 1.00) * 100),
        }

    def _convert_fields_to_transparency(self, fields: dict) -> dict:
        """将字段格式转换为透明度配置（0-100 转为 0-1）"""
        return {
            "enabled": fields.get("TRANSPARENCY_ENABLED", False),
            "system_blur": fields.get("SYSTEM_BLUR", False),
            "master_opacity": fields.get("MASTER_OPACITY", 100) / 100.0,
            "sidebar_opacity": fields.get("SIDEBAR_OPACITY", 85) / 100.0,
            "header_opacity": fields.get("HEADER_OPACITY", 90) / 100.0,
            "content_opacity": fields.get("CONTENT_OPACITY", 95) / 100.0,
            "dialog_opacity": fields.get("DIALOG_OPACITY", 95) / 100.0,
            "modal_opacity": fields.get("MODAL_OPACITY", 92) / 100.0,
            "dropdown_opacity": fields.get("DROPDOWN_OPACITY", 95) / 100.0,
            "tooltip_opacity": fields.get("TOOLTIP_OPACITY", 90) / 100.0,
            "popover_opacity": fields.get("POPOVER_OPACITY", 92) / 100.0,
            "card_opacity": fields.get("CARD_OPACITY", 95) / 100.0,
            "card_glass_opacity": fields.get("CARD_GLASS_OPACITY", 85) / 100.0,
            "overlay_opacity": fields.get("OVERLAY_OPACITY", 50) / 100.0,
            "loading_opacity": fields.get("LOADING_OPACITY", 85) / 100.0,
            "toast_opacity": fields.get("TOAST_OPACITY", 95) / 100.0,
            "input_opacity": fields.get("INPUT_OPACITY", 98) / 100.0,
            "button_opacity": fields.get("BUTTON_OPACITY", 100) / 100.0,
        }

    def _clear_editor(self: "ThemeSettingsWidget"):
        """清空编辑器

        注意：透明度配置从本地加载，不会被清空
        """
        from themes.theme_manager import theme_manager

        self.name_input.clear()

        # 先获取透明度本地配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_fields = self._convert_transparency_to_fields(transparency_config)

        for group_key, group_widgets in self._field_widgets.items():
            for field_key, widget in group_widgets.items():
                # 透明度组：从本地配置加载，不清空
                if group_key == "transparency":
                    value = transparency_fields.get(field_key)
                    if isinstance(widget, SwitchWidget):
                        widget.setChecked(bool(value))
                    elif isinstance(widget, SliderInputWidget):
                        if value is not None:
                            widget.set_value(float(value), emit_signal=False)
                else:
                    # 其他组：清空
                    if isinstance(widget, ColorPickerWidget):
                        widget.set_color("")
                    elif isinstance(widget, SizeInputWidget):
                        widget.set_value("")
                    elif isinstance(widget, FontFamilySelector):
                        widget.set_value("")
                    elif isinstance(widget, SwitchWidget):
                        widget.setChecked(False)
                    elif isinstance(widget, SliderInputWidget):
                        widget.reset_to_default()
                    elif isinstance(widget, QLineEdit):
                        widget.clear()

    def _collect_config_data(self: "ThemeSettingsWidget") -> Dict[str, Any]:
        """收集编辑器数据"""
        data = {
            "config_name": self.name_input.text().strip(),
            "parent_mode": self._current_mode,
        }

        for group_key, group_data in CONFIG_GROUPS.items():
            # 跳过透明度（单独保存到本地）
            if group_key == "transparency":
                continue

            group_values = {}
            for field_key in group_data["fields"]:
                widget = self._field_widgets.get(group_key, {}).get(field_key)
                if widget:
                    if isinstance(widget, ColorPickerWidget):
                        value = widget.get_color()
                    elif isinstance(widget, SizeInputWidget):
                        value = widget.get_value()
                    elif isinstance(widget, FontFamilySelector):
                        value = widget.get_value()
                    elif isinstance(widget, SwitchWidget):
                        value = widget.isChecked()
                    elif isinstance(widget, SliderInputWidget):
                        value = widget.get_value()
                    elif isinstance(widget, QLineEdit):
                        value = widget.text().strip()
                    else:
                        value = ""
                    if value is not None and value != "":
                        group_values[field_key] = value
            if group_values:
                data[group_key] = group_values

        return data

    def _collect_transparency_data(self: "ThemeSettingsWidget") -> Dict[str, Any]:
        """收集透明度配置数据"""
        fields = {}
        transparency_widgets = self._field_widgets.get("transparency", {})

        for field_key, widget in transparency_widgets.items():
            if isinstance(widget, SwitchWidget):
                fields[field_key] = widget.isChecked()
            elif isinstance(widget, SliderInputWidget):
                fields[field_key] = widget.get_value()

        return self._convert_fields_to_transparency(fields)

    def _mark_modified(self: "ThemeSettingsWidget"):
        """标记为已修改"""
        self._is_modified = True
    def _before_save_config(self) -> bool:
        from themes.theme_manager import theme_manager

        transparency_data = self._collect_transparency_data()
        theme_manager.set_transparency_config(transparency_data)
        theme_manager.apply_transparency()
        return True

    def _handle_save_without_config(self) -> bool:
        MessageService.show_success(self, "透明度配置已保存")
        self._is_modified = False
        return True


__all__ = [
    "ThemeConfigEditorMixin",
]
