"""
HuggingFace 模型下载服务

目标：
- 在桌面端（Electron/PyQt）提供“可控下载”：可展示进度、可停止、失败可清理。
- 下载产物落到项目 storage 目录下，保证可移植与可清理（不依赖用户全局缓存目录）。

注意：
- 这里不使用 huggingface_hub 的缓存机制，避免“下载到用户家目录”且难以清理的问题；
  统一用 httpx 流式下载到指定目录。
- 默认使用 https://huggingface.co，但支持通过环境变量 HF_ENDPOINT 覆盖（例如镜像站）。
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class DownloadStoppedError(Exception):
    """下载被用户停止或客户端断开。"""


@dataclass(frozen=True)
class HFRepoFile:
    """HuggingFace 仓库文件描述（最小字段集）"""

    filename: str
    size: Optional[int] = None


def resolve_hf_endpoint() -> str:
    """
    解析 HuggingFace Endpoint。

    允许通过环境变量 HF_ENDPOINT 覆盖（huggingface_hub 也使用该变量）。
    """
    endpoint = (os.environ.get("HF_ENDPOINT") or "https://huggingface.co").strip()
    return endpoint.rstrip("/")


def sanitize_model_dir_name(repo_id: str) -> str:
    """
    将 repo_id 转为适合作为目录名的形式。

    与 EmbeddingService._find_local_model_path 的默认约定保持一致：
    - 将 "/" 替换为 "_"。
    """
    return repo_id.replace("/", "_").strip()


async def fetch_hf_model_manifest(
    repo_id: str,
    *,
    endpoint: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> tuple[Optional[str], List[HFRepoFile]]:
    """
    从 HuggingFace API 获取模型文件清单。

    Returns:
        (revision_sha, files)
    """
    endpoint = (endpoint or resolve_hf_endpoint()).rstrip("/")
    url = f"{endpoint}/api/models/{repo_id}"

    owns_client = client is None
    if client is None:
        # 下载任务通常较长：read 超时设大一点；连接超时保持适中
        timeout = httpx.Timeout(connect=20.0, read=120.0, write=120.0, pool=20.0)
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    try:
        resp = await client.get(url)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json() if resp.content else {}

        sha = data.get("sha")
        siblings = data.get("siblings") or []
        files: List[HFRepoFile] = []
        for item in siblings:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("rfilename") or item.get("path") or "").strip()
            if not filename:
                continue
            # 跳过 .git 目录（理论上不会出现）
            if filename.startswith(".git/") or filename.startswith(".github/"):
                continue
            raw_size = item.get("size")
            size: Optional[int] = None
            try:
                if raw_size is not None:
                    size = int(raw_size)
                    if size < 0:
                        size = None
            except Exception:
                size = None
            files.append(HFRepoFile(filename=filename, size=size))

        return sha, files
    finally:
        if owns_client:
            await client.aclose()


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


async def download_hf_repo_to_dir(
    *,
    repo_id: str,
    revision: str,
    files: List[HFRepoFile],
    target_dir: Path,
    endpoint: Optional[str] = None,
    request_disconnected: Optional[callable] = None,
    progress_emit_min_interval_s: float = 0.2,
    progress_emit_max_interval_s: float = 1.0,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    将 HuggingFace repo（指定 revision）下载到 target_dir。

    以事件流（dict）形式 yield 进度，便于路由层封装为 SSE。

    事件：
    - {"type": "progress", "data": {...}}

    停止条件：
    - request_disconnected 返回 True（客户端断开/用户停止）则抛 DownloadStoppedError。
    """
    endpoint = (endpoint or resolve_hf_endpoint()).rstrip("/")

    # 计算总大小（缺失 size 的文件按 0 计入，总进度将退化为“文件进度”）
    total_bytes = sum(int(f.size or 0) for f in files)
    total_files = len(files)

    downloaded_bytes = 0
    completed_files = 0

    # httpx client（跟随重定向，支持 LFS 文件跳转）
    timeout = httpx.Timeout(connect=20.0, read=120.0, write=120.0, pool=20.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        last_emit_at = 0.0
        last_percent_bucket: Optional[int] = None
        target_root = target_dir.resolve()

        async def _maybe_emit(*, force: bool, current_file: str, note: str = "") -> None:
            nonlocal last_emit_at, last_percent_bucket
            now = time.monotonic()
            if not force:
                elapsed = now - last_emit_at
                if elapsed < progress_emit_min_interval_s:
                    return

            percent: Optional[float]
            if total_bytes > 0:
                percent = min(100.0, max(0.0, (downloaded_bytes / total_bytes) * 100.0))
            elif total_files > 0:
                percent = min(100.0, max(0.0, (completed_files / total_files) * 100.0))
            else:
                percent = None

            bucket = int(percent) if isinstance(percent, (int, float)) else None
            if not force and bucket is not None and last_percent_bucket == bucket:
                # 百分比未变化时，仍然需要周期性推送“字节/文件进度”，避免前端长时间无更新
                if now - last_emit_at < progress_emit_max_interval_s:
                    return

            last_emit_at = now
            last_percent_bucket = bucket

            yield_event = {
                "type": "progress",
                "data": {
                    "phase": "downloading",
                    "message": note or "下载中…",
                    "repo_id": repo_id,
                    "revision": revision,
                    "current_file": current_file,
                    "completed_files": completed_files,
                    "total_files": total_files,
                    "downloaded_bytes": downloaded_bytes,
                    "total_bytes": total_bytes,
                    "progress_percent": percent,
                },
            }
            # 通过闭包 yield（技巧：async generator 内部函数不能直接 yield）
            events_buffer.append(yield_event)

        events_buffer: List[Dict[str, Any]] = []

        for f in files:
            if request_disconnected is not None:
                try:
                    if await request_disconnected():
                        raise DownloadStoppedError("客户端断开，停止下载")
                except DownloadStoppedError:
                    raise
                except Exception:
                    # is_disconnected 不应影响主流程，忽略探测异常
                    pass

            filename = f.filename
            url = f"{endpoint}/{repo_id}/resolve/{revision}/{filename}"

            # 防御：避免文件名包含 ../ 等路径穿越写到 target_dir 之外
            dst_path = (target_dir / filename).resolve()
            if dst_path != target_root and target_root not in dst_path.parents:
                raise ValueError(f"非法文件路径（疑似路径穿越）: {filename}")
            part_path = dst_path.with_suffix(dst_path.suffix + ".part")
            _ensure_parent_dir(dst_path)

            # 如果目标文件已存在且大小匹配，跳过（允许“断点续传式”重复点击）
            if dst_path.exists() and f.size and dst_path.stat().st_size == f.size:
                completed_files += 1
                downloaded_bytes += int(f.size or 0)
                await _maybe_emit(force=True, current_file=filename, note="已存在，跳过…")
                while events_buffer:
                    yield events_buffer.pop(0)
                continue

            # 清理旧的 part 文件
            try:
                if part_path.exists():
                    part_path.unlink()
            except Exception:
                pass

            # 下载单文件
            try:
                async with client.stream("GET", url, headers={"Accept": "application/octet-stream"}) as resp:
                    resp.raise_for_status()

                    with open(part_path, "wb") as fp:
                        async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                            if request_disconnected is not None:
                                try:
                                    if await request_disconnected():
                                        raise DownloadStoppedError("客户端断开，停止下载")
                                except DownloadStoppedError:
                                    raise
                                except Exception:
                                    pass

                            fp.write(chunk)
                            downloaded_bytes += len(chunk)
                            await _maybe_emit(force=False, current_file=filename)
                            while events_buffer:
                                yield events_buffer.pop(0)

                # 完成：原子替换
                part_path.replace(dst_path)
                completed_files += 1
                await _maybe_emit(force=True, current_file=filename, note="文件下载完成")
                while events_buffer:
                    yield events_buffer.pop(0)

            except DownloadStoppedError:
                # 尽量清理 part 文件
                try:
                    if part_path.exists():
                        part_path.unlink()
                except Exception:
                    pass
                raise
            except Exception:
                # 失败时清理 part 文件，避免下次误判
                try:
                    if part_path.exists():
                        part_path.unlink()
                except Exception:
                    pass
                raise


def safe_rmtree(path: Path) -> None:
    """安全删除目录（失败不抛异常）。"""
    try:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
