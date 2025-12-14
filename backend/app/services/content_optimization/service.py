"""
正文优化服务

主服务入口，协调工作流执行并提供对外接口。
"""

import logging
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import OptimizeContentRequest, OptimizationMode
from .workflow import ContentOptimizationWorkflow
from .session_manager import get_session_manager, OptimizationSession

logger = logging.getLogger(__name__)


class ContentOptimizationService:
    """正文优化服务"""

    def __init__(
        self,
        session: AsyncSession,
        llm_service,
        vector_store=None,
        prompt_service=None,
        embedding_service=None,
    ):
        """
        初始化服务

        Args:
            session: 数据库会话
            llm_service: LLM服务
            vector_store: 向量存储服务（可选）
            prompt_service: 提示词服务（可选）
            embedding_service: 嵌入服务（可选，用于时序感知检索）
        """
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.prompt_service = prompt_service
        self.embedding_service = embedding_service
        self.session_manager = get_session_manager()

    async def optimize_chapter_stream(
        self,
        project_id: str,
        chapter_number: int,
        request: OptimizeContentRequest,
        user_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        流式优化章节内容

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            request: 优化请求
            user_id: 用户ID

        Yields:
            SSE事件字符串
        """
        # 创建优化会话（用于review模式的暂停/继续控制）
        opt_session = self.session_manager.create_session(
            project_id=project_id,
            chapter_number=chapter_number,
        )

        try:
            workflow = ContentOptimizationWorkflow(
                session=self.session,
                llm_service=self.llm_service,
                vector_store=self.vector_store,
                prompt_service=self.prompt_service,
                embedding_service=self.embedding_service,
                optimization_session=opt_session,
            )

            async for event in workflow.execute_with_stream(
                project_id=project_id,
                chapter_number=chapter_number,
                request=request,
                user_id=user_id,
            ):
                yield event

        finally:
            # 清理会话
            self.session_manager.remove_session(opt_session.session_id)

    def continue_session(self, session_id: str) -> bool:
        """
        继续暂停的会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功继续
        """
        return self.session_manager.resume_session(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """
        取消会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功取消
        """
        return self.session_manager.cancel_session(session_id)

    def get_session(self, session_id: str) -> Optional[OptimizationSession]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话对象或None
        """
        return self.session_manager.get_session(session_id)

    async def get_paragraph_preview(
        self,
        content: str,
    ) -> dict:
        """
        获取段落预览

        用于前端预览段落分割结果

        Args:
            content: 正文内容

        Returns:
            段落预览信息
        """
        from .paragraph_analyzer import ParagraphAnalyzer

        analyzer = ParagraphAnalyzer()
        paragraphs = analyzer.split_paragraphs(content)

        return {
            "total_paragraphs": len(paragraphs),
            "paragraphs": [
                {
                    "index": i,
                    "preview": p[:100] + "..." if len(p) > 100 else p,
                    "length": len(p),
                }
                for i, p in enumerate(paragraphs)
            ],
        }
