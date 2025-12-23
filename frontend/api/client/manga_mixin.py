"""
漫画提示词 Mixin

提供漫画提示词生成和管理的API方法。
基于专业漫画分镜架构，支持页面模板和画格级提示词生成。
"""

from typing import Any, Dict, List, Optional

from api.exceptions import NotFoundError

from .constants import TimeoutConfig


class MangaMixin:
    """漫画提示词方法 Mixin"""

    def get_manga_templates(self) -> List[Dict[str, Any]]:
        """
        获取所有可用的页面模板

        Returns:
            模板列表，每个模板包含：
            - id: 模板ID
            - name: 英文名称
            - name_zh: 中文名称
            - description: 模板描述
            - panel_count: 画格数量
            - suitable_moods: 适用情感类型列表
            - intensity: 强度等级
        """
        return self._request(
            'GET',
            '/api/writer/templates',
        )

    def generate_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
        style: str = "manga",
        min_scenes: int = 5,
        max_scenes: int = 15,
        language: str = "chinese",
    ) -> Dict[str, Any]:
        """
        生成章节的漫画分镜（支持断点续传）

        基于专业漫画分镜理念，将章节内容转化为：
        1. 多个叙事场景
        2. 每个场景展开为页面+画格
        3. 每个画格生成专属提示词

        如果之前的生成任务中断，会自动从断点继续。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            style: 漫画风格 (manga/anime/comic/webtoon)
            min_scenes: 最少场景数 (3-10)
            max_scenes: 最多场景数 (5-25)
            language: 对话/音效语言 (chinese/japanese/english/korean)

        Returns:
            漫画分镜结果，包含：
            - chapter_number: 章节号
            - style: 漫画风格
            - character_profiles: 角色外观描述字典
            - total_pages: 总页数
            - total_panels: 总画格数
            - scenes: 场景列表，每个场景包含页面信息
            - panels: 画格提示词列表
        """
        payload = {
            'style': style,
            'min_scenes': min_scenes,
            'max_scenes': max_scenes,
            'language': language,
        }

        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts',
            payload,
            timeout=TimeoutConfig.READ_GENERATION
        )

    def get_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取已保存的漫画分镜

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            漫画分镜结果，如果不存在返回None
        """
        try:
            return self._request(
                'GET',
                f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts',
            )
        except NotFoundError:
            return None

    def delete_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        删除章节的漫画分镜

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts',
        )

    def get_manga_prompt_progress(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        获取漫画分镜生成进度

        用于检测是否有未完成的断点，支持断点续传。

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            进度信息，包含：
            - status: 状态 (pending/extracting/expanding/completed)
            - stage: 当前阶段
            - current: 当前进度
            - total: 总数
            - message: 进度消息
            - can_resume: 是否可以继续
        """
        return self._request(
            'GET',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts/progress',
        )
