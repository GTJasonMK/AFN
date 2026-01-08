"""
Coding项目Schema定义

独立的代码项目Pydantic模型，与小说项目Schema完全分离。
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 基础枚举 ====================

class CodingSystemStatus(str, Enum):
    """系统/模块生成状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class CodingFeatureStatus(str, Enum):
    """功能生成状态"""
    NOT_GENERATED = "not_generated"
    GENERATING = "generating"
    EVALUATING = "evaluating"
    SELECTING = "selecting"
    FAILED = "failed"
    SUCCESSFUL = "successful"


# ==================== 技术栈相关 ====================

class TechComponent(BaseModel):
    """技术组件"""
    name: str = Field(..., description="组件名称，如：数据库层/缓存层/消息队列")
    description: str = Field(default="", description="技术选型和配置说明")


class TechDomain(BaseModel):
    """技术领域"""
    name: str = Field(..., description="领域名称：前端/后端/DevOps")
    description: str = Field(default="", description="该领域的技术栈和工具链")


class TechStack(BaseModel):
    """技术栈配置"""
    core_constraints: str = Field(default="", description="核心技术约束和规范")
    components: List[TechComponent] = Field(default_factory=list, description="技术组件列表")
    domains: List[TechDomain] = Field(default_factory=list, description="技术领域列表")


# ==================== 架构设计辅助信息 ====================

class SystemSuggestion(BaseModel):
    """系统划分建议"""
    name: str = Field(..., description="建议的系统名称")
    description: str = Field(default="", description="系统职责概述")
    priority: str = Field(default="medium", description="优先级：core/high/medium/low")
    estimated_modules: int = Field(default=0, description="预估该系统包含的模块数")


class CoreRequirement(BaseModel):
    """核心需求"""
    category: str = Field(default="功能", description="需求类别：功能/数据/集成/用户体验")
    requirement: str = Field(..., description="需求描述")
    priority: str = Field(default="should-have", description="优先级：must-have/should-have/nice-to-have")


class TechnicalChallenge(BaseModel):
    """技术挑战"""
    challenge: str = Field(..., description="技术挑战描述")
    impact: str = Field(default="medium", description="影响范围：high/medium/low")
    solution_direction: str = Field(default="", description="解决思路")


class NonFunctionalRequirements(BaseModel):
    """非功能需求"""
    performance: str = Field(default="", description="性能要求")
    security: str = Field(default="", description="安全要求")
    scalability: str = Field(default="", description="可扩展性要求")
    reliability: str = Field(default="", description="可靠性要求")
    maintainability: str = Field(default="", description="可维护性要求")


class Risk(BaseModel):
    """风险项"""
    risk: str = Field(..., description="风险描述")
    probability: str = Field(default="medium", description="发生概率：high/medium/low")
    mitigation: str = Field(default="", description="应对策略")


class Milestone(BaseModel):
    """里程碑"""
    phase: str = Field(..., description="阶段名称：MVP/Alpha/Beta/Release")
    goals: List[str] = Field(default_factory=list, description="该阶段目标列表")
    key_deliverables: List[str] = Field(default_factory=list, description="关键交付物")


class ModuleDependency(BaseModel):
    """模块依赖关系"""
    from_module: str = Field(..., description="源模块名称")
    to_module: str = Field(..., description="目标模块名称")
    description: str = Field(default="", description="依赖关系描述：调用/数据传递/事件触发等")


# ==================== 三层结构 ====================

class CodingSystem(BaseModel):
    """编程项目系统 - 顶层划分"""
    system_number: int = Field(default=0, description="系统编号（从1开始，0表示未分配）")
    name: str = Field(..., description="系统名称")
    description: str = Field(default="", description="系统描述")
    responsibilities: List[str] = Field(default_factory=list, description="主要职责列表")
    tech_requirements: str = Field(default="", description="技术要求和约束")
    module_count: int = Field(default=0, description="该系统下的模块数量")
    feature_count: int = Field(default=0, description="该系统下的功能数量")
    generation_status: CodingSystemStatus = Field(default=CodingSystemStatus.PENDING, description="模块生成状态")
    progress: int = Field(default=0, description="生成进度 0-100")


class CodingModule(BaseModel):
    """编程项目模块 - 中层组织"""
    module_number: int = Field(default=0, description="全局模块编号（从1开始，0表示未分配）")
    system_number: int = Field(default=0, description="所属系统编号（0表示未分配）")
    name: str = Field(..., description="模块名称")
    type: str = Field(default="", description="模块类型：service/repository/controller/utility/middleware")
    description: str = Field(default="", description="模块职责描述")
    interface: str = Field(default="", description="接口规范和数据格式")
    dependencies: List[str] = Field(default_factory=list, description="依赖的其他模块名称列表")
    feature_count: int = Field(default=0, description="该模块下的功能数量")
    generation_status: CodingSystemStatus = Field(default=CodingSystemStatus.PENDING, description="功能生成状态")


class CodingFeature(BaseModel):
    """编程项目功能大纲 - 最终产物的大纲"""
    feature_number: int = Field(default=0, description="全局功能编号（从1开始，0表示未分配）")
    module_number: int = Field(default=0, description="所属模块编号（0表示未分配）")
    system_number: int = Field(default=0, description="所属系统编号（0表示未分配）")
    name: str = Field(..., description="功能名称")
    description: str = Field(default="", description="功能描述")
    inputs: str = Field(default="", description="输入参数说明")
    outputs: str = Field(default="", description="输出结果说明")
    implementation_notes: str = Field(default="", description="实现要点和注意事项")
    priority: str = Field(default="medium", description="优先级：high/medium/low")


# ==================== 蓝图 ====================

class CodingBlueprint(BaseModel):
    """编程项目架构设计蓝图"""
    title: str = Field(..., description="项目名称")
    target_audience: str = Field(default="", description="目标用户群体描述")
    project_type_desc: str = Field(default="", description="项目类型：Web应用/CLI工具/API服务/桌面应用/移动应用等")
    tech_style: str = Field(default="", description="技术风格：前后端分离/单体架构/微服务/Serverless等")
    project_tone: str = Field(default="", description="项目调性：企业级/轻量级/原型验证/生产就绪等")
    one_sentence_summary: str = Field(default="", description="一句话描述项目核心功能")
    architecture_synopsis: str = Field(default="", description="完整的架构设计描述")
    tech_stack: TechStack = Field(default_factory=TechStack, description="技术栈配置")

    # 架构设计辅助信息
    system_suggestions: List[SystemSuggestion] = Field(default_factory=list, description="系统划分建议")
    core_requirements: List[CoreRequirement] = Field(default_factory=list, description="核心需求列表")
    technical_challenges: List[TechnicalChallenge] = Field(default_factory=list, description="技术挑战")
    non_functional_requirements: Optional[NonFunctionalRequirements] = Field(default=None, description="非功能需求")
    risks: List[Risk] = Field(default_factory=list, description="风险列表")
    milestones: List[Milestone] = Field(default_factory=list, description="里程碑")

    # 三层结构数据
    systems: List[CodingSystem] = Field(default_factory=list, description="系统列表")
    modules: List[CodingModule] = Field(default_factory=list, description="模块列表")
    features: List[CodingFeature] = Field(default_factory=list, description="功能大纲列表")

    # 模块间依赖关系
    dependencies: List[ModuleDependency] = Field(default_factory=list, description="模块依赖关系")

    # 统计信息
    total_systems: int = Field(default=0, description="系统总数（预估）")
    total_modules: int = Field(default=0, description="模块总数（预估）")
    total_features: int = Field(default=0, description="功能总数")

    # 分阶段设计标志
    needs_phased_design: bool = Field(default=False, description="是否需要分阶段设计")


# ==================== 对话相关 ====================

class CodingChoiceOption(BaseModel):
    """对话选择项"""
    id: str
    label: str
    description: Optional[str] = None
    key_elements: Optional[List[str]] = None


class CodingUIControl(BaseModel):
    """对话UI控件"""
    type: str = Field(..., description="控件类型")
    options: Optional[List[CodingChoiceOption]] = None
    placeholder: Optional[str] = None


class CodingConverseResponse(BaseModel):
    """需求分析对话接口的统一返回体"""
    ai_message: str
    ui_control: CodingUIControl
    conversation_state: Dict[str, Any]
    is_complete: bool = False
    ready_for_blueprint: Optional[bool] = None


class CodingConverseRequest(BaseModel):
    """需求分析对话接口的请求体"""
    user_input: Dict[str, Any]
    conversation_state: Dict[str, Any]


# ==================== 项目相关 ====================

class CodingProjectCreate(BaseModel):
    """创建代码项目请求"""
    title: str = Field(..., description="项目名称", min_length=1, max_length=255)
    initial_prompt: Optional[str] = Field(default=None, description="初始需求描述")


class CodingProjectUpdate(BaseModel):
    """更新代码项目请求"""
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None


class CodingProjectResponse(BaseModel):
    """代码项目响应"""
    id: str
    user_id: int
    title: str
    initial_prompt: Optional[str] = None
    status: str
    conversation_history: List[Dict[str, Any]] = []
    blueprint: Optional[CodingBlueprint] = None
    features: List[CodingFeature] = []
    warnings: Optional[List[str]] = None

    class Config:
        from_attributes = True


class CodingProjectSummary(BaseModel):
    """代码项目摘要（用于列表展示）"""
    id: str
    title: str
    project_type_desc: str = ""
    last_edited: str
    completed_features: int = 0
    total_features: int = 0
    status: str


# ==================== 蓝图相关 ====================

class CodingBlueprintGenerationResponse(BaseModel):
    """架构设计生成响应"""
    blueprint: CodingBlueprint
    ai_message: str


class CodingBlueprintRefineRequest(BaseModel):
    """蓝图优化请求"""
    refinement_instruction: str = Field(
        ...,
        description="用户的优化指令",
        min_length=1,
        max_length=2000
    )


class CodingBlueprintPatch(BaseModel):
    """蓝图部分更新"""
    title: Optional[str] = None
    one_sentence_summary: Optional[str] = None
    architecture_synopsis: Optional[str] = None
    tech_stack: Optional[TechStack] = None
    systems: Optional[List[CodingSystem]] = None
    modules: Optional[List[CodingModule]] = None
    features: Optional[List[CodingFeature]] = None


# ==================== 功能生成相关 ====================

class GenerateCodingFeatureRequest(BaseModel):
    """生成功能实现请求"""
    feature_number: int
    writing_notes: Optional[str] = Field(default=None, description="额外的实现指令")


class CodingFeatureGenerationResponse(BaseModel):
    """功能生成响应"""
    ai_message: str
    feature_versions: List[Dict[str, Any]]


class SelectCodingVersionRequest(BaseModel):
    """选择功能版本请求"""
    feature_number: int
    version_index: int


class RetryCodingVersionRequest(BaseModel):
    """重新生成功能版本请求"""
    feature_number: int
    version_index: int
    custom_prompt: Optional[str] = Field(default=None, description="用户自定义的优化提示词")


# ==================== 系统/模块生成相关 ====================

class GenerateCodingSystemsRequest(BaseModel):
    """生成系统列表请求"""
    count: Optional[int] = Field(default=None, description="要生成的系统数量")


class GenerateCodingModulesRequest(BaseModel):
    """生成模块列表请求"""
    system_number: int = Field(..., description="目标系统编号")
    count: Optional[int] = Field(default=None, description="要生成的模块数量")


class GenerateCodingFeaturesRequest(BaseModel):
    """生成功能列表请求"""
    module_number: int = Field(..., description="目标模块编号")
    count: Optional[int] = Field(default=None, description="要生成的功能数量")
