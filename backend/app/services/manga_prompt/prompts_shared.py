"""
漫画提示词共享字段说明

用于在不同提示词模板中复用一致的字段定义文本。
"""

# 事件字段基础说明（提取/规划共用）
EVENT_FIELDS_BASE = """- index: 事件序号（从0开始）
- type: 事件类型（dialogue=对话/action=动作/reaction=反应/transition=过渡/revelation=揭示/conflict=冲突/resolution=解决/description=描述/internal=内心活动）
- description: 事件描述
- participants: 参与角色列表
"""

__all__ = [
    "EVENT_FIELDS_BASE",
]
