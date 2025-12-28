"""
编辑请求分发Mixin

负责处理各类编辑请求，包括简单字段、世界观、角色、关系等。
"""

import logging
from typing import TYPE_CHECKING

from utils.message_service import MessageService

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class EditDispatcherMixin:
    """
    编辑请求分发Mixin

    负责：
    - 接收并分发编辑请求
    - 处理简单字段编辑
    - 处理世界观字段编辑
    - 处理角色和关系列表编辑
    - 暂存编辑到脏数据追踪器
    - 更新Section显示
    """

    def onEditRequested(self: "NovelDetail", field, label, value):
        """处理编辑请求 - 暂存修改，不立即保存

        支持的字段类型：
        1. 章节大纲: chapter_outline:N
        2. 简单文本字段: one_sentence_summary, genre, style, tone, target_audience, full_synopsis
        3. 世界观文本字段: world_setting.core_rules
        4. 世界观列表字段: world_setting.key_locations, world_setting.factions
        5. 角色列表: characters
        6. 关系列表: relationships
        """
        logger.info(f"onEditRequested: field={field}, label={label}, value_type={type(value).__name__}")

        # 1. 章节大纲编辑请求（来自ChapterOutlineSection）
        if field.startswith('chapter_outline:'):
            self._stageChapterOutlineEdit(value)
            return

        # 2. 世界观相关字段
        if field.startswith('world_setting.'):
            self._handleWorldSettingEdit(field, label, value)
            return

        # 3. 角色列表
        if field == 'characters':
            self._handleCharactersEdit(label, value)
            return

        # 4. 关系列表
        if field == 'relationships':
            self._handleRelationshipsEdit(label, value)
            return

        # 5. 简单蓝图字段 - 使用EditDialog
        self._handleSimpleFieldEdit(field, label, value)

    def _handleSimpleFieldEdit(self: "NovelDetail", field, label, value):
        """处理简单文本字段编辑"""
        from ..dialogs import EditDialog

        # 确定是否多行编辑（长文本字段）
        multiline_fields = ['full_synopsis', 'one_sentence_summary']
        multiline = field in multiline_fields

        # 显示编辑对话框
        dialog = EditDialog(label, value, multiline=multiline, parent=self)
        if dialog.exec() != EditDialog.DialogCode.Accepted:
            return

        new_value = dialog.getValue()
        if not new_value or new_value == str(value):
            return

        # 暂存修改到脏数据追踪器
        self._stageFieldEdit(field, value, new_value, label)

    def _handleWorldSettingEdit(self: "NovelDetail", field, label, value):
        """处理世界观字段编辑"""
        from ..dialogs import EditDialog

        # world_setting.core_rules - 文本字段
        if field == 'world_setting.core_rules':
            dialog = EditDialog(label, value or '', multiline=True, parent=self)
            if dialog.exec() != EditDialog.DialogCode.Accepted:
                return

            new_value = dialog.getValue()
            if new_value == (value or ''):
                return

            self._stageFieldEdit(field, value, new_value, label)
            return

        # world_setting.key_locations, world_setting.factions - 列表字段
        if field in ['world_setting.key_locations', 'world_setting.factions']:
            from ..dialogs import ListEditDialog

            items = value if isinstance(value, list) else []
            dialog = ListEditDialog(
                title=f"编辑{label}",
                items=items,
                item_fields=['name', 'description'],
                field_labels={'name': '名称', 'description': '描述'},
                parent=self
            )

            if dialog.exec() != ListEditDialog.DialogCode.Accepted:
                return

            new_items = dialog.get_items()
            # 简单比较（可能不完美但足够）
            if new_items == items:
                return

            self._stageFieldEdit(field, value, new_items, label)

    def _handleCharactersEdit(self: "NovelDetail", label, value):
        """处理角色列表编辑"""
        from ..dialogs import CharacterListEditDialog

        characters = value if isinstance(value, list) else []
        dialog = CharacterListEditDialog(characters=characters, parent=self)

        if dialog.exec() != CharacterListEditDialog.DialogCode.Accepted:
            return

        new_characters = dialog.get_characters()
        if new_characters == characters:
            return

        self._stageFieldEdit('characters', value, new_characters, label)

    def _handleRelationshipsEdit(self: "NovelDetail", label, value):
        """处理关系列表编辑"""
        from ..dialogs import RelationshipListEditDialog

        # 获取角色列表用于选择
        characters = []
        if self.project_data and self.project_data.get('blueprint'):
            characters = self.project_data['blueprint'].get('characters', [])

        relationships = value if isinstance(value, list) else []
        dialog = RelationshipListEditDialog(
            relationships=relationships,
            characters=characters,
            parent=self
        )

        if dialog.exec() != RelationshipListEditDialog.DialogCode.Accepted:
            return

        new_relationships = dialog.get_relationships()
        if new_relationships == relationships:
            return

        self._stageFieldEdit('relationships', value, new_relationships, label)

    def _stageChapterOutlineEdit(self: "NovelDetail", edit_data: dict):
        """暂存章节大纲编辑（不立即保存到后端）"""
        chapter_number = edit_data.get('chapter_number')
        original_title = edit_data.get('original_title', '')
        original_summary = edit_data.get('original_summary', '')
        new_title = edit_data.get('new_title', '')
        new_summary = edit_data.get('new_summary', '')

        # 标记为脏数据
        self.dirty_tracker.mark_outline_dirty(
            chapter_number=chapter_number,
            original_title=original_title,
            original_summary=original_summary,
            current_title=new_title,
            current_summary=new_summary,
            is_new=False
        )

        # 更新保存按钮状态
        self._updateSaveButtonStyle()

    def _stageFieldEdit(self: "NovelDetail", field, original_value, new_value, label):
        """暂存字段修改（不立即保存到后端）

        支持的字段类型：
        1. 简单蓝图字段: one_sentence_summary, genre, style, tone, target_audience, full_synopsis, title
        2. 世界观字段: world_setting.core_rules, world_setting.key_locations, world_setting.factions
        3. 复杂列表字段: characters, relationships
        """
        # 所有支持的字段
        simple_blueprint_fields = [
            'one_sentence_summary', 'genre', 'style', 'tone',
            'target_audience', 'full_synopsis', 'title'
        ]
        world_setting_fields = [
            'world_setting.core_rules',
            'world_setting.key_locations',
            'world_setting.factions'
        ]
        complex_list_fields = ['characters', 'relationships']

        all_supported_fields = simple_blueprint_fields + world_setting_fields + complex_list_fields

        if field not in all_supported_fields:
            MessageService.show_warning(self, f"暂不支持编辑该字段：{label}", "提示")
            return

        # 标记为脏数据
        self.dirty_tracker.mark_field_dirty(
            section=self.active_section,
            field=field,
            original_value=original_value,
            current_value=new_value
        )

        # 更新保存按钮状态
        self._updateSaveButtonStyle()

        # 更新当前section的显示（本地更新，不重新从后端加载）
        self._updateSectionDisplay(field, new_value)

    def _updateSectionDisplay(self: "NovelDetail", field, new_value):
        """更新当前section的显示（本地更新）

        支持的字段类型：
        1. 简单蓝图字段: one_sentence_summary, genre, style, tone等
        2. 世界观字段: world_setting.core_rules, world_setting.key_locations等
        3. 复杂列表字段: characters, relationships
        """
        if not self.project_data or not self.project_data.get('blueprint'):
            return

        blueprint = self.project_data.get('blueprint', {})

        # 更新本地缓存
        if field.startswith('world_setting.'):
            # 世界观嵌套字段
            sub_field = field.replace('world_setting.', '')
            if 'world_setting' not in blueprint:
                blueprint['world_setting'] = {}
            blueprint['world_setting'][sub_field] = new_value
        else:
            # 简单字段或复杂列表字段
            blueprint[field] = new_value

        # 刷新对应的section显示
        if self.active_section not in self.section_widgets:
            return

        widget = self.section_widgets[self.active_section]
        scroll_widget = widget.widget()
        if not scroll_widget:
            return

        layout = scroll_widget.layout()
        if not layout or layout.count() == 0:
            return

        section = layout.itemAt(0).widget()

        # 尝试调用section的局部更新方法
        if hasattr(section, 'updateField'):
            section.updateField(field, new_value)
        elif hasattr(section, 'updateData'):
            # 根据当前section类型调用updateData
            if self.active_section == 'overview':
                section.updateData(blueprint)
            elif self.active_section == 'world_setting':
                world_setting = blueprint.get('world_setting', {})
                section.updateData(world_setting)
            elif self.active_section == 'characters':
                characters = blueprint.get('characters', [])
                section.updateData(characters)
            elif self.active_section == 'relationships':
                relationships = blueprint.get('relationships', [])
                section.updateData(relationships)


__all__ = [
    "EditDispatcherMixin",
]
