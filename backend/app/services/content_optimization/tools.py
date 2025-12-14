"""
Agent工具定义

定义正文优化Agent可以调用的工具集合。
每个工具有明确的输入输出规范，供Agent自主选择调用。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ToolName(str, Enum):
    """工具名称枚举"""
    # 信息获取工具
    RAG_RETRIEVE = "rag_retrieve"              # RAG检索相关内容
    GET_CHARACTER_STATE = "get_character_state"  # 获取角色当前状态
    GET_FORESHADOWING = "get_foreshadowing"    # 获取相关伏笔
    GET_PREVIOUS_CONTENT = "get_previous_content"  # 获取前文内容

    # 分析工具
    ANALYZE_PARAGRAPH = "analyze_paragraph"     # 分析段落元素
    CHECK_COHERENCE = "check_coherence"         # 检查逻辑连贯性
    CHECK_CHARACTER = "check_character"         # 检查角色一致性
    CHECK_TIMELINE = "check_timeline"           # 检查时间线

    # 输出工具
    GENERATE_SUGGESTION = "generate_suggestion"  # 生成修改建议
    RECORD_OBSERVATION = "record_observation"   # 记录观察结果

    # 控制工具
    NEXT_PARAGRAPH = "next_paragraph"           # 移动到下一段
    FINISH_ANALYSIS = "finish_analysis"         # 完成当前段落分析
    COMPLETE_WORKFLOW = "complete_workflow"     # 完成整个工作流


@dataclass
class ToolDefinition:
    """工具定义"""
    name: ToolName
    description: str
    parameters: Dict[str, Any]
    required_params: List[str] = field(default_factory=list)
    returns: str = ""

    def to_prompt_format(self) -> str:
        """转换为提示词格式"""
        params_desc = []
        for param_name, param_info in self.parameters.items():
            required = "(必需)" if param_name in self.required_params else "(可选)"
            params_desc.append(f"    - {param_name} {required}: {param_info}")

        params_str = "\n".join(params_desc) if params_desc else "    无参数"

        return f"""## {self.name.value}
{self.description}

参数:
{params_str}

返回: {self.returns}
"""


@dataclass
class ToolCall:
    """工具调用请求"""
    tool_name: ToolName
    parameters: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""  # Agent调用此工具的理由


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: ToolName
    success: bool
    result: Any
    error: Optional[str] = None


# 工具定义集合
TOOL_DEFINITIONS: Dict[ToolName, ToolDefinition] = {
    ToolName.RAG_RETRIEVE: ToolDefinition(
        name=ToolName.RAG_RETRIEVE,
        description="使用向量检索获取与查询相关的内容片段，用于理解上下文和验证一致性。",
        parameters={
            "query": "检索查询文本，描述你想要查找的内容",
            "query_type": "查询类型: character(角色相关) / plot(情节相关) / scene(场景相关) / general(通用)",
            "top_k": "返回结果数量，默认5",
        },
        required_params=["query"],
        returns="相关内容片段列表，包含章节号、内容、相似度分数",
    ),

    ToolName.GET_CHARACTER_STATE: ToolDefinition(
        name=ToolName.GET_CHARACTER_STATE,
        description="获取指定角色在当前章节之前的最新状态（位置、情绪、关系等）。",
        parameters={
            "character_name": "角色名称",
        },
        required_params=["character_name"],
        returns="角色状态信息，包含最后出现章节、位置、情绪、重要关系变化等",
    ),

    ToolName.GET_FORESHADOWING: ToolDefinition(
        name=ToolName.GET_FORESHADOWING,
        description="获取与当前内容可能相关的伏笔信息。",
        parameters={
            "keywords": "关键词列表，用于匹配相关伏笔",
        },
        required_params=["keywords"],
        returns="相关伏笔列表，包含伏笔描述、埋设章节、是否已回收",
    ),

    ToolName.GET_PREVIOUS_CONTENT: ToolDefinition(
        name=ToolName.GET_PREVIOUS_CONTENT,
        description="获取前一段或前几段的内容，用于检查衔接。",
        parameters={
            "count": "获取前几段，默认1",
        },
        required_params=[],
        returns="前文段落内容",
    ),

    ToolName.ANALYZE_PARAGRAPH: ToolDefinition(
        name=ToolName.ANALYZE_PARAGRAPH,
        description="分析当前段落，提取其中的角色、场景、时间、情感等元素。",
        parameters={},
        required_params=[],
        returns="段落分析结果：涉及角色、场景描述、时间标记、情感基调、关键动作",
    ),

    ToolName.CHECK_COHERENCE: ToolDefinition(
        name=ToolName.CHECK_COHERENCE,
        description="检查当前段落与前文的逻辑连贯性。",
        parameters={
            "focus": "检查焦点: causality(因果逻辑) / transition(过渡衔接) / motivation(行为动机)",
        },
        required_params=[],
        returns="连贯性检查结果，包含是否存在问题及问题描述",
    ),

    ToolName.CHECK_CHARACTER: ToolDefinition(
        name=ToolName.CHECK_CHARACTER,
        description="检查段落中角色的行为、状态是否与前文一致。",
        parameters={
            "character_name": "要检查的角色名称",
        },
        required_params=["character_name"],
        returns="角色一致性检查结果",
    ),

    ToolName.CHECK_TIMELINE: ToolDefinition(
        name=ToolName.CHECK_TIMELINE,
        description="检查时间线是否合理，包括时间流逝、日夜变化等。",
        parameters={},
        required_params=[],
        returns="时间线检查结果",
    ),

    ToolName.GENERATE_SUGGESTION: ToolDefinition(
        name=ToolName.GENERATE_SUGGESTION,
        description="基于发现的问题生成修改建议。只有在确认存在问题时才调用此工具。",
        parameters={
            "issue_type": "问题类型: coherence / character / timeline / foreshadow / style / scene",
            "issue_description": "问题描述",
            "original_text": "原文（需要修改的部分）",
            "suggested_text": "建议修改后的文本",
            "reason": "修改理由",
            "priority": "优先级: high / medium / low",
        },
        required_params=["issue_type", "issue_description", "original_text", "suggested_text", "reason", "priority"],
        returns="确认建议已记录",
    ),

    ToolName.RECORD_OBSERVATION: ToolDefinition(
        name=ToolName.RECORD_OBSERVATION,
        description="记录分析过程中的观察结果，不一定是问题，可能只是信息记录。",
        parameters={
            "observation": "观察内容",
            "category": "类别: info(信息) / warning(警告) / note(备注)",
        },
        required_params=["observation"],
        returns="确认观察已记录",
    ),

    ToolName.NEXT_PARAGRAPH: ToolDefinition(
        name=ToolName.NEXT_PARAGRAPH,
        description="完成当前段落分析，移动到下一段。",
        parameters={},
        required_params=[],
        returns="下一段的内容和索引，如果没有更多段落则返回None",
    ),

    ToolName.FINISH_ANALYSIS: ToolDefinition(
        name=ToolName.FINISH_ANALYSIS,
        description="完成当前段落的分析，准备处理下一段。当认为当前段落已充分分析时调用。",
        parameters={
            "summary": "当前段落分析总结",
        },
        required_params=[],
        returns="确认完成",
    ),

    ToolName.COMPLETE_WORKFLOW: ToolDefinition(
        name=ToolName.COMPLETE_WORKFLOW,
        description="完成整个优化工作流。当所有段落都已分析完成时调用。",
        parameters={
            "overall_summary": "整体分析总结",
            "total_issues_found": "发现的问题总数",
        },
        required_params=["overall_summary"],
        returns="工作流完成确认",
    ),
}


def get_tools_prompt() -> str:
    """生成工具描述的提示词"""
    sections = []

    # 信息获取工具
    sections.append("# 信息获取工具\n用于获取上下文信息，帮助理解和验证内容。\n")
    for tool_name in [ToolName.RAG_RETRIEVE, ToolName.GET_CHARACTER_STATE,
                      ToolName.GET_FORESHADOWING, ToolName.GET_PREVIOUS_CONTENT]:
        sections.append(TOOL_DEFINITIONS[tool_name].to_prompt_format())

    # 分析工具
    sections.append("\n# 分析工具\n用于分析段落内容和检查一致性。\n")
    for tool_name in [ToolName.ANALYZE_PARAGRAPH, ToolName.CHECK_COHERENCE,
                      ToolName.CHECK_CHARACTER, ToolName.CHECK_TIMELINE]:
        sections.append(TOOL_DEFINITIONS[tool_name].to_prompt_format())

    # 输出工具
    sections.append("\n# 输出工具\n用于记录发现和生成建议。\n")
    for tool_name in [ToolName.GENERATE_SUGGESTION, ToolName.RECORD_OBSERVATION]:
        sections.append(TOOL_DEFINITIONS[tool_name].to_prompt_format())

    # 控制工具
    sections.append("\n# 控制工具\n用于控制分析流程。\n")
    for tool_name in [ToolName.NEXT_PARAGRAPH, ToolName.FINISH_ANALYSIS, ToolName.COMPLETE_WORKFLOW]:
        sections.append(TOOL_DEFINITIONS[tool_name].to_prompt_format())

    return "\n".join(sections)


def parse_tool_call(response: str) -> Optional[ToolCall]:
    """
    从LLM响应中解析工具调用

    期望格式:
    <tool_call>
    {
        "tool": "tool_name",
        "parameters": {...},
        "reasoning": "为什么调用这个工具"
    }
    </tool_call>
    """
    import json
    import re

    # 查找tool_call标签
    pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
    match = re.search(pattern, response, re.DOTALL)

    if not match:
        return None

    try:
        tool_data = json.loads(match.group(1))
        tool_name = ToolName(tool_data.get("tool", ""))
        return ToolCall(
            tool_name=tool_name,
            parameters=tool_data.get("parameters", {}),
            reasoning=tool_data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, ValueError):
        return None


def format_tool_result(result: ToolResult) -> str:
    """格式化工具执行结果，供Agent理解"""
    if not result.success:
        return f"<tool_result>\n工具 {result.tool_name.value} 执行失败: {result.error}\n</tool_result>"

    import json
    result_str = json.dumps(result.result, ensure_ascii=False, indent=2) \
        if isinstance(result.result, (dict, list)) else str(result.result)

    return f"<tool_result>\n工具 {result.tool_name.value} 执行成功:\n{result_str}\n</tool_result>"
