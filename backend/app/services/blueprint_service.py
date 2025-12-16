"""
蓝图管理服务

负责小说项目蓝图的创建、更新、清理等核心业务逻辑。
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.constants import NovelConstants
from ..models.novel import NovelProject, CharacterStateIndex, ForeshadowingIndex
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


# ------------------------------------------------------------------
# 数据类：蓝图生成结果
# ------------------------------------------------------------------

@dataclass
class BlueprintGenerationResult:
    """蓝图生成结果"""
    blueprint: Blueprint
    ai_message: str
    needs_part_outlines: bool
    total_chapters: int


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

            # 清理角色状态索引
            await self.session.execute(
                delete(CharacterStateIndex).where(
                    CharacterStateIndex.project_id == project_id
                )
            )

            # 清理伏笔索引（重新生成蓝图时删除所有伏笔记录）
            await self.session.execute(
                delete(ForeshadowingIndex).where(
                    ForeshadowingIndex.project_id == project_id
                )
            )
            logger.info("项目 %s 已清理角色状态和伏笔索引", project_id)

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
                except RuntimeError as exc:
                    # 向量库依赖缺失或配置问题，不阻塞主流程
                    logger.info("向量库未配置或不可用，跳过向量数据清理: %s", exc)
                except (OSError, IOError) as exc:
                    # 向量库连接或文件访问错误
                    log_exception(
                        exc,
                        "清理向量库数据（连接错误）",
                        level="warning",
                        project_id=project_id,
                        chapter_count=len(chapter_numbers),
                    )
                except ValueError as exc:
                    # 数据格式错误
                    log_exception(
                        exc,
                        "清理向量库数据（数据格式错误）",
                        level="warning",
                        project_id=project_id,
                    )

        # 3. 删除所有章节大纲（可能存在大纲但没有章节内容的情况）
        try:
            outline_count = await self.chapter_outline_repo.count_by_project(project_id)
            if outline_count > 0:
                logger.info("项目 %s 准备删除 %d 个章节大纲", project_id, outline_count)
                await self.chapter_outline_repo.delete_by_project(project_id)
                logger.info("项目 %s 重新生成蓝图，已清除 %d 个章节大纲", project_id, outline_count)
        except Exception as exc:
            # 章节大纲删除是核心操作，失败应该抛出让调用者处理
            # 记录日志后重新抛出，确保事务回滚
            log_exception(
                exc,
                "删除章节大纲",
                level="error",
                project_id=project_id,
                outline_count=outline_count if 'outline_count' in locals() else 0
            )
            raise

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

    # ------------------------------------------------------------------
    # 业务逻辑方法（从Router层迁移）
    # ------------------------------------------------------------------

    def validate_and_clean_blueprint(
        self,
        blueprint: Blueprint,
        project_id: str,
    ) -> Blueprint:
        """
        验证蓝图数据并清理违规内容

        强制工作流分离：蓝图生成阶段不包含章节大纲。
        即使LLM违反指令生成了章节大纲，也要强制清空并记录。

        Args:
            blueprint: 原始蓝图对象
            project_id: 项目ID（用于日志）

        Returns:
            Blueprint: 清理后的蓝图对象
        """
        if blueprint.chapter_outline:
            logger.warning(
                "项目 %s 蓝图生成时包含了 %d 个章节大纲，违反工作流设计，正在备份并清空",
                project_id,
                len(blueprint.chapter_outline),
            )

            # 初始化world_setting
            if not blueprint.world_setting:
                blueprint.world_setting = {}

            # 清理旧的违规备份（只保留最新一次，避免数据膨胀）
            if '_discarded_chapter_outlines' in blueprint.world_setting:
                old_count = blueprint.world_setting['_discarded_chapter_outlines'].get('count', 0)
                logger.info(
                    "项目 %s 清理旧的违规章节大纲备份（共 %d 个）",
                    project_id,
                    old_count
                )

            # 备份当前被丢弃的数据（只保留元信息，不保留完整data，减少存储）
            blueprint.world_setting['_discarded_chapter_outlines'] = {
                'timestamp': datetime.now().isoformat(),
                'count': len(blueprint.chapter_outline),
                'summary': f"检测到{len(blueprint.chapter_outline)}个违规章节大纲，已自动清理"
            }

            logger.info(
                "项目 %s 已记录违规章节大纲元信息（count=%d），完整数据已丢弃",
                project_id,
                len(blueprint.chapter_outline)
            )

            # 清空chapter_outline
            blueprint.chapter_outline = []

        return blueprint

    def calculate_needs_part_outlines(
        self,
        blueprint: Blueprint,
        total_chapters: int,
        project_id: str,
    ) -> bool:
        """
        根据章节数计算是否需要分部大纲

        Args:
            blueprint: 蓝图对象（会被修改）
            total_chapters: 总章节数
            project_id: 项目ID（用于日志）

        Returns:
            bool: 是否需要分部大纲
        """
        # 更新蓝图的总章节数
        blueprint.total_chapters = total_chapters

        # 根据章节数判断是否需要分部大纲
        # 使用 >= 与文档保持一致：长篇小说定义为章节数>=阈值
        if total_chapters >= settings.part_outline_threshold:
            blueprint.needs_part_outlines = True
            logger.info(
                "项目 %s 章节数 %d 达到或超过阈值 %d，自动设置 needs_part_outlines=True",
                project_id, total_chapters, settings.part_outline_threshold
            )
        else:
            blueprint.needs_part_outlines = False
            logger.info(
                "项目 %s 章节数 %d 未达到阈值 %d，设置 needs_part_outlines=False",
                project_id, total_chapters, settings.part_outline_threshold
            )

        return blueprint.needs_part_outlines

    def generate_blueprint_message(
        self,
        total_chapters: int,
        needs_part_outlines: bool,
    ) -> str:
        """
        根据蓝图生成结果生成提示消息

        Args:
            total_chapters: 总章节数
            needs_part_outlines: 是否需要分部大纲

        Returns:
            str: AI提示消息
        """
        if needs_part_outlines:
            return (
                f"太棒了！基础蓝图已生成完成。您的小说计划 {total_chapters} 章，"
                "接下来请在详情页点击「生成部分大纲」按钮来规划整体结构，"
                "然后再生成详细的章节大纲。"
            )
        else:
            return (
                f"太棒了！基础蓝图已生成完成。您的小说计划 {total_chapters} 章，"
                "接下来请在详情页点击「生成章节大纲」按钮来规划具体章节。"
            )

    def process_generated_blueprint(
        self,
        blueprint: Blueprint,
        history_records: List[Any],
        formatted_history: List[Dict[str, str]],
        project_id: str,
    ) -> BlueprintGenerationResult:
        """
        处理LLM生成的蓝图数据

        整合蓝图验证、章节数提取、分部大纲判断、消息生成等业务逻辑。

        Args:
            blueprint: LLM生成的原始蓝图
            history_records: 原始对话历史记录
            formatted_history: 格式化后的对话历史
            project_id: 项目ID

        Returns:
            BlueprintGenerationResult: 处理后的蓝图结果
        """
        # 1. 验证并清理蓝图（移除违规章节大纲）
        blueprint = self.validate_and_clean_blueprint(blueprint, project_id)

        # 2. 提取或推断章节数
        total_chapters = self.extract_total_chapters(
            blueprint_total=blueprint.total_chapters,
            history_records=history_records,
            formatted_history=formatted_history,
            project_id=project_id,
        )

        # 3. 计算是否需要分部大纲（会更新blueprint对象）
        needs_part_outlines = self.calculate_needs_part_outlines(
            blueprint, total_chapters, project_id
        )

        logger.info(
            "项目 %s 蓝图处理完成，总章节数=%d，需要部分大纲=%s",
            project_id,
            total_chapters,
            needs_part_outlines,
        )

        # 4. 生成提示消息
        ai_message = self.generate_blueprint_message(total_chapters, needs_part_outlines)

        return BlueprintGenerationResult(
            blueprint=blueprint,
            ai_message=ai_message,
            needs_part_outlines=needs_part_outlines,
            total_chapters=total_chapters,
        )
