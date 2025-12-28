"""
透明度Token系统

定义标准化的透明度级别，供所有组件使用。
提供预设方案和组件默认透明度映射。
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


class OpacityTokens:
    """透明度Token - 统一透明度级别定义

    命名规范：
    - 基础级别：描述透明程度的形容词
    - 组件默认：组件类型大写
    - 边框透明：BORDER_前缀

    使用示例：
        from themes.transparency_tokens import OpacityTokens

        # 获取侧边栏默认透明度
        opacity = OpacityTokens.SIDEBAR  # 0.85

        # 获取基础透明度级别
        opacity = OpacityTokens.DENSE  # 0.85
    """

    # ==================== 基础透明度级别 ====================
    # 从完全透明到完全不透明的8个级别

    NONE = 0.0          # 完全透明
    SUBTLE = 0.1        # 微透明（悬浮提示边缘、装饰性元素）
    LIGHT = 0.3         # 轻透明（hover效果、次要遮罩）
    MEDIUM = 0.5        # 中等透明（模态遮罩、禁用状态背景）
    SOLID = 0.7         # 接近不透明（次要内容区域）
    DENSE = 0.85        # 密集（主要内容区域，默认透明效果）
    OPAQUE = 0.95       # 几乎不透明（对话框、重要内容）
    FULL = 1.0          # 完全不透明

    # ==================== 组件默认透明度 ====================
    # 按组件类型分类

    # --- 布局组件 ---
    SIDEBAR = 0.85          # 侧边栏
    HEADER = 0.90           # 标题栏
    CONTENT = 0.95          # 内容区域
    FOOTER = 0.90           # 底部栏

    # --- 浮层组件 ---
    DIALOG = 0.95           # 对话框
    MODAL = 0.92            # 模态框
    DROPDOWN = 0.95         # 下拉菜单
    TOOLTIP = 0.90          # 工具提示
    POPOVER = 0.92          # 弹出框
    MENU = 0.95             # 菜单

    # --- 卡片组件 ---
    CARD = 0.95             # 普通卡片
    CARD_ELEVATED = 0.98    # 浮起卡片（悬停状态）
    CARD_GLASS = 0.85       # 玻璃态卡片

    # --- 反馈组件 ---
    OVERLAY = 0.5           # 遮罩层
    LOADING = 0.85          # 加载层
    TOAST = 0.95            # 消息提示
    NOTIFICATION = 0.95     # 通知

    # --- 输入组件 ---
    INPUT = 0.98            # 输入框背景
    BUTTON = 1.0            # 按钮（默认不透明）
    BUTTON_GHOST = 0.0      # 幽灵按钮背景
    BUTTON_HOVER = 0.1      # 按钮悬停背景

    # ==================== 边框透明度 ====================

    BORDER_NONE = 0.0       # 无边框
    BORDER_SUBTLE = 0.1     # 微弱边框
    BORDER_LIGHT = 0.2      # 轻边框
    BORDER_DEFAULT = 0.3    # 默认边框
    BORDER_MEDIUM = 0.4     # 中等边框
    BORDER_STRONG = 0.5     # 强边框

    # ==================== 阴影透明度 ====================

    SHADOW_XS = 0.05        # 极小阴影
    SHADOW_SM = 0.1         # 小阴影
    SHADOW_MD = 0.15        # 中等阴影
    SHADOW_LG = 0.2         # 大阴影
    SHADOW_XL = 0.25        # 超大阴影

    @classmethod
    def get_component_opacity(cls, component_id: str) -> float:
        """获取组件默认透明度

        Args:
            component_id: 组件标识符（如 "sidebar", "header", "dialog"）

        Returns:
            组件默认透明度，如果组件不存在则返回 FULL (1.0)
        """
        token_name = component_id.upper()
        return getattr(cls, token_name, cls.FULL)


@dataclass
class TransparencyPreset:
    """透明度预设方案"""
    id: str                 # 预设ID
    name: str               # 显示名称
    description: str        # 描述
    multiplier: float       # 透明度乘数（应用于所有组件）
    icon: str = ""          # 图标（可选）


class TransparencyPresets:
    """透明度预设方案管理

    提供预定义的透明度方案，用户可一键应用。

    使用示例：
        from themes.transparency_tokens import TransparencyPresets

        # 获取所有预设
        presets = TransparencyPresets.get_all()

        # 获取特定预设
        preset = TransparencyPresets.get("glass")

        # 应用预设计算组件透明度
        sidebar_opacity = TransparencyPresets.apply_to_component("glass", "sidebar")
    """

    # 预设方案定义
    NONE = TransparencyPreset(
        id="none",
        name="无透明",
        description="所有组件完全不透明，传统实心界面",
        multiplier=1.0,
        icon="square"
    )

    SUBTLE = TransparencyPreset(
        id="subtle",
        name="轻盈",
        description="微弱的透明效果，保持界面层次感",
        multiplier=0.98,
        icon="feather"
    )

    CLASSIC = TransparencyPreset(
        id="classic",
        name="经典",
        description="适中的透明效果，平衡美观与可读性",
        multiplier=0.92,
        icon="layers"
    )

    GLASS = TransparencyPreset(
        id="glass",
        name="毛玻璃",
        description="强烈的玻璃效果，现代感十足",
        multiplier=0.85,
        icon="blur"
    )

    CRYSTAL = TransparencyPreset(
        id="crystal",
        name="水晶",
        description="极致透明效果，适合桌面壁纸展示",
        multiplier=0.75,
        icon="diamond"
    )

    # 所有预设列表
    _ALL_PRESETS: List[TransparencyPreset] = [NONE, SUBTLE, CLASSIC, GLASS, CRYSTAL]

    @classmethod
    def get_all(cls) -> List[TransparencyPreset]:
        """获取所有预设方案"""
        return cls._ALL_PRESETS.copy()

    @classmethod
    def get(cls, preset_id: str) -> Optional[TransparencyPreset]:
        """根据ID获取预设方案

        Args:
            preset_id: 预设ID

        Returns:
            预设方案，如果不存在则返回 None
        """
        for preset in cls._ALL_PRESETS:
            if preset.id == preset_id:
                return preset
        return None

    @classmethod
    def apply_to_component(cls, preset_id: str, component_id: str) -> float:
        """计算预设应用到组件后的透明度

        Args:
            preset_id: 预设ID
            component_id: 组件标识符

        Returns:
            计算后的透明度值（0.0-1.0）
        """
        preset = cls.get(preset_id)
        if preset is None:
            return OpacityTokens.FULL

        base_opacity = OpacityTokens.get_component_opacity(component_id)

        # 如果预设是"无透明"，直接返回1.0
        if preset.multiplier >= 1.0:
            return OpacityTokens.FULL

        # 计算透明度：组件默认透明度 * 预设乘数
        # 但不能超过1.0或低于组件的最小透明度
        calculated = base_opacity * preset.multiplier

        # 确保结果在合理范围内
        return max(0.3, min(1.0, calculated))

    @classmethod
    def generate_config(cls, preset_id: str) -> Dict[str, float]:
        """生成预设对应的完整透明度配置

        Args:
            preset_id: 预设ID

        Returns:
            包含所有组件透明度的配置字典
        """
        preset = cls.get(preset_id)
        if preset is None:
            preset = cls.NONE

        return {
            "enabled": preset.multiplier < 1.0,
            "sidebar_opacity": cls.apply_to_component(preset_id, "sidebar"),
            "header_opacity": cls.apply_to_component(preset_id, "header"),
            "content_opacity": cls.apply_to_component(preset_id, "content"),
            "dialog_opacity": cls.apply_to_component(preset_id, "dialog"),
            "modal_opacity": cls.apply_to_component(preset_id, "modal"),
            "dropdown_opacity": cls.apply_to_component(preset_id, "dropdown"),
            "tooltip_opacity": cls.apply_to_component(preset_id, "tooltip"),
            "popover_opacity": cls.apply_to_component(preset_id, "popover"),
            "card_opacity": cls.apply_to_component(preset_id, "card"),
            "card_glass_opacity": cls.apply_to_component(preset_id, "card_glass"),
            "overlay_opacity": cls.apply_to_component(preset_id, "overlay"),
            "loading_opacity": cls.apply_to_component(preset_id, "loading"),
            "toast_opacity": cls.apply_to_component(preset_id, "toast"),
            "input_opacity": cls.apply_to_component(preset_id, "input"),
            "button_opacity": cls.apply_to_component(preset_id, "button"),
        }


# 组件配置元数据（用于配置界面）
COMPONENT_CONFIG_META: List[Dict] = [
    {
        "group_id": "layout",
        "group_name": "布局组件",
        "components": [
            {"id": "sidebar", "name": "侧边栏", "default": OpacityTokens.SIDEBAR, "min": 0.5, "max": 1.0},
            {"id": "header", "name": "标题栏", "default": OpacityTokens.HEADER, "min": 0.6, "max": 1.0},
            {"id": "content", "name": "内容区域", "default": OpacityTokens.CONTENT, "min": 0.7, "max": 1.0},
        ]
    },
    {
        "group_id": "overlay",
        "group_name": "浮层组件",
        "components": [
            {"id": "dialog", "name": "对话框", "default": OpacityTokens.DIALOG, "min": 0.7, "max": 1.0},
            {"id": "modal", "name": "模态框", "default": OpacityTokens.MODAL, "min": 0.7, "max": 1.0},
            {"id": "dropdown", "name": "下拉菜单", "default": OpacityTokens.DROPDOWN, "min": 0.7, "max": 1.0},
            {"id": "tooltip", "name": "工具提示", "default": OpacityTokens.TOOLTIP, "min": 0.6, "max": 1.0},
            {"id": "popover", "name": "弹出框", "default": OpacityTokens.POPOVER, "min": 0.7, "max": 1.0},
        ]
    },
    {
        "group_id": "card",
        "group_name": "卡片组件",
        "components": [
            {"id": "card", "name": "普通卡片", "default": OpacityTokens.CARD, "min": 0.6, "max": 1.0},
            {"id": "card_glass", "name": "玻璃态卡片", "default": OpacityTokens.CARD_GLASS, "min": 0.5, "max": 0.95},
        ]
    },
    {
        "group_id": "feedback",
        "group_name": "反馈组件",
        "components": [
            {"id": "overlay", "name": "模态遮罩", "default": OpacityTokens.OVERLAY, "min": 0.2, "max": 0.8},
            {"id": "loading", "name": "加载层", "default": OpacityTokens.LOADING, "min": 0.5, "max": 1.0},
            {"id": "toast", "name": "消息提示", "default": OpacityTokens.TOAST, "min": 0.7, "max": 1.0},
        ]
    },
    {
        "group_id": "input",
        "group_name": "输入组件",
        "components": [
            {"id": "input", "name": "输入框", "default": OpacityTokens.INPUT, "min": 0.8, "max": 1.0},
            {"id": "button", "name": "按钮", "default": OpacityTokens.BUTTON, "min": 0.8, "max": 1.0},
        ]
    },
]


def get_component_meta(component_id: str) -> Optional[Dict]:
    """获取组件配置元数据

    Args:
        component_id: 组件标识符

    Returns:
        组件元数据，如果不存在则返回 None
    """
    for group in COMPONENT_CONFIG_META:
        for comp in group["components"]:
            if comp["id"] == component_id:
                return comp
    return None


def get_all_component_ids() -> List[str]:
    """获取所有组件ID列表"""
    ids = []
    for group in COMPONENT_CONFIG_META:
        for comp in group["components"]:
            ids.append(comp["id"])
    return ids
