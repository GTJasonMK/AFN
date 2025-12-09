"""
配置管理工具

用于保存和加载应用配置（如上次使用的project_id）
"""

from PyQt6.QtCore import QSettings


class ConfigManager:
    """应用配置管理器

    使用QSettings保存配置到本地INI文件
    """

    def __init__(self, organization="AFN", application="PyQtClient"):
        """初始化配置管理器

        Args:
            organization: 组织名称
            application: 应用名称
        """
        self.settings = QSettings(organization, application)

    def get_last_inspiration_project(self):
        """获取上次灵感模式使用的项目ID

        Returns:
            str | None: 项目ID，如果不存在返回None
        """
        return self.settings.value("inspiration/last_project_id", None)

    def set_last_inspiration_project(self, project_id):
        """保存灵感模式使用的项目ID

        Args:
            project_id: 项目ID
        """
        self.settings.setValue("inspiration/last_project_id", project_id)

    def clear_last_inspiration_project(self):
        """清除保存的灵感模式项目ID"""
        self.settings.remove("inspiration/last_project_id")

    def get_window_geometry(self):
        """获取窗口几何信息

        Returns:
            QByteArray | None: 窗口几何信息
        """
        return self.settings.value("window/geometry", None)

    def set_window_geometry(self, geometry):
        """保存窗口几何信息

        Args:
            geometry: QByteArray 窗口几何信息
        """
        self.settings.setValue("window/geometry", geometry)

    def get_api_base_url(self):
        """获取API基础URL

        Returns:
            str: API基础URL，默认为http://127.0.0.1:8123
        """
        return self.settings.value("api/base_url", "http://127.0.0.1:8123")

    def set_api_base_url(self, url):
        """保存API基础URL

        Args:
            url: API基础URL
        """
        self.settings.setValue("api/base_url", url)

    def get_theme_mode(self):
        """获取主题模式

        Returns:
            str: 主题模式 ('light' 或 'dark')，默认为 'light'
        """
        return self.settings.value("appearance/theme_mode", "light")

    def set_theme_mode(self, mode):
        """保存主题模式

        Args:
            mode: 主题模式 ('light' 或 'dark')
        """
        self.settings.setValue("appearance/theme_mode", mode)
