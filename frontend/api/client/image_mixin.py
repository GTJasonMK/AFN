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
    ) -> Dict[str, Any]:
        """
        为场景生成图片

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            scene_id: 场景ID
            prompt: 图片生成提示词
            style: 图片风格（可选）
            aspect_ratio: 宽高比（可选）
            quality: 质量预设（可选）

        Returns:
            生成结果，包含图片URL和信息
        """
        data = {'prompt': prompt}
        if style:
            data['style'] = style
        if aspect_ratio:
            data['aspect_ratio'] = aspect_ratio
        if quality:
            data['quality'] = quality

        return self._request(
            'POST',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/scenes/{scene_id}/generate',
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
        data = {
            'project_id': project_id,
            'image_ids': image_ids,
            'page_size': page_size,
            'images_per_page': images_per_page,
            'include_prompts': include_prompts,
        }
        if title:
            data['title'] = title

        return self._request(
            'POST',
            '/api/image-generation/export/pdf',
            data,
            timeout=TimeoutConfig.READ_GENERATION
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
    ) -> Dict[str, Any]:
        """
        生成章节漫画PDF

        Args:
            project_id: 项目ID
            chapter_number: 章节号
            title: PDF标题
            page_size: 页面大小（A4/A3/Letter）
            include_prompts: 是否包含提示词

        Returns:
            生成结果，包含下载URL
        """
        data = {
            'page_size': page_size,
            'include_prompts': include_prompts,
        }
        if title:
            data['title'] = title

        return self._request(
            'POST',
            f'/api/image-generation/novels/{project_id}/chapters/{chapter_number}/manga-pdf',
            data,
            timeout=TimeoutConfig.READ_GENERATION
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
