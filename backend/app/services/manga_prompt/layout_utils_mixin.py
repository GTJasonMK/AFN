"""
排版工具Mixin

提供排版结果序列化、反序列化和类型转换相关的方法。
"""

import logging
from typing import Optional, Any, TYPE_CHECKING

from .schemas import MangaStyle
from .layout_schemas import (
    LayoutType,
    PageSize,
    LayoutGenerationResult,
    MangaLayout,
    Page,
    Panel,
    PanelImportance,
    CompositionHint,
)

if TYPE_CHECKING:
    from .layout_service import LayoutService

logger = logging.getLogger(__name__)


class LayoutUtilsMixin:
    """排版工具相关方法的Mixin"""

    # 需要被主类提供的属性
    layout_service: "LayoutService"

    def _get_layout_type(self, style: MangaStyle) -> LayoutType:
        """根据漫画风格获取排版类型"""
        mapping = {
            MangaStyle.MANGA: LayoutType.TRADITIONAL_MANGA,
            MangaStyle.ANIME: LayoutType.TRADITIONAL_MANGA,
            MangaStyle.COMIC: LayoutType.COMIC,
            MangaStyle.WEBTOON: LayoutType.WEBTOON,
        }
        return mapping.get(style, LayoutType.TRADITIONAL_MANGA)

    def _serialize_layout_result(
        self, layout_result: Optional[LayoutGenerationResult]
    ) -> Optional[dict]:
        """序列化排版结果用于存储"""
        if not layout_result or not layout_result.success:
            return None

        layout = layout_result.layout
        return {
            "success": True,
            "layout": {
                "layout_type": layout.layout_type.value,
                "page_size": layout.page_size.value,
                "reading_direction": layout.reading_direction,
                "total_pages": layout.total_pages,
                "total_panels": layout.total_panels,
                "pages": [
                    {
                        "page_number": page.page_number,
                        "panels": [
                            {
                                "panel_id": panel.panel_id,
                                "scene_id": panel.scene_id,
                                "x": panel.x,
                                "y": panel.y,
                                "width": panel.width,
                                "height": panel.height,
                                "importance": panel.importance.value,
                                "composition": panel.composition.value,
                                "camera_angle": panel.camera_angle,
                            }
                            for panel in page.panels
                        ],
                    }
                    for page in layout.pages
                ],
            },
        }

    def _restore_layout_result(self, data: dict) -> Optional[LayoutGenerationResult]:
        """从存储的数据恢复排版结果"""
        if not data or not data.get("success"):
            return None

        layout_data = data.get("layout", {})

        pages = []
        for page_data in layout_data.get("pages", []):
            panels = []
            for panel_data in page_data.get("panels", []):
                panel = Panel(
                    panel_id=panel_data.get("panel_id", 0),
                    scene_id=panel_data.get("scene_id", 0),
                    x=panel_data.get("x", 0),
                    y=panel_data.get("y", 0),
                    width=panel_data.get("width", 0.5),
                    height=panel_data.get("height", 0.5),
                    importance=self._parse_importance(panel_data.get("importance")),
                    composition=self._parse_composition(panel_data.get("composition")),
                    camera_angle=panel_data.get("camera_angle"),
                )
                panels.append(panel)

            page = Page(
                page_number=page_data.get("page_number", 0),
                panels=panels,
            )
            pages.append(page)

        layout = MangaLayout(
            layout_type=self._get_layout_type_enum(
                layout_data.get("layout_type", "traditional_manga")
            ),
            page_size=self._get_page_size_enum(layout_data.get("page_size", "A4")),
            reading_direction=layout_data.get("reading_direction", "ltr"),
            pages=pages,
            total_pages=layout_data.get("total_pages", len(pages)),
            total_panels=layout_data.get(
                "total_panels", sum(len(p.panels) for p in pages)
            ),
        )

        return LayoutGenerationResult(success=True, layout=layout)

    def _parse_importance(self, value: Optional[str]) -> PanelImportance:
        """解析重要性枚举值"""
        if not value:
            return PanelImportance.NORMAL
        try:
            return PanelImportance(value)
        except ValueError:
            return PanelImportance.NORMAL

    def _parse_composition(self, value: Optional[str]) -> CompositionHint:
        """解析构图枚举值"""
        if not value:
            return CompositionHint.MEDIUM_SHOT
        try:
            return CompositionHint(value)
        except ValueError:
            return CompositionHint.MEDIUM_SHOT

    def _get_layout_type_enum(self, value: str) -> LayoutType:
        """获取排版类型枚举"""
        try:
            return LayoutType(value)
        except ValueError:
            return LayoutType.TRADITIONAL_MANGA

    def _get_page_size_enum(self, value: str) -> PageSize:
        """获取页面尺寸枚举"""
        try:
            return PageSize(value)
        except ValueError:
            return PageSize.A4
