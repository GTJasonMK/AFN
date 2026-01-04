"""
写作台主工作区 - 章节生成处理 Mixin

包含章节生成过程中的UI更新方法。
"""

import logging

from utils.message_service import MessageService

logger = logging.getLogger(__name__)


class GenerationHandlersMixin:
    """章节生成处理相关方法的 Mixin"""

    def prepareForGeneration(self, chapter_number: int):
        """准备生成章节 - 清空内容区域并显示加载状态"""
        if self.content_text:
            self.content_text.clear()
            self.content_text.setPlaceholderText(f"正在生成第{chapter_number}章...")

        # 禁用生成按钮
        if self.generate_btn:
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("生成中...")

        logger.info(f"准备生成第{chapter_number}章")

    def appendGeneratedContent(self, token: str):
        """追加生成的内容（流式更新）"""
        if self.content_text:
            # 移动光标到末尾并插入文本
            cursor = self.content_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(token)
            self.content_text.setTextCursor(cursor)
            # 确保滚动到底部
            self.content_text.ensureCursorVisible()

    def setGenerationStatus(self, status: str):
        """设置生成状态提示"""
        if self.generate_btn:
            self.generate_btn.setText(status[:15] + "..." if len(status) > 15 else status)

    def showEvaluationSection(self):
        """显示评估区域（生成完成后）"""
        # 切换到评审Tab
        if self.tab_widget:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "评审":
                    self.tab_widget.setCurrentIndex(i)
                    break

    def enableRegenerate(self):
        """启用重新生成按钮"""
        if self.generate_btn:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("重新生成")

    def onGenerationComplete(self, data: dict):
        """处理生成完成"""
        # 恢复生成按钮状态
        if self.generate_btn:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("重新生成")

        # 清除placeholder
        if self.content_text:
            self.content_text.setPlaceholderText("")

        logger.info("章节生成完成")

    def onGenerationError(self, error_title: str, error_message: str):
        """处理生成错误

        Args:
            error_title: 错误标题
            error_message: 错误详细信息
        """
        # 恢复生成按钮状态
        if self.generate_btn:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("生成章节")

        # 在内容区域显示错误
        if self.content_text:
            self.content_text.setPlaceholderText("")
            current_text = self.content_text.toPlainText()
            if not current_text.strip():
                self.content_text.setPlainText(f"{error_title}\n\n{error_message}")

        MessageService.show_error(self, error_message, error_title)
        logger.error(f"章节生成错误: {error_title} - {error_message}")

    def onGenerationCancelled(self):
        """处理生成取消"""
        # 恢复生成按钮状态
        if self.generate_btn:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("生成章节")

        if self.content_text:
            self.content_text.setPlaceholderText("")
            current_text = self.content_text.toPlainText()
            if not current_text.strip():
                self.content_text.setPlainText("生成已取消")

        logger.info("章节生成已取消")

    def refreshCurrentChapter(self):
        """刷新当前章节显示

        强制重新加载当前章节，即使章节号相同。
        这在版本切换后需要刷新内容时特别重要。
        """
        if self.current_chapter:
            # 清除缓存标记以强制重新加载
            # loadChapter会检查_last_loaded_chapter，如果相同会直接返回
            # 版本切换后章节号不变但内容已变，所以需要强制刷新
            if hasattr(self, '_last_loaded_chapter'):
                self._last_loaded_chapter = None
            self.loadChapter(self.current_chapter)

    def showEvaluationResult(self, result: dict):
        """显示评估结果

        Args:
            result: 评估结果数据
        """
        # 切换到评审Tab并更新内容
        if self.tab_widget:
            for i in range(self.tab_widget.count()):
                if self.tab_widget.tabText(i) == "评审":
                    self.tab_widget.setCurrentIndex(i)
                    break

        # 如果有评审面板构建器，更新评审内容
        if hasattr(self, '_review_builder') and self._review_builder:
            # 重新加载当前章节以显示新的评估结果
            if self.current_chapter:
                self.loadChapter(self.current_chapter)

        logger.info("评估结果已显示")
