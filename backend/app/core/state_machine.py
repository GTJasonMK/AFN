"""
项目状态管理机制
统一管理项目状态转换，确保状态流转的一致性和可靠性
"""
import logging
from typing import Dict, List, Optional
from enum import Enum
from app.exceptions import InvalidStateTransitionError

logger = logging.getLogger(__name__)


class ProjectStatus(str, Enum):
    """项目状态枚举"""
    DRAFT = "draft"
    BLUEPRINT_READY = "blueprint_ready"
    PART_OUTLINES_READY = "part_outlines_ready"
    CHAPTER_OUTLINES_READY = "chapter_outlines_ready"
    WRITING = "writing"
    COMPLETED = "completed"


class ProjectStateMachine:
    """
    项目状态机
    管理项目状态的转换规则和验证逻辑
    """
    
    # 状态转换规则：当前状态 -> 允许转换到的状态列表
    TRANSITIONS: Dict[str, List[str]] = {
        ProjectStatus.DRAFT: [
            ProjectStatus.BLUEPRINT_READY,
        ],
        ProjectStatus.BLUEPRINT_READY: [
            ProjectStatus.PART_OUTLINES_READY,
            ProjectStatus.CHAPTER_OUTLINES_READY,
            ProjectStatus.DRAFT,  # 允许回退到draft重新生成蓝图
            ProjectStatus.BLUEPRINT_READY,  # 允许重新生成蓝图（保持当前状态）
        ],
        ProjectStatus.PART_OUTLINES_READY: [
            ProjectStatus.CHAPTER_OUTLINES_READY,
            ProjectStatus.BLUEPRINT_READY,  # 允许回退重新生成部分大纲
        ],
        ProjectStatus.CHAPTER_OUTLINES_READY: [
            ProjectStatus.WRITING,
            ProjectStatus.PART_OUTLINES_READY,  # 允许回退（长篇）
            ProjectStatus.BLUEPRINT_READY,  # 允许回退（短篇）
        ],
        ProjectStatus.WRITING: [
            ProjectStatus.COMPLETED,
            ProjectStatus.CHAPTER_OUTLINES_READY,  # 允许回退修改大纲
        ],
        ProjectStatus.COMPLETED: [
            ProjectStatus.WRITING,  # 允许继续编辑
        ],
    }
    
    # 状态描述（用于日志和错误提示）
    STATUS_DESCRIPTIONS: Dict[str, str] = {
        ProjectStatus.DRAFT: "草稿（灵感对话中）",
        ProjectStatus.BLUEPRINT_READY: "蓝图就绪",
        ProjectStatus.PART_OUTLINES_READY: "部分大纲就绪",
        ProjectStatus.CHAPTER_OUTLINES_READY: "章节大纲就绪",
        ProjectStatus.WRITING: "写作中",
        ProjectStatus.COMPLETED: "已完成",
    }
    
    def __init__(self, current_status: str):
        """
        初始化状态机
        
        Args:
            current_status: 当前项目状态
        """
        self.current_status = current_status
        
    def can_transition_to(self, new_status: str) -> bool:
        """
        检查是否可以转换到目标状态
        
        Args:
            new_status: 目标状态
            
        Returns:
            bool: 是否允许转换
        """
        allowed_transitions = self.TRANSITIONS.get(self.current_status, [])
        return new_status in allowed_transitions
    
    def transition_to(self, new_status: str, force: bool = False) -> str:
        """
        执行状态转换

        Args:
            new_status: 目标状态
            force: 是否强制转换（跳过验证）

        Returns:
            str: 新状态

        Raises:
            InvalidStateTransitionError: 非法状态转换
        """
        if not force and not self.can_transition_to(new_status):
            current_desc = self.STATUS_DESCRIPTIONS.get(self.current_status, self.current_status)
            new_desc = self.STATUS_DESCRIPTIONS.get(new_status, new_status)
            allowed = [self.STATUS_DESCRIPTIONS.get(s, s) for s in self.TRANSITIONS.get(self.current_status, [])]
            allowed_str = ', '.join(allowed) if allowed else '无'

            logger.error(
                "非法的状态转换: %s -> %s. 当前状态只能转换到: %s",
                current_desc, new_desc, allowed_str
            )
            raise InvalidStateTransitionError(current_desc, new_desc, allowed_str)

        logger.info(
            "项目状态转换: %s -> %s%s",
            self.STATUS_DESCRIPTIONS.get(self.current_status, self.current_status),
            self.STATUS_DESCRIPTIONS.get(new_status, new_status),
            " (强制)" if force else ""
        )

        self.current_status = new_status
        return new_status
    
    def get_allowed_transitions(self) -> List[str]:
        """
        获取当前状态允许转换到的所有状态
        
        Returns:
            List[str]: 允许的目标状态列表
        """
        return self.TRANSITIONS.get(self.current_status, [])
    
    def get_status_description(self, status: Optional[str] = None) -> str:
        """
        获取状态描述
        
        Args:
            status: 要查询的状态（None表示查询当前状态）
            
        Returns:
            str: 状态描述
        """
        target_status = status if status is not None else self.current_status
        return self.STATUS_DESCRIPTIONS.get(target_status, target_status)
    
    @classmethod
    def validate_transition(cls, current_status: str, new_status: str) -> bool:
        """
        静态方法：验证状态转换是否合法
        
        Args:
            current_status: 当前状态
            new_status: 目标状态
            
        Returns:
            bool: 是否合法
        """
        allowed_transitions = cls.TRANSITIONS.get(current_status, [])
        return new_status in allowed_transitions