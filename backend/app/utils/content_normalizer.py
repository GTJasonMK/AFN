"""
文本统计工具模块

提供后端统一使用的中文字符计数函数。
"""


def count_chinese_characters(text: str) -> int:
    """
    统计文本中的中文字符数量（只统计汉字，不包括标点、英文、空格等）

    这是用于章节字数统计的标准函数，确保前后端字数一致。

    Args:
        text: 要统计的文本内容

    Returns:
        中文汉字数量
    """
    if not text:
        return 0
    # 统计Unicode范围 U+4E00 到 U+9FFF 的汉字（CJK统一汉字基本区）
    # 这与前端 frontend/utils/formatters.py 中的 count_chinese_characters 保持一致
    return len([c for c in text if '\u4e00' <= c <= '\u9fff'])
