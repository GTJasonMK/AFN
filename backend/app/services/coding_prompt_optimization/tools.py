"""
编程项目 Prompt 优化 - 工具定义

定义 Agent 可调用的工具集，包括信息获取、检查工具、输出工具和控制工具。
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolName(str, Enum):
    """工具名称枚举"""
    # 信息获取工具（3个）
    RAG_RETRIEVE = "rag_retrieve"               # RAG 检索
    GET_FEATURE_CONTEXT = "get_feature_context"  # 获取功能上下文
    GET_DEPENDENCIES = "get_dependencies"        # 获取依赖关系

    # 检查工具（4个）
    CHECK_COMPLETENESS = "check_completeness"    # 检查需求覆盖
    CHECK_INTERFACE = "check_interface"          # 检查接口定义
    CHECK_DEPENDENCY = "check_dependency"        # 检查依赖合理性
    DEEP_CHECK = "deep_check"                    # LLM 深度检查

    # 输出工具（2个）
    GENERATE_SUGGESTION = "generate_suggestion"  # 生成建议
    RECORD_OBSERVATION = "record_observation"    # 记录观察

    # 控制工具（1个）
    COMPLETE_WORKFLOW = "complete_workflow"      # 完成工作流


@dataclass
class ToolDefinition:
    """工具定义"""
    name: ToolName
    description: str
    parameters: Dict[str, str]          # 参数名 -> 参数说明
    required_params: List[str]          # 必需参数
    returns: str                        # 返回值说明


# 工具定义字典
TOOL_DEFINITIONS: Dict[ToolName, ToolDefinition] = {
    # ==================== 信息获取工具 ====================
    ToolName.RAG_RETRIEVE: ToolDefinition(
        name=ToolName.RAG_RETRIEVE,
        description="""使用向量检索获取与查询相关的项目信息。
可检索的内容类型包括：
- architecture: 架构设计
- tech_stack: 技术栈
- requirement: 核心需求
- system: 系统划分
- module: 模块定义
- feature_outline: 功能大纲
- feature_prompt: 其他功能的 Prompt
- dependency: 依赖关系

适合用于：
- 查找与当前功能相关的架构设计
- 获取技术栈约束
- 检查需求是否已覆盖
- 参考类似功能的 Prompt""",
        parameters={
            "query": "检索查询文本，描述你想要查找的内容",
            "data_types": "可选，限制检索的数据类型列表，如 ['architecture', 'requirement']",
            "top_k": "返回结果数量，默认 5",
        },
        required_params=["query"],
        returns="相关内容片段列表，包含数据类型、内容、相似度分数",
    ),

    ToolName.GET_FEATURE_CONTEXT: ToolDefinition(
        name=ToolName.GET_FEATURE_CONTEXT,
        description="""获取当前功能的完整上下文信息。
返回内容包括：
- 功能基本信息（名称、描述、输入输出）
- 所属系统和模块信息
- 当前 Prompt 内容
- 相关的技术栈约束

适合在分析开始时调用，获取完整背景。""",
        parameters={},
        required_params=[],
        returns="功能上下文对象，包含功能信息、层级归属、技术约束等",
    ),

    ToolName.GET_DEPENDENCIES: ToolDefinition(
        name=ToolName.GET_DEPENDENCIES,
        description="""获取与当前功能相关的依赖关系。
返回内容包括：
- 当前功能依赖的其他模块/功能
- 依赖当前功能的其他模块/功能
- 依赖关系的描述和类型

适合用于检查 Prompt 中的依赖引用是否正确。""",
        parameters={
            "include_reverse": "是否包含反向依赖（被谁依赖），默认 True",
        },
        required_params=[],
        returns="依赖关系列表，包含依赖方向、模块名、描述",
    ),

    # ==================== 检查工具 ====================
    ToolName.CHECK_COMPLETENESS: ToolDefinition(
        name=ToolName.CHECK_COMPLETENESS,
        description="""检查 Prompt 是否完整覆盖功能需求。
检查项包括：
- 功能描述中的所有要点是否都有对应实现步骤
- 输入参数是否都有处理逻辑
- 输出结果是否都有生成方式
- 是否遗漏了隐含需求

这是快速规则检查，不调用 LLM。""",
        parameters={},
        required_params=[],
        returns="检查结果，包含是否通过、问题列表",
    ),

    ToolName.CHECK_INTERFACE: ToolDefinition(
        name=ToolName.CHECK_INTERFACE,
        description="""检查 Prompt 中的接口定义是否清晰。
检查项包括：
- 是否明确定义了函数/方法签名
- 参数类型和含义是否清晰
- 返回值类型和结构是否明确
- 是否有必要的类型注解建议

这是快速规则检查，不调用 LLM。""",
        parameters={},
        required_params=[],
        returns="检查结果，包含是否通过、问题列表",
    ),

    ToolName.CHECK_DEPENDENCY: ToolDefinition(
        name=ToolName.CHECK_DEPENDENCY,
        description="""检查 Prompt 中的依赖引用是否正确。
检查项包括：
- 引用的模块/功能是否存在
- 依赖关系是否与架构设计一致
- 是否存在循环依赖风险
- 是否有未声明的隐式依赖

这是快速规则检查，不调用 LLM。""",
        parameters={},
        required_params=[],
        returns="检查结果，包含是否通过、问题列表",
    ),

    ToolName.DEEP_CHECK: ToolDefinition(
        name=ToolName.DEEP_CHECK,
        description="""使用 LLM 对 Prompt 进行深度质量检查。
这是成本较高的检查，仅在快速检查发现问题或需要深入分析时使用。

检查维度可选：
- completeness: 功能完整性
- interface: 接口定义清晰度
- dependency: 依赖关系正确性
- implementation: 实现步骤合理性
- error_handling: 错误处理完备性
- security: 安全性考虑
- performance: 性能考虑

返回详细的分析报告和具体建议。""",
        parameters={
            "dimensions": "要检查的维度列表，如 ['completeness', 'interface']",
            "focus_area": "可选，重点关注的内容区域（如某个函数或某段描述）",
        },
        required_params=["dimensions"],
        returns="深度检查报告，包含各维度的问题和建议",
    ),

    # ==================== 输出工具 ====================
    ToolName.GENERATE_SUGGESTION: ToolDefinition(
        name=ToolName.GENERATE_SUGGESTION,
        description="""生成一条优化建议。
当你发现 Prompt 存在问题并确定了修改方案时，使用此工具记录建议。

必须提供：
- 关联维度（哪个检查维度发现的问题）
- 问题描述（问题是什么）
- 原始文本（有问题的部分，如果能定位）
- 建议文本（建议如何修改）
- 推理过程（为什么这样修改）
- 严重程度（high/medium/low）""",
        parameters={
            "dimension": "关联维度，如 'completeness'",
            "severity": "严重程度: high（必须修改）/ medium（建议修改）/ low（可选优化）",
            "description": "问题描述",
            "original_text": "原始文本（有问题的部分）",
            "suggested_text": "建议的修改文本",
            "reasoning": "推理过程，解释为什么需要修改",
        },
        required_params=["dimension", "severity", "description", "reasoning"],
        returns="建议 ID",
    ),

    ToolName.RECORD_OBSERVATION: ToolDefinition(
        name=ToolName.RECORD_OBSERVATION,
        description="""记录一条观察，不一定是问题。
当你发现一些值得注意但不需要修改的内容时使用此工具。

适合用于：
- 记录 Prompt 的优点
- 记录可能需要关注但当前没有问题的内容
- 记录分析过程中的发现""",
        parameters={
            "observation": "观察内容",
            "related_dimension": "可选，关联的维度",
        },
        required_params=["observation"],
        returns="观察记录 ID",
    ),

    # ==================== 控制工具 ====================
    ToolName.COMPLETE_WORKFLOW: ToolDefinition(
        name=ToolName.COMPLETE_WORKFLOW,
        description="""完成整个优化分析工作流。
当你认为已经完成了所有必要的检查并生成了所有建议时，调用此工具结束工作流。

必须提供一个简短的总结，说明：
- 分析了哪些维度
- 发现了多少问题
- 生成了多少建议
- 总体评估""",
        parameters={
            "summary": "分析总结",
            "overall_quality": "总体质量评估: excellent / good / needs_improvement / poor",
        },
        required_params=["summary", "overall_quality"],
        returns="确认信息",
    ),
}


def get_tools_prompt() -> str:
    """生成工具定义的提示词文本"""
    lines = ["## 可用工具\n"]

    for tool_def in TOOL_DEFINITIONS.values():
        lines.append(f"### {tool_def.name.value}")
        lines.append(tool_def.description)
        lines.append("")

        if tool_def.parameters:
            lines.append("**参数：**")
            for param_name, param_desc in tool_def.parameters.items():
                required_mark = " (必需)" if param_name in tool_def.required_params else " (可选)"
                lines.append(f"- `{param_name}`{required_mark}: {param_desc}")
            lines.append("")

        lines.append(f"**返回：** {tool_def.returns}")
        lines.append("")

    return "\n".join(lines)


# ==================== 工具调用解析 ====================

@dataclass
class ToolCall:
    """解析后的工具调用"""
    tool_name: ToolName
    parameters: Dict[str, Any]
    reasoning: str = ""


@dataclass
class ToolCallParseResult:
    """工具调用解析结果"""
    success: bool
    tool_call: Optional[ToolCall] = None
    error: Optional[str] = None
    is_parse_error: bool = False    # 找到了标签但格式不对


def parse_tool_call(response: str) -> ToolCallParseResult:
    """
    从 LLM 响应中解析工具调用

    期望格式：
    <tool_call>
    {
        "tool": "tool_name",
        "parameters": {...},
        "reasoning": "为什么调用这个工具"
    }
    </tool_call>
    """
    # 查找 tool_call 标签
    pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
    match = re.search(pattern, response, re.DOTALL)

    if not match:
        return ToolCallParseResult(
            success=False,
            error="未找到工具调用标签 <tool_call>",
            is_parse_error=False,
        )

    json_str = match.group(1).strip()

    # 尝试解析 JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return ToolCallParseResult(
            success=False,
            error=f"JSON 解析失败: {str(e)}",
            is_parse_error=True,
        )

    # 验证必需字段
    tool_name_str = data.get("tool")
    if not tool_name_str:
        return ToolCallParseResult(
            success=False,
            error="缺少 'tool' 字段",
            is_parse_error=True,
        )

    # 验证工具名称
    try:
        tool_name = ToolName(tool_name_str)
    except ValueError:
        valid_tools = [t.value for t in ToolName]
        return ToolCallParseResult(
            success=False,
            error=f"无效的工具名称 '{tool_name_str}'，可用工具: {valid_tools}",
            is_parse_error=True,
        )

    # 获取参数和推理
    parameters = data.get("parameters", {})
    reasoning = data.get("reasoning", "")

    # 验证必需参数
    tool_def = TOOL_DEFINITIONS.get(tool_name)
    if tool_def:
        for required_param in tool_def.required_params:
            if required_param not in parameters:
                return ToolCallParseResult(
                    success=False,
                    error=f"缺少必需参数 '{required_param}'",
                    is_parse_error=True,
                )

    return ToolCallParseResult(
        success=True,
        tool_call=ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            reasoning=reasoning,
        ),
    )


def parse_thinking(response: str) -> Optional[str]:
    """
    从 LLM 响应中解析思考过程

    期望格式：
    <thinking>
    思考内容...
    </thinking>
    """
    pattern = r"<thinking>\s*(.*?)\s*</thinking>"
    match = re.search(pattern, response, re.DOTALL)
    return match.group(1).strip() if match else None


# ==================== 工具执行结果 ====================

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    summary: str = ""   # 用于向 Agent 反馈的摘要


__all__ = [
    "ToolName",
    "ToolDefinition",
    "TOOL_DEFINITIONS",
    "get_tools_prompt",
    "ToolCall",
    "ToolCallParseResult",
    "parse_tool_call",
    "parse_thinking",
    "ToolResult",
]
