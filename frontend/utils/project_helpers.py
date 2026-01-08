"""
项目辅助函数

提供与项目数据处理相关的通用函数。
"""

from typing import Any, Dict, Optional


def get_blueprint(project: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """获取蓝图数据，支持小说和编程项目

    根据项目类型返回对应的蓝图数据：
    - 小说项目：返回 project['blueprint']
    - 编程项目：返回 project['coding_blueprint']

    Args:
        project: 项目数据字典

    Returns:
        dict: 蓝图数据，如果不存在则返回空字典
    """
    if not project:
        return {}
    project_type = project.get('project_type', 'novel')
    if project_type == 'coding':
        return project.get('coding_blueprint') or {}
    return project.get('blueprint') or {}


__all__ = ['get_blueprint']
