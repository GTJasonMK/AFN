"""
Prompt构建服务

专门负责构建各种LLM提示词，保持提示词逻辑的集中管理和可维护性。
"""

import json
from typing import Dict, List, Optional

from ..models.novel import NovelProject
from ..models.part_outline import PartOutline
from ..repositories.part_outline_repository import PartOutlineRepository


class PromptBuilder:
    """
    提示词构建服务

    负责构建各种场景下的LLM提示词，包括：
    - 部分大纲生成
    - 章节大纲生成
    - 章节内容生成等
    """

    def __init__(self, part_outline_repo: Optional[PartOutlineRepository] = None):
        """
        初始化PromptBuilder

        Args:
            part_outline_repo: 部分大纲Repository，用于查询上下文信息
        """
        self.part_outline_repo = part_outline_repo

    def build_part_outline_prompt(
        self,
        total_chapters: int,
        chapters_per_part: int,
        total_parts: int,
        world_setting: Dict,
        characters: List[Dict],
        full_synopsis: str,
        current_part_number: int = 1,
        previous_parts: Optional[List[PartOutline]] = None,
        optimization_prompt: Optional[str] = None,
    ) -> str:
        """
        构建生成部分大纲的提示词（支持串行生成）

        Args:
            total_chapters: 总章节数
            chapters_per_part: 每部分的章节数
            total_parts: 总部分数
            world_setting: 世界观设定
            characters: 角色列表
            full_synopsis: 完整剧情简介
            current_part_number: 当前要生成的部分编号（串行模式）
            previous_parts: 前面已生成的部分列表（串行模式）
            optimization_prompt: 优化方向提示（可选）

        Returns:
            str: 构建好的提示词
        """
        base_prompt = f"""请基于以下信息，为这部长篇小说生成第 {current_part_number} 部分的大纲。

## 小说基本信息

总章节数：{total_chapters}
每个部分的章节数：约 {chapters_per_part} 章
总共分为 {total_parts} 个部分
当前生成：第 {current_part_number} 部分

## 世界观设定

{json.dumps(world_setting, ensure_ascii=False, indent=2)}

## 角色档案

{json.dumps(characters, ensure_ascii=False, indent=2)}

## 主要剧情

{full_synopsis}"""

        # 如果有前面已生成的部分，展示出来确保连贯性
        if previous_parts and len(previous_parts) > 0:
            base_prompt += "\n\n## 已生成的部分大纲\n\n"
            base_prompt += "请仔细参考以下已生成的部分，确保第 {0} 部分与前文保持连贯、承接自然、设定一致。\n\n".format(current_part_number)

            for part in previous_parts:
                base_prompt += f"""### 第 {part.part_number} 部分：{part.title}

- 章节范围：第 {part.start_chapter}-{part.end_chapter} 章
- 主题：{part.theme or ""}
- 摘要：{part.summary or ""}
- 关键事件：{json.dumps(part.key_events or [], ensure_ascii=False)}
- 角色发展：{json.dumps(part.character_arcs or {}, ensure_ascii=False)}
- 主要冲突：{json.dumps(part.conflicts or [], ensure_ascii=False)}
- 结尾钩子：{part.ending_hook or ""}

"""

        # 如果有优化提示词，添加到提示中
        if optimization_prompt:
            base_prompt += f"""

## 优化方向

用户要求：{optimization_prompt}

请在生成部分大纲时，特别注意用户的优化方向，确保生成的内容符合这些要求。"""

        base_prompt += f"""

## 输出要求

请生成第 {current_part_number} 部分的大纲，应包含：
- part_number: 部分编号（当前为 {current_part_number}）
- title: 部分标题
- start_chapter: 起始章节号
- end_chapter: 结束章节号
- summary: 该部分的剧情摘要（200-300字）
- theme: 该部分的核心主题
- key_events: 关键事件列表（3-5个）
- character_arcs: 角色成长弧线（字典格式，key为角色名，value为成长描述）
- conflicts: 主要冲突列表（2-3个）
- ending_hook: 部分结尾的悬念/钩子

确保：
1. 章节范围与前面部分连续不重叠（第{current_part_number}部分应从第{(current_part_number-1) * chapters_per_part + 1}章开始）
2. 与前面部分有清晰的承接关系（特别是前一部分的ending_hook）
3. 角色发展符合前面部分已建立的设定（不能出现能力倒退、性格突变等矛盾）
4. 世界观规则保持一致（不能违背前面部分已确立的规则）
5. 剧情线索自然延续（呼应前面部分的伏笔）
6. 该部分有独立的小高潮和节奏起伏

输出JSON格式（只返回单个部分）：
{{
  "part_number": {current_part_number},
  "title": "...",
  "start_chapter": ...,
  "end_chapter": ...,
  "summary": "...",
  "theme": "...",
  "key_events": ["...", "..."],
  "character_arcs": {{"角色名": "成长描述", ...}},
  "conflicts": ["...", "..."],
  "ending_hook": "..."
}}
"""

        return base_prompt

    async def build_part_chapters_prompt(
        self,
        part_outline: PartOutline,
        project: NovelProject,
        start_chapter: Optional[int] = None,
        num_chapters: Optional[int] = None,
        previous_chapters: Optional[List] = None,
        relevant_summaries: Optional[List[Dict]] = None,
    ) -> str:
        """
        构建生成单个部分章节大纲的提示词（异步方法，支持串行生成）

        此方法需要查询上下文信息（前后部分），因此是异步的。

        Args:
            part_outline: 部分大纲对象
            project: 项目对象
            start_chapter: 起始章节号（串行模式，默认从part_outline.start_chapter开始）
            num_chapters: 要生成的章节数（串行模式，默认生成该部分的全部章节）
            previous_chapters: 前面已生成的章节大纲列表（串行模式）
            relevant_summaries: RAG检索到的相关已完成章节摘要列表

        Returns:
            str: 构建好的提示词

        Raises:
            RuntimeError: 如果未提供part_outline_repo
        """
        if not self.part_outline_repo:
            raise RuntimeError("build_part_chapters_prompt 需要 part_outline_repo")

        # 确定要生成的章节范围
        actual_start = start_chapter if start_chapter is not None else part_outline.start_chapter
        actual_num = num_chapters if num_chapters is not None else (part_outline.end_chapter - part_outline.start_chapter + 1)
        actual_end = actual_start + actual_num - 1

        # 获取上一部分的ending_hook
        prev_part = None
        if part_outline.part_number > 1:
            prev_part_outline = await self.part_outline_repo.get_by_part_number(
                project.id, part_outline.part_number - 1
            )
            if prev_part_outline:
                prev_part = prev_part_outline.ending_hook

        # 获取下一部分的summary
        next_part = None
        next_part_outline = await self.part_outline_repo.get_by_part_number(
            project.id, part_outline.part_number + 1
        )
        if next_part_outline:
            next_part = next_part_outline.summary

        world_setting = project.blueprint.world_setting or {}

        # 转换角色列表
        characters = [
            {
                "name": char.name,
                "identity": char.identity or "",
                "personality": char.personality or "",
                "goals": char.goals or "",
            }
            for char in sorted(project.characters, key=lambda c: c.position)
        ]

        prompt = f"""请基于以下信息，为这部小说的第 {part_outline.part_number} 部分生成详细的章节大纲。

## 部分信息

标题：{part_outline.title}
该部分章节范围：第 {part_outline.start_chapter} 章 - 第 {part_outline.end_chapter} 章
主题：{part_outline.theme or ""}

### 部分摘要
{part_outline.summary or ""}

### 关键事件
{json.dumps(part_outline.key_events or [], ensure_ascii=False, indent=2)}

### 主要冲突
{json.dumps(part_outline.conflicts or [], ensure_ascii=False, indent=2)}

### 角色成长弧线
{json.dumps(part_outline.character_arcs or {}, ensure_ascii=False, indent=2)}

### 结尾钩子
{part_outline.ending_hook or "（无）"}

"""

        # 如果有前面已生成的章节，展示出来确保连贯性
        if previous_chapters and len(previous_chapters) > 0:
            prompt += "\n## 前文章节大纲\n\n"
            prompt += f"请仔细参考以下已生成的章节大纲，确保第 {actual_start}-{actual_end} 章与前文保持连贯、承接自然、设定一致。\n\n"

            # 显示最近的10章详情，其余简略显示
            recent_chapters = previous_chapters[-10:] if len(previous_chapters) > 10 else previous_chapters

            if len(previous_chapters) > 10:
                prompt += f"（前 {len(previous_chapters) - 10} 章已生成，以下展示最近10章详情）\n\n"

            for ch in recent_chapters:
                prompt += f"### 第 {ch.get('chapter_number', '?')} 章：{ch.get('title', '未命名')}\n"
                prompt += f"摘要：{ch.get('summary', '')}\n\n"

        # 如果有RAG检索到的相关摘要，展示出来
        if relevant_summaries and len(relevant_summaries) > 0:
            prompt += "\n## 语义相关的已完成章节\n\n"
            prompt += "以下是通过语义检索找到的与待生成章节最相关的已完成章节摘要，请确保新大纲与这些已完成内容保持一致：\n\n"
            for summary in relevant_summaries:
                prompt += f"- 第{summary.get('chapter_number', '?')}章 {summary.get('title', '')}：{summary.get('summary', '')}"
                if summary.get('relevance_score'):
                    prompt += f"（相关度: {summary.get('relevance_score')}）"
                prompt += "\n"
            prompt += "\n"

        if prev_part:
            prompt += f"""
## 上一部分的结尾
{prev_part}
"""

        if next_part:
            prompt += f"""
## 下一部分的开始
{next_part}
"""

        prompt += f"""
## 世界观设定
{json.dumps(world_setting, ensure_ascii=False, indent=2)}

## 角色档案
{json.dumps(characters, ensure_ascii=False, indent=2)}

## 输出要求

请为第 {actual_start} 章到第 {actual_end} 章生成详细的章节大纲（共 {actual_num} 章）。

每个章节应包含：
- chapter_number: 章节编号
- title: 章节标题
- summary: 章节摘要（100-200字）

确保：
1. 严格按照章节编号顺序生成（{actual_start} 到 {actual_end}）
2. 章节之间有自然的承接关系
3. 与前文已生成的章节保持设定一致、剧情连贯
4. 关键事件和冲突合理分布在各个章节
5. 角色成长轨迹清晰可见、符合前文的发展
6. 整体节奏符合起承转合结构

输出JSON格式：
{{
  "chapter_outline": [
    {{
      "chapter_number": {actual_start},
      "title": "...",
      "summary": "..."
    }},
    ...
  ]
}}
"""
        return prompt
