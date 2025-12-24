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

    # 对话气泡类型到视觉描述的映射
    DIALOGUE_BUBBLE_MAP = {
        "normal": "speech bubble, character speaking, open mouth",
        "shout": "jagged speech bubble, shouting, wide open mouth, intense expression",
        "whisper": "dotted speech bubble, whispering, leaning close",
        "thought": "thought bubble, thoughtful expression, inner monologue",
        "narration": "narration box, caption text",
        "electronic": "wavy speech bubble, phone conversation",
    }

    # 音效到视觉效果的映射
    SOUND_EFFECT_VISUAL_MAP = {
        # 中文音效
        "砰": "explosion effect, impact burst",
        "嗖": "speed lines, motion blur",
        "咚": "impact vibration",
        "嘭": "explosion effect",
        "轰": "massive explosion, shockwave",
        "呼": "wind effect",
        # 日文音效
        "ドン": "explosion effect",
        "シュッ": "speed lines",
        "バン": "impact effect",
        "ゴゴゴ": "menacing aura effect",
        # 英文音效
        "BANG": "explosion effect",
        "WHOOSH": "speed lines, motion blur",
        "BOOM": "massive explosion",
        "CRASH": "destruction effect",
    }

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
        - 融合漫画画格元数据（对话、旁白、音效）

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

        # 融合漫画画格元数据（对话、旁白、音效）
        manga_visual_parts = self._build_manga_visual_elements(request)
        if manga_visual_parts:
            prompt = f"{prompt}, {manga_visual_parts}"

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

    # 构图描述映射
    COMPOSITION_MAP = {
        "wide shot": "wide shot, full scene view, establishing shot, characters shown in environment",
        "medium shot": "medium shot, waist-up view, conversational framing, character interaction focus",
        "medium close-up": "medium close-up, chest-up view, intimate framing, emotional connection",
        "close-up": "close-up shot, face focus, emotional emphasis, detailed expression",
        "extreme close-up": "extreme close-up, eye or detail focus, intense emotion, dramatic impact",
        "dynamic wide shot": "dynamic wide shot, action framing, motion blur, sweeping composition",
        "dynamic composition": "dynamic composition, diagonal lines, movement emphasis, energy",
    }

    # 镜头角度映射
    CAMERA_ANGLE_MAP = {
        "eye level": "eye level shot, neutral perspective, natural viewpoint",
        "low angle": "low angle shot, looking up, heroic perspective, powerful presence",
        "high angle": "high angle shot, looking down, vulnerable perspective, emphasizing smallness",
        "bird's eye": "bird's eye view, overhead shot, god's perspective, scene overview",
        "dutch angle": "dutch angle, tilted frame, tension and unease, dramatic instability",
        "dynamic": "dynamic angle, action perspective, dramatic viewpoint, cinematic",
        "dramatic": "dramatic angle, cinematic framing, high contrast, impactful composition",
    }

    # 语言到描述的映射
    LANGUAGE_CONSTRAINT_MAP = {
        "chinese": "Chinese text only (simplified/traditional Chinese characters), NO Japanese/Korean/English text",
        "japanese": "Japanese text only (hiragana, katakana, kanji), NO Chinese/Korean/English text",
        "english": "English text only, NO Chinese/Japanese/Korean text",
        "korean": "Korean text only (Hangul), NO Chinese/Japanese/English text",
    }

    def _build_manga_visual_elements(self, request: ImageGenerationRequest) -> str:
        """
        构建漫画视觉元素描述

        将对话、旁白、音效、构图、镜头角度等漫画元素转换为图片生成的视觉描述。
        包含实际内容，让AI理解场景的完整视觉信息。

        Args:
            request: 生成请求（包含漫画元数据）

        Returns:
            视觉元素描述字符串
        """
        parts = []

        # ==================== 0. 语言约束（最重要！）====================
        # 确保生成的文字/气泡使用正确的语言
        if request.dialogue_language:
            lang_constraint = self.LANGUAGE_CONSTRAINT_MAP.get(
                request.dialogue_language,
                f"{request.dialogue_language} text only"
            )
            parts.append(f"[LANGUAGE CONSTRAINT: {lang_constraint}]")

        # ==================== 1. 构图和镜头（最重要！）====================
        if request.composition:
            comp_desc = self.COMPOSITION_MAP.get(request.composition, request.composition)
            parts.append(comp_desc)

        if request.camera_angle:
            angle_desc = self.CAMERA_ANGLE_MAP.get(request.camera_angle, request.camera_angle)
            parts.append(angle_desc)

        # ==================== 2. 关键画格强调 ====================
        if request.is_key_panel:
            parts.append("key panel, dramatic emphasis, maximum detail, high visual impact, detailed rendering")

        # ==================== 3. 光线和氛围 ====================
        if request.lighting:
            parts.append(f"lighting: {request.lighting}")

        if request.atmosphere:
            parts.append(f"atmosphere: {request.atmosphere}")

        # ==================== 4. 关键视觉元素 ====================
        if request.key_visual_elements:
            elements = ", ".join(request.key_visual_elements[:5])  # 最多5个
            parts.append(f"featuring {elements}")

        # ==================== 5. 角色描述 ====================
        if request.characters:
            char_list = ", ".join(request.characters[:3])  # 最多3个角色
            parts.append(f"characters in scene: {char_list}")

        # ==================== 6. 对话视觉效果 + 实际内容 ====================
        if request.dialogue:
            dialogue_parts = []

            # 说话者
            speaker = request.dialogue_speaker or "character"

            # 气泡类型和说话动作
            bubble_type = request.dialogue_bubble_type or "normal"
            bubble_desc = self.DIALOGUE_BUBBLE_MAP.get(bubble_type, "speech bubble")

            # 根据气泡类型构建描述
            if bubble_type == "shout":
                dialogue_parts.append(f"{speaker} shouting loudly, wide open mouth, intense expression")
            elif bubble_type == "whisper":
                dialogue_parts.append(f"{speaker} whispering quietly, leaning close, subtle expression")
            elif bubble_type == "thought":
                dialogue_parts.append(f"{speaker} thinking deeply, thoughtful expression, contemplative pose")
            else:
                dialogue_parts.append(f"{speaker} speaking, open mouth, conversational expression")

            dialogue_parts.append(bubble_desc)

            # 气泡位置（影响构图）
            if request.dialogue_position:
                position_map = {
                    "top-right": "speech bubble at top right, leaving space for dialogue",
                    "top-left": "speech bubble at top left, leaving space for dialogue",
                    "top-center": "speech bubble at top center",
                    "bottom-right": "speech bubble at bottom right",
                    "bottom-left": "speech bubble at bottom left",
                    "bottom-center": "speech bubble at bottom center",
                }
                pos_desc = position_map.get(request.dialogue_position, "")
                if pos_desc:
                    dialogue_parts.append(pos_desc)

            # 添加对话内容描述（让AI理解角色在说什么，以便配合表情动作）
            dialogue_content = request.dialogue[:100] if len(request.dialogue) > 100 else request.dialogue
            dialogue_parts.append(f'dialogue content: "{dialogue_content}"')

            # 情绪效果
            if request.dialogue_emotion:
                emotion_lower = request.dialogue_emotion.lower()
                emotion_effects = {
                    "angry": "anger vein effect, furrowed brows, aggressive stance, intense glare",
                    "happy": "sparkle effect, bright smile, joyful expression, warm atmosphere",
                    "sad": "tear drop effect, melancholic expression, downcast eyes, somber mood",
                    "surprised": "shock lines effect, wide eyes, open mouth, dramatic reaction",
                    "scared": "sweat drops effect, fearful expression, trembling, tense posture",
                    "excited": "sparkle eyes effect, energetic pose, enthusiastic expression",
                    "shy": "blush lines effect, looking away, fidgeting, embarrassed expression",
                    "serious": "stern expression, focused gaze, determined look, intense atmosphere",
                    "confused": "question mark effect, tilted head, puzzled expression",
                    "determined": "focused eyes, firm jaw, confident stance, resolute expression",
                }
                for key, effect in emotion_effects.items():
                    if key in emotion_lower:
                        dialogue_parts.append(effect)
                        break

            parts.extend(dialogue_parts)

        # ==================== 7. 旁白视觉效果 + 实际内容 ====================
        if request.narration:
            narration_parts = []
            narration_parts.append("rectangular narration box, caption text overlay")

            # 旁白位置
            if request.narration_position:
                position_map = {
                    "top": "narration box at top of panel",
                    "bottom": "narration box at bottom of panel",
                    "left": "narration box on left side",
                    "right": "narration box on right side",
                }
                pos_desc = position_map.get(request.narration_position, "")
                if pos_desc:
                    narration_parts.append(pos_desc)

            # 添加旁白内容（影响场景氛围）
            narration_content = request.narration[:150] if len(request.narration) > 150 else request.narration
            narration_parts.append(f'narration text: "{narration_content}"')

            # 根据旁白内容推断并强化氛围
            narration_lower = request.narration.lower()
            if any(word in narration_lower for word in ["夜", "黑暗", "night", "dark", "shadow", "月", "moon"]):
                narration_parts.append("dark atmospheric lighting, nighttime ambiance, shadows")
            elif any(word in narration_lower for word in ["阳光", "明亮", "sunny", "bright", "light", "dawn", "晨"]):
                narration_parts.append("bright warm lighting, daylight, cheerful atmosphere")
            elif any(word in narration_lower for word in ["紧张", "危险", "tension", "danger", "threat", "危机"]):
                narration_parts.append("tense atmosphere, dramatic shadows, suspenseful mood")
            elif any(word in narration_lower for word in ["平静", "安宁", "peace", "calm", "quiet", "宁静"]):
                narration_parts.append("peaceful serene atmosphere, gentle lighting")
            elif any(word in narration_lower for word in ["悲伤", "痛苦", "sad", "sorrow", "grief", "tears"]):
                narration_parts.append("melancholic atmosphere, subdued lighting, emotional weight")
            elif any(word in narration_lower for word in ["快乐", "喜悦", "happy", "joy", "celebration"]):
                narration_parts.append("joyful atmosphere, vibrant lighting, celebratory mood")

            parts.extend(narration_parts)

        # ==================== 8. 音效视觉效果 + 实际文字 ====================
        if request.sound_effects or request.sound_effect_details:
            sfx_parts = []
            sfx_parts.append("manga sound effect text overlay, onomatopoeia")

            # 优先使用详细音效信息
            if request.sound_effect_details:
                for sfx_detail in request.sound_effect_details[:3]:
                    sfx_text = sfx_detail.get('text', '')
                    sfx_type = sfx_detail.get('type', '')
                    sfx_intensity = sfx_detail.get('intensity', 'medium')

                    # 根据类型添加视觉效果
                    type_effects = {
                        "action": "speed lines, motion blur, dynamic effect",
                        "impact": "impact lines, radial burst, shockwave effect",
                        "ambient": "ambient particles, environmental effect",
                        "emotional": "emotion symbols, heart or sweat effects",
                        "vocal": "vocal expression marks",
                    }
                    if sfx_type and sfx_type in type_effects:
                        sfx_parts.append(type_effects[sfx_type])

                    # 根据强度调整
                    intensity_effects = {
                        "small": "subtle effect, small text",
                        "medium": "moderate effect, medium emphasis",
                        "large": "dramatic effect, large bold text, screen-filling",
                    }
                    if sfx_intensity in intensity_effects:
                        sfx_parts.append(intensity_effects[sfx_intensity])

                    # 添加实际音效文字
                    if sfx_text:
                        visual = self.SOUND_EFFECT_VISUAL_MAP.get(sfx_text)
                        if visual:
                            sfx_parts.append(visual)
                        sfx_parts.append(f'sound effect text "{sfx_text}"')

            elif request.sound_effects:
                # 使用简单音效列表
                for sfx in request.sound_effects[:3]:
                    visual = self.SOUND_EFFECT_VISUAL_MAP.get(sfx)
                    if visual:
                        sfx_parts.append(visual)
                    sfx_parts.append(f'sound effect text "{sfx}"')

            # 去重
            unique_sfx = list(dict.fromkeys(sfx_parts))
            parts.extend(unique_sfx)

        return ", ".join(parts) if parts else ""
