"""
主题配置 Mixin

提供主题配置的API方法。
"""

from typing import Any, Dict, List, Optional


class ThemeConfigMixin:
    """主题配置方法 Mixin"""

    # ==================== 主题配置列表 ====================

    def get_theme_configs(self) -> List[Dict[str, Any]]:
        """获取用户的所有主题配置列表"""
        return self._request('GET', '/api/theme-configs')

    def get_theme_config(self, config_id: int) -> Dict[str, Any]:
        """
        获取指定ID的主题配置详情

        Args:
            config_id: 配置ID

        Returns:
            配置详情
        """
        return self._request('GET', f'/api/theme-configs/{config_id}')

    def get_active_theme_config(self, parent_mode: str) -> Optional[Dict[str, Any]]:
        """
        获取指定模式下当前激活的主题配置

        Args:
            parent_mode: 顶级主题模式（'light' 或 'dark'）

        Returns:
            激活的配置，如果没有则返回None
        """
        return self._request('GET', f'/api/theme-configs/active/{parent_mode}')

    def get_theme_defaults(self, mode: str) -> Dict[str, Any]:
        """
        获取指定模式的默认主题值

        Args:
            mode: 主题模式（'light' 或 'dark'）

        Returns:
            默认主题值
        """
        return self._request('GET', f'/api/theme-configs/defaults/{mode}')

    # ==================== 主题配置CRUD ====================

    def create_theme_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建新的主题配置

        Args:
            config_data: 配置数据，必须包含 config_name 和 parent_mode

        Returns:
            创建的配置
        """
        return self._request('POST', '/api/theme-configs', config_data)

    def update_theme_config(
        self,
        config_id: int,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新主题配置

        Args:
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置
        """
        return self._request('PUT', f'/api/theme-configs/{config_id}', config_data)

    def delete_theme_config(self, config_id: int) -> Dict[str, Any]:
        """
        删除主题配置

        Args:
            config_id: 配置ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/theme-configs/{config_id}')

    # ==================== 主题配置操作 ====================

    def activate_theme_config(self, config_id: int) -> Dict[str, Any]:
        """
        激活主题配置

        Args:
            config_id: 配置ID

        Returns:
            激活后的配置
        """
        return self._request('POST', f'/api/theme-configs/{config_id}/activate')

    def duplicate_theme_config(self, config_id: int) -> Dict[str, Any]:
        """
        复制主题配置

        Args:
            config_id: 配置ID

        Returns:
            复制后的新配置
        """
        return self._request('POST', f'/api/theme-configs/{config_id}/duplicate')

    def reset_theme_config(self, config_id: int) -> Dict[str, Any]:
        """
        重置主题配置为默认值

        Args:
            config_id: 配置ID

        Returns:
            重置后的配置
        """
        return self._request('POST', f'/api/theme-configs/{config_id}/reset')

    # ==================== 导入导出 ====================

    def export_theme_config(self, config_id: int) -> Dict[str, Any]:
        """
        导出单个主题配置

        Args:
            config_id: 配置ID

        Returns:
            导出的配置数据
        """
        return self._request('GET', f'/api/theme-configs/{config_id}/export')

    def export_all_theme_configs(self) -> Dict[str, Any]:
        """
        导出用户所有主题配置

        Returns:
            导出的配置数据（包含版本号和时间戳）
        """
        return self._request('GET', '/api/theme-configs/export')

    def import_theme_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入主题配置

        Args:
            import_data: 导入的配置数据

        Returns:
            导入结果
        """
        return self._request('POST', '/api/theme-configs/import', {'data': import_data})
