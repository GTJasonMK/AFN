"""
部分大纲模型工厂

负责根据解析后的数据创建PartOutline ORM模型。
"""

import uuid
from typing import Dict, List

from ...models.part_outline import PartOutline


class PartOutlineModelFactory:
    """
    部分大纲模型工厂

    负责根据解析后的数据创建PartOutline ORM模型实例。
    """

    def create_from_dict(
        self,
        project_id: str,
        part_data: Dict,
        default_part_number: int = 1,
    ) -> PartOutline:
        """
        根据解析后的数据创建单个PartOutline模型

        Args:
            project_id: 项目ID
            part_data: 部分大纲数据
            default_part_number: 默认部分编号（当数据中未指定时使用）

        Returns:
            PartOutline: PartOutline模型
        """
        part_number = part_data.get("part_number", default_part_number)

        return PartOutline(
            id=str(uuid.uuid4()),
            project_id=project_id,
            part_number=part_number,
            title=part_data.get("title", f"第{part_number}部分"),
            start_chapter=part_data.get("start_chapter"),
            end_chapter=part_data.get("end_chapter"),
            summary=part_data.get("summary", ""),
            theme=part_data.get("theme", ""),
            key_events=part_data.get("key_events", []),
            character_arcs=part_data.get("character_arcs", {}),
            conflicts=part_data.get("conflicts", []),
            ending_hook=part_data.get("ending_hook"),
            generation_status="pending",
            progress=0,
        )

    def create_batch(
        self,
        project_id: str,
        parts_data: List[Dict],
    ) -> List[PartOutline]:
        """
        根据解析后的数据批量创建PartOutline模型列表

        Args:
            project_id: 项目ID
            parts_data: 部分大纲数据列表

        Returns:
            List[PartOutline]: PartOutline模型列表
        """
        part_outlines = []
        for idx, part_data in enumerate(parts_data):
            part = self.create_from_dict(
                project_id=project_id,
                part_data=part_data,
                default_part_number=idx + 1,
            )
            part_outlines.append(part)
        return part_outlines


# 模块级单例
_default_factory = None


def get_part_outline_factory() -> PartOutlineModelFactory:
    """获取默认的部分大纲模型工厂实例"""
    global _default_factory
    if _default_factory is None:
        _default_factory = PartOutlineModelFactory()
    return _default_factory


__all__ = [
    "PartOutlineModelFactory",
    "get_part_outline_factory",
]
