"""
漫画提示词 Mixin

提供漫画提示词生成和管理的API方法。
基于页面驱动的漫画分镜架构。
"""

from typing import Any, Dict, List, Optional

from api.exceptions import NotFoundError

from .constants import TimeoutConfig


class MangaMixin:
    """漫画提示词方法 Mixin"""

    def generate_manga_prompts(
        self,
        project_id: str,
        chapter_number: int,
        style: str = "manga",
        min_pages: int = 8,
        max_pages: int = 15,
        language: str = "chinese",
        use_portraits: bool = True,
        auto_generate_portraits: bool = True,
        force_restart: bool = False,
        start_from_stage: Optional[str] = None,
        auto_generate_page_images: bool = False,
        page_prompt_concurrency: int = 5,
    ) -> Dict[str, Any]:
        """
        生成章节的漫画分镜（支持断点续传和指定起始阶段）

        基于页面驱动的4步流水线：
        1. 信息提取 - 提取角色、对话、事件、场景
        2. 页面规划 - 全局页数分配和节奏控制
        3. 分镜设计 - 每页画格设计
        4. 提示词构建 - 生成AI绘图提示词
        5. (可选) 整页图片生成 - 自动生成所有页面的整页漫画图片

        如果之前的生成任务中断，会自动从断点继续（除非 force_restart=True）。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            style: 漫画风格 (manga/anime/comic/webtoon)
            min_pages: 最少页数 (3-20)
            max_pages: 最多页数 (5-30)
            language: 对话/音效语言 (chinese/japanese/english/korean)
            use_portraits: 是否使用角色立绘作为参考图
            auto_generate_portraits: 是否自动为缺失立绘的角色生成立绘
            force_restart: 是否强制从头开始，忽略断点
            start_from_stage: 指定从哪个阶段开始 (extraction/planning/storyboard/prompt_building)
            auto_generate_page_images: 是否在分镜生成完成后自动生成所有整页图片
            page_prompt_concurrency: 整页提示词LLM生成的并发数 (1-20)

        Returns:
            漫画分镜结果，包含：
            - chapter_number: 章节号
            - style: 漫画风格
            - character_profiles: 角色外观描述字典
            - total_pages: 总页数
            - total_panels: 总画格数
            - pages: 页面列表
            - panels: 画格提示词列表
        """
        payload = {
            'style': style,
            'min_pages': min_pages,
            'max_pages': max_pages,
            'language': language,
            'use_portraits': use_portraits,
            'auto_generate_portraits': auto_generate_portraits,
            'force_restart': force_restart,
            'auto_generate_page_images': auto_generate_page_images,
            'page_prompt_concurrency': page_prompt_concurrency,
        }

        # 只有指定了起始阶段才添加到请求中
        if start_from_stage:
            payload['start_from_stage'] = start_from_stage

        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts',
            payload,
            timeout=TimeoutConfig.READ_LONG  # 漫画分镜生成涉及多个LLM调用，需要较长超时
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
            - status: 状态 (pending/extracting/expanding/completed/cancelled)
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

    def cancel_manga_prompt_generation(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        取消漫画分镜生成

        将生成状态设置为 cancelled，正在进行的生成任务会在下次检查点时停止。

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            取消结果，包含：
            - success: 是否成功
            - message: 结果消息
        """
        return self._request(
            'POST',
            f'/api/writer/novels/{project_id}/chapters/{chapter_number}/manga-prompts/cancel',
        )

    def preview_image_prompt(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        style: Optional[str] = None,
        ratio: Optional[str] = None,
        resolution: Optional[str] = None,
        # 漫画画格元数据 - 对话相关
        dialogue: Optional[str] = None,
        dialogue_speaker: Optional[str] = None,
        dialogue_bubble_type: Optional[str] = None,
        dialogue_emotion: Optional[str] = None,
        dialogue_position: Optional[str] = None,
        # 漫画画格元数据 - 旁白相关
        narration: Optional[str] = None,
        narration_position: Optional[str] = None,
        # 漫画画格元数据 - 音效相关
        sound_effects: Optional[List[str]] = None,
        sound_effect_details: Optional[List[Dict[str, Any]]] = None,
        # 漫画画格元数据 - 视觉相关
        composition: Optional[str] = None,
        camera_angle: Optional[str] = None,
        is_key_panel: bool = False,
        characters: Optional[List[str]] = None,
        lighting: Optional[str] = None,
        atmosphere: Optional[str] = None,
        key_visual_elements: Optional[List[str]] = None,
        # 语言设置
        dialogue_language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        预览处理后的图片生成提示词（不生成图片）

        展示发送给生图模型的实际提示词，包括：
        - 场景类型检测结果
        - 动态添加的上下文前缀
        - 风格后缀（如果需要）
        - 宽高比描述
        - 漫画视觉元素（对话、旁白、音效、构图、镜头等）
        - 负面提示词

        Args:
            prompt: 原始提示词
            negative_prompt: 负面提示词
            style: 风格
            ratio: 宽高比
            resolution: 分辨率
            dialogue: 对话内容
            dialogue_speaker: 对话说话者
            dialogue_bubble_type: 气泡类型
            dialogue_emotion: 说话情绪
            dialogue_position: 气泡位置
            narration: 旁白内容
            narration_position: 旁白位置
            sound_effects: 音效列表
            sound_effect_details: 详细音效信息
            composition: 构图
            camera_angle: 镜头角度
            is_key_panel: 是否为关键画格
            characters: 角色列表
            lighting: 光线描述
            atmosphere: 氛围描述
            key_visual_elements: 关键视觉元素

        Returns:
            预览结果，包含：
            - success: 是否成功
            - original_prompt: 原始提示词
            - scene_type: 检测到的场景类型（英文）
            - scene_type_zh: 场景类型（中文）
            - final_prompt: 最终发送给模型的完整提示词
            - prompt_without_context: 不带上下文前缀的提示词
            - manga_visual_elements: 漫画视觉元素描述
            - provider: 当前供应商类型
            - model: 当前模型名称
        """
        payload = {
            'prompt': prompt,
        }
        if negative_prompt:
            payload['negative_prompt'] = negative_prompt
        if style:
            payload['style'] = style
        if ratio:
            payload['ratio'] = ratio
        if resolution:
            payload['resolution'] = resolution

        # 漫画画格元数据 - 对话相关
        if dialogue:
            payload['dialogue'] = dialogue
        if dialogue_speaker:
            payload['dialogue_speaker'] = dialogue_speaker
        if dialogue_bubble_type:
            payload['dialogue_bubble_type'] = dialogue_bubble_type
        if dialogue_emotion:
            payload['dialogue_emotion'] = dialogue_emotion
        if dialogue_position:
            payload['dialogue_position'] = dialogue_position

        # 漫画画格元数据 - 旁白相关
        if narration:
            payload['narration'] = narration
        if narration_position:
            payload['narration_position'] = narration_position

        # 漫画画格元数据 - 音效相关
        if sound_effects:
            payload['sound_effects'] = sound_effects
        if sound_effect_details:
            payload['sound_effect_details'] = sound_effect_details

        # 漫画画格元数据 - 视觉相关
        if composition:
            payload['composition'] = composition
        if camera_angle:
            payload['camera_angle'] = camera_angle
        if is_key_panel:
            payload['is_key_panel'] = is_key_panel
        if characters:
            payload['characters'] = characters
        if lighting:
            payload['lighting'] = lighting
        if atmosphere:
            payload['atmosphere'] = atmosphere
        if key_visual_elements:
            payload['key_visual_elements'] = key_visual_elements

        # 语言设置
        if dialogue_language:
            payload['dialogue_language'] = dialogue_language

        return self._request(
            'POST',
            '/api/image-generation/preview-prompt',
            payload,
        )
