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
from .prompt_checker import PromptChecker
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
        project_id: str,
        feature_index: int,
        dimensions: Optional[List[str]] = None,
        mode: OptimizationMode = OptimizationMode.AUTO,
        prompt_type: PromptType = PromptType.IMPLEMENTATION,
    ) -> AsyncGenerator[str, None]:
        """
        启动 Prompt 优化工作流

        Args:
            project_id: 项目 ID
            feature_index: 功能索引（0-based）
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

        # 计算 feature_number（1-based）
        feature_number = feature_index + 1

        # 获取维度显示名称
        dimension_names_map = get_all_dimension_names(prompt_type)

        try:
            # 构建优化上下文
            context = await self._build_context(project_id, feature_index)
            if not context:
                yield sse_event(OptimizationEventType.ERROR, {
                    "error": f"无法获取功能上下文: project_id={project_id}, feature_index={feature_index}",
                })
                return

            # 根据类型获取 Prompt 内容
            if prompt_type == PromptType.REVIEW:
                prompt_content = await self._get_review_prompt_content(project_id, feature_index)
                prompt_type_name = "审查"
                error_msg = "功能尚无审查 Prompt 内容，请先生成审查 Prompt"
            else:
                prompt_content = await self._get_prompt_content(project_id, feature_index)
                prompt_type_name = "实现"
                error_msg = "功能尚无实现 Prompt 内容，请先生成 Prompt"

            if not prompt_content:
                yield sse_event(OptimizationEventType.ERROR, {
                    "error": error_msg,
                })
                return

            # 注册会话（使用简化的追踪，不需要chapter_number）
            # 注意：content_optimization的session_manager需要chapter_number
            # 这里我们跳过注册，因为session_id已经在本地生成
            # 暂停/恢复/取消功能暂不支持，后续可添加专用管理器

            # 获取功能的 feature_id（用于 Agent 状态）
            feature = await self._get_feature_by_number(project_id, feature_number)
            # CodingFeature 使用 id 作为主键（整数），转换为字符串作为 feature_id
            feature_id = str(feature.id) if feature else f"{project_id}_{feature_number}"

            # 创建 Agent 状态
            state = AgentState(
                project_id=context.project.project_id,
                feature_id=feature_id,
                prompt_content=prompt_content,
                context=context,
            )

            # 创建 Prompt 检查器（用于 LLM 深度检查）
            prompt_checker = PromptChecker(llm_service=self.llm_service)

            # 创建工具执行器
            tool_executor = ToolExecutor(
                session=self.session,
                llm_service=self.llm_service,
                vector_store=self.vector_store,
                user_id=self.user_id,
                prompt_checker=prompt_checker,
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
                "feature_index": feature_index,
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
            # 清理会话（如果存在）
            # 注意：由于跳过了注册，这里也跳过清理
            pass

    async def _build_context(self, project_id: str, feature_index: int) -> Optional[OptimizationContext]:
        """构建优化上下文"""
        feature_number = feature_index + 1
        try:
            # 获取功能信息
            feature = await self._get_feature_by_number(project_id, feature_number)
            if not feature:
                logger.warning("功能不存在: project_id=%s, feature_number=%s", project_id, feature_number)
                return None

            # 获取项目信息
            project = await self._get_project(project_id)
            if not project:
                logger.warning("项目不存在: %s", project_id)
                return None

            # 获取蓝图信息
            blueprint = await self._get_blueprint(project_id)

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
            # 注意：CodingFeature 模型使用 id, name, description
            # FeatureContext schema 使用 feature_id, feature_name, feature_description
            feature_context = FeatureContext(
                feature_id=str(feature.id),
                feature_number=feature.feature_number,
                feature_name=feature.name,
                feature_description=feature.description,
                inputs=feature.inputs,
                outputs=feature.outputs,
                priority=feature.priority,
                system_number=feature.system_number,
                system_name=None,  # CodingFeature 不直接存储 system_name
                module_number=feature.module_number,
                module_name=None,  # CodingFeature 不直接存储 module_name
            )

            # 获取相关功能（同模块）
            related_features = await self._get_related_features(
                project_id=project_id,
                module_number=feature.module_number,
                exclude_feature_id=feature.id,  # 传递整数 ID
            )

            return OptimizationContext(
                project=project_context,
                feature=feature_context,
                related_features=related_features,
            )

        except Exception as e:
            logger.error("构建优化上下文失败: %s", e, exc_info=True)
            return None

    async def _get_feature(self, feature_id: int) -> Optional[CodingFeature]:
        """获取功能（通过 feature id）"""
        stmt = select(CodingFeature).where(CodingFeature.id == feature_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_feature_by_number(self, project_id: str, feature_number: int) -> Optional[CodingFeature]:
        """获取功能（通过 project_id 和 feature_number）"""
        stmt = select(CodingFeature).where(
            CodingFeature.project_id == project_id,
            CodingFeature.feature_number == feature_number,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project(self, project_id: str) -> Optional[CodingProject]:
        """获取项目"""
        stmt = select(CodingProject).where(CodingProject.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_blueprint(self, project_id: str) -> Optional[CodingBlueprint]:
        """获取蓝图"""
        stmt = select(CodingBlueprint).where(CodingBlueprint.project_id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_prompt_content(self, project_id: str, feature_index: int) -> Optional[str]:
        """获取功能的当前实现 Prompt 内容"""
        feature_number = feature_index + 1
        feature = await self._get_feature_by_number(project_id, feature_number)
        if not feature:
            return None

        # 获取选中的版本或最新版本
        # CodingFeatureVersion 使用 feature_id (int) 关联 CodingFeature.id
        # 使用 created_at 降序获取最新版本
        stmt = (
            select(CodingFeatureVersion)
            .where(CodingFeatureVersion.feature_id == feature.id)
            .order_by(CodingFeatureVersion.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()

        if version:
            # 版本内容字段是 content 不是 prompt_content
            return version.content

        return None

    async def _get_review_prompt_content(self, project_id: str, feature_index: int) -> Optional[str]:
        """获取功能的审查 Prompt 内容"""
        feature_number = feature_index + 1
        feature = await self._get_feature_by_number(project_id, feature_number)
        if feature:
            return feature.review_prompt
        return None

    async def _get_related_features(
        self,
        project_id: str,
        module_number: Optional[int],
        exclude_feature_id: int,
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
                CodingFeature.id != exclude_feature_id,
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        features = result.scalars().all()

        return [
            FeatureContext(
                feature_id=str(f.id),
                feature_number=f.feature_number,
                feature_name=f.name,
                feature_description=f.description,
                inputs=f.inputs,
                outputs=f.outputs,
                priority=f.priority,
                system_number=f.system_number,
                system_name=None,
                module_number=f.module_number,
                module_name=None,
            )
            for f in features
        ]

    async def apply_suggestion(
        self,
        project_id: str,
        feature_index: int,
        suggestion_id: str,
        suggested_text: str,
        original_text: Optional[str] = None,
        prompt_type: PromptType = PromptType.IMPLEMENTATION,
    ) -> bool:
        """
        应用优化建议到 Prompt

        Args:
            project_id: 项目 ID
            feature_index: 功能索引（0-based）
            suggestion_id: 建议 ID
            suggested_text: 建议的新文本
            original_text: 原始文本（用于替换）
            prompt_type: Prompt 类型

        Returns:
            是否应用成功
        """
        feature_number = feature_index + 1
        try:
            # 获取功能
            feature = await self._get_feature_by_number(project_id, feature_number)
            if not feature:
                logger.warning("功能不存在: project_id=%s, feature_number=%s", project_id, feature_number)
                return False

            # 根据类型获取当前内容
            if prompt_type == PromptType.REVIEW:
                current_content = await self._get_review_prompt_content(project_id, feature_index)
                if not current_content:
                    logger.warning("功能没有审查 Prompt 内容: project_id=%s, feature_index=%s", project_id, feature_index)
                    return False
            else:
                current_content = await self._get_prompt_content(project_id, feature_index)
                if not current_content:
                    logger.warning("功能没有实现 Prompt 内容: project_id=%s, feature_index=%s", project_id, feature_index)
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
                await self._update_review_prompt(feature.id, new_content)
            else:
                await self._create_new_version(feature.id, new_content, suggestion_id)

            return True

        except Exception as e:
            logger.error("应用建议失败: %s", e, exc_info=True)
            return False

    async def _update_review_prompt(
        self,
        feature_id: int,
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
        feature_id: int,
        content: str,
        suggestion_id: str,
    ) -> CodingFeatureVersion:
        """创建新的实现 Prompt 版本"""
        # 获取当前最新版本（用于生成版本标签）
        stmt = (
            select(CodingFeatureVersion)
            .where(CodingFeatureVersion.feature_id == feature_id)
            .order_by(CodingFeatureVersion.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        latest_version = result.scalar_one_or_none()

        # 生成版本标签
        if latest_version and latest_version.version_label:
            try:
                # 尝试从 "v1", "v2" 等格式提取版本号
                current_num = int(latest_version.version_label.lstrip('v'))
                next_label = f"v{current_num + 1}"
            except (ValueError, AttributeError):
                next_label = "v1"
        else:
            next_label = "v1"

        # 创建新版本
        # CodingFeatureVersion 字段：id(自增), feature_id, version_label, provider, content, metadata_json, created_at
        new_version = CodingFeatureVersion(
            feature_id=feature_id,
            version_label=next_label,
            provider="optimization_agent",
            content=content,
            metadata_json={"suggestion_id": suggestion_id},
        )

        self.session.add(new_version)
        await self.session.flush()

        return new_version

    def get_session_info(self, session_id: str) -> Optional[OptimizationSessionInfo]:
        """获取会话信息

        注意：当前版本跳过了会话注册，此方法暂时返回 None
        后续版本可添加专用的编程项目优化会话管理器
        """
        # 当前版本不注册会话，返回 None
        return None

    def pause_session(self, session_id: str) -> bool:
        """暂停会话

        注意：当前版本跳过了会话注册，此方法可能返回 False
        """
        return self.session_manager.pause_session(session_id)

    def resume_session(self, session_id: str) -> bool:
        """恢复会话

        注意：当前版本跳过了会话注册，此方法可能返回 False
        """
        return self.session_manager.resume_session(session_id)

    def cancel_session(self, session_id: str) -> bool:
        """取消会话

        注意：当前版本跳过了会话注册，此方法可能返回 False
        """
        return self.session_manager.cancel_session(session_id)


__all__ = [
    "PromptOptimizationWorkflow",
]
