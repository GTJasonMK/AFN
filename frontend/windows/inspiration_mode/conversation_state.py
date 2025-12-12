"""
对话状态管理类

将 InspirationMode 中的对话状态封装为独立的数据类，
遵循单一职责原则，使状态管理更清晰。

设计说明：
- ConversationState: 管理对话逻辑状态（project_id, blueprint等）
- UI组件状态（current_ai_bubble等）保留在 InspirationMode 中
- 提供 reset() 方法统一重置状态
"""

from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class ConversationState:
    """对话状态数据类

    封装灵感对话的核心状态，与UI组件状态分离。

    Attributes:
        project_id: 当前项目ID
        blueprint: 生成的蓝图数据
        is_complete: 对话是否完成（AI表示信息足够）
        pending_options: 流式接收的选项缓存

    用法示例：
        state = ConversationState()
        state.project_id = "xxx"
        state.mark_complete()

        # 重置为新对话
        state.reset()

        # 重置为继续对话
        state.reset(project_id="xxx")
    """
    project_id: Optional[str] = None
    blueprint: Optional[dict] = None
    is_complete: bool = False
    pending_options: List[str] = field(default_factory=list)

    def reset(self, project_id: Optional[str] = None):
        """重置状态

        Args:
            project_id: 如果提供，表示继续已有对话；否则为全新对话
        """
        self.project_id = project_id
        self.blueprint = None
        self.is_complete = False
        self.pending_options = []

    def mark_complete(self):
        """标记对话完成"""
        self.is_complete = True

    def has_project(self) -> bool:
        """检查是否有关联的项目"""
        return self.project_id is not None

    def clear_pending_options(self):
        """清空待处理选项"""
        self.pending_options = []

    def add_pending_option(self, option: str):
        """添加待处理选项"""
        self.pending_options.append(option)
