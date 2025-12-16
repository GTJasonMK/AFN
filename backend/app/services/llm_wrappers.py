"""
LLM调用包装器

提供统一的LLM调用接口，消除重复的调用模式。
通过预定义配置简化各服务中的LLM调用。
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..core.config import settings
from ..core.constants import LLMConstants


class LLMProfile(str, Enum):
    """LLM调用配置档案

    预定义的配置档案，覆盖常见的调用场景。
    """
    # 创意类任务（temperature较高）
    CREATIVE = "creative"           # 通用创意任务
    INSPIRATION = "inspiration"     # 灵感对话
    WRITING = "writing"             # 章节写作
    MANGA = "manga"                 # 漫画提示词生成

    # 分析类任务（temperature较低）
    ANALYTICAL = "analytical"       # 通用分析任务
    SUMMARY = "summary"             # 摘要生成
    EVALUATION = "evaluation"       # 评估任务
    COHERENCE = "coherence"         # 连贯性检查
    AGENT = "agent"                 # Agent任务

    # 结构化任务
    BLUEPRINT = "blueprint"         # 蓝图生成
    OUTLINE = "outline"             # 大纲生成
    LAYOUT = "layout"               # 排版布局

    # 快速响应
    QUICK = "quick"                 # 快速响应（低延迟）


@dataclass
class LLMCallConfig:
    """LLM调用配置"""
    temperature: float
    timeout: float = LLMConstants.DEFAULT_TIMEOUT
    response_format: Optional[str] = None
    max_tokens: Optional[int] = None


# 预定义的调用配置映射
_PROFILE_CONFIGS: Dict[LLMProfile, LLMCallConfig] = {
    # 创意类
    LLMProfile.CREATIVE: LLMCallConfig(
        temperature=0.7,
        timeout=LLMConstants.DEFAULT_TIMEOUT,
    ),
    LLMProfile.INSPIRATION: LLMCallConfig(
        temperature=settings.llm_temp_inspiration,
        timeout=LLMConstants.INSPIRATION_TIMEOUT,
    ),
    LLMProfile.WRITING: LLMCallConfig(
        temperature=settings.llm_temp_writing,
        timeout=LLMConstants.CHAPTER_GENERATION_TIMEOUT,
    ),
    LLMProfile.MANGA: LLMCallConfig(
        temperature=0.7,
        timeout=LLMConstants.DEFAULT_TIMEOUT * 2,
    ),

    # 分析类
    LLMProfile.ANALYTICAL: LLMCallConfig(
        temperature=0.3,
        timeout=LLMConstants.DEFAULT_TIMEOUT,
    ),
    LLMProfile.SUMMARY: LLMCallConfig(
        temperature=settings.llm_temp_summary,
        timeout=LLMConstants.SUMMARY_GENERATION_TIMEOUT,
    ),
    LLMProfile.EVALUATION: LLMCallConfig(
        temperature=settings.llm_temp_evaluation,
        timeout=LLMConstants.EVALUATION_TIMEOUT,
    ),
    LLMProfile.COHERENCE: LLMCallConfig(
        temperature=0.3,
        timeout=LLMConstants.COHERENCE_CHECK_TIMEOUT,
    ),
    LLMProfile.AGENT: LLMCallConfig(
        temperature=0.5,
        timeout=LLMConstants.DEFAULT_TIMEOUT * 2,
    ),

    # 结构化任务
    LLMProfile.BLUEPRINT: LLMCallConfig(
        temperature=LLMConstants.BLUEPRINT_TEMPERATURE,
        timeout=LLMConstants.BLUEPRINT_GENERATION_TIMEOUT,
        max_tokens=LLMConstants.BLUEPRINT_MAX_TOKENS,
    ),
    LLMProfile.OUTLINE: LLMCallConfig(
        temperature=settings.llm_temp_outline,
        timeout=LLMConstants.CHAPTER_OUTLINE_TIMEOUT,
    ),
    LLMProfile.LAYOUT: LLMCallConfig(
        temperature=0.7,
        timeout=LLMConstants.DEFAULT_TIMEOUT,
        response_format="json_object",
    ),

    # 快速响应
    LLMProfile.QUICK: LLMCallConfig(
        temperature=0.5,
        timeout=60.0,
        response_format="json_object",
    ),
}


def get_profile_config(profile: Union[LLMProfile, str]) -> LLMCallConfig:
    """
    获取配置档案

    Args:
        profile: 配置档案名称或枚举值

    Returns:
        LLMCallConfig: 调用配置
    """
    if isinstance(profile, str):
        try:
            profile = LLMProfile(profile)
        except ValueError:
            # 未知档案，返回默认配置
            return LLMCallConfig(
                temperature=LLMConstants.DEFAULT_TEMPERATURE,
                timeout=LLMConstants.DEFAULT_TIMEOUT,
            )
    return _PROFILE_CONFIGS.get(profile, _PROFILE_CONFIGS[LLMProfile.CREATIVE])


async def call_llm(
    llm_service,
    profile: Union[LLMProfile, str],
    system_prompt: str,
    user_content: str,
    user_id: Union[int, str],
    *,
    temperature_override: Optional[float] = None,
    timeout_override: Optional[float] = None,
    response_format: Optional[str] = None,
    extra_messages: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    统一的LLM调用入口

    简化LLM调用，通过预定义配置档案消除重复的参数设置。

    Args:
        llm_service: LLM服务实例
        profile: 配置档案（使用LLMProfile枚举或字符串）
        system_prompt: 系统提示词
        user_content: 用户消息内容
        user_id: 用户ID
        temperature_override: 覆盖默认temperature（可选）
        timeout_override: 覆盖默认timeout（可选）
        response_format: 响应格式（可选，如"json_object"）
        extra_messages: 额外的对话历史消息（可选）

    Returns:
        str: LLM响应文本

    Example:
        # 使用预定义配置
        response = await call_llm(
            llm_service, LLMProfile.ANALYTICAL,
            system_prompt="你是专业的编辑...",
            user_content="请分析这段文本",
            user_id=1,
        )

        # 覆盖部分配置
        response = await call_llm(
            llm_service, LLMProfile.CREATIVE,
            system_prompt="...",
            user_content="...",
            user_id=1,
            temperature_override=0.9,
        )
    """
    config = get_profile_config(profile)

    # 构建对话历史
    conversation_history = []
    if extra_messages:
        conversation_history.extend(extra_messages)
    conversation_history.append({"role": "user", "content": user_content})

    # 确定最终参数
    temperature = temperature_override if temperature_override is not None else config.temperature
    timeout = timeout_override if timeout_override is not None else config.timeout
    fmt = response_format if response_format is not None else config.response_format

    # 统一user_id类型
    uid = int(user_id) if isinstance(user_id, str) else user_id

    return await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        temperature=temperature,
        timeout=timeout,
        response_format=fmt,
        user_id=uid,
    )


async def call_llm_json(
    llm_service,
    profile: Union[LLMProfile, str],
    system_prompt: str,
    user_content: str,
    user_id: Union[int, str],
    **kwargs,
) -> str:
    """
    调用LLM并期望JSON响应

    便捷方法，自动设置response_format为json_object。

    Args:
        与call_llm相同

    Returns:
        str: LLM响应文本（JSON格式）
    """
    return await call_llm(
        llm_service,
        profile,
        system_prompt,
        user_content,
        user_id,
        response_format="json_object",
        **kwargs,
    )


def build_conversation_history(
    user_content: str,
    previous_messages: Optional[List[Dict[str, str]]] = None,
) -> List[Dict[str, str]]:
    """
    构建对话历史

    辅助方法，用于需要手动构建对话历史的场景。

    Args:
        user_content: 当前用户消息
        previous_messages: 之前的对话消息列表

    Returns:
        List[Dict[str, str]]: 完整的对话历史
    """
    history = []
    if previous_messages:
        history.extend(previous_messages)
    history.append({"role": "user", "content": user_content})
    return history
