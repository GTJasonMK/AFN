"""
通用格式化工具模块

提供项目中常用的数据格式化方法，避免代码重复
"""

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
