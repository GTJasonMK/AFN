"""
配置管理 Mixin

提供LLM配置、嵌入模型配置、高级配置的API方法。
"""

from typing import Any, Dict, List


class ConfigMixin:
    """配置管理方法 Mixin"""

    # ==================== LLM配置 ====================

    def get_llm_configs(self) -> List[Dict[str, Any]]:
        """获取LLM配置列表"""
        return self._request('GET', '/api/llm-configs')

    def create_llm_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建LLM配置

        Args:
            config_data: 配置数据

        Returns:
            创建的配置
        """
        return self._request('POST', '/api/llm-configs', config_data)

    def update_llm_config(
        self,
        config_id: int,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新LLM配置

        Args:
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置
        """
        return self._request('PUT', f'/api/llm-configs/{config_id}', config_data)

    def delete_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        删除LLM配置

        Args:
            config_id: 配置ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/llm-configs/{config_id}')

    def activate_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        激活LLM配置

        Args:
            config_id: 配置ID

        Returns:
            激活结果
        """
        return self._request('POST', f'/api/llm-configs/{config_id}/activate')

    def test_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试LLM配置连接

        Args:
            config_id: 配置ID

        Returns:
            测试结果
        """
        return self._request('POST', f'/api/llm-configs/{config_id}/test', timeout=30)

    def import_llm_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入LLM配置

        Args:
            import_data: LLMConfigExportData格式的导入数据
                        {"version": "1.0", "export_time": "...", "export_type": "...", "configs": [...]}

        Returns:
            导入结果
        """
        return self._request('POST', '/api/llm-configs/import', import_data)

    def export_llm_config(self, config_id: int) -> Dict[str, Any]:
        """
        导出单个LLM配置

        Args:
            config_id: 配置ID

        Returns:
            LLMConfigExportData格式的导出数据
            {"version": "1.0", "export_time": "...", "export_type": "single", "configs": [...]}
        """
        return self._request('GET', f'/api/llm-configs/{config_id}/export')

    def export_llm_configs(self) -> Dict[str, Any]:
        """
        导出所有LLM配置

        Returns:
            LLMConfigExportData格式的导出数据
            {"version": "1.0", "export_time": "...", "export_type": "batch", "configs": [...]}
        """
        return self._request('GET', '/api/llm-configs/export')

    # ==================== 嵌入模型配置 ====================

    def get_embedding_configs(self) -> List[Dict[str, Any]]:
        """获取嵌入模型配置列表"""
        return self._request('GET', '/api/embedding-configs')

    def get_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        获取指定嵌入模型配置

        Args:
            config_id: 配置ID

        Returns:
            配置详情
        """
        return self._request('GET', f'/api/embedding-configs/{config_id}')

    def create_embedding_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建嵌入模型配置

        Args:
            config_data: 配置数据

        Returns:
            创建的配置
        """
        return self._request('POST', '/api/embedding-configs', config_data)

    def update_embedding_config(
        self,
        config_id: int,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新嵌入模型配置

        Args:
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置
        """
        return self._request('PUT', f'/api/embedding-configs/{config_id}', config_data)

    def delete_embedding_config(self, config_id: int) -> None:
        """
        删除嵌入模型配置

        Args:
            config_id: 配置ID
        """
        self._request('DELETE', f'/api/embedding-configs/{config_id}')

    def activate_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        激活嵌入模型配置

        Args:
            config_id: 配置ID

        Returns:
            激活后的配置
        """
        return self._request('POST', f'/api/embedding-configs/{config_id}/activate')

    def test_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试嵌入模型配置连接

        Args:
            config_id: 配置ID

        Returns:
            测试结果
        """
        return self._request('POST', f'/api/embedding-configs/{config_id}/test', timeout=60)

    # ==================== 高级配置管理 ====================

    def get_advanced_config(self) -> Dict[str, Any]:
        """
        获取高级配置

        Returns:
            当前配置值
        """
        return self._request('GET', '/api/settings/advanced-config')

    def update_advanced_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新高级配置

        Args:
            config: 配置更新数据

        Returns:
            更新结果
        """
        return self._request('PUT', '/api/settings/advanced-config', data=config)

    # ==================== 嵌入模型配置导入导出 ====================

    def export_embedding_config(self, config_id: int) -> Dict[str, Any]:
        """
        导出单个嵌入模型配置

        Args:
            config_id: 配置ID

        Returns:
            导出数据
        """
        return self._request('GET', f'/api/embedding-configs/{config_id}/export')

    def export_embedding_configs(self) -> Dict[str, Any]:
        """
        导出所有嵌入模型配置

        Returns:
            导出数据
        """
        return self._request('GET', '/api/embedding-configs/export/all')

    def import_embedding_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入嵌入模型配置

        Args:
            import_data: 导入数据

        Returns:
            导入结果
        """
        return self._request('POST', '/api/embedding-configs/import', import_data)

    # ==================== 高级配置导入导出 ====================

    def export_advanced_config(self) -> Dict[str, Any]:
        """
        导出高级配置

        Returns:
            导出数据
        """
        return self._request('GET', '/api/settings/advanced-config/export')

    def import_advanced_config(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入高级配置

        Args:
            import_data: 导入数据

        Returns:
            导入结果
        """
        return self._request('POST', '/api/settings/advanced-config/import', import_data)

    # ==================== 队列配置导入导出 ====================

    def export_queue_config(self) -> Dict[str, Any]:
        """
        导出队列配置

        Returns:
            导出数据
        """
        return self._request('GET', '/api/settings/queue-config/export')

    def import_queue_config(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入队列配置

        Args:
            import_data: 导入数据

        Returns:
            导入结果
        """
        return self._request('POST', '/api/settings/queue-config/import', import_data)

    # ==================== 全局配置导入导出 ====================

    def export_all_configs(self) -> Dict[str, Any]:
        """
        导出所有配置（LLM、嵌入、图片、高级、队列）

        Returns:
            包含所有配置的导出数据
        """
        return self._request('GET', '/api/settings/export/all')

    def import_all_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入所有配置

        Args:
            import_data: 包含所有配置的导入数据

        Returns:
            导入结果
        """
        return self._request('POST', '/api/settings/import/all', import_data)
