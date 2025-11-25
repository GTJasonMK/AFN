"""
数据模型（可选）
用于类型提示和数据验证
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .project_status import ProjectStatus


@dataclass
class NovelProject:
    """小说项目数据模型"""
    id: str
    title: str
    initial_prompt: str
    status: str
    created_at: datetime
    updated_at: datetime
    blueprint: Optional[Dict[str, Any]] = None
    conversations: List[Dict[str, str]] = None
    chapters: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.conversations is None:
            self.conversations = []
        if self.chapters is None:
            self.chapters = []


@dataclass
class Blueprint:
    """蓝图数据模型"""
    title: str
    theme: str
    core_conflict: str
    story_summary: str
    world_settings: Dict[str, Any]
    characters: List[Dict[str, Any]]
    chapters: List[Dict[str, Any]]


@dataclass
class Chapter:
    """章节数据模型"""
    chapter_number: int
    selected_content: Optional[str] = None
    versions: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.versions is None:
            self.versions = []


@dataclass
class ChapterVersion:
    """章节版本数据模型"""
    content: str
    is_selected: bool = False
    evaluation: Optional[str] = None


@dataclass
class LLMConfig:
    """LLM配置数据模型"""
    id: int
    name: str
    api_key: str
    base_url: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4000
    is_active: bool = False
