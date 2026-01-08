"""
小说项目RAG数据类型定义

定义15种需要入库的数据类型及其检索权重。
"""

from enum import Enum
from typing import Dict


class NovelDataType(str, Enum):
    """小说项目RAG数据类型枚举"""

    # 创作前期
    INSPIRATION = "inspiration"           # 灵感对话
    SYNOPSIS = "synopsis"                 # 故事概述
    WORLD_SETTING = "world_setting"       # 世界观设定
    BLUEPRINT_METADATA = "blueprint_metadata"  # 蓝图元数据(标题、体裁、风格、基调等)

    # 角色相关
    CHARACTER = "character"               # 角色设定
    RELATIONSHIP = "relationship"         # 角色关系
    CHARACTER_STATE = "character_state"   # 角色状态快照
    PROTAGONIST = "protagonist"           # 主角档案
    PROTAGONIST_CHANGE = "protagonist_change"  # 主角属性变更历史

    # 大纲相关
    PART_OUTLINE = "part_outline"         # 分部大纲
    CHAPTER_OUTLINE = "chapter_outline"   # 章节大纲

    # 内容相关
    CHAPTER_CONTENT = "chapter_content"   # 章节正文
    CHAPTER_SUMMARY = "chapter_summary"   # 章节摘要
    KEY_EVENT = "key_event"               # 章节关键事件
    CHAPTER_METADATA = "chapter_metadata" # 章节元数据(地点、物品、标签)

    # 伏笔追踪
    FORESHADOWING = "foreshadowing"       # 伏笔记录

    @classmethod
    def get_weight(cls, data_type: str) -> float:
        """
        获取数据类型的检索权重

        权重越高，检索时该类型结果越优先。
        权重影响排序，不影响召回。

        Args:
            data_type: 数据类型字符串

        Returns:
            权重值，范围0.0-1.0
        """
        weights: Dict[str, float] = {
            cls.SYNOPSIS.value: 1.0,              # 最高：故事核心
            cls.BLUEPRINT_METADATA.value: 0.98,   # 蓝图元数据(标题、体裁、风格)
            cls.WORLD_SETTING.value: 0.95,        # 世界观约束
            cls.CHARACTER.value: 0.9,             # 角色设定
            cls.KEY_EVENT.value: 0.88,            # 关键事件（高优先级，情节驱动）
            cls.CHAPTER_CONTENT.value: 0.85,      # 章节正文
            cls.CHAPTER_SUMMARY.value: 0.8,       # 章节摘要
            cls.CHAPTER_OUTLINE.value: 0.75,      # 章节大纲
            cls.CHAPTER_METADATA.value: 0.72,     # 章节元数据（地点、物品、标签）
            cls.PART_OUTLINE.value: 0.7,          # 分部大纲
            cls.FORESHADOWING.value: 0.65,        # 伏笔
            cls.RELATIONSHIP.value: 0.6,          # 角色关系
            cls.CHARACTER_STATE.value: 0.55,      # 角色状态
            cls.PROTAGONIST.value: 0.5,           # 主角档案
            cls.PROTAGONIST_CHANGE.value: 0.48,   # 主角属性变更历史
            cls.INSPIRATION.value: 0.4,           # 灵感对话（最低）
        }
        return weights.get(data_type, 0.5)

    @classmethod
    def get_display_name(cls, data_type: str) -> str:
        """
        获取数据类型的显示名称

        Args:
            data_type: 数据类型字符串

        Returns:
            中文显示名称
        """
        names: Dict[str, str] = {
            cls.INSPIRATION.value: "灵感对话",
            cls.SYNOPSIS.value: "故事概述",
            cls.WORLD_SETTING.value: "世界观设定",
            cls.BLUEPRINT_METADATA.value: "蓝图元数据",
            cls.CHARACTER.value: "角色设定",
            cls.RELATIONSHIP.value: "角色关系",
            cls.CHARACTER_STATE.value: "角色状态",
            cls.PROTAGONIST.value: "主角档案",
            cls.PROTAGONIST_CHANGE.value: "主角属性变更",
            cls.PART_OUTLINE.value: "分部大纲",
            cls.CHAPTER_OUTLINE.value: "章节大纲",
            cls.CHAPTER_CONTENT.value: "章节正文",
            cls.CHAPTER_SUMMARY.value: "章节摘要",
            cls.KEY_EVENT.value: "关键事件",
            cls.CHAPTER_METADATA.value: "章节元数据",
            cls.FORESHADOWING.value: "伏笔记录",
        }
        return names.get(data_type, data_type)

    @classmethod
    def get_source_table(cls, data_type: str) -> str:
        """
        获取数据类型对应的数据库表名

        Args:
            data_type: 数据类型字符串

        Returns:
            数据库表名
        """
        tables: Dict[str, str] = {
            cls.INSPIRATION.value: "novel_conversations",
            cls.SYNOPSIS.value: "novel_blueprints",
            cls.WORLD_SETTING.value: "novel_blueprints",
            cls.BLUEPRINT_METADATA.value: "novel_blueprints",
            cls.CHARACTER.value: "blueprint_characters",
            cls.RELATIONSHIP.value: "blueprint_relationships",
            cls.CHARACTER_STATE.value: "character_state_index",
            cls.PROTAGONIST.value: "protagonist_profiles",
            cls.PROTAGONIST_CHANGE.value: "protagonist_attribute_changes",
            cls.PART_OUTLINE.value: "part_outlines",
            cls.CHAPTER_OUTLINE.value: "chapter_outlines",
            cls.CHAPTER_CONTENT.value: "chapter_versions",
            cls.CHAPTER_SUMMARY.value: "chapters",
            cls.KEY_EVENT.value: "chapters",           # 从章节analysis_data中提取
            cls.CHAPTER_METADATA.value: "chapters",    # 从章节analysis_data中提取
            cls.FORESHADOWING.value: "foreshadowing_index",
        }
        return tables.get(data_type, "unknown")

    @classmethod
    def all_types(cls) -> list:
        """获取所有数据类型列表"""
        return list(cls)


# 蓝图生成时需要入库的类型
BLUEPRINT_INGESTION_TYPES = [
    NovelDataType.SYNOPSIS,
    NovelDataType.WORLD_SETTING,
    NovelDataType.BLUEPRINT_METADATA,
    NovelDataType.CHARACTER,
    NovelDataType.RELATIONSHIP,
]

# 分部大纲生成时需要入库的类型
PART_OUTLINE_INGESTION_TYPES = [
    NovelDataType.PART_OUTLINE,
]

# 章节大纲生成时需要入库的类型
CHAPTER_OUTLINE_INGESTION_TYPES = [
    NovelDataType.CHAPTER_OUTLINE,
]

# 章节版本选择时需要入库的类型
CHAPTER_VERSION_INGESTION_TYPES = [
    NovelDataType.CHAPTER_CONTENT,
    NovelDataType.CHAPTER_SUMMARY,
    NovelDataType.FORESHADOWING,
    NovelDataType.CHARACTER_STATE,
    NovelDataType.KEY_EVENT,           # 新增：章节关键事件
    NovelDataType.CHAPTER_METADATA,    # 新增：章节元数据
]

# 主角档案更新时需要入库的类型
PROTAGONIST_INGESTION_TYPES = [
    NovelDataType.PROTAGONIST,
    NovelDataType.PROTAGONIST_CHANGE,  # 新增：主角属性变更历史
]


__all__ = [
    "NovelDataType",
    "BLUEPRINT_INGESTION_TYPES",
    "PART_OUTLINE_INGESTION_TYPES",
    "CHAPTER_OUTLINE_INGESTION_TYPES",
    "CHAPTER_VERSION_INGESTION_TYPES",
    "PROTAGONIST_INGESTION_TYPES",
]
