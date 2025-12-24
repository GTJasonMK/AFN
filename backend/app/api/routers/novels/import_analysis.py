"""
导入分析路由

处理外部小说文件的导入和分析功能。
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, File, UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_import_analysis_service,
)
from ....db.session import get_session
from ....exceptions import ResourceNotFoundError, InvalidParameterError
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService
from ....services.import_analysis import ImportAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/import-txt")
async def import_txt_file(
    project_id: str,
    file: UploadFile = File(...),
    novel_service: NovelService = Depends(get_novel_service),
    import_service: ImportAnalysisService = Depends(get_import_analysis_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    导入TXT文件到项目

    将外部小说TXT文件解析并导入到指定项目中。
    自动检测编码和章节结构。

    Args:
        project_id: 项目ID
        file: TXT文件

    Returns:
        导入结果，包含章节数量、解析信息等
    """
    # 验证项目所有权
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 验证文件类型
    if not file.filename or not file.filename.lower().endswith('.txt'):
        raise InvalidParameterError("文件类型", "仅支持TXT文件格式")

    # 读取文件内容
    file_content = await file.read()
    if not file_content:
        raise InvalidParameterError("文件内容", "文件内容为空")

    # 执行导入
    result = await import_service.import_txt(
        project_id=project_id,
        file_content=file_content,
        user_id=desktop_user.id,
    )

    await session.commit()

    logger.info(
        "用户 %s 导入TXT到项目 %s，共 %d 章",
        desktop_user.id,
        project_id,
        result.total_chapters,
    )

    return {
        "status": "success",
        "total_chapters": result.total_chapters,
        "chapters": result.chapters,
        "parse_info": result.parse_info,
    }


@router.post("/{project_id}/analyze")
async def start_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    novel_service: NovelService = Depends(get_novel_service),
    import_service: ImportAnalysisService = Depends(get_import_analysis_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, str]:
    """
    开始分析导入的小说

    启动后台分析任务，包括：
    1. 批量生成章节摘要
    2. 更新章节大纲
    3. 生成分部大纲（长篇）
    4. 反推蓝图
    5. 生成分析数据

    分析进度可通过 GET /analyze/status 接口获取。

    Args:
        project_id: 项目ID

    Returns:
        分析启动状态
    """
    # 验证项目所有权
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 验证项目是已导入状态
    if not project.is_imported:
        raise InvalidParameterError("项目状态", "该项目不是导入项目，无法执行分析")

    # 检查是否已在分析中
    if project.import_analysis_status == "analyzing":
        raise InvalidParameterError("分析状态", "项目正在分析中，请勿重复启动")

    # 更新状态为分析中
    project.import_analysis_status = "analyzing"
    await session.commit()

    # 创建新的session用于后台任务
    # 因为后台任务需要独立的数据库连接
    async def run_analysis():
        from ....db.session import AsyncSessionLocal
        from ....services.llm_service import LLMService
        from ....services.prompt_service import PromptService
        from sqlalchemy import select, update
        from ....models.novel import NovelProject

        async with AsyncSessionLocal() as bg_session:
            try:
                llm_service = LLMService(bg_session)
                prompt_service = PromptService(bg_session)
                bg_import_service = ImportAnalysisService(
                    session=bg_session,
                    llm_service=llm_service,
                    prompt_service=prompt_service,
                )
                await bg_import_service.start_analysis(
                    project_id=project_id,
                    user_id=desktop_user.id,
                )
            except Exception as e:
                logger.exception("后台分析任务失败: %s", e)
                # 确保失败时更新状态
                try:
                    await bg_session.execute(
                        update(NovelProject)
                        .where(NovelProject.id == project_id)
                        .values(
                            import_analysis_status='failed',
                            import_analysis_progress={'error': str(e)}
                        )
                    )
                    await bg_session.commit()
                except Exception as update_error:
                    logger.error("更新失败状态时出错: %s", update_error)

    background_tasks.add_task(run_analysis)

    logger.info("用户 %s 启动项目 %s 的分析任务", desktop_user.id, project_id)

    return {
        "status": "started",
        "message": "分析任务已启动，请通过状态接口查询进度",
    }


@router.get("/{project_id}/analyze/status")
async def get_analysis_status(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    import_service: ImportAnalysisService = Depends(get_import_analysis_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, Any]:
    """
    获取分析进度

    返回当前分析状态和进度信息。

    Args:
        project_id: 项目ID

    Returns:
        分析状态和进度信息
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    if not project.is_imported:
        raise InvalidParameterError("项目状态", "该项目不是导入项目")

    # 使用ProgressTracker获取完整的进度信息（包括overall_progress）
    progress = await import_service.progress.get_status(project_id)

    return {
        "status": project.import_analysis_status or "pending",
        "progress": progress,
        "is_imported": project.is_imported,
    }


@router.post("/{project_id}/analyze/cancel")
async def cancel_analysis(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    import_service: ImportAnalysisService = Depends(get_import_analysis_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> Dict[str, str]:
    """
    取消分析任务

    标记分析任务为取消状态。正在执行的批次会在完成后停止。

    Args:
        project_id: 项目ID

    Returns:
        取消状态
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)

    if not project.is_imported:
        raise InvalidParameterError("项目状态", "该项目不是导入项目")

    if project.import_analysis_status != "analyzing":
        raise InvalidParameterError("分析状态", "项目不在分析中，无法取消")

    # 标记为取消
    await import_service.progress.mark_cancelled(project_id)
    await session.commit()

    logger.info("用户 %s 取消项目 %s 的分析任务", desktop_user.id, project_id)

    return {
        "status": "cancelled",
        "message": "分析任务已标记为取消",
    }
