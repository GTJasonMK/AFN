"""
蓝图管理服务

负责小说项目蓝图的创建、更新、清理等核心业务逻辑。
"""

import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.constants import NovelConstants
from ..models.novel import NovelProject
from ..repositories.blueprint_repository import (
    BlueprintCharacterRepository,
    BlueprintRelationshipRepository,
    NovelBlueprintRepository,
)
from ..repositories.chapter_repository import ChapterOutlineRepository, ChapterRepository
from ..repositories.part_outline_repository import PartOutlineRepository
from ..schemas.novel import Blueprint
from ..services.llm_service import LLMService
from ..services.vector_store_service import VectorStoreService
from ..services.chapter_ingest_service import ChapterIngestionService
from ..utils.json_utils import parse_llm_json_safe
from ..utils.exception_helpers import log_exception

logger = logging.getLogger(__name__)


class BlueprintService:
    """
    蓝图管理服务

    负责蓝图的创建、更新、优化和相关数据的清理。
    """

    def __init__(self, session: AsyncSession):
        """
        初始化BlueprintService

        Args:
            session: 数据库会话
        """
        self.session = session
        self.blueprint_repo = NovelBlueprintRepository(session)
        self.character_repo = BlueprintCharacterRepository(session)
        self.relationship_repo = BlueprintRelationshipRepository(session)
        self.chapter_outline_repo = ChapterOutlineRepository(session)
        self.part_outline_repo = PartOutlineRepository(session)
        self.chapter_repo = ChapterRepository(session)

    async def replace_blueprint(self, project_id: str, blueprint: Blueprint) -> None:
        """
        替换项目的完整蓝图数据

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID
            blueprint: 蓝图数据对象
        """
        # 构建蓝图数据字典
        blueprint_data = {
            "title": blueprint.title,
            "target_audience": blueprint.target_audience,
            "genre": blueprint.genre,
            "style": blueprint.style,
            "tone": blueprint.tone,
            "one_sentence_summary": blueprint.one_sentence_summary,
            "full_synopsis": blueprint.full_synopsis,
            "world_setting": blueprint.world_setting,
            "needs_part_outlines": blueprint.needs_part_outlines,
            "total_chapters": blueprint.total_chapters,
            "chapters_per_part": blueprint.chapters_per_part,
        }

        # 使用Repository创建或更新蓝图
        await self.blueprint_repo.create_or_update(project_id, blueprint_data)

        # 替换关联数据（角色、关系、章节大纲）
        await self._replace_blueprint_characters(project_id, blueprint.characters)
        await self._replace_blueprint_relationships(project_id, blueprint.relationships)
        await self._replace_chapter_outlines(project_id, blueprint.chapter_outline)

    async def patch_blueprint(self, project_id: str, patch: Dict) -> None:
        """
        部分更新蓝图数据

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project_id: 项目ID
            patch: 要更新的字段字典
        """
        # 获取现有蓝图（如果不存在会创建）
        blueprint = await self.blueprint_repo.get_by_project_id(project_id)

        # 构建更新数据字典（只包含patch中的字段）
        blueprint_data = {}

        if "one_sentence_summary" in patch:
            blueprint_data["one_sentence_summary"] = patch["one_sentence_summary"]
        if "full_synopsis" in patch:
            blueprint_data["full_synopsis"] = patch["full_synopsis"]

        # world_setting需要特殊处理：merge而不是替换
        if "world_setting" in patch and patch["world_setting"] is not None:
            existing = blueprint.world_setting if blueprint else {}
            existing = existing or {}
            existing.update(patch["world_setting"])
            blueprint_data["world_setting"] = existing

        # 更新蓝图主表字段（如果有）
        if blueprint_data:
            await self.blueprint_repo.create_or_update(project_id, blueprint_data)

        # 更新关联表数据
        if "characters" in patch and patch["characters"] is not None:
            await self._replace_blueprint_characters(project_id, patch["characters"])
        if "relationships" in patch and patch["relationships"] is not None:
            await self._replace_blueprint_relationships(project_id, patch["relationships"])
        if "chapter_outline" in patch and patch["chapter_outline"] is not None:
            await self._replace_chapter_outlines(project_id, patch["chapter_outline"])

    async def cleanup_old_blueprint_data(
        self,
        project: NovelProject,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        """
        清理旧的蓝图相关数据（部分大纲、章节、向量库）

        当重新生成蓝图时，需要清理所有依赖旧蓝图的数据。

        注意：此方法不commit，调用方需要在适当时候commit

        Args:
            project: 项目对象
            llm_service: LLM服务（用于初始化向量库清理）
        """
        project_id = project.id

        # 1. 删除所有部分大纲（PartOutline）
        # 不依赖 project.part_outlines 属性（可能未加载），直接调用 repository 删除
        # 先获取数量用于日志
        existing_parts = await self.part_outline_repo.get_by_project_id(project_id)
        if existing_parts:
            await self.part_outline_repo.delete_by_project_id(project_id)
            logger.info("项目 %s 重新生成蓝图，清除 %d 个部分大纲", project_id, len(existing_parts))

        # 2. 删除所有已生成的章节（Chapter）
        # 不依赖 project.chapters 属性（可能未加载），直接查询数据库
        from sqlalchemy import delete, select, func
        from ..models.novel import Chapter

        # 查询该项目的所有章节号
        stmt = select(Chapter.chapter_number).where(Chapter.project_id == project_id)
        result = await self.session.execute(stmt)
        chapter_numbers = [row[0] for row in result.fetchall()]

        if chapter_numbers:
            logger.info("项目 %s 重新生成蓝图，清除 %d 个已生成章节", project_id, len(chapter_numbers))

            # 删除章节记录
            await self.session.execute(
                delete(Chapter).where(Chapter.project_id == project_id)
            )

            # 同步清理向量库
            if settings.vector_store_enabled and llm_service:
                try:
                    vector_store = VectorStoreService()
                    ingestion_service = ChapterIngestionService(
                        llm_service=llm_service,
                        vector_store=vector_store
                    )
                    await ingestion_service.delete_chapters(project_id, chapter_numbers)
                    logger.info("项目 %s 已从向量库移除 %d 个章节", project_id, len(chapter_numbers))
                except Exception as exc:
                    # 区分向量库不可用和其他错误
                    error_msg = str(exc)
                    if "not enabled" in error_msg.lower() or "not configured" in error_msg.lower():
                        logger.info("向量库未启用，跳过向量数据清理")
                    else:
                        # 向量库删除失败不应阻止主流程，记录详细警告
                        log_exception(
                            exc,
                            "清理向量库数据",
                            level="warning",
                            include_traceback=True,
                            project_id=project_id,
                            chapter_count=len(chapter_numbers),
                            note="数据库记录已删除，但向量数据可能残留，建议手动清理"
                        )

        # 3. 删除所有章节大纲（可能存在大纲但没有章节内容的情况）
        try:
            outline_count = await self.chapter_outline_repo.count_by_project(project_id)
            if outline_count > 0:
                logger.info("项目 %s 准备删除 %d 个章节大纲", project_id, outline_count)
                await self.chapter_outline_repo.delete_by_project(project_id)
                logger.info("项目 %s 重新生成蓝图，已清除 %d 个章节大纲", project_id, outline_count)
        except Exception as exc:
            log_exception(
                exc,
                "删除章节大纲",
                level="error",
                project_id=project_id,
                outline_count=outline_count if 'outline_count' in locals() else 0
            )

        # 4. 使 project 对象的关系缓存失效，确保后续查询获取最新数据
        # 这非常重要：如果不刷新，ORM 可能返回缓存的旧数据
        await self.session.refresh(project, ['part_outlines', 'chapters', 'outlines'])
        logger.info("项目 %s 数据清理完成，ORM 缓存已刷新", project_id)

    def extract_total_chapters(
        self,
        blueprint_total: Optional[int],
        history_records: List[Any],
        formatted_history: List[Dict[str, str]],
        project_id: str,
    ) -> int:
        """
        从蓝图、对话历史中提取章节数，或计算默认值

        优先级策略：
        1. 如果blueprint_total有效（5-10000范围），直接使用
        2. 从conversation_state中的chapter_count提取
        3. 使用正则从用户消息中匹配章节数
        4. 基于对话轮次推断默认值（30/80/150）

        Args:
            blueprint_total: 蓝图中已有的章节数（可能为None或0）
            history_records: 原始对话历史记录（包含conversation_state）
            formatted_history: 格式化后的对话历史（用于正则匹配）
            project_id: 项目ID（用于日志记录）

        Returns:
            int: 章节数（保证在5-10000范围内）
        """
        # 如果blueprint_total已经有效，直接使用
        if blueprint_total and NovelConstants.MIN_TOTAL_CHAPTERS <= blueprint_total <= NovelConstants.MAX_TOTAL_CHAPTERS:
            return blueprint_total

        # 开始提取流程
        extracted_chapters = None

        # 优先级1：从conversation_state中提取chapter_count
        extracted_chapters = self._extract_from_conversation_state(history_records, project_id)

        # 优先级2：使用正则从用户消息中匹配
        if not extracted_chapters:
            extracted_chapters = self._extract_from_user_messages(formatted_history, project_id)

        # 优先级3：基于对话轮次推断默认值
        if extracted_chapters:
            default_chapters = extracted_chapters
            logger.warning(
                "项目 %s LLM返回的total_chapters=%s无效，使用提取值 %d",
                project_id,
                blueprint_total,
                default_chapters,
            )
        else:
            default_chapters = self._infer_default_chapters(history_records, project_id)
            logger.warning(
                "项目 %s LLM返回的total_chapters=%s无效，使用默认值 %d",
                project_id,
                blueprint_total,
                default_chapters,
            )

        return default_chapters

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    async def _replace_blueprint_characters(
        self,
        project_id: str,
        characters_data: List[Dict]
    ) -> None:
        """
        替换项目的角色列表（原子操作）

        Args:
            project_id: 项目ID
            characters_data: 角色数据列表（dict格式）
        """
        await self.character_repo.bulk_create(project_id, characters_data)

    async def _replace_blueprint_relationships(
        self,
        project_id: str,
        relationships: List
    ) -> None:
        """
        替换项目的关系列表（原子操作）

        Args:
            project_id: 项目ID
            relationships: 关系数据列表（可以是dict或Pydantic对象）
        """
        await self.relationship_repo.bulk_create(project_id, relationships)

    async def _replace_chapter_outlines(
        self,
        project_id: str,
        outlines: List[Dict]
    ) -> None:
        """
        替换项目的章节大纲列表（原子操作）

        Args:
            project_id: 项目ID
            outlines: 大纲数据列表（dict格式）
        """
        await self.chapter_outline_repo.bulk_create(project_id, outlines)

    def _extract_from_conversation_state(
        self,
        history_records: List[Any],
        project_id: str,
    ) -> Optional[int]:
        """
        从对话历史的conversation_state中提取章节数

        Args:
            history_records: 原始对话历史记录
            project_id: 项目ID（用于日志记录）

        Returns:
            Optional[int]: 提取到的章节数，如果未找到则返回None
        """
        for record in reversed(history_records):
            if record.role == "assistant":
                # 使用安全解析（失败时跳过）
                data = parse_llm_json_safe(record.content)
                if not data:
                    continue

                conversation_state = data.get("conversation_state", {})
                if isinstance(conversation_state, dict):
                    chapter_count = conversation_state.get("chapter_count")
                    if isinstance(chapter_count, int) and NovelConstants.MIN_TOTAL_CHAPTERS <= chapter_count <= NovelConstants.MAX_TOTAL_CHAPTERS:
                        logger.info(
                            "项目 %s 从conversation_state中提取到章节数: %d",
                            project_id,
                            chapter_count,
                        )
                        return chapter_count

        return None

    def _extract_from_user_messages(
        self,
        formatted_history: List[Dict[str, str]],
        project_id: str,
    ) -> Optional[int]:
        """
        使用正则从用户消息中提取章节数

        使用简化的正则模式，只保留最可靠的匹配模式：
        - "章节数:100" / "设置100章"
        - "写100章" / "创作100章"

        Args:
            formatted_history: 格式化后的对话历史
            project_id: 项目ID（用于日志记录）

        Returns:
            Optional[int]: 提取到的章节数，如果未找到则返回None
        """
        for msg in reversed(formatted_history):
            if msg.get("role") == "user":
                content = msg.get("content", "")

                # 只使用最明确的两个模式
                patterns = [
                    r'(?:设置|设定|计划|章节数|篇幅)[\s:：]*?(\d+)\s*(?:章|$)',  # "章节数:100"
                    r'(?:写|创作|生成|共|总共)[\s]*(\d+)\s*章',  # "写100章"
                ]

                for pattern in patterns:
                    match = re.search(pattern, content)
                    if match:
                        candidate = int(match.group(1))
                        if NovelConstants.MIN_TOTAL_CHAPTERS <= candidate <= NovelConstants.MAX_TOTAL_CHAPTERS:
                            logger.info(
                                "项目 %s 通过简化正则提取到章节数: %d（原文：%s）",
                                project_id,
                                candidate,
                                content[:50],
                            )
                            return candidate

        return None

    def _infer_default_chapters(
        self,
        history_records: List[Any],
        project_id: str,
    ) -> int:
        """
        基于对话轮次推断默认章节数

        推断规则：
        - ≤5轮对话：30章（简单短篇故事）
        - 6-10轮对话：80章（中等复杂度）
        - >10轮对话：150章（复杂史诗）

        Args:
            history_records: 原始对话历史记录
            project_id: 项目ID（用于日志记录）

        Returns:
            int: 推断的默认章节数
        """
        conversation_rounds = len(history_records) // 2

        if conversation_rounds <= NovelConstants.CONVERSATION_ROUNDS_SHORT:
            default_chapters = NovelConstants.DEFAULT_CHAPTERS_SHORT
        elif conversation_rounds <= NovelConstants.CONVERSATION_ROUNDS_MEDIUM:
            default_chapters = NovelConstants.DEFAULT_CHAPTERS_MEDIUM
        else:
            default_chapters = NovelConstants.DEFAULT_CHAPTERS_LONG

        logger.warning(
            "项目 %s 无法从对话中提取章节数，使用对话轮次推断的默认值: %d（对话轮次: %d）",
            project_id,
            default_chapters,
            conversation_rounds,
        )

        return default_chapters
