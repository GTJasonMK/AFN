"""
项目状态校验工具

提供统一的项目状态校验功能，包括装饰器和校验函数。
用于确保项目在正确的状态下执行特定操作。
"""

from typing import List, Optional, Set, Union

from .state_machine import ProjectStatus
from ..exceptions import InvalidStateTransitionError


# ============================================================================
# 预定义的状态组合
# ============================================================================

# 允许生成章节大纲的状态
OUTLINE_GENERATION_STATES: Set[ProjectStatus] = {
    ProjectStatus.BLUEPRINT_READY,
    ProjectStatus.PART_OUTLINES_READY,
    ProjectStatus.CHAPTER_OUTLINES_READY,
    ProjectStatus.WRITING,
}

# 允许生成章节内容的状态
# Bug 15, 16 修复: 添加 COMPLETED 状态，允许完结项目继续编辑章节
CHAPTER_GENERATION_STATES: Set[ProjectStatus] = {
    ProjectStatus.CHAPTER_OUTLINES_READY,
    ProjectStatus.WRITING,
    ProjectStatus.COMPLETED,  # 允许在完成状态下继续编辑
}

# 允许生成分部大纲的状态
PART_OUTLINE_STATES: Set[ProjectStatus] = {
    ProjectStatus.BLUEPRINT_READY,
}

# 允许编辑蓝图的状态
BLUEPRINT_EDIT_STATES: Set[ProjectStatus] = {
    ProjectStatus.DRAFT,
    ProjectStatus.BLUEPRINT_READY,
}

# 写作中状态（用于连贯性检查）
WRITING_STATES: Set[ProjectStatus] = {
    ProjectStatus.WRITING,
}


# ============================================================================
# 校验函数
# ============================================================================

def validate_project_status(
    project_status: str,
    allowed_statuses: Union[Set[ProjectStatus], List[ProjectStatus]],
    operation_name: str = "此操作",
) -> None:
    """
    验证项目状态是否允许执行操作

    Args:
        project_status: 项目当前状态（字符串）
        allowed_statuses: 允许的状态集合
        operation_name: 操作名称（用于错误消息）

    Raises:
        InvalidStateTransitionError: 当状态不允许时抛出

    示例:
        validate_project_status(
            project.status,
            OUTLINE_GENERATION_STATES,
            "生成章节大纲"
        )
    """
    allowed_values = {s.value for s in allowed_statuses}
    if project_status not in allowed_values:
        allowed_names = ", ".join(sorted(allowed_values))
        raise InvalidStateTransitionError(
            f"当前项目状态 '{project_status}' 不允许执行{operation_name}。"
            f"允许的状态: {allowed_names}"
        )


def check_writing_coherence(
    project_status: str,
    start_chapter: int,
    max_generated_chapter: int,
    operation_name: str = "生成章节大纲",
) -> None:
    """
    检查写作状态下的连贯性约束

    在WRITING状态下，只允许追加生成已生成正文之后的内容，
    防止在已有正文的章节之前插入新内容导致上下文不一致。

    Args:
        project_status: 项目当前状态
        start_chapter: 请求生成的起始章节号
        max_generated_chapter: 已生成正文的最大章节号
        operation_name: 操作名称

    Raises:
        InvalidStateTransitionError: 当违反连贯性约束时抛出
    """
    if project_status != ProjectStatus.WRITING.value:
        return

    if max_generated_chapter > 0 and start_chapter <= max_generated_chapter:
        raise InvalidStateTransitionError(
            f"连贯性保护：已生成到第 {max_generated_chapter} 章正文，"
            f"只能追加生成第 {max_generated_chapter + 1} 章之后的内容。"
            f"当前请求从第 {start_chapter} 章开始{operation_name}与已生成正文冲突。"
        )


def get_max_generated_chapter(chapters: list) -> int:
    """
    获取已生成正文的最大章节号

    Args:
        chapters: 章节列表（需要有chapter_number和selected_version_id属性）

    Returns:
        int: 最大已生成章节号，没有则返回0
    """
    max_chapter = 0
    for ch in chapters:
        if getattr(ch, 'selected_version_id', None) is not None:
            chapter_num = getattr(ch, 'chapter_number', 0)
            max_chapter = max(max_chapter, chapter_num)
    return max_chapter


# ============================================================================
# 便捷校验函数
# ============================================================================

def require_outline_generation_status(project_status: str) -> None:
    """要求项目处于可生成章节大纲的状态"""
    validate_project_status(project_status, OUTLINE_GENERATION_STATES, "生成章节大纲")


def require_chapter_generation_status(project_status: str) -> None:
    """要求项目处于可生成章节内容的状态"""
    validate_project_status(project_status, CHAPTER_GENERATION_STATES, "生成章节内容")


def require_part_outline_status(project_status: str) -> None:
    """要求项目处于可生成分部大纲的状态"""
    validate_project_status(project_status, PART_OUTLINE_STATES, "生成分部大纲")


def require_blueprint_edit_status(project_status: str) -> None:
    """要求项目处于可编辑蓝图的状态"""
    validate_project_status(project_status, BLUEPRINT_EDIT_STATES, "编辑蓝图")


# ============================================================================
# 状态检查辅助函数
# ============================================================================

def is_in_writing_phase(project_status: str) -> bool:
    """检查项目是否处于写作阶段"""
    return project_status == ProjectStatus.WRITING.value


def is_completed(project_status: str) -> bool:
    """检查项目是否已完成"""
    return project_status == ProjectStatus.COMPLETED.value


def can_generate_outlines(project_status: str) -> bool:
    """检查是否可以生成大纲"""
    return project_status in {s.value for s in OUTLINE_GENERATION_STATES}


def can_generate_chapters(project_status: str) -> bool:
    """检查是否可以生成章节"""
    return project_status in {s.value for s in CHAPTER_GENERATION_STATES}
