"""
章节信息提取器

从章节内容中提取结构化信息，用于漫画分镜设计。
"""

import logging
from typing import Optional, TYPE_CHECKING

from app.services.llm_wrappers import call_llm, LLMProfile
from app.utils.json_utils import parse_llm_json_safe

from .models import (
    ChapterInfo,
    CharacterInfo,
    DialogueInfo,
    SceneInfo,
    EventInfo,
    ItemInfo,
    CharacterRole,
    ImportanceLevel,
    EmotionType,
    EventType,
)
from .prompts import (
    PROMPT_NAME,
    CHAPTER_INFO_EXTRACTION_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
)

if TYPE_CHECKING:
    from app.services.prompt_service import PromptService
    from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ChapterInfoExtractor:
    """
    章节信息提取器

    从章节内容中提取结构化信息，包括：
    - 人物信息（外观/性格/关系）
    - 对话信息（说话人/内容/情绪）
    - 场景信息（地点/时间/氛围）
    - 事件信息（动作/冲突/转折）
    - 物品信息（关键道具/环境元素）
    """

    # 内容长度限制（字符数）
    MAX_CONTENT_LENGTH = 12000

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_service: Optional["PromptService"] = None,
    ):
        """
        初始化提取器

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例（可选，用于加载可配置提示词）
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def extract(
        self,
        chapter_content: str,
        user_id: Optional[int] = None,
        dialogue_language: str = "chinese",
    ) -> ChapterInfo:
        """
        从章节内容中提取结构化信息

        Args:
            chapter_content: 章节内容文本
            user_id: 用户ID（用于LLM调用追踪）
            dialogue_language: 对话语言（chinese/japanese/english/korean）

        Returns:
            ChapterInfo: 包含所有提取信息的结构化数据
        """
        # 限制内容长度
        content = chapter_content[:self.MAX_CONTENT_LENGTH]

        # 构建提示词
        prompt = await self._build_prompt(content)

        # 获取系统提示词
        system_prompt = await self._get_system_prompt()

        # 调用LLM
        logger.info("开始提取章节信息，内容长度: %d 字符", len(content))
        response = await call_llm(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=system_prompt,
            user_content=prompt,
            user_id=user_id,
        )

        # 解析响应
        data = parse_llm_json_safe(response)

        if not data:
            logger.warning("章节信息提取失败，LLM返回无法解析的内容")
            return self._create_fallback_chapter_info(content)

        # 转换为ChapterInfo对象
        try:
            chapter_info = self._parse_chapter_info(data)
            logger.info(
                "章节信息提取成功: %d 角色, %d 对话, %d 场景, %d 事件, %d 物品",
                len(chapter_info.characters),
                len(chapter_info.dialogues),
                len(chapter_info.scenes),
                len(chapter_info.events),
                len(chapter_info.items),
            )
            return chapter_info
        except Exception as e:
            logger.error("解析提取结果失败: %s", e)
            return self._create_fallback_chapter_info(content)

    async def _build_prompt(self, content: str) -> str:
        """
        构建提取提示词

        Args:
            content: 章节内容

        Returns:
            格式化后的提示词
        """
        # 尝试从PromptService加载可配置提示词
        prompt_template = None
        if self.prompt_service:
            try:
                prompt_template = await self.prompt_service.get_prompt(PROMPT_NAME)
            except Exception as e:
                logger.warning("无法加载 %s 提示词: %s", PROMPT_NAME, e)

        # 使用内置提示词作为回退
        if not prompt_template:
            prompt_template = CHAPTER_INFO_EXTRACTION_PROMPT

        return prompt_template.format(content=content)

    async def _get_system_prompt(self) -> str:
        """
        获取系统提示词

        Returns:
            系统提示词
        """
        # 暂时使用内置系统提示词
        # 未来可扩展为从PromptService加载
        return EXTRACTION_SYSTEM_PROMPT

    def _parse_chapter_info(self, data: dict) -> ChapterInfo:
        """
        将LLM返回的字典解析为ChapterInfo对象

        Args:
            data: LLM返回的原始字典

        Returns:
            ChapterInfo对象
        """
        # 解析角色信息
        characters = {}
        raw_characters = data.get("characters", {})
        for name, char_data in raw_characters.items():
            if isinstance(char_data, dict):
                characters[name] = CharacterInfo.from_dict(char_data)
            elif isinstance(char_data, str):
                # 兼容简单格式：只有外观描述
                characters[name] = CharacterInfo(name=name, appearance=char_data)

        # 解析对话信息
        dialogues = []
        for d in data.get("dialogues", []):
            if isinstance(d, dict):
                dialogues.append(DialogueInfo.from_dict(d))

        # 解析场景信息
        scenes = []
        for s in data.get("scenes", []):
            if isinstance(s, dict):
                scenes.append(SceneInfo.from_dict(s))

        # 解析事件信息
        events = []
        for e in data.get("events", []):
            if isinstance(e, dict):
                events.append(EventInfo.from_dict(e))

        # 解析物品信息
        items = []
        for i in data.get("items", []):
            if isinstance(i, dict):
                items.append(ItemInfo.from_dict(i))

        return ChapterInfo(
            characters=characters,
            dialogues=dialogues,
            scenes=scenes,
            events=events,
            items=items,
            chapter_summary=data.get("chapter_summary", ""),
            chapter_summary_en=data.get("chapter_summary_en", ""),
            mood_progression=data.get("mood_progression", []),
            climax_event_indices=data.get("climax_event_indices", []),
            total_estimated_pages=data.get("total_estimated_pages", 0),
        )

    def _create_fallback_chapter_info(self, content: str) -> ChapterInfo:
        """
        创建回退的章节信息（当LLM提取失败时）

        Args:
            content: 章节内容

        Returns:
            基本的ChapterInfo对象
        """
        # 简单分段作为事件
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        events = []
        for i, para in enumerate(paragraphs[:10]):  # 最多10个事件
            events.append(EventInfo(
                index=i,
                type=EventType.DESCRIPTION,
                description=para[:100] + "..." if len(para) > 100 else para,
                description_en="",
                participants=[],
                scene_index=0,
                importance=ImportanceLevel.NORMAL,
            ))

        # 创建一个默认场景
        scenes = [SceneInfo(
            index=0,
            location="未知地点",
            location_en="Unknown location",
            event_indices=list(range(len(events))),
        )]

        return ChapterInfo(
            characters={},
            dialogues=[],
            scenes=scenes,
            events=events,
            items=[],
            chapter_summary="信息提取失败，使用回退模式",
            chapter_summary_en="Extraction failed, using fallback mode",
            mood_progression=[],
            climax_event_indices=[],
            total_estimated_pages=max(5, len(events) // 2),
        )


__all__ = [
    "ChapterInfoExtractor",
]
