"""
漫画排版服务

负责调用AI生成专业的漫画排版方案，包括：
- 页面布局规划
- 格子大小分配
- 构图建议
- 阅读流引导
- 叙事节拍分析
- 框线语言设计
- 翻页钩子规划
"""

import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession

from .layout_schemas import (
    LayoutType,
    PageSize,
    PanelImportance,
    CompositionHint,
    StoryBeat,
    FrameStyle,
    BleedType,
    FlowDirection,
    PageFunction,
    PageRhythm,
    Panel,
    Page,
    MangaLayout,
    LayoutGenerationRequest,
    LayoutGenerationResult,
    SceneCompositionGuide,
    RhythmSummary,
)
from .schemas import MangaStyle
from ...utils.json_utils import parse_llm_json_safe
from ..llm_wrappers import call_llm_json, LLMProfile

logger = logging.getLogger(__name__)


class LayoutService:
    """漫画排版服务"""

    def __init__(
        self,
        session: AsyncSession,
        llm_service,
        prompt_service=None,
    ):
        """
        初始化服务

        Args:
            session: 数据库会话
            llm_service: LLM服务
            prompt_service: 提示词服务
        """
        self.session = session
        self.llm_service = llm_service
        self.prompt_service = prompt_service

    async def generate_layout(
        self,
        chapter_content: str,
        scene_summaries: List[Dict[str, Any]],
        request: LayoutGenerationRequest,
        user_id: str,
    ) -> LayoutGenerationResult:
        """
        生成漫画排版方案

        Args:
            chapter_content: 章节内容概要
            scene_summaries: 场景简述列表，每个包含 scene_id, summary, emotion, characters
            request: 排版生成请求
            user_id: 用户ID

        Returns:
            排版生成结果
        """
        # 构建提示词
        system_prompt = await self._get_layout_prompt()
        user_prompt = self._build_user_prompt(
            chapter_content=chapter_content,
            scene_summaries=scene_summaries,
            request=request,
        )

        # 调用LLM生成排版
        try:
            llm_response = await call_llm_json(
                self.llm_service,
                LLMProfile.LAYOUT,
                system_prompt=system_prompt,
                user_content=user_prompt,
                user_id=int(user_id) if user_id else 0,
            )

            # 解析响应
            layout = self._parse_layout_response(llm_response, request)

            return LayoutGenerationResult(
                success=True,
                layout=layout,
                scene_panel_mapping=self._build_scene_panel_mapping(layout),
            )

        except Exception as e:
            logger.error("排版生成失败: %s", e)
            return LayoutGenerationResult(
                success=False,
                error_message=str(e),
            )

    async def _get_layout_prompt(self) -> str:
        """获取排版提示词模板"""
        if self.prompt_service:
            try:
                template = await self.prompt_service.get_prompt("manga_layout")
                if template:
                    return template
            except Exception as e:
                logger.warning("获取排版提示词模板失败: %s, 使用默认模板", e)

        return self._get_default_layout_prompt()

    def _get_default_layout_prompt(self) -> str:
        """获取默认排版提示词模板"""
        return """# 角色
你是专业的漫画分镜师和排版设计师。你精通：
- 漫画分镜和页面布局设计
- 视觉引导和阅读节奏控制
- 不同漫画风格的排版规范（日漫、美漫、条漫）
- 将文字叙述转化为视觉叙事结构

# 任务
根据章节内容和场景列表，设计专业的漫画排版方案。你需要决定：
1. 每个场景应该占多大的格子（重要程度）
2. 每页放置几个场景
3. 格子的排列方式
4. 每个场景的推荐构图类型

# 排版原则

## 1. 格子大小分配
- **主角镜头 (hero)**: 情感高潮、关键转折、震撼场景 -> 占页面50%以上，甚至整页
- **重要场景 (major)**: 重要对话、动作关键帧 -> 占页面25-40%
- **标准场景 (standard)**: 普通叙事、对话 -> 占页面15-25%
- **次要场景 (minor)**: 过渡、反应镜头 -> 占页面10-15%

## 2. 每页格数建议
- 节奏紧凑的场景：5-7格
- 普通叙事：4-6格
- 重要场景/战斗：2-4格
- 高潮/转折：1-2格（大格子）

## 3. 构图类型选择
| 场景类型 | 推荐构图 |
|---------|---------|
| 表情特写 | extreme close-up, close-up |
| 对话场景 | medium shot, over the shoulder |
| 动作场景 | full shot, wide shot |
| 环境介绍 | establishing shot, wide shot |
| 心理刻画 | close-up, point of view |
| 威压感 | worm's eye view (仰视) |
| 俯瞰全局 | bird's eye view |

# 输出格式
必须输出严格符合以下结构的JSON对象：

```json
{
  "layout_analysis": "用中文简述你的排版设计思路",
  "layout_type": "traditional_manga",
  "reading_direction": "ltr",
  "total_pages": 5,
  "pages": [
    {
      "page_number": 1,
      "page_note": "开篇建立镜头",
      "panels": [
        {
          "panel_id": 1,
          "scene_id": 1,
          "importance": "major",
          "composition": "establishing shot",
          "position": "top-full",
          "size_hint": "占页面上半部分",
          "x": 0,
          "y": 0,
          "width": 1.0,
          "height": 0.45
        }
      ]
    }
  ],
  "scene_composition_guide": {
    "1": {
      "composition": "establishing shot",
      "camera_angle": "slightly high angle",
      "framing_note": "展示整体环境"
    }
  }
}
```

# 字段说明
- importance: hero/major/standard/minor
- composition: 构图类型
- x,y,width,height: 0-1的相对值，(0,0)为左上角
- 确保格子不重叠，留出适当间距(约0.02-0.04)"""

    def _build_user_prompt(
        self,
        chapter_content: str,
        scene_summaries: List[Dict[str, Any]],
        request: LayoutGenerationRequest,
    ) -> str:
        """构建用户提示词"""
        # 构建场景列表描述
        scenes_text = ""
        for scene in scene_summaries:
            scene_id = scene.get("scene_id", 0)
            summary = scene.get("summary", "")
            emotion = scene.get("emotion", "")
            characters = scene.get("characters", [])

            scenes_text += f"""
场景 {scene_id}:
- 简述: {summary}
- 情感: {emotion}
- 角色: {', '.join(characters) if characters else '无'}
"""

        # 排版类型映射
        layout_type_map = {
            LayoutType.TRADITIONAL_MANGA: "传统漫画（分页阅读，适合印刷）",
            LayoutType.WEBTOON: "条漫（垂直滚动，适合手机阅读）",
            LayoutType.COMIC: "西方漫画（分页阅读，从左到右）",
            LayoutType.FOUR_PANEL: "四格漫画",
        }

        return f"""## 章节内容概要
{chapter_content[:1500]}...

## 场景列表（共{len(scene_summaries)}个场景）
{scenes_text}

## 排版偏好
- 类型: {layout_type_map.get(request.layout_type, "传统漫画")}
- 页面尺寸: {request.page_size.value}
- 阅读方向: {"从左到右" if request.reading_direction == "ltr" else "从右到左"}
- 每页平均格数: {request.panels_per_page}

## 重点场景（需要更大格子）
{request.emphasis_scenes if request.emphasis_scenes else "无指定"}

## 动作场景（需要动感排版）
{request.action_scenes if request.action_scenes else "无指定"}

请设计专业的漫画排版方案。"""

    def _parse_layout_response(
        self,
        response: str,
        request: LayoutGenerationRequest,
    ) -> MangaLayout:
        """解析LLM响应为排版数据"""
        data = parse_llm_json_safe(response)

        if not data:
            logger.error("无法解析排版响应: %s", response[:500])
            raise ValueError("排版响应解析失败")

        # 解析页面
        pages = []
        for page_data in data.get("pages", []):
            panels = []
            for panel_data in page_data.get("panels", []):
                panel = Panel(
                    panel_id=panel_data.get("panel_id", len(panels) + 1),
                    scene_id=panel_data.get("scene_id", 0),
                    x=float(panel_data.get("x", 0)),
                    y=float(panel_data.get("y", 0)),
                    width=float(panel_data.get("width", 0.5)),
                    height=float(panel_data.get("height", 0.5)),
                    importance=self._parse_importance(panel_data.get("importance")),
                    composition=self._parse_composition(panel_data.get("composition")),
                    camera_angle=panel_data.get("camera_angle"),
                    reading_order=panel_data.get("reading_order", 0),
                    # 新增字段
                    story_beat=self._parse_story_beat(panel_data.get("story_beat")),
                    frame_style=self._parse_frame_style(panel_data.get("frame_style")),
                    bleed=self._parse_bleed_type(panel_data.get("bleed")),
                    flow_direction=self._parse_flow_direction(panel_data.get("flow_direction")),
                    visual_focus=panel_data.get("visual_focus"),
                    size_hint=panel_data.get("size_hint"),
                )
                panels.append(panel)

            page = Page(
                page_number=page_data.get("page_number", len(pages) + 1),
                panels=panels,
                is_spread=page_data.get("is_spread", False),
                # 新增字段
                page_function=self._parse_page_function(page_data.get("page_function")),
                page_rhythm=self._parse_page_rhythm(page_data.get("page_rhythm")),
                page_note=page_data.get("page_note"),
                page_turn_hook=page_data.get("page_turn_hook"),
            )
            pages.append(page)

        # 计算总格数
        total_panels = sum(len(page.panels) for page in pages)

        # 解析场景构图指南
        scene_composition_guide = {}
        guide_data = data.get("scene_composition_guide", {})
        for scene_id, guide in guide_data.items():
            scene_composition_guide[str(scene_id)] = SceneCompositionGuide(
                recommended_composition=self._parse_composition(
                    guide.get("recommended_composition") or guide.get("composition")
                ),
                camera_angle=guide.get("camera_angle"),
                framing_note=guide.get("framing_note"),
                lighting_suggestion=guide.get("lighting_suggestion"),
                emotion_keywords=guide.get("emotion_keywords", []),
            )

        # 解析节奏统计
        rhythm_summary = None
        rhythm_data = data.get("rhythm_summary")
        if rhythm_data:
            rhythm_summary = RhythmSummary(
                total_scenes=rhythm_data.get("total_scenes", 0),
                hero_panels=rhythm_data.get("hero_panels", 0),
                major_panels=rhythm_data.get("major_panels", 0),
                standard_panels=rhythm_data.get("standard_panels", 0),
                minor_panels=rhythm_data.get("minor_panels", 0),
                micro_panels=rhythm_data.get("micro_panels", 0),
                average_panels_per_page=rhythm_data.get("average_panels_per_page", 0),
                climax_pages=rhythm_data.get("climax_pages", []),
                breathing_pages=rhythm_data.get("breathing_pages", []),
            )
        else:
            # 自动计算节奏统计
            rhythm_summary = self._calculate_rhythm_summary(pages)

        return MangaLayout(
            layout_type=request.layout_type,
            page_size=request.page_size,
            reading_direction=request.reading_direction,
            pages=pages,
            total_pages=len(pages),
            total_panels=total_panels,
            # 新增字段
            pacing_strategy=data.get("pacing_strategy"),
            layout_analysis=data.get("layout_analysis"),
            scene_composition_guide=scene_composition_guide,
            rhythm_summary=rhythm_summary,
        )

    def _calculate_rhythm_summary(self, pages: List[Page]) -> RhythmSummary:
        """自动计算节奏统计"""
        hero_panels = 0
        major_panels = 0
        standard_panels = 0
        minor_panels = 0
        micro_panels = 0
        total_panels = 0
        climax_pages = []
        breathing_pages = []

        for page in pages:
            page_panel_count = len(page.panels)
            total_panels += page_panel_count

            for panel in page.panels:
                if panel.importance == PanelImportance.HERO:
                    hero_panels += 1
                elif panel.importance == PanelImportance.MAJOR:
                    major_panels += 1
                elif panel.importance == PanelImportance.STANDARD:
                    standard_panels += 1
                elif panel.importance == PanelImportance.MINOR:
                    minor_panels += 1
                elif panel.importance == PanelImportance.MICRO:
                    micro_panels += 1

            # 判断高潮页（格子少且有hero/major）
            if page_panel_count <= 2 and any(
                p.importance in [PanelImportance.HERO, PanelImportance.MAJOR]
                for p in page.panels
            ):
                climax_pages.append(page.page_number)

            # 判断呼吸页（格子少且为aftermath）
            if page_panel_count <= 3 and page.page_function == PageFunction.AFTERMATH:
                breathing_pages.append(page.page_number)

        return RhythmSummary(
            total_scenes=total_panels,
            hero_panels=hero_panels,
            major_panels=major_panels,
            standard_panels=standard_panels,
            minor_panels=minor_panels,
            micro_panels=micro_panels,
            average_panels_per_page=total_panels / len(pages) if pages else 0,
            climax_pages=climax_pages,
            breathing_pages=breathing_pages,
        )

    def _parse_importance(self, value: str) -> PanelImportance:
        """解析重要性枚举"""
        if not value:
            return PanelImportance.STANDARD

        value = value.lower().strip()
        mapping = {
            "hero": PanelImportance.HERO,
            "major": PanelImportance.MAJOR,
            "standard": PanelImportance.STANDARD,
            "minor": PanelImportance.MINOR,
            "micro": PanelImportance.MICRO,
        }
        return mapping.get(value, PanelImportance.STANDARD)

    def _parse_story_beat(self, value: str) -> StoryBeat:
        """解析叙事节拍枚举"""
        if not value:
            return StoryBeat.DIALOGUE

        value = value.lower().strip()
        mapping = {
            "setup": StoryBeat.SETUP,
            "build-up": StoryBeat.BUILD_UP,
            "buildup": StoryBeat.BUILD_UP,
            "turn": StoryBeat.TURN,
            "climax": StoryBeat.CLIMAX,
            "aftermath": StoryBeat.AFTERMATH,
            "transition": StoryBeat.TRANSITION,
            "dialogue": StoryBeat.DIALOGUE,
            "action": StoryBeat.ACTION,
            "introspection": StoryBeat.INTROSPECTION,
            "flashback": StoryBeat.FLASHBACK,
        }
        return mapping.get(value, StoryBeat.DIALOGUE)

    def _parse_frame_style(self, value: str) -> FrameStyle:
        """解析框线风格枚举"""
        if not value:
            return FrameStyle.STANDARD

        value = value.lower().strip()
        mapping = {
            "standard": FrameStyle.STANDARD,
            "bold": FrameStyle.BOLD,
            "thin": FrameStyle.THIN,
            "rounded": FrameStyle.ROUNDED,
            "jagged": FrameStyle.JAGGED,
            "dashed": FrameStyle.DASHED,
            "borderless": FrameStyle.BORDERLESS,
            "diagonal": FrameStyle.DIAGONAL,
            "irregular": FrameStyle.IRREGULAR,
        }
        return mapping.get(value, FrameStyle.STANDARD)

    def _parse_bleed_type(self, value: str) -> BleedType:
        """解析出血类型枚举"""
        if not value:
            return BleedType.NONE

        value = value.lower().strip()
        mapping = {
            "none": BleedType.NONE,
            "full": BleedType.FULL,
            "top": BleedType.TOP,
            "bottom": BleedType.BOTTOM,
            "left": BleedType.LEFT,
            "right": BleedType.RIGHT,
            "horizontal": BleedType.HORIZONTAL,
            "vertical": BleedType.VERTICAL,
        }
        return mapping.get(value, BleedType.NONE)

    def _parse_flow_direction(self, value: str) -> FlowDirection:
        """解析视线引导方向枚举"""
        if not value:
            return FlowDirection.DOWN

        value = value.lower().strip()
        mapping = {
            "down": FlowDirection.DOWN,
            "right": FlowDirection.RIGHT,
            "left": FlowDirection.LEFT,
            "down-left": FlowDirection.DOWN_LEFT,
            "down-right": FlowDirection.DOWN_RIGHT,
            "center-focus": FlowDirection.CENTER_FOCUS,
            "next-page": FlowDirection.NEXT_PAGE,
        }
        return mapping.get(value, FlowDirection.DOWN)

    def _parse_page_function(self, value: str) -> PageFunction:
        """解析页面功能枚举"""
        if not value:
            return PageFunction.DIALOGUE

        value = value.lower().strip()
        mapping = {
            "setup": PageFunction.SETUP,
            "build": PageFunction.BUILD,
            "climax": PageFunction.CLIMAX,
            "aftermath": PageFunction.AFTERMATH,
            "transition": PageFunction.TRANSITION,
            "dialogue": PageFunction.DIALOGUE,
            "action": PageFunction.ACTION,
        }
        return mapping.get(value, PageFunction.DIALOGUE)

    def _parse_page_rhythm(self, value: str) -> PageRhythm:
        """解析页面节奏枚举"""
        if not value:
            return PageRhythm.MEDIUM

        value = value.lower().strip()
        mapping = {
            "slow": PageRhythm.SLOW,
            "medium": PageRhythm.MEDIUM,
            "fast": PageRhythm.FAST,
            "explosive": PageRhythm.EXPLOSIVE,
        }
        return mapping.get(value, PageRhythm.MEDIUM)

    def _parse_composition(self, value: str) -> CompositionHint:
        """解析构图枚举"""
        if not value:
            return CompositionHint.MEDIUM_SHOT

        value = value.lower().strip()
        mapping = {
            "extreme close-up": CompositionHint.EXTREME_CLOSEUP,
            "close-up": CompositionHint.CLOSEUP,
            "medium close-up": CompositionHint.MEDIUM_CLOSEUP,
            "medium shot": CompositionHint.MEDIUM_SHOT,
            "medium full shot": CompositionHint.MEDIUM_FULL,
            "full shot": CompositionHint.FULL_SHOT,
            "wide shot": CompositionHint.WIDE_SHOT,
            "establishing shot": CompositionHint.ESTABLISHING,
            "bird's eye view": CompositionHint.BIRDS_EYE,
            "worm's eye view": CompositionHint.WORMS_EYE,
            "over the shoulder": CompositionHint.OVER_SHOULDER,
            "point of view": CompositionHint.POV,
        }
        return mapping.get(value, CompositionHint.MEDIUM_SHOT)

    def _build_scene_panel_mapping(
        self,
        layout: MangaLayout,
    ) -> Dict[int, List[int]]:
        """构建场景到格子的映射"""
        mapping: Dict[int, List[int]] = {}

        for page in layout.pages:
            for panel in page.panels:
                scene_id = panel.scene_id
                if scene_id not in mapping:
                    mapping[scene_id] = []
                mapping[scene_id].append(panel.panel_id)

        return mapping

    def get_composition_for_scene(
        self,
        layout: MangaLayout,
        scene_id: int,
    ) -> Optional[CompositionHint]:
        """
        获取场景的构图建议

        Args:
            layout: 排版数据
            scene_id: 场景ID

        Returns:
            构图类型或None
        """
        for page in layout.pages:
            for panel in page.panels:
                if panel.scene_id == scene_id:
                    return panel.composition
        return None

    def get_panel_aspect_ratio(
        self,
        layout: MangaLayout,
        scene_id: int,
    ) -> Optional[str]:
        """
        获取场景对应格子的宽高比

        用于指导图片生成的尺寸

        Args:
            layout: 排版数据
            scene_id: 场景ID

        Returns:
            宽高比字符串如 "16:9", "1:1", "9:16" 等
        """
        for page in layout.pages:
            for panel in page.panels:
                if panel.scene_id == scene_id:
                    ratio = panel.width / panel.height
                    # 映射到常见比例
                    if ratio > 1.6:
                        return "16:9"  # 宽屏
                    elif ratio > 1.2:
                        return "4:3"  # 标准横向
                    elif ratio > 0.9:
                        return "1:1"  # 方形
                    elif ratio > 0.7:
                        return "3:4"  # 标准纵向
                    else:
                        return "9:16"  # 竖屏
        return "1:1"  # 默认方形

    def get_scene_layout_info(
        self,
        layout: MangaLayout,
        scene_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取场景的完整排版信息

        用于图片生成时提供排版上下文

        Args:
            layout: 排版数据
            scene_id: 场景ID

        Returns:
            包含构图、框线风格、出血等信息的字典
        """
        for page in layout.pages:
            for panel in page.panels:
                if panel.scene_id == scene_id:
                    # 获取场景构图指南
                    guide = layout.scene_composition_guide.get(str(scene_id))

                    return {
                        "page_number": page.page_number,
                        "panel_id": panel.panel_id,
                        "importance": panel.importance.value,
                        "composition": panel.composition.value,
                        "camera_angle": panel.camera_angle,
                        "story_beat": panel.story_beat.value,
                        "frame_style": panel.frame_style.value,
                        "bleed": panel.bleed.value,
                        "flow_direction": panel.flow_direction.value,
                        "visual_focus": panel.visual_focus,
                        "size_hint": panel.size_hint,
                        "aspect_ratio": self.get_panel_aspect_ratio(layout, scene_id),
                        "page_function": page.page_function.value,
                        "page_rhythm": page.page_rhythm.value,
                        "is_climax_page": page.page_number in (
                            layout.rhythm_summary.climax_pages
                            if layout.rhythm_summary else []
                        ),
                        # 构图指南
                        "framing_note": guide.framing_note if guide else None,
                        "lighting_suggestion": guide.lighting_suggestion if guide else None,
                        "emotion_keywords": guide.emotion_keywords if guide else [],
                    }
        return None

    def enhance_prompt_with_layout(
        self,
        base_prompt: str,
        layout_info: Dict[str, Any],
    ) -> str:
        """
        根据排版信息增强图片生成提示词

        Args:
            base_prompt: 基础提示词
            layout_info: 场景排版信息

        Returns:
            增强后的提示词
        """
        enhancements = []

        # 添加构图信息
        composition = layout_info.get("composition")
        if composition:
            enhancements.append(composition)

        # 添加镜头角度
        camera_angle = layout_info.get("camera_angle")
        if camera_angle:
            enhancements.append(camera_angle)

        # 添加框线风格对应的视觉效果
        frame_style = layout_info.get("frame_style")
        frame_style_effects = {
            "borderless": "no frame, bleeding edge",
            "diagonal": "dynamic angle, diagonal composition",
            "jagged": "tense atmosphere, sharp edges",
            "rounded": "soft mood, gentle atmosphere",
            "bold": "dramatic emphasis, bold lines",
        }
        if frame_style in frame_style_effects:
            enhancements.append(frame_style_effects[frame_style])

        # 添加叙事节拍对应的氛围
        story_beat = layout_info.get("story_beat")
        beat_atmospheres = {
            "climax": "dramatic moment, intense, peak emotion",
            "action": "dynamic, motion blur, action lines",
            "introspection": "contemplative, emotional depth",
            "flashback": "nostalgic, soft focus, dream-like",
            "aftermath": "quiet, aftermath, breathing space",
        }
        if story_beat in beat_atmospheres:
            enhancements.append(beat_atmospheres[story_beat])

        # 添加光线建议
        lighting = layout_info.get("lighting_suggestion")
        if lighting:
            enhancements.append(lighting)

        # 添加情感关键词
        emotion_keywords = layout_info.get("emotion_keywords", [])
        if emotion_keywords:
            enhancements.extend(emotion_keywords)

        # 组合提示词
        if enhancements:
            enhancement_str = ", ".join(enhancements)
            return f"{base_prompt}, {enhancement_str}"

        return base_prompt
