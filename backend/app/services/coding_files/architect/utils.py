"""
CodingFiles 架构模块公共工具

集中维护“语言 → 文件扩展名”等基础映射，避免多个模块重复维护导致策略漂移。
"""

from __future__ import annotations


def get_file_extension(language: str) -> str:
    """获取文件扩展名（未知语言默认 .py）。"""
    lang = (language or "").lower()
    extensions = {
        "python": ".py",
        "typescript": ".ts",
        "javascript": ".js",
        "go": ".go",
        "rust": ".rs",
        "java": ".java",
        "kotlin": ".kt",
        "swift": ".swift",
    }
    return extensions.get(lang, ".py")

