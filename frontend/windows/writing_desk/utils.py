"""
写作台工具函数
"""

from typing import Optional, Dict, Any


def extract_protagonist_name(project: Dict[str, Any]) -> Optional[str]:
    """从项目数据中提取主角名称

    检查蓝图中的角色列表，根据identity字段识别主角。
    如果没有明确标记为主角的角色，返回第一个角色的名字。

    Args:
        project: 项目数据字典

    Returns:
        主角名称，如果未找到则返回None
    """
    if not project:
        return None

    blueprint = project.get('blueprint', {})
    if not blueprint:
        return None

    characters = blueprint.get('characters', [])
    if not characters:
        return None

    # 先尝试找明确标记为主角的角色
    for char in characters:
        # 检查identity字段（蓝图生成的标准字段）
        identity = char.get('identity', '')
        if identity == '主角' or '主角' in identity:
            return char.get('name')
        # 兼容其他可能的字段格式
        if char.get('is_protagonist') or char.get('role') == '主角':
            return char.get('name')

    # 如果没有找到主角标记，返回第一个角色的名字
    first_char = characters[0]
    return first_char.get('name')
