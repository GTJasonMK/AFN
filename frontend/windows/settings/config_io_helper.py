"""
设置页导入导出通用工具

统一 QFileDialog + JSON 读写 + export_type 校验与错误提示。
"""

from typing import Any, Callable, Dict, Optional
import json

from PyQt6.QtWidgets import QFileDialog, QWidget

from utils.message_service import MessageService


def _show_error(parent: Optional[QWidget], message: str, title: Optional[str]) -> None:
    if title:
        MessageService.show_error(parent, message, title)
    else:
        MessageService.show_error(parent, message)


def export_config_json(
    parent: Optional[QWidget],
    dialog_title: str,
    default_filename: str,
    export_func: Callable[[], Dict[str, Any]],
    on_success: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    on_exception: Optional[Callable[[Exception], None]] = None,
    error_title: Optional[str] = "错误",
    error_template: str = "导出失败：{error}",
) -> Optional[Dict[str, Any]]:
    """导出配置到 JSON 文件"""
    file_path, _ = QFileDialog.getSaveFileName(
        parent,
        dialog_title,
        default_filename,
        "JSON文件 (*.json)"
    )

    if not file_path:
        return None

    try:
        export_data = export_func()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        if on_success:
            on_success(file_path, export_data)
        return export_data
    except Exception as e:
        if on_exception:
            on_exception(e)
        _show_error(parent, error_template.format(error=str(e)), error_title)
        return None


def import_config_json(
    parent: Optional[QWidget],
    dialog_title: str,
    expected_export_type: str,
    expected_type_label: str,
    import_func: Callable[[Dict[str, Any]], Dict[str, Any]],
    on_success: Optional[Callable[[Dict[str, Any]], None]] = None,
    on_exception: Optional[Callable[[Exception], None]] = None,
    error_title: Optional[str] = "错误",
    error_template: str = "导入失败：{error}",
    warning_title: str = "格式错误",
) -> Optional[Dict[str, Any]]:
    """从 JSON 文件导入配置"""
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        dialog_title,
        "",
        "JSON文件 (*.json)"
    )

    if not file_path:
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
    except Exception as e:
        if on_exception:
            on_exception(e)
        _show_error(parent, error_template.format(error=str(e)), error_title)
        return None

    if not isinstance(import_data, dict):
        MessageService.show_warning(parent, "导入文件格式不正确", warning_title)
        return None

    if import_data.get('export_type') != expected_export_type:
        MessageService.show_warning(
            parent,
            f"导入文件类型不正确，需要{expected_type_label}",
            warning_title
        )
        return None

    try:
        result = import_func(import_data)
    except Exception as e:
        if on_exception:
            on_exception(e)
        _show_error(parent, error_template.format(error=str(e)), error_title)
        return None

    if not isinstance(result, dict):
        _show_error(parent, "导入失败：返回结果格式不正确", error_title)
        return None

    if result.get('success'):
        if on_success:
            on_success(result)
    else:
        _show_error(parent, result.get('message', '导入失败'), error_title)

    return result
