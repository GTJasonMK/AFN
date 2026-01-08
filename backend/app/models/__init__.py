"""集中导出 ORM 模型，确保 SQLAlchemy 元数据在初始化时被正确加载。"""

# 注意：导入顺序很重要！被其他模型外键引用的模型必须先导入
from .novel import (
    BlueprintCharacter,
    BlueprintRelationship,
    Chapter,
    ChapterEvaluation,
    ChapterMangaPrompt,
    ChapterOutline,
    ChapterVersion,
    CharacterStateIndex,
    ForeshadowingIndex,
    NovelBlueprint,
    NovelConversation,
    NovelProject,
)
from .coding import (
    CodingProject,
    CodingConversation,
    CodingBlueprint,
    CodingSystem,
    CodingModule,
    CodingFeature,
    CodingFeatureVersion,
)
from .character_portrait import CharacterPortrait
from .embedding_config import EmbeddingConfig
from .image_config import ImageGenerationConfig, GeneratedImage
from .llm_config import LLMConfig
from .part_outline import PartOutline
from .prompt import Prompt
from .protagonist import (
    ProtagonistProfile,
    ProtagonistAttributeChange,
    ProtagonistBehaviorRecord,
    ProtagonistDeletionMark,
)
from .theme_config import ThemeConfig
from .user import User

__all__ = [
    # Novel models
    "CharacterPortrait",
    "EmbeddingConfig",
    "GeneratedImage",
    "ImageGenerationConfig",
    "LLMConfig",
    "NovelConversation",
    "NovelBlueprint",
    "BlueprintCharacter",
    "BlueprintRelationship",
    "ChapterOutline",
    "Chapter",
    "ChapterMangaPrompt",
    "ChapterVersion",
    "ChapterEvaluation",
    "CharacterStateIndex",
    "ForeshadowingIndex",
    "NovelProject",
    "PartOutline",
    "Prompt",
    "ProtagonistProfile",
    "ProtagonistAttributeChange",
    "ProtagonistBehaviorRecord",
    "ProtagonistDeletionMark",
    "ThemeConfig",
    "User",
    # Coding models
    "CodingProject",
    "CodingConversation",
    "CodingBlueprint",
    "CodingSystem",
    "CodingModule",
    "CodingFeature",
    "CodingFeatureVersion",
]
