"""
章节生成错误格式化工具

将章节生成错误转换为用户友好的消息。
"""

from typing import Tuple


class ChapterErrorFormatter:
    """章节生成错误格式化器

    根据错误消息内容识别错误类型，提供更有用的建议。
    """

    # 错误关键词映射
    ERROR_PATTERNS = {
        'llm': {
            'keywords': ['ai服务', 'llm', 'api key', 'openai', '模型'],
            'title': 'AI服务错误',
            'template': (
                "第{chapter}章生成失败：AI服务暂时不可用\n\n"
                "请检查：\n"
                "- LLM配置是否正确\n"
                "- API密钥是否有效\n"
                "- 网络连接是否正常"
            ),
        },
        'timeout': {
            'keywords': ['超时', 'timeout', 'timed out'],
            'title': '生成超时',
            'template': (
                "第{chapter}章生成超时\n\n"
                "这可能是因为：\n"
                "- 章节内容较长，需要更多生成时间\n"
                "- 服务器负载较高\n\n"
                "请稍后重试。"
            ),
        },
        'connection': {
            'keywords': ['连接', 'connection', 'network'],
            'title': '连接失败',
            'template': (
                "第{chapter}章生成失败：网络连接问题\n\n"
                "请检查：\n"
                "- 后端服务是否已启动\n"
                "- 网络连接是否正常"
            ),
        },
        'json': {
            'keywords': ['json', '解析', '格式'],
            'title': '响应格式错误',
            'template': (
                "第{chapter}章生成失败：AI响应格式异常\n\n"
                "这可能是由于AI模型返回了非预期的内容。\n"
                "请重试生成。"
            ),
        },
    }

    @classmethod
    def format(cls, error_msg: str, chapter_number: int) -> Tuple[str, str]:
        """格式化章节生成错误消息

        Args:
            error_msg: 原始错误消息
            chapter_number: 章节号

        Returns:
            (title, message) 元组
        """
        error_lower = (error_msg or "").lower()

        # 遍历错误模式查找匹配
        for pattern_info in cls.ERROR_PATTERNS.values():
            if any(kw in error_lower for kw in pattern_info['keywords']):
                return (
                    pattern_info['title'],
                    pattern_info['template'].format(chapter=chapter_number)
                )

        # 特殊处理：章节大纲相关错误
        if '大纲' in error_msg:
            return (
                '大纲错误',
                f"第{chapter_number}章生成失败：章节大纲问题\n\n"
                f"{error_msg}\n\n"
                "请检查章节大纲是否已正确生成。"
            )

        # 默认错误
        return ('生成失败', f"第{chapter_number}章生成失败\n\n{error_msg}")


# 便捷函数
def format_chapter_error(error_msg: str, chapter_number: int) -> Tuple[str, str]:
    """格式化章节生成错误（便捷函数）"""
    return ChapterErrorFormatter.format(error_msg, chapter_number)
