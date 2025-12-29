# 漫画 Prompt 生成逻辑重构实施计划

> 版本: 1.0
> 创建日期: 2024-12
> 状态: 待实施

---

## 目录

1. [背景与目标](#1-背景与目标)
2. [当前实现分析](#2-当前实现分析)
3. [新方案设计](#3-新方案设计)
4. [技术实现方案](#4-技术实现方案)
5. [数据结构设计](#5-数据结构设计)
6. [API 设计](#6-api-设计)
7. [分阶段实施计划](#7-分阶段实施计划)
8. [风险与缓解措施](#8-风险与缓解措施)
9. [验收标准](#9-验收标准)

---

## 1. 背景与目标

### 1.1 背景

当前漫画 Prompt 生成采用"场景驱动"模式：
1. 从章节内容中提取 5-15 个叙事场景
2. 逐场景展开为页面和画格
3. 为每个画格生成提示词

这种模式存在以下问题：
- 页面数量不可控（取决于场景数量）
- 信息提取不够结构化（缺少对话、物品、事件的专门提取）
- 缺乏全局视角（逐场景独立处理，无法规划整章节奏）
- 分镜设计与内容分配耦合度高

### 1.2 目标

重构为"页面驱动"模式：
1. **结构化信息提取**：专门提取人物、对话、物品、事件、场景等信息
2. **全局页面规划**：LLM 看到整章内容，规划页面数量和内容分配
3. **专业分镜设计**：独立的分镜设计步骤，输出排版位置和镜头语言
4. **多层上下文提示词**：基于章节+页面+分镜三层上下文生成提示词

### 1.3 预期收益

| 指标 | 当前 | 目标 | 提升 |
|:-----|:-----|:-----|:-----|
| 页面数量控制 | 不可控 | 可指定范围 | 可控性 +100% |
| 信息利用率 | ~40% | ~80% | +100% |
| 分镜专业度 | 模板匹配 | LLM 专业设计 | 质量 +50% |
| 叙事连贯性 | 逐场景独立 | 全局规划 | 流畅度 +40% |

---

## 2. 当前实现分析

### 2.1 当前流程

```
章节内容
    ↓
[场景提取] SceneExtractor
    ├── 输出: 5-15 个场景
    └── 输出: 角色外观描述
    ↓
[场景展开] SceneExpansionService (循环每个场景)
    ├── SceneAnalyzer: 分析情感/重要性/类型
    ├── LayoutSelector: 选择页面布局
    └── ContentGenerator: 分配画格内容
    ↓
[提示词生成] PanelPromptBuilder
    └── 输出: 每个画格的 prompt_en/prompt_zh/negative_prompt
    ↓
[结果保存] ResultPersistence
```

### 2.2 当前代码结构

```
backend/app/services/manga_prompt/
├── core/
│   ├── service.py           # MangaPromptServiceV2 主服务
│   ├── scene_extractor.py   # 场景提取
│   ├── prompts.py           # 场景提取提示词
│   ├── checkpoint_manager.py # 断点管理
│   └── result_persistence.py # 结果持久化
├── scene_expansion/
│   ├── service.py           # SceneExpansionService
│   ├── scene_analyzer.py    # 场景分析
│   ├── layout_selector.py   # 布局选择
│   ├── content_generator.py # 内容分配
│   └── prompts.py           # 分镜相关提示词
├── panel_prompt/
│   ├── builder.py           # PanelPromptBuilder
│   └── component_builders.py # 子构建器
├── page_templates/          # 页面模板定义
└── llm_layout_service.py    # LLM 动态布局
```

### 2.3 当前提示词分析

**场景提取提示词** (`core/prompts.py`):
- 输入: 章节内容(限制8000字)
- 输出: scenes 列表 + character_profiles
- 问题: 只提取了角色外观，缺少对话/物品/事件的结构化提取

**内容分配提示词** (`scene_expansion/prompts.py`):
- 输入: 场景内容 + 模板信息
- 输出: 每个画格的内容描述
- 问题: 上下文仅限于单个场景，无法利用全章信息

### 2.4 LLM 调用分析

| 步骤 | 调用次数 | Token 估算 |
|:-----|:---------|:-----------|
| 场景提取 | 1 次 | ~3000 |
| 场景分析 | N 次 (场景数) | ~500 × N |
| 布局选择 | N 次 | ~800 × N |
| 内容分配 | N 次 | ~1000 × N |
| **总计** | 1 + 3N | ~3000 + 2300N |

假设 N=10，总 Token 约 26,000

---

## 3. 新方案设计

### 3.1 新流程概览

```
章节内容
    ↓
[步骤1: 结构化信息提取] ChapterInfoExtractor
    ├── 人物信息 (外观/性格/关系)
    ├── 对话信息 (说话人/内容/情绪)
    ├── 场景信息 (地点/时间/氛围)
    ├── 事件信息 (动作/冲突/转折)
    └── 物品信息 (关键道具/环境元素)
    ↓
[步骤2: 全局页面规划] PagePlanner
    ├── 确定总页数 (可由用户指定范围)
    ├── 内容分配 (每页包含哪些事件)
    └── 节奏控制 (铺垫/高潮/收尾)
    ↓
[步骤3: 分镜设计] StoryboardDesigner (循环每个页面)
    ├── 分镜数量
    ├── 排版布局 (大小/位置/形状)
    ├── 镜头语言 (远景/近景/特写)
    └── 每格内容描述
    ↓
[步骤4: 提示词构建] PromptBuilder
    ├── 章节上下文
    ├── 页面上下文
    └── 分镜内容
    ↓
[结果保存] (复用现有)
```

### 3.2 核心设计原则

1. **关注点分离**: 每个步骤职责单一，易于测试和维护
2. **全局优先**: 先全局规划，再局部细化
3. **上下文传递**: 每一步都能访问前面步骤的输出
4. **渐进增强**: 可以逐步启用新功能，保持向后兼容
5. **断点续传**: 每个步骤完成后保存检查点

### 3.3 与现有系统的兼容性

- **API 接口保持不变**: `GenerateRequest` 和 `GenerateResponse` 结构不变
- **数据库结构复用**: `manga_prompts` 表结构不变
- **断点机制复用**: `CheckpointManager` 可复用，调整阶段定义
- **模板系统复用**: `PageTemplate` 和 `PanelSlot` 可继续使用

---

## 4. 技术实现方案

### 4.1 新增模块设计

#### 4.1.1 ChapterInfoExtractor (信息提取器)

```python
# backend/app/services/manga_prompt/extraction/chapter_info_extractor.py

class ChapterInfoExtractor:
    """
    章节信息提取器

    从章节内容中提取结构化信息，为后续步骤提供数据基础。
    """

    async def extract(
        self,
        chapter_content: str,
        user_id: Optional[int] = None,
        dialogue_language: str = "chinese",
    ) -> ChapterInfo:
        """
        提取章节信息

        Returns:
            ChapterInfo: 包含人物、对话、场景、事件、物品的结构化数据
        """
        pass
```

#### 4.1.2 PagePlanner (页面规划器)

```python
# backend/app/services/manga_prompt/planning/page_planner.py

class PagePlanner:
    """
    全局页面规划器

    基于提取的信息，规划整章的页面结构。
    """

    async def plan(
        self,
        chapter_info: ChapterInfo,
        min_pages: int = 8,
        max_pages: int = 15,
        user_id: Optional[int] = None,
    ) -> PagePlanResult:
        """
        规划页面

        Args:
            chapter_info: 章节信息
            min_pages: 最少页数
            max_pages: 最多页数

        Returns:
            PagePlanResult: 包含每页内容分配的规划结果
        """
        pass
```

#### 4.1.3 StoryboardDesigner (分镜设计器)

```python
# backend/app/services/manga_prompt/storyboard/designer.py

class StoryboardDesigner:
    """
    分镜设计器

    为单个页面设计分镜布局。
    """

    async def design(
        self,
        page_plan: PagePlanItem,
        chapter_info: ChapterInfo,
        previous_page: Optional[StoryboardResult] = None,
        user_id: Optional[int] = None,
    ) -> StoryboardResult:
        """
        设计分镜

        Args:
            page_plan: 页面规划信息
            chapter_info: 章节信息 (用于上下文)
            previous_page: 前一页的分镜结果 (用于连续性)

        Returns:
            StoryboardResult: 包含分镜布局和内容的结果
        """
        pass
```

#### 4.1.4 ContextualPromptBuilder (上下文提示词构建器)

```python
# backend/app/services/manga_prompt/prompt/contextual_builder.py

class ContextualPromptBuilder:
    """
    上下文感知的提示词构建器

    基于多层上下文生成精确的提示词。
    """

    def build(
        self,
        panel: PanelDesign,
        page_context: PageContext,
        chapter_context: ChapterContext,
        style: str = "manga",
    ) -> PanelPrompt:
        """
        构建提示词

        Args:
            panel: 分镜设计
            page_context: 页面上下文
            chapter_context: 章节上下文

        Returns:
            PanelPrompt: 完整的提示词结果
        """
        pass
```

### 4.2 新目录结构

```
backend/app/services/manga_prompt/
├── core/
│   ├── service.py           # 主服务入口 (重构)
│   ├── models.py            # 数据模型
│   ├── checkpoint_manager.py # 断点管理 (调整阶段)
│   └── result_persistence.py # 结果持久化 (复用)
│
├── extraction/              # [新增] 信息提取模块
│   ├── __init__.py
│   ├── chapter_info_extractor.py
│   ├── prompts.py           # 信息提取提示词
│   └── models.py            # ChapterInfo 等数据类
│
├── planning/                # [新增] 页面规划模块
│   ├── __init__.py
│   ├── page_planner.py
│   ├── prompts.py           # 页面规划提示词
│   └── models.py            # PagePlanResult 等数据类
│
├── storyboard/              # [新增] 分镜设计模块
│   ├── __init__.py
│   ├── designer.py
│   ├── prompts.py           # 分镜设计提示词
│   └── models.py            # StoryboardResult 等数据类
│
├── prompt/                  # [重构] 提示词构建模块
│   ├── __init__.py
│   ├── contextual_builder.py # 新的上下文感知构建器
│   ├── component_builders.py # 复用现有组件
│   └── negative_prompts.py   # 负向提示词
│
├── scene_expansion/         # [保留] 向后兼容
├── panel_prompt/            # [保留] 部分复用
├── page_templates/          # [复用] 页面模板
└── llm_layout_service.py    # [复用] LLM布局服务
```

### 4.3 LLM 调用优化

| 步骤 | 调用次数 | Token 估算 | 优化策略 |
|:-----|:---------|:-----------|:---------|
| 信息提取 | 1 次 | ~4000 | 一次性提取所有信息 |
| 页面规划 | 1 次 | ~2000 | 全局规划，只调用一次 |
| 分镜设计 | P 次 (页数) | ~1000 × P | 并行处理多页 |
| 提示词构建 | 0 次 | 0 | 纯规则，无需LLM |
| **总计** | 2 + P | ~6000 + 1000P |

假设 P=10，总 Token 约 16,000，相比当前 26,000 **减少约 40%**

**关键优化**:
1. 合并场景分析和布局选择为一个"分镜设计"步骤
2. 页面规划只需一次 LLM 调用（当前需要逐场景处理）
3. 提示词构建不需要 LLM（当前也不需要，保持不变）

---

## 5. 数据结构设计

### 5.1 核心数据类

```python
# backend/app/services/manga_prompt/extraction/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class EmotionType(str, Enum):
    """情绪类型"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    CONTEMPTUOUS = "contemptuous"


class EventType(str, Enum):
    """事件类型"""
    DIALOGUE = "dialogue"       # 对话
    ACTION = "action"           # 动作
    REACTION = "reaction"       # 反应
    TRANSITION = "transition"   # 过渡
    REVELATION = "revelation"   # 揭示
    CONFLICT = "conflict"       # 冲突
    RESOLUTION = "resolution"   # 解决


@dataclass
class CharacterInfo:
    """角色信息"""
    name: str
    appearance: str              # 英文外观描述
    personality: str             # 性格特点
    role: str                    # protagonist/antagonist/supporting/minor
    first_appearance: int        # 首次出现的事件索引
    relationships: Dict[str, str] = field(default_factory=dict)  # 与其他角色的关系


@dataclass
class DialogueInfo:
    """对话信息"""
    speaker: str
    content: str
    emotion: EmotionType
    target: Optional[str] = None  # 对话对象
    event_index: int = 0          # 所属事件索引


@dataclass
class SceneInfo:
    """场景信息"""
    location: str                 # 地点
    time: str                     # 时间 (morning/afternoon/evening/night)
    atmosphere: str               # 氛围
    weather: Optional[str] = None # 天气
    lighting: str = "natural"     # 光线


@dataclass
class EventInfo:
    """事件信息"""
    index: int
    type: EventType
    description: str              # 事件描述
    participants: List[str]       # 参与角色
    scene_index: int              # 所属场景索引
    importance: str = "normal"    # low/normal/high/critical
    dialogues: List[int] = field(default_factory=list)  # 关联的对话索引


@dataclass
class ItemInfo:
    """物品信息"""
    name: str
    description: str              # 英文描述
    importance: str               # prop/key_item/mcguffin
    first_appearance: int         # 首次出现的事件索引


@dataclass
class ChapterInfo:
    """章节信息汇总"""
    characters: Dict[str, CharacterInfo]
    dialogues: List[DialogueInfo]
    scenes: List[SceneInfo]
    events: List[EventInfo]
    items: List[ItemInfo]
    chapter_summary: str          # 章节摘要
    mood_progression: List[str]   # 情绪变化轨迹
```

### 5.2 页面规划数据类

```python
# backend/app/services/manga_prompt/planning/models.py

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class PacingType(str, Enum):
    """节奏类型"""
    SLOW = "slow"           # 慢节奏，铺垫
    MEDIUM = "medium"       # 中等节奏
    FAST = "fast"           # 快节奏，紧张
    EXPLOSIVE = "explosive" # 爆发，高潮


class PageRole(str, Enum):
    """页面角色"""
    OPENING = "opening"         # 开场
    SETUP = "setup"             # 铺垫
    RISING = "rising"           # 上升
    CLIMAX = "climax"           # 高潮
    FALLING = "falling"         # 下降
    RESOLUTION = "resolution"   # 收尾
    TRANSITION = "transition"   # 过渡


@dataclass
class PagePlanItem:
    """单页规划"""
    page_number: int
    event_indices: List[int]      # 包含的事件索引
    content_summary: str          # 内容摘要
    pacing: PacingType
    role: PageRole
    key_characters: List[str]     # 主要角色
    has_dialogue: bool
    has_action: bool
    suggested_panel_count: int    # 建议分镜数 (3-7)
    notes: str = ""               # 特殊说明


@dataclass
class PagePlanResult:
    """页面规划结果"""
    total_pages: int
    pages: List[PagePlanItem]
    pacing_notes: str             # 整体节奏说明
    climax_pages: List[int]       # 高潮页码
```

### 5.3 分镜设计数据类

```python
# backend/app/services/manga_prompt/storyboard/models.py

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ShotType(str, Enum):
    """镜头类型"""
    ESTABLISHING = "establishing"   # 全景/建立镜头
    LONG = "long"                   # 远景
    MEDIUM = "medium"               # 中景
    CLOSE_UP = "close_up"           # 近景
    EXTREME_CLOSE_UP = "extreme_close_up"  # 特写
    OVER_SHOULDER = "over_shoulder" # 过肩镜头
    POV = "pov"                     # 主观视角
    BIRD_EYE = "bird_eye"           # 鸟瞰
    WORM_EYE = "worm_eye"           # 仰视


class PanelSize(str, Enum):
    """画格大小"""
    SMALL = "small"       # 小格 (1/6 页)
    MEDIUM = "medium"     # 中格 (1/4 页)
    LARGE = "large"       # 大格 (1/3 页)
    HALF = "half"         # 半页
    FULL = "full"         # 整页
    SPREAD = "spread"     # 跨页


class PanelPosition(str, Enum):
    """画格位置"""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    MIDDLE_CENTER = "middle_center"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    TOP_FULL = "top_full"
    MIDDLE_FULL = "middle_full"
    BOTTOM_FULL = "bottom_full"


@dataclass
class PanelDesign:
    """分镜设计"""
    slot_id: int
    size: PanelSize
    position: PanelPosition
    aspect_ratio: str             # "16:9", "4:3", "1:1", "9:16"
    shot_type: ShotType

    # 内容描述
    visual_description: str       # 画面描述
    characters: List[str]         # 出场角色
    character_actions: Dict[str, str]  # 角色动作 {角色名: 动作描述}
    character_expressions: Dict[str, str]  # 角色表情

    # 文字元素
    dialogue: Optional[str] = None
    dialogue_speaker: Optional[str] = None
    narration: Optional[str] = None
    sound_effects: List[str] = field(default_factory=list)

    # 视觉效果
    focus_point: str = ""         # 视觉焦点
    lighting: str = ""            # 光线
    atmosphere: str = ""          # 氛围
    motion_lines: bool = False    # 是否需要速度线
    impact_effects: bool = False  # 是否需要冲击效果

    # 元信息
    is_key_panel: bool = False    # 是否关键画格
    transition_to_next: str = ""  # 到下一格的过渡方式


@dataclass
class StoryboardResult:
    """分镜结果"""
    page_number: int
    panel_count: int
    panels: List[PanelDesign]
    page_purpose: str             # 页面目的
    reading_flow: str             # 阅读流向描述
    visual_rhythm: str            # 视觉节奏描述
```

---

## 6. API 设计

### 6.1 API 接口 (保持向后兼容)

现有 API 接口保持不变:

```python
# POST /api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts
class GenerateRequest(BaseModel):
    style: str = "manga"
    min_scenes: int = 5          # 重新解释为 min_pages
    max_scenes: int = 15         # 重新解释为 max_pages
    language: str = "chinese"
    use_portraits: bool = True
    auto_generate_portraits: bool = True
    use_dynamic_layout: bool = True

# 响应结构不变
class GenerateResponse(BaseModel):
    chapter_number: int
    style: str
    character_profiles: Dict[str, str]
    total_pages: int
    total_panels: int
    scenes: List[SceneResponse]   # 兼容现有结构
    panels: List[PanelResponse]
```

### 6.2 新增内部参数

```python
# 内部使用的扩展请求
class ExtendedGenerateRequest(GenerateRequest):
    # 新增参数 (可选)
    extraction_mode: str = "full"  # full/basic (控制信息提取深度)
    planning_mode: str = "auto"    # auto/manual (是否使用LLM规划)

    # 页面控制 (新功能)
    target_pages: Optional[int] = None  # 精确指定页数

    # 调试选项
    return_intermediate: bool = False  # 是否返回中间结果
```

### 6.3 进度查询扩展

```python
# GET /api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts/progress

# 响应增加更详细的阶段信息
{
    "status": "in_progress",
    "stage": "storyboard",
    "stage_label": "设计分镜中",
    "current": 5,
    "total": 10,
    "message": "正在设计第 5/10 页分镜",
    "stages_completed": ["extraction", "planning"],
    "stages_pending": ["prompt_building"],
    "can_resume": true,
    # 新增: 各阶段耗时
    "stage_durations": {
        "extraction": 3.2,
        "planning": 2.1
    }
}
```

---

## 7. 分阶段实施计划

### 7.1 第一阶段: 优化信息提取 (5 天)

**目标**: 增强信息提取，不改变后续流程

**任务清单**:
1. [ ] 创建 `extraction/` 模块目录结构
2. [ ] 实现 `ChapterInfo` 及相关数据类
3. [ ] 编写信息提取提示词 (`extraction/prompts.py`)
4. [ ] 实现 `ChapterInfoExtractor`
5. [ ] 在 `MangaPromptServiceV2` 中集成新提取器
6. [ ] 将提取结果转换为现有 `scenes` 格式 (兼容)
7. [ ] 单元测试

**向后兼容策略**:
- 新提取器输出同时包含新格式和旧格式
- 后续步骤暂时使用旧格式
- 通过配置开关控制是否启用新功能

**验收标准**:
- [ ] 信息提取成功率 > 95%
- [ ] 提取结果包含所有必需字段
- [ ] 现有功能不受影响

### 7.2 第二阶段: 引入全局页面规划 (5 天)

**目标**: 增加页面规划步骤，支持页数控制

**任务清单**:
1. [ ] 创建 `planning/` 模块目录结构
2. [ ] 实现 `PagePlanItem` 和 `PagePlanResult` 数据类
3. [ ] 编写页面规划提示词 (`planning/prompts.py`)
4. [ ] 实现 `PagePlanner`
5. [ ] 修改 `MangaPromptServiceV2` 集成规划步骤
6. [ ] 更新断点管理，增加 `planning` 阶段
7. [ ] 将规划结果映射到现有场景展开流程
8. [ ] 集成测试

**向后兼容策略**:
- 新增 `use_page_planning` 配置开关
- 默认启用新规划，可回退到旧模式
- 规划结果转换为现有 `scenes_data` 格式

**验收标准**:
- [ ] 页面数量可控 (误差 +/-1 页)
- [ ] 内容分配合理，无重要内容遗漏
- [ ] 高潮场景正确识别

### 7.3 第三阶段: 分镜设计独立化 (5 天)

**目标**: 专门的分镜设计步骤，替换现有场景展开

**任务清单**:
1. [ ] 创建 `storyboard/` 模块目录结构
2. [ ] 实现 `PanelDesign` 和 `StoryboardResult` 数据类
3. [ ] 编写分镜设计提示词 (`storyboard/prompts.py`)
4. [ ] 实现 `StoryboardDesigner`
5. [ ] 修改 `MangaPromptServiceV2` 替换场景展开
6. [ ] 更新断点管理，调整阶段定义
7. [ ] 重构 `ContextualPromptBuilder`
8. [ ] 集成测试
9. [ ] 性能优化 (并行处理多页)

**向后兼容策略**:
- 保留 `scene_expansion/` 模块
- 通过配置选择使用新/旧分镜流程
- 输出格式保持与现有 `PanelPrompt` 兼容

**验收标准**:
- [ ] 分镜布局专业合理
- [ ] 镜头语言正确使用
- [ ] 提示词质量提升 (人工评估)

### 7.4 测试验收阶段 (3 天)

**任务清单**:
1. [ ] 端到端测试
2. [ ] 性能对比测试 (Token 消耗、响应时间)
3. [ ] 质量对比测试 (生成效果人工评估)
4. [ ] 回归测试 (确保旧功能正常)
5. [ ] 文档更新
6. [ ] 代码审查

---

## 8. 风险与缓解措施

### 8.1 技术风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|:-----|:-------|:-----|:---------|
| LLM 输出不稳定 | 中 | 高 | 增加重试机制，完善回退逻辑 |
| Token 成本超预期 | 中 | 中 | 监控 Token 使用，优化提示词 |
| 数据结构不兼容 | 低 | 高 | 保持旧结构，新结构并行 |
| 性能下降 | 低 | 中 | 并行处理，缓存优化 |

### 8.2 项目风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|:-----|:-------|:-----|:---------|
| 开发周期延长 | 中 | 中 | 分阶段交付，每阶段可独立验收 |
| 需求变更 | 低 | 中 | 模块化设计，降低耦合 |
| 测试覆盖不足 | 低 | 高 | 提前编写测试用例 |

### 8.3 回滚策略

每个阶段都支持回滚:

```python
# core/config.py
class MangaPromptConfig:
    # 功能开关
    use_new_extraction: bool = True    # 第一阶段
    use_page_planning: bool = True     # 第二阶段
    use_new_storyboard: bool = True    # 第三阶段

    # 全部回滚到旧版本
    use_legacy_mode: bool = False
```

---

## 9. 验收标准

### 9.1 功能验收

- [ ] 信息提取: 人物、对话、场景、事件、物品全部正确提取
- [ ] 页面规划: 页面数量在指定范围内，内容分配合理
- [ ] 分镜设计: 布局专业，镜头语言正确
- [ ] 提示词生成: 英文提示词准确，中文描述清晰
- [ ] 断点续传: 任意阶段中断后可恢复
- [ ] 向后兼容: 现有 API 调用无需修改

### 9.2 性能验收

| 指标 | 当前值 | 目标值 |
|:-----|:-------|:-------|
| 总 Token 消耗 | ~26,000 | < 20,000 |
| 响应时间 (10页) | ~60s | < 50s |
| LLM 调用次数 | ~30 | < 15 |

### 9.3 质量验收

- [ ] 生成的漫画分镜经人工评估，质量不低于当前版本
- [ ] 页面节奏更合理 (开场/高潮/收尾明确)
- [ ] 分镜布局更专业 (镜头变化丰富)
- [ ] 角色一致性更好 (外观描述准确)

---

## 附录

### A. 提示词模板草稿

#### A.1 信息提取提示词

```
你是专业的漫画编剧助手。请从以下章节内容中提取结构化信息。

## 章节内容
{content}

## 提取要求

### 1. 角色信息 (characters)
为每个出场角色提取:
- name: 角色名
- appearance: 外观描述 (英文，用于AI绘图)
- personality: 性格特点
- role: 角色定位 (protagonist/antagonist/supporting/minor)

### 2. 对话信息 (dialogues)
提取所有对话:
- speaker: 说话人
- content: 对话内容 (保留原文)
- emotion: 情绪 (neutral/happy/sad/angry/surprised/fearful)
- target: 对话对象 (如有)

### 3. 场景信息 (scenes)
识别不同场景:
- location: 地点
- time: 时间
- atmosphere: 氛围
- lighting: 光线

### 4. 事件信息 (events)
按时间顺序提取事件:
- type: 类型 (dialogue/action/reaction/transition/revelation/conflict)
- description: 事件描述
- participants: 参与角色
- importance: 重要程度 (low/normal/high/critical)

### 5. 物品信息 (items)
识别关键物品:
- name: 物品名
- description: 描述 (英文)
- importance: 重要程度 (prop/key_item/mcguffin)

## 输出格式
```json
{
  "characters": {...},
  "dialogues": [...],
  "scenes": [...],
  "events": [...],
  "items": [...],
  "chapter_summary": "章节摘要",
  "mood_progression": ["开始情绪", "中间情绪", "结束情绪"]
}
```
```

#### A.2 页面规划提示词

```
你是专业的漫画分镜师。请根据以下章节信息规划页面结构。

## 章节信息
{chapter_info_json}

## 规划要求

1. 页面数量: {min_pages}-{max_pages} 页
2. 每页应包含 1-3 个相关事件
3. 高潮事件应使用更多页面空间
4. 注意节奏变化: 慢-快-慢 或 平稳-高潮-收尾

## 输出格式
```json
{
  "total_pages": 10,
  "pages": [
    {
      "page_number": 1,
      "event_indices": [0, 1],
      "content_summary": "开场，主角登场",
      "pacing": "slow",
      "role": "opening",
      "key_characters": ["李明"],
      "has_dialogue": true,
      "has_action": false,
      "suggested_panel_count": 4,
      "notes": "建立场景氛围"
    }
  ],
  "pacing_notes": "整体节奏说明",
  "climax_pages": [6, 7]
}
```
```

### B. 相关文件路径

| 文件 | 用途 |
|:-----|:-----|
| `backend/app/services/manga_prompt/core/service.py` | 主服务，需重构 |
| `backend/app/services/manga_prompt/core/prompts.py` | 场景提取提示词 |
| `backend/app/services/manga_prompt/scene_expansion/` | 场景展开，需替换 |
| `backend/app/services/manga_prompt/panel_prompt/` | 提示词构建，需重构 |
| `backend/app/api/routers/writer/manga_prompt_v2.py` | API路由，小调整 |
| `backend/app/repositories/manga_prompt_repository.py` | 数据访问，复用 |

---

**文档结束**
