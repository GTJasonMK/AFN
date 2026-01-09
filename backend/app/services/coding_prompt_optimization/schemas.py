"""
编程项目 Prompt 优化 - 数据模型定义

定义检查维度、事件类型、优化模式等核心数据结构。
支持两种 Prompt 类型：实现 Prompt 和审查 Prompt。
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ==================== Prompt 类型 ====================

class PromptType(str, Enum):
    """Prompt 类型"""
    IMPLEMENTATION = "implementation"   # 实现 Prompt
    REVIEW = "review"                   # 审查 Prompt


# ==================== 实现 Prompt 检查维度配置 ====================

class PromptDimension(str, Enum):
    """实现 Prompt 质量检查维度"""
    COMPLETENESS = "completeness"       # 功能完整性
    INTERFACE = "interface"             # 接口定义清晰度
    DEPENDENCY = "dependency"           # 依赖关系正确性
    IMPLEMENTATION = "implementation"   # 实现步骤合理性
    ERROR_HANDLING = "error_handling"   # 错误处理完备性
    SECURITY = "security"               # 安全性考虑
    PERFORMANCE = "performance"         # 性能考虑


# 实现 Prompt 维度中文名称
DIMENSION_DISPLAY_NAMES: Dict[str, str] = {
    "completeness": "功能完整性",
    "interface": "接口定义",
    "dependency": "依赖关系",
    "implementation": "实现步骤",
    "error_handling": "错误处理",
    "security": "安全性",
    "performance": "性能",
}

# 实现 Prompt 维度权重（影响检查优先级和建议排序）
DIMENSION_WEIGHTS: Dict[str, float] = {
    "completeness": 1.0,       # 最高优先级
    "interface": 0.95,
    "dependency": 0.9,
    "implementation": 0.85,
    "error_handling": 0.8,
    "security": 0.75,
    "performance": 0.7,
}

# 实现 Prompt 维度检测关键词（自动识别维度）
DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "completeness": ["需求", "功能", "覆盖", "缺失", "遗漏", "完整"],
    "interface": ["接口", "输入", "输出", "参数", "返回", "定义", "签名"],
    "dependency": ["依赖", "导入", "模块", "引用", "调用", "耦合"],
    "implementation": ["实现", "步骤", "流程", "逻辑", "算法", "方案"],
    "error_handling": ["错误", "异常", "边界", "校验", "处理", "容错"],
    "security": ["安全", "注入", "XSS", "权限", "认证", "授权", "加密"],
    "performance": ["性能", "效率", "优化", "缓存", "并发", "复杂度"],
}

# 实现 Prompt 默认检查维度（按优先级排序）
DEFAULT_DIMENSIONS: List[str] = [
    "completeness",
    "interface",
    "dependency",
    "implementation",
    "error_handling",
]


# ==================== 审查 Prompt 检查维度配置 ====================

class ReviewDimension(str, Enum):
    """审查 Prompt 质量检查维度"""
    TEST_COVERAGE = "test_coverage"             # 测试覆盖度
    ACCEPTANCE_CRITERIA = "acceptance_criteria" # 验收标准完整性
    EDGE_CASES = "edge_cases"                   # 边界条件覆盖
    SECURITY_CHECK = "security_check"           # 安全检查项
    PERFORMANCE_CHECK = "performance_check"     # 性能检查项
    CODE_QUALITY = "code_quality"               # 代码质量检查
    DOCUMENTATION = "documentation"             # 文档检查


# 审查 Prompt 维度中文名称
REVIEW_DIMENSION_DISPLAY_NAMES: Dict[str, str] = {
    "test_coverage": "测试覆盖",
    "acceptance_criteria": "验收标准",
    "edge_cases": "边界条件",
    "security_check": "安全检查",
    "performance_check": "性能检查",
    "code_quality": "代码质量",
    "documentation": "文档检查",
}

# 审查 Prompt 维度权重
REVIEW_DIMENSION_WEIGHTS: Dict[str, float] = {
    "test_coverage": 1.0,           # 最高优先级
    "acceptance_criteria": 0.95,
    "edge_cases": 0.9,
    "security_check": 0.85,
    "performance_check": 0.8,
    "code_quality": 0.75,
    "documentation": 0.7,
}

# 审查 Prompt 维度检测关键词
REVIEW_DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "test_coverage": ["测试", "单元测试", "集成测试", "覆盖", "用例", "断言"],
    "acceptance_criteria": ["验收", "标准", "条件", "通过", "完成", "交付"],
    "edge_cases": ["边界", "极端", "空值", "null", "异常输入", "特殊情况"],
    "security_check": ["安全", "注入", "XSS", "权限", "认证", "漏洞"],
    "performance_check": ["性能", "响应时间", "吞吐量", "内存", "CPU", "负载"],
    "code_quality": ["代码规范", "命名", "结构", "可读性", "复杂度", "重复"],
    "documentation": ["文档", "注释", "说明", "README", "API文档", "使用说明"],
}

# 审查 Prompt 默认检查维度（按优先级排序）
DEFAULT_REVIEW_DIMENSIONS: List[str] = [
    "test_coverage",
    "acceptance_criteria",
    "edge_cases",
    "security_check",
    "code_quality",
]


# ==================== 统一维度访问函数 ====================

def get_dimension_weight(dimension: str, prompt_type: PromptType = PromptType.IMPLEMENTATION) -> float:
    """获取维度权重"""
    if prompt_type == PromptType.REVIEW:
        return REVIEW_DIMENSION_WEIGHTS.get(dimension, 0.5)
    return DIMENSION_WEIGHTS.get(dimension, 0.5)


def get_dimension_display_name(dimension: str, prompt_type: PromptType = PromptType.IMPLEMENTATION) -> str:
    """获取维度中文名称"""
    if prompt_type == PromptType.REVIEW:
        return REVIEW_DIMENSION_DISPLAY_NAMES.get(dimension, dimension)
    return DIMENSION_DISPLAY_NAMES.get(dimension, dimension)


def get_default_dimensions(prompt_type: PromptType = PromptType.IMPLEMENTATION) -> List[str]:
    """获取默认检查维度"""
    if prompt_type == PromptType.REVIEW:
        return DEFAULT_REVIEW_DIMENSIONS.copy()
    return DEFAULT_DIMENSIONS.copy()


def get_all_dimension_names(prompt_type: PromptType = PromptType.IMPLEMENTATION) -> Dict[str, str]:
    """获取所有维度名称映射"""
    if prompt_type == PromptType.REVIEW:
        return REVIEW_DIMENSION_DISPLAY_NAMES.copy()
    return DIMENSION_DISPLAY_NAMES.copy()


def detect_dimension_from_text(text: str, prompt_type: PromptType = PromptType.IMPLEMENTATION) -> Optional[str]:
    """从文本中检测相关维度"""
    keywords_map = REVIEW_DIMENSION_KEYWORDS if prompt_type == PromptType.REVIEW else DIMENSION_KEYWORDS
    for dim, keywords in keywords_map.items():
        for keyword in keywords:
            if keyword in text:
                return dim
    return None


# ==================== 优化模式 ====================

class OptimizationMode(str, Enum):
    """优化模式"""
    AUTO = "auto"           # 自动模式：无暂停，直接完成
    REVIEW = "review"       # 审核模式：每个建议后暂停
    PLAN = "plan"           # 计划模式：完成分析后暂停，用户选择建议


# ==================== 事件类型 ====================

class OptimizationEventType:
    """优化事件类型（用于 SSE 流式输出）"""
    # 工作流控制
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    PLAN_READY = "plan_ready"

    # Agent 思考过程
    THINKING = "thinking"
    ACTION = "action"
    OBSERVATION = "observation"

    # 结果输出
    SUGGESTION = "suggestion"
    ERROR = "error"


# ==================== 数据模型 ====================

class FeatureContext(BaseModel):
    """功能上下文"""
    feature_id: str
    feature_number: int
    feature_name: str
    feature_description: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None
    priority: Optional[str] = None

    # 所属层级
    system_number: Optional[int] = None
    system_name: Optional[str] = None
    module_number: Optional[int] = None
    module_name: Optional[str] = None

    # Prompt 内容
    prompt_content: Optional[str] = None
    prompt_version_id: Optional[str] = None


class ProjectContext(BaseModel):
    """项目上下文"""
    project_id: str
    project_name: str

    # 蓝图信息
    architecture_synopsis: Optional[str] = None
    tech_stack: Optional[Dict[str, Any]] = None
    core_requirements: Optional[List[Dict[str, Any]]] = None
    technical_challenges: Optional[List[Dict[str, Any]]] = None
    dependencies: Optional[List[Dict[str, Any]]] = None


class OptimizationContext(BaseModel):
    """优化上下文"""
    project: ProjectContext
    feature: FeatureContext
    related_features: List[FeatureContext] = Field(default_factory=list)


class SuggestionSeverity(str, Enum):
    """建议严重程度"""
    HIGH = "high"           # 必须修改
    MEDIUM = "medium"       # 建议修改
    LOW = "low"             # 可选优化


class Suggestion(BaseModel):
    """优化建议"""
    id: str
    dimension: str                          # 关联维度
    severity: SuggestionSeverity            # 严重程度
    description: str                        # 问题描述
    original_text: Optional[str] = None     # 原始文本
    suggested_text: Optional[str] = None    # 建议文本
    reasoning: str                          # 推理过程
    confidence: float = 0.8                 # 置信度


class ThinkingStepType(str, Enum):
    """思考步骤类型"""
    ANALYSIS = "analysis"           # 分析
    RETRIEVAL = "retrieval"         # 检索
    COMPARISON = "comparison"       # 对比
    DECISION = "decision"           # 决策
    VERIFICATION = "verification"   # 验证


class ThinkingStep(BaseModel):
    """结构化思考步骤"""
    step_type: ThinkingStepType
    content: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.5
    related_dimension: Optional[str] = None


class StructuredThinking(BaseModel):
    """结构化思考"""
    raw_content: str
    steps: List[ThinkingStep] = Field(default_factory=list)
    summary: str = ""
    next_action_hint: Optional[str] = None

    @classmethod
    def parse_from_text(cls, raw_text: str) -> "StructuredThinking":
        """从原始文本解析结构化思考"""
        steps = []
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]

        # 关键词映射到步骤类型
        type_keywords = {
            ThinkingStepType.ANALYSIS: ["分析", "检查", "查看", "观察"],
            ThinkingStepType.RETRIEVAL: ["检索", "获取", "查找", "搜索"],
            ThinkingStepType.COMPARISON: ["对比", "比较", "差异", "一致"],
            ThinkingStepType.DECISION: ["决定", "判断", "确定", "选择"],
            ThinkingStepType.VERIFICATION: ["验证", "确认", "核实", "检验"],
        }

        for line in lines:
            # 检测步骤类型
            step_type = ThinkingStepType.ANALYSIS  # 默认
            for stype, keywords in type_keywords.items():
                if any(kw in line for kw in keywords):
                    step_type = stype
                    break

            # 提取引号中的证据
            evidence = []
            import re
            quotes = re.findall(r'["\u201c\u201d]([^"\u201c\u201d]+)["\u201c\u201d]', line)
            evidence.extend(quotes)

            # 检测关联维度
            related_dim = detect_dimension_from_text(line)

            # 估算置信度
            confidence = 0.5
            high_conf_words = ["确定", "明确", "显然", "必须"]
            low_conf_words = ["可能", "也许", "或许", "似乎"]
            if any(w in line for w in high_conf_words):
                confidence = 0.8
            elif any(w in line for w in low_conf_words):
                confidence = 0.3

            steps.append(ThinkingStep(
                step_type=step_type,
                content=line,
                evidence=evidence,
                confidence=confidence,
                related_dimension=related_dim,
            ))

        # 生成摘要
        summary = lines[-1] if lines else ""

        return cls(
            raw_content=raw_text,
            steps=steps,
            summary=summary,
        )


# ==================== 请求/响应模型 ====================

class OptimizePromptRequest(BaseModel):
    """优化 Prompt 请求"""
    feature_id: str                                     # 功能 ID
    dimensions: List[str] = Field(default_factory=lambda: DEFAULT_DIMENSIONS.copy())
    mode: OptimizationMode = OptimizationMode.AUTO


class OptimizationSessionInfo(BaseModel):
    """优化会话信息"""
    session_id: str
    project_id: str
    feature_id: str
    status: str                         # running, paused, completed, cancelled
    mode: OptimizationMode
    dimensions: List[str]
    suggestions_count: int = 0
    current_dimension: Optional[str] = None
    created_at: str
    updated_at: str
