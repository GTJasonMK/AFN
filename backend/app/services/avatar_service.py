"""
小说头像生成服务

负责使用LLM生成小说的SVG动物头像。
"""

import logging
import re
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.blueprint_repository import NovelBlueprintRepository, BlueprintCharacterRepository
from ..services.llm_service import LLMService
from ..services.llm_wrappers import call_llm_json, LLMProfile
from ..services.prompt_service import PromptService
from ..utils.json_utils import parse_llm_json_or_fail
from ..exceptions import ResourceNotFoundError, InvalidParameterError
from ..core.constants import AvatarConstants

logger = logging.getLogger(__name__)


class AvatarService:
    """
    小说头像生成服务

    使用LLM根据小说的类型、风格、氛围生成匹配的小动物SVG头像。
    """

    # SVG安全检查的危险标签和属性
    # 注意: style标签在SVG内是安全的（仅影响SVG内部样式），不列入危险标签
    DANGEROUS_TAGS = ['script', 'iframe', 'object', 'embed', 'link']
    DANGEROUS_ATTRS = ['onclick', 'onerror', 'onload', 'onmouseover', 'onfocus', 'onblur']

    def __init__(
        self,
        session: AsyncSession,
        llm_service: Optional[LLMService] = None,
        prompt_service: Optional[PromptService] = None,
    ):
        """
        初始化AvatarService

        Args:
            session: 数据库会话
            llm_service: LLM服务（可选，未提供则内部创建）
            prompt_service: 提示词服务（可选，未提供则内部创建）
        """
        self.session = session
        self.blueprint_repo = NovelBlueprintRepository(session)
        self.character_repo = BlueprintCharacterRepository(session)
        self.llm_service = llm_service or LLMService(session)
        self.prompt_service = prompt_service or PromptService(session)

    async def generate_avatar(
        self,
        project_id: str,
        user_id: int,
    ) -> dict:
        """
        为小说生成SVG头像

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            dict: {
                "avatar_svg": "<svg>...</svg>",
                "animal": "fox",
                "animal_cn": "狐狸"
            }

        Raises:
            ResourceNotFoundError: 蓝图不存在
            InvalidParameterError: SVG验证失败
        """
        # 1. 获取蓝图信息
        blueprint = await self.blueprint_repo.get_by_project_id(project_id)
        if not blueprint:
            raise ResourceNotFoundError("蓝图", project_id)

        # 2. 获取角色信息
        characters = await self.character_repo.list_by_project(project_id)

        # 3. 构建提示词
        system_prompt = await self.prompt_service.get_prompt("avatar_generation")
        user_prompt = self._build_user_prompt(blueprint, list(characters))

        # 4. 调用LLM生成
        logger.info("项目 %s 开始生成头像", project_id)
        response = await call_llm_json(
            self.llm_service,
            LLMProfile.CREATIVE,
            system_prompt=system_prompt,
            user_content=user_prompt,
            user_id=user_id,
        )

        # 5. 解析响应
        result = parse_llm_json_or_fail(response, "头像生成失败")

        svg = result.get("svg", "")
        animal = result.get("animal", "")
        animal_cn = result.get("animal_cn", "")

        # 6. 验证并清理SVG
        svg = self._validate_and_sanitize_svg(svg)

        # 7. 保存到数据库
        await self._save_avatar(project_id, svg, animal)
        await self.session.commit()

        logger.info(
            "项目 %s 头像生成成功: %s (%s)",
            project_id,
            animal_cn,
            animal,
        )

        return {
            "avatar_svg": svg,
            "animal": animal,
            "animal_cn": animal_cn,
        }

    def _build_user_prompt(self, blueprint, characters: list) -> str:
        """
        构建用户提示词

        Args:
            blueprint: 蓝图数据库对象
            characters: 角色列表（BlueprintCharacter对象列表）

        Returns:
            str: 格式化的用户提示词
        """
        title = blueprint.title or "未命名小说"
        genre = blueprint.genre or "未知类型"
        style = blueprint.style or "未知风格"
        tone = blueprint.tone or "未知氛围"
        target_audience = blueprint.target_audience or "一般读者"
        one_sentence_summary = blueprint.one_sentence_summary or "暂无简介"

        # 从角色列表获取主角信息
        protagonist_info = ""
        if characters and len(characters) > 0:
            main_char = characters[0]
            char_name = main_char.name or "未知"
            char_personality = main_char.personality or ""
            char_identity = main_char.identity or ""
            protagonist_info = f"""
## 主角信息
- 名字：{char_name}
- 身份：{char_identity}
- 性格：{char_personality}
"""

        # 获取世界观核心设定
        world_info = ""
        if blueprint.world_setting:
            try:
                world = blueprint.world_setting if isinstance(blueprint.world_setting, dict) else {}
                core_rules = world.get('core_rules', '')
                if core_rules:
                    # 截取前N字符，避免过长
                    preview_len = AvatarConstants.WORLD_RULES_PREVIEW_LENGTH
                    core_rules_preview = core_rules[:preview_len] + "..." if len(core_rules) > preview_len else core_rules
                    world_info = f"""
## 世界观
{core_rules_preview}
"""
            except (TypeError, AttributeError):
                pass

        return f"""请为以下小说创作一个独特的动物图腾头像：

## 作品信息
- **标题**：{title}
- **类型**：{genre}
- **风格**：{style}
- **氛围**：{tone}
- **目标读者**：{target_audience}

## 故事简介
{one_sentence_summary}
{protagonist_info}{world_info}
## 创作要求

1. 根据作品的整体气质，选择最能代表这部小说灵魂的动物
2. 设计风格要与小说类型和氛围高度匹配
3. 配色方案要能传达故事的情感基调
4. 如果有主角信息，可以让头像体现主角的某些特质
5. 追求简洁而有辨识度，让人一眼就能感受到作品的独特魅力

请发挥你的创意，创作一个让人过目不忘的头像！
"""

    def _validate_and_sanitize_svg(self, svg: str) -> str:
        """
        验证并清理SVG代码，防止XSS攻击

        Args:
            svg: 原始SVG代码

        Returns:
            str: 清理后的安全SVG代码

        Raises:
            InvalidParameterError: SVG格式无效或包含危险内容
        """
        if not svg or not isinstance(svg, str):
            raise InvalidParameterError("SVG内容为空", "svg")

        svg = svg.strip()

        # 检查基本格式
        if not svg.startswith("<svg") or not svg.endswith("</svg>"):
            raise InvalidParameterError("SVG格式无效：必须以<svg>开头，</svg>结尾", "svg")

        # 检查危险标签
        svg_lower = svg.lower()
        for tag in self.DANGEROUS_TAGS:
            if f"<{tag}" in svg_lower or f"</{tag}" in svg_lower:
                raise InvalidParameterError(f"SVG包含危险标签: {tag}", "svg")

        # 检查危险属性
        for attr in self.DANGEROUS_ATTRS:
            if attr in svg_lower:
                raise InvalidParameterError(f"SVG包含危险属性: {attr}", "svg")

        # 检查外部资源链接
        if "http://" in svg_lower or "https://" in svg_lower:
            # 允许 xmlns 中的命名空间URL
            if re.search(r'(?<!xmlns=")https?://', svg_lower):
                raise InvalidParameterError("SVG包含外部资源链接", "svg")

        # 确保有正确的xmlns
        if 'xmlns="http://www.w3.org/2000/svg"' not in svg:
            # 尝试添加xmlns
            svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)

        # 限制SVG大小（防止过大的SVG）
        max_size = AvatarConstants.SVG_MAX_SIZE_BYTES
        if len(svg) > max_size:
            raise InvalidParameterError(f"SVG大小超过限制（{len(svg)} > {max_size}字节）", "svg")

        return svg

    async def _save_avatar(
        self,
        project_id: str,
        svg: str,
        animal: str,
    ) -> None:
        """
        保存头像到数据库

        Args:
            project_id: 项目ID
            svg: SVG代码
            animal: 动物类型
        """
        blueprint = await self.blueprint_repo.get_by_project_id(project_id)
        if blueprint:
            blueprint.avatar_svg = svg
            blueprint.avatar_animal = animal
            await self.session.flush()

    async def get_avatar(self, project_id: str) -> Optional[dict]:
        """
        获取项目的头像信息

        Args:
            project_id: 项目ID

        Returns:
            Optional[dict]: 头像信息，如果不存在则返回None
        """
        blueprint = await self.blueprint_repo.get_by_project_id(project_id)
        if not blueprint or not blueprint.avatar_svg:
            return None

        return {
            "avatar_svg": blueprint.avatar_svg,
            "animal": blueprint.avatar_animal,
        }

    async def delete_avatar(self, project_id: str) -> bool:
        """
        删除项目的头像

        Args:
            project_id: 项目ID

        Returns:
            bool: 是否成功删除
        """
        blueprint = await self.blueprint_repo.get_by_project_id(project_id)
        if not blueprint:
            return False

        blueprint.avatar_svg = None
        blueprint.avatar_animal = None
        await self.session.flush()

        logger.info("项目 %s 头像已删除", project_id)
        return True
