"""
导入分析Mixin

负责导入小说的分析功能。
"""

import logging
import traceback
from typing import TYPE_CHECKING

from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService, confirm

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class ImportAnalyzerMixin:
    """
    导入分析Mixin

    负责：
    - 处理导入小说的分析请求
    - 显示分析进度对话框
    - 支持断点续传分析
    """

    def onStartAnalysis(self: "NovelDetail"):
        """开始分析导入的小说"""
        # 检查是否是继续分析（之前中断过）
        analysis_status = self.project_data.get('import_analysis_status', '')
        is_resume = analysis_status in ('failed', 'cancelled')

        # 根据状态显示不同的确认对话框
        if is_resume:
            confirm_message = (
                "检测到之前的分析进度，将从断点继续：\n\n"
                "- 已生成的分析数据会被保留\n"
                "- 已生成的章节摘要会被复用\n"
                "- 只处理未完成的内容\n\n"
                "确定要继续分析吗？"
            )
            confirm_title = "确认继续分析"
        else:
            confirm_message = (
                "将开始分析导入的小说内容，包括：\n\n"
                "1. 逐章生成分析数据\n"
                "2. 逐章生成章节摘要\n"
                "3. 更新章节大纲\n"
                "4. 生成分部大纲（长篇）\n"
                "5. 反推蓝图信息\n\n"
                "此过程可能需要较长时间，确定要开始吗？"
            )
            confirm_title = "确认开始分析"

        if not confirm(self, confirm_message, confirm_title):
            return

        logger.info(f"{'继续' if is_resume else '开始'}分析导入项目: project_id={self.project_id}")

        # 禁用按钮
        if hasattr(self, 'analyze_btn') and self.analyze_btn:
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.setText("启动中...")

        # 异步启动分析
        self._doStartAnalysis()

    def _doStartAnalysis(self: "NovelDetail"):
        """执行启动分析"""
        logger.info("=== _doStartAnalysis 开始 ===")

        def start_analysis():
            logger.info("start_analysis 函数被调用")
            result = self.api_client.start_import_analysis(self.project_id)
            logger.info(f"API 返回: {result}")
            return result

        def on_success(result):
            try:
                logger.info(f"=== on_success 回调开始 ===")
                logger.info(f"分析任务启动成功: {result}")
                # 显示进度对话框
                logger.info("即将调用 _showAnalysisProgressDialog...")
                self._showAnalysisProgressDialog()
                logger.info("_showAnalysisProgressDialog 返回")
            except Exception as e:
                logger.error(f"on_success 回调异常: {e}")
                logger.error(traceback.format_exc())

        def on_error(error_msg):
            logger.error(f"启动分析失败: {error_msg}")
            MessageService.show_error(self, f"启动分析失败：{error_msg}", "错误")
            # 恢复按钮状态
            if hasattr(self, 'analyze_btn') and self.analyze_btn:
                self.analyze_btn.setEnabled(True)
                # 根据状态恢复按钮文案
                analysis_status = self.project_data.get('import_analysis_status', '')
                if analysis_status in ('failed', 'cancelled'):
                    self.analyze_btn.setText("继续分析")
                else:
                    self.analyze_btn.setText("开始分析")

        worker = AsyncAPIWorker(start_analysis)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(worker)
        logger.info("启动 AsyncAPIWorker...")
        worker.start()

    def _showAnalysisProgressDialog(self: "NovelDetail"):
        """显示分析进度对话框"""
        logger.info("=== 开始显示分析进度对话框 ===")

        try:
            logger.info("导入 ImportProgressDialog...")
            from components.dialogs import ImportProgressDialog
            logger.info("导入成功")

            logger.info(f"创建对话框实例: project_id={self.project_id}")
            dialog = ImportProgressDialog(
                parent=self,
                project_id=self.project_id,
                api_client=self.api_client
            )
            logger.info("对话框实例创建成功")

            # 对话框关闭后刷新页面
            logger.info("调用 dialog.exec()...")
            result = dialog.exec()
            logger.info(f"dialog.exec() 返回: {result}")

            if dialog.was_completed():
                MessageService.show_success(self, "分析完成！")
                # 刷新项目数据
                self.refreshProject()
            elif dialog.was_cancelled():
                MessageService.show_info(self, "分析已取消")
                # 刷新项目数据以更新状态
                self.loadProjectBasicInfo()

        except Exception as e:
            logger.error(f"显示进度对话框时发生异常: {e}")
            logger.error(traceback.format_exc())
            MessageService.show_error(self, f"显示进度对话框失败：{e}", "错误")


__all__ = [
    "ImportAnalyzerMixin",
]
