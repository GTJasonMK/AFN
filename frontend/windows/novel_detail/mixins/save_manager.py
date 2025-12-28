"""
保存管理Mixin

负责批量保存、导出和未保存检查。
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog

from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService
from utils.error_handler import handle_errors

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class SaveManagerMixin:
    """
    保存管理Mixin

    负责：
    - 批量保存所有修改
    - 检查未保存的修改
    - 刷新当前Section
    - 编辑项目标题
    - 导出小说
    """

    def onSaveAll(self: "NovelDetail"):
        """批量保存所有修改"""
        if not self.dirty_tracker.is_dirty():
            MessageService.show_info(self, "没有需要保存的修改", "提示")
            return

        # 获取脏数据
        dirty_data = self.dirty_tracker.get_dirty_data()
        summary = self.dirty_tracker.get_dirty_summary()

        logger.info("开始批量保存: %s", summary)

        # 异步保存
        self._doSaveAll(dirty_data)

    def _doSaveAll(self: "NovelDetail", dirty_data):
        """执行批量保存（异步）"""
        from components.dialogs import LoadingDialog

        # 创建加载对话框
        loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在保存修改...",
            cancelable=False
        )
        loading_dialog.show()

        # 创建异步worker
        worker = AsyncAPIWorker(
            self.api_client.batch_update_blueprint,
            self.project_id,
            dirty_data.get("blueprint_updates"),
            dirty_data.get("chapter_outline_updates")
        )

        def on_success(result):
            loading_dialog.close()
            # 重置脏数据追踪器
            self.dirty_tracker.reset()
            # 更新保存按钮状态
            self._updateSaveButtonStyle()
            # 更新本地数据
            self.project_data = result
            # 刷新当前section
            self._refreshCurrentSection()
            MessageService.show_success(self, "保存成功")

        def on_error(error_msg):
            loading_dialog.close()
            MessageService.show_api_error(self, error_msg, "保存修改")

        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        worker.start()

    def _checkUnsavedChanges(self: "NovelDetail") -> bool:
        """检查未保存的修改，返回是否可以继续

        Returns:
            True: 可以继续（无修改或用户选择不保存/已保存）
            False: 用户取消操作
        """
        if not self.dirty_tracker.is_dirty():
            return True

        summary = self.dirty_tracker.get_dirty_summary()

        # 显示三按钮对话框
        from components.dialogs import SaveDiscardDialog, SaveDiscardResult

        dialog = SaveDiscardDialog(
            parent=self,
            title="确认离开",
            message=f"有未保存的修改（{summary}）",
            detail="是否保存修改？",
            save_text="保存",
            discard_text="不保存",
            cancel_text="取消"
        )

        result = dialog.exec()

        if result == SaveDiscardResult.SAVE:
            # 同步保存（阻塞）
            try:
                dirty_data = self.dirty_tracker.get_dirty_data()
                self.api_client.batch_update_blueprint(
                    self.project_id,
                    dirty_data.get("blueprint_updates"),
                    dirty_data.get("chapter_outline_updates")
                )
                self.dirty_tracker.reset()
                return True
            except Exception as e:
                MessageService.show_error(self, f"保存失败：{str(e)}", "错误")
                return False
        elif result == SaveDiscardResult.DISCARD:
            # 不保存，直接继续
            self.dirty_tracker.reset()
            return True
        else:
            # 取消
            return False

    @handle_errors("保存修改")
    def _saveFieldEdit(self: "NovelDetail", field, new_value, label):
        """保存字段修改到后端（已废弃，保留兼容性）"""
        # 构建更新数据
        blueprint_fields = [
            'one_sentence_summary', 'genre', 'style', 'tone',
            'target_audience', 'full_synopsis'
        ]

        if field in blueprint_fields:
            update_data = {field: new_value}
            self.api_client.update_blueprint(self.project_id, update_data)
        else:
            MessageService.show_warning(self, f"暂不支持编辑该字段：{label}", "提示")
            return

        MessageService.show_operation_success(self, f"{label}更新")
        self._refreshCurrentSection()

    def _refreshCurrentSection(self: "NovelDetail"):
        """刷新当前显示的section"""
        # 重新加载项目数据
        response = self.api_client.get_novel(self.project_id)
        self.project_data = response

        # 如果当前section已缓存且支持updateData，使用updateData更新
        if self.active_section in self.section_widgets:
            widget = self.section_widgets[self.active_section]

            # 获取内部的section组件（在QScrollArea内）
            scroll_widget = widget.widget()
            if scroll_widget:
                layout = scroll_widget.layout()
                if layout and layout.count() > 0:
                    section = layout.itemAt(0).widget()

                    if self.active_section == 'overview' and hasattr(section, 'updateData'):
                        blueprint = self.project_data.get('blueprint', {})
                        section.updateData(blueprint)
                        return
                    elif self.active_section == 'world_setting' and hasattr(section, 'updateData'):
                        world_setting = self.project_data.get('blueprint', {}).get('world_setting', {})
                        section.updateData(world_setting)
                        return
                    elif self.active_section == 'characters' and hasattr(section, 'updateData'):
                        characters = self.project_data.get('blueprint', {}).get('characters', [])
                        section.updateData(characters)
                        return
                    elif self.active_section == 'relationships' and hasattr(section, 'updateData'):
                        relationships = self.project_data.get('blueprint', {}).get('relationships', [])
                        section.updateData(relationships)
                        return
                    elif self.active_section == 'chapter_outline' and hasattr(section, 'updateData'):
                        blueprint = self.project_data.get('blueprint', {})
                        outline = blueprint.get('chapter_outline', [])
                        section.updateData(outline, blueprint)
                        return
                    elif self.active_section == 'chapters' and hasattr(section, 'updateData'):
                        chapters = self.project_data.get('chapters', [])
                        section.updateData(chapters)
                        return

            # 如果不支持updateData，重建section
            if hasattr(widget, 'stopAllTasks'):
                widget.stopAllTasks()

            self.content_stack.removeWidget(widget)
            widget.deleteLater()
            del self.section_widgets[self.active_section]

        self.loadSection(self.active_section)

    def editProjectTitle(self: "NovelDetail"):
        """编辑项目标题"""
        from components.dialogs import InputDialog
        current_title = self.project_data.get('title', '') if self.project_data else ''
        new_title, ok = InputDialog.getTextStatic(
            parent=self,
            title="编辑项目标题",
            label="请输入新标题：",
            text=current_title
        )

        if ok and new_title:
            @handle_errors("更新标题")
            def _update_title():
                self.api_client.update_project(self.project_id, {'title': new_title})
                self.project_title.setText(new_title)
                MessageService.show_operation_success(self, "标题更新")

            _update_title()

    def exportNovel(self: "NovelDetail", format_type):
        """导出小说"""
        @handle_errors("导出小说")
        def _export():
            response = self.api_client.export_novel(self.project_id, format_type)

            file_filter = "文本文件 (*.txt)" if format_type == 'txt' else "Markdown文件 (*.md)"
            default_name = f"{self.project_data.get('title', '小说')}.{format_type if format_type == 'md' else 'txt'}"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存导出文件",
                default_name,
                file_filter
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(response)
                MessageService.show_operation_success(self, "导出", f"已导出到：{file_path}")

        _export()


__all__ = [
    "SaveManagerMixin",
]
