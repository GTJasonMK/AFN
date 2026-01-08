"""
编辑请求分发Mixin

负责处理编程项目各类编辑请求。
"""

import logging
from typing import TYPE_CHECKING

from utils.message_service import MessageService

if TYPE_CHECKING:
    from ..main import CodingDetail

logger = logging.getLogger(__name__)


class EditDispatcherMixin:
    """编辑请求分发Mixin

    负责：
    - 接收并分发编辑请求
    - 处理简单字段编辑
    - 处理模块编辑
    - 处理功能大纲编辑
    - 处理依赖关系编辑
    - 暂存编辑到脏数据追踪器
    """

    def onEditRequested(self: "CodingDetail", field, label, value):
        """处理编辑请求

        支持的字段类型：
        1. 功能大纲: features.add, features:N
        2. 模块: modules.add, modules.{name}
        3. 依赖: dependencies.add
        4. 技术栈: tech_stack.*
        5. 简单字段: project_name, project_type_desc等
        """
        logger.info(f"onEditRequested: field={field}, label={label}, value_type={type(value).__name__}")

        # 1. 功能大纲添加
        if field == 'features.add':
            self._handleAddFeature()
            return

        # 2. 模块添加
        if field == 'modules.add':
            self._handleAddModule()
            return

        # 3. 模块编辑
        if field.startswith('modules.') and field != 'modules.add':
            self._handleEditModule(field, label, value)
            return

        # 4. 依赖添加
        if field == 'dependencies.add':
            self._handleAddDependency()
            return

        # 5. 技术栈编辑
        if field.startswith('tech_stack.'):
            self._handleTechStackEdit(field, label, value)
            return

        # 6. 简单字段编辑
        self._handleSimpleFieldEdit(field, label, value)

    def _handleSimpleFieldEdit(self: "CodingDetail", field, label, value):
        """处理简单文本字段编辑"""
        from windows.novel_detail.dialogs import EditDialog

        # 确定是否多行编辑
        multiline_fields = ['project_description', 'summary']
        multiline = field in multiline_fields

        dialog = EditDialog(label, value or '', multiline=multiline, parent=self)
        if dialog.exec() != EditDialog.DialogCode.Accepted:
            return

        new_value = dialog.getValue()
        if not new_value or new_value == str(value):
            return

        self._stageFieldEdit(field, value, new_value, label)

    def _handleTechStackEdit(self: "CodingDetail", field, label, value):
        """处理技术栈字段编辑"""
        from windows.novel_detail.dialogs import EditDialog

        # tech_stack.languages, tech_stack.frameworks 等是列表
        sub_field = field.replace('tech_stack.', '')
        list_fields = ['languages', 'frameworks', 'libraries', 'tools']

        if sub_field in list_fields:
            # 列表字段，转换为逗号分隔的字符串编辑
            current_text = ', '.join(value) if isinstance(value, list) else str(value or '')
            dialog = EditDialog(label, current_text, multiline=False, parent=self)
            if dialog.exec() != EditDialog.DialogCode.Accepted:
                return

            new_text = dialog.getValue()
            if not new_text:
                return

            # 转换回列表
            new_value = [item.strip() for item in new_text.split(',') if item.strip()]
            if new_value == value:
                return

            self._stageFieldEdit(field, value, new_value, label)
        else:
            # 简单文本字段
            dialog = EditDialog(label, value or '', multiline=True, parent=self)
            if dialog.exec() != EditDialog.DialogCode.Accepted:
                return

            new_value = dialog.getValue()
            if not new_value or new_value == str(value):
                return

            self._stageFieldEdit(field, value, new_value, label)

    def _handleAddFeature(self: "CodingDetail"):
        """添加功能"""
        from windows.novel_detail.dialogs import ListEditDialog

        dialog = ListEditDialog(
            title="添加功能",
            items=[],
            item_fields=['name', 'description'],
            field_labels={'name': '功能名称', 'description': '功能描述'},
            parent=self
        )

        if dialog.exec() != ListEditDialog.DialogCode.Accepted:
            return

        new_items = dialog.get_items()
        if not new_items:
            return

        # 获取当前功能列表并添加新功能
        blueprint = self.get_blueprint()
        current_features = blueprint.get('chapter_outline', [])

        for item in new_items:
            new_feature = {
                'title': item.get('name', ''),
                'summary': item.get('description', ''),
                'priority': 'medium',
                'status': 'pending'
            }
            current_features.append(new_feature)

        self._stageFieldEdit('chapter_outline', blueprint.get('chapter_outline', []), current_features, '功能大纲')
        MessageService.show_info(self, f"已添加 {len(new_items)} 个功能", "提示")

    def _handleAddModule(self: "CodingDetail"):
        """添加模块"""
        from windows.novel_detail.dialogs import ListEditDialog

        dialog = ListEditDialog(
            title="添加模块",
            items=[],
            item_fields=['name', 'description'],
            field_labels={'name': '模块名称', 'description': '模块描述'},
            parent=self
        )

        if dialog.exec() != ListEditDialog.DialogCode.Accepted:
            return

        new_items = dialog.get_items()
        if not new_items:
            return

        # 获取当前模块列表并添加新模块
        blueprint = self.get_blueprint()
        current_modules = blueprint.get('modules', [])

        for item in new_items:
            new_module = {
                'name': item.get('name', ''),
                'description': item.get('description', ''),
                'type': 'module',
                'interface': '',
                'goals': [],
                'abilities': []
            }
            current_modules.append(new_module)

        self._stageFieldEdit('modules', blueprint.get('modules', []), current_modules, '模块列表')
        MessageService.show_info(self, f"已添加 {len(new_items)} 个模块", "提示")

    def _handleEditModule(self: "CodingDetail", field, label, value):
        """编辑模块"""
        from windows.novel_detail.dialogs import EditDialog

        if not isinstance(value, dict):
            MessageService.show_warning(self, "模块数据格式错误", "提示")
            return

        # 简单编辑模块描述
        current_desc = value.get('description', '')
        dialog = EditDialog(f"编辑模块描述: {value.get('name', '')}", current_desc, multiline=True, parent=self)

        if dialog.exec() != EditDialog.DialogCode.Accepted:
            return

        new_desc = dialog.getValue()
        if new_desc == current_desc:
            return

        # 更新模块
        blueprint = self.get_blueprint()
        modules = blueprint.get('modules', [])
        module_name = value.get('name', '')

        for module in modules:
            if module.get('name') == module_name:
                module['description'] = new_desc
                break

        self._stageFieldEdit('modules', blueprint.get('modules', []), modules, '模块列表')

    def _handleAddDependency(self: "CodingDetail"):
        """添加依赖关系"""
        from windows.novel_detail.dialogs import ListEditDialog

        blueprint = self.get_blueprint()
        modules = blueprint.get('modules', [])
        module_names = [m.get('name', '') for m in modules if m.get('name')]

        if len(module_names) < 2:
            MessageService.show_warning(self, "需要至少2个模块才能添加依赖关系", "提示")
            return

        dialog = ListEditDialog(
            title="添加依赖关系",
            items=[],
            item_fields=['name', 'description'],
            field_labels={'name': '依赖关系 (格式: 源模块 -> 目标模块)', 'description': '依赖描述'},
            parent=self
        )

        if dialog.exec() != ListEditDialog.DialogCode.Accepted:
            return

        new_items = dialog.get_items()
        if not new_items:
            return

        # 解析并添加依赖关系
        current_deps = blueprint.get('dependencies', [])

        for item in new_items:
            name = item.get('name', '')
            if ' -> ' in name:
                parts = name.split(' -> ')
                if len(parts) == 2:
                    new_dep = {
                        'source': parts[0].strip(),
                        'target': parts[1].strip(),
                        'type': 'uses',
                        'description': item.get('description', '')
                    }
                    current_deps.append(new_dep)

        self._stageFieldEdit('dependencies', blueprint.get('dependencies', []), current_deps, '依赖关系')
        MessageService.show_info(self, f"已添加依赖关系", "提示")

    def _stageFieldEdit(self: "CodingDetail", field, original_value, new_value, label):
        """暂存字段修改"""
        # 支持的字段
        supported_fields = [
            'project_name', 'project_type_desc', 'project_description',
            'tech_stack.languages', 'tech_stack.frameworks', 'tech_stack.libraries',
            'tech_stack.tools', 'tech_stack.architecture',
            'modules', 'dependencies', 'chapter_outline'
        ]

        if field not in supported_fields:
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

        # 更新当前section的显示
        self._updateSectionDisplay(field, new_value)

    def _updateSectionDisplay(self: "CodingDetail", field, new_value):
        """更新当前section的显示"""
        if not self.project_data:
            return

        # 获取coding_blueprint引用
        blueprint = self.project_data.get('coding_blueprint', {})
        if not blueprint:
            self.project_data['coding_blueprint'] = {}
            blueprint = self.project_data['coding_blueprint']

        # 更新本地缓存
        if field.startswith('tech_stack.'):
            sub_field = field.replace('tech_stack.', '')
            if 'tech_stack' not in blueprint:
                blueprint['tech_stack'] = {}
            blueprint['tech_stack'][sub_field] = new_value
        else:
            blueprint[field] = new_value

        # 刷新对应的section显示
        if self.active_section not in self.section_widgets:
            return

        widget = self.section_widgets[self.active_section]
        scroll_widget = widget.widget() if hasattr(widget, 'widget') else None
        if not scroll_widget:
            return

        layout = scroll_widget.layout()
        if not layout or layout.count() == 0:
            return

        section = layout.itemAt(0).widget()

        # 尝试调用section的更新方法
        if hasattr(section, 'updateData'):
            if self.active_section == 'overview':
                section.updateData(blueprint)
            elif self.active_section == 'tech_stack':
                section.updateData(blueprint.get('tech_stack', {}))
            elif self.active_section == 'modules':
                section.updateData(blueprint.get('modules', []))
            elif self.active_section == 'dependencies':
                section.updateData(blueprint.get('dependencies', []))
            elif self.active_section == 'features':
                section.updateData(blueprint.get('chapter_outline', []))


__all__ = ["EditDispatcherMixin"]
