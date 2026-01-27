"""漫画页面布局通用字段与序列化工具。"""

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List, Optional, Type


DEFAULT_GUTTER_HORIZONTAL = 8
DEFAULT_GUTTER_VERTICAL = 8

@dataclass
class PageLayoutBase:
    """页面布局通用字段（不包含 panels 类型差异）。"""

    page_number: int
    layout_description: str = ""
    gutter_horizontal: int = DEFAULT_GUTTER_HORIZONTAL
    gutter_vertical: int = DEFAULT_GUTTER_VERTICAL

    PANEL_CLS: ClassVar[Optional[Type[Any]]] = None

    def build_layout_dict(self, *, panels: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建页面布局 dict（panels 由子类转换后传入）。"""
        return {
            "page_number": self.page_number,
            "panels": panels,
            "layout_description": self.layout_description,
            "gutter_horizontal": self.gutter_horizontal,
            "gutter_vertical": self.gutter_vertical,
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为 dict（要求子类提供 panels 字段且元素实现 to_dict）。"""
        panels = [p.to_dict() for p in getattr(self, "panels", [])]
        return self.build_layout_dict(panels=panels)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """从 dict 创建（要求子类设置 PANEL_CLS 且该类实现 from_dict）。"""
        layout_kwargs = cls.parse_layout_kwargs(data)
        panel_cls = cls.PANEL_CLS
        panels_data = data.get("panels", []) or []
        panels = [panel_cls.from_dict(p) for p in panels_data] if panel_cls else []
        return cls(panels=panels, **layout_kwargs)

    @classmethod
    def parse_layout_kwargs(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析页面布局字段为 kwargs（供子类 from_dict 复用）。"""
        return {
            "page_number": data.get("page_number", 1),
            "layout_description": data.get("layout_description", ""),
            "gutter_horizontal": data.get("gutter_horizontal", DEFAULT_GUTTER_HORIZONTAL),
            "gutter_vertical": data.get("gutter_vertical", DEFAULT_GUTTER_VERTICAL),
        }
