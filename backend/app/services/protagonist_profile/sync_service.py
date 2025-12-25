"""主角档案同步服务

负责协调各子服务，实现章节同步的完整流程。
"""
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.protagonist import SyncResult
from .service import ProtagonistProfileService
from .analysis_service import ProtagonistAnalysisService
from .implicit_tracker import ImplicitAttributeTracker
from .deletion_protection import DeletionProtectionService

logger = logging.getLogger(__name__)


class ProtagonistSyncService:
    """主角档案同步服务

    协调各子服务，实现章节同步的完整流程：
    1. 调用LLM分析章节内容
    2. 应用属性变更
    3. 记录行为并分类
    4. 处理删除候选
    5. 检查隐性属性阈值
    """

    def __init__(
        self,
        session: AsyncSession,
        profile_service: ProtagonistProfileService,
        analysis_service: ProtagonistAnalysisService,
        implicit_tracker: ImplicitAttributeTracker,
        deletion_protection: DeletionProtectionService
    ):
        self.session = session
        self.profile_service = profile_service
        self.analysis_service = analysis_service
        self.implicit_tracker = implicit_tracker
        self.deletion_protection = deletion_protection

    async def sync_from_chapter(
        self,
        profile_id: int,
        chapter_number: int,
        chapter_content: str,
        user_id: int
    ) -> SyncResult:
        """从章节同步更新主角档案

        完整同步流程：
        1. 获取当前档案状态
        2. 调用LLM分析章节
        3. 应用显性和社会属性变更
        4. 记录行为并进行隐性属性分类
        5. 处理删除候选
        6. 检查是否需要更新隐性属性
        7. 更新同步章节号

        Args:
            profile_id: 档案ID
            chapter_number: 章节号
            chapter_content: 章节正文内容
            user_id: 用户ID（用于LLM配置）

        Returns:
            同步结果
        """
        changes_applied = 0
        behaviors_recorded = 0
        deletions_marked = 0

        # 1. 获取当前档案状态
        current_state = await self.profile_service.get_current_state(profile_id)
        current_profile = {
            "explicit": current_state["explicit"],
            "implicit": current_state["implicit"],
            "social": current_state["social"],
        }

        logger.info(f"开始同步主角档案: profile={profile_id}, chapter={chapter_number}")

        # 2. 调用LLM分析章节
        analysis_result = await self.analysis_service.analyze_chapter(
            chapter_content=chapter_content,
            current_profile=current_profile,
            chapter_number=chapter_number,
            user_id=user_id
        )

        # 3. 应用属性变更
        for change in analysis_result.attribute_changes:
            try:
                if change.operation == "add":
                    await self.profile_service.add_attribute(
                        profile_id=profile_id,
                        category=change.category,
                        key=change.key,
                        value=change.new_value,
                        event_cause=change.event_cause,
                        evidence=change.evidence,
                        chapter_number=chapter_number
                    )
                    changes_applied += 1

                elif change.operation == "modify":
                    await self.profile_service.modify_attribute(
                        profile_id=profile_id,
                        category=change.category,
                        key=change.key,
                        new_value=change.new_value,
                        event_cause=change.event_cause,
                        evidence=change.evidence,
                        chapter_number=chapter_number
                    )
                    changes_applied += 1

                    # 属性被修改，重置可能存在的删除标记
                    await self.deletion_protection.reset_marks(
                        profile_id, change.category, change.key
                    )

            except ValueError as e:
                logger.warning(f"应用属性变更失败: {e}")

        # 4. 记录行为并分类
        for behavior in analysis_result.behaviors:
            # 获取最新的隐性属性（可能在上面被修改了）
            updated_state = await self.profile_service.get_current_state(profile_id)
            implicit_attrs = updated_state["implicit"]

            # 如果有隐性属性，进行分类
            classification_results = {}
            if implicit_attrs:
                classification = await self.analysis_service.classify_behavior(
                    behavior_description=behavior.description,
                    original_text=behavior.original_text,
                    behavior_tags=behavior.tags,
                    implicit_attributes=implicit_attrs,
                    user_id=user_id
                )
                classification_results = classification.classifications

                # 处理LLM建议的新属性
                for suggested in classification.suggested_new_attributes:
                    try:
                        await self.profile_service.add_attribute(
                            profile_id=profile_id,
                            category="implicit",
                            key=suggested.get("key", ""),
                            value=suggested.get("value"),
                            event_cause="LLM从行为分析中推断",
                            evidence=suggested.get("evidence", behavior.original_text),
                            chapter_number=chapter_number
                        )
                        changes_applied += 1
                    except ValueError as e:
                        logger.debug(f"添加建议属性失败（可能已存在）: {e}")

            # 记录行为
            await self.implicit_tracker.record_behavior(
                profile_id=profile_id,
                chapter_number=chapter_number,
                behavior_description=behavior.description,
                original_text=behavior.original_text,
                behavior_tags=behavior.tags,
                classification_results=classification_results
            )
            behaviors_recorded += 1

        # 5. 处理删除候选
        for candidate in analysis_result.deletion_candidates:
            await self.deletion_protection.add_mark(
                profile_id=profile_id,
                category=candidate.category,
                key=candidate.key,
                reason=candidate.reason,
                evidence=candidate.evidence,
                chapter_number=chapter_number
            )
            deletions_marked += 1

            # 检查是否达到删除阈值
            ready, count = await self.deletion_protection.check_ready_for_deletion(
                profile_id, candidate.category, candidate.key
            )
            if ready:
                # 执行实际删除
                try:
                    await self.profile_service.delete_attribute(
                        profile_id=profile_id,
                        category=candidate.category,
                        key=candidate.key,
                        event_cause=f"连续{count}次标记删除",
                        evidence=candidate.evidence,
                        chapter_number=chapter_number
                    )
                    await self.deletion_protection.mark_as_executed(
                        profile_id, candidate.category, candidate.key
                    )
                    changes_applied += 1
                    logger.info(
                        f"执行删除: profile={profile_id}, "
                        f"{candidate.category}.{candidate.key}"
                    )
                except ValueError as e:
                    logger.warning(f"删除属性失败: {e}")

        # 6. 检查隐性属性是否需要更新
        updated_state = await self.profile_service.get_current_state(profile_id)
        implicit_attrs = updated_state["implicit"]

        attributes_to_review = await self.implicit_tracker.get_attributes_needing_review(
            profile_id=profile_id,
            implicit_attributes=implicit_attrs
        )

        for attr_info in attributes_to_review:
            # 获取相关行为证据
            evidence = await self.implicit_tracker.get_behavior_evidence(
                profile_id=profile_id,
                attribute_key=attr_info["key"]
            )

            # 请求LLM决策
            decision = await self.analysis_service.decide_implicit_update(
                attribute_key=attr_info["key"],
                current_value=attr_info["current_value"],
                behavior_records=evidence,
                non_conform_count=attr_info["stats"]["non_conform_count"],
                user_id=user_id
            )

            # 根据决策执行操作
            if decision.decision == "modify" and decision.new_value is not None:
                try:
                    await self.profile_service.modify_attribute(
                        profile_id=profile_id,
                        category="implicit",
                        key=attr_info["key"],
                        new_value=decision.new_value,
                        event_cause=f"基于行为分析自动更新: {decision.reasoning[:100]}",
                        evidence=decision.evidence_summary,
                        chapter_number=chapter_number
                    )
                    changes_applied += 1
                    logger.info(
                        f"自动更新隐性属性: profile={profile_id}, "
                        f"{attr_info['key']} -> {decision.new_value}"
                    )
                except ValueError as e:
                    logger.warning(f"更新隐性属性失败: {e}")

            elif decision.decision == "delete":
                # 为隐性属性添加删除标记
                await self.deletion_protection.add_mark(
                    profile_id=profile_id,
                    category="implicit",
                    key=attr_info["key"],
                    reason=decision.reasoning,
                    evidence=decision.evidence_summary,
                    chapter_number=chapter_number
                )
                deletions_marked += 1

        # 7. 更新同步章节号
        await self.profile_service.update_synced_chapter(profile_id, chapter_number)

        logger.info(
            f"同步完成: profile={profile_id}, chapter={chapter_number}, "
            f"changes={changes_applied}, behaviors={behaviors_recorded}, "
            f"deletions={deletions_marked}"
        )

        return SyncResult(
            changes_applied=changes_applied,
            behaviors_recorded=behaviors_recorded,
            deletions_marked=deletions_marked,
            synced_chapter=chapter_number
        )

    async def batch_sync(
        self,
        profile_id: int,
        chapters: Dict[int, str],
        user_id: int
    ) -> Dict[int, SyncResult]:
        """批量同步多个章节

        按章节号顺序同步多个章节。

        Args:
            profile_id: 档案ID
            chapters: 章节字典 {章节号: 章节内容}
            user_id: 用户ID

        Returns:
            每个章节的同步结果 {章节号: SyncResult}
        """
        results = {}

        # 按章节号排序处理
        for chapter_number in sorted(chapters.keys()):
            chapter_content = chapters[chapter_number]
            result = await self.sync_from_chapter(
                profile_id=profile_id,
                chapter_number=chapter_number,
                chapter_content=chapter_content,
                user_id=user_id
            )
            results[chapter_number] = result

        return results
