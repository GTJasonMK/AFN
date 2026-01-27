"""
Coding 文件相关路由：目录生成 API（三阶段架构）

拆分自 `backend/app/api/routers/coding/files.py`。
"""

import logging
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import get_default_user, get_llm_service, get_prompt_service
from ....db.session import AsyncSessionLocal, get_session
from ....schemas.user import UserInDB
from ....services.coding_files import DirectoryStructureService
from ....services.coding_files.architect import (
    ArchitectureBasedGenerator,
    ArchitectureDecisionMaker,
    ArchitecturePattern,
    ProjectProfiler,
    QualityEvaluator,
    RefinementAgent,
)
from ....services.coding_files.directory_generator import BruteForceOutput, DirectoryTreeBuilder
from ....services.llm_service import LLMService
from ....services.prompt_service import PromptService
from ....utils.sse_helpers import create_sse_response, sse_event
from ....repositories.coding_files_repository import CodingAgentStateRepository
from .files_dependencies import DIRECTORY_AGENT_TYPE
from .files_planning_context import load_directory_planning_context

logger = logging.getLogger(__name__)
router = APIRouter()


class PlanDirectoryV2Request(BaseModel):
    """目录规划请求（三阶段架构）"""

    preference: Optional[str] = Field(None, description="规划偏好说明")
    architecture_pattern: Optional[str] = Field(
        None,
        description="架构模式：layered(分层架构), feature_based(功能模块架构), simple(简单架构)",
    )
    run_refinement: bool = Field(True, description="是否运行质量评估和精化阶段")
    clear_existing: bool = Field(False, description="是否清除现有目录结构")


@router.post("/coding/{project_id}/directories/plan-v2")
async def plan_directory_structure_v2(
    project_id: str,
    request: Optional[PlanDirectoryV2Request] = None,
    session: AsyncSession = Depends(get_session),
    llm_service: LLMService = Depends(get_llm_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    三阶段目录结构规划（SSE流式模式）

    阶段一（项目画像）：
    - 收集项目信息，构建项目画像
    - 分析技术栈、模块依赖、项目复杂度
    - 推荐适合的架构模式

    阶段二（架构决策）：
    - 选择架构模式（可由用户指定或系统推荐）
    - 生成层级定义和模块放置计划
    - 确定命名约定和共享模块策略

    阶段三（生成与精化）：
    - 按架构决策生成目录结构
    - 质量评估：覆盖率、内聚性、耦合度、可理解性
    - 精化Agent：自动修复不达标的问题

    事件类型：
    - progress: 进度更新
    - profile_built: 项目画像构建完成
    - decision_made: 架构决策完成
    - quality_evaluated: 质量评估完成
    - structure: 生成的结构数据
    - complete: 规划完成
    - error: 发生错误
    """
    logger.info(
        "收到目录规划请求: project_id=%s, pattern=%s",
        project_id,
        request.architecture_pattern if request else "auto",
    )

    context = await load_directory_planning_context(session, project_id, desktop_user.id)
    if not context.modules:
        return create_sse_response(_error_generator("项目没有模块，无法生成目录结构"))

    async def event_generator():
        async with AsyncSessionLocal() as inner_session:
            inner_state_repo = CodingAgentStateRepository(inner_session)
            inner_directory_service = DirectoryStructureService(inner_session)

            async for event in _three_phase_pipeline(
                project_id=project_id,
                user_id=desktop_user.id,
                project_data=context.project_data,
                blueprint_data=context.blueprint_data,
                systems=context.systems,
                modules=context.modules,
                architecture_pattern=request.architecture_pattern if request else None,
                run_refinement=request.run_refinement if request else True,
                clear_existing=request.clear_existing if request else False,
                inner_session=inner_session,
                inner_state_repo=inner_state_repo,
                inner_directory_service=inner_directory_service,
                llm_service=llm_service,
                prompt_service=prompt_service,
            ):
                yield event

    return create_sse_response(event_generator())


async def _error_generator(message: str):
    """错误事件生成器"""
    yield sse_event("error", {"message": message})


async def _three_phase_pipeline(
    project_id: str,
    user_id: int,
    project_data: dict,
    blueprint_data: dict,
    systems: list,
    modules: list,
    architecture_pattern: Optional[str],
    run_refinement: bool,
    clear_existing: bool,
    inner_session,
    inner_state_repo,
    inner_directory_service,
    llm_service=None,
    prompt_service=None,
):
    """
    三阶段目录结构生成流水线

    阶段一：ProjectProfiler - 项目画像构建
    阶段二：ArchitectureDecisionMaker - 架构决策
    阶段三：ArchitectureBasedGenerator + QualityEvaluator + RefinementAgent - 生成与精化

    Yields:
        SSE事件
    """
    try:
        # ============ 阶段一：项目画像构建 ============
        yield sse_event(
            "progress",
            {
                "stage": "phase1",
                "phase": "profiling",
                "message": "正在分析项目特征...",
            },
        )

        # 保存运行状态
        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="phase1_profiling",
            state_data={"started": True},
            progress_percent=10,
            progress_message="正在构建项目画像...",
            status="running",
        )
        await inner_session.commit()

        # 构建模块依赖
        module_dependencies = []
        for m in modules:
            deps = m.get("dependencies", [])
            if deps:
                for dep in deps:
                    module_dependencies.append(
                        {
                            "from_module": m.get("name", ""),
                            "to_module": dep,
                        }
                    )

        # 创建项目画像
        profiler = ProjectProfiler(
            project_id=project_id,
            project_data=project_data,
            blueprint_data=blueprint_data,
            systems=systems,
            modules=modules,
            module_dependencies=module_dependencies,
        )
        profile = profiler.build_profile()

        yield sse_event(
            "profile_built",
            {
                "project_name": profile.project_name,
                "total_modules": profile.total_modules,
                "total_systems": profile.total_systems,
                "complexity_score": profile.complexity_score,
                "recommended_pattern": profile.recommended_pattern.value if profile.recommended_pattern else None,
                "recommendation_reason": profile.recommendation_reason,
            },
        )

        yield sse_event(
            "progress",
            {
                "stage": "phase1_complete",
                "message": f"项目画像构建完成: {profile.total_modules}个模块, 复杂度{profile.complexity_score:.2f}",
            },
        )

        # ============ 阶段二：架构决策 ============
        yield sse_event(
            "progress",
            {
                "stage": "phase2",
                "phase": "decision",
                "message": "正在制定架构决策...",
            },
        )

        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="phase2_decision",
            state_data={"profile_built": True},
            progress_percent=30,
            progress_message="正在制定架构决策...",
            status="running",
        )
        await inner_session.commit()

        # 解析用户指定的架构模式
        user_pattern = None
        if architecture_pattern:
            try:
                user_pattern = ArchitecturePattern(architecture_pattern)
            except ValueError:
                logger.warning("无效的架构模式: %s, 将使用推荐模式", architecture_pattern)

        # 创建架构决策
        decision_maker = ArchitectureDecisionMaker(
            profile=profile,
            user_preference=user_pattern,
        )
        decision = decision_maker.make_decision()

        yield sse_event(
            "decision_made",
            {
                "pattern": decision.pattern.value,
                "pattern_rationale": decision.pattern_rationale,
                "layers": [
                    {"name": l.name, "path": l.path, "description": l.description} for l in decision.layers
                ],
                "module_placements_count": len(decision.module_placements),
                "naming_convention": decision.naming_convention,
            },
        )

        yield sse_event(
            "progress",
            {
                "stage": "phase2_complete",
                "message": f"架构决策完成: 选择{decision.pattern.value}模式",
            },
        )

        # ============ 阶段三：目录结构生成 ============
        yield sse_event(
            "progress",
            {
                "stage": "phase3",
                "phase": "generating",
                "message": f"正在按{decision.pattern.value}架构生成目录结构...",
            },
        )

        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="phase3_generating",
            state_data={
                "profile": profile.to_dict(),
                "decision": decision.to_dict(),
            },
            progress_percent=50,
            progress_message="正在生成目录结构...",
            status="running",
        )
        await inner_session.commit()

        # 生成目录结构
        generator = ArchitectureBasedGenerator(
            profile=profile,
            decision=decision,
            llm_service=llm_service,
            prompt_service=prompt_service,
            user_id=user_id,
        )

        # 使用流式生成
        output = None
        async for event in generator.generate_stream():
            event_type = event.get("event", "")
            event_data = event.get("data", {})

            if event_type == "structure":
                # 构建BruteForceOutput
                from ....services.coding_files.directory_generator.schemas import DirectorySpec, FileSpec

                output = BruteForceOutput(
                    root_path=decision.root_path,
                    directories=[DirectorySpec(**d) for d in event_data.get("directories", [])],
                    files=[FileSpec(**f) for f in event_data.get("files", [])],
                    shared_modules=event_data.get("shared_modules", []),
                    architecture_notes=event_data.get("architecture_notes", ""),
                )
            elif event_type == "complete":
                yield sse_event(
                    "progress",
                    {
                        "stage": "phase3_generated",
                        "message": f"目录结构生成完成: {event_data.get('total_directories', 0)}个目录, {event_data.get('total_files', 0)}个文件",
                        "total_directories": event_data.get("total_directories", 0),
                        "total_files": event_data.get("total_files", 0),
                    },
                )
            else:
                # 转发其他事件
                yield sse_event(event_type, event_data)

        if output is None:
            # 如果流式生成没有产出，使用同步生成
            output = generator.generate()

        # ============ 阶段三b：质量评估与精化 ============
        if run_refinement:
            yield sse_event(
                "progress",
                {
                    "stage": "phase3b",
                    "phase": "evaluating",
                    "message": "正在评估目录结构质量...",
                },
            )

            await inner_state_repo.save_state(
                project_id=project_id,
                agent_type=DIRECTORY_AGENT_TYPE,
                current_phase="phase3b_evaluating",
                state_data={"output": output.model_dump()},
                progress_percent=70,
                progress_message="正在评估和精化...",
                status="running",
            )
            await inner_session.commit()

            # 质量评估
            evaluator = QualityEvaluator(
                profile=profile,
                decision=decision,
                output=output,
            )
            initial_metrics = evaluator.evaluate()

            yield sse_event(
                "quality_evaluated",
                {
                    "overall_score": initial_metrics.overall_score,
                    "grade": initial_metrics.get_grade(),
                    "module_coverage": initial_metrics.module_coverage,
                    "file_completeness": initial_metrics.file_completeness,
                    "pattern_adherence": initial_metrics.pattern_adherence,
                    "issues_count": len(initial_metrics.issues),
                },
            )

            # 如果质量不达标，运行精化Agent
            if initial_metrics.overall_score < 0.8:
                yield sse_event(
                    "progress",
                    {
                        "stage": "phase3b",
                        "phase": "refining",
                        "message": f"质量评分{initial_metrics.overall_score:.2f}，开始精化...",
                    },
                )

                refiner = RefinementAgent(
                    profile=profile,
                    decision=decision,
                    output=output,
                )

                async for event in refiner.refine_stream():
                    event_type = event.get("event", "")
                    event_data = event.get("data", {})
                    yield sse_event(event_type, event_data)

                # 获取精化后的输出
                output = refiner.output
                summary = refiner.get_refinement_summary()

                yield sse_event(
                    "progress",
                    {
                        "stage": "phase3b_complete",
                        "message": f"精化完成: {summary['rounds']}轮, 评分提升{summary['improvement']:.2f}",
                        "refinement_rounds": summary["rounds"],
                        "initial_score": summary["initial_score"],
                        "final_score": summary["final_score"],
                    },
                )
            else:
                yield sse_event(
                    "progress",
                    {
                        "stage": "phase3b_complete",
                        "message": f"质量评分{initial_metrics.overall_score:.2f}达标，无需精化",
                    },
                )

        # ============ 保存到数据库 ============
        yield sse_event(
            "progress",
            {
                "stage": "saving",
                "message": "正在保存目录结构到数据库...",
            },
        )

        await inner_state_repo.save_state(
            project_id=project_id,
            agent_type=DIRECTORY_AGENT_TYPE,
            current_phase="saving",
            state_data={"output": output.model_dump()},
            progress_percent=90,
            progress_message="正在保存到数据库...",
            status="running",
        )
        await inner_session.commit()

        # 使用TreeBuilder构建目录树
        tree_builder = DirectoryTreeBuilder()
        root_dirs, all_files = tree_builder.build(output)

        # 如果需要清除现有结构
        if clear_existing:
            await inner_directory_service.clear_project_structure(project_id, user_id)
            await inner_session.flush()

        # 转换为LLM输出格式并保存
        from ....schemas.coding_files import LLMDirectoryNode, LLMDirectoryStructureOutput, LLMSourceFile

        def convert_planned_directory(planned_dir) -> LLMDirectoryNode:
            """转换PlannedDirectory为LLMDirectoryNode"""
            return LLMDirectoryNode(
                name=planned_dir.name,
                path=planned_dir.path,
                node_type=planned_dir.node_type,
                description=planned_dir.description,
                module_number=planned_dir.module_number,
                files=[
                    LLMSourceFile(
                        filename=f.filename,
                        file_type=f.file_type,
                        language=f.language,
                        description=f.description,
                        purpose=f.purpose,
                        priority=f.priority,
                        module_number=f.module_number,
                    )
                    for f in planned_dir.files
                ],
                children=[convert_planned_directory(c) for c in planned_dir.children],
            )

        llm_output = LLMDirectoryStructureOutput(
            root_path=output.root_path,
            directories=[convert_planned_directory(d) for d in root_dirs],
            summary=output.architecture_notes,
        )

        # 保存到数据库
        dirs_created, files_created = await inner_directory_service._save_structure(
            project_id=project_id,
            module_number=0,  # 项目级别
            structure=llm_output,
        )

        # 清除Agent状态（成功完成）
        await inner_state_repo.delete_state(project_id, DIRECTORY_AGENT_TYPE)
        await inner_session.commit()

        logger.info(
            "三阶段目录结构生成完成: project_id=%s, dirs=%d, files=%d",
            project_id,
            dirs_created,
            files_created,
        )

        # 最终质量评估
        final_evaluator = QualityEvaluator(
            profile=profile,
            decision=decision,
            output=output,
        )
        final_metrics = final_evaluator.evaluate()

        # 发送完成事件
        yield sse_event(
            "structure",
            {
                "directories": [d.model_dump() for d in output.directories],
                "files": [f.model_dump() for f in output.files],
                "shared_modules": output.shared_modules,
                "architecture_notes": output.architecture_notes,
            },
        )

        yield sse_event(
            "complete",
            {
                "success": True,
                "directories_created": dirs_created,
                "files_created": files_created,
                "total_modules": len(modules),
                "architecture_pattern": decision.pattern.value,
                "quality_score": final_metrics.overall_score,
                "quality_grade": final_metrics.get_grade(),
                "message": f"目录结构生成完成: {dirs_created}个目录, {files_created}个文件, 质量等级{final_metrics.get_grade()}",
            },
        )

    except Exception as e:
        logger.error("三阶段目录生成失败: %s", e, exc_info=True)
        # 保存错误状态（可以恢复）
        try:
            await inner_state_repo.save_state(
                project_id=project_id,
                agent_type=DIRECTORY_AGENT_TYPE,
                current_phase="error",
                state_data={"error": str(e)},
                progress_percent=0,
                progress_message=f"发生错误: {str(e)[:100]}",
                status="paused",
            )
            await inner_session.commit()
        except Exception:
            pass

        yield sse_event("error", {"message": str(e)})


__all__ = ["router"]

