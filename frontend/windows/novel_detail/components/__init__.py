"""
NovelDetail Components - 子组件

- CharacterRow: 角色行组件
- RelationshipRow: 关系行组件
- CharacterPortraitsWidget: 角色立绘组件
"""

from .character_row import CharacterRow
from .relationship_row import RelationshipRow
from .character_portraits_widget import CharacterPortraitsWidget

__all__ = [
    'CharacterRow',
    'RelationshipRow',
    'CharacterPortraitsWidget',
]
