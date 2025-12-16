"""
章节分析服务

负责对已生成的章节内容进行深度分析，提取元数据、摘要、角色状态、伏笔和关键事件等信息。
分析结果用于优化后续章节生成时的上下文构建。
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..schemas.novel import ChapterAnalysisData
from ..services.llm_service import LLMService
from ..services.llm_wrappers import call_llm_json, LLMProfile
from ..services.prompt_service import PromptService
from ..utils.json_utils import parse_llm_json_safe, remove_think_tags

logger = logging.getLogger(__name__)


class ChapterAnalysisService:
    """
    章节分析服务

    提供章节内容的深度分析能力，提取结构化信息用于RAG和后续章节生成。

    职责：
    - 调用LLM分析章节内容
    - 解析分析结果为结构化数据
    - 提供分析数据的验证和默认值处理

    Example:
        ```python
        analysis_service = ChapterAnalysisService(session)
        analysis_data = await analysis_service.analyze_chapter(
            content="章节正文...",
            title="第一章 初始",
            chapter_number=1,
            novel_title="示例小说",
            user_id=1,
        )
        if analysis_data:
            chapter.analysis_data = analysis_data.model_dump()
        ```
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm_service = LLMService(session)
        self.prompt_service = PromptService(session)

    async def analyze_chapter(
        self,
        content: str,
        title: str,
        chapter_number: int,
        novel_title: str,
        user_id: Optional[int] = None,
        timeout: float = 300.0,
    ) -> Optional[ChapterAnalysisData]:
        """
        分析章节内容，提取结构化信息

        Args:
            content: 章节正文内容
            title: 章节标题
            chapter_number: 章节号
            novel_title: 小说标题
            user_id: 用户ID（用于LLM配置）
            timeout: 超时时间（秒）

        Returns:
            ChapterAnalysisData: 分析结果，失败返回None
        """
        if not content or not content.strip():
            logger.warning(
                "章节内容为空，跳过分析: novel=%s chapter=%d",
                novel_title,
                chapter_number,
            )
            return None

        # 获取分析提示词
        system_prompt = await self.prompt_service.get_prompt("chapter_analysis")
        if not system_prompt:
            logger.error("未找到chapter_analysis提示词，跳过章节分析")
            return None

        # 构建用户消息，替换模板变量
        user_message = f"""小说标题: {novel_title}
当前章节: 第{chapter_number}章 {title}
章节内容:
{content}"""

        try:
            logger.info(
                "开始分析章节: novel=%s chapter=%d title=%s",
                novel_title,
                chapter_number,
                title,
            )

            # 调用LLM进行分析
            response = await call_llm_json(
                self.llm_service,
                LLMProfile.SUMMARY,
                system_prompt=system_prompt,
                user_content=user_message,
                user_id=user_id or 0,
                timeout_override=timeout,
            )

            # 解析JSON响应
            cleaned = remove_think_tags(response)
            data = parse_llm_json_safe(cleaned)

            if not data:
                logger.error(
                    "章节分析JSON解析失败: novel=%s chapter=%d",
                    novel_title,
                    chapter_number,
                )
                return None

            # 验证并转换为Pydantic模型
            try:
                analysis_data = ChapterAnalysisData.model_validate(data)
                logger.info(
                    "章节分析完成: novel=%s chapter=%d characters=%d events=%d",
                    novel_title,
                    chapter_number,
                    len(analysis_data.metadata.characters) if analysis_data.metadata else 0,
                    len(analysis_data.key_events),
                )
                return analysis_data
            except (ValueError, TypeError, KeyError) as exc:
                # Pydantic验证失败，尝试宽松模式
                logger.warning(
                    "章节分析数据验证失败，尝试宽松解析: novel=%s chapter=%d error=%s",
                    novel_title,
                    chapter_number,
                    exc,
                )
                # 尝试使用宽松模式创建部分数据
                return self._create_partial_analysis(data)

        except Exception as exc:
            logger.error(
                "章节分析失败: novel=%s chapter=%d error=%s",
                novel_title,
                chapter_number,
                exc,
                exc_info=True,
            )
            return None

    def _create_partial_analysis(self, data: dict) -> Optional[ChapterAnalysisData]:
        """
        从不完整的数据创建部分分析结果

        当LLM返回的数据不完全符合schema时，尝试提取可用部分。

        Args:
            data: 原始数据字典

        Returns:
            ChapterAnalysisData: 部分分析结果，完全失败返回None
        """
        try:
            # 使用默认值填充缺失字段
            return ChapterAnalysisData(
                metadata=data.get("metadata"),
                summaries=data.get("summaries"),
                character_states=data.get("character_states", {}),
                foreshadowing=data.get("foreshadowing"),
                key_events=data.get("key_events", []),
            )
        except Exception as exc:
            logger.warning("创建部分分析数据失败: %s", exc)
            return None
