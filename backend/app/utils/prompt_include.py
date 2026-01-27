"""
提示词模板 include 工具

用于在提示词 Markdown 模板中复用公共片段，减少概念重复与策略漂移。

当前支持的 include 语法：

  <!-- @include relative/path.md -->
  <!-- @include "relative/path.md" -->

注意：
- include 路径相对 `backend/prompts/` 根目录（即 PROMPTS_DIR）。
- 支持递归 include，并包含循环检测与最大深度限制。
- include 文件若包含 YAML frontmatter（--- ... ---），会自动剥离，仅插入正文部分。
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class PromptFrontmatter:
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_INCLUDE_RE = re.compile(r"<!--\s*@include\s+(.+?)\s*-->")


def parse_yaml_frontmatter(content: str) -> Tuple[Dict[str, Optional[str]], str]:
    """
    解析 Markdown 文件的 YAML frontmatter（仅支持简单 key: value）。

    Returns:
        (metadata_dict, body)；metadata_dict 包含 title/description/tags 三个键。
    """
    metadata: Dict[str, Optional[str]] = {"title": None, "description": None, "tags": None}

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return metadata, content

    yaml_block = match.group(1)
    body = content[match.end():]

    for line in yaml_block.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        if key in metadata:
            metadata[key] = value if value else None

    return metadata, body


def _parse_include_target(raw: str) -> str:
    target = raw.strip()
    if (target.startswith('"') and target.endswith('"')) or (target.startswith("'") and target.endswith("'")):
        return target[1:-1].strip()
    return target


def resolve_prompt_includes(
    body: str,
    *,
    current_file: Path,
    prompts_dir: Path,
    max_depth: int = 10,
    _depth: int = 0,
    _stack: Optional[Tuple[Path, ...]] = None,
) -> str:
    """
    解析并替换提示词正文中的 include 指令。

    Args:
        body: 提示词正文（不含 frontmatter）
        current_file: 当前模板文件路径（用于构造报错链路）
        prompts_dir: prompts 根目录
        max_depth: 最大递归深度

    Returns:
        展开 include 后的正文
    """
    if _stack is None:
        _stack = (current_file,)

    if _depth > max_depth:
        chain = " -> ".join(str(p.relative_to(prompts_dir)) for p in _stack if p.is_absolute())
        raise ValueError(f"提示词 include 深度超过限制（max_depth={max_depth}）：{chain}")

    prompts_root = prompts_dir.resolve()

    def _replace(match: re.Match[str]) -> str:
        raw_target = match.group(1)
        rel = _parse_include_target(raw_target)
        if not rel:
            return ""

        include_path = (prompts_root / rel).resolve()
        if prompts_root not in include_path.parents and include_path != prompts_root:
            raise ValueError(f"提示词 include 路径越界: {rel}")
        if not include_path.is_file():
            raise FileNotFoundError(f"提示词 include 文件不存在: {rel}")

        if include_path in _stack:
            chain = " -> ".join(str(p.relative_to(prompts_root)) for p in (*_stack, include_path))
            raise ValueError(f"提示词 include 发生循环引用：{chain}")

        text = include_path.read_text(encoding="utf-8")
        _, include_body = parse_yaml_frontmatter(text)
        include_body = resolve_prompt_includes(
            include_body,
            current_file=include_path,
            prompts_dir=prompts_root,
            max_depth=max_depth,
            _depth=_depth + 1,
            _stack=(*_stack, include_path),
        )
        return include_body.rstrip("\n")

    return _INCLUDE_RE.sub(_replace, body)

