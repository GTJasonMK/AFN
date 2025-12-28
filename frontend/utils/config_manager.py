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

    # ==================== 透明效果配置 ====================
    # 支持15种组件类型的独立透明度配置

    # 组件透明度默认值（与OpacityTokens保持一致）
    _OPACITY_DEFAULTS = {
        # 布局组件
        "sidebar": 0.85,
        "header": 0.90,
        "content": 0.95,
        # 浮层组件
        "dialog": 0.95,
        "modal": 0.92,
        "dropdown": 0.95,
        "tooltip": 0.90,
        "popover": 0.92,
        # 卡片组件
        "card": 0.95,
        "card_glass": 0.85,
        # 反馈组件
        "overlay": 0.50,
        "loading": 0.85,
        "toast": 0.95,
        # 输入组件
        "input": 0.98,
        "button": 1.00,
    }

    def get_transparency_config(self) -> dict:
        """获取透明效果配置

        Returns:
            dict: 透明效果配置字典，包含：
                - enabled: 是否启用透明效果
                - system_blur: 是否启用系统级模糊（仅Windows）
                - master_opacity: 主控透明度系数（与所有组件透明度相乘）
                - {component_id}_opacity: 各组件的透明度值
        """
        config = {
            "enabled": self.settings.value("transparency/enabled", False, type=bool),
            "system_blur": self.settings.value("transparency/system_blur", False, type=bool),
            "master_opacity": self.settings.value("transparency/master_opacity", 1.0, type=float),
        }

        # 加载所有组件的透明度配置
        for comp_id, default_value in self._OPACITY_DEFAULTS.items():
            key = f"transparency/{comp_id}_opacity"
            config[f"{comp_id}_opacity"] = self.settings.value(key, default_value, type=float)

        return config

    def set_transparency_config(self, config: dict):
        """保存透明效果配置

        Args:
            config: 透明效果配置字典
        """
        # 保存基础配置
        if "enabled" in config:
            self.settings.setValue("transparency/enabled", config["enabled"])
        if "system_blur" in config:
            self.settings.setValue("transparency/system_blur", config["system_blur"])
        if "master_opacity" in config:
            self.settings.setValue("transparency/master_opacity", config["master_opacity"])

        # 保存所有组件的透明度配置
        for comp_id in self._OPACITY_DEFAULTS.keys():
            config_key = f"{comp_id}_opacity"
            if config_key in config:
                self.settings.setValue(f"transparency/{config_key}", config[config_key])

        # 强制同步到磁盘
        self.settings.sync()

    def get_transparency_enabled(self) -> bool:
        """获取透明效果是否启用"""
        return self.settings.value("transparency/enabled", False, type=bool)

    def set_transparency_enabled(self, enabled: bool):
        """设置透明效果是否启用"""
        self.settings.setValue("transparency/enabled", enabled)

    def get_component_opacity(self, component_id: str) -> float:
        """获取组件透明度

        Args:
            component_id: 组件标识符

        Returns:
            float: 透明度值 (0.0-1.0)
        """
        default = self._OPACITY_DEFAULTS.get(component_id, 1.0)
        key = f"transparency/{component_id}_opacity"
        return self.settings.value(key, default, type=float)

    def set_component_opacity(self, component_id: str, opacity: float):
        """设置组件透明度

        Args:
            component_id: 组件标识符
            opacity: 透明度值 (0.0-1.0)
        """
        key = f"transparency/{component_id}_opacity"
        self.settings.setValue(key, opacity)

    def reset_transparency_config(self):
        """重置透明效果配置为默认值"""
        self.settings.setValue("transparency/enabled", False)
        self.settings.setValue("transparency/system_blur", False)
        self.settings.setValue("transparency/master_opacity", 1.0)

        # 重置所有组件透明度为默认值
        for comp_id, default_value in self._OPACITY_DEFAULTS.items():
            self.settings.setValue(f"transparency/{comp_id}_opacity", default_value)

    # ==================== 背景图片配置 ====================

    def get_background_image_path(self) -> str:
        """获取背景图片路径

        Returns:
            str: 背景图片的绝对路径，如果未设置返回空字符串
        """
        path = self.settings.value("appearance/background_image", "", type=str)
        # 调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[ConfigManager] 读取背景图片路径: '{path}'")
        return path

    def set_background_image_path(self, path: str):
        """设置背景图片路径

        Args:
            path: 背景图片的绝对路径，传入空字符串表示清除
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[ConfigManager] 保存背景图片路径: '{path}'")
        self.settings.setValue("appearance/background_image", path)
        self.settings.sync()
        # 验证保存成功
        saved = self.settings.value("appearance/background_image", "", type=str)
        logger.info(f"[ConfigManager] 验证保存结果: '{saved}'")

    def clear_background_image(self):
        """清除背景图片设置"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("[ConfigManager] 清除背景图片设置")
        self.settings.remove("appearance/background_image")
        self.settings.sync()

    def get_background_image_opacity(self) -> float:
        """获取背景图片透明度

        Returns:
            float: 透明度值 (0.0-1.0)，默认0.3（较淡）
        """
        opacity = self.settings.value("appearance/background_image_opacity", 0.3, type=float)
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[ConfigManager] 读取背景图片透明度: {opacity}")
        return opacity

    def set_background_image_opacity(self, opacity: float):
        """设置背景图片透明度

        Args:
            opacity: 透明度值 (0.0-1.0)
        """
        import logging
        logger = logging.getLogger(__name__)
        # 限制范围
        opacity = max(0.0, min(1.0, opacity))
        logger.info(f"[ConfigManager] 保存背景图片透明度: {opacity}")
        self.settings.setValue("appearance/background_image_opacity", opacity)
        self.settings.sync()
