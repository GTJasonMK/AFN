"""
目录规划Agent工具定义

定义Agent可以使用的所有工具，包括：
- 信息获取工具：获取项目、系统、模块信息
- 分析工具：分析依赖关系、评估放置合理性
- 操作工具：创建目录、创建文件、设置依赖
- 控制工具：获取当前结构、验证、完成规划
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import re
import json


class ToolCategory(str, Enum):
    """工具分类"""
    INFO = "info"           # 信息获取
    ANALYSIS = "analysis"   # 分析工具
    ACTION = "action"       # 操作工具
    CONTROL = "control"     # 控制工具


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory
    parameters: Dict[str, Dict[str, Any]]  # {param_name: {type, description, required}}
    returns: str
    example: Optional[str] = None


# ==================== 工具定义 ====================

TOOLS: List[ToolDefinition] = [
    # ==================== 信息获取工具 ====================
    ToolDefinition(
        name="get_project_overview",
        description="获取项目概览信息，包括项目标题、描述、技术栈、架构概要等基础信息",
        category=ToolCategory.INFO,
        parameters={},
        returns="项目概览JSON，包含: project_id, title, initial_prompt, one_sentence_summary, architecture_synopsis, tech_style, primary_language, frameworks, total_systems, total_modules",
        example='{"tool": "get_project_overview", "parameters": {}, "reasoning": "需要了解项目的整体情况"}'
    ),
    ToolDefinition(
        name="get_blueprint_details",
        description="获取项目蓝图详情，包括核心需求、技术挑战、非功能性需求、风险点等",
        category=ToolCategory.INFO,
        parameters={},
        returns="蓝图详情JSON，包含: core_requirements, technical_challenges, non_functional_requirements, risks, milestones, dependencies, system_suggestions",
        example='{"tool": "get_blueprint_details", "parameters": {}, "reasoning": "需要了解项目的详细设计要求"}'
    ),
    ToolDefinition(
        name="get_all_systems",
        description="获取项目的所有系统（子系统）列表，包括系统名称、描述、职责",
        category=ToolCategory.INFO,
        parameters={},
        returns="系统列表，每个系统包含system_number, name, description, responsibilities",
        example='{"tool": "get_all_systems", "parameters": {}, "reasoning": "需要了解项目的系统划分"}'
    ),
    ToolDefinition(
        name="get_system_modules",
        description="获取指定系统下的所有模块",
        category=ToolCategory.INFO,
        parameters={
            "system_number": {"type": "int", "description": "系统编号", "required": True}
        },
        returns="模块列表，每个模块包含: module_number, name, module_type, description, dependencies",
        example='{"tool": "get_system_modules", "parameters": {"system_number": 1}, "reasoning": "需要了解用户认证系统包含哪些模块"}'
    ),
    ToolDefinition(
        name="get_module_detail",
        description="获取指定模块的详细信息，包括描述、类型、接口定义、依赖列表",
        category=ToolCategory.INFO,
        parameters={
            "module_number": {"type": "int", "description": "模块编号", "required": True}
        },
        returns="模块详情JSON，包含: module_number, system_number, system_name, name, module_type, description, interface, dependencies",
        example='{"tool": "get_module_detail", "parameters": {"module_number": 5}, "reasoning": "需要详细了解这个模块的功能和接口"}'
    ),
    ToolDefinition(
        name="get_modules_by_type",
        description="按模块类型获取所有模块（如service、repository、controller等）",
        category=ToolCategory.INFO,
        parameters={
            "module_type": {"type": "str", "description": "模块类型", "required": True}
        },
        returns="模块列表，每个模块包含: module_number, name, system_number, description",
        example='{"tool": "get_modules_by_type", "parameters": {"module_type": "service"}, "reasoning": "需要了解所有服务层模块"}'
    ),
    ToolDefinition(
        name="get_dependency_graph",
        description="获取模块间的依赖关系图，包括谁依赖谁、被谁依赖、循环依赖检测",
        category=ToolCategory.INFO,
        parameters={},
        returns="依赖关系图，包含edges（边）、high_dependency_modules（高依赖模块）、cycles（循环依赖）",
        example='{"tool": "get_dependency_graph", "parameters": {}, "reasoning": "需要分析模块间的依赖关系来决定目录结构"}'
    ),

    # ==================== 分析工具 ====================
    ToolDefinition(
        name="analyze_module_placement",
        description="分析某个模块应该放在哪个目录位置，考虑其类型、依赖、所属系统等因素",
        category=ToolCategory.ANALYSIS,
        parameters={
            "module_number": {"type": "int", "description": "模块编号", "required": True},
            "candidate_paths": {"type": "list[str]", "description": "候选路径列表", "required": False}
        },
        returns="放置建议，包含推荐路径和理由",
        example='{"tool": "analyze_module_placement", "parameters": {"module_number": 3, "candidate_paths": ["src/services", "src/domain"]}, "reasoning": "需要确定用户服务模块的最佳位置"}'
    ),
    ToolDefinition(
        name="analyze_shared_candidates",
        description="分析哪些模块适合作为共享模块（被多个模块依赖、工具类性质等）",
        category=ToolCategory.ANALYSIS,
        parameters={},
        returns="共享模块候选列表及理由",
        example='{"tool": "analyze_shared_candidates", "parameters": {}, "reasoning": "需要识别可以抽取为共享模块的组件"}'
    ),
    ToolDefinition(
        name="evaluate_structure",
        description="评估当前已规划的目录结构质量，包括模块覆盖率、文件信息完整度、质量评分等指标。返回是否可以完成规划以及阻塞原因",
        category=ToolCategory.ANALYSIS,
        parameters={},
        returns="结构质量评估报告，包含module_coverage、quality_assessment、can_finish、blocking_reasons等",
        example='{"tool": "evaluate_structure", "parameters": {}, "reasoning": "需要检查当前规划的质量和完整度"}'
    ),
    ToolDefinition(
        name="check_file_quality",
        description="检查单个文件的信息质量，返回该文件是否达标以及具体的质量问题",
        category=ToolCategory.ANALYSIS,
        parameters={
            "path": {"type": "str", "description": "文件路径", "required": True}
        },
        returns="文件质量报告，包含is_quality_ok、issues列表、current_values和requirements",
        example='{"tool": "check_file_quality", "parameters": {"path": "src/services/auth/service.py"}, "reasoning": "检查这个文件的信息是否足够详细"}'
    ),
    ToolDefinition(
        name="request_llm_evaluation",
        description="使用LLM对指定文件进行语义级评估，返回多维度评分和改进建议",
        category=ToolCategory.ANALYSIS,
        parameters={
            "path": {"type": "str", "description": "文件路径", "required": True}
        },
        returns="评估结果，包含is_acceptable、overall_score、scores（各维度得分）、issues、suggestions",
        example='{"tool": "request_llm_evaluation", "parameters": {"path": "src/services/auth/service.py"}, "reasoning": "需要对这个关键文件进行深度评估"}'
    ),

    # ==================== 操作工具 ====================
    ToolDefinition(
        name="create_directory",
        description="创建一个目录节点",
        category=ToolCategory.ACTION,
        parameters={
            "path": {"type": "str", "description": "目录路径（如src/services/user）", "required": True},
            "description": {"type": "str", "description": "目录描述", "required": True},
            "purpose": {"type": "str", "description": "目录存在的理由", "required": False}
        },
        returns="创建结果JSON，包含: created(bool), path, description",
        example='{"tool": "create_directory", "parameters": {"path": "src/services/auth", "description": "用户认证服务目录", "purpose": "集中管理所有认证相关的业务逻辑"}, "reasoning": "需要为认证模块创建专门的目录"}'
    ),
    ToolDefinition(
        name="create_file",
        description="创建一个源文件节点，需要详细说明文件的功能、依赖和存在理由",
        category=ToolCategory.ACTION,
        parameters={
            "path": {"type": "str", "description": "文件完整路径（如src/services/user/service.py）", "required": True},
            "description": {"type": "str", "description": "文件功能描述（详细说明这个文件要实现什么）", "required": True},
            "purpose": {"type": "str", "description": "文件存在理由（为什么需要这个文件）", "required": True},
            "module_number": {"type": "int", "description": "关联的模块编号", "required": True},
            "dependencies": {"type": "list[int]", "description": "依赖的其他模块编号列表", "required": False},
            "dependency_reasons": {"type": "str", "description": "为什么需要这些依赖", "required": False},
            "file_type": {"type": "str", "description": "文件类型（source/test/config/interface）", "required": False},
            "priority": {"type": "str", "description": "实现优先级（high/medium/low）", "required": False},
            "implementation_notes": {"type": "str", "description": "实现建议和注意事项", "required": False}
        },
        returns="创建结果JSON，包含: created(bool), path, module_number, quality_ok(bool), quality_warnings(如有问题)",
        example='{"tool": "create_file", "parameters": {"path": "src/services/auth/service.py", "description": "实现用户登录、注册、Token刷新等认证核心逻辑", "purpose": "封装认证业务逻辑，为Controller提供统一的认证接口", "module_number": 1, "dependencies": [5, 8], "dependency_reasons": "依赖用户仓储(5)进行数据访问，依赖加密服务(8)进行密码处理", "file_type": "source", "priority": "high", "implementation_notes": "使用JWT进行Token管理，密码使用bcrypt加密"}, "reasoning": "认证服务是核心模块，需要详细定义其实现方式"}'
    ),
    ToolDefinition(
        name="update_file",
        description="更新已创建文件的信息",
        category=ToolCategory.ACTION,
        parameters={
            "path": {"type": "str", "description": "文件路径", "required": True},
            "description": {"type": "str", "description": "新的描述", "required": False},
            "purpose": {"type": "str", "description": "新的存在理由", "required": False},
            "dependencies": {"type": "list[int]", "description": "新的依赖列表", "required": False},
            "dependency_reasons": {"type": "str", "description": "新的依赖理由", "required": False},
            "implementation_notes": {"type": "str", "description": "新的实现建议", "required": False}
        },
        returns="更新结果JSON，包含: updated(bool), path, updated_fields, quality_ok(bool), remaining_issues(如有)",
        example='{"tool": "update_file", "parameters": {"path": "src/services/auth/service.py", "dependencies": [5, 8, 12], "dependency_reasons": "新增依赖日志服务(12)用于审计登录行为"}, "reasoning": "发现需要补充依赖"}'
    ),
    ToolDefinition(
        name="remove_item",
        description="移除已创建的目录或文件（用于修正错误）",
        category=ToolCategory.ACTION,
        parameters={
            "path": {"type": "str", "description": "要移除的路径", "required": True},
            "reason": {"type": "str", "description": "移除理由", "required": True}
        },
        returns="移除结果JSON，包含: removed(bool), path, reason",
        example='{"tool": "remove_item", "parameters": {"path": "src/services/legacy", "reason": "发现这个目录设计不合理，需要重新规划"}, "reasoning": "之前的设计有问题，需要修正"}'
    ),

    # ==================== 控制工具 ====================
    ToolDefinition(
        name="get_current_structure",
        description="获取当前已规划的目录结构",
        category=ToolCategory.CONTROL,
        parameters={},
        returns="当前结构JSON，包含: directories列表, files列表(含path/module_number/description/quality_ok), total_directories, total_files, covered_modules",
        example='{"tool": "get_current_structure", "parameters": {}, "reasoning": "需要查看当前进度"}'
    ),
    ToolDefinition(
        name="get_uncovered_modules",
        description="获取尚未被覆盖的模块列表",
        category=ToolCategory.CONTROL,
        parameters={},
        returns="未覆盖模块列表，每个包含: module_number, name, module_type, system_number",
        example='{"tool": "get_uncovered_modules", "parameters": {}, "reasoning": "需要检查还有哪些模块没有安排"}'
    ),
    ToolDefinition(
        name="get_optimization_history",
        description="获取优化历程摘要，包括操作统计和最近的操作记录",
        category=ToolCategory.CONTROL,
        parameters={},
        returns="优化历程摘要，包含total_steps、action_counts、recent_actions",
        example='{"tool": "get_optimization_history", "parameters": {}, "reasoning": "需要回顾优化历程，判断是否可以完成"}'
    ),
    ToolDefinition(
        name="finish_planning",
        description="完成目录规划，进行最终验证并保存结果",
        category=ToolCategory.CONTROL,
        parameters={
            "summary": {"type": "str", "description": "规划总结说明", "required": True}
        },
        returns="完成结果JSON，包含: finished(bool), summary, llm_reasoning, final_evaluation, optimization_history; 如未通过则包含blocked, blocking_reasons",
        example='{"tool": "finish_planning", "parameters": {"summary": "采用分层架构，共创建5个顶层目录、23个模块目录、67个源文件。所有模块已覆盖，依赖关系清晰。"}, "reasoning": "所有模块都已规划完成，准备提交结果"}'
    ),
]


# ==================== 工具名到定义的映射 ====================
TOOLS_BY_NAME: Dict[str, ToolDefinition] = {tool.name: tool for tool in TOOLS}


def get_tool(name: str) -> Optional[ToolDefinition]:
    """获取工具定义"""
    return TOOLS_BY_NAME.get(name)


def get_tools_by_category(category: ToolCategory) -> List[ToolDefinition]:
    """按分类获取工具"""
    return [tool for tool in TOOLS if tool.category == category]


def get_tools_prompt() -> str:
    """
    生成工具列表的提示词文本

    Returns:
        格式化的工具列表描述
    """
    lines = ["## 可用工具\n"]

    for category in ToolCategory:
        category_tools = get_tools_by_category(category)
        if not category_tools:
            continue

        category_names = {
            ToolCategory.INFO: "信息获取工具",
            ToolCategory.ANALYSIS: "分析工具",
            ToolCategory.ACTION: "操作工具",
            ToolCategory.CONTROL: "控制工具",
        }
        lines.append(f"\n### {category_names[category]}\n")

        for tool in category_tools:
            lines.append(f"**{tool.name}**")
            lines.append(f"- 描述: {tool.description}")

            if tool.parameters:
                # 详细列出每个参数
                lines.append("- 参数:")
                for name, info in tool.parameters.items():
                    required_mark = "(必需)" if info.get("required") else "(可选)"
                    lines.append(f"  - `{name}`: {info['type']} {required_mark} - {info.get('description', '')}")
            else:
                lines.append("- 参数: 无")

            lines.append(f"- 返回: {tool.returns}")

            # 添加调用示例
            if tool.example:
                lines.append(f"- 示例: `{tool.example}`")

            lines.append("")

    return "\n".join(lines)


# ==================== 工具调用解析 ====================

@dataclass
class ToolCall:
    """工具调用"""
    tool: str
    parameters: Dict[str, Any]
    reasoning: str = ""


@dataclass
class ToolCallParseResult:
    """单个工具调用解析结果"""
    success: bool
    tool_call: Optional[ToolCall] = None
    error: Optional[str] = None
    raw_text: str = ""


@dataclass
class BatchToolCallParseResult:
    """批量工具调用解析结果"""
    success: bool
    tool_calls: List[ToolCall] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    raw_text: str = ""


def parse_tool_call(text: str) -> ToolCallParseResult:
    """
    从Agent响应中解析工具调用

    Args:
        text: Agent响应文本

    Returns:
        ToolCallParseResult: 解析结果
    """
    # 查找 <tool_call>...</tool_call> 标签
    pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return ToolCallParseResult(
            success=False,
            error="未找到<tool_call>标签",
            raw_text=text
        )

    json_str = match.group(1).strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return ToolCallParseResult(
            success=False,
            error=f"JSON解析失败: {e}",
            raw_text=json_str
        )

    # 验证必需字段
    tool_name = data.get("tool")
    if not tool_name:
        return ToolCallParseResult(
            success=False,
            error="缺少tool字段",
            raw_text=json_str
        )

    # 验证工具是否存在
    if tool_name not in TOOLS_BY_NAME:
        return ToolCallParseResult(
            success=False,
            error=f"未知工具: {tool_name}",
            raw_text=json_str
        )

    tool_call = ToolCall(
        tool=tool_name,
        parameters=data.get("parameters", {}),
        reasoning=data.get("reasoning", "")
    )

    return ToolCallParseResult(
        success=True,
        tool_call=tool_call,
        raw_text=json_str
    )


def parse_tool_calls(text: str) -> BatchToolCallParseResult:
    """
    从Agent响应中解析多个工具调用

    支持两种格式：
    1. 单个: <tool_call>...</tool_call>
    2. 批量: <tool_calls><tool_call>...</tool_call><tool_call>...</tool_call></tool_calls>

    Args:
        text: Agent响应文本

    Returns:
        BatchToolCallParseResult: 批量解析结果
    """
    tool_calls = []
    errors = []

    # 先尝试解析批量格式 <tool_calls>...</tool_calls>
    batch_pattern = r'<tool_calls>\s*(.*?)\s*</tool_calls>'
    batch_match = re.search(batch_pattern, text, re.DOTALL)

    if batch_match:
        # 批量格式：从中提取所有 <tool_call>
        inner_text = batch_match.group(1)
        single_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(single_pattern, inner_text, re.DOTALL)
    else:
        # 单个格式：直接查找所有 <tool_call>
        single_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.findall(single_pattern, text, re.DOTALL)

    if not matches:
        return BatchToolCallParseResult(
            success=False,
            errors=["未找到任何<tool_call>标签"],
            raw_text=text
        )

    # 解析每个工具调用
    for json_str in matches:
        json_str = json_str.strip()
        try:
            data = json.loads(json_str)
            tool_name = data.get("tool")

            if not tool_name:
                errors.append(f"缺少tool字段: {json_str[:50]}...")
                continue

            if tool_name not in TOOLS_BY_NAME:
                errors.append(f"未知工具: {tool_name}")
                continue

            tool_calls.append(ToolCall(
                tool=tool_name,
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", "")
            ))
        except json.JSONDecodeError as e:
            errors.append(f"JSON解析失败: {e}")

    return BatchToolCallParseResult(
        success=len(tool_calls) > 0,
        tool_calls=tool_calls,
        errors=errors,
        raw_text=text
    )


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None

    def to_message(self) -> str:
        """
        转换为Agent可读的消息格式

        注意：不在此处做压缩，压缩策略应基于实际数据分析后在tool_executor中针对性处理
        """
        import logging
        logger = logging.getLogger(__name__)

        if self.success:
            if isinstance(self.result, dict):
                result_str = json.dumps(self.result, ensure_ascii=False, indent=2)
            elif isinstance(self.result, list):
                result_str = json.dumps(self.result, ensure_ascii=False, indent=2)
            else:
                result_str = str(self.result)

            # 记录实际消息大小，用于分析
            logger.debug(
                "[消息大小分析] tool=%s, result_length=%d",
                self.tool_name, len(result_str)
            )

            return f"[工具执行成功: {self.tool_name}]\n{result_str}"
        else:
            return f"[工具执行失败: {self.tool_name}]\n错误: {self.error}"
