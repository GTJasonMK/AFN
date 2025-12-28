"""
主题配置组定义

定义所有可配置的主题常量及其类型和说明。
每个配置组包含相关的配置项，用于主题设置界面的编辑。
"""

# 配置组定义：每个组包含的常量及其类型和说明
# 格式: "KEY": ("type", "label", "tooltip")
CONFIG_GROUPS = {
    "primary_colors": {
        "label": "主色调",
        "description": "应用的主要品牌色彩，影响按钮、链接等核心元素",
        "fields": {
            "PRIMARY": ("color", "主色", "主要按钮背景色、链接颜色、活动状态指示、导航选中等核心强调元素"),
            "PRIMARY_LIGHT": ("color", "浅主色", "悬浮状态背景、选中项高亮、次级强调，通常用于按钮hover状态"),
            "PRIMARY_DARK": ("color", "深主色", "按钮按下状态、深色强调、active状态，提供视觉反馈"),
            "PRIMARY_PALE": ("color", "极浅主色", "列表项悬浮背景、轻微高亮、选中行背景等大面积淡化区域"),
        }
    },
    "accent_colors": {
        "label": "强调色",
        "description": "书籍风格的强调色系，用于标题、装饰性元素",
        "fields": {
            "ACCENT": ("color", "强调色", "书籍风格主强调色，用于标题装饰、重要提示、选中标签边框等"),
            "ACCENT_LIGHT": ("color", "浅强调色", "选中项背景色、标签背景、悬浮状态的淡化效果"),
            "ACCENT_DARK": ("color", "深强调色", "强调按钮按下状态、深色装饰线、标题下划线等"),
            "ACCENT_PALE": ("color", "极浅强调色", "强调区域淡化背景、卡片微弱高亮、分组背景等"),
        }
    },
    "text_colors": {
        "label": "文字色",
        "description": "各级文字颜色，确保可读性和层次感",
        "fields": {
            "TEXT_PRIMARY": ("color", "主文字色", "标题、正文、主要内容文字，需要最高对比度和可读性"),
            "TEXT_SECONDARY": ("color", "次文字色", "描述文字、次要信息、副标题，略淡于主文字"),
            "TEXT_TERTIARY": ("color", "三级文字色", "提示文字、帮助信息、时间戳、脚注等最不重要的文字"),
            "TEXT_PLACEHOLDER": ("color", "占位符色", "输入框占位提示文字、空状态说明文字"),
            "TEXT_DISABLED": ("color", "禁用文字色", "禁用按钮、不可点击链接、灰色状态的文字"),
        }
    },
    "background_colors": {
        "label": "背景色",
        "description": "各层级背景色，构建视觉层次",
        "fields": {
            "BG_PRIMARY": ("color", "主背景色", "页面主背景、输入框背景、最底层的基础背景色"),
            "BG_SECONDARY": ("color", "次背景色", "卡片背景、侧边栏、面板背景，比主背景略深或略浅"),
            "BG_TERTIARY": ("color", "三级背景色", "输入框内部、代码块背景、嵌套区域背景"),
            "BG_CARD": ("color", "卡片背景", "独立卡片、对话框、弹出层的背景色"),
            "BG_CARD_HOVER": ("color", "卡片悬浮背景", "卡片鼠标悬浮状态的背景色变化"),
            "BG_MUTED": ("color", "柔和背景", "禁用元素背景、静默状态区域、分隔区块"),
            "BG_ACCENT": ("color", "强调背景", "强调提示区域、重要通知背景、徽章背景"),
            "GLASS_BG": ("color", "玻璃态背景", "半透明毛玻璃效果背景，常用于悬浮面板"),
        }
    },
    "semantic_colors": {
        "label": "语义色",
        "description": "表达状态含义的颜色，如成功、错误、警告等",
        "fields": {
            "SUCCESS": ("color", "成功色", "成功状态主色，如操作成功提示、完成标记、正确图标"),
            "SUCCESS_LIGHT": ("color", "浅成功色", "成功状态的悬浮、浅色变体，用于背景或边框"),
            "SUCCESS_DARK": ("color", "深成功色", "成功状态的按下、强调变体"),
            "SUCCESS_BG": ("color", "成功背景", "成功提示消息的背景色、成功状态卡片背景"),
            "ERROR": ("color", "错误色", "错误状态主色，如验证失败、删除操作、错误提示"),
            "ERROR_LIGHT": ("color", "浅错误色", "错误状态的悬浮、浅色变体"),
            "ERROR_DARK": ("color", "深错误色", "错误状态的按下、强调变体"),
            "ERROR_BG": ("color", "错误背景", "错误提示消息的背景色、错误状态卡片背景"),
            "WARNING": ("color", "警告色", "警告状态主色，如需要注意的操作、警示信息"),
            "WARNING_LIGHT": ("color", "浅警告色", "警告状态的悬浮、浅色变体"),
            "WARNING_DARK": ("color", "深警告色", "警告状态的按下、强调变体"),
            "WARNING_BG": ("color", "警告背景", "警告提示消息的背景色"),
            "INFO": ("color", "信息色", "信息提示主色，如帮助说明、一般通知"),
            "INFO_LIGHT": ("color", "浅信息色", "信息状态的悬浮、浅色变体"),
            "INFO_DARK": ("color", "深信息色", "信息状态的按下、强调变体"),
            "INFO_BG": ("color", "信息背景", "信息提示消息的背景色"),
        }
    },
    "border_effects": {
        "label": "边框与阴影",
        "description": "边框颜色和阴影效果，营造层次和深度",
        "fields": {
            "BORDER_DEFAULT": ("color", "默认边框", "输入框边框、卡片边框、分隔线等通用边框颜色"),
            "BORDER_LIGHT": ("color", "浅边框", "次要分隔线、微弱边框、内部分隔使用"),
            "BORDER_DARK": ("color", "深边框", "强调边框、选中状态边框、重要分隔线"),
            "SHADOW_COLOR": ("text", "阴影颜色", "阴影的基础颜色值，如 rgba(0,0,0,0.1)，用于构建各种阴影"),
            "OVERLAY_COLOR": ("text", "遮罩颜色", "模态框背景遮罩，如 rgba(0,0,0,0.5)，半透明黑色覆盖"),
            "SHADOW_CARD": ("text", "卡片阴影", "普通卡片的完整阴影CSS值，如 0 2px 8px rgba(0,0,0,0.1)"),
            "SHADOW_CARD_HOVER": ("text", "卡片悬浮阴影", "卡片悬浮时的阴影，通常更深更大"),
            "SHADOW_SIENNA": ("text", "书香阴影", "书籍风格卡片的特殊阴影，带有暖色调"),
            "SHADOW_SIENNA_HOVER": ("text", "书香悬浮阴影", "书籍风格卡片悬浮时的阴影效果"),
        }
    },
    "button_colors": {
        "label": "按钮文字",
        "description": "按钮上的文字颜色",
        "fields": {
            "BUTTON_TEXT": ("color", "按钮主文字", "主要按钮（实心背景）上的文字颜色，通常为白色或浅色"),
            "BUTTON_TEXT_SECONDARY": ("color", "按钮次文字", "次要按钮、边框按钮上的文字颜色"),
        }
    },
    "typography": {
        "label": "字体配置",
        "description": "字体族、字号、字重和行高设置",
        "fields": {
            "FONT_HEADING": ("font", "标题字体", "页面标题、章节标题使用的字体族，建议使用衬线字体增强书香气息"),
            "FONT_BODY": ("font", "正文字体", "文章正文、段落文字使用的字体族，需要良好的可读性"),
            "FONT_DISPLAY": ("font", "展示字体", "大标题、品牌展示、装饰性标题使用的字体"),
            "FONT_UI": ("font", "UI字体", "按钮、标签、菜单、表单等界面元素使用的字体"),
            "FONT_SIZE_XS": ("size", "超小字号", "脚注、版权信息等最小文字，约10-11px"),
            "FONT_SIZE_SM": ("size", "小字号", "辅助说明、时间戳等小文字，约12-13px"),
            "FONT_SIZE_BASE": ("size", "基础字号", "正文默认字号，约14px，是最常用的文字大小"),
            "FONT_SIZE_MD": ("size", "中等字号", "小标题、强调文字，约16px"),
            "FONT_SIZE_LG": ("size", "大字号", "二级标题、重要信息，约18px"),
            "FONT_SIZE_XL": ("size", "超大字号", "一级标题，约20-24px"),
            "FONT_SIZE_2XL": ("size", "特大字号", "页面主标题，约28-32px"),
            "FONT_SIZE_3XL": ("size", "超特大字号", "超大展示标题，约36-48px"),
            "FONT_WEIGHT_NORMAL": ("text", "正常粗细", "正文默认字重，通常为400"),
            "FONT_WEIGHT_MEDIUM": ("text", "中等粗细", "略加强调的文字，通常为500"),
            "FONT_WEIGHT_SEMIBOLD": ("text", "半粗", "小标题、按钮文字，通常为600"),
            "FONT_WEIGHT_BOLD": ("text", "粗体", "标题、重要强调，通常为700"),
            "LINE_HEIGHT_TIGHT": ("text", "紧凑行高", "标题等短文本的行高，约1.2-1.3"),
            "LINE_HEIGHT_NORMAL": ("text", "正常行高", "正文默认行高，约1.5"),
            "LINE_HEIGHT_RELAXED": ("text", "宽松行高", "长文阅读的舒适行高，约1.6-1.7"),
            "LINE_HEIGHT_LOOSE": ("text", "超宽松行高", "特别强调可读性的行高，约1.8-2"),
        }
    },
    "border_radius": {
        "label": "圆角配置",
        "description": "各元素的圆角尺寸，影响整体视觉风格",
        "fields": {
            "RADIUS_XS": ("size", "超小圆角", "微小圆角，约2px，用于小型元素如标签"),
            "RADIUS_SM": ("size", "小圆角", "小圆角，约4px，用于按钮、输入框"),
            "RADIUS_MD": ("size", "中等圆角", "中等圆角，约6-8px，用于卡片、面板"),
            "RADIUS_LG": ("size", "大圆角", "大圆角，约12px，用于大型卡片、对话框"),
            "RADIUS_XL": ("size", "超大圆角", "超大圆角，约16px，用于特殊强调元素"),
            "RADIUS_2XL": ("size", "特大圆角", "特大圆角，约20-24px"),
            "RADIUS_3XL": ("size", "超特大圆角", "超特大圆角，约28-32px，接近椭圆"),
            "RADIUS_ROUND": ("text", "圆形", "完全圆形，值为50%，用于头像、圆形按钮"),
            "RADIUS_PILL": ("text", "药丸形", "药丸/胶囊形，值为9999px，用于标签、徽章"),
        }
    },
    "spacing": {
        "label": "间距配置",
        "description": "元素之间的间距尺寸，遵循8pt网格系统",
        "fields": {
            "SPACING_XS": ("size", "超小间距", "最小间距，约4px，用于紧凑元素内部"),
            "SPACING_SM": ("size", "小间距", "小间距，约8px，用于相关元素之间"),
            "SPACING_MD": ("size", "中等间距", "中等间距，约12-16px，用于分组内元素"),
            "SPACING_LG": ("size", "大间距", "大间距，约20-24px，用于分组之间"),
            "SPACING_XL": ("size", "超大间距", "超大间距，约32px，用于大区块分隔"),
            "SPACING_XXL": ("size", "特大间距", "特大间距，约48px，用于页面级分隔"),
        }
    },
    "animation": {
        "label": "动画配置",
        "description": "过渡动画的时长和缓动曲线",
        "fields": {
            "TRANSITION_FAST": ("size", "快速过渡", "快速动画，约100-150ms，用于按钮悬浮等即时反馈"),
            "TRANSITION_BASE": ("size", "标准过渡", "标准动画，约200-300ms，用于一般交互效果"),
            "TRANSITION_SLOW": ("size", "缓慢过渡", "缓慢动画，约400-500ms，用于页面切换、大型动画"),
            "TRANSITION_DRAMATIC": ("size", "戏剧性过渡", "戏剧性动画，约600-800ms，用于强调效果"),
            "EASING_DEFAULT": ("text", "默认缓动", "动画缓动曲线，如 ease-in-out、cubic-bezier(...)"),
        }
    },
    "button_sizes": {
        "label": "按钮尺寸",
        "description": "不同尺寸按钮的高度和内边距",
        "fields": {
            "BUTTON_HEIGHT_SM": ("size", "小按钮高度", "小型按钮的高度，约28-32px，用于紧凑布局"),
            "BUTTON_HEIGHT_DEFAULT": ("size", "默认按钮高度", "标准按钮的高度，约36-40px，最常用"),
            "BUTTON_HEIGHT_LG": ("size", "大按钮高度", "大型按钮的高度，约44-48px，用于重要操作"),
            "BUTTON_PADDING_SM": ("size", "小按钮内边距", "小型按钮的左右内边距，约12px"),
            "BUTTON_PADDING_DEFAULT": ("size", "默认按钮内边距", "标准按钮的左右内边距，约16-20px"),
            "BUTTON_PADDING_LG": ("size", "大按钮内边距", "大型按钮的左右内边距，约24-32px"),
        }
    },
    "transparency": {
        "label": "透明度配置",
        "description": "控制各UI组件的透明度，实现毛玻璃效果",
        "fields": {
            # 总开关 - switch类型自带标签
            "TRANSPARENCY_ENABLED": ("switch", "启用透明效果", "开启后界面将显示半透明效果"),
            "SYSTEM_BLUR": ("switch", "系统级模糊", "仅Windows有效，使用系统原生模糊API"),
            # 布局组件 (范围0-100，内部转换为0-1)
            "SIDEBAR_OPACITY": ("slider", "侧边栏透明度", {"min": 0, "max": 100, "step": 1, "default": 85}),
            "HEADER_OPACITY": ("slider", "标题栏透明度", {"min": 0, "max": 100, "step": 1, "default": 90}),
            "CONTENT_OPACITY": ("slider", "内容区透明度", {"min": 0, "max": 100, "step": 1, "default": 95}),
            # 浮层组件
            "DIALOG_OPACITY": ("slider", "对话框透明度", {"min": 0, "max": 100, "step": 1, "default": 95}),
            "MODAL_OPACITY": ("slider", "模态框透明度", {"min": 0, "max": 100, "step": 1, "default": 92}),
            "DROPDOWN_OPACITY": ("slider", "下拉菜单透明度", {"min": 0, "max": 100, "step": 1, "default": 95}),
            "TOOLTIP_OPACITY": ("slider", "工具提示透明度", {"min": 0, "max": 100, "step": 1, "default": 90}),
            "POPOVER_OPACITY": ("slider", "弹出框透明度", {"min": 0, "max": 100, "step": 1, "default": 92}),
            # 卡片组件
            "CARD_OPACITY": ("slider", "卡片透明度", {"min": 0, "max": 100, "step": 1, "default": 95}),
            "CARD_GLASS_OPACITY": ("slider", "玻璃卡片透明度", {"min": 0, "max": 100, "step": 1, "default": 85}),
            # 反馈组件
            "OVERLAY_OPACITY": ("slider", "遮罩层透明度", {"min": 0, "max": 100, "step": 1, "default": 50}),
            "LOADING_OPACITY": ("slider", "加载层透明度", {"min": 0, "max": 100, "step": 1, "default": 85}),
            "TOAST_OPACITY": ("slider", "消息提示透明度", {"min": 0, "max": 100, "step": 1, "default": 95}),
            # 输入组件
            "INPUT_OPACITY": ("slider", "输入框透明度", {"min": 0, "max": 100, "step": 1, "default": 98}),
            "BUTTON_OPACITY": ("slider", "按钮透明度", {"min": 0, "max": 100, "step": 1, "default": 100}),
        }
    },
}


__all__ = [
    "CONFIG_GROUPS",
]
