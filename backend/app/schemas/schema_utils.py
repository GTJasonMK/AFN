"""
Schema 通用工具函数

目标：收敛多个 Schema 中的重复小工具，避免并行维护导致策略漂移。
"""

from __future__ import annotations

from typing import Optional


def mask_api_key(api_key: Optional[str]) -> Optional[str]:
    """遮蔽 API Key，仅显示前 8 位和后 4 位。"""
    if not api_key or len(api_key) <= 12:
        return "***" if api_key else None
    return f"{api_key[:8]}{'*' * (len(api_key) - 12)}{api_key[-4:]}"

