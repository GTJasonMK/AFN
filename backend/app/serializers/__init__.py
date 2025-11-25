"""
序列化器模块

提供ORM模型到Pydantic Schema的转换逻辑。
将序列化逻辑从Service层分离，保持Service层专注于业务逻辑。
"""

from .novel_serializer import NovelSerializer

__all__ = ["NovelSerializer"]
