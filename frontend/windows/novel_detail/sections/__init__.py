"""
NovelDetail Sections - Tab页面内容组件

- OverviewSection: 项目概览
- WorldSettingSection: 世界设定
- CharactersSection: 角色列表
- RelationshipsSection: 关系图谱
- ChaptersSection: 已生成章节
"""

from .overview_section import OverviewSection
from .world_setting_section import WorldSettingSection
from .characters_section import CharactersSection
from .relationships_section import RelationshipsSection
from .chapters_section import ChaptersSection

__all__ = [
    'OverviewSection',
    'WorldSettingSection',
    'CharactersSection',
    'RelationshipsSection',
    'ChaptersSection',
]
