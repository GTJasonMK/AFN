"""
章节信息提取器

从章节内容中提取结构化信息，用于漫画分镜设计。

采用分步提取策略避免单次LLM调用输出过大导致JSON被截断：
1. 步骤1：提取角色 + 基础事件
2. 步骤2：提取对话信息
3. 步骤3：提取场景信息
4. 步骤4：提取物品 + 摘要信息
"""

import json
import logging
from typing import Any, Callable, Dict, Optional, Tuple, TYPE_CHECKING

from app.exceptions import JSONParseError
from app.services.llm_wrappers import call_llm_json, LLMProfile
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
    PROMPT_NAME_STEP1,
    PROMPT_NAME_STEP2,
    PROMPT_NAME_STEP3,
    PROMPT_NAME_STEP4,
    CHAPTER_INFO_EXTRACTION_PROMPT,
    EXTRACTION_SYSTEM_PROMPT,
    STEP1_CHARACTERS_EVENTS_PROMPT,
    STEP2_DIALOGUES_PROMPT,
    STEP3_SCENES_PROMPT,
    STEP4_ITEMS_SUMMARY_PROMPT,
    STEP_EXTRACTION_SYSTEM_PROMPT,
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
        从章节内容中提取结构化信息（使用分步提取策略）

        采用分步提取避免单次LLM调用输出过大导致JSON被截断：
        1. 步骤1：提取角色 + 基础事件
        2. 步骤2：提取对话信息
        3. 步骤3：提取场景信息
        4. 步骤4：提取物品 + 摘要信息

        Args:
            chapter_content: 章节内容文本
            user_id: 用户ID（用于LLM调用追踪）
            dialogue_language: 对话语言（chinese/japanese/english/korean）

        Returns:
            ChapterInfo: 包含所有提取信息的结构化数据

        Raises:
            JSONParseError: 当LLM返回的JSON无法解析时
        """
        # 限制内容长度
        content = chapter_content[:self.MAX_CONTENT_LENGTH]
        logger.info("开始分步提取章节信息，内容长度: %d 字符", len(content))

        # 步骤1：提取角色和事件
        logger.info("步骤1/4: 提取角色和事件...")
        step1_data = await self._extract_step1_characters_events(content, user_id)
        characters = step1_data.get("characters", {})
        events = step1_data.get("events", [])
        climax_event_indices = step1_data.get("climax_event_indices", [])
        logger.info("步骤1完成: %d 角色, %d 事件", len(characters), len(events))

        # 步骤2：提取对话
        logger.info("步骤2/4: 提取对话...")
        step2_data = await self._extract_step2_dialogues(
            content, characters, events, user_id
        )
        dialogues = step2_data.get("dialogues", [])
        logger.info("步骤2完成: %d 对话", len(dialogues))

        # 步骤3：提取场景
        logger.info("步骤3/4: 提取场景...")
        step3_data = await self._extract_step3_scenes(content, events, user_id)
        scenes = step3_data.get("scenes", [])
        logger.info("步骤3完成: %d 场景", len(scenes))

        # 步骤4：提取物品和摘要
        logger.info("步骤4/4: 提取物品和摘要...")
        step4_data = await self._extract_step4_items_summary(
            content, len(events), user_id
        )
        items = step4_data.get("items", [])
        chapter_summary = step4_data.get("chapter_summary", "")
        mood_progression = step4_data.get("mood_progression", [])
        total_estimated_pages = step4_data.get("total_estimated_pages", 10)
        logger.info("步骤4完成: %d 物品", len(items))

        # 组合所有数据
        try:
            chapter_info = self._combine_step_results(
                characters=characters,
                events=events,
                dialogues=dialogues,
                scenes=scenes,
                items=items,
                chapter_summary=chapter_summary,
                mood_progression=mood_progression,
                climax_event_indices=climax_event_indices,
                total_estimated_pages=total_estimated_pages,
            )
            logger.info(
                "分步提取完成: %d 角色, %d 对话, %d 场景, %d 事件, %d 物品",
                len(chapter_info.characters),
                len(chapter_info.dialogues),
                len(chapter_info.scenes),
                len(chapter_info.events),
                len(chapter_info.items),
            )
            return chapter_info
        except Exception as e:
            logger.error("组合提取结果失败: %s", e)
            raise JSONParseError(
                context="章节信息提取",
                detail_msg=f"组合提取数据时出错: {str(e)}"
            ) from e

    async def extract_with_checkpoint(
        self,
        chapter_content: str,
        user_id: Optional[int] = None,
        dialogue_language: str = "chinese",
        checkpoint_data: Optional[Dict[str, Any]] = None,
        on_step_complete: Optional[Callable[[int, Dict[str, Any]], None]] = None,
    ) -> Tuple[ChapterInfo, Dict[str, Any]]:
        """
        支持断点恢复的章节信息提取

        每完成一个步骤后调用 on_step_complete 回调，便于保存中间状态。

        Args:
            chapter_content: 章节内容文本
            user_id: 用户ID
            dialogue_language: 对话语言
            checkpoint_data: 已有的断点数据，包含已完成步骤的结果
            on_step_complete: 步骤完成回调 (step_number, updated_checkpoint_data)

        Returns:
            (ChapterInfo, checkpoint_data) 元组
        """
        content = chapter_content[:self.MAX_CONTENT_LENGTH]
        logger.info("开始分步提取章节信息（支持断点），内容长度: %d 字符", len(content))

        # 初始化或恢复断点数据
        cp_data = checkpoint_data.copy() if checkpoint_data else {}

        # 从断点恢复已提取的数据
        step1_data = cp_data.get("extraction_step1")
        step2_data = cp_data.get("extraction_step2")
        step3_data = cp_data.get("extraction_step3")
        step4_data = cp_data.get("extraction_step4")

        # 步骤1：提取角色和事件
        if not step1_data:
            logger.info("步骤1/4: 提取角色和事件...")
            step1_data = await self._extract_step1_characters_events(content, user_id)
            cp_data["extraction_step1"] = step1_data
            logger.info(
                "步骤1完成: %d 角色, %d 事件",
                len(step1_data.get("characters", {})),
                len(step1_data.get("events", []))
            )
            if on_step_complete:
                await self._safe_callback(on_step_complete, 1, cp_data)
        else:
            logger.info("步骤1已从断点恢复，跳过")

        characters = step1_data.get("characters", {})
        events = step1_data.get("events", [])
        climax_event_indices = step1_data.get("climax_event_indices", [])

        # 步骤2：提取对话
        if not step2_data:
            logger.info("步骤2/4: 提取对话...")
            step2_data = await self._extract_step2_dialogues(
                content, characters, events, user_id
            )
            cp_data["extraction_step2"] = step2_data
            logger.info("步骤2完成: %d 对话", len(step2_data.get("dialogues", [])))
            if on_step_complete:
                await self._safe_callback(on_step_complete, 2, cp_data)
        else:
            logger.info("步骤2已从断点恢复，跳过")

        dialogues = step2_data.get("dialogues", [])

        # 步骤3：提取场景
        if not step3_data:
            logger.info("步骤3/4: 提取场景...")
            step3_data = await self._extract_step3_scenes(content, events, user_id)
            cp_data["extraction_step3"] = step3_data
            logger.info("步骤3完成: %d 场景", len(step3_data.get("scenes", [])))
            if on_step_complete:
                await self._safe_callback(on_step_complete, 3, cp_data)
        else:
            logger.info("步骤3已从断点恢复，跳过")

        scenes = step3_data.get("scenes", [])

        # 步骤4：提取物品和摘要
        if not step4_data:
            logger.info("步骤4/4: 提取物品和摘要...")
            step4_data = await self._extract_step4_items_summary(
                content, len(events), user_id
            )
            cp_data["extraction_step4"] = step4_data
            logger.info("步骤4完成: %d 物品", len(step4_data.get("items", [])))
            if on_step_complete:
                await self._safe_callback(on_step_complete, 4, cp_data)
        else:
            logger.info("步骤4已从断点恢复，跳过")

        items = step4_data.get("items", [])
        chapter_summary = step4_data.get("chapter_summary", "")
        mood_progression = step4_data.get("mood_progression", [])
        total_estimated_pages = step4_data.get("total_estimated_pages", 10)

        # 组合所有数据
        try:
            chapter_info = self._combine_step_results(
                characters=characters,
                events=events,
                dialogues=dialogues,
                scenes=scenes,
                items=items,
                chapter_summary=chapter_summary,
                mood_progression=mood_progression,
                climax_event_indices=climax_event_indices,
                total_estimated_pages=total_estimated_pages,
            )

            # 保存完整的 chapter_info 到断点数据
            cp_data["chapter_info"] = chapter_info.to_dict()

            logger.info(
                "分步提取完成: %d 角色, %d 对话, %d 场景, %d 事件, %d 物品",
                len(chapter_info.characters),
                len(chapter_info.dialogues),
                len(chapter_info.scenes),
                len(chapter_info.events),
                len(chapter_info.items),
            )
            return chapter_info, cp_data

        except Exception as e:
            logger.error("组合提取结果失败: %s", e)
            raise JSONParseError(
                context="章节信息提取",
                detail_msg=f"组合提取数据时出错: {str(e)}"
            ) from e

    async def _safe_callback(
        self,
        callback: Callable,
        step: int,
        data: Dict[str, Any]
    ) -> None:
        """安全执行回调，支持同步和异步回调"""
        import asyncio
        try:
            result = callback(step, data)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            logger.warning("步骤%d完成回调执行失败: %s", step, e)

    async def _extract_step1_characters_events(
        self,
        content: str,
        user_id: Optional[int] = None,
    ) -> dict:
        """步骤1：提取角色和事件"""
        # 尝试从 PromptService 加载，失败则使用内置模板
        prompt_template = await self._get_step_prompt(
            PROMPT_NAME_STEP1, STEP1_CHARACTERS_EVENTS_PROMPT
        )
        prompt = prompt_template.format(content=content)

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=STEP_EXTRACTION_SYSTEM_PROMPT,
            user_content=prompt,
            user_id=user_id,
        )

        data = parse_llm_json_safe(response)
        if not data:
            error_preview = response[:200] if response else "(empty)"
            logger.error(
                "步骤1提取失败: 角色和事件。响应长度: %d, 预览: %s",
                len(response) if response else 0,
                error_preview
            )
            raise JSONParseError(
                context="章节信息提取-步骤1(角色和事件)",
                detail_msg="AI返回的数据格式错误，请重试。"
            )
        return data

    async def _extract_step2_dialogues(
        self,
        content: str,
        characters: dict,
        events: list,
        user_id: Optional[int] = None,
    ) -> dict:
        """步骤2：提取对话"""
        # 准备上下文信息
        characters_json = json.dumps(
            list(characters.keys()),
            ensure_ascii=False
        )
        events_json = json.dumps(
            [{"index": e.get("index", i), "description": e.get("description", "")}
             for i, e in enumerate(events)],
            ensure_ascii=False,
            indent=2
        )

        # 尝试从 PromptService 加载，失败则使用内置模板
        prompt_template = await self._get_step_prompt(
            PROMPT_NAME_STEP2, STEP2_DIALOGUES_PROMPT
        )
        prompt = prompt_template.format(
            content=content,
            characters_json=characters_json,
            events_json=events_json,
        )

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=STEP_EXTRACTION_SYSTEM_PROMPT,
            user_content=prompt,
            user_id=user_id,
        )

        data = parse_llm_json_safe(response)
        if not data:
            error_preview = response[:200] if response else "(empty)"
            logger.error(
                "步骤2提取失败: 对话。响应长度: %d, 预览: %s",
                len(response) if response else 0,
                error_preview
            )
            raise JSONParseError(
                context="章节信息提取-步骤2(对话)",
                detail_msg="AI返回的数据格式错误，请重试。"
            )
        return data

    async def _extract_step3_scenes(
        self,
        content: str,
        events: list,
        user_id: Optional[int] = None,
    ) -> dict:
        """步骤3：提取场景"""
        events_json = json.dumps(
            [{"index": e.get("index", i), "description": e.get("description", "")}
             for i, e in enumerate(events)],
            ensure_ascii=False,
            indent=2
        )

        # 尝试从 PromptService 加载，失败则使用内置模板
        prompt_template = await self._get_step_prompt(
            PROMPT_NAME_STEP3, STEP3_SCENES_PROMPT
        )
        prompt = prompt_template.format(
            content=content,
            events_json=events_json,
        )

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=STEP_EXTRACTION_SYSTEM_PROMPT,
            user_content=prompt,
            user_id=user_id,
        )

        data = parse_llm_json_safe(response)
        if not data:
            error_preview = response[:200] if response else "(empty)"
            logger.error(
                "步骤3提取失败: 场景。响应长度: %d, 预览: %s",
                len(response) if response else 0,
                error_preview
            )
            raise JSONParseError(
                context="章节信息提取-步骤3(场景)",
                detail_msg="AI返回的数据格式错误，请重试。"
            )
        return data

    async def _extract_step4_items_summary(
        self,
        content: str,
        event_count: int,
        user_id: Optional[int] = None,
    ) -> dict:
        """步骤4：提取物品和摘要"""
        # 尝试从 PromptService 加载，失败则使用内置模板
        prompt_template = await self._get_step_prompt(
            PROMPT_NAME_STEP4, STEP4_ITEMS_SUMMARY_PROMPT
        )
        prompt = prompt_template.format(
            content=content,
            event_count=event_count,
        )

        response = await call_llm_json(
            self.llm_service,
            LLMProfile.ANALYTICAL,
            system_prompt=STEP_EXTRACTION_SYSTEM_PROMPT,
            user_content=prompt,
            user_id=user_id,
        )

        data = parse_llm_json_safe(response)
        if not data:
            error_preview = response[:200] if response else "(empty)"
            logger.error(
                "步骤4提取失败: 物品和摘要。响应长度: %d, 预览: %s",
                len(response) if response else 0,
                error_preview
            )
            raise JSONParseError(
                context="章节信息提取-步骤4(物品和摘要)",
                detail_msg="AI返回的数据格式错误，请重试。"
            )
        return data

    async def _get_step_prompt(
        self,
        prompt_name: str,
        fallback_template: str,
    ) -> str:
        """
        获取分步提取的提示词模板

        优先从 PromptService 加载用户自定义提示词，
        加载失败时回退到内置模板。

        Args:
            prompt_name: 提示词注册名称
            fallback_template: 内置的回退模板

        Returns:
            提示词模板字符串
        """
        if self.prompt_service:
            try:
                prompt_content = await self.prompt_service.get_prompt(prompt_name)
                if prompt_content:
                    logger.debug("从 PromptService 加载提示词: %s", prompt_name)
                    return prompt_content
            except Exception as e:
                logger.warning(
                    "无法从 PromptService 加载 %s 提示词: %s，使用内置模板",
                    prompt_name, e
                )
        return fallback_template

    def _combine_step_results(
        self,
        characters: dict,
        events: list,
        dialogues: list,
        scenes: list,
        items: list,
        chapter_summary: str,
        mood_progression: list,
        climax_event_indices: list,
        total_estimated_pages: int,
    ) -> ChapterInfo:
        """组合所有步骤的结果为 ChapterInfo 对象"""
        # 解析角色信息
        parsed_characters = {}
        for name, char_data in characters.items():
            if isinstance(char_data, dict):
                parsed_characters[name] = CharacterInfo.from_dict(char_data)
            elif isinstance(char_data, str):
                parsed_characters[name] = CharacterInfo(name=name, appearance=char_data)

        # 解析事件信息
        parsed_events = []
        for e in events:
            if isinstance(e, dict):
                parsed_events.append(EventInfo.from_dict(e))

        # 解析对话信息
        parsed_dialogues = []
        for d in dialogues:
            if isinstance(d, dict):
                parsed_dialogues.append(DialogueInfo.from_dict(d))

        # 解析场景信息
        parsed_scenes = []
        for s in scenes:
            if isinstance(s, dict):
                parsed_scenes.append(SceneInfo.from_dict(s))

        # 解析物品信息
        parsed_items = []
        for i in items:
            if isinstance(i, dict):
                parsed_items.append(ItemInfo.from_dict(i))

        return ChapterInfo(
            characters=parsed_characters,
            dialogues=parsed_dialogues,
            scenes=parsed_scenes,
            events=parsed_events,
            items=parsed_items,
            chapter_summary=chapter_summary,
            mood_progression=mood_progression,
            climax_event_indices=climax_event_indices,
            total_estimated_pages=total_estimated_pages,
        )

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
                participants=[],
                scene_index=0,
                importance=ImportanceLevel.NORMAL,
            ))

        # 创建一个默认场景
        scenes = [SceneInfo(
            index=0,
            location="未知地点",
            event_indices=list(range(len(events))),
        )]

        return ChapterInfo(
            characters={},
            dialogues=[],
            scenes=scenes,
            events=events,
            items=[],
            chapter_summary="信息提取失败，使用回退模式",
            mood_progression=[],
            climax_event_indices=[],
            total_estimated_pages=max(5, len(events) // 2),
        )


__all__ = [
    "ChapterInfoExtractor",
]
