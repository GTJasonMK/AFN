"""
整页提示词生成器

使用LLM将分镜设计转换为高质量的整页漫画图像生成提示词。
"""

import logging
from typing import Dict, List, Optional

from app.services.llm_service import LLMService
from app.services.prompt_service import PromptService
from app.utils.json_utils import parse_llm_json_safe

from ..storyboard import PageStoryboard, StoryboardResult
from ..extraction import ChapterInfo
from .models import PagePrompt
from .builder import build_layout_template, build_panel_summaries

logger = logging.getLogger(__name__)

# 镜头类型映射（中文）
SHOT_TYPE_CHINESE = {
    "long": "远景，全身，建立镜头",
    "medium": "中景，上半身",
    "close_up": "特写，面部聚焦",
    "extreme_close_up": "超特写，局部放大",
}

# 默认负面提示词（中文，自然语言描述）
DEFAULT_NEGATIVE_PROMPT = (
    "禁止出现以下内容：模糊低质量的图像、变形扭曲的人体、多余的手指或肢体、"
    "真实照片风格、3D渲染效果、任何水印或签名、"
    "画格之间出现黑色或深色间隙、"
    "页码页眉页脚等页面标记、版权文字或作者签名、"
    "图像边缘有边框或留白、"
    "内容被裁剪或截断不完整、对话气泡被切断、文字模糊难以辨认、"
    "任何平台Logo或水印"
)


class PagePromptGenerator:
    """
    整页提示词生成器

    使用LLM智能生成整页漫画的图像提示词，比规则拼接更加自然和有效。
    """

    def __init__(
        self,
        llm_service: LLMService,
        prompt_service: Optional[PromptService] = None,
        style: str = "manga",
        character_profiles: Optional[Dict[str, str]] = None,
        character_portraits: Optional[Dict[str, str]] = None,
    ):
        """
        初始化生成器

        Args:
            llm_service: LLM服务
            prompt_service: 提示词服务（用于加载模板）
            style: 漫画风格
            character_profiles: 角色外观描述
            character_portraits: 角色立绘路径
        """
        self.llm_service = llm_service
        self.prompt_service = prompt_service
        self.style = style
        self.character_profiles = character_profiles or {}
        self.character_portraits = character_portraits or {}

    async def generate_page_prompts(
        self,
        storyboard: StoryboardResult,
        chapter_info: ChapterInfo,
        user_id: Optional[int] = None,
        max_concurrency: int = 5,
        on_page_complete: Optional[callable] = None,
        completed_prompts: Optional[List[PagePrompt]] = None,
        on_prompt_generated: Optional[callable] = None,
    ) -> List[PagePrompt]:
        """
        为所有页面并发生成整页提示词（支持断点恢复）

        Args:
            storyboard: 分镜设计结果
            chapter_info: 章节信息
            user_id: 用户ID
            max_concurrency: 最大并发数（默认5，避免API限流）
            on_page_complete: 每页完成后的回调函数，签名: async (page_number, completed_count, total) -> None
            completed_prompts: 已完成的页面提示词列表（用于断点恢复）
            on_prompt_generated: 每页提示词生成完成后的回调，签名: async (page_number, page_prompt) -> None
                用于实时保存已生成的提示词到断点数据

        Returns:
            List[PagePrompt]: 所有页面的整页提示词（按页码排序）
        """
        import asyncio

        total = len(storyboard.pages)

        # 处理已完成的页面
        completed_page_numbers = set()
        completed_prompts_dict: Dict[int, PagePrompt] = {}
        if completed_prompts:
            for prompt in completed_prompts:
                completed_page_numbers.add(prompt.page_number)
                completed_prompts_dict[prompt.page_number] = prompt
            logger.info(f"从断点恢复 {len(completed_prompts)} 页已生成的整页提示词")

        # 筛选需要生成的页面
        pages_to_generate = [
            page for page in storyboard.pages
            if page.page_number not in completed_page_numbers
        ]

        if not pages_to_generate:
            logger.info("所有页面的整页提示词已从断点恢复，无需重新生成")
            # 按页码排序返回
            return [completed_prompts_dict[i] for i in sorted(completed_prompts_dict.keys())]

        logger.info(f"开始并发生成 {len(pages_to_generate)}/{total} 页整页提示词 (并发数: {max_concurrency})")

        # 预先获取LLM配置，避免并发任务同时访问数据库session
        cached_config = None
        try:
            cached_config = await self.llm_service.resolve_llm_config_cached(user_id)
            logger.debug("LLM配置预获取成功")
        except Exception as e:
            logger.warning(f"LLM配置预获取失败，将在每次调用时重新获取: {e}")

        # 使用信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrency)
        # 完成计数器和回调锁
        # 初始计数包括已完成的页面
        completed_count = len(completed_page_numbers)
        callback_lock = asyncio.Lock()

        async def generate_with_semaphore(page):
            nonlocal completed_count
            async with semaphore:
                # LLM调用失败时直接抛出异常，不使用回退方案
                page_prompt = await self.generate_single_page_prompt(
                    page=page,
                    chapter_info=chapter_info,
                    user_id=user_id,
                    cached_config=cached_config,
                )
                logger.debug(f"第 {page.page_number} 页整页提示词LLM生成成功")
                result = (page.page_number, page_prompt, None)

            # 使用锁序列化回调调用，避免并发访问数据库session
            async with callback_lock:
                completed_count += 1
                logger.debug(f"整页提示词生成进度: {completed_count}/{total}")

                # 实时保存已生成的提示词（用于断点恢复）
                if on_prompt_generated:
                    try:
                        await on_prompt_generated(result[0], result[1])
                    except Exception as save_error:
                        logger.warning(f"保存提示词回调执行失败: {save_error}")

                # 实时调用进度回调
                if on_page_complete:
                    try:
                        await on_page_complete(page.page_number, completed_count, total)
                    except Exception as cb_error:
                        logger.warning(f"进度回调执行失败: {cb_error}")

            return result

        # 只对需要生成的页面并发执行
        tasks = [generate_with_semaphore(page) for page in pages_to_generate]
        results = await asyncio.gather(*tasks)

        # 合并已完成的和新生成的结果
        all_prompts_dict = dict(completed_prompts_dict)  # 从已完成的开始

        for page_number, page_prompt, error in results:
            all_prompts_dict[page_number] = page_prompt

        # 按页码排序返回
        page_prompts = [all_prompts_dict[i] for i in sorted(all_prompts_dict.keys())]

        # 汇总日志
        restored_count = len(completed_page_numbers)
        new_count = len(pages_to_generate)
        logger.info(
            f"整页提示词生成完成: 共 {total} 页, 恢复 {restored_count} 页, "
            f"新生成 {new_count} 页"
        )

        return page_prompts

    async def generate_single_page_prompt(
        self,
        page: PageStoryboard,
        chapter_info: ChapterInfo,
        user_id: Optional[int] = None,
        cached_config: Optional[Dict] = None,
    ) -> PagePrompt:
        """
        为单个页面生成整页提示词

        Args:
            page: 页面分镜设计
            chapter_info: 章节信息
            user_id: 用户ID
            cached_config: 预先获取的LLM配置（避免并发时访问数据库）

        Returns:
            PagePrompt: 整页提示词
        """
        page_num = page.page_number
        logger.debug(f"[页{page_num}] 开始生成整页提示词...")

        # 1. 准备输入数据
        panels_detail = self._format_panels_detail(page, chapter_info)
        character_profiles_text = self._format_character_profiles(page, chapter_info)
        logger.debug(f"[页{page_num}] 输入数据准备完成, 画格数: {len(page.panels)}")

        # 2. 加载提示词模板
        system_prompt = await self._load_system_prompt()
        if not system_prompt:
            raise ValueError("无法加载系统提示词模板")
        logger.debug(f"[页{page_num}] 系统提示词加载完成, 长度: {len(system_prompt)}")

        # 3. 构建用户提示词
        user_prompt = self._build_user_prompt(
            page_number=page.page_number,
            style=self.style,
            row_count=self._count_rows(page),
            panels_detail=panels_detail,
            character_profiles=character_profiles_text,
        )
        logger.debug(f"[页{page_num}] 用户提示词构建完成, 长度: {len(user_prompt)}")

        # 4. 调用LLM
        logger.debug(f"[页{page_num}] 正在调用LLM生成整页提示词...")
        try:
            # 构建对话历史
            conversation_history = [
                {"role": "user", "content": user_prompt}
            ]
            response = await self.llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_id=user_id,
                response_format="json_object",
                cached_config=cached_config,
            )
        except Exception as llm_error:
            logger.error(f"[页{page_num}] LLM调用失败: {type(llm_error).__name__}: {llm_error}")
            raise

        if not response:
            raise ValueError("LLM返回空响应")
        logger.debug(f"[页{page_num}] LLM响应长度: {len(response)}")

        # 5. 解析响应
        result = parse_llm_json_safe(response)
        if not result:
            logger.error(f"[页{page_num}] JSON解析失败, 原始响应前500字符: {response[:500]}")
            raise ValueError("LLM响应JSON解析失败")
        logger.debug(f"[页{page_num}] JSON解析成功, 字段: {list(result.keys())}")

        # 6. 构建PagePrompt对象
        page_prompt = self._build_page_prompt_from_llm_result(page, chapter_info, result)
        logger.debug(f"[页{page_num}] PagePrompt构建完成")

        return page_prompt

    def _format_panels_detail(
        self,
        page: PageStoryboard,
        chapter_info: ChapterInfo,
    ) -> str:
        """格式化画格详情供LLM理解"""
        lines = []

        for i, panel in enumerate(page.panels, 1):
            lines.append(f"### 画格 {i}")
            lines.append(f"- 位置：第 {panel.row_id} 行")
            lines.append(f"- 宽度比例：{panel.width_ratio.value}")
            lines.append(f"- 宽高比：{panel.aspect_ratio.value}")

            if panel.row_span > 1:
                lines.append(f"- 跨行：{panel.row_span} 行")

            # 镜头类型
            shot_map = {"long": "远景", "medium": "中景", "close_up": "特写"}
            lines.append(f"- 镜头：{shot_map.get(panel.shot_type.value, '中景')}")

            # 画面描述
            if panel.visual_description:
                lines.append(f"- 画面描述：{panel.visual_description}")

            # 角色
            if panel.characters:
                lines.append(f"- 角色：{', '.join(panel.characters)}")

            # 角色动作
            if panel.character_actions:
                actions = [f"{k}{v}" for k, v in panel.character_actions.items() if v]
                if actions:
                    lines.append(f"- 动作：{', '.join(actions)}")

            # 角色表情
            if panel.character_expressions:
                exprs = [f"{k}{v}表情" for k, v in panel.character_expressions.items() if v]
                if exprs:
                    lines.append(f"- 表情：{', '.join(exprs)}")

            # 背景
            if panel.background:
                lines.append(f"- 背景：{panel.background}")

            # 氛围
            if panel.atmosphere:
                lines.append(f"- 氛围：{panel.atmosphere}")

            # 光线
            if panel.lighting:
                lines.append(f"- 光线：{panel.lighting}")

            # 对话和想法 - 区分气泡类型
            if panel.dialogues:
                # 分类收集
                thoughts = []
                dialogues = []
                shouts = []
                whispers = []

                for d in panel.dialogues:
                    speaker = d.speaker if d.speaker else "角色"
                    if d.is_internal or d.bubble_type == "thought":
                        thoughts.append(f"  - {speaker}(想法): ({d.content})")
                    elif d.bubble_type == "shout":
                        shouts.append(f"  - {speaker}(喊叫): \"{d.content}\"")
                    elif d.bubble_type == "whisper":
                        whispers.append(f"  - {speaker}(低语): \"{d.content}\"")
                    else:
                        dialogues.append(f"  - {speaker}: \"{d.content}\"")

                if thoughts:
                    lines.append("- 想法气泡(云朵状)：")
                    lines.extend(thoughts)
                if dialogues:
                    lines.append("- 对话气泡：")
                    lines.extend(dialogues)
                if shouts:
                    lines.append("- 喊叫气泡(锯齿状)：")
                    lines.extend(shouts)
                if whispers:
                    lines.append("- 低语气泡(虚线)：")
                    lines.extend(whispers)

            lines.append("")

        return "\n".join(lines)

    def _format_character_profiles(
        self,
        page: PageStoryboard,
        chapter_info: ChapterInfo,
    ) -> str:
        """格式化角色外观描述"""
        # 收集页面中出现的所有角色
        all_characters = set()
        for panel in page.panels:
            all_characters.update(panel.characters)

        if not all_characters:
            return "无特定角色"

        lines = []
        for char_name in all_characters:
            # 优先从chapter_info获取
            char_info = chapter_info.characters.get(char_name)
            if char_info and char_info.appearance:
                lines.append(f"- {char_name}: {char_info.appearance}")
            elif char_name in self.character_profiles:
                lines.append(f"- {char_name}: {self.character_profiles[char_name]}")
            else:
                lines.append(f"- {char_name}: (未知外观)")

        return "\n".join(lines)

    def _count_rows(self, page: PageStoryboard) -> int:
        """计算页面行数"""
        if not page.panels:
            return 0
        row_ids = set(p.row_id for p in page.panels)
        return len(row_ids)

    async def _load_system_prompt(self) -> str:
        """加载系统提示词"""
        if not self.prompt_service:
            raise ValueError("PromptService未配置，无法加载系统提示词")

        prompt = await self.prompt_service.get_prompt(
            "manga_page_prompt_generation"
        )
        if not prompt:
            raise ValueError("系统提示词模板 'manga_page_prompt_generation' 不存在")
        return prompt

    def _build_user_prompt(
        self,
        page_number: int,
        style: str,
        row_count: int,
        panels_detail: str,
        character_profiles: str,
    ) -> str:
        """构建用户提示词"""
        style_cn = {
            "manga": "日式漫画",
            "anime": "动漫风格",
            "comic": "美式漫画",
            "webtoon": "条漫风格",
        }

        return f"""请为以下漫画页面生成整页图像提示词：

## 页面基本信息
- 页码：第 {page_number} 页
- 风格：{style_cn.get(style, style)}
- 布局：{row_count} 行结构

## 画格详情
{panels_detail}

## 角色外观
{character_profiles}

请生成一个完整的整页漫画图像提示词，用于让AI绘图模型生成带分格布局的整页漫画。"""

    def _build_page_prompt_from_llm_result(
        self,
        page: PageStoryboard,
        chapter_info: ChapterInfo,
        llm_result: dict,
    ) -> PagePrompt:
        """从LLM结果构建PagePrompt对象"""
        # 提取LLM生成的提示词
        full_page_prompt = llm_result.get("full_page_prompt", "")

        # 如果LLM没有生成有效提示词，直接报错
        if not full_page_prompt:
            raise ValueError(f"LLM未生成有效的整页提示词，返回内容: {llm_result}")

        # 构建布局模板名称
        layout_template = build_layout_template(page.panels)

        # 获取所有角色的立绘路径
        all_characters = set()
        for panel in page.panels:
            all_characters.update(panel.characters)
        reference_paths = self._get_reference_paths(list(all_characters))

        # 构建panel简要信息
        panel_summaries = build_panel_summaries(page.panels)

        return PagePrompt(
            page_number=page.page_number,
            layout_template=layout_template,
            layout_description=page.layout_description or "",
            panel_summaries=panel_summaries,
            full_page_prompt=full_page_prompt,
            negative_prompt=DEFAULT_NEGATIVE_PROMPT,
            aspect_ratio="3:4",
            panels=[],  # 画格级提示词由PromptBuilder单独生成
            reference_image_paths=reference_paths,
        )

    def _get_reference_paths(self, characters: List[str]) -> Optional[List[str]]:
        """获取角色立绘路径"""
        if not characters or not self.character_portraits:
            return None

        paths = []
        for char in characters:
            if char in self.character_portraits:
                paths.append(self.character_portraits[char])

        return paths if paths else None


__all__ = ["PagePromptGenerator"]
