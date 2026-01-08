"""
灵感模式模块 - AI对话生成项目蓝图

目录结构：
inspiration_mode/
├── main.py                 # InspirationMode 主类
├── mixins/                 # Mixin 模块
│   ├── blueprint_handler.py    # 蓝图生成和处理
│   └── conversation_manager.py # 对话管理（SSE流式）
├── components/             # UI组件
│   ├── chat_bubble.py          # 对话气泡
│   ├── conversation_input.py   # 对话输入框
│   ├── blueprint_display.py    # 蓝图展示
│   ├── blueprint_confirmation.py # 蓝图确认界面（小说项目）
│   └── inspired_option_card.py # 灵感选项卡片
└── services/               # 服务模块
    └── conversation_state.py   # 对话状态管理
"""

# 主类
from .main import InspirationMode

# Mixins（从 mixins/ 子目录导入，保持向后兼容）
from .mixins import BlueprintHandlerMixin, ConversationManagerMixin

# Components（从 components/ 子目录导入，保持向后兼容）
from .components import (
    ChatBubble,
    ConversationInput,
    BlueprintDisplay,
    BlueprintConfirmation,
    InspiredOptionCard,
    InspiredOptionsContainer,
)

# Services（从 services/ 子目录导入，保持向后兼容）
from .services import ConversationState

__all__ = [
    'InspirationMode',
    # Mixins
    'BlueprintHandlerMixin',
    'ConversationManagerMixin',
    # Components
    'ChatBubble',
    'ConversationInput',
    'BlueprintDisplay',
    'BlueprintConfirmation',
    'InspiredOptionCard',
    'InspiredOptionsContainer',
    # Services
    'ConversationState',
]
