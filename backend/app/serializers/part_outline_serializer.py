"""
PartOutline 序列化工具

目标：将 PartOutline（ORM）→ PartOutlineSchema（Pydantic）的字段映射集中到单一真源，
避免在 serializer/service 两处并行维护导致默认值与字段漂移。
"""

from __future__ import annotations

from ..models.part_outline import PartOutline
from ..schemas.novel import PartOutline as PartOutlineSchema


def build_part_outline_schema(part: PartOutline) -> PartOutlineSchema:
    """将数据库模型转换为 Pydantic Schema（字段与默认值策略保持一致）"""
    return PartOutlineSchema(
        part_number=part.part_number,
        title=part.title or "",
        start_chapter=part.start_chapter,
        end_chapter=part.end_chapter,
        summary=part.summary or "",
        theme=part.theme or "",
        key_events=part.key_events or [],
        character_arcs=part.character_arcs or {},
        conflicts=part.conflicts or [],
        ending_hook=part.ending_hook,
        generation_status=part.generation_status,
        progress=part.progress,
    )

