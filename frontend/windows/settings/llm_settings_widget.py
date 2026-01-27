"""
LLM配置管理 - 书籍风格
"""

from themes.theme_manager import theme_manager
from utils.message_service import MessageService
from .ui_helpers import (
    build_config_list_danger_button_style,
    build_config_list_primary_button_style,
    build_config_list_secondary_button_style,
    build_config_list_widget_style,
)
from .base_config_list_widget import BaseConfigListWidget
from .dialogs import LLMConfigDialog


class LLMSettingsWidget(BaseConfigListWidget):
    """LLM配置管理 - 书籍风格"""

    def _apply_styles(self):
        """应用书籍风格主题"""
        palette = theme_manager.get_book_palette()

        # 主要按钮（新增配置）
        self.add_btn.setStyleSheet(build_config_list_primary_button_style(palette, with_pressed=True))

        # 次要按钮样式
        secondary_style = build_config_list_secondary_button_style(palette, variant="full")

        for btn in [self.import_btn, self.export_all_btn, self.test_btn,
                    self.activate_btn, self.edit_btn, self.export_btn]:
            btn.setStyleSheet(secondary_style)

        # 删除按钮样式（危险操作）
        self.delete_btn.setStyleSheet(build_config_list_danger_button_style(palette, variant="full"))

        # 配置列表样式 - 优化质感
        self.config_list.setStyleSheet(build_config_list_widget_style(palette))

        # 强制刷新样式缓存
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def fetch_configs(self):
        return self.api_client.get_llm_configs()

    def formatConfigText(self, config):
        """格式化配置显示文本"""
        name = config.get("config_name", "未命名")
        is_active = config.get("is_active", False)
        url = config.get("llm_provider_url", "(默认)")
        model = config.get("llm_provider_model", "(默认)")

        status = " [当前激活]" if is_active else ""
        return f"{name}{status}\n{url}\n模型: {model}"

    def create_config_dialog(self, config=None):
        return LLMConfigDialog(config=config, parent=self)

    def create_config(self, data):
        return self.api_client.create_llm_config(data)

    def update_config(self, config_id, data):
        return self.api_client.update_llm_config(config_id, data)

    def delete_config(self, config_id):
        return self.api_client.delete_llm_config(config_id)

    def activate_config(self, config_id):
        return self.api_client.activate_llm_config(config_id)

    def test_config(self, config_id):
        return self.api_client.test_llm_config(config_id)

    def export_config(self, config_id):
        return self.api_client.export_llm_config(config_id)

    def export_configs(self):
        return self.api_client.export_llm_configs()

    def import_configs(self, import_data):
        return self.api_client.import_llm_configs(import_data)

    def get_export_all_filename(self):
        return "llm_configs.json"

    def handle_import_success(self, result):
        MessageService.show_success(self, "成功导入配置")
