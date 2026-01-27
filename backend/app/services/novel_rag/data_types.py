"""
小说项目RAG数据类型定义

定义15种需要入库的数据类型及其检索权重。
"""

from enum import Enum
from ..rag_common.data_type_mixin import RAGDataTypeMixin


class NovelDataType(RAGDataTypeMixin, str, Enum):
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


NovelDataType.WEIGHTS = {
    NovelDataType.SYNOPSIS.value: 1.0,              # 最高：故事核心
    NovelDataType.BLUEPRINT_METADATA.value: 0.98,   # 蓝图元数据(标题、体裁、风格)
    NovelDataType.WORLD_SETTING.value: 0.95,        # 世界观约束
    NovelDataType.CHARACTER.value: 0.9,             # 角色设定
    NovelDataType.KEY_EVENT.value: 0.88,            # 关键事件（高优先级，情节驱动）
    NovelDataType.CHAPTER_CONTENT.value: 0.85,      # 章节正文
    NovelDataType.CHAPTER_SUMMARY.value: 0.8,       # 章节摘要
    NovelDataType.CHAPTER_OUTLINE.value: 0.75,      # 章节大纲
    NovelDataType.CHAPTER_METADATA.value: 0.72,     # 章节元数据（地点、物品、标签）
    NovelDataType.PART_OUTLINE.value: 0.7,          # 分部大纲
    NovelDataType.FORESHADOWING.value: 0.65,        # 伏笔
    NovelDataType.RELATIONSHIP.value: 0.6,          # 角色关系
    NovelDataType.CHARACTER_STATE.value: 0.55,      # 角色状态
    NovelDataType.PROTAGONIST.value: 0.5,           # 主角档案
    NovelDataType.PROTAGONIST_CHANGE.value: 0.48,   # 主角属性变更历史
    NovelDataType.INSPIRATION.value: 0.4,           # 灵感对话（最低）
}

NovelDataType.DISPLAY_NAMES = {
    NovelDataType.INSPIRATION.value: "灵感对话",
    NovelDataType.SYNOPSIS.value: "故事概述",
    NovelDataType.WORLD_SETTING.value: "世界观设定",
    NovelDataType.BLUEPRINT_METADATA.value: "蓝图元数据",
    NovelDataType.CHARACTER.value: "角色设定",
    NovelDataType.RELATIONSHIP.value: "角色关系",
    NovelDataType.CHARACTER_STATE.value: "角色状态",
    NovelDataType.PROTAGONIST.value: "主角档案",
    NovelDataType.PROTAGONIST_CHANGE.value: "主角属性变更",
    NovelDataType.PART_OUTLINE.value: "分部大纲",
    NovelDataType.CHAPTER_OUTLINE.value: "章节大纲",
    NovelDataType.CHAPTER_CONTENT.value: "章节正文",
    NovelDataType.CHAPTER_SUMMARY.value: "章节摘要",
    NovelDataType.KEY_EVENT.value: "关键事件",
    NovelDataType.CHAPTER_METADATA.value: "章节元数据",
    NovelDataType.FORESHADOWING.value: "伏笔记录",
}

NovelDataType.SOURCE_TABLES = {
    NovelDataType.INSPIRATION.value: "novel_conversations",
    NovelDataType.SYNOPSIS.value: "novel_blueprints",
    NovelDataType.WORLD_SETTING.value: "novel_blueprints",
    NovelDataType.BLUEPRINT_METADATA.value: "novel_blueprints",
    NovelDataType.CHARACTER.value: "blueprint_characters",
    NovelDataType.RELATIONSHIP.value: "blueprint_relationships",
    NovelDataType.CHARACTER_STATE.value: "character_state_index",
    NovelDataType.PROTAGONIST.value: "protagonist_profiles",
    NovelDataType.PROTAGONIST_CHANGE.value: "protagonist_attribute_changes",
    NovelDataType.PART_OUTLINE.value: "part_outlines",
    NovelDataType.CHAPTER_OUTLINE.value: "chapter_outlines",
    NovelDataType.CHAPTER_CONTENT.value: "chapter_versions",
    NovelDataType.CHAPTER_SUMMARY.value: "chapters",
    NovelDataType.KEY_EVENT.value: "chapters",           # 从章节analysis_data中提取
    NovelDataType.CHAPTER_METADATA.value: "chapters",    # 从章节analysis_data中提取
    NovelDataType.FORESHADOWING.value: "foreshadowing_index",
}

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
