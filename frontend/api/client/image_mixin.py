"""
图片生成 Mixin

提供图片生成配置、图片生成和PDF导出的API方法。
"""

from typing import Any, Dict, List, Optional

from .constants import TimeoutConfig


class ImageMixin:
    """图片生成方法 Mixin"""

    # ==================== 图片生成配置 ====================

    def get_image_configs(self) -> List[Dict[str, Any]]:
        """获取图片生成配置列表"""
        return self._request('GET', '/api/image-generation/configs')

    def get_image_config(self, config_id: int) -> Dict[str, Any]:
        """
        获取指定图片生成配置

        Args:
            config_id: 配置ID

        Returns:
            配置详情
        """
        return self._request('GET', f'/api/image-generation/configs/{config_id}')

    def create_image_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建图片生成配置

        Args:
            config_data: 配置数据

        Returns:
            创建的配置
        """
        return self._request('POST', '/api/image-generation/configs', config_data)

    def update_image_config(
        self,
        config_id: int,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        更新图片生成配置

        Args:
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置
        """
        return self._request('PUT', f'/api/image-generation/configs/{config_id}', config_data)

    def delete_image_config(self, config_id: int) -> Dict[str, Any]:
        """
        删除图片生成配置

        Args:
            config_id: 配置ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/image-generation/configs/{config_id}')

    def activate_image_config(self, config_id: int) -> Dict[str, Any]:
        """
        激活图片生成配置

        Args:
            config_id: 配置ID

        Returns:
            激活结果
        """
        return self._request('POST', f'/api/image-generation/configs/{config_id}/activate')

    def test_image_config(self, config_id: int) -> Dict[str, Any]:
        """
        测试图片生成配置连接

        Args:
            config_id: 配置ID

        Returns:
            测试结果，包含 success 和 message 字段
        """
        return self._request(
            'POST',
            f'/api/image-generation/configs/{config_id}/test',
            timeout=TimeoutConfig.READ_GENERATION
        )

    def export_image_config(self, config_id: int) -> Dict[str, Any]:
        """
        导出单个图片生成配置

        Args:
            config_id: 配置ID

        Returns:
            导出数据
        """
        return self._request('GET', f'/api/image-generation/configs/{config_id}/export')

    def export_image_configs(self) -> Dict[str, Any]:
        """
        导出所有图片生成配置

        Returns:
            导出数据
        """
        return self._request('GET', '/api/image-generation/configs/export/all')

    def import_image_configs(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入图片生成配置

        Args:
            import_data: 导入数据

        Returns:
            导入结果
        """
        return self._request('POST', '/api/image-generation/configs/import', import_data)

    # ==================== 图片生成 ====================

    def generate_scene_image(
        self,
        project_id: str,
        chapter_number: int,
        scene_id: int,
        prompt: str,
        style: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        panel_id: Optional[str] = None,
        reference_image_paths: Optional[List[str]] = None,
        reference_strength: Optional[float] = None,
        # Bug 25/38 修复: 添加章节版本ID参数
        chapter_version_id: Optional[int] = None,
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
        为场景生成图片

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID
            prompt: 图片生成提示词
            style: 图片风格（可选）
            aspect_ratio: 宽高比（可选，如 "16:9", "4:3", "1:1" 等）
            quality: 质量预设（可选）
            negative_prompt: 负面提示词（可选）
            panel_id: 画格ID，格式如 scene1_page1_panel1（可选）
            reference_image_paths: 参考图片路径列表（角色立绘等）
            reference_strength: 参考强度 0.0-1.0（可选）
            dialogue: 对话内容（用于增强提示词）
            dialogue_speaker: 对话说话者
            dialogue_bubble_type: 气泡类型 (normal/shout/whisper/thought)
            dialogue_emotion: 说话情绪
            dialogue_position: 气泡位置 (top-right/top-left等)
            narration: 旁白内容
            narration_position: 旁白位置 (top/bottom/left/right)
            sound_effects: 音效列表
            sound_effect_details: 详细音效信息（含类型、强度）
            composition: 构图 (wide shot/medium shot/close-up等)
            camera_angle: 镜头角度 (eye level/low angle/high angle等)
            is_key_panel: 是否为关键画格
            characters: 角色列表
            lighting: 光线描述
            atmosphere: 氛围描述
            key_visual_elements: 关键视觉元素列表

        Returns:
            生成结果，包含图片URL和信息
        """
        data = {'prompt': prompt}
        if style:
            data['style'] = style
        if aspect_ratio:
            # 后端使用 'ratio' 字段
            data['ratio'] = aspect_ratio
        if quality:
            data['quality'] = quality
        if negative_prompt:
            data['negative_prompt'] = negative_prompt
        if panel_id:
            data['panel_id'] = panel_id
        if reference_image_paths:
            data['reference_image_paths'] = reference_image_paths
        if reference_strength is not None:
            data['reference_strength'] = reference_strength

        # Bug 25/38 修复: 传递章节版本ID
        if chapter_version_id is not None:
            data['chapter_version_id'] = chapter_version_id

        # 漫画画格元数据 - 对话相关
        if dialogue:
            data['dialogue'] = dialogue
        if dialogue_speaker:
            data['dialogue_speaker'] = dialogue_speaker
        if dialogue_bubble_type:
            data['dialogue_bubble_type'] = dialogue_bubble_type
        if dialogue_emotion:
            data['dialogue_emotion'] = dialogue_emotion
        if dialogue_position:
            data['dialogue_position'] = dialogue_position

        # 漫画画格元数据 - 旁白相关
        if narration:
            data['narration'] = narration
        if narration_position:
            data['narration_position'] = narration_position

        # 漫画画格元数据 - 音效相关
        if sound_effects:
            data['sound_effects'] = sound_effects
        if sound_effect_details:
            data['sound_effect_details'] = sound_effect_details

        # 漫画画格元数据 - 视觉相关
        if composition:
            data['composition'] = composition
        if camera_angle:
            data['camera_angle'] = camera_angle
        if is_key_panel:
            data['is_key_panel'] = is_key_panel
        if characters:
            data['characters'] = characters
        if lighting:
            data['lighting'] = lighting
        if atmosphere:
            data['atmosphere'] = atmosphere
        if key_visual_elements:
            data['key_visual_elements'] = key_visual_elements

        # 语言设置
        if dialogue_language:
            data['dialogue_language'] = dialogue_language

        return self._request(
            'POST',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/scenes/{scene_id}/generate',
            data,
            timeout=TimeoutConfig.READ_GENERATION
        )

    def generate_page_image(
        self,
        project_id: str,
        chapter_number: int,
        page_number: int,
        full_page_prompt: str,
        negative_prompt: Optional[str] = None,
        layout_template: str = "",
        layout_description: str = "",
        aspect_ratio: str = "3:4",
        resolution: str = "2K",
        style: str = "manga",
        chapter_version_id: Optional[int] = None,
        reference_image_paths: Optional[List[str]] = None,
        reference_strength: float = 0.5,
        panel_summaries: Optional[List[Dict[str, Any]]] = None,
        dialogue_language: str = "chinese",
    ) -> Dict[str, Any]:
        """
        为整页漫画生成图片

        让AI直接生成带分格布局的整页漫画，包含对话气泡和音效文字。
        相比逐panel生成，整页生成的画面更统一，布局更自然。

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            page_number: 页码
            full_page_prompt: 整页漫画提示词（由 PromptBuilder.build_page_prompt() 生成）
            negative_prompt: 负面提示词（可选）
            layout_template: 布局模板名（如 "3row_1x2x1"）
            layout_description: 布局描述文本
            aspect_ratio: 页面宽高比（默认 3:4 漫画页标准比例）
            resolution: 分辨率（默认 2K，整页建议高分辨率）
            style: 风格（默认 manga）
            chapter_version_id: 章节版本ID（可选）
            reference_image_paths: 角色立绘路径列表（可选）
            reference_strength: 参考图影响强度
            panel_summaries: 画格简要信息列表（用于后续处理）
            dialogue_language: 对话语言（默认 chinese）

        Returns:
            生成结果，包含图片URL和信息
        """
        data = {
            'full_page_prompt': full_page_prompt,
            'ratio': aspect_ratio,
            'resolution': resolution,
            'style': style,
            'reference_strength': reference_strength,
            'dialogue_language': dialogue_language,
        }

        if negative_prompt:
            data['negative_prompt'] = negative_prompt
        if layout_template:
            data['layout_template'] = layout_template
        if layout_description:
            data['layout_description'] = layout_description
        if chapter_version_id is not None:
            data['chapter_version_id'] = chapter_version_id
        if reference_image_paths:
            data['reference_image_paths'] = reference_image_paths
        if panel_summaries:
            data['panel_summaries'] = panel_summaries

        return self._request(
            'POST',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/pages/{page_number}/generate',
            data,
            timeout=TimeoutConfig.READ_GENERATION
        )

    def get_scene_images(
        self,
        project_id: str,
        chapter_number: int,
        scene_id: int,
    ) -> Dict[str, Any]:
        """
        获取场景的所有图片

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID

        Returns:
            图片列表
        """
        return self._request(
            'GET',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/scenes/{scene_id}/images'
        )

    def get_chapter_images(
        self,
        project_id: str,
        chapter_number: int,
    ) -> List[Dict[str, Any]]:
        """
        获取章节的所有图片

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            图片列表
        """
        return self._request(
            'GET',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/images'
        )

    def delete_generated_image(self, image_id: int) -> Dict[str, Any]:
        """
        删除生成的图片

        Args:
            image_id: 图片ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/image-generation/images/{image_id}')

    def toggle_image_selection(
        self,
        image_id: int,
        selected: bool = True
    ) -> Dict[str, Any]:
        """
        切换图片选中状态（用于PDF导出）

        Args:
            image_id: 图片ID
            selected: 是否选中

        Returns:
            操作结果
        """
        return self._request(
            'POST',
            f'/api/image-generation/images/{image_id}/toggle-selection',
            params={'selected': selected}
        )

    # ==================== PDF导出 ====================

    def _build_pdf_payload(
        self,
        *,
        title: Optional[str],
        page_size: str,
        include_prompts: bool,
        **extra_fields: Any
    ) -> Dict[str, Any]:
        """构建PDF导出通用payload"""
        data: Dict[str, Any] = {
            'page_size': page_size,
            'include_prompts': include_prompts,
        }
        if title:
            data['title'] = title
        if extra_fields:
            data.update(extra_fields)
        return data

    def _post_pdf_request(
        self,
        path: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """统一发起PDF导出请求"""
        return self._request(
            'POST',
            path,
            payload,
            timeout=TimeoutConfig.READ_GENERATION
        )

    def export_images_to_pdf(
        self,
        project_id: str,
        image_ids: List[int],
        title: Optional[str] = None,
        page_size: str = "A4",
        images_per_page: int = 2,
        include_prompts: bool = False,
    ) -> Dict[str, Any]:
        """
        导出图片为PDF

        Args:
            project_id: 项目ID
            image_ids: 要导出的图片ID列表
            title: PDF标题
            page_size: 页面大小（A4/A3/Letter）
            images_per_page: 每页图片数量
            include_prompts: 是否包含提示词

        Returns:
            导出结果，包含下载URL
        """
        data = self._build_pdf_payload(
            title=title,
            page_size=page_size,
            include_prompts=include_prompts,
            project_id=project_id,
            image_ids=image_ids,
            images_per_page=images_per_page,
        )

        return self._post_pdf_request(
            '/api/image-generation/export/pdf',
            data,
        )

    def get_image_file_url(
        self,
        project_id: str,
        chapter_number: int,
        scene_id: int,
        file_name: str,
    ) -> str:
        """
        获取图片文件的URL

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID
            file_name: 文件名

        Returns:
            图片文件URL
        """
        return f"{self.base_url}/api/image-generation/files/{project_id}/chapter_{chapter_number}/scene_{scene_id}/{file_name}"

    def generate_chapter_manga_pdf(
        self,
        project_id: str,
        chapter_number: int,
        title: Optional[str] = None,
        page_size: str = "A4",
        include_prompts: bool = False,
        layout: str = "manga",  # 默认使用漫画分格排版
        # Bug 26 修复: 添加章节版本ID参数
        chapter_version_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        生成章节漫画PDF

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: PDF标题
            page_size: 页面大小（A4/A3/Letter）
            include_prompts: 是否包含提示词
            layout: 布局模式（manga=漫画分格排版, full=一页一图）
            chapter_version_id: 章节版本ID（可选，用于过滤特定版本的图片）

        Returns:
            生成结果，包含下载URL
        """
        data = self._build_pdf_payload(
            title=title,
            page_size=page_size,
            include_prompts=include_prompts,
            layout=layout,
            chapter_version_id=chapter_version_id,
        )

        return self._post_pdf_request(
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/manga-pdf',
            data,
        )

    def get_latest_chapter_manga_pdf(
        self,
        project_id: str,
        chapter_number: int,
    ) -> Dict[str, Any]:
        """
        获取章节最新的漫画PDF

        Args:
            project_id: 项目ID
            chapter_number: 章节号

        Returns:
            PDF信息，包含下载URL
        """
        return self._request(
            'GET',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/manga-pdf/latest'
        )

    def get_export_download_url(self, file_name: str) -> str:
        """
        获取导出文件下载URL

        Args:
            file_name: 文件名

        Returns:
            下载URL
        """
        return f"{self.base_url}/api/image-generation/export/download/{file_name}"
