"""
V2 主题配置 Mixin

提供面向组件的配置访问方法，支持从后端加载 V2 格式的主题配置。
包含设计令牌访问、组件配置访问和效果配置访问。

扩展内容：
- 全组件透明度访问（15种组件类型）
- 透明度Token系统集成
"""

from typing import Any, Optional
from themes.transparency_tokens import OpacityTokens, TransparencyPresets, get_component_meta


class V2ConfigMixin:
    """V2 主题配置 Mixin - 面向组件的配置访问"""

    def __init__(self):
        """初始化 V2 配置存储"""
        # V2 配置缓存
        self._v2_config = None
        self._use_v2 = False
        # 调用下一个类的 __init__（协作式多重继承）
        super().__init__()

    # ==================== V2 配置管理 ====================

    def apply_v2_config(self, config: dict):
        """应用 V2 格式的主题配置

        Args:
            config: V2 格式的配置字典，包含 token_*, comp_*, effects 等字段
        """
        # 重置V1配置（V1/V2互斥）
        if hasattr(self, '_use_custom'):
            self._use_custom = False
        if hasattr(self, '_custom_theme_config'):
            self._custom_theme_config = None

        # 应用V2配置
        self._v2_config = config
        self._use_v2 = True

        # 发射主题切换信号（使用防抖版本，由父类提供）
        if hasattr(self, '_emit_theme_changed'):
            self._emit_theme_changed()
        elif hasattr(self, 'theme_changed') and hasattr(self, '_current_mode'):
            self.theme_changed.emit(self._current_mode.value)

    def reset_v2_config(self):
        """重置 V2 配置，回退到内置主题"""
        self._v2_config = None
        self._use_v2 = False

        # 发射主题切换信号（使用防抖版本，由父类提供）
        if hasattr(self, '_emit_theme_changed'):
            self._emit_theme_changed()
        elif hasattr(self, 'theme_changed') and hasattr(self, '_current_mode'):
            self.theme_changed.emit(self._current_mode.value)

    @property
    def is_using_v2_config(self) -> bool:
        """检查是否正在使用 V2 配置"""
        return self._use_v2 and self._v2_config is not None

    @property
    def v2_config(self) -> dict:
        """获取当前 V2 配置"""
        return self._v2_config or {}

    # ==================== 设计令牌访问 ====================

    def get_token(self, category: str, key: str, default: Any = None) -> Any:
        """获取设计令牌值

        Args:
            category: 令牌类别 ("colors", "typography", "spacing", "radius")
            key: 令牌键名
            default: 默认值

        Returns:
            令牌值
        """
        if not self._v2_config:
            return default

        token_key = f"token_{category}"
        tokens = self._v2_config.get(token_key, {})
        return tokens.get(key, default)

    def get_color_token(self, key: str, default: str = "#000000") -> str:
        """获取颜色令牌"""
        return self.get_token("colors", key, default)

    def get_typography_token(self, key: str, default: str = "") -> str:
        """获取排版令牌"""
        return self.get_token("typography", key, default)

    def get_spacing_token(self, key: str, default: str = "8px") -> str:
        """获取间距令牌"""
        return self.get_token("spacing", key, default)

    def get_radius_token(self, key: str, default: str = "4px") -> str:
        """获取圆角令牌"""
        return self.get_token("radius", key, default)

    # ==================== 组件配置访问 ====================

    def get_component_config(self, component: str) -> dict:
        """获取组件配置

        Args:
            component: 组件名称 ("button", "card", "input", "sidebar", etc.)

        Returns:
            组件配置字典
        """
        if not self._v2_config:
            return {}

        comp_key = f"comp_{component}"
        return self._v2_config.get(comp_key, {})

    def get_component_value(
        self, component: str, key: str, default: Any = None
    ) -> Any:
        """获取组件配置中的单个值

        Args:
            component: 组件名称
            key: 配置键名
            default: 默认值

        Returns:
            配置值
        """
        config = self.get_component_config(component)
        return config.get(key, default)

    def get_component_variant(
        self, component: str, variant: str, key: str = None, default: Any = None
    ) -> Any:
        """获取组件变体配置

        Args:
            component: 组件名称
            variant: 变体名称 (如 "primary", "secondary", "ghost")
            key: 可选的具体键名，如果为 None 则返回整个变体配置
            default: 默认值

        Returns:
            变体配置或具体值
        """
        config = self.get_component_config(component)
        variant_config = config.get(variant, {})

        if key is None:
            return variant_config or default
        return variant_config.get(key, default)

    # ==================== 按钮组件访问 ====================

    def get_button_style(self, variant: str = "primary") -> dict:
        """获取按钮变体样式

        Args:
            variant: 按钮变体 ("primary", "secondary", "ghost", "danger")

        Returns:
            按钮样式字典
        """
        return self.get_component_variant("button", variant, default={})

    def get_button_size(self, size: str = "default") -> dict:
        """获取按钮尺寸配置

        Args:
            size: 尺寸 ("sm", "default", "lg")

        Returns:
            尺寸配置字典
        """
        sizes = self.get_component_value("button", "sizes", {})
        return sizes.get(size, {})

    # ==================== 卡片组件访问 ====================

    def get_card_style(self) -> dict:
        """获取卡片样式配置"""
        return self.get_component_config("card")

    # ==================== 输入框组件访问 ====================

    def get_input_style(self) -> dict:
        """获取输入框样式配置"""
        return self.get_component_config("input")

    # ==================== 侧边栏组件访问（含透明） ====================

    def get_sidebar_style(self) -> dict:
        """获取侧边栏样式配置（含透明效果）"""
        return self.get_component_config("sidebar")

    def get_sidebar_transparency(self) -> dict:
        """获取侧边栏透明效果配置

        Returns:
            dict: 包含 opacity, use_transparency 的字典
        """
        config = self.get_component_config("sidebar")
        return {
            "opacity": config.get("opacity", 0.85),
            "use_transparency": config.get("use_transparency", False),
        }

    # ==================== 顶部栏组件访问（含透明） ====================

    def get_header_style(self) -> dict:
        """获取顶部栏样式配置（含透明效果）"""
        return self.get_component_config("header")

    def get_header_transparency(self) -> dict:
        """获取顶部栏透明效果配置"""
        config = self.get_component_config("header")
        return {
            "opacity": config.get("opacity", 0.90),
            "use_transparency": config.get("use_transparency", False),
        }

    # ==================== 对话框组件访问（含透明） ====================

    def get_dialog_style(self) -> dict:
        """获取对话框样式配置（含透明效果）"""
        return self.get_component_config("dialog")

    def get_dialog_transparency(self) -> dict:
        """获取对话框透明效果配置"""
        config = self.get_component_config("dialog")
        return {
            "opacity": config.get("opacity", 0.95),
            "use_transparency": config.get("use_transparency", False),
        }

    # ==================== 其他组件访问 ====================

    def get_scrollbar_style(self) -> dict:
        """获取滚动条样式配置"""
        return self.get_component_config("scrollbar")

    def get_tooltip_style(self) -> dict:
        """获取工具提示样式配置"""
        return self.get_component_config("tooltip")

    def get_tabs_style(self) -> dict:
        """获取标签页样式配置"""
        return self.get_component_config("tabs")

    def get_text_style(self, variant: str = "body") -> dict:
        """获取文本样式配置

        Args:
            variant: 文本变体 ("heading", "body", "muted", "link")
        """
        return self.get_component_variant("text", variant, default={})

    def get_semantic_style(self, type_: str = "info") -> dict:
        """获取语义反馈样式配置

        Args:
            type_: 语义类型 ("success", "error", "warning", "info")
        """
        return self.get_component_variant("semantic", type_, default={})

    # ==================== 效果配置访问 ====================

    def get_effects_config(self) -> dict:
        """获取效果配置"""
        if not self._v2_config:
            return {}
        return self._v2_config.get("effects", {})

    def get_effect_value(self, key: str, default: Any = None) -> Any:
        """获取单个效果配置值"""
        effects = self.get_effects_config()
        return effects.get(key, default)

    def get_animation_speed(self) -> str:
        """获取动画速度设置

        Returns:
            str: "none" | "slow" | "normal" | "fast"
        """
        return self.get_effect_value("animation_speed", "normal")

    def get_transition(self, speed: str = "base") -> str:
        """获取过渡动画时长

        Args:
            speed: 速度级别 ("fast", "base", "slow")
        """
        key = f"transition_{speed}"
        return self.get_effect_value(key, "300ms")

    # ==================== 统一组件透明度访问 ====================
    # 注意：透明度配置已统一到V1经典模式管理，始终从本地ConfigManager读取

    def get_master_opacity(self) -> float:
        """获取主控透明度系数

        主控透明度会与所有组件透明度相乘，用于统一调控整体透明效果。

        Returns:
            主控透明度值 (0.0-1.0)，默认1.0表示不影响
        """
        if hasattr(self, 'get_transparency_config'):
            config = self.get_transparency_config()
            return config.get("master_opacity", 1.0)
        return 1.0

    def get_component_opacity(self, component_id: str) -> float:
        """获取组件透明度（已应用主控透明度系数）

        最终透明度 = 组件透明度 * 主控透明度系数

        Args:
            component_id: 组件标识符（如 "sidebar", "header", "dialog"）

        Returns:
            透明度值 (0.0-1.0)
        """
        # 检查透明效果是否启用
        if not self.is_transparency_globally_enabled():
            return OpacityTokens.FULL

        # 获取主控透明度系数
        master = self.get_master_opacity()

        # 透明度始终从本地配置读取
        base_opacity = OpacityTokens.FULL
        if hasattr(self, 'get_transparency_config'):
            config = self.get_transparency_config()
            config_key = f"{component_id}_opacity"
            if config_key in config:
                base_opacity = config[config_key]
            else:
                # 回退到Token默认值
                base_opacity = OpacityTokens.get_component_opacity(component_id)
        else:
            base_opacity = OpacityTokens.get_component_opacity(component_id)

        # 应用主控透明度系数
        return base_opacity * master

    def is_transparency_globally_enabled(self) -> bool:
        """检查透明效果是否全局启用

        透明度始终从本地ConfigManager读取，不使用V2配置。

        Returns:
            bool: 透明效果是否启用
        """
        # 透明度始终从本地配置读取
        if hasattr(self, 'get_transparency_config'):
            config = self.get_transparency_config()
            return config.get("enabled", False)

        return False

    def is_component_transparency_enabled(self, component_id: str) -> bool:
        """检查组件透明效果是否启用

        组件透明启用条件：
        1. 全局透明效果启用
        2. 组件透明度 < 1.0

        Args:
            component_id: 组件标识符

        Returns:
            bool: 组件透明效果是否启用
        """
        if not self.is_transparency_globally_enabled():
            return False

        opacity = self.get_component_opacity(component_id)
        return opacity < 1.0

    def get_all_component_opacities(self) -> dict:
        """获取所有组件的透明度配置

        Returns:
            dict: 组件ID -> 透明度值的映射
        """
        from themes.transparency_tokens import get_all_component_ids

        result = {}
        for comp_id in get_all_component_ids():
            result[comp_id] = self.get_component_opacity(comp_id)
        return result

    def apply_transparency_preset(self, preset_id: str) -> dict:
        """应用透明度预设方案

        Args:
            preset_id: 预设ID（"none", "subtle", "classic", "glass", "crystal"）

        Returns:
            dict: 生成的完整透明度配置
        """
        config = TransparencyPresets.generate_config(preset_id)

        # 保存到配置并应用
        if hasattr(self, 'set_transparency_config'):
            self.set_transparency_config(config)
        if hasattr(self, 'apply_transparency'):
            self.apply_transparency()

        return config

    def get_current_preset(self) -> Optional[str]:
        """检测当前使用的预设方案

        通过比较当前配置与预设配置来检测。

        Returns:
            str | None: 预设ID，如果不匹配任何预设则返回 None
        """
        if not self.is_transparency_globally_enabled():
            return "none"

        current_opacities = self.get_all_component_opacities()

        # 与每个预设比较
        for preset in TransparencyPresets.get_all():
            preset_config = TransparencyPresets.generate_config(preset.id)
            match = True

            for key, value in preset_config.items():
                if key == "enabled":
                    continue
                if key in current_opacities:
                    # 允许小误差
                    if abs(current_opacities.get(key.replace("_opacity", ""), 1.0) - value) > 0.02:
                        match = False
                        break

            if match:
                return preset.id

        return None

    # ==================== 布局组件透明度 ====================

    def get_sidebar_opacity(self) -> float:
        """获取侧边栏透明度"""
        return self.get_component_opacity("sidebar")

    def get_header_opacity(self) -> float:
        """获取标题栏透明度"""
        return self.get_component_opacity("header")

    def get_content_opacity(self) -> float:
        """获取内容区域透明度"""
        return self.get_component_opacity("content")

    # ==================== 浮层组件透明度 ====================

    def get_dialog_opacity(self) -> float:
        """获取对话框透明度"""
        return self.get_component_opacity("dialog")

    def get_modal_opacity(self) -> float:
        """获取模态框透明度"""
        return self.get_component_opacity("modal")

    def get_dropdown_opacity(self) -> float:
        """获取下拉菜单透明度"""
        return self.get_component_opacity("dropdown")

    def get_tooltip_opacity(self) -> float:
        """获取工具提示透明度"""
        return self.get_component_opacity("tooltip")

    def get_popover_opacity(self) -> float:
        """获取弹出框透明度"""
        return self.get_component_opacity("popover")

    # ==================== 卡片组件透明度 ====================

    def get_card_opacity(self) -> float:
        """获取普通卡片透明度"""
        return self.get_component_opacity("card")

    def get_card_glass_opacity(self) -> float:
        """获取玻璃态卡片透明度"""
        return self.get_component_opacity("card_glass")

    # ==================== 反馈组件透明度 ====================

    def get_overlay_opacity(self) -> float:
        """获取模态遮罩透明度"""
        return self.get_component_opacity("overlay")

    def get_loading_opacity(self) -> float:
        """获取加载层透明度"""
        return self.get_component_opacity("loading")

    def get_toast_opacity(self) -> float:
        """获取消息提示透明度"""
        return self.get_component_opacity("toast")

    # ==================== 输入组件透明度 ====================

    def get_input_opacity(self) -> float:
        """获取输入框透明度"""
        return self.get_component_opacity("input")

    def get_button_opacity(self) -> float:
        """获取按钮透明度"""
        return self.get_component_opacity("button")
