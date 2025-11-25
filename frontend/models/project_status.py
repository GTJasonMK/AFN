"""
项目状态管理模块

参照Web应用的状态机设计，实现严格的串行工作流控制。
"""

from enum import Enum
from typing import Optional


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


class ProjectStatusHelpers:
    """项目状态权限检查辅助类"""

    @staticmethod
    def can_access_concept_dialogue(status: str) -> bool:
        """
        检查是否可以访问概念对话页

        规则：任何状态都可以访问（用于查看历史对话）
        """
        return True

    @staticmethod
    def can_access_blueprint(status: str) -> bool:
        """
        检查是否可以访问蓝图编辑页

        规则：必须完成概念对话并生成蓝图后才能访问
        """
        return status in [
            ProjectStatus.BLUEPRINT_READY,
            ProjectStatus.PART_OUTLINES_READY,
            ProjectStatus.CHAPTER_OUTLINES_READY,
            ProjectStatus.WRITING,
            ProjectStatus.COMPLETED
        ]

    @staticmethod
    def can_access_writing_desk(status: str) -> bool:
        """
        检查是否可以访问写作台

        规则：必须完成章节大纲后才能开始写作
        """
        return status in [
            ProjectStatus.CHAPTER_OUTLINES_READY,
            ProjectStatus.WRITING,
            ProjectStatus.COMPLETED
        ]

    @staticmethod
    def can_generate_blueprint(status: str) -> bool:
        """
        检查是否可以生成蓝图

        规则：仅在draft状态可以生成蓝图
        """
        return status == ProjectStatus.DRAFT

    @staticmethod
    def can_start_writing(status: str) -> bool:
        """
        检查是否可以开始写作

        规则：章节大纲就绪或已在写作中
        """
        return status in [
            ProjectStatus.CHAPTER_OUTLINES_READY,
            ProjectStatus.WRITING
        ]

    @staticmethod
    def get_entry_page(status: str) -> int:
        """
        确定进入项目时应该显示的页面

        参数:
            status: 项目状态

        返回:
            页面索引（对应MainWindowV2的PAGE_*常量）
        """
        from ui.main_window_v2 import MainWindowV2

        if status == ProjectStatus.DRAFT:
            # draft状态强制进入概念对话
            return MainWindowV2.PAGE_CONCEPT_DIALOGUE
        elif status in [ProjectStatus.BLUEPRINT_READY, ProjectStatus.PART_OUTLINES_READY]:
            # 蓝图就绪但还未完成章节大纲，进入蓝图编辑页
            return MainWindowV2.PAGE_BLUEPRINT
        else:
            # chapter_outlines_ready, writing, completed 状态进入写作台
            return MainWindowV2.PAGE_WRITING_DESK

    @staticmethod
    def get_status_display_name(status: str) -> str:
        """
        获取状态的显示名称

        参数:
            status: 项目状态

        返回:
            中文显示名称
        """
        status_names = {
            ProjectStatus.DRAFT: "草稿",
            ProjectStatus.BLUEPRINT_READY: "蓝图就绪",
            ProjectStatus.PART_OUTLINES_READY: "分卷大纲就绪",
            ProjectStatus.CHAPTER_OUTLINES_READY: "章节大纲就绪",
            ProjectStatus.WRITING: "写作中",
            ProjectStatus.COMPLETED: "已完成"
        }
        return status_names.get(status, "未知状态")

    @staticmethod
    def get_status_badge_type(status: str) -> str:
        """
        获取状态徽章的类型（用于StatusBadge组件）

        参数:
            status: 项目状态

        返回:
            徽章类型：successful, generating, pending, warning, error, info
        """
        if status == ProjectStatus.COMPLETED:
            return 'successful'
        elif status == ProjectStatus.WRITING:
            return 'generating'
        elif status == ProjectStatus.DRAFT:
            return 'pending'
        elif status in [ProjectStatus.CHAPTER_OUTLINES_READY, ProjectStatus.PART_OUTLINES_READY]:
            return 'info'
        else:  # BLUEPRINT_READY
            return 'info'

    @staticmethod
    def get_locked_page_message(page_name: str, current_status: str) -> str:
        """
        获取页面锁定提示信息

        参数:
            page_name: 页面名称
            current_status: 当前项目状态

        返回:
            提示信息
        """
        if page_name == "蓝图编辑":
            return "请先完成概念对话并生成蓝图"
        elif page_name == "写作台":
            if current_status == ProjectStatus.DRAFT:
                return "请先完成概念对话并生成蓝图"
            elif current_status == ProjectStatus.BLUEPRINT_READY:
                return "请先完成章节大纲"
            elif current_status == ProjectStatus.PART_OUTLINES_READY:
                return "请先完成章节大纲细化"
            else:
                return "暂时无法访问写作台"
        else:
            return "当前状态下无法访问此页面"
