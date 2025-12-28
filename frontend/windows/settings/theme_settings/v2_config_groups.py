"""
V2 主题配置组定义

面向组件的配置结构，用户直接编辑按钮、卡片、侧边栏等组件的样式。
透明配置已融入到相关组件中（sidebar, header, dialog）。

配置分为三个层级：
1. 效果配置 (effects) - 全局效果开关
2. 组件配置 (components) - 各UI组件的样式
3. 设计令牌 (tokens) - 高级用户的基础变量（默认折叠）
"""

from typing import Dict, Any, List, Tuple

# 效果配置组 - 全局效果开关
# 注意：透明度配置（transparency_enabled, system_blur）已统一到V1经典模式管理
EFFECTS_CONFIG = {
    "label": "效果配置",
    "description": "控制全局视觉效果的开关和参数（透明度配置请在经典模式中调整）",
    "icon": "sparkles",
    "fields": {
        "animation_speed": {
            "type": "select",
            "label": "动画速度",
            "description": "控制界面过渡动画的快慢",
            "options": [
                ("none", "无动画"),
                ("slow", "缓慢"),
                ("normal", "正常"),
                ("fast", "快速"),
            ],
            "default": "normal",
        },
        "hover_effects": {
            "type": "switch",
            "label": "悬浮效果",
            "description": "鼠标悬浮时的视觉反馈效果",
            "default": True,
        },
        "focus_ring": {
            "type": "switch",
            "label": "焦点指示器",
            "description": "键盘焦点时的边框高亮",
            "default": True,
        },
    }
}

# 组件配置组 - 面向组件的样式编辑
COMPONENT_CONFIGS = {
    "button": {
        "label": "按钮",
        "description": "各类按钮的样式配置",
        "icon": "button",
        "variants": {
            "primary": {
                "label": "主要按钮",
                "description": "主要操作按钮，如提交、确认",
                "fields": {
                    "bg": ("color", "背景色"),
                    "bg_hover": ("color", "悬浮背景"),
                    "bg_pressed": ("color", "按下背景"),
                    "text": ("color", "文字颜色"),
                    "border": ("text", "边框样式"),
                    "radius": ("size", "圆角大小"),
                    "shadow": ("text", "阴影样式"),
                }
            },
            "secondary": {
                "label": "次要按钮",
                "description": "次要操作按钮，边框样式",
                "fields": {
                    "bg": ("color", "背景色"),
                    "bg_hover": ("color", "悬浮背景"),
                    "text": ("color", "文字颜色"),
                    "text_hover": ("color", "悬浮文字"),
                    "border": ("text", "边框样式"),
                    "radius": ("size", "圆角大小"),
                }
            },
            "ghost": {
                "label": "幽灵按钮",
                "description": "无背景的轻量按钮",
                "fields": {
                    "bg": ("color", "背景色"),
                    "bg_hover": ("color", "悬浮背景"),
                    "text": ("color", "文字颜色"),
                    "border": ("text", "边框样式"),
                    "radius": ("size", "圆角大小"),
                }
            },
            "danger": {
                "label": "危险按钮",
                "description": "危险操作按钮，如删除",
                "fields": {
                    "bg": ("color", "背景色"),
                    "bg_hover": ("color", "悬浮背景"),
                    "text": ("color", "文字颜色"),
                    "border": ("text", "边框样式"),
                    "radius": ("size", "圆角大小"),
                }
            },
        },
        "sizes": {
            "sm": {
                "label": "小尺寸",
                "fields": {
                    "height": ("size", "高度"),
                    "padding_x": ("size", "水平内边距"),
                    "font_size": ("size", "字号"),
                }
            },
            "default": {
                "label": "默认尺寸",
                "fields": {
                    "height": ("size", "高度"),
                    "padding_x": ("size", "水平内边距"),
                    "font_size": ("size", "字号"),
                }
            },
            "lg": {
                "label": "大尺寸",
                "fields": {
                    "height": ("size", "高度"),
                    "padding_x": ("size", "水平内边距"),
                    "font_size": ("size", "字号"),
                }
            },
        }
    },
    "card": {
        "label": "卡片",
        "description": "卡片容器的样式配置",
        "icon": "card",
        "fields": {
            "bg": ("color", "背景色"),
            "bg_hover": ("color", "悬浮背景"),
            "border": ("text", "边框样式"),
            "border_hover": ("text", "悬浮边框"),
            "radius": ("size", "圆角大小"),
            "shadow": ("text", "阴影样式"),
            "shadow_hover": ("text", "悬浮阴影"),
            "padding": ("size", "内边距"),
        }
    },
    "input": {
        "label": "输入框",
        "description": "文本输入框的样式配置",
        "icon": "input",
        "fields": {
            "bg": ("color", "背景色"),
            "bg_focus": ("color", "聚焦背景"),
            "text": ("color", "文字颜色"),
            "placeholder": ("color", "占位符颜色"),
            "border": ("text", "边框样式"),
            "border_focus": ("text", "聚焦边框"),
            "radius": ("size", "圆角大小"),
            "padding": ("size", "内边距"),
        }
    },
    "sidebar": {
        "label": "侧边栏",
        "description": "侧边栏的样式配置（含透明效果）",
        "icon": "sidebar",
        "fields": {
            "bg": ("color", "背景色"),
            "border": ("text", "边框样式"),
            "item_bg_hover": ("color", "项目悬浮背景"),
            "item_bg_active": ("color", "项目激活背景"),
            "item_text": ("color", "项目文字颜色"),
            "item_text_active": ("color", "激活文字颜色"),
        },
        "transparency": {
            "label": "透明效果",
            "description": "侧边栏的透明配置",
            "fields": {
                "use_transparency": ("switch", "启用透明"),
                "opacity": ("slider", "透明度", {"min": 0.5, "max": 1.0, "step": 0.05}),
            }
        }
    },
    "header": {
        "label": "顶部栏",
        "description": "顶部标题栏的样式配置（含透明效果）",
        "icon": "header",
        "fields": {
            "bg": ("color", "背景色"),
            "border": ("text", "底部边框"),
            "title_color": ("color", "标题颜色"),
            "subtitle_color": ("color", "副标题颜色"),
        },
        "transparency": {
            "label": "透明效果",
            "description": "顶部栏的透明配置",
            "fields": {
                "use_transparency": ("switch", "启用透明"),
                "opacity": ("slider", "透明度", {"min": 0.5, "max": 1.0, "step": 0.05}),
            }
        }
    },
    "dialog": {
        "label": "对话框",
        "description": "弹出对话框的样式配置（含透明效果）",
        "icon": "dialog",
        "fields": {
            "bg": ("color", "背景色"),
            "border": ("text", "边框样式"),
            "radius": ("size", "圆角大小"),
            "shadow": ("text", "阴影样式"),
            "overlay": ("color", "遮罩颜色"),
            "overlay_opacity": ("slider", "遮罩透明度", {"min": 0.0, "max": 0.8, "step": 0.1}),
        },
        "transparency": {
            "label": "透明效果",
            "description": "对话框的透明配置",
            "fields": {
                "use_transparency": ("switch", "启用透明"),
                "opacity": ("slider", "透明度", {"min": 0.7, "max": 1.0, "step": 0.05}),
            }
        }
    },
    "scrollbar": {
        "label": "滚动条",
        "description": "滚动条的样式配置",
        "icon": "scrollbar",
        "fields": {
            "track_bg": ("color", "轨道背景"),
            "thumb_bg": ("color", "滑块背景"),
            "thumb_hover": ("color", "滑块悬浮"),
            "width": ("size", "滚动条宽度"),
            "radius": ("size", "滑块圆角"),
        }
    },
    "tooltip": {
        "label": "工具提示",
        "description": "悬浮提示框的样式配置",
        "icon": "tooltip",
        "fields": {
            "bg": ("color", "背景色"),
            "text": ("color", "文字颜色"),
            "border": ("text", "边框样式"),
            "radius": ("size", "圆角大小"),
            "shadow": ("text", "阴影样式"),
        }
    },
    "tabs": {
        "label": "标签页",
        "description": "标签页切换的样式配置",
        "icon": "tabs",
        "fields": {
            "bg": ("color", "标签背景"),
            "bg_active": ("color", "激活背景"),
            "text": ("color", "标签文字"),
            "text_active": ("color", "激活文字"),
            "border": ("text", "边框样式"),
            "indicator": ("color", "指示器颜色"),
            "indicator_height": ("size", "指示器高度"),
        }
    },
    "text": {
        "label": "文本样式",
        "description": "各类文本的样式配置",
        "icon": "text",
        "variants": {
            "heading": {
                "label": "标题",
                "fields": {
                    "color": ("color", "颜色"),
                    "font_family": ("font", "字体"),
                    "font_weight": ("text", "字重"),
                }
            },
            "body": {
                "label": "正文",
                "fields": {
                    "color": ("color", "颜色"),
                    "font_family": ("font", "字体"),
                    "line_height": ("text", "行高"),
                }
            },
            "muted": {
                "label": "次要文本",
                "fields": {
                    "color": ("color", "颜色"),
                }
            },
            "link": {
                "label": "链接",
                "fields": {
                    "color": ("color", "颜色"),
                    "color_hover": ("color", "悬浮颜色"),
                    "underline": ("switch", "下划线"),
                }
            },
        }
    },
    "semantic": {
        "label": "语义反馈",
        "description": "成功、错误、警告、信息等状态的样式",
        "icon": "semantic",
        "variants": {
            "success": {
                "label": "成功",
                "fields": {
                    "color": ("color", "主色"),
                    "bg": ("color", "背景色"),
                    "border": ("color", "边框色"),
                }
            },
            "error": {
                "label": "错误",
                "fields": {
                    "color": ("color", "主色"),
                    "bg": ("color", "背景色"),
                    "border": ("color", "边框色"),
                }
            },
            "warning": {
                "label": "警告",
                "fields": {
                    "color": ("color", "主色"),
                    "bg": ("color", "背景色"),
                    "border": ("color", "边框色"),
                }
            },
            "info": {
                "label": "信息",
                "fields": {
                    "color": ("color", "主色"),
                    "bg": ("color", "背景色"),
                    "border": ("color", "边框色"),
                }
            },
        }
    },
}

# 设计令牌配置 - 高级用户的基础变量
TOKEN_CONFIGS = {
    "colors": {
        "label": "颜色令牌",
        "description": "基础颜色变量，组件样式可引用这些值",
        "icon": "palette",
        "collapsed": True,  # 默认折叠
        "fields": {
            "brand": ("color", "品牌色", "主要按钮、链接、活动状态的主色调"),
            "brand_light": ("color", "浅品牌色", "悬浮状态、选中项高亮"),
            "brand_dark": ("color", "深品牌色", "按钮按下状态、深色强调"),
            "accent": ("color", "强调色", "书籍风格强调色，用于装饰元素"),
            "accent_light": ("color", "浅强调色", "强调区域淡化背景"),
            "background": ("color", "主背景", "页面主背景色"),
            "surface": ("color", "表面色", "卡片、面板等容器背景"),
            "surface_alt": ("color", "次表面色", "嵌套区域、代码块背景"),
            "text": ("color", "主文字", "标题、正文等主要文字"),
            "text_muted": ("color", "次文字", "描述、次要信息文字"),
            "text_subtle": ("color", "淡文字", "提示、脚注文字"),
            "text_disabled": ("color", "禁用文字", "禁用状态文字"),
            "border": ("color", "边框色", "通用边框颜色"),
            "border_light": ("color", "浅边框", "次要分隔线"),
            "border_dark": ("color", "深边框", "强调边框"),
        }
    },
    "typography": {
        "label": "排版令牌",
        "description": "字体、字号、字重配置",
        "icon": "typography",
        "collapsed": True,
        "fields": {
            "font_heading": ("font", "标题字体", "页面标题、章节标题使用"),
            "font_body": ("font", "正文字体", "文章正文、段落文字"),
            "font_ui": ("font", "UI字体", "按钮、标签、菜单等界面元素"),
            "size_xs": ("size", "超小字号", "脚注、版权信息"),
            "size_sm": ("size", "小字号", "辅助说明、时间戳"),
            "size_base": ("size", "基础字号", "正文默认字号"),
            "size_md": ("size", "中等字号", "小标题、强调文字"),
            "size_lg": ("size", "大字号", "二级标题"),
            "size_xl": ("size", "超大字号", "一级标题"),
            "size_2xl": ("size", "特大字号", "页面主标题"),
            "weight_normal": ("text", "正常字重", "正文默认字重"),
            "weight_medium": ("text", "中等字重", "略加强调"),
            "weight_semibold": ("text", "半粗字重", "小标题、按钮"),
            "weight_bold": ("text", "粗体字重", "标题、重要强调"),
        }
    },
    "spacing": {
        "label": "间距令牌",
        "description": "元素间距配置",
        "icon": "spacing",
        "collapsed": True,
        "fields": {
            "xs": ("size", "超小间距", "4px，紧凑元素内部"),
            "sm": ("size", "小间距", "8px，相关元素之间"),
            "md": ("size", "中等间距", "16px，分组内元素"),
            "lg": ("size", "大间距", "24px，分组之间"),
            "xl": ("size", "超大间距", "32px，大区块分隔"),
            "xxl": ("size", "特大间距", "48px，页面级分隔"),
        }
    },
    "radius": {
        "label": "圆角令牌",
        "description": "圆角尺寸配置",
        "icon": "radius",
        "collapsed": True,
        "fields": {
            "sm": ("size", "小圆角", "4px，按钮、输入框"),
            "md": ("size", "中等圆角", "8px，卡片、面板"),
            "lg": ("size", "大圆角", "12px，大型卡片"),
            "xl": ("size", "超大圆角", "16px，特殊强调"),
            "full": ("text", "完全圆形", "50%，用于头像"),
            "pill": ("text", "药丸形", "9999px，用于标签"),
        }
    },
}

# 导出所有配置组
V2_CONFIG_GROUPS = {
    "effects": EFFECTS_CONFIG,
    "components": COMPONENT_CONFIGS,
    "tokens": TOKEN_CONFIGS,
}


def get_component_field_key(component: str, field: str, variant: str = None) -> str:
    """生成组件字段的完整键名

    Args:
        component: 组件名称
        field: 字段名称
        variant: 变体名称（可选）

    Returns:
        完整键名，如 "comp_button.primary.bg"
    """
    if variant:
        return f"comp_{component}.{variant}.{field}"
    return f"comp_{component}.{field}"


def get_token_field_key(category: str, field: str) -> str:
    """生成令牌字段的完整键名

    Args:
        category: 令牌类别
        field: 字段名称

    Returns:
        完整键名，如 "token_colors.brand"
    """
    return f"token_{category}.{field}"


def get_effect_field_key(field: str) -> str:
    """生成效果配置字段的完整键名

    Args:
        field: 字段名称

    Returns:
        完整键名，如 "effects.transparency_enabled"
    """
    return f"effects.{field}"


__all__ = [
    "EFFECTS_CONFIG",
    "COMPONENT_CONFIGS",
    "TOKEN_CONFIGS",
    "V2_CONFIG_GROUPS",
    "get_component_field_key",
    "get_token_field_key",
    "get_effect_field_key",
]
