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


class ThemeConfigEditorMixin:
    """
    主题配置编辑器Mixin

    负责：
    - 加载和更新配置列表
    - 配置的CRUD操作（创建、复制、删除、保存、激活、重置）
    - 编辑器数据的填充和收集
    """

    def _load_configs(self: "ThemeSettingsWidget"):
        """加载配置列表"""
        if getattr(self, '_is_destroyed', False):
            return

        def do_load():
            return self.api_client.get_theme_configs()

        def on_success(configs):
            if getattr(self, '_is_destroyed', False):
                return
            self._configs = configs
            self._update_config_list()

        def on_error(error):
            if getattr(self, '_is_destroyed', False):
                return
            logger.error(f"加载主题配置失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _update_config_list(self: "ThemeSettingsWidget"):
        """更新配置列表显示"""
        from PyQt6.QtWidgets import QListWidgetItem

        self.config_list.clear()

        # 筛选当前模式的配置
        mode_configs = [c for c in self._configs if c.get("parent_mode") == self._current_mode]

        for config in mode_configs:
            item = QListWidgetItem()
            name = config.get("config_name", "未命名")
            if config.get("is_active"):
                name = f"{name} *"
            item.setText(name)
            item.setData(Qt.ItemDataRole.UserRole, config.get("id"))
            self.config_list.addItem(item)

        # 自动选中第一项
        if self.config_list.count() > 0:
            self.config_list.setCurrentRow(0)
        else:
            self._clear_editor()

    def _on_mode_changed(self: "ThemeSettingsWidget", index: int):
        """模式切换处理"""
        self._current_mode = "light" if index == 0 else "dark"
        self._update_config_list()

    def _on_config_selected(self: "ThemeSettingsWidget", row: int):
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

    def _load_config_detail(self: "ThemeSettingsWidget", config_id: int):
        """加载配置详情"""
        if getattr(self, '_is_destroyed', False):
            return

        def do_load():
            return self.api_client.get_theme_config(config_id)

        def on_success(config):
            if getattr(self, '_is_destroyed', False):
                return
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            if getattr(self, '_is_destroyed', False):
                return
            logger.error(f"加载配置详情失败: {error}")

        self._worker = AsyncWorker(do_load)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

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

    def _create_new_config(self: "ThemeSettingsWidget"):
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
            return self.api_client.create_theme_config({
                "config_name": name.strip(),
                "parent_mode": self._current_mode
            })

        def on_success(config):
            MessageService.show_success(self, f"已创建子主题：{config.get('config_name')}")
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"创建失败：{error}")

        self._worker = AsyncWorker(do_create)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _duplicate_config(self: "ThemeSettingsWidget"):
        """复制当前配置"""
        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_duplicate():
            return self.api_client.duplicate_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已复制为：{config.get('config_name')}")
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"复制失败：{error}")

        self._worker = AsyncWorker(do_duplicate)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _delete_config(self: "ThemeSettingsWidget"):
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
            return self.api_client.delete_theme_config(self._current_config_id)

        def on_success(result):
            MessageService.show_success(self, "配置已删除")
            self._current_config_id = None
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"删除失败：{error}")

        self._worker = AsyncWorker(do_delete)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _save_config(self: "ThemeSettingsWidget"):
        """保存当前配置（只保存，不应用）"""
        from themes.theme_manager import theme_manager

        # 透明度配置是本地存储，不依赖后端配置ID，总是保存
        transparency_data = self._collect_transparency_data()
        theme_manager.set_transparency_config(transparency_data)
        # 注意：不再调用 apply_transparency()，统一由"激活"按钮应用

        # 后端配置需要先选择一个配置
        if not self._current_config_id:
            # 如果只有透明度修改，仍然显示保存成功
            MessageService.show_success(self, "透明度配置已保存")
            self._is_modified = False
            return

        # 收集后端配置数据
        data = self._collect_config_data()

        def do_save():
            return self.api_client.update_theme_config(self._current_config_id, data)

        def on_success(config):
            MessageService.show_success(self, "配置已保存")
            self._is_modified = False
            self._load_configs()

        def on_error(error):
            MessageService.show_error(self, f"保存失败：{error}")

        self._worker = AsyncWorker(do_save)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _activate_config(self: "ThemeSettingsWidget"):
        """激活当前配置（应用主题和透明效果）"""
        from themes.theme_manager import theme_manager

        if not self._current_config_id:
            MessageService.show_warning(self, "请先选择一个配置")
            return

        def do_activate():
            return self.api_client.activate_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, f"已激活：{config.get('config_name')}")
            self._load_configs()
            # 使用批量更新模式，避免多次信号发射
            theme_manager.begin_batch_update()
            try:
                # 应用主题配置
                self._apply_active_theme(config)
                # 透明度配置已在主题应用中处理，无需单独调用
            finally:
                # 结束批量更新，统一发射一次信号
                theme_manager.end_batch_update()

        def on_error(error):
            MessageService.show_error(self, f"激活失败：{error}")

        self._worker = AsyncWorker(do_activate)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _reset_config(self: "ThemeSettingsWidget"):
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
            return self.api_client.reset_theme_config(self._current_config_id)

        def on_success(config):
            MessageService.show_success(self, "配置已重置为默认值")
            self._populate_editor(config)
            self._is_modified = False

        def on_error(error):
            MessageService.show_error(self, f"重置失败：{error}")

        self._worker = AsyncWorker(do_reset)
        self._worker.success.connect(on_success)
        self._worker.error.connect(on_error)
        self._worker.start()

    def _apply_active_theme(self: "ThemeSettingsWidget", config: Dict[str, Any]):
        """应用激活的主题配置到主题管理器

        支持V1和V2两种配置格式，根据config_version字段自动选择。
        """
        from themes.theme_manager import theme_manager

        config_version = config.get("config_version", 1)

        if config_version == 2 and config.get("effects"):
            # V2配置：使用面向组件的配置
            if hasattr(theme_manager, 'apply_v2_config'):
                theme_manager.apply_v2_config(config)
        else:
            # V1配置：合并所有配置组为平面字典
            flat_config = {}
            for group_key in CONFIG_GROUPS:
                group_values = config.get(group_key, {}) or {}
                flat_config.update(group_values)

            # 调用主题管理器应用自定义主题
            if flat_config and hasattr(theme_manager, 'apply_custom_theme'):
                theme_manager.apply_custom_theme(flat_config)


__all__ = [
    "ThemeConfigEditorMixin",
]
