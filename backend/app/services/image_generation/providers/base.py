"""
图片生成供应商基类

定义供应商接口规范，所有具体供应商都需要实现这些方法。
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any, List, Optional

import httpx

from ....models.image_config import ImageGenerationConfig
from ..schemas import ImageGenerationRequest


# HTTP客户端默认配置
DEFAULT_TEST_TIMEOUT = 30.0  # 测试连接超时
DEFAULT_GENERATE_TIMEOUT = 180.0  # 图片生成超时（较长，因为生成需要时间）


@dataclass
class ProviderTestResult:
    """供应商测试结果"""
    success: bool
    message: str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderGenerateResult:
    """供应商生成结果"""
    success: bool
    image_urls: List[str] = field(default_factory=list)
    error_message: str = ""
    extra_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReferenceImageInfo:
    """参考图信息（用于img2img）"""
    file_path: str  # 图片文件路径
    base64_data: Optional[str] = None  # Base64编码数据（可选，运行时填充）
    strength: float = 0.7  # 参考图影响强度


class BaseImageProvider(ABC):
    """
    图片生成供应商抽象基类

    所有具体供应商需要实现以下方法：
    - test_connection: 测试连接是否正常
    - generate: 生成图片

    可选重写：
    - get_supported_features: 获取供应商支持的特性
    """

    # 供应商标识符，子类必须设置
    PROVIDER_TYPE: str = ""

    # 供应商显示名称
    DISPLAY_NAME: str = ""

    # 场景类型关键词映射 - 用于从提示词推断场景类型
    SCENE_TYPE_KEYWORDS = {
        "action": ["fight", "battle", "attack", "combat", "action", "speed lines", "motion blur", "dynamic"],
        "romantic": ["romantic", "love", "kiss", "embrace", "tender", "gentle", "sparkle", "blush"],
        "horror": ["horror", "scary", "dark", "ominous", "creepy", "shadow", "fear", "terror"],
        "comedy": ["comedy", "funny", "laugh", "chibi", "exaggerated", "comedic", "silly"],
        "emotional": ["emotional", "crying", "tears", "sad", "happy", "touching", "heartfelt"],
        "mystery": ["mystery", "suspense", "tense", "dramatic shadows", "noir", "detective"],
        "daily": ["daily", "casual", "slice of life", "peaceful", "calm", "relaxed", "everyday"],
    }

    # 场景类型到上下文描述的映射
    SCENE_CONTEXT_MAP = {
        "action": (
            "Scene Type: Action/Battle sequence - dynamic combat or intense physical activity.\n"
            "场景类型: 动作/战斗场景 - 动态战斗或激烈的身体活动。\n"
        ),
        "romantic": (
            "Scene Type: Romantic/Emotional moment - tender interaction between characters.\n"
            "场景类型: 浪漫/情感场景 - 角色之间的温柔互动。\n"
        ),
        "horror": (
            "Scene Type: Horror/Suspense atmosphere - dark and mysterious mood.\n"
            "场景类型: 恐怖/悬疑氛围 - 黑暗神秘的氛围。\n"
        ),
        "comedy": (
            "Scene Type: Comedy/Light-hearted moment - humorous and playful scene.\n"
            "场景类型: 喜剧/轻松场景 - 幽默有趣的画面。\n"
        ),
        "emotional": (
            "Scene Type: Emotional/Dramatic moment - deep feelings and character development.\n"
            "场景类型: 情感/戏剧性场景 - 深刻的情感和角色发展。\n"
        ),
        "mystery": (
            "Scene Type: Mystery/Suspense scene - tense atmosphere with unknown elements.\n"
            "场景类型: 悬疑/紧张场景 - 充满未知元素的紧张氛围。\n"
        ),
        "daily": (
            "Scene Type: Daily life/Slice of life - peaceful everyday moment.\n"
            "场景类型: 日常生活场景 - 平静的日常时刻。\n"
        ),
    }

    # 基础上下文前缀模板
    BASE_CONTEXT_TEMPLATE = (
        "[CONTENT CONTEXT / 内容说明]\n"
        "Purpose: Professional manga/comic illustration for a licensed novel-to-manga adaptation project.\n"
        "用途: 专业的漫画插图，用于正版小说改编漫画项目。\n"
        "Usage: This artwork is created for legitimate storytelling and publishing purposes in creative fiction.\n"
        "使用场景: 该作品用于合法的故事叙述和创意小说出版用途。\n"
        "Content Rating: General audience / All ages appropriate artistic content.\n"
        "内容分级: 面向普通观众/适合所有年龄段的艺术内容。\n"
        "Style: Anime/manga art style illustration, non-photorealistic, stylized artwork.\n"
        "风格: 动漫/漫画艺术风格插图，非写实，风格化艺术作品。\n"
        "{scene_context}"
        "[END CONTEXT]\n\n"
        "Scene description / 场景描述:\n"
    )

    # 保留静态 CONTEXT_PREFIX 作为回退
    CONTEXT_PREFIX = (
        "[CONTENT CONTEXT / 内容说明]\n"
        "Purpose: Professional manga/comic illustration for a licensed novel-to-manga adaptation project.\n"
        "用途: 专业的漫画插图，用于正版小说改编漫画项目。\n"
        "Usage: This artwork is created for legitimate storytelling and publishing purposes in creative fiction.\n"
        "使用场景: 该作品用于合法的故事叙述和创意小说出版用途。\n"
        "Content Rating: General audience / All ages appropriate artistic content.\n"
        "内容分级: 面向普通观众/适合所有年龄段的艺术内容。\n"
        "Style: Anime/manga art style illustration, non-photorealistic, stylized artwork.\n"
        "风格: 动漫/漫画艺术风格插图，非写实，风格化艺术作品。\n"
        "[END CONTEXT]\n\n"
        "Scene description / 场景描述:\n"
    )

    def _detect_scene_type(self, prompt: str) -> str:
        """
        从提示词内容推断场景类型

        Args:
            prompt: 提示词内容

        Returns:
            场景类型字符串，如 "action", "romantic" 等
        """
        prompt_lower = prompt.lower()

        # 统计每种场景类型的匹配关键词数量
        scene_scores = {}
        for scene_type, keywords in self.SCENE_TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in prompt_lower)
            if score > 0:
                scene_scores[scene_type] = score

        if not scene_scores:
            return "daily"  # 默认为日常场景

        # 返回得分最高的场景类型
        return max(scene_scores, key=scene_scores.get)

    def _build_context_prefix(self, prompt: str) -> str:
        """
        根据提示词内容动态构建上下文前缀

        会分析提示词中的关键词，推断场景类型，
        然后生成针对该场景类型的上下文描述。

        Args:
            prompt: 提示词内容

        Returns:
            动态生成的上下文前缀
        """
        # 检测场景类型
        scene_type = self._detect_scene_type(prompt)

        # 获取场景特定的上下文描述
        scene_context = self.SCENE_CONTEXT_MAP.get(scene_type, "")

        # 构建完整的上下文前缀
        return self.BASE_CONTEXT_TEMPLATE.format(scene_context=scene_context)

    @asynccontextmanager
    async def create_http_client(
        self,
        config: ImageGenerationConfig,
        timeout: Optional[float] = None,
        for_test: bool = False,
    ) -> AsyncIterator[httpx.AsyncClient]:
        """
        创建配置好的HTTP客户端（工厂方法）

        统一管理超时设置、请求头等配置，避免重复代码。

        Args:
            config: 供应商配置
            timeout: 自定义超时时间（秒），None则使用默认值
            for_test: 是否用于连接测试（使用较短超时）

        Yields:
            配置好的 httpx.AsyncClient 实例

        Usage:
            async with self.create_http_client(config, for_test=True) as client:
                response = await client.get(url, headers=self.get_auth_headers(config))
        """
        if timeout is None:
            timeout = DEFAULT_TEST_TIMEOUT if for_test else DEFAULT_GENERATE_TIMEOUT

        # 代理配置：
        # - 默认使用系统代理（trust_env=True），保持与之前行为兼容
        # - 如果用户在 extra_params 中配置了 proxy，则使用用户指定的代理
        # - 如果用户设置 disable_proxy=True，则禁用代理
        extra_params = config.extra_params or {}
        proxy_url = extra_params.get("proxy")
        disable_proxy = extra_params.get("disable_proxy", False)

        async with httpx.AsyncClient(
            timeout=timeout,
            proxy=proxy_url,
            trust_env=not disable_proxy,  # 默认使用系统代理
        ) as client:
            yield client

    def get_auth_headers(
        self,
        config: ImageGenerationConfig,
        content_type: str = "application/json",
        accept: str = "application/json",
    ) -> Dict[str, str]:
        """
        获取认证请求头

        Args:
            config: 供应商配置
            content_type: Content-Type 头
            accept: Accept 头

        Returns:
            请求头字典
        """
        headers = {
            "Authorization": f"Bearer {config.api_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        if accept:
            headers["Accept"] = accept
        return headers

    @abstractmethod
    async def test_connection(self, config: ImageGenerationConfig) -> ProviderTestResult:
        """
        测试供应商连接

        Args:
            config: 供应商配置

        Returns:
            ProviderTestResult: 测试结果
        """
        pass

    @abstractmethod
    async def generate(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
    ) -> ProviderGenerateResult:
        """
        生成图片

        Args:
            config: 供应商配置
            request: 生成请求

        Returns:
            ProviderGenerateResult: 生成结果，包含图片URL列表
        """
        pass

    def get_supported_features(self) -> Dict[str, bool]:
        """
        获取供应商支持的特性

        Returns:
            特性支持映射，如 {"negative_prompt": True, "style": True}
        """
        return {
            "negative_prompt": True,
            "style": True,
            "quality": True,
            "resolution": True,
            "ratio": True,
            "img2img": False,  # 默认不支持 img2img
        }

    def supports_img2img(self) -> bool:
        """
        检查供应商是否支持 img2img

        Returns:
            是否支持 img2img 功能
        """
        return self.get_supported_features().get("img2img", False)

    async def generate_with_reference(
        self,
        config: ImageGenerationConfig,
        request: ImageGenerationRequest,
        reference_images: List["ReferenceImageInfo"],
    ) -> ProviderGenerateResult:
        """
        使用参考图生成图片（img2img）

        子类如果支持 img2img，应该重写此方法。
        默认实现降级为普通的 text-to-image。

        Args:
            config: 供应商配置
            request: 生成请求
            reference_images: 参考图列表

        Returns:
            ProviderGenerateResult: 生成结果
        """
        # 默认降级为普通生成
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "供应商 %s 不支持 img2img，降级为普通 text-to-image",
            self.PROVIDER_TYPE
        )
        return await self.generate(config, request)

    def build_prompt(self, request: ImageGenerationRequest, add_context: bool = True) -> str:
        """
        构建完整提示词

        智能检测：
        - 根据提示词内容动态生成场景感知的上下文前缀
        - 如果提示词已包含风格关键词（由LLM生成），则跳过风格后缀添加

        Args:
            request: 生成请求
            add_context: 是否添加上下文前缀

        Returns:
            构建后的提示词
        """
        from ..schemas import STYLE_SUFFIXES, RESOLUTION_SUFFIXES, ASPECT_RATIO_TO_SIZE, has_style_keywords

        # 动态生成场景感知的上下文前缀
        if add_context:
            context_prefix = self._build_context_prefix(request.prompt)
            prompt = context_prefix + request.prompt
        else:
            prompt = request.prompt

        # 智能检测：如果提示词已包含风格关键词，则跳过风格后缀添加
        # 使用集中定义的风格检测函数，确保检测逻辑与STYLE_SUFFIXES保持一致
        has_style = has_style_keywords(prompt)

        # 只有当提示词不包含风格关键词时，才添加风格后缀
        if not has_style and request.style:
            style_suffix = STYLE_SUFFIXES.get(request.style, "")
            if style_suffix:
                prompt = f"{prompt}, {style_suffix}"

        # 添加分辨率后缀
        if request.resolution:
            res_suffix = RESOLUTION_SUFFIXES.get(request.resolution, "")
            if res_suffix:
                prompt = f"{prompt}{res_suffix}"

        # 添加宽高比（强化描述）
        if request.ratio:
            # 获取像素尺寸以提供更具体的描述
            size = ASPECT_RATIO_TO_SIZE.get(request.ratio, (1024, 1024))
            width, height = size

            # 构建更强的宽高比约束描述
            if width > height * 2:
                # 超宽图（如3:1, 6:1）
                ratio_desc = f"IMPORTANT: extremely wide panoramic image, aspect ratio {request.ratio}, {width}x{height} pixels, horizontal letterbox format, ultrawide composition"
            elif height > width * 2:
                # 超高图（如1:3）
                ratio_desc = f"IMPORTANT: extremely tall vertical image, aspect ratio {request.ratio}, {width}x{height} pixels, vertical composition"
            elif width > height:
                # 横向图
                ratio_desc = f"IMPORTANT: wide horizontal image, aspect ratio {request.ratio}, {width}x{height} pixels, landscape orientation"
            elif height > width:
                # 竖向图
                ratio_desc = f"IMPORTANT: tall vertical image, aspect ratio {request.ratio}, {width}x{height} pixels, portrait orientation"
            else:
                # 正方形
                ratio_desc = f"IMPORTANT: square image, aspect ratio {request.ratio}, {width}x{height} pixels"

            prompt = f"{prompt}, {ratio_desc}"

        # 添加负面提示词
        if request.negative_prompt:
            prompt = f"{prompt}\n\nNegative: {request.negative_prompt}"

        return prompt
