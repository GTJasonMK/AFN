"""主角档案系统Pydantic Schemas

定义主角档案相关的请求/响应数据模型。
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AttributeCategory(str, Enum):
    """属性类别枚举"""
    EXPLICIT = "explicit"  # 显性属性
    IMPLICIT = "implicit"  # 隐性属性
    SOCIAL = "social"      # 社会属性


class AttributeOperation(str, Enum):
    """属性操作类型枚举"""
    ADD = "add"
    MODIFY = "modify"
    DELETE = "delete"


class ClassificationResult(str, Enum):
    """行为分类结果枚举"""
    CONFORM = "conform"        # 符合
    NON_CONFORM = "non-conform"  # 不符合


# ============== 档案相关 Schemas ==============

class ProtagonistProfileBase(BaseModel):
    """主角档案基础模型"""
    character_name: str = Field(..., description="角色名称", min_length=1, max_length=128)


class ProtagonistProfileCreate(ProtagonistProfileBase):
    """创建主角档案请求"""
    explicit_attributes: Dict[str, Any] = Field(default_factory=dict, description="显性属性")
    implicit_attributes: Dict[str, Any] = Field(default_factory=dict, description="隐性属性")
    social_attributes: Dict[str, Any] = Field(default_factory=dict, description="社会属性")


class ProtagonistProfileResponse(ProtagonistProfileBase):
    """主角档案响应"""
    id: int
    project_id: str
    explicit_attributes: Dict[str, Any]
    implicit_attributes: Dict[str, Any]
    social_attributes: Dict[str, Any]
    last_synced_chapter: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProtagonistProfileSummary(BaseModel):
    """主角档案摘要（用于列表展示）"""
    id: int
    character_name: str
    last_synced_chapter: int
    attribute_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="各类属性数量统计 {explicit: n, implicit: n, social: n}"
    )
    created_at: datetime

    class Config:
        from_attributes = True


# ============== 属性操作相关 Schemas ==============

class AttributeAddRequest(BaseModel):
    """添加属性请求"""
    category: AttributeCategory = Field(..., description="属性类别")
    key: str = Field(..., description="属性键名", min_length=1, max_length=128)
    value: Any = Field(..., description="属性值")
    event_cause: str = Field(..., description="触发事件描述")
    evidence: str = Field(..., description="原文引用证据", min_length=1)
    chapter_number: int = Field(..., description="章节号", ge=1)


class AttributeModifyRequest(BaseModel):
    """修改属性请求"""
    new_value: Any = Field(..., description="新属性值")
    event_cause: str = Field(..., description="触发事件描述")
    evidence: str = Field(..., description="原文引用证据", min_length=1)
    chapter_number: int = Field(..., description="章节号", ge=1)


class AttributeDeleteRequest(BaseModel):
    """删除属性请求（标记删除）"""
    reason: str = Field(..., description="删除原因")
    evidence: str = Field(..., description="支持删除的原文证据", min_length=1)
    chapter_number: int = Field(..., description="章节号", ge=1)


# ============== 变更历史相关 Schemas ==============

class AttributeChangeResponse(BaseModel):
    """属性变更记录响应"""
    id: int
    profile_id: int
    chapter_number: int
    attribute_category: str
    attribute_key: str
    operation: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    change_description: str
    event_cause: str
    evidence: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChangeHistoryQuery(BaseModel):
    """变更历史查询参数"""
    start_chapter: Optional[int] = Field(default=None, description="起始章节", ge=1)
    end_chapter: Optional[int] = Field(default=None, description="结束章节", ge=1)
    category: Optional[AttributeCategory] = Field(default=None, description="属性类别")


# ============== 行为记录相关 Schemas ==============

class BehaviorRecordResponse(BaseModel):
    """行为记录响应"""
    id: int
    profile_id: int
    chapter_number: int
    behavior_description: str
    original_text: str
    behavior_tags: List[str]
    classification_results: Dict[str, str]
    created_at: datetime

    class Config:
        from_attributes = True


class BehaviorRecordQuery(BaseModel):
    """行为记录查询参数"""
    chapter: Optional[int] = Field(default=None, description="指定章节", ge=1)
    limit: Optional[int] = Field(default=20, description="返回数量限制", ge=1, le=100)


# ============== 删除标记相关 Schemas ==============

class DeletionMarkResponse(BaseModel):
    """删除标记响应"""
    id: int
    profile_id: int
    attribute_category: str
    attribute_key: str
    chapter_number: int
    mark_reason: str
    evidence: str
    consecutive_count: int
    last_marked_chapter: int
    is_executed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DeletionMarkQuery(BaseModel):
    """删除标记查询参数"""
    category: Optional[AttributeCategory] = Field(default=None, description="属性类别")


# ============== 同步相关 Schemas ==============

class SyncRequest(BaseModel):
    """章节同步请求"""
    chapter_number: int = Field(..., description="要同步的章节号", ge=1)


class SyncResult(BaseModel):
    """同步结果"""
    changes_applied: int = Field(..., description="应用的变更数")
    behaviors_recorded: int = Field(..., description="记录的行为数")
    deletions_marked: int = Field(..., description="标记的删除数")
    synced_chapter: int = Field(..., description="同步的章节号")


# ============== 隐性属性分析相关 Schemas ==============

class ImplicitStatsQuery(BaseModel):
    """隐性属性统计查询参数"""
    attribute_key: str = Field(..., description="属性键名")
    window: int = Field(default=10, description="统计窗口大小（章节数）", ge=1, le=50)


class ImplicitStatsResponse(BaseModel):
    """隐性属性统计响应"""
    attribute_key: str
    total: int = Field(..., description="总记录数")
    conform_count: int = Field(..., description="符合次数")
    non_conform_count: int = Field(..., description="不符合次数")
    conform_rate: float = Field(..., description="符合率")
    threshold_reached: bool = Field(..., description="是否达到更新阈值")


class ImplicitCheckRequest(BaseModel):
    """隐性属性检查请求"""
    attribute_key: str = Field(..., description="属性键名")


class ImplicitCheckResponse(BaseModel):
    """隐性属性检查响应（LLM建议）"""
    attribute_key: str
    current_value: Any
    decision: str = Field(..., description="决策: keep/modify/delete")
    reasoning: str = Field(..., description="推理过程")
    suggested_new_value: Optional[Any] = Field(default=None, description="建议的新值")
    evidence_summary: str = Field(..., description="证据汇总")


# ============== LLM分析结果相关 Schemas ==============

class LLMAttributeChange(BaseModel):
    """LLM返回的属性变更"""
    category: str
    key: str
    operation: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    change_description: str
    event_cause: str
    evidence: str


class LLMBehavior(BaseModel):
    """LLM返回的行为记录"""
    description: str
    original_text: str
    tags: List[str]


class LLMDeletionCandidate(BaseModel):
    """LLM返回的删除候选"""
    category: str
    key: str
    reason: str
    evidence: str


class ChapterAnalysisResult(BaseModel):
    """章节分析结果（LLM返回）"""
    attribute_changes: List[LLMAttributeChange] = Field(default_factory=list)
    behaviors: List[LLMBehavior] = Field(default_factory=list)
    deletion_candidates: List[LLMDeletionCandidate] = Field(default_factory=list)


class BehaviorClassificationResult(BaseModel):
    """行为分类结果（LLM返回）"""
    classifications: Dict[str, str] = Field(
        default_factory=dict,
        description="分类结果 {属性名: conform/non-conform}"
    )
    reasoning: str = Field(..., description="推理过程")
    suggested_new_attributes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="建议添加的新属性"
    )


class ImplicitUpdateDecision(BaseModel):
    """隐性属性更新决策（LLM返回）"""
    decision: str = Field(..., description="决策: keep/modify/delete")
    reasoning: str = Field(..., description="推理过程")
    new_value: Optional[Any] = Field(default=None, description="新值（modify时）")
    evidence_summary: str = Field(..., description="证据汇总")


# ============== 状态快照相关 Schemas （类Git节点） ==============

class SnapshotResponse(BaseModel):
    """状态快照响应"""
    id: int
    profile_id: int
    chapter_number: int
    explicit_attributes: Dict[str, Any]
    implicit_attributes: Dict[str, Any]
    social_attributes: Dict[str, Any]
    changes_in_chapter: int = Field(..., description="本章变更数量")
    behaviors_in_chapter: int = Field(..., description="本章行为数量")
    created_at: datetime

    class Config:
        from_attributes = True


class SnapshotSummary(BaseModel):
    """快照摘要（用于列表展示）"""
    chapter_number: int
    changes_in_chapter: int
    behaviors_in_chapter: int
    attribute_counts: Dict[str, int] = Field(
        description="各类属性数量 {explicit: n, implicit: n, social: n}"
    )
    created_at: datetime


class SnapshotListResponse(BaseModel):
    """快照列表响应"""
    profile_id: int
    character_name: str
    total_snapshots: int
    snapshots: List[SnapshotSummary]


class AttributeDiff(BaseModel):
    """单类属性的差异"""
    added: Dict[str, Any] = Field(default_factory=dict, description="新增的属性")
    modified: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="修改的属性 {key: {from: old, to: new}}"
    )
    deleted: Dict[str, Any] = Field(default_factory=dict, description="删除的属性")


class DiffResponse(BaseModel):
    """状态差异响应（类Git diff）"""
    profile_id: int
    character_name: str
    from_chapter: int
    to_chapter: int
    categories: Dict[str, AttributeDiff] = Field(
        default_factory=dict,
        description="各类属性的差异 {explicit: {...}, implicit: {...}, social: {...}}"
    )
    has_changes: bool = Field(..., description="是否有任何变化")


class RollbackRequest(BaseModel):
    """回滚请求"""
    target_chapter: int = Field(..., description="目标章节号", ge=1)


class RollbackResponse(BaseModel):
    """回滚响应"""
    success: bool
    target_chapter: int
    message: str


# ============== 冲突检测相关 Schemas ==============

class ProfileConflictCheck(BaseModel):
    """档案冲突检测响应"""
    has_conflict: bool = Field(..., description="是否存在冲突")
    last_synced_chapter: int = Field(..., description="档案最后同步的章节号")
    max_available_chapter: int = Field(..., description="当前最大可用章节号")
    available_snapshot_chapters: List[int] = Field(
        default_factory=list,
        description="可回滚的快照章节列表（<= max_available_chapter）"
    )
