from typing import List, Literal, Optional

from pydantic import BaseModel, Field


RollbackTargetStatus = Literal[
    "blueprint_ready",
    "part_outlines_ready",
    "chapter_outlines_ready",
]

WorkflowStatus = Literal[
    "draft",
    "blueprint_ready",
    "part_outlines_ready",
    "chapter_outlines_ready",
    "writing",
    "completed",
]

CleanupKind = Literal[
    "delete_chapters",
    "delete_chapter_outlines",
    "delete_part_outlines",
    "delete_vector_store",
]


class ProjectWorkflowCleanupImpact(BaseModel):
    """回退步骤可能触发的清理影响（用于前端可视化展示）"""

    kind: CleanupKind
    title: str = Field(..., description="面向用户的清理动作标题")
    tables: List[str] = Field(default_factory=list, description="涉及的数据库表（或外部数据域）")

    count: Optional[int] = Field(default=None, description="预计删除的条目数量（若可估算）")
    chapter_start: Optional[int] = Field(default=None, description="涉及的起始章节号（若适用）")
    chapter_end: Optional[int] = Field(default=None, description="涉及的结束章节号（若适用）")
    part_start: Optional[int] = Field(default=None, description="涉及的起始部分号（若适用）")
    part_end: Optional[int] = Field(default=None, description="涉及的结束部分号（若适用）")

    note: Optional[str] = Field(default=None, description="补充说明（可选）")


class ProjectWorkflowRollbackStepPreview(BaseModel):
    """单步回退预览（包含该步会触发的清理动作）"""

    from_status: WorkflowStatus
    to_status: WorkflowStatus
    from_label: str
    to_label: str
    impacts: List[ProjectWorkflowCleanupImpact] = Field(default_factory=list)


class ProjectWorkflowRollbackPreviewResponse(BaseModel):
    """回退预览响应（前端可直接渲染）"""

    project_id: str
    from_status: WorkflowStatus
    to_status: WorkflowStatus
    path: List[WorkflowStatus] = Field(default_factory=list, description="实际执行的状态转换路径（不含起点）")
    steps: List[ProjectWorkflowRollbackStepPreview] = Field(default_factory=list)
    summary: str = Field("", description="预格式化摘要（适用于确认弹窗直接展示）")


class ProjectWorkflowRollbackRequest(BaseModel):
    """项目工作流回退请求

    说明：
    - 回退是破坏性操作：会删除依赖数据（章节正文 / 章节大纲 / 部分大纲等）。
    - 需要前端显式传入 confirm=true，避免误触导致数据丢失。
    """

    target_status: RollbackTargetStatus = Field(..., description="回退目标状态")
    confirm: bool = Field(False, description="必须为 true 才会执行回退")


class ProjectWorkflowRollbackResponse(BaseModel):
    """项目工作流回退响应（用于前端提示）"""

    project_id: str
    from_status: WorkflowStatus
    to_status: WorkflowStatus
    path: List[WorkflowStatus] = Field(default_factory=list, description="实际执行的状态转换路径（不含起点）")
    message: str
