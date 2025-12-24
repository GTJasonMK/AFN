"""
LLM动态布局服务

使用LLM替代硬编码模板，根据场景内容动态生成最佳布局。
这是解决"布局重复"和"模板不够灵活"问题的核心服务。

核心优势：
1. 根据场景内容智能规划画格数量和位置
2. 考虑上下页连续性，避免布局重复
3. 支持格间过渡类型、间白策略、翻页钩子
4. 动态调整画格大小以匹配内容重要性
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from .page_templates import (
    PanelSlot,
    PanelShape,
    PanelPurpose,
    PageTemplate,
    SceneMood,
)
from app.utils.json_utils import parse_llm_json_safe

logger = logging.getLogger(__name__)


@dataclass
class DynamicPanel:
    """LLM生成的动态画格"""
    panel_id: int
    scene_id: int
    x: float
    y: float
    width: float
    height: float

    # 叙事属性
    story_beat: str = "standard"  # setup/build-up/turn/climax/aftermath/dialogue/action/transition/ma
    importance: str = "standard"  # hero/major/standard/minor/micro

    # 视觉属性
    composition: str = "medium shot"
    camera_angle: str = "eye level"
    frame_style: str = "standard"  # standard/bold/thin/rounded/jagged/dashed/borderless/diagonal/irregular
    bleed: str = "none"  # none/full/top/bottom/left/right/horizontal/vertical

    # 过渡属性
    transition_to_next: str = "action-to-action"  # moment-to-moment/action-to-action/subject-to-subject/scene-to-scene/aspect-to-aspect/non-sequitur
    gaze_direction: str = ""  # 视线引导方向
    flow_direction: str = "down"  # down/right/left/down-left/down-right/center-focus/next-page

    # 特殊标记
    is_ma_panel: bool = False  # 是否为"间"格（留白/氛围格）
    visual_focus: str = ""  # 视觉焦点描述


@dataclass
class DynamicPage:
    """LLM生成的动态页面"""
    page_number: int
    panels: List[DynamicPanel]

    # 页面属性
    page_function: str = "dialogue"  # setup/build/climax/aftermath/transition/dialogue/action
    page_note: str = ""
    page_rhythm: str = "medium"  # slow/medium/fast/explosive
    gutter_style: str = "standard"  # tight/standard/loose
    page_turn_hook: str = ""  # 翻页钩子描述
    is_spread: bool = False  # 是否为跨页


@dataclass
class DynamicLayout:
    """LLM生成的完整动态布局"""
    layout_analysis: str  # 布局设计思路说明
    layout_type: str = "traditional_manga"  # traditional_manga/webtoon
    reading_direction: str = "ltr"  # ltr/rtl
    pacing_strategy: str = ""  # 节奏策略
    pages: List[DynamicPage] = field(default_factory=list)

    # 统计信息
    total_pages: int = 0
    average_panels_per_page: float = 0.0
    hero_panels: int = 0
    ma_panels: int = 0


class LLMLayoutService:
    """
    LLM动态布局服务

    使用LLM根据场景内容生成最优布局，替代硬编码模板。
    """

    def __init__(self, llm_service=None, prompt_service=None):
        """
        初始化服务

        Args:
            llm_service: LLM服务实例
            prompt_service: 提示词服务实例（用于加载manga_layout提示词）
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self._cached_layout_prompt = None

    async def _get_layout_system_prompt(self) -> str:
        """获取布局系统提示词"""
        if self._cached_layout_prompt:
            return self._cached_layout_prompt

        if self.prompt_service:
            try:
                prompt = await self.prompt_service.get_prompt("manga_layout")
                if prompt:
                    self._cached_layout_prompt = prompt
                    return prompt
            except Exception as e:
                logger.warning(f"无法加载 manga_layout 提示词: {e}")

        # 返回最小化的默认提示词
        return self._get_default_layout_prompt()

    def _get_default_layout_prompt(self) -> str:
        """默认布局提示词（manga_layout.md不可用时的回退）"""
        return """你是专业的漫画分镜师(Storyboarder)和排版设计师(Layout Artist)。

## 核心原则
1. 普通页面必须包含4-6个格子
2. 整页单格极其罕见，每5-8页最多出现1次
3. 格子大小必须有层次变化
4. 每3-4页应有1个"间"格（留白/氛围格）

## 格间过渡类型
- moment-to-moment: 同一动作的微小时间差
- action-to-action: 同一主体的连续动作
- subject-to-subject: 同一场景内不同主体
- scene-to-scene: 不同时间或地点
- aspect-to-aspect: 同一场景的不同方面
- non-sequitur: 无明显逻辑关联

## 坐标系统
- x, y, width, height: 值域0-1（相对于页面）
- (0,0)为左上角，(1,1)为右下角
- 格子间保留适当间距"""

    async def generate_layout_for_scenes(
        self,
        scenes: List[Dict[str, Any]],
        previous_pages: Optional[List[DynamicPage]] = None,
        chapter_position: str = "middle",
        reading_direction: str = "ltr",
        user_id: Optional[int] = None,
    ) -> DynamicLayout:
        """
        为多个场景生成动态布局

        Args:
            scenes: 场景列表，每个包含 scene_id, summary, content, mood, characters
            previous_pages: 前面已生成的页面（用于保持连续性）
            chapter_position: 章节位置（beginning/middle/climax/ending）
            reading_direction: 阅读方向（ltr/rtl）
            user_id: 用户ID

        Returns:
            动态布局结果
        """
        if not self.llm_service:
            logger.warning("LLM服务不可用，使用规则布局")
            return self._generate_layout_by_rules(scenes, reading_direction)

        # 构建场景描述
        scenes_description = self._format_scenes_for_llm(scenes)

        # 获取前页上下文（避免重复）
        previous_context = self._format_previous_pages(previous_pages) if previous_pages else "（无）"

        # 构建用户提示词
        user_prompt = f"""请为以下场景规划漫画布局：

## 章节位置
{chapter_position}

## 阅读方向
{reading_direction}

## 前面的页面布局（避免重复）
{previous_context}

## 待规划的场景
{scenes_description}

请输出完整的JSON布局规划，确保：
1. 平均每页4-6个格子
2. 整页单格极其罕见
3. 避免与前面页面使用相同的布局模式
4. 每个画格都有transition_to_next
5. 每3-4页至少1个ma格
"""

        try:
            from app.services.llm_wrappers import call_llm, LLMProfile

            system_prompt = await self._get_layout_system_prompt()

            response = await call_llm(
                self.llm_service,
                LLMProfile.MANGA,
                system_prompt=system_prompt,
                user_content=user_prompt,
                user_id=user_id,
            )

            result = parse_llm_json_safe(response)
            if result:
                layout = self._parse_llm_layout(result, reading_direction)
                layout = self._validate_and_fix_layout(layout)
                return layout

        except Exception as e:
            logger.error(f"LLM布局生成失败: {e}")

        # 回退到规则布局
        return self._generate_layout_by_rules(scenes, reading_direction)

    async def generate_layout_for_single_scene(
        self,
        scene: Dict[str, Any],
        previous_page: Optional[DynamicPage] = None,
        next_scene_hint: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> DynamicPage:
        """
        为单个场景生成动态布局

        Args:
            scene: 场景信息
            previous_page: 前一页布局（用于避免重复）
            next_scene_hint: 下一场景提示（用于翻页钩子设计）
            user_id: 用户ID

        Returns:
            动态页面布局
        """
        layout = await self.generate_layout_for_scenes(
            scenes=[scene],
            previous_pages=[previous_page] if previous_page else None,
            user_id=user_id,
        )

        if layout.pages:
            return layout.pages[0]

        # 回退到默认布局
        return self._create_default_page(scene, 1)

    def _format_scenes_for_llm(self, scenes: List[Dict[str, Any]]) -> str:
        """格式化场景信息供LLM使用"""
        lines = []
        for i, scene in enumerate(scenes, 1):
            lines.append(f"""
### 场景 {scene.get('scene_id', i)}
- 摘要: {scene.get('summary', '无')}
- 情感: {scene.get('mood', 'calm')}
- 角色: {', '.join(scene.get('characters', []))}
- 内容片段: {scene.get('content', '')[:200]}...
- 是否高潮: {scene.get('is_climax', False)}
- 有对话: {scene.get('has_dialogue', False)}
- 是动作场景: {scene.get('is_action', False)}
""")
        return "\n".join(lines)

    def _format_previous_pages(self, pages: List[DynamicPage]) -> str:
        """格式化前面的页面信息"""
        if not pages:
            return "（无）"

        lines = []
        for page in pages[-3:]:  # 只取最近3页
            panel_count = len(page.panels)
            lines.append(
                f"- 第{page.page_number}页: {panel_count}格, "
                f"功能={page.page_function}, "
                f"节奏={page.page_rhythm}"
            )
        return "\n".join(lines)

    def _parse_llm_layout(self, result: Dict[str, Any], reading_direction: str) -> DynamicLayout:
        """解析LLM返回的布局JSON"""
        layout = DynamicLayout(
            layout_analysis=result.get("layout_analysis", ""),
            layout_type=result.get("layout_type", "traditional_manga"),
            reading_direction=result.get("reading_direction", reading_direction),
            pacing_strategy=result.get("pacing_strategy", ""),
            total_pages=result.get("total_pages", 0),
        )

        pages_data = result.get("pages", [])
        for page_data in pages_data:
            page = DynamicPage(
                page_number=page_data.get("page_number", 0),
                panels=[],
                page_function=page_data.get("page_function", "dialogue"),
                page_note=page_data.get("page_note", ""),
                page_rhythm=page_data.get("page_rhythm", "medium"),
                gutter_style=page_data.get("gutter_style", "standard"),
                page_turn_hook=page_data.get("page_turn_hook", ""),
                is_spread=page_data.get("is_spread", False),
            )

            panels_data = page_data.get("panels", [])
            for panel_data in panels_data:
                panel = DynamicPanel(
                    panel_id=panel_data.get("panel_id", 0),
                    scene_id=panel_data.get("scene_id", 0),
                    x=float(panel_data.get("x", 0)),
                    y=float(panel_data.get("y", 0)),
                    width=float(panel_data.get("width", 0.5)),
                    height=float(panel_data.get("height", 0.3)),
                    story_beat=panel_data.get("story_beat", "standard"),
                    importance=panel_data.get("importance", "standard"),
                    composition=panel_data.get("composition", "medium shot"),
                    camera_angle=panel_data.get("camera_angle", "eye level"),
                    frame_style=panel_data.get("frame_style", "standard"),
                    bleed=panel_data.get("bleed", "none"),
                    transition_to_next=panel_data.get("transition_to_next", "action-to-action"),
                    gaze_direction=panel_data.get("gaze_direction", ""),
                    flow_direction=panel_data.get("flow_direction", "down"),
                    is_ma_panel=panel_data.get("is_ma_panel", False),
                    visual_focus=panel_data.get("visual_focus", ""),
                )
                page.panels.append(panel)

            layout.pages.append(page)

        # 计算统计信息
        if layout.pages:
            total_panels = sum(len(p.panels) for p in layout.pages)
            layout.total_pages = len(layout.pages)
            layout.average_panels_per_page = total_panels / len(layout.pages)
            layout.hero_panels = sum(
                1 for p in layout.pages for panel in p.panels
                if panel.importance == "hero"
            )
            layout.ma_panels = sum(
                1 for p in layout.pages for panel in p.panels
                if panel.is_ma_panel
            )

        return layout

    def _validate_and_fix_layout(self, layout: DynamicLayout) -> DynamicLayout:
        """验证并修正布局，确保满足基本约束"""
        for page in layout.pages:
            # 1. 确保每页至少有1个格子
            if not page.panels:
                page.panels.append(self._create_default_panel(1, 1))

            # 2. 修正坐标越界
            for panel in page.panels:
                panel.x = max(0, min(1, panel.x))
                panel.y = max(0, min(1, panel.y))
                panel.width = max(0.1, min(1, panel.width))
                panel.height = max(0.1, min(1, panel.height))

                # 确保不超出边界
                if panel.x + panel.width > 1:
                    panel.width = 1 - panel.x
                if panel.y + panel.height > 1:
                    panel.height = 1 - panel.y

            # 3. 检测并修复重叠（简单处理：重叠时缩小后面的格子）
            page.panels = self._fix_overlapping_panels(page.panels)

        # 4. 检查hero格子是否过多（每6页最多1个）
        hero_count = 0
        for page in layout.pages:
            for panel in page.panels:
                if panel.importance == "hero":
                    hero_count += 1
                    if hero_count > max(1, len(layout.pages) // 6):
                        panel.importance = "major"  # 降级

        # 5. 确保有足够的ma格（每4页至少1个）
        ma_count = sum(1 for p in layout.pages for panel in p.panels if panel.is_ma_panel)
        required_ma = max(1, len(layout.pages) // 4)
        if ma_count < required_ma:
            # 将一些minor格子标记为ma格
            for page in layout.pages:
                if ma_count >= required_ma:
                    break
                for panel in page.panels:
                    if panel.importance == "minor" and not panel.is_ma_panel:
                        panel.is_ma_panel = True
                        ma_count += 1
                        if ma_count >= required_ma:
                            break

        return layout

    def _fix_overlapping_panels(self, panels: List[DynamicPanel]) -> List[DynamicPanel]:
        """修复重叠的画格"""
        # 简单策略：按panel_id排序，后面的格子如果重叠就缩小
        panels = sorted(panels, key=lambda p: p.panel_id)

        for i, panel in enumerate(panels):
            for j, other in enumerate(panels[:i]):
                if self._panels_overlap(panel, other):
                    # 简单处理：将当前格子移到other下方
                    panel.y = other.y + other.height + 0.02
                    if panel.y + panel.height > 1:
                        panel.height = 1 - panel.y

        return panels

    def _panels_overlap(self, p1: DynamicPanel, p2: DynamicPanel) -> bool:
        """检查两个画格是否重叠"""
        # 检查x轴是否重叠
        x_overlap = not (p1.x + p1.width <= p2.x or p2.x + p2.width <= p1.x)
        # 检查y轴是否重叠
        y_overlap = not (p1.y + p1.height <= p2.y or p2.y + p2.height <= p1.y)
        return x_overlap and y_overlap

    def _generate_layout_by_rules(
        self,
        scenes: List[Dict[str, Any]],
        reading_direction: str
    ) -> DynamicLayout:
        """基于规则生成布局（LLM不可用时的回退）"""
        layout = DynamicLayout(
            layout_analysis="使用规则生成的标准布局",
            reading_direction=reading_direction,
        )

        page_number = 1
        for scene in scenes:
            page = self._create_default_page(scene, page_number)
            layout.pages.append(page)
            page_number += 1

        layout.total_pages = len(layout.pages)
        if layout.pages:
            total_panels = sum(len(p.panels) for p in layout.pages)
            layout.average_panels_per_page = total_panels / len(layout.pages)

        return layout

    def _create_default_page(self, scene: Dict[str, Any], page_number: int) -> DynamicPage:
        """创建默认页面布局（5格标准布局）"""
        mood = scene.get("mood", "calm")
        is_climax = scene.get("is_climax", False)
        is_action = scene.get("is_action", False)
        has_dialogue = scene.get("has_dialogue", False)
        scene_id = scene.get("scene_id", 1)

        # 根据场景类型选择页面功能
        if is_climax:
            page_function = "climax"
            page_rhythm = "explosive"
        elif is_action:
            page_function = "action"
            page_rhythm = "fast"
        elif has_dialogue:
            page_function = "dialogue"
            page_rhythm = "medium"
        else:
            page_function = "transition"
            page_rhythm = "slow"

        # 创建5格标准布局
        panels = [
            DynamicPanel(
                panel_id=1, scene_id=scene_id,
                x=0, y=0, width=1.0, height=0.35,
                story_beat="setup", importance="major",
                composition="establishing shot", camera_angle="high angle",
                transition_to_next="aspect-to-aspect",
            ),
            DynamicPanel(
                panel_id=2, scene_id=scene_id,
                x=0, y=0.38, width=0.48, height=0.28,
                story_beat="dialogue" if has_dialogue else "build-up",
                importance="standard",
                composition="medium shot", camera_angle="eye level",
                transition_to_next="subject-to-subject",
            ),
            DynamicPanel(
                panel_id=3, scene_id=scene_id,
                x=0.52, y=0.38, width=0.48, height=0.28,
                story_beat="dialogue" if has_dialogue else "build-up",
                importance="standard",
                composition="close-up", camera_angle="eye level",
                transition_to_next="action-to-action",
            ),
            DynamicPanel(
                panel_id=4, scene_id=scene_id,
                x=0, y=0.68, width=0.48, height=0.32,
                story_beat="turn" if is_climax else "dialogue",
                importance="standard",
                composition="medium shot", camera_angle="eye level",
                transition_to_next="subject-to-subject",
            ),
            DynamicPanel(
                panel_id=5, scene_id=scene_id,
                x=0.52, y=0.68, width=0.48, height=0.32,
                story_beat="aftermath" if is_climax else "transition",
                importance="standard",
                composition="close-up", camera_angle="eye level",
                transition_to_next="scene-to-scene",
                flow_direction="next-page",
            ),
        ]

        return DynamicPage(
            page_number=page_number,
            panels=panels,
            page_function=page_function,
            page_rhythm=page_rhythm,
            gutter_style="tight" if is_action else "standard",
        )

    def _create_default_panel(self, panel_id: int, scene_id: int) -> DynamicPanel:
        """创建默认画格"""
        return DynamicPanel(
            panel_id=panel_id,
            scene_id=scene_id,
            x=0, y=0, width=1.0, height=0.5,
            story_beat="standard",
            importance="standard",
        )

    def convert_to_template(self, page: DynamicPage) -> PageTemplate:
        """
        将动态页面转换为PageTemplate格式（兼容现有代码）

        Args:
            page: 动态页面

        Returns:
            PageTemplate对象
        """
        panel_slots = []
        for panel in page.panels:
            # 映射story_beat到PanelPurpose
            purpose_map = {
                "setup": PanelPurpose.ESTABLISHING,
                "build-up": PanelPurpose.ACTION,
                "turn": PanelPurpose.EMPHASIS,
                "climax": PanelPurpose.EMPHASIS,
                "aftermath": PanelPurpose.REACTION,
                "dialogue": PanelPurpose.DIALOGUE,
                "action": PanelPurpose.ACTION,
                "transition": PanelPurpose.TRANSITION,
                "ma": PanelPurpose.ESTABLISHING,  # ma格通常是环境/氛围
            }
            purpose = purpose_map.get(panel.story_beat, PanelPurpose.ACTION)

            # 映射frame_style到PanelShape
            shape_map = {
                "standard": PanelShape.RECTANGLE,
                "bold": PanelShape.RECTANGLE,
                "thin": PanelShape.RECTANGLE,
                "rounded": PanelShape.ROUNDED,
                "jagged": PanelShape.JAGGED,
                "dashed": PanelShape.RECTANGLE,
                "borderless": PanelShape.BORDERLESS,
                "diagonal": PanelShape.DIAGONAL_LEFT,
                "irregular": PanelShape.IRREGULAR,
            }
            shape = shape_map.get(panel.frame_style, PanelShape.RECTANGLE)

            slot = PanelSlot(
                slot_id=panel.panel_id,
                x=panel.x,
                y=panel.y,
                width=panel.width,
                height=panel.height,
                shape=shape,
                purpose=purpose,
                suggested_composition=panel.composition,
                suggested_angle=panel.camera_angle,
                is_key_panel=(panel.importance in ["hero", "major"]),
                can_break_frame=(panel.bleed != "none"),
                border_weight="thin" if panel.frame_style == "thin" else "normal",
                visual_flow_to=panel.panel_id + 1 if panel.panel_id < len(page.panels) else None,
            )
            panel_slots.append(slot)

        # 映射page_rhythm到SceneMood
        mood_map = {
            "slow": SceneMood.CALM,
            "medium": SceneMood.CALM,
            "fast": SceneMood.ACTION,
            "explosive": SceneMood.DRAMATIC,
        }
        mood = mood_map.get(page.page_rhythm, SceneMood.CALM)

        return PageTemplate(
            id=f"llm_dynamic_{page.page_number}",
            name=f"LLM Dynamic Layout {page.page_number}",
            name_zh=f"LLM动态布局 {page.page_number}",
            description=page.page_note or f"LLM根据场景动态生成的布局",
            suitable_moods=[mood],
            panel_slots=panel_slots,
            reading_direction="rtl" if page.page_function == "action" else "ltr",
            pacing=page.page_rhythm,
            intensity=8 if page.page_function == "climax" else 5,
        )
