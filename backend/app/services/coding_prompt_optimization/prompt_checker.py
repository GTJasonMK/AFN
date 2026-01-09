"""
编程项目 Prompt 优化 - Prompt 质量检查器

提供 LLM 驱动的深度质量检查功能。
"""

import json
import logging
from typing import Any, Dict, List, Optional

from .schemas import (
    DIMENSION_DISPLAY_NAMES,
    OptimizationContext,
    get_dimension_weight,
)

logger = logging.getLogger(__name__)


class PromptChecker:
    """
    Prompt 质量检查器

    使用 LLM 对 Prompt 进行深度质量检查，分析多个维度的问题。
    """

    def __init__(self, llm_service: Any):
        self.llm_service = llm_service

    async def deep_check(
        self,
        prompt_content: str,
        context: OptimizationContext,
        dimensions: List[str],
        focus_area: Optional[str],
        user_id: str,
    ) -> Dict[str, Any]:
        """
        执行 LLM 深度检查

        Args:
            prompt_content: 待检查的 Prompt 内容
            context: 优化上下文
            dimensions: 检查维度列表
            focus_area: 重点关注区域
            user_id: 用户 ID

        Returns:
            检查结果字典
        """
        # 构建系统提示词
        system_prompt = self._build_system_prompt(dimensions)

        # 构建用户提示词
        user_prompt = self._build_user_prompt(
            prompt_content=prompt_content,
            context=context,
            dimensions=dimensions,
            focus_area=focus_area,
        )

        try:
            # 调用 LLM
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": user_prompt}],
                user_id=int(user_id) if user_id else None,
                max_tokens=4000,
                timeout=120,
            )

            # 解析响应
            return self._parse_response(response, dimensions)

        except Exception as e:
            logger.error("LLM 深度检查失败: %s", e)
            return {
                "success": False,
                "error": str(e),
                "dimension_results": [],
            }

    def _build_system_prompt(self, dimensions: List[str]) -> str:
        """构建系统提示词"""
        dimension_descriptions = self._get_dimension_descriptions(dimensions)

        return f"""你是一位资深的软件工程师和代码审查专家。你的任务是对编程项目功能的 Prompt 进行深度质量检查。

## 检查维度

{dimension_descriptions}

## 输出格式

请以 JSON 格式输出检查结果：

```json
{{
    "overall_assessment": "总体评估（excellent/good/needs_improvement/poor）",
    "dimension_results": [
        {{
            "dimension": "维度标识",
            "score": 0-100,
            "status": "pass/warning/fail",
            "issues": [
                {{
                    "severity": "high/medium/low",
                    "description": "问题描述",
                    "location": "问题位置（如有）",
                    "suggestion": "改进建议"
                }}
            ],
            "strengths": ["优点1", "优点2"]
        }}
    ],
    "summary": "总结性说明",
    "priority_fixes": ["最需要修复的问题1", "最需要修复的问题2"]
}}
```

## 评估标准

- **excellent**: 90-100分，几乎没有问题
- **good**: 70-89分，有少量可改进点
- **needs_improvement**: 50-69分，存在明显问题需要修复
- **poor**: 0-49分，存在严重问题

## 注意事项

1. 客观评估，不要过于苛刻或过于宽松
2. 问题描述要具体，指出问题的位置
3. 建议要可操作，给出具体的修改方向
4. 关注实际影响，区分严重问题和次要问题"""

    def _build_user_prompt(
        self,
        prompt_content: str,
        context: OptimizationContext,
        dimensions: List[str],
        focus_area: Optional[str],
    ) -> str:
        """构建用户提示词"""
        feature = context.feature
        project = context.project

        focus_instruction = ""
        if focus_area:
            focus_instruction = f"\n\n**重点关注区域**: {focus_area}"

        return f"""请对以下编程项目功能的 Prompt 进行深度质量检查。

## 功能信息

- **功能名称**: {feature.feature_name}
- **功能编号**: {feature.feature_number}
- **功能描述**: {feature.feature_description or '无'}
- **输入**: {feature.inputs or '无'}
- **输出**: {feature.outputs or '无'}
- **所属系统**: {feature.system_name or '无'}
- **所属模块**: {feature.module_name or '无'}

## 项目背景

- **项目名称**: {project.project_name}
- **技术栈**: {json.dumps(project.tech_stack, ensure_ascii=False) if project.tech_stack else '未指定'}

## 待检查的 Prompt 内容

```
{prompt_content}
```

## 检查维度

请检查以下维度：{', '.join([DIMENSION_DISPLAY_NAMES.get(d, d) for d in dimensions])}
{focus_instruction}

请按照指定的 JSON 格式输出检查结果。"""

    def _get_dimension_descriptions(self, dimensions: List[str]) -> str:
        """获取维度描述"""
        descriptions = {
            "completeness": """### 功能完整性 (completeness)
检查 Prompt 是否完整覆盖功能需求：
- 功能描述中的所有要点是否都有对应实现
- 输入参数是否都有处理逻辑
- 输出结果是否都有生成方式
- 是否遗漏了隐含需求""",

            "interface": """### 接口定义 (interface)
检查接口定义是否清晰：
- 是否明确定义了函数/方法签名
- 参数类型和含义是否清晰
- 返回值类型和结构是否明确
- 是否有必要的类型注解""",

            "dependency": """### 依赖关系 (dependency)
检查依赖关系是否正确：
- 引用的模块/服务是否存在
- 依赖关系是否合理
- 是否存在循环依赖风险
- 是否有未声明的隐式依赖""",

            "implementation": """### 实现步骤 (implementation)
检查实现步骤是否合理：
- 步骤是否清晰、可执行
- 逻辑流程是否正确
- 算法选择是否合适
- 是否考虑了边界条件""",

            "error_handling": """### 错误处理 (error_handling)
检查错误处理是否完备：
- 是否处理了常见异常
- 边界条件是否考虑
- 错误信息是否清晰
- 是否有适当的容错机制""",

            "security": """### 安全性 (security)
检查安全性考虑：
- 是否有输入验证
- 是否防止了注入攻击
- 权限控制是否合理
- 敏感数据处理是否安全""",

            "performance": """### 性能考虑 (performance)
检查性能相关考虑：
- 算法复杂度是否合理
- 是否考虑了大数据量场景
- 是否有必要的缓存策略
- 是否避免了明显的性能问题""",
        }

        lines = []
        for dim in dimensions:
            if dim in descriptions:
                lines.append(descriptions[dim])
                lines.append(f"权重: {get_dimension_weight(dim)}")
                lines.append("")

        return "\n".join(lines)

    def _parse_response(
        self,
        response: str,
        dimensions: List[str],
    ) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            json_str = self._extract_json(response)
            if json_str:
                result = json.loads(json_str)
                result["success"] = True
                return result
        except json.JSONDecodeError as e:
            logger.warning("JSON 解析失败: %s", e)

        # 解析失败，返回降级结果
        return {
            "success": False,
            "error": "无法解析 LLM 响应",
            "raw_response": response[:1000],
            "dimension_results": [
                {
                    "dimension": dim,
                    "status": "unknown",
                    "issues": [],
                    "strengths": [],
                }
                for dim in dimensions
            ],
        }

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取 JSON"""
        import re

        # 尝试提取 ```json ... ``` 块
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if json_match:
            return json_match.group(1).strip()

        # 尝试找 { ... } 块
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            return text[brace_start:brace_end + 1]

        return None

    async def quick_score(
        self,
        prompt_content: str,
        context: OptimizationContext,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        快速评分（轻量级检查）

        Args:
            prompt_content: Prompt 内容
            context: 优化上下文
            user_id: 用户 ID

        Returns:
            快速评分结果
        """
        system_prompt = """你是一位代码审查专家。请对给定的编程功能 Prompt 进行快速评分。

输出格式（JSON）：
```json
{
    "score": 0-100,
    "grade": "A/B/C/D/F",
    "brief_assessment": "一句话评价",
    "top_issue": "最主要的问题（如有）",
    "top_strength": "最突出的优点"
}
```"""

        feature = context.feature
        user_prompt = f"""功能: {feature.feature_name}
描述: {feature.feature_description or '无'}

Prompt 内容:
```
{prompt_content[:2000]}
```

请快速评分。"""

        try:
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": user_prompt}],
                user_id=int(user_id) if user_id else None,
                max_tokens=500,
                timeout=30,
            )

            json_str = self._extract_json(response)
            if json_str:
                result = json.loads(json_str)
                result["success"] = True
                return result

        except Exception as e:
            logger.error("快速评分失败: %s", e)

        return {
            "success": False,
            "score": 0,
            "grade": "?",
            "brief_assessment": "评分失败",
        }


__all__ = [
    "PromptChecker",
]
