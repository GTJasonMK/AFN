"""
嵌入模型配置路由

提供嵌入模型配置的 CRUD 和测试接口。
"""

import logging
import asyncio
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request, status

from ...core.dependencies import get_default_user, get_embedding_config_service
from ...exceptions import ResourceNotFoundError
from ...schemas.embedding_config import (
    EmbeddingConfigCreate,
    EmbeddingConfigRead,
    EmbeddingConfigUpdate,
    EmbeddingConfigTestResponse,
    EMBEDDING_PROVIDERS,
)
from ...schemas.model_download import DownloadDefaultLocalEmbeddingModelRequest
from ...schemas.user import UserInDB
from ...services.embedding_config_service import EmbeddingConfigService
from ...services.hf_model_download_service import (
    DownloadStoppedError,
    download_hf_repo_to_dir,
    fetch_hf_model_manifest,
    sanitize_model_dir_name,
    safe_rmtree,
)
from ...utils.sse_helpers import create_sse_response, sse_complete_event, sse_error_event, sse_event


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/embedding-configs", tags=["Embedding Configuration"])


# ========== 嵌入模型配置管理API ==========


@router.get("/providers")
async def list_providers():
    """获取支持的嵌入模型提供方列表。"""
    return [provider.model_dump() for provider in EMBEDDING_PROVIDERS]


@router.get("", response_model=list[EmbeddingConfigRead])
async def list_embedding_configs(
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> list[EmbeddingConfigRead]:
    """获取用户的所有嵌入模型配置列表。"""
    logger.debug("用户 %s 查询嵌入模型配置列表", desktop_user.id)
    return await service.list_configs(desktop_user.id)


@router.get("/active", response_model=EmbeddingConfigRead)
async def get_active_config(
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """获取用户当前激活的嵌入模型配置。"""
    config = await service.get_active_config(desktop_user.id)
    if not config:
        logger.warning("用户 %s 没有激活的嵌入模型配置", desktop_user.id)
        raise ResourceNotFoundError("激活的嵌入模型配置", f"用户 {desktop_user.id}")
    logger.debug("用户 %s 获取激活的嵌入模型配置: %s", desktop_user.id, config.config_name)
    return config


@router.get("/{config_id}", response_model=EmbeddingConfigRead)
async def get_embedding_config_by_id(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """获取指定ID的嵌入模型配置。"""
    logger.debug("用户 %s 查询嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.get_config(config_id, desktop_user.id)


@router.post("", response_model=EmbeddingConfigRead, status_code=status.HTTP_201_CREATED)
async def create_embedding_config(
    payload: EmbeddingConfigCreate,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """创建新的嵌入模型配置。"""
    logger.info("用户 %s 创建嵌入模型配置: %s", desktop_user.id, payload.config_name)
    return await service.create_config(desktop_user.id, payload)


@router.put("/{config_id}", response_model=EmbeddingConfigRead)
async def update_embedding_config(
    config_id: int,
    payload: EmbeddingConfigUpdate,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """更新指定ID的嵌入模型配置。"""
    logger.info("用户 %s 更新嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.update_config(config_id, desktop_user.id, payload)


@router.post("/{config_id}/activate", response_model=EmbeddingConfigRead)
async def activate_embedding_config(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigRead:
    """激活指定ID的嵌入模型配置。"""
    logger.info("用户 %s 激活嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.activate_config(config_id, desktop_user.id)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_embedding_config_by_id(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> None:
    """删除指定ID的嵌入模型配置。"""
    logger.info("用户 %s 删除嵌入模型配置 ID=%s", desktop_user.id, config_id)
    await service.delete_config(config_id, desktop_user.id)


@router.post("/{config_id}/test", response_model=EmbeddingConfigTestResponse)
async def test_embedding_config(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> EmbeddingConfigTestResponse:
    """测试指定ID的嵌入模型配置是否可用。"""
    logger.info("用户 %s 测试嵌入模型配置 ID=%s", desktop_user.id, config_id)
    return await service.test_config(config_id, desktop_user.id)


# ========== 导入导出API ==========


@router.get("/{config_id}/export")
async def export_embedding_config(
    config_id: int,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """导出单个嵌入模型配置。"""
    logger.debug("用户 %s 导出嵌入模型配置 ID=%s", desktop_user.id, config_id)
    export_data = await service.export_config(config_id, desktop_user.id)
    return export_data


@router.get("/export/all")
async def export_all_embedding_configs(
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """导出用户的所有嵌入模型配置。"""
    logger.debug("用户 %s 导出所有嵌入模型配置", desktop_user.id)
    export_data = await service.export_all_configs(desktop_user.id)
    return export_data


@router.post("/import")
async def import_embedding_configs(
    import_data: dict,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """导入嵌入模型配置。"""
    logger.info("用户 %s 导入嵌入模型配置", desktop_user.id)
    result = await service.import_configs(desktop_user.id, import_data)
    return result


# ========== 本地模型下载 API ==========


DEFAULT_LOCAL_EMBEDDING_REPO_ID = "BAAI/bge-base-zh-v1.5"


def _is_local_model_ready(model_dir: Path) -> bool:
    """判断目录是否看起来像可用的 sentence-transformers 模型目录。"""
    try:
        if not model_dir.exists():
            return False
        return (model_dir / "modules.json").exists() or (model_dir / "config.json").exists()
    except Exception:
        return False


@router.post("/local-models/download-default-stream")
async def download_default_local_embedding_model_stream(
    request: Request,
    payload: DownloadDefaultLocalEmbeddingModelRequest,
    service: EmbeddingConfigService = Depends(get_embedding_config_service),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    下载默认本地嵌入模型（SSE流式返回进度）

    说明：
    - 下载产物落到 `storage/models/<repo_id.replace('/', '_')>`；
    - 下载完成后会自动创建嵌入配置（provider=local, model_name=repo_id）；
    - 默认会自动激活该配置（activate_after_download=True）。

    事件类型：
    - progress: {"phase","message","progress_percent",...}
    - complete: {"message","repo_id","model_dir","config_id","activated"}
    - error: {"message"}
    """
    repo_id = (payload.repo_id or DEFAULT_LOCAL_EMBEDDING_REPO_ID).strip()
    if not repo_id:
        repo_id = DEFAULT_LOCAL_EMBEDDING_REPO_ID

    # 统一使用 settings.storage_dir/models 作为落盘目录（与 EmbeddingService 查找逻辑一致）
    from ...core.config import settings

    models_root = (settings.storage_dir / "models").resolve()
    models_root.mkdir(parents=True, exist_ok=True)

    safe_dir_name = sanitize_model_dir_name(repo_id)
    final_dir = (models_root / safe_dir_name).resolve()
    tmp_dir = (models_root / f".tmp_download_{safe_dir_name}_{uuid.uuid4().hex}").resolve()

    async def gen():
        started = time.time()
        try:
            yield sse_event(
                "progress",
                {
                    "phase": "starting",
                    "message": "准备下载默认本地嵌入模型…",
                    "repo_id": repo_id,
                    "progress_percent": 0,
                },
            )

            # 已存在则跳过下载
            if _is_local_model_ready(final_dir):
                yield sse_event(
                    "progress",
                    {
                        "phase": "checking",
                        "message": "检测到模型目录已存在，跳过下载。",
                        "repo_id": repo_id,
                        "progress_percent": 100,
                    },
                )
            else:
                # 若存在“残缺目录”（例如上次下载中断留下的半成品），先清理再开始，避免反复失败
                if final_dir.exists() and not _is_local_model_ready(final_dir):
                    safe_rmtree(final_dir)

                safe_rmtree(tmp_dir)
                tmp_dir.mkdir(parents=True, exist_ok=True)

                yield sse_event(
                    "progress",
                    {
                        "phase": "manifest",
                        "message": "获取模型清单…",
                        "repo_id": repo_id,
                        "progress_percent": 0,
                    },
                )
                sha, files = await fetch_hf_model_manifest(repo_id)
                revision = sha or "main"

                if not files:
                    raise RuntimeError("模型清单为空，无法下载。请检查网络或仓库是否存在。")

                yield sse_event(
                    "progress",
                    {
                        "phase": "downloading",
                        "message": f"开始下载（共 {len(files)} 个文件）…",
                        "repo_id": repo_id,
                        "revision": revision,
                        "completed_files": 0,
                        "total_files": len(files),
                        "progress_percent": 0,
                    },
                )

                async for evt in download_hf_repo_to_dir(
                    repo_id=repo_id,
                    revision=revision,
                    files=files,
                    target_dir=tmp_dir,
                    request_disconnected=request.is_disconnected,
                ):
                    if evt.get("type") == "progress":
                        yield sse_event("progress", evt.get("data") or {})

                # 基本校验
                if not _is_local_model_ready(tmp_dir):
                    raise RuntimeError("下载完成但模型目录结构不完整（缺少 modules.json/config.json）。")

                # 原子替换：只在成功时落盘到最终目录
                safe_rmtree(final_dir)
                tmp_dir.replace(final_dir)

            # 下载完成：确保创建配置
            yield sse_event(
                "progress",
                {
                    "phase": "config",
                    "message": "写入嵌入配置…",
                    "repo_id": repo_id,
                    "model_dir": str(final_dir),
                    "progress_percent": 100,
                },
            )

            # 查找是否已存在相同 provider+model 的配置（避免重复创建）
            existing = None
            try:
                configs = await service.repo.list_by_user(desktop_user.id)
                for cfg in configs:
                    if (cfg.provider or "").lower() == "local" and (cfg.model_name or "").strip() == repo_id:
                        existing = cfg
                        break
            except Exception:
                existing = None

            activated = False
            if existing:
                config_id = existing.id
            else:
                create_payload = EmbeddingConfigCreate(
                    config_name=f"本地嵌入：{repo_id}",
                    provider="local",
                    api_base_url=None,
                    api_key=None,
                    model_name=repo_id,
                    vector_size=None,
                )
                created = await service.create_config(desktop_user.id, create_payload)
                config_id = created.id

            if payload.activate_after_download:
                try:
                    await service.activate_config(config_id, desktop_user.id)
                    activated = True
                except Exception:
                    activated = False

            cost_s = max(0.0, time.time() - started)
            yield sse_complete_event(
                "下载完成",
                {
                    "repo_id": repo_id,
                    "model_dir": str(final_dir),
                    "config_id": config_id,
                    "activated": activated,
                    "elapsed_seconds": round(cost_s, 2),
                },
            )

        except DownloadStoppedError:
            # 用户停止/客户端断开：静默清理，不返回 error（前端会当作停止）
            safe_rmtree(tmp_dir)
            return
        except asyncio.CancelledError:
            safe_rmtree(tmp_dir)
            raise
        except Exception as exc:
            safe_rmtree(tmp_dir)
            yield sse_error_event(exc, "下载本地嵌入模型")

    return create_sse_response(gen())
