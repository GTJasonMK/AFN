"""
LLM请求队列

管理所有LLM API调用的并发控制。
"""

from .base import ConfigurableRequestQueue


class LLMRequestQueue(ConfigurableRequestQueue):
    """
    LLM请求队列（单例模式）

    所有LLM调用（灵感对话、蓝图生成、章节生成等）都通过此队列进行并发控制。
    """

    queue_name = "llm"
    settings_key = "llm_max_concurrent"
    default_max_concurrent = 3
    log_label = "LLM"
