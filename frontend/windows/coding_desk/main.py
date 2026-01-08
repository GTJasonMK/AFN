"""
Prompt生成工作台主类

提供编程项目的Prompt生成和内容编辑功能。
采用简化的工作台结构：
- Header: 项目信息和导航
- Sidebar: 功能列表和选择
- Workspace: 内容编辑区
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer

from pages.base_page import BasePage
from api.manager import APIClientManager
from utils.async_worker import AsyncAPIWorker
from utils.worker_manager import WorkerManager
from utils.message_service import MessageService, confirm
from utils.sse_worker import SSEWorker
from utils.dpi_utils import dp
from components.dialogs import TextInputDialog
from themes.theme_manager import theme_manager

from .header import CDHeader
from .sidebar import CDSidebar
from .workspace import CDWorkspace

logger = logging.getLogger(__name__)


class CodingDesk(BasePage):
    """Prompt生成工作台

    专为编程项目设计：
    - 功能Prompt生成
    - 多版本管理
    - 内容编辑
    """

    # 生成初始阶段状态提示消息列表
    _GENERATION_INIT_MESSAGES = [
        "正在连接AI服务...",
        "正在分析项目蓝图...",
        "正在准备功能上下文...",
        "正在构建提示词...",
        "AI正在生成Prompt...",
    ]

    def __init__(self, project_id, parent=None):
        super().__init__(parent)
        self.project_id = project_id

        self.api_client = APIClientManager.get_client()
        self.project = None
        self.selected_feature_number = None  # 1-based feature_number
        self.generating_feature = None  # 1-based feature_number
        self._generating_review = False  # 是否正在生成审查Prompt

        # 异步任务管理
        self.worker_manager = WorkerManager(self)
        self._sse_worker = None

        # 加载操作ID（用于防止加载动画竞态条件）
        self._load_project_op_id = None
        self._load_feature_op_id = None
        self._generate_op_id = None

        # 生成状态定时器
        self._gen_status_timer = None
        self._gen_status_step = 0
        self._gen_first_content_received = False

        self.setupUI()
        self.loadProject()

    def setupUI(self):
        """初始化UI"""
        if not self.layout():
            self._create_ui_structure()
        self._apply_theme()

    def _create_ui_structure(self):
        """创建UI结构"""
        from PyQt6.QtWidgets import QApplication

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        self.header = CDHeader()
        main_layout.addWidget(self.header)

        # 主内容区
        self.content_widget = QWidget()
        content_layout = QHBoxLayout(self.content_widget)
        content_layout.setContentsMargins(dp(12), dp(12), dp(12), dp(12))
        content_layout.setSpacing(dp(12))

        # Sidebar（固定宽度）
        self.sidebar = CDSidebar()
        content_layout.addWidget(self.sidebar)

        # Workspace（占据剩余空间）
        self.workspace = CDWorkspace()
        self.workspace.setProjectId(self.project_id)
        self.workspace.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self.workspace, stretch=1)

        main_layout.addWidget(self.content_widget, stretch=1)

        # 处理事件循环
        QApplication.processEvents()

        # 连接信号
        self._connect_signals()

    def _connect_signals(self):
        """统一管理所有信号连接"""
        # Header 信号
        self.header.goBackClicked.connect(self.goBackToHome)
        self.header.viewDetailClicked.connect(self.openProjectDetail)
        self.header.exportClicked.connect(self.exportContent)

        # Sidebar 信号
        self.sidebar.featureSelected.connect(self.onFeatureSelected)
        self.sidebar.generateFeature.connect(self.onGenerateFeature)

        # Workspace 信号（实现Prompt）
        self.workspace.generateRequested.connect(self.onGenerateFeature)
        self.workspace.saveContentRequested.connect(self.onSaveContent)

        # Workspace 信号（审查Prompt）
        self.workspace.generateReviewRequested.connect(self.onGenerateReview)
        self.workspace.saveReviewRequested.connect(self.onSaveReview)

    def _apply_theme(self):
        """应用主题样式"""
        from themes.modern_effects import ModernEffects

        bg_color = theme_manager.book_bg_primary()

        # 获取透明效果配置
        transparency_config = theme_manager.get_transparency_config()
        transparency_enabled = transparency_config.get("enabled", False)
        content_opacity = theme_manager.get_component_opacity("content")

        if transparency_enabled:
            bg_rgba = ModernEffects.hex_to_rgba(bg_color, content_opacity)
            self.setStyleSheet(f"background-color: {bg_rgba};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAutoFillBackground(False)

            transparent_containers = ['header', 'content_widget', 'sidebar', 'workspace']
            for container_name in transparent_containers:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(False)

            if hasattr(self, 'content_widget') and self.content_widget:
                self.content_widget.setStyleSheet("background-color: transparent;")
        else:
            self.setStyleSheet(f"background-color: {bg_color};")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setAutoFillBackground(True)

            containers_to_restore = ['header', 'content_widget', 'sidebar', 'workspace']
            for container_name in containers_to_restore:
                container = getattr(self, container_name, None)
                if container:
                    container.setAutoFillBackground(True)

            if hasattr(self, 'content_widget') and self.content_widget:
                self.content_widget.setStyleSheet("background-color: transparent;")

    # ==================== 项目加载 ====================

    def loadProject(self):
        """加载项目数据"""
        self._load_project_op_id = self.show_loading("正在加载项目数据...", "load_project")

        worker = AsyncAPIWorker(self.api_client.get_novel, self.project_id)
        worker.success.connect(self._onProjectLoaded)
        worker.error.connect(self._onProjectLoadError)
        self.worker_manager.start(worker, 'load_project')

    def _onProjectLoaded(self, project_data):
        """项目数据加载成功"""
        self.hide_loading(self._load_project_op_id)
        self._load_project_op_id = None
        self.project = project_data
        logger.info("项目数据加载成功")

        self.header.setProject(self.project)
        self.sidebar.setProject(self.project)

        # 如果有待选中的功能编号，选中它
        if hasattr(self, '_pending_feature_number') and self._pending_feature_number is not None:
            feature_number = self._pending_feature_number
            self._pending_feature_number = None
            # 使用QTimer延迟执行，确保UI已更新
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.sidebar.selectFeature(feature_number))

    def _onProjectLoadError(self, error_msg):
        """项目数据加载失败"""
        self.hide_loading(self._load_project_op_id)
        self._load_project_op_id = None
        logger.error(f"项目加载失败: {error_msg}")
        MessageService.show_error(self, f"加载项目失败：\n\n{error_msg}", "错误")

    # ==================== 功能事件 ====================

    def onFeatureSelected(self, feature_number: int):
        """功能被选中（feature_number是1-based）"""
        self.selected_feature_number = feature_number
        feature_index = feature_number - 1  # 转换为0-based索引
        self._loadFeatureContent(feature_index)

    def _loadFeatureContent(self, feature_index: int):
        """加载功能内容（feature_index是0-based）"""
        self._load_feature_op_id = self.show_loading("正在加载功能内容...", "load_feature")

        def do_load():
            return self.api_client.get_coding_feature_content(
                self.project_id, feature_index
            )

        worker = AsyncAPIWorker(do_load)
        worker.success.connect(
            lambda data: self._onFeatureContentLoaded(feature_index, data)
        )
        worker.error.connect(self._onFeatureContentError)
        self.worker_manager.start(worker, f'load_feature_{feature_index}')

    def _onFeatureContentLoaded(self, feature_index: int, data: dict):
        """功能内容加载成功"""
        self.hide_loading(self._load_feature_op_id)
        self._load_feature_op_id = None
        self.workspace.setFeatureContent(feature_index, data)

    def _onFeatureContentError(self, error_msg: str):
        """功能内容加载失败"""
        self.hide_loading(self._load_feature_op_id)
        self._load_feature_op_id = None
        logger.error(f"加载功能内容失败: {error_msg}")
        # 可能是还没有生成内容，这不是错误
        if self.selected_feature_number is not None:
            feature_index = self.selected_feature_number - 1
            self.workspace.loadFeature(feature_index)

    def onGenerateFeature(self, feature_number: int):
        """生成功能Prompt（feature_number是1-based）"""
        if self.generating_feature is not None:
            MessageService.show_warning(self, "正在生成中，请稍候...")
            return

        feature_index = feature_number - 1  # 转换为0-based索引

        # 获取功能标题
        feature_title = self._getFeatureTitle(feature_index)

        # 检查是否已有生成内容
        chapters = self.project.get('chapters', []) if self.project else []
        existing_chapter = next(
            (ch for ch in chapters if ch.get('chapter_number') == feature_number),
            None
        )
        has_content = existing_chapter and existing_chapter.get('content')

        # 根据是否已有内容显示不同的确认信息
        if has_content:
            if not confirm(
                self,
                f"功能 [{feature_title}] 已有生成内容。\n\n"
                "重新生成将覆盖现有的Prompt内容。\n\n"
                "确定要继续吗？",
                "确认覆盖"
            ):
                return
        else:
            if not confirm(
                self,
                f"确定要生成功能 [{feature_title}] 的Prompt吗？\n\n生成过程可能需要1-2分钟。",
                "确认生成"
            ):
                return

        # 询问用户输入写作指导（可选）
        writing_notes, ok = TextInputDialog.getTextStatic(
            parent=self,
            title="写作指导",
            label=f"请输入生成 [{feature_title}] 的额外要求（可选）：\n\n"
                  "留空则按蓝图设定生成。",
            placeholder="示例：重点描述API接口设计、添加详细的错误处理逻辑..."
        )

        if not ok:
            return

        # 清理旧的SSE
        self._cleanup_sse_worker()

        # 记录正在生成的功能（使用feature_number）
        self.generating_feature = feature_number

        # 更新UI状态
        self.workspace.showGenerating(feature_index, feature_title)

        # 显示初始加载状态并启动状态更新定时器
        self._generate_op_id = self.show_loading("正在准备生成...", "generate")
        self._start_gen_status_timer()

        # 创建SSE Worker（API使用feature_index）
        url = f"{self.api_client.base_url}/api/coding/{self.project_id}/features/{feature_index}/generate-stream"
        payload = {
            "feature_index": feature_index,
            "writing_notes": writing_notes.strip() if writing_notes else None,
        }

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.token_received.connect(self._on_gen_token)
        self._sse_worker.progress_received.connect(self._on_gen_progress)
        self._sse_worker.complete.connect(self._on_gen_complete)
        # 使用 QueuedConnection 确保错误处理在主线程执行，避免 Windows COM 线程冲突
        from PyQt6.QtCore import Qt
        self._sse_worker.error.connect(self._on_gen_error, Qt.ConnectionType.QueuedConnection)
        self._sse_worker.start()

        logger.info(f"开始生成功能 {feature_number} (index={feature_index}) 的Prompt")

    def _getFeatureTitle(self, feature_index: int) -> str:
        """获取功能标题

        从 coding_blueprint.features 中获取功能名称。
        注意：features 是功能列表，modules 是模块列表，不要混淆。
        """
        if not self.project:
            return f"功能 {feature_index + 1}"

        blueprint = self.project.get('coding_blueprint') or {}

        # 优先从 features 字段获取（三层架构的标准字段）
        # 回退兼容：chapter_outline（旧格式）
        # 注意：不要使用 modules，那是模块列表而非功能列表！
        features = blueprint.get('features', []) or blueprint.get('chapter_outline', [])

        if feature_index < len(features):
            feature = features[feature_index]
            # CodingFeature 使用 name 字段
            return feature.get('name') or feature.get('title') or f'功能 {feature_index + 1}'

        return f"功能 {feature_index + 1}"

    # ==================== 生成状态定时器 ====================

    def _start_gen_status_timer(self):
        """启动生成状态更新定时器"""
        self._gen_status_step = 0
        self._gen_first_content_received = False

        if self._gen_status_timer is None:
            self._gen_status_timer = QTimer(self)
            self._gen_status_timer.timeout.connect(self._update_gen_status)

        self._gen_status_timer.start(2000)  # 每2秒更新一次状态

    def _stop_gen_status_timer(self):
        """停止生成状态更新定时器"""
        if self._gen_status_timer:
            self._gen_status_timer.stop()
        self._gen_status_step = 0

    def _update_gen_status(self):
        """更新生成状态提示"""
        if self._gen_first_content_received:
            self._stop_gen_status_timer()
            return

        messages = self._GENERATION_INIT_MESSAGES
        if self._gen_status_step < len(messages):
            message = messages[self._gen_status_step]
            # 更新加载提示文字（保持使用生成操作ID）
            self.show_loading(message, "generate")
            self._gen_status_step += 1
        else:
            # 循环显示最后两条消息
            loop_messages = messages[-2:]
            idx = (self._gen_status_step - len(messages)) % len(loop_messages)
            message = loop_messages[idx]
            self.show_loading(message, "generate")
            self._gen_status_step += 1

    # ==================== SSE事件处理 ====================

    def _on_gen_token(self, token: str):
        """处理生成的token（流式文本）"""
        if not self._gen_first_content_received:
            self._gen_first_content_received = True
            self._stop_gen_status_timer()
            self.hide_loading(self._generate_op_id)

        self.workspace.appendGeneratedContent(token)

    def _on_gen_progress(self, data: dict):
        """处理生成进度"""
        stage = data.get('stage', '')
        message = data.get('message', '')
        if message:
            self.show_loading(message, "generate")

    def _on_gen_complete(self, data: dict):
        """处理生成完成"""
        feature_number = self.generating_feature  # 1-based
        self.generating_feature = None

        self._stop_gen_status_timer()
        self.hide_loading(self._generate_op_id)
        self._generate_op_id = None
        self._cleanup_sse_worker()

        # 通知workspace完成
        content = data.get('content', '')
        version_count = data.get('version_count', 1)
        self.workspace.finishGenerating(content, version_count)

        # 刷新项目数据以更新侧边栏状态
        self.loadProject()

        logger.info(f"功能 {feature_number} Prompt生成完成")
        MessageService.show_success(self, "Prompt生成完成!")

    def _on_gen_error(self, error_msg: str):
        """处理生成错误"""
        feature_number = self.generating_feature  # 1-based
        self.generating_feature = None

        self._stop_gen_status_timer()
        self.hide_loading(self._generate_op_id)
        self._generate_op_id = None
        self._cleanup_sse_worker()

        self.workspace.onGenerationError(error_msg)
        MessageService.show_error(self, f"生成失败：{error_msg}")
        logger.error(f"功能 {feature_number} Prompt生成失败: {error_msg}")

    def _cleanup_sse_worker(self):
        """清理SSE Worker"""
        if self._sse_worker:
            try:
                self._sse_worker.stop()
                self._sse_worker.deleteLater()
            except RuntimeError:
                pass
            self._sse_worker = None

    # ==================== 保存和版本管理 ====================

    def onSaveContent(self, feature_index: int, content: str):
        """保存实现Prompt内容"""
        self.show_loading("正在保存...")

        def do_save():
            return self.api_client.save_coding_feature_content(
                self.project_id, feature_index, content
            )

        def on_success(result):
            self.hide_loading()
            word_count = result.get('word_count', len(content))
            self.workspace.onSaveSuccess(word_count)
            MessageService.show_success(self, "保存成功")

        def on_error(error_msg):
            self.hide_loading()
            MessageService.show_error(self, f"保存失败：{error_msg}")

        worker = AsyncAPIWorker(do_save)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, 'save_content')

    # ==================== 审查Prompt生成和保存 ====================

    def onGenerateReview(self, feature_index: int):
        """生成审查Prompt"""
        if self.generating_feature is not None:
            MessageService.show_warning(self, "正在生成中，请稍候...")
            return

        # 检查是否已有实现Prompt
        # 注意：项目数据中 chapters 的 content 字段为空（include_content=False）
        # 应该检查 word_count > 0 或 selected_version is not None
        chapters = self.project.get('chapters', []) if self.project else []
        existing_chapter = next(
            (ch for ch in chapters if ch.get('chapter_number') == feature_index + 1),
            None
        )

        # 检查 word_count 或 selected_version 来判断是否已生成内容
        has_content = (
            existing_chapter and
            (existing_chapter.get('word_count', 0) > 0 or existing_chapter.get('selected_version') is not None)
        )

        if not has_content:
            MessageService.show_warning(self, "请先生成功能Prompt，才能生成审查Prompt")
            return

        feature_title = self._getFeatureTitle(feature_index)

        # 确认生成
        if not confirm(
            self,
            f"确定要为 [{feature_title}] 生成审查Prompt吗？\n\n"
            "审查Prompt用于验证AI生成的代码是否正确实现了功能。",
            "确认生成"
        ):
            return

        # 清理旧的SSE
        self._cleanup_sse_worker()

        # 记录正在生成的功能（使用feature_number）
        self.generating_feature = feature_index + 1
        self._generating_review = True  # 标记正在生成审查Prompt

        # 更新UI状态
        self.workspace.showGeneratingReview(feature_index, feature_title)

        # 显示初始加载状态
        self._generate_op_id = self.show_loading("正在准备生成审查Prompt...", "generate")
        self._start_gen_status_timer()

        # 创建SSE Worker
        url = self.api_client.get_review_prompt_generate_stream_url(
            self.project_id, feature_index
        )
        payload = {}

        self._sse_worker = SSEWorker(url, payload)
        self._sse_worker.token_received.connect(self._on_gen_token)
        self._sse_worker.progress_received.connect(self._on_gen_progress)
        self._sse_worker.complete.connect(self._on_review_gen_complete)
        from PyQt6.QtCore import Qt
        self._sse_worker.error.connect(self._on_gen_error, Qt.ConnectionType.QueuedConnection)
        self._sse_worker.start()

        logger.info(f"开始生成功能 {feature_index + 1} 的审查Prompt")

    def _on_review_gen_complete(self, data: dict):
        """处理审查Prompt生成完成"""
        feature_number = self.generating_feature
        self.generating_feature = None
        self._generating_review = False

        self._stop_gen_status_timer()
        self.hide_loading(self._generate_op_id)
        self._generate_op_id = None
        self._cleanup_sse_worker()

        # 通知workspace完成
        review_prompt = data.get('review_prompt', '')
        self.workspace.finishGeneratingReview(review_prompt)

        # 刷新项目数据
        self.loadProject()

        logger.info(f"功能 {feature_number} 审查Prompt生成完成")
        MessageService.show_success(self, "审查Prompt生成完成!")

    def onSaveReview(self, feature_index: int, review_content: str):
        """保存审查Prompt内容"""
        self.show_loading("正在保存审查Prompt...")

        def do_save():
            return self.api_client.save_review_prompt(
                self.project_id, feature_index, review_content
            )

        def on_success(result):
            self.hide_loading()
            word_count = result.get('word_count', len(review_content))
            self.workspace.onSaveSuccess(word_count)
            MessageService.show_success(self, "审查Prompt保存成功")

        def on_error(error_msg):
            self.hide_loading()
            MessageService.show_error(self, f"保存失败：{error_msg}")

        worker = AsyncAPIWorker(do_save)
        worker.success.connect(on_success)
        worker.error.connect(on_error)
        self.worker_manager.start(worker, 'save_review')

    # ==================== 导航 ====================

    def openProjectDetail(self):
        """打开项目详情"""
        self.navigateTo("CODING_DETAIL", project_id=self.project_id)

    def goBackToHome(self):
        """返回首页"""
        self.navigateTo("HOME")

    def exportContent(self, format_type: str):
        """导出内容"""
        if not self.project:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出内容",
            f"{self.project.get('title', '未命名')}.{format_type}",
            f"{format_type.upper()} Files (*.{format_type})"
        )
        if not file_path:
            return

        # TODO: 实现导出功能
        MessageService.show_info(self, "导出功能开发中")

    # ==================== 生命周期 ====================

    def onHide(self):
        """页面隐藏时停止任务"""
        self._cleanup_workers(full_cleanup=False)

    def _cleanup_workers(self, full_cleanup: bool = True):
        """清理异步任务"""
        # 清理SSE Worker
        if self._sse_worker:
            try:
                self._sse_worker.stop()
            except Exception:
                pass
            self._sse_worker = None

        # 清理WorkerManager
        if hasattr(self, 'worker_manager') and self.worker_manager:
            if full_cleanup:
                self.worker_manager.cleanup_all()
            else:
                self.worker_manager.stop_all()

    def __del__(self):
        """析构时清理资源"""
        try:
            self._cleanup_workers(full_cleanup=True)
        except (RuntimeError, AttributeError):
            pass

    def closeEvent(self, event):
        """窗口关闭时清理"""
        self._cleanup_workers(full_cleanup=True)
        super().closeEvent(event)

    def refresh(self, **params):
        """刷新页面"""
        if 'project_id' in params:
            self.project_id = params['project_id']
            if hasattr(self, 'workspace'):
                self.workspace.setProjectId(self.project_id)

        # 保存要选中的功能编号（1-based feature_number）
        # 支持传入 feature_index（0-based）或 feature_number（1-based）
        if 'feature_number' in params:
            self._pending_feature_number = params['feature_number']
        elif 'feature_index' in params:
            # 兼容旧的feature_index参数，转换为feature_number
            self._pending_feature_number = params['feature_index'] + 1
        else:
            self._pending_feature_number = None

        self.loadProject()
