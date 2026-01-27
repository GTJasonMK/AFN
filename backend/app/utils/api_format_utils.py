# -*- coding: utf-8 -*-
"""LLM API格式工具函数

提供API格式检测、URL构建等工具函数。
"""

import logging
import re
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)
_SCHEME_RE = re.compile(r"^(https?://)(.*)$", re.IGNORECASE)


class APIFormat(Enum):
    """API格式枚举"""
    OPENAI = "openai"          # OpenAI Chat Completions API
    ANTHROPIC = "anthropic"    # Anthropic Messages API


def detect_api_format(model_name: str) -> APIFormat:
    """
    根据模型名称自动检测API格式

    Args:
        model_name: 模型名称

    Returns:
        APIFormat: 检测到的API格式
    """
    if not model_name:
        return APIFormat.OPENAI

    model_lower = model_name.lower()

    # Claude系列模型使用Anthropic格式
    if 'claude' in model_lower:
        return APIFormat.ANTHROPIC

    # 其他模型使用OpenAI格式
    return APIFormat.OPENAI


def fix_base_url(base_url: str) -> str:
    """
    修复base_url中可能存在的问题

    - 移除尾部斜杠
    - 修复双斜杠问题（协议部分保留，仅归一化 path 的连续斜杠）
    """
    if not base_url:
        return base_url

    fixed_url = base_url.rstrip('/')

    # 检查是否存在双斜杠（排除协议部分的://）
    m = _SCHEME_RE.match(fixed_url)
    scheme, rest = (m.group(1), m.group(2)) if m else ("", fixed_url)
    if '//' in rest:
        # 仅处理 path 中的连续斜杠，避免破坏 http://
        rest_fixed = re.sub(r"/{2,}", "/", rest)
        fixed = f"{scheme}{rest_fixed}" if scheme else rest_fixed
        logger.warning("base_url包含双斜杠，已自动修复: %s -> %s", base_url, fixed)
        return fixed

    return fixed_url


def build_anthropic_endpoint(base_url: str) -> str:
    """
    构建Anthropic Messages API端点

    智能处理各种base_url格式：
    - http://api.example.com -> http://api.example.com/v1/messages
    - http://api.example.com/v1 -> http://api.example.com/v1/messages
    - http://api.example.com/v1/messages -> 保持不变
    """
    base = fix_base_url(base_url)

    if base.endswith('/messages'):
        return base
    elif base.endswith('/v1'):
        return f"{base}/messages"
    else:
        return f"{base}/v1/messages"


def build_openai_endpoint(base_url: str) -> str:
    """
    构建OpenAI Chat Completions API端点

    智能处理各种base_url格式：
    - http://api.example.com -> http://api.example.com/v1/chat/completions
    - http://api.example.com/v1 -> http://api.example.com/v1/chat/completions
    - http://api.example.com/v1/chat/completions -> 保持不变
    """
    base = fix_base_url(base_url)

    if base.endswith('/chat/completions'):
        return base
    elif base.endswith('/v1'):
        return f"{base}/chat/completions"
    else:
        return f"{base}/v1/chat/completions"


def build_openai_image_generations_endpoint(base_url: str) -> str:
    """
    构建OpenAI Images Generations API端点

    智能处理各种base_url格式：
    - http://api.example.com -> http://api.example.com/v1/images/generations
    - http://api.example.com/v1 -> http://api.example.com/v1/images/generations
    - http://api.example.com/v1/images/generations -> 保持不变
    """
    base = fix_base_url(base_url)

    if base.endswith('/images/generations'):
        return base
    elif base.endswith('/v1'):
        return f"{base}/images/generations"
    else:
        return f"{base}/v1/images/generations"


def get_browser_headers() -> Dict[str, str]:
    """获取模拟浏览器的请求头，帮助绕过一些API限制"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'DNT': '1',
    }
