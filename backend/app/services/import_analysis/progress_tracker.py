"""
分析进度跟踪器

管理导入分析的进度状态和阶段信息。
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.novel import NovelProject

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    分析进度跟踪器

    负责更新和查询项目的分析进度状态。
    """

    # 分析阶段定义（按执行顺序排列）
    STAGES = [
        ('generating_analysis_data', '生成分析数据'),    # 阶段1: 逐章生成分析数据
        ('analyzing_chapters', '生成章节摘要'),          # 阶段2: 逐章生成摘要
        ('generating_outlines', '更新章节大纲'),         # 阶段3: 更新章节大纲
        ('generating_part_outlines', '生成分部大纲'),    # 阶段4: 长篇才有
        ('extracting_blueprint', '反推蓝图信息'),        # 阶段5: 利用分析数据反推蓝图
    ]

    # 状态常量
    STATUS_PENDING = 'pending'
    STATUS_ANALYZING = 'analyzing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_project(self, project_id: str) -> Optional[NovelProject]:
        """获取项目"""
        result = await self.session.execute(
            select(NovelProject).where(NovelProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def initialize(
        self,
        project_id: str,
        total_chapters: int,
        needs_part_outlines: bool = False,
    ) -> None:
        """
        初始化分析进度

        Args:
            project_id: 项目ID
            total_chapters: 总章节数
            needs_part_outlines: 是否需要生成分部大纲
        """
        project = await self._get_project(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        # 计算分部数量（每25章一个分部）
        chapters_per_part = 25
        part_count = (total_chapters + chapters_per_part - 1) // chapters_per_part if needs_part_outlines else 0

        # 构建初始进度
        stages = {}
        for stage_key, stage_name in self.STAGES:
            if stage_key == 'generating_part_outlines' and not needs_part_outlines:
                # 跳过分部大纲阶段
                continue

            if stage_key in ('analyzing_chapters', 'generating_analysis_data'):
                total = total_chapters
            elif stage_key == 'generating_part_outlines':
                total = part_count  # 分部大纲的进度按分部数量计算
            else:
                total = 1

            stages[stage_key] = {
                'name': stage_name,
                'completed': 0,
                'total': total,
                'status': 'pending',
            }

        progress = {
            'status': self.STATUS_ANALYZING,
            'current_stage': 'generating_analysis_data',  # 第一阶段
            'stages': stages,
            'message': '正在初始化分析...',
            'started_at': datetime.utcnow().isoformat(),
            'error': None,
            'needs_part_outlines': needs_part_outlines,
        }

        project.import_analysis_status = self.STATUS_ANALYZING
        project.import_analysis_progress = progress
        await self.session.flush()

    async def update(
        self,
        project_id: str,
        stage: str,
        completed: int,
        total: int,
        message: Optional[str] = None,
    ) -> None:
        """
        更新分析进度

        Args:
            project_id: 项目ID
            stage: 当前阶段
            completed: 已完成数量
            total: 总数量
            message: 进度消息
        """
        project = await self._get_project(project_id)
        if not project or not project.import_analysis_progress:
            return

        progress = project.import_analysis_progress.copy()
        stages = progress.get('stages', {})

        if stage in stages:
            stages[stage]['completed'] = completed
            stages[stage]['total'] = total
            stages[stage]['status'] = 'in_progress'

            # 检查阶段是否完成
            if completed >= total:
                stages[stage]['status'] = 'completed'

        progress['stages'] = stages
        progress['current_stage'] = stage
        progress['message'] = message or f"正在{stages.get(stage, {}).get('name', stage)}..."

        project.import_analysis_progress = progress
        await self.session.flush()

    async def advance_stage(
        self,
        project_id: str,
        next_stage: str,
        message: Optional[str] = None,
    ) -> None:
        """
        推进到下一阶段

        Args:
            project_id: 项目ID
            next_stage: 下一阶段
            message: 消息
        """
        project = await self._get_project(project_id)
        if not project or not project.import_analysis_progress:
            return

        progress = project.import_analysis_progress.copy()
        stages = progress.get('stages', {})

        # 标记当前阶段完成
        current_stage = progress.get('current_stage')
        if current_stage and current_stage in stages:
            stages[current_stage]['status'] = 'completed'
            stages[current_stage]['completed'] = stages[current_stage]['total']

        # 开始新阶段
        if next_stage in stages:
            stages[next_stage]['status'] = 'in_progress'
            progress['current_stage'] = next_stage
            stage_name = stages[next_stage].get('name', next_stage)
            progress['message'] = message or f"正在{stage_name}..."

        progress['stages'] = stages
        project.import_analysis_progress = progress
        await self.session.flush()

    async def mark_completed(self, project_id: str) -> None:
        """标记分析完成"""
        project = await self._get_project(project_id)
        if not project:
            return

        progress = project.import_analysis_progress or {}
        progress = progress.copy()

        # 标记所有阶段完成
        stages = progress.get('stages', {})
        for stage_key in stages:
            stages[stage_key]['status'] = 'completed'
            stages[stage_key]['completed'] = stages[stage_key]['total']

        progress['stages'] = stages
        progress['status'] = self.STATUS_COMPLETED
        progress['message'] = '分析完成'
        progress['completed_at'] = datetime.utcnow().isoformat()

        project.import_analysis_status = self.STATUS_COMPLETED
        project.import_analysis_progress = progress
        await self.session.flush()

    async def mark_failed(self, project_id: str, error: str) -> None:
        """标记分析失败"""
        project = await self._get_project(project_id)
        if not project:
            return

        progress = project.import_analysis_progress or {}
        progress = progress.copy()

        progress['status'] = self.STATUS_FAILED
        progress['error'] = error
        progress['message'] = f"分析失败: {error}"

        project.import_analysis_status = self.STATUS_FAILED
        project.import_analysis_progress = progress
        await self.session.flush()

    async def mark_cancelled(self, project_id: str) -> None:
        """标记分析取消"""
        project = await self._get_project(project_id)
        if not project:
            return

        progress = project.import_analysis_progress or {}
        progress = progress.copy()

        progress['status'] = self.STATUS_CANCELLED
        progress['message'] = '分析已取消'

        project.import_analysis_status = self.STATUS_CANCELLED
        project.import_analysis_progress = progress
        await self.session.flush()

    async def get_status(self, project_id: str) -> Dict[str, Any]:
        """
        获取分析状态

        Returns:
            {
                'status': 'analyzing',
                'current_stage': 'analyzing_chapters',
                'stages': {...},
                'message': '...',
                'overall_progress': 50,  # 总体进度百分比
            }
        """
        project = await self._get_project(project_id)
        if not project:
            return {'status': 'not_found', 'message': '项目不存在'}

        if not project.import_analysis_progress:
            return {
                'status': project.import_analysis_status or 'pending',
                'message': '等待开始分析',
            }

        progress = project.import_analysis_progress.copy()

        # 计算总体进度
        stages = progress.get('stages', {})
        total_items = 0
        completed_items = 0
        for stage_info in stages.values():
            total_items += stage_info.get('total', 0)
            completed_items += stage_info.get('completed', 0)

        overall_progress = int(completed_items / total_items * 100) if total_items > 0 else 0
        progress['overall_progress'] = overall_progress

        return progress

    async def is_cancelled(self, project_id: str) -> bool:
        """检查是否已取消"""
        project = await self._get_project(project_id)
        if not project:
            return True

        return project.import_analysis_status == self.STATUS_CANCELLED

    async def resume(self, project_id: str) -> None:
        """
        恢复之前中断的分析

        将状态重置为 analyzing，保留进度信息以便从断点继续。
        """
        project = await self._get_project(project_id)
        if not project:
            raise ValueError(f"项目不存在: {project_id}")

        if not project.import_analysis_progress:
            raise ValueError("没有之前的进度信息可恢复")

        progress = project.import_analysis_progress.copy()

        # 重置状态
        progress['status'] = self.STATUS_ANALYZING
        progress['error'] = None
        progress['message'] = '正在恢复分析...'

        # 重置当前阶段的状态为 in_progress
        current_stage = progress.get('current_stage')
        if current_stage and current_stage in progress.get('stages', {}):
            progress['stages'][current_stage]['status'] = 'in_progress'

        project.import_analysis_status = self.STATUS_ANALYZING
        project.import_analysis_progress = progress
        await self.session.flush()

        logger.info("项目 %s 分析已恢复，将从阶段 '%s' 继续", project_id, current_stage)
