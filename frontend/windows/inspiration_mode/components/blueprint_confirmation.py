"""
蓝图确认界面

在生成蓝图后显示详细内容供用户确认
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QWidget, QFrame, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from components.base import ThemeAwareWidget
from themes.theme_manager import theme_manager
from themes import ButtonStyles
from utils.dpi_utils import dp, sp

logger = logging.getLogger(__name__)


class BlueprintConfirmation(ThemeAwareWidget):
    """蓝图确认界面 - 展示详细蓝图内容"""

    confirmed = pyqtSignal()
    rejected = pyqtSignal()

    def __init__(self, blueprint=None, parent=None):
        self.blueprint = blueprint or {}

        # 保存组件引用
        self.title_label = None
        self.genre_label = None
        self.audience_label = None
        self.summary_label = None
        self.synopsis_label = None
        self.world_setting_label = None
        self.characters_container = None
        self.characters_layout = None  # 角色列表布局
        self.chapter_count_label = None
        self.confirm_btn = None
        self.reject_btn = None
        self.scroll_area = None

        logger.info("BlueprintConfirmation.__init__ 初始化完成")
        super().__init__(parent)
        self.setupUI()

    def _create_ui_structure(self):
        """创建UI结构（只调用一次）"""
        logger.info("BlueprintConfirmation._create_ui_structure 开始")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部标题栏
        header = QFrame()
        header.setFixedHeight(dp(64))
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(dp(24), 0, dp(24), 0)

        header_title = QLabel("蓝图预览")
        header_title.setObjectName("header_title")
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # 可滚动内容区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        # 设置尺寸策略，确保内容区域不会超出滚动区域宽度
        content_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(dp(24), dp(16), dp(24), dp(24))
        content_layout.setSpacing(dp(20))

        # 成功图标和标题
        success_section = QWidget()
        success_layout = QVBoxLayout(success_section)
        success_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.setSpacing(dp(12))

        icon = QLabel("*")
        icon.setObjectName("success_icon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(icon)

        success_title = QLabel("蓝图生成完成！")
        success_title.setObjectName("success_title")
        success_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        success_layout.addWidget(success_title)

        content_layout.addWidget(success_section)

        # 基本信息卡片
        basic_card = self._create_card("基本信息")
        basic_layout = basic_card.layout()

        # 标题
        self.title_label = self._create_info_row("书名", "")
        basic_layout.addWidget(self.title_label)

        # 类型和目标读者
        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(dp(24))

        self.genre_label = self._create_info_row("类型", "")
        meta_layout.addWidget(self.genre_label)

        self.audience_label = self._create_info_row("目标读者", "")
        meta_layout.addWidget(self.audience_label)

        self.chapter_count_label = self._create_info_row("预计章节", "")
        meta_layout.addWidget(self.chapter_count_label)

        meta_layout.addStretch()
        meta_widget = QWidget()
        meta_widget.setLayout(meta_layout)
        basic_layout.addWidget(meta_widget)

        content_layout.addWidget(basic_card)

        # 故事梗概卡片
        synopsis_card = self._create_card("故事梗概")
        synopsis_layout = synopsis_card.layout()

        self.summary_label = QLabel()
        self.summary_label.setObjectName("summary_label")
        self.summary_label.setWordWrap(True)
        self.summary_label.setMinimumWidth(0)
        synopsis_layout.addWidget(self.summary_label)

        self.synopsis_label = QLabel()
        self.synopsis_label.setObjectName("synopsis_label")
        self.synopsis_label.setWordWrap(True)
        self.synopsis_label.setMinimumWidth(0)
        synopsis_layout.addWidget(self.synopsis_label)

        content_layout.addWidget(synopsis_card)

        # 世界观设置卡片
        world_card = self._create_card("世界观设置")
        world_layout = world_card.layout()

        self.world_setting_label = QLabel()
        self.world_setting_label.setObjectName("world_setting_label")
        self.world_setting_label.setWordWrap(True)
        self.world_setting_label.setMinimumWidth(0)  # 允许缩小到0
        self.world_setting_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        world_layout.addWidget(self.world_setting_label)

        content_layout.addWidget(world_card)

        # 角色列表卡片
        characters_card = self._create_card("主要角色")
        characters_layout = characters_card.layout()

        self.characters_container = QWidget()
        self.characters_layout = QVBoxLayout(self.characters_container)
        self.characters_layout.setContentsMargins(0, 0, 0, 0)
        self.characters_layout.setSpacing(dp(12))
        characters_layout.addWidget(self.characters_container)
        logger.info("characters_layout 创建完成")

        content_layout.addWidget(characters_card)

        content_layout.addStretch()

        self.scroll_area.setWidget(content_widget)
        main_layout.addWidget(self.scroll_area, stretch=1)

        # 底部按钮栏
        footer = QFrame()
        footer.setFixedHeight(dp(72))
        footer.setObjectName("footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(dp(24), dp(12), dp(24), dp(12))
        footer_layout.setSpacing(dp(16))

        footer_layout.addStretch()

        self.reject_btn = QPushButton("重新生成")
        self.reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reject_btn.setMinimumWidth(dp(120))
        self.reject_btn.clicked.connect(self.rejected.emit)
        footer_layout.addWidget(self.reject_btn)

        self.confirm_btn = QPushButton("确认并继续")
        self.confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.confirm_btn.setMinimumWidth(dp(120))
        self.confirm_btn.clicked.connect(self.confirmed.emit)
        footer_layout.addWidget(self.confirm_btn)

        main_layout.addWidget(footer)

        logger.info("BlueprintConfirmation._create_ui_structure 完成")

    def _create_card(self, title):
        """创建卡片容器"""
        card = QFrame()
        card.setObjectName("blueprint_card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(dp(16), dp(16), dp(16), dp(16))
        layout.setSpacing(dp(12))

        title_label = QLabel(title)
        title_label.setObjectName("card_title")
        layout.addWidget(title_label)

        return card

    def _create_info_row(self, label, value):
        """创建信息行"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(dp(8))

        label_widget = QLabel(f"{label}:")
        label_widget.setObjectName("info_label")
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setObjectName("info_value")
        value_widget.setWordWrap(True)  # 启用自动换行
        layout.addWidget(value_widget, stretch=1)  # 让值标签占据剩余空间

        # 存储value_widget的引用以便后续更新
        widget.value_widget = value_widget
        return widget

    def _create_character_item(self, character):
        """创建角色项"""
        item = QFrame()
        item.setObjectName("character_item")
        layout = QVBoxLayout(item)
        layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        layout.setSpacing(dp(6))

        # 角色名称
        name = character.get('name', '未知角色')
        name_label = QLabel(name)
        name_label.setObjectName("character_name")
        layout.addWidget(name_label)

        # 角色身份（identity）
        identity = character.get('identity', '')
        if identity:
            identity_label = QLabel(f"身份: {identity}")
            identity_label.setObjectName("character_identity")
            identity_label.setWordWrap(True)
            layout.addWidget(identity_label)

        # 性格特点
        personality = character.get('personality', '')
        if personality:
            personality_label = QLabel(f"性格: {personality}")
            personality_label.setObjectName("character_desc")
            personality_label.setWordWrap(True)
            layout.addWidget(personality_label)

        # 人物目标
        goals = character.get('goals', '')
        if goals:
            goals_label = QLabel(f"目标: {goals}")
            goals_label.setObjectName("character_desc")
            goals_label.setWordWrap(True)
            layout.addWidget(goals_label)

        # 能力特长
        abilities = character.get('abilities', '')
        if abilities:
            abilities_label = QLabel(f"能力: {abilities}")
            abilities_label.setObjectName("character_desc")
            abilities_label.setWordWrap(True)
            layout.addWidget(abilities_label)

        # 与主角关系
        relationship = character.get('relationship_to_protagonist', '')
        if relationship:
            rel_label = QLabel(f"与主角关系: {relationship}")
            rel_label.setObjectName("character_desc")
            rel_label.setWordWrap(True)
            layout.addWidget(rel_label)

        # 兼容旧格式：如果有description字段则显示
        description = character.get('description', '')
        if description and not personality and not goals:
            desc_label = QLabel(description)
            desc_label.setObjectName("character_desc")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        return item

    def _apply_theme(self):
        """应用主题样式（可多次调用）"""
        # 整体背景 - 注意：不使用Python类名选择器，Qt不识别Python类名
        # 使用通配符*来匹配根组件，再使用objectName选择器匹配子组件
        self.setStyleSheet(f"""
            * {{
                background-color: {theme_manager.BG_PRIMARY};
            }}
            #header_title {{
                font-size: {sp(20)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #success_icon {{
                font-size: {sp(48)}px;
                color: {theme_manager.SUCCESS};
            }}
            #success_title {{
                font-size: {sp(24)}px;
                font-weight: 700;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #blueprint_card {{
                background-color: {theme_manager.BG_CARD};
                border: 1px solid {theme_manager.BORDER_LIGHT};
                border-radius: {theme_manager.RADIUS_MD};
            }}
            #card_title {{
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.PRIMARY};
            }}
            #info_label {{
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_TERTIARY};
            }}
            #info_value {{
                font-size: {sp(14)}px;
                font-weight: 500;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #summary_label {{
                font-size: {sp(16)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
                line-height: 1.6;
            }}
            #synopsis_label {{
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.6;
            }}
            #world_setting_label {{
                font-size: {sp(14)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.6;
            }}
            #character_item {{
                background-color: {theme_manager.BG_TERTIARY};
                border-radius: {theme_manager.RADIUS_SM};
            }}
            #character_name {{
                font-size: {sp(14)}px;
                font-weight: 600;
                color: {theme_manager.TEXT_PRIMARY};
            }}
            #character_identity {{
                font-size: {sp(13)}px;
                color: {theme_manager.PRIMARY};
                font-weight: 500;
            }}
            #character_desc {{
                font-size: {sp(13)}px;
                color: {theme_manager.TEXT_SECONDARY};
                line-height: 1.4;
            }}
            #footer {{
                background-color: {theme_manager.BG_CARD};
                border-top: 1px solid {theme_manager.BORDER_LIGHT};
            }}
        """)

        # 滚动区域样式
        if self.scroll_area:
            self.scroll_area.setStyleSheet(f"""
                QScrollArea {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea > QWidget > QWidget {{
                    background: transparent;
                }}
                {theme_manager.scrollbar()}
            """)

        # 按钮样式
        if self.confirm_btn:
            self.confirm_btn.setStyleSheet(ButtonStyles.primary())

        if self.reject_btn:
            self.reject_btn.setStyleSheet(ButtonStyles.secondary())

    def setBlueprint(self, blueprint):
        """更新蓝图数据并刷新显示"""
        self.blueprint = blueprint

        logger.info(f"setBlueprint: 蓝图键={list(blueprint.keys()) if blueprint else 'None'}")

        # 打印角色数据用于调试
        characters = blueprint.get('characters', [])
        logger.info(f"角色数据: 共{len(characters)}个角色")
        for i, char in enumerate(characters[:3]):  # 只打印前3个
            logger.info(f"  角色{i+1}: {char.get('name', 'N/A')} - {list(char.keys())}")

        # 更新标题
        title = blueprint.get('title', '未命名作品')
        if self.title_label and hasattr(self.title_label, 'value_widget'):
            self.title_label.value_widget.setText(title)

        # 更新类型
        genre = blueprint.get('genre', '未知类型')
        if self.genre_label and hasattr(self.genre_label, 'value_widget'):
            self.genre_label.value_widget.setText(genre)

        # 更新目标读者
        audience = blueprint.get('target_audience', '未指定')
        if self.audience_label and hasattr(self.audience_label, 'value_widget'):
            self.audience_label.value_widget.setText(audience)

        # 更新章节数
        chapter_outline = blueprint.get('chapter_outline', [])
        total_chapters = blueprint.get('total_chapters', len(chapter_outline))
        if self.chapter_count_label and hasattr(self.chapter_count_label, 'value_widget'):
            self.chapter_count_label.value_widget.setText(f"{total_chapters} 章")

        # 更新一句话摘要
        summary = blueprint.get('one_sentence_summary', '')
        if self.summary_label:
            self.summary_label.setText(summary if summary else '暂无摘要')

        # 更新完整梗概
        synopsis = blueprint.get('full_synopsis', '')
        if self.synopsis_label:
            self.synopsis_label.setText(synopsis if synopsis else '暂无详细梗概')
            self.synopsis_label.setVisible(bool(synopsis))

        # 更新世界观设置
        world_setting = blueprint.get('world_setting', {})
        if self.world_setting_label:
            world_text = self._format_world_setting(world_setting)
            self.world_setting_label.setText(world_text if world_text else '暂无世界观设置')

        # 更新角色列表
        self._update_characters(blueprint.get('characters', []))

    def _format_world_setting(self, world_setting):
        """格式化世界观设置"""
        if not world_setting:
            return ""

        parts = []

        # 字段名称映射（英文键 -> 中文显示名）
        field_names = {
            'era': '时代背景',
            'time_period': '时代背景',
            'location': '故事地点',
            'setting': '故事地点',
            'society': '社会背景',
            'social_context': '社会背景',
            'special_elements': '特殊设定',
            'unique_elements': '特殊设定',
            'core_rules': '核心规则',
            'magic_system': '魔法体系',
            'technology_level': '科技水平',
            'political_system': '政治体系',
            'economic_system': '经济体系',
            'culture': '文化背景',
            'religion': '宗教信仰',
            'history': '历史背景',
            'geography': '地理环境',
            'climate': '气候环境',
            'key_locations': '关键地点',
            'factions': '势力阵营',
            'organizations': '组织势力',
            'powers': '力量体系',
            'rules': '世界规则',
        }

        # 简单文本字段（优先显示）
        simple_fields = ['era', 'time_period', 'location', 'setting', 'society',
                        'social_context', 'core_rules', 'magic_system', 'technology_level']

        # 复杂列表字段（单独处理）
        complex_fields = ['key_locations', 'factions', 'organizations', 'special_elements', 'unique_elements']

        # 先处理简单字段
        processed_keys = set()
        for key in simple_fields:
            if key in world_setting and world_setting[key]:
                value = world_setting[key]
                # 只处理字符串类型的值
                if isinstance(value, str):
                    display_name = field_names.get(key, key)
                    parts.append(f"{display_name}: {value}")
                    processed_keys.add(key)

        # 处理复杂列表字段
        for key in complex_fields:
            if key in world_setting and world_setting[key]:
                value = world_setting[key]
                display_name = field_names.get(key, self._format_key_name(key))
                formatted = self._format_complex_list(value, display_name)
                if formatted:
                    parts.append(formatted)
                processed_keys.add(key)

        # 处理剩余字段
        for key, value in world_setting.items():
            if key in processed_keys or not value:
                continue

            display_name = field_names.get(key, self._format_key_name(key))

            if isinstance(value, str):
                parts.append(f"{display_name}: {value}")
            elif isinstance(value, list):
                formatted = self._format_complex_list(value, display_name)
                if formatted:
                    parts.append(formatted)
            elif isinstance(value, dict):
                formatted = self._format_nested_dict(value, display_name)
                if formatted:
                    parts.append(formatted)

        return "\n\n".join(parts)

    def _format_complex_list(self, items, title):
        """格式化复杂列表（如key_locations、factions）"""
        if not items:
            return ""

        if isinstance(items, str):
            return f"{title}: {items}"

        if not isinstance(items, list):
            return f"{title}: {str(items)}"

        formatted_items = []
        for item in items:
            if isinstance(item, dict):
                # 提取name和description
                name = item.get('name', '')
                desc = item.get('description', item.get('role', item.get('summary', '')))
                if name:
                    if desc:
                        formatted_items.append(f"  - {name}: {desc}")
                    else:
                        formatted_items.append(f"  - {name}")
                elif desc:
                    formatted_items.append(f"  - {desc}")
            elif isinstance(item, str):
                formatted_items.append(f"  - {item}")

        if formatted_items:
            return f"{title}:\n" + "\n".join(formatted_items)
        return ""

    def _format_nested_dict(self, data, title):
        """格式化嵌套字典"""
        if not data:
            return ""

        if isinstance(data, str):
            return f"{title}: {data}"

        parts = []
        for key, value in data.items():
            display_key = self._format_key_name(key)
            if isinstance(value, str):
                parts.append(f"  - {display_key}: {value}")
            elif isinstance(value, list):
                str_items = [str(v) for v in value if v]
                if str_items:
                    parts.append(f"  - {display_key}: {'、'.join(str_items)}")

        if parts:
            return f"{title}:\n" + "\n".join(parts)
        return ""

    def _format_setting_value(self, value):
        """格式化设置值，处理字符串、列表和字典"""
        if isinstance(value, str):
            return value
        elif isinstance(value, list):
            # 列表：检查元素类型
            str_items = []
            for item in value:
                if isinstance(item, str):
                    str_items.append(item)
                elif isinstance(item, dict):
                    # 字典项：提取name或description
                    name = item.get('name', '')
                    if name:
                        str_items.append(name)
            return '、'.join(str_items) if str_items else ''
        elif isinstance(value, dict):
            # 字典：递归格式化为缩进形式
            sub_parts = []
            for k, v in value.items():
                display_key = self._format_key_name(k)
                formatted_v = self._format_setting_value(v)
                if formatted_v:
                    sub_parts.append(f"  - {display_key}: {formatted_v}")
            return '\n' + '\n'.join(sub_parts) if sub_parts else ''
        else:
            return str(value) if value else ''

    def _format_key_name(self, key):
        """将下划线分隔的键名转换为更友好的显示格式"""
        # 将下划线替换为空格，首字母大写
        return key.replace('_', ' ').title()

    def _update_characters(self, characters):
        """更新角色列表"""
        logger.info(f"_update_characters: 接收到 {len(characters) if characters else 0} 个角色")

        if self.characters_layout is None:
            logger.warning("characters_layout为None，无法更新角色列表")
            return

        # 清空现有角色
        while self.characters_layout.count():
            item = self.characters_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加新角色
        if not characters:
            logger.info("角色列表为空，显示暂无角色信息提示")
            no_char_label = QLabel("暂无角色信息")
            no_char_label.setStyleSheet(f"color: {theme_manager.TEXT_TERTIARY}; font-size: {sp(14)}px;")
            self.characters_layout.addWidget(no_char_label)
        else:
            for character in characters[:6]:  # 最多显示6个角色
                char_item = self._create_character_item(character)
                self.characters_layout.addWidget(char_item)
                logger.info(f"添加角色卡片: {character.get('name', 'N/A')}")

            if len(characters) > 6:
                more_label = QLabel(f"还有 {len(characters) - 6} 个角色...")
                more_label.setStyleSheet(f"color: {theme_manager.TEXT_TERTIARY}; font-size: {sp(13)}px;")
                self.characters_layout.addWidget(more_label)

        logger.info(f"角色列表更新完成，当前布局中有 {self.characters_layout.count()} 个组件")
