"""
项目状态管理模块

参照Web应用的状态机设计，实现严格的串行工作流控制。
"""

from enum import Enum


class ProjectStatus(str, Enum):
    """
    项目状态枚举

    工作流：
    draft → blueprint_ready → [part_outlines_ready] → chapter_outlines_ready → writing → completed

    说明：
    - draft: 概念对话阶段，用户需要完善世界观和剧情要素
    - blueprint_ready: 蓝图已生成，可以编辑世界观、角色、章节纲要
    - part_outlines_ready: 分卷大纲就绪（仅长篇小说>50章）
    - chapter_outlines_ready: 章节大纲就绪，可以开始写作
    - writing: 写作进行中
    - completed: 所有章节已完成
    """
    DRAFT = "draft"
    BLUEPRINT_READY = "blueprint_ready"
    PART_OUTLINES_READY = "part_outlines_ready"
    CHAPTER_OUTLINES_READY = "chapter_outlines_ready"
    WRITING = "writing"
    COMPLETED = "completed"
