"""
优化会话管理器

管理正文优化的会话状态，支持暂停/继续控制。
使用asyncio.Event实现线程安全的等待/通知机制。
"""

import asyncio
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class OptimizationSession:
    """优化会话"""
    session_id: str
    project_id: str
    chapter_number: int
    user_id: int
    created_at: datetime = field(default_factory=datetime.now)

    # 暂停控制
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
    is_paused: bool = False

    # 会话状态
    is_cancelled: bool = False
    current_paragraph: int = 0
    total_paragraphs: int = 0

    # 内容更新支持：当用户处理完建议后，前端会发送最新编辑器内容
    # 后端在 resume 时使用此内容更新 AgentState
    pending_content: Optional[str] = None  # 待更新的内容
    has_pending_content: bool = False  # 是否有待更新的内容

    def __post_init__(self):
        # 初始状态为"未暂停"，即可以继续执行
        self.pause_event.set()

    def set_pending_content(self, content: str):
        """设置待更新的内容（前端发送的最新编辑器内容）"""
        self.pending_content = content
        self.has_pending_content = True

    def consume_pending_content(self) -> Optional[str]:
        """获取并清除待更新的内容"""
        if self.has_pending_content:
            content = self.pending_content
            self.pending_content = None
            self.has_pending_content = False
            return content
        return None


class OptimizationSessionManager:
    """
    优化会话管理器

    提供会话的创建、暂停、继续、取消功能。
    使用asyncio.Event实现非阻塞的等待机制。
    """

    # 会话超时时间（分钟）
    SESSION_TIMEOUT_MINUTES = 30

    def __init__(self):
        self._sessions: Dict[str, OptimizationSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_session(
        self,
        project_id: str,
        chapter_number: int,
        user_id: int,
    ) -> OptimizationSession:
        """
        创建新的优化会话

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            新创建的会话
        """
        session_id = str(uuid.uuid4())
        session = OptimizationSession(
            session_id=session_id,
            project_id=project_id,
            chapter_number=chapter_number,
            user_id=int(user_id),
        )
        self._sessions[session_id] = session

        logger.info(
            "创建优化会话: session_id=%s, project=%s, chapter=%d",
            session_id, project_id, chapter_number
        )

        return session

    def get_session(self, session_id: str) -> Optional[OptimizationSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def pause_session(self, session_id: str) -> bool:
        """
        暂停会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功暂停
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("尝试暂停不存在的会话: %s", session_id)
            return False

        if session.is_paused:
            logger.debug("会话已经处于暂停状态: %s", session_id)
            return True

        session.is_paused = True
        session.pause_event.clear()  # 清除事件，使await会阻塞

        logger.info("暂停会话: %s", session_id)
        return True

    def resume_session(self, session_id: str, content: Optional[str] = None) -> bool:
        """
        继续会话

        Args:
            session_id: 会话ID
            content: 前端发送的最新编辑器内容（可选）

        Returns:
            是否成功继续
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("尝试继续不存在的会话: %s", session_id)
            return False

        # 如果有新内容，保存到会话中供 Agent 获取
        if content is not None:
            session.set_pending_content(content)
            logger.info("会话 %s 收到新内容，长度: %d", session_id, len(content))

        if not session.is_paused:
            logger.debug("会话未处于暂停状态: %s", session_id)
            return True

        session.is_paused = False
        session.pause_event.set()  # 设置事件，解除await阻塞

        logger.info("继续会话: %s", session_id)
        return True

    def cancel_session(self, session_id: str) -> bool:
        """
        取消会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功取消
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning("尝试取消不存在的会话: %s", session_id)
            return False

        session.is_cancelled = True
        # 如果会话处于暂停状态，需要解除阻塞让它可以检测到取消
        if session.is_paused:
            session.pause_event.set()

        logger.info("取消会话: %s", session_id)
        return True

    def remove_session(self, session_id: str):
        """
        移除会话

        Args:
            session_id: 会话ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info("移除会话: %s", session_id)

    def update_progress(
        self,
        session_id: str,
        current_paragraph: int,
        total_paragraphs: int,
    ) -> bool:
        """
        更新会话的段落进度

        Args:
            session_id: 会话ID
            current_paragraph: 当前段落索引
            total_paragraphs: 总段落数

        Returns:
            是否成功更新
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.current_paragraph = current_paragraph
        session.total_paragraphs = total_paragraphs
        return True

    async def wait_if_paused(
        self,
        session_id: str,
        timeout: float = 300.0,
    ) -> bool:
        """
        如果会话处于暂停状态，等待继续信号

        Args:
            session_id: 会话ID
            timeout: 超时时间（秒）

        Returns:
            True: 可以继续执行
            False: 会话被取消或超时
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        if session.is_cancelled:
            return False

        if not session.is_paused:
            return True

        try:
            # 等待继续信号，带超时
            await asyncio.wait_for(
                session.pause_event.wait(),
                timeout=timeout
            )

            # 检查是否被取消
            if session.is_cancelled:
                return False

            return True

        except asyncio.TimeoutError:
            logger.warning("会话等待超时: %s", session_id)
            return False

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        timeout = timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)

        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.created_at > timeout
        ]

        for session_id in expired:
            self.remove_session(session_id)

        if expired:
            logger.info("清理了 %d 个过期会话", len(expired))

    def get_active_session_count(self) -> int:
        """获取活跃会话数量"""
        return len(self._sessions)


# 全局会话管理器实例
_session_manager: Optional[OptimizationSessionManager] = None
_session_manager_lock = threading.Lock()


def get_session_manager() -> OptimizationSessionManager:
    """
    获取全局会话管理器实例（线程安全）

    使用双重检查锁定模式确保线程安全的单例初始化。
    """
    global _session_manager
    if _session_manager is None:
        with _session_manager_lock:
            # 双重检查：在获取锁之后再次检查
            if _session_manager is None:
                _session_manager = OptimizationSessionManager()
    return _session_manager
