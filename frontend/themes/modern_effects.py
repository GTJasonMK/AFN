"""
现代美学效果库 - 提供渐变、玻璃态、新拟态等现代设计效果

提供各种现代UI设计效果，提升应用的视觉美感。
支持两种主题风格：
- Academia/Classical (深色): 黄铜渐变、浮雕效果、蜡封阴影
- Organic/Natural (浅色): 苔藓色阴影、陶土渐变、柔和效果
"""

from typing import Tuple, Optional
from PyQt6.QtGui import QLinearGradient, QRadialGradient, QConicalGradient


class ModernEffects:
    """现代设计效果生成器"""

    # ==================== 渐变色彩系统 ====================

    # 优雅渐变色组合 - 与主题系统对应
    GRADIENTS = {
        # 黄铜系列 - Academia主题主色
        "brass": {
            "light": ["#D4A87A", "#C18C5D", "#A87040"],    # 陶土渐变（浅色主题强调色）
            "dark": ["#D4B872", "#C9A962", "#B8953F"],     # 黄铜渐变（深色主题主色）
        },
        # 苔藓系列 - Organic主题主色
        "moss": {
            "light": ["#7A9474", "#5D7052", "#4A5D40"],    # 苔藓绿渐变
            "dark": ["#7A9474", "#5D7052", "#4A5D40"],     # 深色主题也可用
        },
        # 深红系列 - Academia主题强调色
        "crimson": {
            "light": ["#C4706A", "#A85448", "#8B3F35"],    # 烧焦赭色渐变
            "dark": ["#A83344", "#8B2635", "#6E1E2A"],     # 图书馆深红渐变
        },
        # 陶土系列 - Organic主题强调色
        "terracotta": {
            "light": ["#D4A87A", "#C18C5D", "#A87040"],    # 陶土渐变
            "dark": ["#D4A87A", "#C18C5D", "#A87040"],     # 陶土渐变
        },
        # 成功色系列
        "success": {
            "light": ["#8fcca6", "#6db88a", "#4a9f6e"],    # 翠绿渐变
            "dark": ["#8fcca6", "#6db88a", "#4a9f6e"],     # 翠绿渐变
        },
        # 警告色系列
        "warning": {
            "light": ["#f0c67d", "#e5ad5c", "#d4923a"],    # 暖琥珀渐变
            "dark": ["#E5AD5C", "#D4923A", "#B87A2A"],     # 暖琥珀渐变
        },
        # 错误色系列
        "error": {
            "light": ["#C4706A", "#A85448", "#8B3F35"],    # 烧焦赭色渐变
            "dark": ["#C4706A", "#A85448", "#8B3F35"],     # 烧焦赭色渐变
        },
        # 信息色系列
        "info": {
            "light": ["#90c5dd", "#6da8c9", "#4a8db3"],    # 青石蓝渐变
            "dark": ["#6DA8C9", "#4A8DB3", "#3A7499"],     # 青石蓝渐变
        },
        # 极光系列 - 多彩渐变
        "aurora": {
            "light": ["#5D7052", "#C18C5D", "#7A9474"],    # 自然极光（苔藓+陶土）
            "dark": ["#C9A962", "#8B2635", "#D4B872"],     # 学院极光（黄铜+深红）
        },
        # 木质系列 - 背景渐变
        "wood": {
            "light": ["#FDFCF8", "#FEFEFA", "#F0EBE5"],    # 米白纸张渐变
            "dark": ["#1C1714", "#251E19", "#3D332B"],     # 桃花心木渐变
        },
    }

    # ==================== 玻璃态效果 ====================

    @staticmethod
    def glassmorphism(
        bg_color: str = "rgba(255, 255, 255, 0.1)",
        blur_radius: int = 10,
        border_color: str = "rgba(255, 255, 255, 0.2)",
        border_width: int = 1,
        include_border: bool = True
    ) -> str:
        """
        生成玻璃态效果样式

        Args:
            bg_color: 背景色（需要透明度）
            blur_radius: 模糊半径
            border_color: 边框颜色
            border_width: 边框宽度
            include_border: 是否包含边框样式

        Returns:
            CSS样式字符串
        """
        if include_border:
            return f"""
                background-color: {bg_color};
                border: {border_width}px solid {border_color};
            """
        else:
            return f"""
                background-color: {bg_color};
            """

    @staticmethod
    def glassmorphism_card(is_dark: bool = False, border_color: str = None) -> str:
        """生成玻璃态卡片样式 - 针对亮色和深色主题优化

        Args:
            is_dark: 是否深色模式
            border_color: 边框颜色（可选，未提供则使用默认配色）
                        注意：此参数已废弃，边框应由调用方在StyleSheet中单独设置
        """
        if is_dark:
            # 深色主题 Academia - 深桃花心木玻璃效果
            return ModernEffects.glassmorphism(
                bg_color="rgba(28, 23, 20, 0.85)",  # 深桃花心木底色
                blur_radius=24,
                include_border=False
            )
        else:
            # 亮色主题 Organic - 米白纸张玻璃效果
            return ModernEffects.glassmorphism(
                bg_color="rgba(253, 252, 248, 0.85)",  # 米白纸张底色
                blur_radius=20,
                include_border=False
            )

    # ==================== 新拟态效果 ====================

    @staticmethod
    def neumorphism(
        bg_color: str,
        light_shadow: str = "rgba(255, 255, 255, 0.5)",
        dark_shadow: str = "rgba(0, 0, 0, 0.15)",
        distance: int = 6,
        blur: int = 12,
        inset: bool = False
    ) -> str:
        """
        生成新拟态效果样式

        Args:
            bg_color: 背景色
            light_shadow: 亮色阴影
            dark_shadow: 暗色阴影
            distance: 阴影距离
            blur: 模糊半径
            inset: 是否内凹

        Returns:
            CSS样式字符串
        """
        if inset:
            shadow = f"""
                inset {distance}px {distance}px {blur}px {dark_shadow},
                inset -{distance}px -{distance}px {blur}px {light_shadow}
            """
        else:
            shadow = f"""
                {distance}px {distance}px {blur}px {dark_shadow},
                -{distance}px -{distance}px {blur}px {light_shadow}
            """

        return f"""
            background: {bg_color};
            box-shadow: {shadow};
        """

    @staticmethod
    def neumorphism_button(bg_color: str, pressed: bool = False) -> str:
        """生成新拟态按钮样式"""
        if pressed:
            return ModernEffects.neumorphism(
                bg_color=bg_color,
                distance=2,
                blur=4,
                inset=True
            )
        else:
            return ModernEffects.neumorphism(
                bg_color=bg_color,
                distance=4,
                blur=8,
                inset=False
            )

    # ==================== 高级阴影系统 ====================

    SHADOWS = {
        # 通用阴影
        "xs": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "sm": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
        "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
        "inner": "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)",

        # Academia主题特有阴影
        "engraved": "1px 1px 1px rgba(0,0,0,0.4), -1px -1px 1px rgba(255,255,255,0.1)",
        "brass-glow": "0 4px 12px rgba(201,169,98,0.3)",
        "wax-seal": "inset 0 2px 4px rgba(255,255,255,0.2), inset 0 -2px 4px rgba(0,0,0,0.3), 0 4px 8px rgba(0,0,0,0.4)",
        "card-dark": "none",
        "card-dark-hover": "0 8px 24px rgba(0,0,0,0.3)",

        # Organic主题特有阴影
        "moss": "0 4px 20px -2px rgba(93,112,82,0.15)",
        "moss-hover": "0 6px 24px -4px rgba(93,112,82,0.25)",
        "clay": "0 10px 40px -10px rgba(193,140,93,0.2)",
        "card-light": "0 4px 20px -2px rgba(93,112,82,0.15)",
        "card-light-hover": "0 20px 40px -10px rgba(93,112,82,0.15)",
    }

    @staticmethod
    def colored_shadow(color: str, opacity: float = 0.2, size: str = "md") -> str:
        """
        生成彩色阴影

        Args:
            color: 颜色值
            opacity: 透明度
            size: 阴影大小（xs, sm, md, lg, xl, 2xl）

        Returns:
            CSS阴影样式
        """
        shadow_templates = {
            "xs": f"0 1px 2px 0 {color}{int(opacity*255):02x}",
            "sm": f"0 1px 3px 0 {color}{int(opacity*255):02x}",
            "md": f"0 4px 6px -1px {color}{int(opacity*255):02x}",
            "lg": f"0 10px 15px -3px {color}{int(opacity*255):02x}",
            "xl": f"0 20px 25px -5px {color}{int(opacity*255):02x}",
            "2xl": f"0 25px 50px -12px {color}{int(opacity*255):02x}",
        }
        return shadow_templates.get(size, shadow_templates["md"])

    # ==================== 动画和过渡 ====================

    TRANSITIONS = {
        # 通用过渡
        "fast": "all 0.15s ease-out",
        "base": "all 0.3s ease-out",
        "slow": "all 0.5s ease-out",
        "dramatic": "all 0.7s ease-out",

        # 特定属性过渡
        "colors": "background-color 0.3s ease-out, border-color 0.3s ease-out, color 0.3s ease-out",
        "transform": "transform 0.3s ease-out",
        "shadow": "box-shadow 0.3s ease-out",
        "opacity": "opacity 0.3s ease-out",

        # Academia主题 - 庄重平滑
        "academia": "all 0.3s ease-out",
        "academia-hover": "all 0.5s ease-out",

        # Organic主题 - 自然轻柔
        "organic": "all 0.3s ease-out",
        "organic-hover": "all 0.5s ease-out",
    }

    ANIMATIONS = {
        "pulse": """
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        """,
        "bounce": """
            @keyframes bounce {
                0%, 100% { transform: translateY(-25%); animation-timing-function: cubic-bezier(0.8, 0, 1, 1); }
                50% { transform: translateY(0); animation-timing-function: cubic-bezier(0, 0, 0.2, 1); }
            }
        """,
        "spin": """
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        """,
        "ping": """
            @keyframes ping {
                75%, 100% {
                    transform: scale(2);
                    opacity: 0;
                }
            }
        """,
        "fade-in": """
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
        """,
        "slide-up": """
            @keyframes slideUp {
                from { transform: translateY(100%); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }
        """,
        "scale-in": """
            @keyframes scaleIn {
                from { transform: scale(0.95); opacity: 0; }
                to { transform: scale(1); opacity: 1; }
            }
        """,
    }

    # ==================== 渐变生成器 ====================

    @staticmethod
    def linear_gradient(
        colors: list,
        angle: int = 45,
        positions: Optional[list] = None
    ) -> str:
        """
        生成线性渐变（Qt QSS格式）

        Args:
            colors: 颜色列表
            angle: 渐变角度
            positions: 颜色位置列表（可选）

        Returns:
            Qt QSS渐变样式（qlineargradient格式）
        """
        import math

        # 将角度转换为Qt的坐标系统
        # CSS角度：0deg = 向上，90deg = 向右
        # Qt坐标：x1,y1是起点，x2,y2是终点
        angle_rad = math.radians(angle)

        # 计算起点和终点坐标（0-1范围）
        # CSS角度从上方开始顺时针，Qt需要转换
        x1 = 0.5 - 0.5 * math.sin(angle_rad)
        y1 = 0.5 + 0.5 * math.cos(angle_rad)
        x2 = 0.5 + 0.5 * math.sin(angle_rad)
        y2 = 0.5 - 0.5 * math.cos(angle_rad)

        # 生成颜色停止点
        if positions:
            stops = []
            for color, pos in zip(colors, positions):
                stops.append(f"stop: {pos/100:.2f} {color}")
        else:
            # 自动均匀分布
            stops = []
            step = 1.0 / (len(colors) - 1) if len(colors) > 1 else 1.0
            for i, color in enumerate(colors):
                stops.append(f"stop: {i*step:.2f} {color}")

        return f"qlineargradient(x1: {x1:.2f}, y1: {y1:.2f}, x2: {x2:.2f}, y2: {y2:.2f}, {', '.join(stops)})"

    @staticmethod
    def radial_gradient(
        colors: list,
        shape: str = "circle",
        position: str = "center",
        positions: Optional[list] = None
    ) -> str:
        """
        生成径向渐变（Qt QSS格式）

        Args:
            colors: 颜色列表
            shape: 形状（circle或ellipse）- Qt中忽略此参数
            position: 中心位置
            positions: 颜色位置列表（可选）

        Returns:
            Qt QSS渐变样式（qradialgradient格式）
        """
        # 解析位置
        cx, cy = 0.5, 0.5  # 默认中心
        if position == "center":
            cx, cy = 0.5, 0.5
        elif position == "top":
            cx, cy = 0.5, 0.0
        elif position == "bottom":
            cx, cy = 0.5, 1.0
        elif position == "left":
            cx, cy = 0.0, 0.5
        elif position == "right":
            cx, cy = 1.0, 0.5

        # 生成颜色停止点
        if positions:
            stops = []
            for color, pos in zip(colors, positions):
                stops.append(f"stop: {pos/100:.2f} {color}")
        else:
            stops = []
            step = 1.0 / (len(colors) - 1) if len(colors) > 1 else 1.0
            for i, color in enumerate(colors):
                stops.append(f"stop: {i*step:.2f} {color}")

        return f"qradialgradient(cx: {cx:.2f}, cy: {cy:.2f}, radius: 0.5, fx: {cx:.2f}, fy: {cy:.2f}, {', '.join(stops)})"

    @staticmethod
    def mesh_gradient(colors: list) -> str:
        """
        生成网格渐变（模拟效果）

        Args:
            colors: 颜色列表（至少4个）

        Returns:
            CSS多重渐变样式
        """
        if len(colors) < 4:
            colors = colors + colors[:4-len(colors)]

        return f"""
            background:
                radial-gradient(at 0% 0%, {colors[0]} 0px, transparent 50%),
                radial-gradient(at 100% 0%, {colors[1]} 0px, transparent 50%),
                radial-gradient(at 100% 100%, {colors[2]} 0px, transparent 50%),
                radial-gradient(at 0% 100%, {colors[3]} 0px, transparent 50%);
        """

    # ==================== 高级效果 ====================

    @staticmethod
    def glow_effect(color: str, size: int = 20) -> str:
        """
        生成发光效果

        Args:
            color: 发光颜色
            size: 发光大小

        Returns:
            CSS样式
        """
        return f"""
            box-shadow:
                0 0 {size//2}px {color}40,
                0 0 {size}px {color}30,
                0 0 {size*2}px {color}20;
        """

    @staticmethod
    def neon_effect(color: str) -> str:
        """
        生成霓虹灯效果

        Args:
            color: 霓虹颜色

        Returns:
            CSS样式
        """
        return f"""
            color: {color};
            text-shadow:
                0 0 7px {color},
                0 0 10px {color},
                0 0 21px {color},
                0 0 42px {color}80,
                0 0 82px {color}60,
                0 0 92px {color}40,
                0 0 102px {color}20,
                0 0 151px {color}10;
        """

    @staticmethod
    def frosted_glass(blur: int = 8, opacity: float = 0.8) -> str:
        """
        生成毛玻璃效果

        Args:
            blur: 模糊程度
            opacity: 不透明度

        Returns:
            CSS样式
        """
        return f"""
            background-color: rgba(255, 255, 255, {opacity});
        """

    @staticmethod
    def aurora_bg(is_dark: bool = False) -> str:
        """
        生成极光背景效果 - 与主题系统配色一致

        Args:
            is_dark: 是否深色模式

        Returns:
            CSS样式
        """
        if is_dark:
            # 深色主题 Academia - 黄铜与深红的学院极光
            colors = ["#C9A962", "#8B2635", "#D4B872", "#A83344"]
        else:
            # 亮色主题 Organic - 苔藓与陶土的自然极光
            colors = ["#5D7052", "#C18C5D", "#7A9474", "#D4A87A"]

        return f"""
            background: linear-gradient(-45deg, {', '.join(colors)});
            background-size: 400% 400%;
            animation: aurora 15s ease infinite;
        """ + """
            @keyframes aurora {
                0% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
                100% { background-position: 0% 50%; }
            }
        """

    @staticmethod
    def brass_gradient_style() -> str:
        """生成黄铜渐变样式 - Academia主题按钮专用"""
        return "qlineargradient(x1: 0.5, y1: 0, x2: 0.5, y2: 1, stop: 0 #D4B872, stop: 0.5 #C9A962, stop: 1 #B8953F)"

    @staticmethod
    def crimson_gradient_style() -> str:
        """生成深红渐变样式 - Academia主题强调按钮专用"""
        return "qlineargradient(x1: 0.5, y1: 0, x2: 0.5, y2: 1, stop: 0 #A83344, stop: 0.5 #8B2635, stop: 1 #6E1E2A)"

    @staticmethod
    def moss_gradient_style() -> str:
        """生成苔藓绿渐变样式 - Organic主题按钮专用"""
        return "qlineargradient(x1: 0.5, y1: 0, x2: 0.5, y2: 1, stop: 0 #7A9474, stop: 0.5 #5D7052, stop: 1 #4A5D40)"

    @staticmethod
    def terracotta_gradient_style() -> str:
        """生成陶土渐变样式 - Organic主题强调按钮专用"""
        return "qlineargradient(x1: 0.5, y1: 0, x2: 0.5, y2: 1, stop: 0 #D4A87A, stop: 0.5 #C18C5D, stop: 1 #A87040)"

    @staticmethod
    def floating_animation() -> str:
        """生成漂浮动画效果"""
        return """
            animation: floating 3s ease-in-out infinite;
            @keyframes floating {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
                100% { transform: translateY(0px); }
            }
        """


# 导出便捷函数
def gradient(gradient_name: str, theme: str = "light") -> str:
    """
    获取预定义渐变

    Args:
        gradient_name: 渐变名称
        theme: 主题（light或dark）

    Returns:
        CSS渐变样式
    """
    colors = ModernEffects.GRADIENTS.get(gradient_name, {}).get(theme, [])
    if colors:
        return ModernEffects.linear_gradient(colors)
    return ""


def shadow(size: str = "md") -> str:
    """
    获取阴影样式

    Args:
        size: 阴影大小

    Returns:
        CSS阴影样式
    """
    return ModernEffects.SHADOWS.get(size, ModernEffects.SHADOWS["md"])


def transition(type: str = "base") -> str:
    """
    获取过渡动画

    Args:
        type: 过渡类型

    Returns:
        CSS过渡样式
    """
    return ModernEffects.TRANSITIONS.get(type, ModernEffects.TRANSITIONS["base"])