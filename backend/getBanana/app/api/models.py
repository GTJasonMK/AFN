"""
模型列表API路由
- OpenAI兼容的 /v1/models 接口
"""
import time
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.utils.auth import require_api_auth
from app.config import config_manager

router = APIRouter()


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "google"


class ModelList(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


@router.get("/v1/models")
async def list_models(token: str = Depends(require_api_auth)) -> ModelList:
    """
    列出可用模型

    返回OpenAI兼容的模型列表格式
    """
    config = config_manager.config
    models = []

    for model_config in config.models:
        models.append(
            ModelInfo(
                id=model_config.id,
                created=int(time.time()),
                owned_by="google"
            )
        )

    # 添加默认模型（2025年11月）
    default_models = [
        # Gemini 3 系列
        "gemini-3-pro-preview",
        "gemini-3-pro-image-preview",
        # Gemini 2.5 系列
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        # 图像生成
        "nano-banana-pro",
    ]

    existing_ids = {m.id for m in models}
    for model_id in default_models:
        if model_id not in existing_ids:
            models.append(
                ModelInfo(
                    id=model_id,
                    created=int(time.time()),
                    owned_by="google"
                )
            )

    return ModelList(data=models)


@router.get("/v1/models/{model_id}")
async def get_model(
    model_id: str,
    token: str = Depends(require_api_auth)
) -> ModelInfo:
    """获取单个模型信息"""
    return ModelInfo(
        id=model_id,
        created=int(time.time()),
        owned_by="google"
    )
