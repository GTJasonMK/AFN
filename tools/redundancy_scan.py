#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全仓库重复片段扫描工具（文本级）

目的：
- 为 `docs/REDUNDANCY_AUDIT_NEXT.md` 生成候选重复片段清单
- 仅做“文本重复”发现，不直接等同于“应该重构”

规则（默认）：
- 仅扫描指定扩展名
- 排除常见构建/缓存/依赖目录
- 去空行、压缩空白后，以 N 行滑动窗口做重复检测
- 过滤低信息量片段（过短/几乎全是符号）
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Iterable


_WS_RE = re.compile(r"\s+")
_ALNUM_RE = re.compile(r"[A-Za-z0-9_]")


@dataclasses.dataclass(frozen=True)
class Occurrence:
    path: str
    line: int


def _iter_files(
    root: Path,
    exts: set[str],
    exclude_dirs: set[str],
) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        for name in filenames:
            p = Path(dirpath) / name
            if p.suffix.lower() in exts:
                yield p


def _normalize_lines(text: str) -> list[tuple[int, str]]:
    """
    返回 (原始行号, 规范化后行内容) 列表。
    - 去掉空行
    - 压缩空白
    """
    out: list[tuple[int, str]] = []
    for idx, raw in enumerate(text.splitlines(), start=1):
        s = _WS_RE.sub(" ", raw.strip())
        if not s:
            continue
        out.append((idx, s))
    return out


def _is_low_signal(window_lines: list[str], min_chars: int, min_alnum: int) -> bool:
    joined = "\n".join(window_lines)
    if len(joined) < min_chars:
        return True
    alnum_count = len(_ALNUM_RE.findall(joined))
    if alnum_count < min_alnum:
        return True
    return False


def _scan_file(
    root: Path,
    path: Path,
    window: int,
    min_chars: int,
    min_alnum: int,
    buckets: DefaultDict[str, list[Occurrence]],
    samples: dict[str, str],
) -> None:
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    lines = _normalize_lines(data)
    if len(lines) < window:
        return

    try:
        rel_path = path.resolve().relative_to(root).as_posix()
    except ValueError:
        rel_path = path.as_posix()

    for i in range(0, len(lines) - window + 1):
        start_line = lines[i][0]
        w = [lines[j][1] for j in range(i, i + window)]
        if _is_low_signal(w, min_chars=min_chars, min_alnum=min_alnum):
            continue
        key = "\n".join(w)
        buckets[key].append(Occurrence(path=rel_path, line=start_line))
        if key not in samples:
            samples[key] = w[0]


def _render_markdown(
    *,
    now_date: str,
    window: int,
    exts: list[str],
    exclude_dirs: list[str],
    results: list[tuple[str, list[Occurrence]]],
) -> str:
    lines: list[str] = []
    lines.append("# 全仓库重复代码审查清单（自动扫描）")
    lines.append("")
    lines.append(f"- 日期：{now_date}")
    lines.append("- 执行者：Codex")
    lines.append(f"- 扫描范围：{', '.join(exts)}")
    lines.append(f"- 排除目录：{', '.join(exclude_dirs)}")
    lines.append(f"- 重复片段阈值：连续 {window} 行（去空行、压缩空白后匹配）")
    lines.append("")
    lines.append("## 说明")
    lines.append("- 本清单基于文本重复检测，可能存在误报；需人工确认业务差异与复用价值。")
    lines.append("- 已做低信息量过滤（过短/符号占比过高的片段会被丢弃），优先输出更“可重构”的候选。")
    lines.append("")
    lines.append("## 候选重复片段")

    if not results:
        lines.append("（未发现满足阈值的候选项）")
        lines.append("")
        return "\n".join(lines)

    for idx, (snippet_key, occs) in enumerate(results, start=1):
        files = sorted({o.path for o in occs})
        lines.append(f"### 候选 {idx}（涉及文件 {len(files)} 个，出现 {len(occs)} 次）")
        summary = ""
        for s in snippet_key.splitlines():
            if len(_ALNUM_RE.findall(s)) >= 5 and len(s) >= 10:
                summary = s
                break
        if not summary:
            summary = snippet_key.splitlines()[0]
        if len(summary) > 120:
            summary = summary[:117] + "..."
        lines.append(f"- 片段摘要：{summary}")
        for o in sorted(occs, key=lambda x: (x.path, x.line)):
            lines.append(f"  - `{o.path}:{o.line}`")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="扫描根目录（默认：仓库根）")
    parser.add_argument("--window", type=int, default=12, help="滑动窗口行数")
    parser.add_argument("--min-occ", type=int, default=3, help="最少出现次数")
    parser.add_argument("--min-files", type=int, default=3, help="最少涉及文件数")
    parser.add_argument("--max-items", type=int, default=80, help="最多输出候选项数量")
    parser.add_argument("--min-chars", type=int, default=180, help="窗口最少字符数（过滤噪声）")
    parser.add_argument("--min-alnum", type=int, default=60, help="窗口最少字母数字数量（过滤噪声）")
    args = parser.parse_args(argv)

    exts = {
        ".css",
        ".js",
        ".jsx",
        ".py",
        ".qml",
        ".qss",
        ".ts",
        ".tsx",
    }
    exclude_dirs = {
        ".codex",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "storage",
        "venv",
    }

    root = Path(args.root).resolve()
    buckets: DefaultDict[str, list[Occurrence]] = defaultdict(list)
    samples: dict[str, str] = {}

    for p in _iter_files(root=root, exts=exts, exclude_dirs=exclude_dirs):
        _scan_file(
            root,
            p,
            window=args.window,
            min_chars=args.min_chars,
            min_alnum=args.min_alnum,
            buckets=buckets,
            samples=samples,
        )

    # 过滤：至少 N 次、至少 M 个文件
    kept: list[tuple[str, list[Occurrence]]] = []
    for key, occs in buckets.items():
        if len(occs) < args.min_occ:
            continue
        if len({o.path for o in occs}) < args.min_files:
            continue
        kept.append((key, occs))

    # 排序：文件数 > 出现次数 > 片段长度
    kept.sort(key=lambda kv: (len({o.path for o in kv[1]}), len(kv[1]), len(kv[0])), reverse=True)
    kept = kept[: args.max_items]

    now_date = _dt.date.today().isoformat()
    md = _render_markdown(
        now_date=now_date,
        window=args.window,
        exts=sorted(exts),
        exclude_dirs=sorted(exclude_dirs),
        results=kept,
    )
    sys.stdout.write(md)
    if not md.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
