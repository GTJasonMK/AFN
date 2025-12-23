"""
正文优化数据模型

定义请求、响应、事件等数据结构。
"""

from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


# ==================== 维度配置（可扩展） ====================

# 维度定义：标识符 -> 中文名称
# 修改此配置可调整检查维度，无需修改代码逻辑
DIMENSION_CONFIG: Dict[str, str] = {
    "coherence": "逻辑连贯性",      # 核心维度（优先级最高）
    "character": "角色一致性",      # 重要维度
    "foreshadow": "伏笔呼应",       # 重要维度
    "timeline": "时间线一致性",     # 重要维度
    "style": "风格一致性",          # 辅助维度
    "scene": "场景描写",            # 辅助维度
}

# 默认开启的维度（按优先级排序）
DEFAULT_DIMENSIONS: List[str] = list(DIMENSION_CONFIG.keys())

# 维度检测关键词：用于从思考文本中识别相关维度
# 格式：维度标识 -> 关键词列表
DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "coherence": ["连贯", "逻辑", "过渡"],
    "character": ["角色", "人物", "性格"],
    "foreshadow": ["伏笔", "铺垫", "呼应"],
    "timeline": ["时间", "顺序", "先后"],
    "style": ["风格", "语气", "文风"],
    "scene": ["场景", "地点", "环境"],
}

# 置信度检测关键词：用于估算思考步骤的置信度
HIGH_CONFIDENCE_KEYWORDS: List[str] = ["明显", "确定", "肯定", "必须", "严重", "重要"]
LOW_CONFIDENCE_KEYWORDS: List[str] = ["可能", "也许", "似乎", "好像", "不确定", "待"]


class CheckDimension:
    """检查维度定义"""

    # 从配置动态生成维度常量
    COHERENCE = "coherence"          # 逻辑连贯性（最主要）
    CHARACTER = "character"          # 角色一致性
    FORESHADOW = "foreshadow"        # 伏笔呼应
    TIMELINE = "timeline"            # 时间线一致性
    STYLE = "style"                  # 风格一致性
    SCENE = "scene"                  # 场景描写一致性

    @classmethod
    def get_default_dimensions(cls) -> List[str]:
        """获取默认开启的维度（全部）"""
        return DEFAULT_DIMENSIONS.copy()

    @classmethod
    def get_all_dimensions(cls) -> List[str]:
        """获取所有维度"""
        return list(DIMENSION_CONFIG.keys())

    @classmethod
    def get_dimension_name(cls, dimension: str) -> str:
        """获取维度的中文名称"""
        return DIMENSION_CONFIG.get(dimension, dimension)


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


class ThinkingStepType(str, Enum):
    """思考步骤类型"""
    ANALYSIS = "analysis"       # 分析当前内容
    RETRIEVAL = "retrieval"     # 检索相关信息
    COMPARISON = "comparison"   # 对比前后文
    DECISION = "decision"       # 做出决策
    VERIFICATION = "verification"  # 验证结论


class ThinkingStep(BaseModel):
    """
    P2-3: 结构化思考步骤

    将Agent的思考过程拆分为可追踪的步骤，便于：
    - 前端展示结构化的思考链
    - 调试Agent的决策过程
    - 评估Agent的推理质量
    """
    step_type: ThinkingStepType = Field(..., description="步骤类型")
    content: str = Field(..., description="思考内容")
    evidence: List[str] = Field(default_factory=list, description="支撑证据")
    confidence: float = Field(default=0.5, ge=0, le=1, description="置信度(0-1)")
    related_dimension: Optional[str] = Field(default=None, description="相关检查维度")


class StructuredThinking(BaseModel):
    """
    结构化思考过程

    将原始思考文本解析为结构化步骤序列。
    """
    raw_content: str = Field(..., description="原始思考内容")
    steps: List[ThinkingStep] = Field(default_factory=list, description="结构化步骤")
    summary: str = Field(default="", description="思考总结")
    next_action_hint: Optional[str] = Field(default=None, description="下一步行动提示")

    @classmethod
    def parse_from_text(cls, raw_text: str) -> "StructuredThinking":
        """
        从原始思考文本解析出结构化步骤

        解析策略：
        1. 按句号或换行分割文本
        2. 根据关键词识别步骤类型
        3. 提取证据（引号内容、具体引用）
        4. 估算置信度（基于确定性词汇）

        关键词配置在文件顶部的常量中定义，便于维护和扩展。
        """
        if not raw_text:
            return cls(raw_content="", steps=[], summary="")

        steps = []
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

        # 步骤类型关键词映射（内部使用，与维度配置分离）
        type_keywords = {
            ThinkingStepType.ANALYSIS: ["分析", "观察", "发现", "注意到", "段落", "内容"],
            ThinkingStepType.RETRIEVAL: ["检索", "查询", "获取", "RAG", "前文", "历史"],
            ThinkingStepType.COMPARISON: ["对比", "比较", "与之前", "前后", "变化", "差异"],
            ThinkingStepType.DECISION: ["决定", "选择", "需要", "应该", "计划", "下一步"],
            ThinkingStepType.VERIFICATION: ["验证", "确认", "检查", "核实", "没有问题", "一致"],
        }

        for line in lines:
            if not line:
                continue

            # 识别步骤类型
            step_type = ThinkingStepType.ANALYSIS  # 默认
            for stype, keywords in type_keywords.items():
                if any(kw in line for kw in keywords):
                    step_type = stype
                    break

            # 提取证据（引号内容）
            import re
            evidence = re.findall(r'["\u201c\u300c]([^"\u201d\u300d]+)["\u201d\u300d]', line)

            # 估算置信度（使用配置常量）
            confidence = 0.5
            if any(word in line for word in HIGH_CONFIDENCE_KEYWORDS):
                confidence = 0.8
            elif any(word in line for word in LOW_CONFIDENCE_KEYWORDS):
                confidence = 0.3

            # 识别相关维度（使用配置常量）
            dimension = None
            for dim, kws in DIMENSION_KEYWORDS.items():
                if any(kw in line for kw in kws):
                    dimension = dim
                    break

            steps.append(ThinkingStep(
                step_type=step_type,
                content=line,
                evidence=evidence,
                confidence=confidence,
                related_dimension=dimension,
            ))

        # 生成总结（取最后一个decision类型的步骤，或最后一步）
        summary = ""
        for step in reversed(steps):
            if step.step_type == ThinkingStepType.DECISION:
                summary = step.content
                break
        if not summary and steps:
            summary = steps[-1].content

        # 提取下一步行动提示
        next_action = None
        for step in steps:
            if step.step_type == ThinkingStepType.DECISION and "使用" in step.content:
                next_action = step.content
                break

        return cls(
            raw_content=raw_text,
            steps=steps,
            summary=summary[:200] if summary else "",
            next_action_hint=next_action,
        )


class ThinkingEvent(BaseModel):
    """
    思考过程事件

    P2-3优化: 支持结构化思考步骤展示
    """
    paragraph_index: int = Field(..., description="段落索引")
    content: str = Field(..., description="思考内容（原始文本）")
    step: str = Field(..., description="当前步骤标识")
    # P2-3: 新增结构化字段
    structured: Optional[StructuredThinking] = Field(default=None, description="结构化思考过程")
    step_count: int = Field(default=0, description="思考步骤数")
    primary_dimension: Optional[str] = Field(default=None, description="主要关注维度")


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
    total_chapters: int = Field(default=0, description="小说总章节数（用于时序感知检索）")
