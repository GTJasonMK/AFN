"""
正文优化数据模型

定义请求、响应、事件等数据结构。
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class CheckDimension:
    """检查维度定义"""

    # 核心维度（优先级最高）
    COHERENCE = "coherence"          # 逻辑连贯性（最主要）

    # 重要维度
    CHARACTER = "character"          # 角色一致性
    FORESHADOW = "foreshadow"        # 伏笔呼应
    TIMELINE = "timeline"            # 时间线一致性

    # 辅助维度
    STYLE = "style"                  # 风格一致性
    SCENE = "scene"                  # 场景描写一致性

    @classmethod
    def get_default_dimensions(cls) -> List[str]:
        """获取默认开启的维度（全部）"""
        return [
            cls.COHERENCE,    # 逻辑连贯性
            cls.CHARACTER,    # 角色一致性
            cls.FORESHADOW,   # 伏笔呼应
            cls.TIMELINE,     # 时间线一致性
            cls.STYLE,        # 风格一致性
            cls.SCENE,        # 场景描写
        ]

    @classmethod
    def get_all_dimensions(cls) -> List[str]:
        """获取所有维度"""
        return cls.get_default_dimensions()

    @classmethod
    def get_dimension_name(cls, dimension: str) -> str:
        """获取维度的中文名称"""
        names = {
            cls.COHERENCE: "逻辑连贯性",
            cls.CHARACTER: "角色一致性",
            cls.FORESHADOW: "伏笔呼应",
            cls.TIMELINE: "时间线一致性",
            cls.STYLE: "风格一致性",
            cls.SCENE: "场景描写",
        }
        return names.get(dimension, dimension)


class AnalysisScope(str, Enum):
    """分析范围"""
    FULL = "full"              # 全章节分析
    SELECTED = "selected"      # 选中段落分析


class OptimizationMode(str, Enum):
    """优化模式 - 参考Claude Code的三层权限设计"""
    REVIEW = "review"      # 审核模式：每个建议暂停等待确认
    AUTO = "auto"          # 自动模式：自动处理所有建议
    PLAN = "plan"          # 计划模式：先完成分析，用户选择性应用


class OptimizationEventType:
    """SSE事件类型定义"""

    # 工作流控制
    WORKFLOW_START = "workflow_start"      # 开始优化
    WORKFLOW_COMPLETE = "workflow_complete" # 完成优化
    WORKFLOW_PAUSED = "workflow_paused"    # 工作流暂停（等待用户确认）
    WORKFLOW_RESUMED = "workflow_resumed"  # 工作流恢复

    # 段落处理
    PARAGRAPH_START = "paragraph_start"    # 开始处理段落
    PARAGRAPH_COMPLETE = "paragraph_complete" # 完成段落处理

    # Agent思考过程（核心）
    THINKING = "thinking"                  # 思考过程
    ACTION = "action"                      # 执行动作
    OBSERVATION = "observation"            # 观察结果

    # 结果输出
    SUGGESTION = "suggestion"              # 修改建议
    ERROR = "error"                        # 错误


class SuggestionPriority(str, Enum):
    """建议优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SuggestionCategory(str, Enum):
    """建议类别"""
    COHERENCE = "coherence"      # 连贯性问题
    CHARACTER = "character"      # 角色问题
    FORESHADOW = "foreshadow"    # 伏笔问题
    TIMELINE = "timeline"        # 时间线问题
    STYLE = "style"              # 风格问题
    SCENE = "scene"              # 场景问题


# ====== 请求模型 ======

class OptimizeContentRequest(BaseModel):
    """优化请求"""
    content: str = Field(..., description="章节正文")
    scope: AnalysisScope = Field(default=AnalysisScope.FULL, description="分析范围")
    selected_paragraphs: Optional[List[int]] = Field(default=None, description="选中的段落索引（0-based）")
    dimensions: Optional[List[str]] = Field(default=None, description="检查维度")
    mode: OptimizationMode = Field(default=OptimizationMode.AUTO, description="优化模式")

    @field_validator('dimensions', mode='before')
    @classmethod
    def set_default_dimensions(cls, v):
        """设置默认维度"""
        if v is None:
            return CheckDimension.get_default_dimensions()
        return v

    @field_validator('selected_paragraphs', mode='before')
    @classmethod
    def validate_selected_paragraphs(cls, v, info):
        """验证选中段落"""
        if info.data.get('scope') == AnalysisScope.SELECTED and not v:
            raise ValueError("选择分析模式下必须指定段落索引")
        return v


# ====== 事件数据模型 ======

class WorkflowStartEvent(BaseModel):
    """工作流开始事件"""
    session_id: str = Field(..., description="会话ID，用于暂停/继续控制")
    total_paragraphs: int = Field(..., description="总段落数")
    dimensions: List[str] = Field(..., description="检查维度")
    mode: str = Field(default="auto", description="优化模式")


class WorkflowCompleteEvent(BaseModel):
    """工作流完成事件"""
    total_suggestions: int = Field(..., description="总建议数")
    high_priority_count: int = Field(default=0, description="高优先级建议数")
    summary: str = Field(default="分析完成", description="汇总信息")


class WorkflowPausedEvent(BaseModel):
    """工作流暂停事件"""
    session_id: str = Field(..., description="会话ID")
    message: str = Field(default="等待用户确认", description="暂停原因")


class ParagraphStartEvent(BaseModel):
    """段落开始处理事件"""
    index: int = Field(..., description="段落索引")
    text_preview: str = Field(..., description="段落预览（前100字符）")


class ParagraphCompleteEvent(BaseModel):
    """段落处理完成事件"""
    index: int = Field(..., description="段落索引")
    suggestion_count: int = Field(default=0, description="该段落的建议数")


class ThinkingEvent(BaseModel):
    """思考过程事件"""
    paragraph_index: int = Field(..., description="段落索引")
    content: str = Field(..., description="思考内容")
    step: str = Field(..., description="当前步骤")


class ActionEvent(BaseModel):
    """执行动作事件"""
    paragraph_index: int = Field(..., description="段落索引")
    action: str = Field(..., description="动作类型")
    description: str = Field(..., description="动作描述")


class ObservationEvent(BaseModel):
    """观察结果事件"""
    paragraph_index: int = Field(..., description="段落索引")
    action: str = Field(..., description="对应的动作类型")
    result: str = Field(..., description="观察结果")
    relevance: Optional[float] = Field(default=None, description="相关度分数")


class SuggestionEvent(BaseModel):
    """修改建议事件"""
    paragraph_index: int = Field(..., description="段落索引")
    original_text: str = Field(..., description="原文")
    suggested_text: str = Field(..., description="建议修改后的文本")
    reason: str = Field(..., description="修改理由")
    category: str = Field(..., description="建议类别")
    priority: str = Field(default="medium", description="优先级")


class ErrorEvent(BaseModel):
    """错误事件"""
    message: str = Field(..., description="错误信息")
    paragraph_index: Optional[int] = Field(default=None, description="相关段落索引")


# ====== 内部数据模型 ======

class ParagraphAnalysis(BaseModel):
    """段落分析结果"""
    index: int = Field(..., description="段落索引")
    text: str = Field(..., description="段落文本")
    characters: List[str] = Field(default_factory=list, description="涉及的角色")
    scene: Optional[str] = Field(default=None, description="场景/地点")
    time_marker: Optional[str] = Field(default=None, description="时间标记")
    emotion_tone: Optional[str] = Field(default=None, description="情感基调")
    key_actions: List[str] = Field(default_factory=list, description="关键动作")


class CoherenceIssue(BaseModel):
    """连贯性问题"""
    dimension: str = Field(..., description="问题维度")
    description: str = Field(..., description="问题描述")
    severity: str = Field(default="medium", description="严重程度")
    location: Optional[str] = Field(default=None, description="问题位置")


class RAGContext(BaseModel):
    """RAG检索上下文"""
    character_states: List[dict] = Field(default_factory=list, description="角色状态")
    foreshadowings: List[dict] = Field(default_factory=list, description="相关伏笔")
    related_chunks: List[dict] = Field(default_factory=list, description="相关文本片段")
    chapter_summaries: List[dict] = Field(default_factory=list, description="章节摘要")


class OptimizationContext(BaseModel):
    """优化上下文"""
    project_id: str = Field(..., description="项目ID")
    chapter_number: int = Field(..., description="章节号")
    blueprint_core: Optional[str] = Field(default=None, description="蓝图核心信息")
    character_names: List[str] = Field(default_factory=list, description="已知角色名")
    style_guide: Optional[str] = Field(default=None, description="风格指南")
    prev_chapter_ending: Optional[str] = Field(default=None, description="前章结尾")
