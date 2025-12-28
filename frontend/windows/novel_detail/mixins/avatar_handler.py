"""
头像处理Mixin

负责头像的加载、显示和生成。
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QByteArray

from utils.async_worker import AsyncAPIWorker
from utils.message_service import MessageService, confirm
from utils.constants import WorkerTimeouts

if TYPE_CHECKING:
    from ..main import NovelDetail

logger = logging.getLogger(__name__)


class AvatarHandlerMixin:
    """
    头像处理Mixin

    负责：
    - 加载并显示头像SVG
    - 显示头像占位符
    - 处理头像点击事件
    - 异步生成头像
    """

    def _loadAvatar(self: "NovelDetail", avatar_svg: str = None):
        """加载并显示头像SVG

        Args:
            avatar_svg: SVG字符串，为None时显示占位符
        """
        if avatar_svg:
            try:
                # 使用QSvgRenderer验证SVG有效性
                from PyQt6.QtSvg import QSvgRenderer
                svg_bytes = QByteArray(avatar_svg.encode('utf-8'))
                renderer = QSvgRenderer(svg_bytes)

                if renderer.isValid():
                    # SVG有效，加载到widget
                    self.avatar_svg_widget.load(svg_bytes)
                    self.avatar_svg_widget.setVisible(True)
                    self.icon_placeholder.setVisible(False)
                    self.icon_container.setToolTip("点击重新生成头像")
                    # 强制重绘确保显示更新
                    self.avatar_svg_widget.update()
                    self.avatar_svg_widget.repaint()
                    logger.debug(f"头像SVG加载成功, size={len(avatar_svg)}")
                else:
                    # SVG无效，显示占位符并记录警告
                    logger.warning(f"头像SVG无效，无法渲染: size={len(avatar_svg)}, preview={avatar_svg[:100]}...")
                    self._showAvatarPlaceholder()
            except Exception as e:
                logger.error(f"加载头像SVG失败: {e}")
                self._showAvatarPlaceholder()
        else:
            self._showAvatarPlaceholder()

    def _showAvatarPlaceholder(self: "NovelDetail"):
        """显示头像占位符"""
        self.avatar_svg_widget.setVisible(False)
        self.icon_placeholder.setVisible(True)
        # 使用项目标题首字作为占位符
        if self.project_data:
            title = self.project_data.get('title', 'B')
            first_char = title[0] if title else 'B'
            self.icon_placeholder.setText(first_char)
        self.icon_container.setToolTip("点击生成小说头像")

    def _onIconClicked(self: "NovelDetail", event):
        """点击头像图标时触发生成"""
        # 检查是否有蓝图
        if not self.project_data or not self.project_data.get('blueprint'):
            MessageService.show_warning(self, "请先生成蓝图后再生成头像", "提示")
            return

        # 确认生成
        blueprint = self.project_data.get('blueprint', {})
        has_avatar = blueprint.get('avatar_svg') is not None

        if has_avatar:
            if not confirm(self, "确定要重新生成头像吗？\n当前头像将被替换。", "重新生成头像"):
                return

        logger.info(f"开始生成头像: project_id={self.project_id}")
        self._generateAvatar()

    def _generateAvatar(self: "NovelDetail"):
        """执行头像生成（异步）"""
        from components.dialogs import LoadingDialog

        # 创建加载对话框
        self._avatar_loading_dialog = LoadingDialog(
            parent=self,
            title="请稍候",
            message="正在生成小说头像...",
            cancelable=True
        )
        self._avatar_loading_dialog.show()

        # 创建异步worker
        self._avatar_worker = AsyncAPIWorker(
            self.api_client.generate_avatar,
            self.project_id
        )

        self._avatar_worker.success.connect(self._onAvatarGenerated)
        self._avatar_worker.error.connect(self._onAvatarGenerateError)
        self._avatar_loading_dialog.rejected.connect(self._onAvatarGenerateCancelled)

        # 保持worker引用
        if not hasattr(self, '_workers'):
            self._workers = []
        self._workers.append(self._avatar_worker)

        self._avatar_worker.start()

    def _onAvatarGenerated(self: "NovelDetail", result):
        """头像生成成功回调"""
        # 关闭加载对话框
        if hasattr(self, '_avatar_loading_dialog') and self._avatar_loading_dialog:
            self._avatar_loading_dialog.close()

        avatar_svg = result.get('avatar_svg')
        animal_cn = result.get('animal_cn', '小动物')

        logger.info(f"头像生成成功: animal={result.get('animal')}, animal_cn={animal_cn}")

        # 更新显示
        self._loadAvatar(avatar_svg)

        # 更新本地缓存的项目数据
        if self.project_data and self.project_data.get('blueprint'):
            self.project_data['blueprint']['avatar_svg'] = avatar_svg
            self.project_data['blueprint']['avatar_animal'] = result.get('animal')

        MessageService.show_success(self, f"已生成{animal_cn}头像")

    def _onAvatarGenerateError(self: "NovelDetail", error_msg):
        """头像生成失败回调"""
        # 关闭加载对话框
        if hasattr(self, '_avatar_loading_dialog') and self._avatar_loading_dialog:
            self._avatar_loading_dialog.close()

        logger.error(f"头像生成失败: {error_msg}")
        MessageService.show_api_error(self, error_msg, "生成头像")

    def _onAvatarGenerateCancelled(self: "NovelDetail"):
        """头像生成取消回调"""
        if hasattr(self, '_avatar_worker') and self._avatar_worker:
            try:
                if self._avatar_worker.isRunning():
                    self._avatar_worker.cancel()
                    self._avatar_worker.quit()
                    self._avatar_worker.wait(WorkerTimeouts.DEFAULT_MS)
            except RuntimeError:
                pass

        logger.info("头像生成已取消")


__all__ = [
    "AvatarHandlerMixin",
]
