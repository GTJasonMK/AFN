"""
编程项目 Prompt 优化 - 工作流协调器

提供优化工作流的主入口，协调 Agent、工具执行器和会话管理。
支持两种 Prompt 类型：实现 Prompt 和审查 Prompt。
"""

import logging
import uuid
from typing import Any, AsyncGenerator, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...models.coding import (
    CodingBlueprint,
    CodingFeature,
    CodingFeatureVersion,
    CodingProject,
)
from ..content_optimization.session_manager import get_session_manager
from .agent import PromptOptimizationAgent, sse_event
from .schemas import (
    DEFAULT_DIMENSIONS,
    DEFAULT_REVIEW_DIMENSIONS,
    FeatureContext,
    OptimizationContext,
    OptimizationEventType,
    OptimizationMode,
    OptimizationSessionInfo,
    ProjectContext,
    PromptType,
    get_default_dimensions,
    get_all_dimension_names,
)
from .tool_executor import AgentState, ToolExecutor

logger = logging.getLogger(__name__)


class PromptOptimizationWorkflow:
    """
    Prompt 优化工作流

    提供完整的优化流程控制，包括：
    - 上下文构建
    - Agent 执行
    - 会话管理
    - 结果应用

    支持两种 Prompt 类型：
    - implementation: 实现 Prompt
    - review: 审查 Prompt
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_service: Any,
        vector_store: Any,
        user_id: str,
    ):
        self.session = session
        self.llm_service = llm_service
        self.vector_store = vector_store
        self.user_id = user_id
        self.session_manager = get_session_manager()

    async def start_optimization(
        self,
        feature_id: str,
        dimensions: Optional[List[str]] = None,
        mode: OptimizationMode = OptimizationMode.AUTO,
        prompt_type: PromptType = PromptType.IMPLEMENTATION,
    ) -> AsyncGenerator[str, None]:
        """
        启动 Prompt 优化工作流

        Args:
            feature_id: 功能 ID
            dimensions: 检查维度列表，默认根据 prompt_type 使用对应的默认维度
            mode: 优化模式
            prompt_type: Prompt 类型（implementation 或 review）

        Yields:
            SSE 事件字符串
        """
        # 使用对应类型的默认维度
        if not dimensions:
            dimensions = get_default_dimensions(prompt_type)

        # 生成会话 ID
        session_id = str(uuid.uuid4())

        # 获取维度显示名称
        dimension_names_map = get_all_dimension_names(prompt_type)

        try:
            # 构建优化上下文
            context = await self._build_context(feature_id)
            if not context:
                yield sse_event(OptimizationEventType.ERROR, {
                    "error": f"无法获取功能上下文: feature_id={feature_id}",
                })
                return

            # 根据类型获取 Prompt 内容
            if prompt_type == PromptType.REVIEW:
                prompt_content = await self._get_review_prompt_content(feature_id)
                prompt_type_name = "审查"
                error_msg = "功能尚无审查 Prompt 内容，请先生成审查 Prompt"
            else:
                prompt_content = await self._get_prompt_content(feature_id)
                prompt_type_name = "实现"
                error_msg = "功能尚无实现 Prompt 内容，请先生成 Prompt"

            if not prompt_content:
                yield sse_event(OptimizationEventType.ERROR, {
                    "error": error_msg,
                })
                return

            # 注册会话
            self.session_manager.register_session(
                session_id=session_id,
                project_id=context.project.project_id,
            )

            # 创建 Agent 状态
            state = AgentState(
                project_id=context.project.project_id,
                feature_id=feature_id,
                prompt_content=prompt_content,
                context=context,
            )

            # 创建工具执行器
            tool_executor = ToolExecutor(
                session=self.session,
                llm_service=self.llm_service,
                vector_store=self.vector_store,
                user_id=self.user_id,
                prompt_checker=None,
                prompt_type=prompt_type,
            )

            # 创建 Agent
            agent = PromptOptimizationAgent(
                llm_service=self.llm_service,
                tool_executor=tool_executor,
                optimization_mode=mode,
                session_id=session_id,
                prompt_type=prompt_type,
            )

            # 发送工作流开始事件（包含 prompt_type 信息）
            yield sse_event(OptimizationEventType.WORKFLOW_START, {
                "session_id": session_id,
                "feature_id": feature_id,
                "feature_name": context.feature.feature_name,
                "dimensions": dimensions,
                "dimension_names": [dimension_names_map.get(d, d) for d in dimensions],
                "mode": mode.value,
                "prompt_type": prompt_type.value,
                "prompt_type_name": prompt_type_name,
                "prompt_length": len(prompt_content),
            })

            # 运行 Agent
            async for event in agent.run(
                state=state,
                dimensions=dimensions,
                user_id=self.user_id,
            ):
                yield event

        except Exception as e:
            logger.error("优化工作流异常: %s", e, exc_info=True)
            yield sse_event(OptimizationEventType.ERROR, {
                "error": f"优化工作流异常: {str(e)}",
            })
        finally:
            # 清理会话
            self.session_manager.unregister_session(session_id)

    async def _build_context(self, feature_id: str) -> Optional[OptimizationContext]:
        """构建优化上下文"""
        try:
            # 获取功能信息
            feature = await self._get_feature(feature_id)
            if not feature:
                logger.warning("功能不存在: %s", feature_id)
                return None

            # 获取项目信息
            project = await self._get_project(feature.project_id)
            if not project:
                logger.warning("项目不存在: %s", feature.project_id)
                return None

            # 获取蓝图信息
            blueprint = await self._get_blueprint(feature.project_id)

            # 构建项目上下文
            project_context = ProjectContext(
                project_id=project.project_id,
                project_name=project.project_name,
                architecture_synopsis=blueprint.architecture_synopsis if blueprint else None,
                tech_stack=blueprint.tech_stack if blueprint else None,
                core_requirements=blueprint.core_requirements if blueprint else None,
                technical_challenges=blueprint.technical_challenges if blueprint else None,
                dependencies=blueprint.dependencies if blueprint else None,
            )

            # 构建功能上下文
            feature_context = FeatureContext(
                feature_id=feature.feature_id,
                feature_number=feature.feature_number,
                feature_name=feature.feature_name,
                feature_description=feature.feature_description,
                inputs=feature.inputs,
                outputs=feature.outputs,
                priority=feature.priority,
                system_number=feature.system_number,
                system_name=feature.system_name,
                module_number=feature.module_number,
                module_name=feature.module_name,
            )

            # 获取相关功能（同模块）
            related_features = await self._get_related_features(
                project_id=feature.project_id,
                module_number=feature.module_number,
                exclude_feature_id=feature_id,
            )

            return OptimizationContext(
                project=project_context,
                feature=feature_context,
                related_features=related_features,
            )

        except Exception as e:
            logger.error("构建优化上下文失败: %s", e, exc_info=True)
            return None

    async def _get_feature(self, feature_id: str) -> Optional[CodingFeature]:
        """获取功能"""
        stmt = select(CodingFeature).where(CodingFeature.feature_id == feature_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project(self, project_id: str) -> Optional[CodingProject]:
        """获取项目"""
        stmt = select(CodingProject).where(CodingProject.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_blueprint(self, project_id: str) -> Optional[CodingBlueprint]:
        """获取蓝图"""
        stmt = select(CodingBlueprint).where(CodingBlueprint.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_prompt_content(self, feature_id: str) -> Optional[str]:
        """获取功能的当前实现 Prompt 内容"""
        # 获取选中的版本或最新版本
        stmt = (
            select(CodingFeatureVersion)
            .where(CodingFeatureVersion.feature_id == feature_id)
            .order_by(CodingFeatureVersion.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()

        if version:
            return version.prompt_content

        return None

    async def _get_review_prompt_content(self, feature_id: str) -> Optional[str]:
        """获取功能的审查 Prompt 内容"""
        feature = await self._get_feature(feature_id)
        if feature:
            return feature.review_prompt
        return None

    async def _get_related_features(
        self,
        project_id: str,
        module_number: Optional[int],
        exclude_feature_id: str,
        limit: int = 5,
    ) -> List[FeatureContext]:
        """获取相关功能（同模块的其他功能）"""
        if module_number is None:
            return []

        stmt = (
            select(CodingFeature)
            .where(
                CodingFeature.project_id == project_id,
                CodingFeature.module_number == module_number,
                CodingFeature.feature_id != exclude_feature_id,
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        features = result.scalars().all()

        return [
            FeatureContext(
                feature_id=f.feature_id,
                feature_number=f.feature_number,
                feature_name=f.feature_name,
                feature_description=f.feature_description,
                inputs=f.inputs,
                outputs=f.outputs,
                priority=f.priority,
                system_number=f.system_number,
                system_name=f.system_name,
                module_number=f.module_number,
                module_name=f.module_name,
            )
            for f in features
        ]

    async def apply_suggestion(
        self,
        feature_id: str,
        suggestion_id: str,
        suggested_text: str,
        original_text: Optional[str] = None,
        prompt_type: PromptType = PromptType.IMPLEMENTATION,
    ) -> bool:
        """
        应用优化建议到 Prompt

        Args:
            feature_id: 功能 ID
            suggestion_id: 建议 ID
            suggested_text: 建议的新文本
            original_text: 原始文本（用于替换）
            prompt_type: Prompt 类型

        Returns:
            是否应用成功
        """
        try:
            # 根据类型获取当前内容
            if prompt_type == PromptType.REVIEW:
                current_content = await self._get_review_prompt_content(feature_id)
                if not current_content:
                    logger.warning("功能没有审查 Prompt 内容: %s", feature_id)
                    return False
            else:
                current_content = await self._get_prompt_content(feature_id)
                if not current_content:
                    logger.warning("功能没有实现 Prompt 内容: %s", feature_id)
                    return False

            # 应用修改
            if original_text and original_text in current_content:
                # 替换指定文本
                new_content = current_content.replace(original_text, suggested_text, 1)
            else:
                # 追加建议（如果无法定位原文）
                new_content = f"{current_content}\n\n{suggested_text}"

            # 根据类型保存
            if prompt_type == PromptType.REVIEW:
                await self._update_review_prompt(feature_id, new_content)
            else:
                await self._create_new_version(feature_id, new_content, suggestion_id)

            return True

        except Exception as e:
            logger.error("应用建议失败: %s", e, exc_info=True)
            return False

    async def _update_review_prompt(
        self,
        feature_id: str,
        content: str,
    ) -> bool:
        """更新审查 Prompt"""
        feature = await self._get_feature(feature_id)
        if not feature:
            return False

        feature.review_prompt = content
        await self.session.flush()
        return True

    async def _create_new_version(
        self,
        feature_id: str,
        content: str,
        suggestion_id: str,
    ) -> CodingFeatureVersion:
        """创建新的实现 Prompt 版本"""
        # 获取当前最大版本号
        stmt = (
            select(CodingFeatureVersion)
            .where(CodingFeatureVersion.feature_id == feature_id)
            .order_by(CodingFeatureVersion.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        latest_version = result.scalar_one_or_none()

        next_version = (latest_version.version_number + 1) if latest_version else 1

        # 创建新版本
        new_version = CodingFeatureVersion(
            version_id=str(uuid.uuid4()),
            feature_id=feature_id,
            version_number=next_version,
            prompt_content=content,
            generation_model="optimization_agent",
            generation_params={"suggestion_id": suggestion_id},
        )

        self.session.add(new_version)
        await self.session.flush()

        return new_version

    def get_session_info(self, session_id: str) -> Optional[OptimizationSessionInfo]:
        """获取会话信息"""
        return self.session_manager.get_session_info(session_id)

    def pause_session(self, session_id: str) -> bool:
        """暂停会话"""
        return self.session_manager.pause_session(session_id)

    def resume_session(self, session_id: str) -> bool:
        """恢复会话"""
        return self.session_manager.resume_session(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """取消会话"""
        return self.session_manager.cancel_session(session_id)


__all__ = [
    "PromptOptimizationWorkflow",
]
