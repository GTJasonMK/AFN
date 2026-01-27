"""图片生成模块文件系统工具：异步 Path I/O + 目录入口（支持热更新）。"""

from __future__ import annotations

import asyncio
from os import stat_result
from pathlib import Path
from typing import List

from ...core.config import settings


# 目录入口（支持热更新）
def get_images_root() -> Path:
    return settings.generated_images_dir


def get_export_dir() -> Path:
    return settings.exports_dir


# 异步文件操作（薄封装）：统一基于 asyncio.to_thread，避免阻塞事件循环
async def async_exists(path: Path) -> bool:
    return await asyncio.to_thread(path.exists)


async def async_is_dir(path: Path) -> bool:
    return await asyncio.to_thread(path.is_dir)


async def async_mkdir(path: Path, *, parents: bool = False, exist_ok: bool = False) -> None:
    await asyncio.to_thread(path.mkdir, parents=parents, exist_ok=exist_ok)


async def async_read_bytes(path: Path) -> bytes:
    return await asyncio.to_thread(path.read_bytes)


async def async_write_bytes(path: Path, data: bytes) -> None:
    await asyncio.to_thread(path.write_bytes, data)


async def async_rename(src: Path, dst: Path) -> None:
    await asyncio.to_thread(src.rename, dst)


async def async_unlink(path: Path, *, missing_ok: bool = False) -> None:
    await asyncio.to_thread(path.unlink, missing_ok=missing_ok)


async def async_rmdir(path: Path) -> None:
    await asyncio.to_thread(path.rmdir)


async def async_iterdir(path: Path) -> List[Path]:
    return await asyncio.to_thread(lambda: list(path.iterdir()))


async def async_stat(path: Path) -> stat_result:
    return await asyncio.to_thread(path.stat)


async def async_glob(path: Path, pattern: str) -> List[Path]:
    return await asyncio.to_thread(lambda: list(path.glob(pattern)))
