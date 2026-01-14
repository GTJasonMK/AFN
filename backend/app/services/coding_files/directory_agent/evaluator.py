"""
目录规划质量评估器

使用LLM对规划结果进行多维度语义级评估，
替代简单的规则检查，提供更准确的质量判断。
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationDimension:
    """评估维度"""
    name: str           # 维度名称
    weight: float       # 权重 (0-1)
    description: str    # 维度说明


# 评估维度定义
EVALUATION_DIMENSIONS = [
    EvaluationDimension(
        name="functionality",
        weight=0.30,
        description="功能完整性：文件描述是否清晰说明要实现的具体功能",
    ),
    EvaluationDimension(
        name="architecture",
        weight=0.25,
        description="架构合理性：文件位置是否符合分层/模块化原则",
    ),
    EvaluationDimension(
        name="dependencies",
        weight=0.20,
        description="依赖合理性：依赖关系是否必要且合理，无循环依赖",
    ),
    EvaluationDimension(
        name="implementability",
        weight=0.25,
        description="可实现性：信息是否足够让编程Agent生成代码",
    ),
]


@dataclass
class FileEvaluation:
    """单个文件的评估结果"""
    path: str
    scores: Dict[str, int]      # 各维度得分 (1-5)
    overall_score: float        # 综合得分
    issues: List[str]           # 发现的问题
    suggestions: List[str]      # 改进建议
    is_acceptable: bool         # 是否达标


@dataclass
class OverallEvaluation:
    """整体评估结果"""
    total_files: int
    evaluated_files: int
    average_score: float
    dimension_scores: Dict[str, float]  # 各维度平均分
    critical_issues: List[str]          # 关键问题
    can_finish: bool                    # 是否可以完成
    finish_reasoning: str               # 完成决策的理由


class PlanningEvaluator:
    """
    规划质量评估器

    使用LLM进行语义级评估，支持：
    1. 单文件评估
    2. 整体结构评估
    3. 完成决策
    """

    # 评估通过阈值
    ACCEPTABLE_SCORE = 3.0  # 单文件最低可接受分数
    FINISH_THRESHOLD = 3.5  # 整体完成阈值

    def __init__(self, llm_caller: Optional[Callable] = None):
        """
        初始化评估器

        Args:
            llm_caller: LLM调用函数，签名为 async (system_prompt, user_prompt) -> str
        """
        self.llm_caller = llm_caller
        self._evaluation_cache: Dict[str, FileEvaluation] = {}

    def build_file_evaluation_prompt(self, file_info: Dict[str, Any],
                                     project_context: Dict[str, Any]) -> str:
        """构建单文件评估的用户提示词"""
        return f"""请评估以下文件规划的质量。

## 项目背景
- 项目名称: {project_context.get('title', '未知')}
- 项目描述: {project_context.get('summary', '未知')}
- 技术栈: {project_context.get('tech_stack', '未知')}

## 待评估文件
- 路径: {file_info.get('path', '')}
- 描述: {file_info.get('description', '')}
- 存在理由: {file_info.get('purpose', '')}
- 所属模块: {file_info.get('module_name', '')}
- 依赖模块: {file_info.get('dependencies', [])}
- 依赖原因: {file_info.get('dependency_reasons', '')}
- 实现备注: {file_info.get('implementation_notes', '')}

## 评估要求
请从以下四个维度评估，每个维度给出1-5分：
1. 功能完整性(functionality): 描述是否清晰说明要实现的具体功能
2. 架构合理性(architecture): 文件位置是否符合分层/模块化原则
3. 依赖合理性(dependencies): 依赖关系是否必要且合理
4. 可实现性(implementability): 信息是否足够让编程Agent生成代码

## 输出格式(JSON)
```json
{{
    "scores": {{
        "functionality": <1-5>,
        "architecture": <1-5>,
        "dependencies": <1-5>,
        "implementability": <1-5>
    }},
    "issues": ["问题1", "问题2"],
    "suggestions": ["建议1", "建议2"]
}}
```"""

    def build_finish_decision_prompt(self, state_summary: Dict[str, Any],
                                     optimization_history: List[Dict]) -> str:
        """构建完成决策的用户提示词"""
        # 格式化优化历程
        history_text = ""
        for record in optimization_history[-10:]:  # 最近10条
            history_text += f"- [{record.get('action')}] {record.get('target')}: {record.get('reason', '')[:50]}\n"

        return f"""请判断目录规划是否可以完成。

## 当前状态
- 总模块数: {state_summary.get('total_modules', 0)}
- 已覆盖模块: {state_summary.get('covered_modules', 0)}
- 覆盖率: {state_summary.get('coverage_rate', 0):.0%}
- 总文件数: {state_summary.get('total_files', 0)}
- 质量达标文件数: {state_summary.get('quality_ok_count', 0)}
- 质量达标率: {state_summary.get('quality_rate', 0):.0%}

## 优化历程（最近10条）
{history_text if history_text else "暂无优化记录"}

## 判断标准
1. 所有模块是否都有对应的文件覆盖
2. 文件信息是否足够详细，能支撑后续代码生成
3. 目录结构是否合理，符合架构原则
4. 是否还有明显需要优化的地方

## 输出格式(JSON)
```json
{{
    "can_finish": true/false,
    "reasoning": "判断理由",
    "remaining_issues": ["如果不能完成，列出需要解决的问题"]
}}
```"""

    def _parse_evaluation_response(self, response: str) -> Dict[str, Any]:
        """解析LLM评估响应"""
        import json
        import re

        # 尝试提取JSON
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("无法解析LLM评估响应: %s", response[:200])
            return {}

    def _calculate_overall_score(self, scores: Dict[str, int]) -> float:
        """计算加权综合得分"""
        total_weight = 0
        weighted_sum = 0

        for dim in EVALUATION_DIMENSIONS:
            if dim.name in scores:
                weighted_sum += scores[dim.name] * dim.weight
                total_weight += dim.weight

        return weighted_sum / total_weight if total_weight > 0 else 0

    async def evaluate_file(self, file_info: Dict[str, Any],
                           project_context: Dict[str, Any]) -> FileEvaluation:
        """
        评估单个文件

        Args:
            file_info: 文件信息
            project_context: 项目上下文

        Returns:
            FileEvaluation: 评估结果

        Raises:
            ValueError: 未配置LLM调用函数
        """
        path = file_info.get("path", "")

        # 检查缓存
        if path in self._evaluation_cache:
            return self._evaluation_cache[path]

        if not self.llm_caller:
            raise ValueError("未配置LLM调用函数，无法进行语义级评估")

        # 构建提示词并调用LLM
        system_prompt = "你是一个专业的软件架构评估专家，负责评估目录规划的质量。请严格按照JSON格式输出。"
        user_prompt = self.build_file_evaluation_prompt(file_info, project_context)

        response = await self.llm_caller(system_prompt, user_prompt)
        parsed = self._parse_evaluation_response(response)

        scores = parsed.get("scores", {})
        overall_score = self._calculate_overall_score(scores)

        evaluation = FileEvaluation(
            path=path,
            scores=scores,
            overall_score=overall_score,
            issues=parsed.get("issues", []),
            suggestions=parsed.get("suggestions", []),
            is_acceptable=overall_score >= self.ACCEPTABLE_SCORE,
        )

        self._evaluation_cache[path] = evaluation
        return evaluation

    async def decide_finish(self, state_summary: Dict[str, Any],
                           optimization_history: List[Dict]) -> Dict[str, Any]:
        """
        决定是否可以完成规划

        Args:
            state_summary: 当前状态摘要
            optimization_history: 优化历程

        Returns:
            决策结果

        Raises:
            ValueError: 未配置LLM调用函数
        """
        # 基础检查
        coverage_rate = state_summary.get("coverage_rate", 0)

        # 硬性条件检查
        if coverage_rate < 1.0:
            return {
                "can_finish": False,
                "reasoning": f"模块覆盖率不足: {coverage_rate:.0%}",
                "remaining_issues": ["需要为所有模块创建对应文件"],
            }

        if not self.llm_caller:
            raise ValueError("未配置LLM调用函数，无法进行完成决策")

        # 使用LLM判断
        system_prompt = "你是一个专业的软件架构评估专家。请根据当前状态判断目录规划是否可以完成。"
        user_prompt = self.build_finish_decision_prompt(state_summary, optimization_history)

        response = await self.llm_caller(system_prompt, user_prompt)
        return self._parse_evaluation_response(response)
