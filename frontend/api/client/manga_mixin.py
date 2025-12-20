"""
漫画提示词 Mixin

提供漫画提示词生成和管理的API方法。
"""

from typing import Any, Dict, Optional

from api.exceptions import NotFoundError

from .constants import TimeoutConfig


class MangaMixin:
    """漫画提示词方法 Mixin"""

    def get_manga_prompt_status(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        获取漫画提示词生成状态

        用于检查是否有未完成的生成任务可以继续。

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            状态信息，包含：
            - status: 生成状态 (none/pending/scene_extracted/layout_generated/completed/failed)
            - has_checkpoint: 是否有可恢复的检查点
            - failed_step: 失败的步骤（如果有）
            - error_message: 错误信息（如果有）
            - progress_info: 进度详情
        """
        return self._request(
            'GET',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts/status',
        )

    def generate_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
        style: str = "manga",
        scene_count: Optional[int] = None,
        dialogue_language: str = "chinese",
        continue_from_checkpoint: bool = False,
    ) -> Dict[str, Any]:
        """
        生成章节的漫画提示词

        将章节内容智能分割为多个关键画面，并为每个画面生成文生图提示词。
        支持断点续传：如果 continue_from_checkpoint=True，会从上次中断的步骤继续。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            style: 漫画风格 (manga/anime/comic/webtoon)
            scene_count: 目标场景数量 (5-20)，为None时由LLM自动决定
            dialogue_language: 对话语言 (chinese/japanese/english/korean/none)
            continue_from_checkpoint: 是否从检查点继续生成

        Returns:
            漫画提示词结果，包含：
            - character_profiles: 角色外观描述字典
            - scenes: 场景列表
            - style_guide: 整体风格指南
        """
        # 构建请求体，scene_count为None时不传递，让LLM自动决定
        payload = {
            'style': style,
            'dialogue_language': dialogue_language,
        }
        if scene_count is not None:
            payload['scene_count'] = scene_count

        # 构建URL，包含continue_from_checkpoint参数
        url = f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts'
        if continue_from_checkpoint:
            url += '?continue_from_checkpoint=true'

        return self._request(
            'POST',
            url,
            payload,
            timeout=TimeoutConfig.READ_GENERATION
        )

    def get_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Optional[Dict[str, Any]]:
        """
        获取已保存的漫画提示词

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            漫画提示词结果，如果不存在返回None
        """
        try:
            return self._request(
                'GET',
                f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts',
            )
        except NotFoundError:
            return None

    def update_manga_scene(
        self,
        project_id: str,
        chapter_number: int,
        scene_id: int,
        update_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        更新单个场景的提示词

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID
            update_data: 更新数据

        Returns:
            更新后的场景
        """
        return self._request(
            'PUT',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts/scenes/{scene_id}',
            update_data,
        )

    def delete_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        删除章节的漫画提示词

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
