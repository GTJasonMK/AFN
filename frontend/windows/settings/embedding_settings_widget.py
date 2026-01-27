"""
嵌入模型配置管理 - 书籍风格
"""

from themes.theme_manager import theme_manager
from .ui_helpers import (
    build_config_list_danger_button_style,
    build_config_list_primary_button_style,
    build_config_list_secondary_button_style,
    build_config_list_widget_style,
)
from .base_config_list_widget import BaseConfigListWidget
from .dialogs import EmbeddingConfigDialog


class EmbeddingSettingsWidget(BaseConfigListWidget):
    """嵌入模型配置管理 - 书籍风格"""

    activate_success_template = "已激活配置: {name}"
    delete_confirm_template = "确定要删除配置 \"{name}\" 吗?"
    error_message_templates = {
        "load": "加载配置失败: {error}",
        "create": "创建失败: {error}",
        "update": "更新失败: {error}",
        "delete": "删除失败: {error}",
        "activate": "激活失败: {error}",
        "export": "导出失败：{error}",
        "import": "导入失败：{error}",
    }

    def __init__(self, parent=None):
        self.providers = []
        super().__init__(parent)

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
        return self.api_client.get_embedding_configs()

    def formatConfigText(self, config):
        """格式化配置显示文本"""
        name = config.get("config_name", "未命名")
        is_active = config.get("is_active", False)
        provider = config.get("provider", "openai")
        model = config.get("model_name", "(默认)")
        url = config.get("api_base_url", "(默认)")
        vector_size = config.get("vector_size")

        provider_name = "OpenAI/兼容API" if provider == "openai" else "Ollama本地"
        status = " [当前激活]" if is_active else ""
        dim_info = f" | 维度: {vector_size}" if vector_size else ""

        return f"{name}{status}\n{provider_name} | {model}{dim_info}\n{url}"

    def create_config_dialog(self, config=None):
        return EmbeddingConfigDialog(config=config, providers=self.providers, parent=self)

    def create_config(self, data):
        return self.api_client.create_embedding_config(data)

    def update_config(self, config_id, data):
        return self.api_client.update_embedding_config(config_id, data)

    def delete_config(self, config_id):
        return self.api_client.delete_embedding_config(config_id)

    def activate_config(self, config_id):
        return self.api_client.activate_embedding_config(config_id)

    def test_config(self, config_id):
        return self.api_client.test_embedding_config(config_id)

    def export_config(self, config_id):
        return self.api_client.export_embedding_config(config_id)

    def export_configs(self):
        return self.api_client.export_embedding_configs()

    def import_configs(self, import_data):
        return self.api_client.import_embedding_configs(import_data)

    def get_export_all_filename(self):
        return "embedding_configs.json"

    def build_test_dialog_payload(self, result):
        return (
            result.get("success", False),
            result.get("message", ""),
            {
                "response_time_ms": result.get("response_time_ms"),
                "vector_dimension": result.get("vector_dimension"),
                "model_info": result.get("model_info"),
            },
        )

    def after_test_success(self, result):
        self.loadConfigs()

    def __del__(self):
        """析构时断开主题信号连接并清理worker"""
        self._cleanup_test_worker()
        try:
            theme_manager.theme_changed.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
