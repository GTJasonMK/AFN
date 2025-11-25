"""
通用格式化工具模块

提供项目中常用的数据格式化方法，避免代码重复
"""

from themes.theme_manager import theme_manager


def get_project_status_text(status: str) -> str:
    """
    获取项目状态的中文文本

    Args:
        status: 项目状态代码

    Returns:
        状态的中文文本，如果状态未知则返回"未知状态"
    """
    status_map = {
        'draft': '草稿',
        'blueprint_ready': '蓝图就绪',
        'part_outlines_ready': '部分大纲就绪',
        'chapter_outlines_ready': '章节大纲就绪',
        'writing': '写作中',
        'completed': '已完成'
    }
    return status_map.get(status, '未知状态')


def get_chapter_status_text(status: str) -> str:
    """
    获取章节生成状态的中文文本

    支持后端ChapterGenerationStatus枚举的所有状态值

    Args:
        status: 章节状态代码

    Returns:
        状态的中文文本，如果状态未知则返回原状态值
    """
    status_map = {
        'not_generated': '未生成',
        'generating': '生成中',
        'evaluating': '评审中',
        'selecting': '选择中',
        'successful': '已完成',
        'failed': '失败',
        'evaluation_failed': '评审失败',
        'waiting_for_confirm': '等待确认',
        # 向后兼容旧的状态值
        'in_progress': '生成中',
        'completed': '已完成'
    }
    return status_map.get(status, status)


def get_status_badge_style(status: str) -> str:
    """
    获取状态标签的CSS样式

    支持章节生成的所有状态，返回对应的主题颜色

    Args:
        status: 状态代码（支持章节状态）

    Returns:
        包含background-color和color的CSS样式字符串
    """
    # 成功状态
    if status in ('completed', 'successful'):
        return f"background-color: {theme_manager.SUCCESS_BG}; color: {theme_manager.SUCCESS};"
    # 进行中状态
    elif status in ('in_progress', 'generating', 'evaluating', 'selecting', 'waiting_for_confirm'):
        return f"background-color: {theme_manager.ACCENT_PALE}; color: {theme_manager.ACCENT_PRIMARY};"
    # 失败状态
    elif status in ('failed', 'evaluation_failed'):
        return f"background-color: {theme_manager.ERROR_BG}; color: {theme_manager.ERROR};"
    # 默认状态（未生成等）
    else:
        return f"background-color: {theme_manager.BG_TERTIARY}; color: {theme_manager.TEXT_SECONDARY};"


def count_chinese_characters(text: str) -> int:
    """
    统计文本中的中文字符数量

    Args:
        text: 要统计的文本内容

    Returns:
        中文字符数量（不包括标点、英文等）
    """
    if not text:
        return 0
    # 统计Unicode范围 U+4E00 到 U+9FFF 的汉字
    return len([c for c in text if '\u4e00' <= c <= '\u9fff'])


def format_word_count(count: int) -> str:
    """
    格式化字数显示

    Args:
        count: 字数

    Returns:
        格式化后的字数文本，如 "1,234 字" 或 "1.2万字"
    """
    if count < 10000:
        return f"{count:,} 字"
    else:
        return f"{count / 10000:.1f}万字"
