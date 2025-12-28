"""
设置模块对话框

提供设置页面使用的各类对话框：
- TestResultDialog: 测试结果对话框
- LLMConfigDialog: LLM配置对话框
- EmbeddingConfigDialog: 嵌入配置对话框
- PromptEditDialog: 提示词编辑对话框
"""

from .test_result_dialog import TestResultDialog
from .config_dialog import LLMConfigDialog
from .embedding_config_dialog import EmbeddingConfigDialog
from .prompt_edit_dialog import PromptEditDialog

__all__ = [
    "TestResultDialog",
    "LLMConfigDialog",
    "EmbeddingConfigDialog",
    "PromptEditDialog",
]
