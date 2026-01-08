"""主角分析服务

负责调用LLM进行章节分析、行为分类和隐性属性更新决策。
"""
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...schemas.protagonist import (
    ChapterAnalysisResult,
    BehaviorClassificationResult,
    ImplicitUpdateDecision,
    LLMAttributeChange,
    LLMBehavior,
    LLMDeletionCandidate,
)
from ...services.llm_service import LLMService
from ...services.prompt_service import PromptService
from ...utils.json_utils import parse_llm_json_safe

logger = logging.getLogger(__name__)


class ProtagonistAnalysisService:
    """主角分析服务

    使用LLM进行：
    1. 章节分析 - 提取属性变化和行为记录
    2. 行为分类 - 判断行为与隐性属性的符合度
    3. 隐性属性更新决策 - 决定是否更新隐性属性
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: LLMService,
        prompt_service: PromptService
    ):
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def _load_prompt(self, name: str) -> str:
        """加载提示词内容

        Args:
            name: 提示词名称（不含.md后缀）

        Returns:
            提示词内容
        """
        # 优先从数据库获取（支持用户修改）
        content = await self.prompt_service.get_prompt(name)
        if content:
            return content

        # 回退到默认文件
        default_content = await self.prompt_service.get_default_content(name)
        if default_content:
            return default_content

        logger.warning(f"提示词不存在: {name}")
        return ""

    async def analyze_chapter(
        self,
        chapter_content: str,
        current_profile: Dict[str, Any],
        chapter_number: int,
        user_id: int
    ) -> ChapterAnalysisResult:
        """分析章节内容，提取主角相关信息

        Args:
            chapter_content: 章节正文内容
            current_profile: 当前主角档案 {explicit, implicit, social}
            chapter_number: 章节号
            user_id: 用户ID（用于LLM配置）

        Returns:
            章节分析结果
        """
        system_prompt = await self._load_prompt("protagonist_analysis")

        # 构建用户提示
        user_prompt = f"""请分析以下章节内容，提取主角属性变化和行为记录。

## 当前章节号
第{chapter_number}章

## 当前主角档案
```json
{json.dumps(current_profile, ensure_ascii=False, indent=2)}
```

## 章节内容
{chapter_content[:8000]}  # 限制内容长度
"""

        try:
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": user_prompt}],
                user_id=user_id,
                max_tokens=settings.llm_max_tokens_analysis,
            )

            # 解析LLM返回的JSON
            result_data = parse_llm_json_safe(response)
            if not result_data:
                logger.warning(f"章节分析LLM返回解析失败: {response[:200]}")
                return ChapterAnalysisResult()

            # 构建结果对象
            attribute_changes = [
                LLMAttributeChange(**change)
                for change in result_data.get("attribute_changes", [])
            ]
            behaviors = [
                LLMBehavior(**behavior)
                for behavior in result_data.get("behaviors", [])
            ]
            deletion_candidates = [
                LLMDeletionCandidate(**candidate)
                for candidate in result_data.get("deletion_candidates", [])
            ]

            return ChapterAnalysisResult(
                attribute_changes=attribute_changes,
                behaviors=behaviors,
                deletion_candidates=deletion_candidates,
            )

        except Exception as e:
            logger.error(f"章节分析失败: {e}")
            return ChapterAnalysisResult()

    async def classify_behavior(
        self,
        behavior_description: str,
        original_text: str,
        behavior_tags: List[str],
        implicit_attributes: Dict[str, Any],
        user_id: int
    ) -> BehaviorClassificationResult:
        """对行为进行二元分类

        判断行为是否符合已有的隐性属性。

        Args:
            behavior_description: 行为描述
            original_text: 原文摘录
            behavior_tags: 行为标签
            implicit_attributes: 当前隐性属性字典
            user_id: 用户ID

        Returns:
            分类结果
        """
        system_prompt = await self._load_prompt("implicit_classification")

        user_prompt = f"""请判断以下行为是否符合已有的隐性属性。

## 行为信息
- 描述: {behavior_description}
- 标签: {', '.join(behavior_tags)}
- 原文: {original_text}

## 当前隐性属性
```json
{json.dumps(implicit_attributes, ensure_ascii=False, indent=2)}
```
"""

        try:
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": user_prompt}],
                user_id=user_id,
                max_tokens=settings.llm_max_tokens_analysis,
            )

            result_data = parse_llm_json_safe(response)
            if not result_data:
                logger.warning(f"行为分类LLM返回解析失败: {response[:200]}")
                return BehaviorClassificationResult(
                    classifications={},
                    reasoning="LLM返回解析失败",
                    suggested_new_attributes=[]
                )

            return BehaviorClassificationResult(
                classifications=result_data.get("classifications", {}),
                reasoning=result_data.get("reasoning", ""),
                suggested_new_attributes=result_data.get("suggested_new_attributes", [])
            )

        except Exception as e:
            logger.error(f"行为分类失败: {e}")
            return BehaviorClassificationResult(
                classifications={},
                reasoning=f"分类失败: {str(e)}",
                suggested_new_attributes=[]
            )

    async def decide_implicit_update(
        self,
        attribute_key: str,
        current_value: Any,
        behavior_records: List[Dict[str, Any]],
        non_conform_count: int,
        user_id: int
    ) -> ImplicitUpdateDecision:
        """决定是否更新隐性属性

        当某属性在窗口内累计多次"不符合"时，由LLM决定是否真的需要更新。

        Args:
            attribute_key: 属性键名
            current_value: 当前值
            behavior_records: 相关行为记录列表
            non_conform_count: 不符合次数
            user_id: 用户ID

        Returns:
            更新决策
        """
        system_prompt = await self._load_prompt("implicit_update")

        # 构建行为记录摘要
        records_summary = []
        for record in behavior_records[:10]:  # 最多10条
            records_summary.append(
                f"- 第{record['chapter']}章: {record['behavior']} "
                f"[{record['classification']}]\n  原文: {record['original_text'][:100]}..."
            )

        user_prompt = f"""请决定是否需要更新以下隐性属性。

## 属性信息
- 属性名: {attribute_key}
- 当前值: {json.dumps(current_value, ensure_ascii=False)}
- 不符合次数: {non_conform_count}

## 相关行为记录
{chr(10).join(records_summary)}
"""

        try:
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=[{"role": "user", "content": user_prompt}],
                user_id=user_id,
                max_tokens=settings.llm_max_tokens_analysis,
            )

            result_data = parse_llm_json_safe(response)
            if not result_data:
                logger.warning(f"隐性属性更新决策LLM返回解析失败: {response[:200]}")
                return ImplicitUpdateDecision(
                    decision="keep",
                    reasoning="LLM返回解析失败，保持原值",
                    new_value=None,
                    evidence_summary=""
                )

            return ImplicitUpdateDecision(
                decision=result_data.get("decision", "keep"),
                reasoning=result_data.get("reasoning", ""),
                new_value=result_data.get("new_value"),
                evidence_summary=result_data.get("evidence_summary", "")
            )

        except Exception as e:
            logger.error(f"隐性属性更新决策失败: {e}")
            return ImplicitUpdateDecision(
                decision="keep",
                reasoning=f"决策失败: {str(e)}",
                new_value=None,
                evidence_summary=""
            )
