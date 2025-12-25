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
        构建生成部分大纲的用户消息（系统提示词已外部化到 part_outline_single.md）

        本方法只负责数据填充，指导性内容已移至外部系统提示词。

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
            str: 构建好的用户消息
        """
        # 计算章节范围
        start_chapter = (current_part_number - 1) * chapters_per_part + 1
        end_chapter = min(current_part_number * chapters_per_part, total_chapters)

        # 构建用户消息（只包含数据，不包含指导）
        prompt = f"""## 生成任务

请为这部长篇小说生成**第 {current_part_number} 部分**的大纲。

## 小说规模

- 总章节数：{total_chapters}
- 每部分章节数：约 {chapters_per_part} 章
- 总部分数：{total_parts}
- 当前部分：第 {current_part_number} 部分（第 {start_chapter}-{end_chapter} 章）

## 世界观设定

{json.dumps(world_setting, ensure_ascii=False, indent=2)}

## 角色档案

{json.dumps(characters, ensure_ascii=False, indent=2)}

## 主要剧情

{full_synopsis}"""

        # 添加前面已生成的部分（用于保持连贯性）
        if previous_parts and len(previous_parts) > 0:
            prompt += "\n\n## 前面已生成的部分\n"
            for part in previous_parts:
                prompt += f"""
### 第 {part.part_number} 部分：{part.title}
- 章节：第 {part.start_chapter}-{part.end_chapter} 章
- 主题：{part.theme or ""}
- 摘要：{part.summary or ""}
- 关键事件：{json.dumps(part.key_events or [], ensure_ascii=False)}
- 角色发展：{json.dumps(part.character_arcs or {}, ensure_ascii=False)}
- 冲突：{json.dumps(part.conflicts or [], ensure_ascii=False)}
- 结尾钩子：{part.ending_hook or ""}
"""

        # 添加优化方向（如果有）
        if optimization_prompt:
            prompt += f"\n\n## 用户特别要求\n\n{optimization_prompt}"

        # 添加输出格式强调（防止LLM返回错误格式）
        prompt += f"""

---

## 输出要求（重要）

请直接输出第 {current_part_number} 部分的JSON对象，格式如下：

```json
{{
  "part_number": {current_part_number},
  "title": "...",
  "start_chapter": {start_chapter},
  "end_chapter": {end_chapter},
  "summary": "200-300字详细摘要...",
  "theme": "...",
  "key_events": ["事件1", "事件2", "事件3"],
  "character_arcs": {{"角色名": "发展轨迹"}},
  "conflicts": ["冲突1", "冲突2"],
  "ending_hook": "..."
}}
```

**注意**：
- 直接输出 `{{...}}` 单个对象
- 不要包装成 `{{"parts": [...]}}` 数组格式
- 所有字段必须完整填写，summary 必须 200 字以上"""

        return prompt

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
        构建生成章节大纲的用户消息（系统提示词已外部化到 part_chapters.md）

        本方法只负责数据填充，指导性内容已移至外部系统提示词。
        此方法需要查询上下文信息（前后部分），因此是异步的。

        Args:
            part_outline: 部分大纲对象
            project: 项目对象
            start_chapter: 起始章节号（串行模式，默认从part_outline.start_chapter开始）
            num_chapters: 要生成的章节数（串行模式，默认生成该部分的全部章节）
            previous_chapters: 前面已生成的章节大纲列表（串行模式）
            relevant_summaries: RAG检索到的相关已完成章节摘要列表

        Returns:
            str: 构建好的用户消息

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
        prev_part_hook = None
        if part_outline.part_number > 1:
            prev_part_outline = await self.part_outline_repo.get_by_part_number(
                project.id, part_outline.part_number - 1
            )
            if prev_part_outline:
                prev_part_hook = prev_part_outline.ending_hook

        # 获取下一部分的summary
        next_part_summary = None
        next_part_outline = await self.part_outline_repo.get_by_part_number(
            project.id, part_outline.part_number + 1
        )
        if next_part_outline:
            next_part_summary = next_part_outline.summary

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

        # 构建用户消息（只包含数据）
        prompt = f"""## 生成任务

请为第 {part_outline.part_number} 部分生成第 {actual_start}-{actual_end} 章的大纲（共 {actual_num} 章）。

## 部分大纲

- 标题：{part_outline.title}
- 范围：第 {part_outline.start_chapter}-{part_outline.end_chapter} 章
- 主题：{part_outline.theme or ""}
- 摘要：{part_outline.summary or ""}
- 关键事件：{json.dumps(part_outline.key_events or [], ensure_ascii=False)}
- 冲突：{json.dumps(part_outline.conflicts or [], ensure_ascii=False)}
- 角色发展：{json.dumps(part_outline.character_arcs or {}, ensure_ascii=False)}
- 结尾钩子：{part_outline.ending_hook or ""}"""

        # 添加前面已生成的章节
        if previous_chapters and len(previous_chapters) > 0:
            prompt += "\n\n## 前文章节大纲\n"
            recent_chapters = previous_chapters[-10:] if len(previous_chapters) > 10 else previous_chapters
            if len(previous_chapters) > 10:
                prompt += f"（展示最近10章，前 {len(previous_chapters) - 10} 章已省略）\n"
            for ch in recent_chapters:
                prompt += f"\n### 第 {ch.get('chapter_number', '?')} 章：{ch.get('title', '')}\n{ch.get('summary', '')}"

        # 添加RAG检索结果
        if relevant_summaries and len(relevant_summaries) > 0:
            prompt += "\n\n## 语义相关的历史章节\n"
            for summary in relevant_summaries:
                score = f"（相关度: {summary.get('relevance_score')}）" if summary.get('relevance_score') else ""
                prompt += f"\n- 第{summary.get('chapter_number', '?')}章 {summary.get('title', '')}：{summary.get('summary', '')}{score}"

        # 添加上下文信息
        if prev_part_hook:
            prompt += f"\n\n## 上一部分结尾\n{prev_part_hook}"

        if next_part_summary:
            prompt += f"\n\n## 下一部分开始\n{next_part_summary}"

        prompt += f"""

## 世界观设定

{json.dumps(world_setting, ensure_ascii=False, indent=2)}

## 角色档案

{json.dumps(characters, ensure_ascii=False, indent=2)}"""

        return prompt
