"""
文件上传API路由
- OpenAI兼容的文件上传接口
- 上传文件到Gemini API
- 图片访问接口
"""
import uuid
import time
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.utils.auth import require_api_auth
from app.config import IMAGES_DIR
from app.services.image_service import image_service
from app.services.account_manager import (
    account_manager,
    NoAvailableAccountError,
    AccountAuthError,
    AccountRateLimitError,
    AccountRequestError
)
from app.services.jwt_service import jwt_service
from app.services.chat_service import chat_service
from app.services.file_upload_service import file_upload_service

logger = logging.getLogger(__name__)

router = APIRouter()


class FileObject(BaseModel):
    id: str
    object: str = "file"
    bytes: int
    created_at: int
    filename: str
    purpose: str = "assistants"


class FileList(BaseModel):
    object: str = "list"
    data: list


@router.post("/v1/files")
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = Form("assistants"),
    token: str = Depends(require_api_auth)
) -> FileObject:
    """
    上传文件到Gemini

    1. 获取可用账号
    2. 确保有有效的JWT和Session
    3. 上传文件到Gemini API
    4. 返回OpenAI格式的文件ID

    支持图片等文件类型，返回OpenAI兼容的文件对象
    """
    # 读取文件内容
    content = await file.read()
    file_size = len(content)
    filename = file.filename or f"file_{uuid.uuid4().hex[:8]}"

    # 确定MIME类型
    mime_type = file.content_type
    if not mime_type:
        guessed = mimetypes.guess_type(filename)
        mime_type = guessed[0] if guessed[0] else "application/octet-stream"

    logger.info(f"开始上传文件: {filename}, 大小: {file_size}, MIME: {mime_type}")

    # 获取可用账号列表
    available_accounts = account_manager.get_available_accounts()
    if not available_accounts:
        next_cd = account_manager._get_next_cooldown_info()
        wait_msg = ""
        if next_cd:
            remaining = next_cd["remaining"]
            wait_msg = f"（最近冷却账号将在 {remaining} 秒后可用）"
        raise HTTPException(status_code=429, detail=f"没有可用账号{wait_msg}")

    # 尝试上传（支持多账号重试）
    max_retries = len(available_accounts)
    last_error = None

    for retry_idx in range(max_retries):
        account_idx = None
        try:
            # 获取下一个账号
            account = await account_manager.get_next_account()
            account_idx = account.index

            # 确保JWT有效
            jwt = await jwt_service.ensure_jwt(account)

            # 确保有Session（文件需要关联到Session）
            session_name = account.state.session_name
            if not session_name:
                session_name = await chat_service.create_gemini_session(account, jwt)
                account_manager.update_account_state(account_idx, session_name=session_name)

            # 上传到Gemini
            mapping = await file_upload_service.upload_and_map(
                jwt=jwt,
                session_name=session_name,
                team_id=account.team_id,
                file_content=content,
                filename=filename,
                mime_type=mime_type
            )

            logger.info(f"文件上传成功: {mapping.openai_file_id} -> {mapping.gemini_file_id}")

            return FileObject(
                id=mapping.openai_file_id,
                bytes=file_size,
                created_at=int(mapping.created_at),
                filename=filename,
                purpose=purpose
            )

        except AccountRateLimitError as e:
            last_error = e
            if account_idx is not None:
                from app.models.account import CooldownReason
                account_manager.mark_account_cooldown(account_idx, CooldownReason.RATE_LIMIT)
            logger.warning(f"上传重试 {retry_idx + 1}/{max_retries} 失败(限额): {e}")
            continue

        except AccountAuthError as e:
            last_error = e
            if account_idx is not None:
                from app.models.account import CooldownReason
                account_manager.mark_account_cooldown(account_idx, CooldownReason.AUTH_ERROR)
            logger.warning(f"上传重试 {retry_idx + 1}/{max_retries} 失败(认证): {e}")
            continue

        except AccountRequestError as e:
            last_error = e
            if account_idx is not None:
                from app.models.account import CooldownReason
                account_manager.mark_account_cooldown(account_idx, CooldownReason.GENERIC_ERROR)
            logger.warning(f"上传重试 {retry_idx + 1}/{max_retries} 失败(请求): {e}")
            continue

        except NoAvailableAccountError as e:
            last_error = e
            logger.warning(f"无可用账号: {e}")
            break

        except Exception as e:
            last_error = e
            logger.error(f"上传重试 {retry_idx + 1}/{max_retries} 失败: {e}")
            if account_idx is None:
                break
            continue

    # 所有重试都失败
    error_msg = f"文件上传失败: {last_error}"
    logger.error(error_msg)

    if isinstance(last_error, (AccountRateLimitError, NoAvailableAccountError)):
        raise HTTPException(status_code=429, detail=error_msg)
    elif isinstance(last_error, AccountAuthError):
        raise HTTPException(status_code=401, detail=error_msg)
    else:
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/v1/files")
async def list_files(
    token: str = Depends(require_api_auth)
) -> FileList:
    """列出所有上传的文件"""
    files = file_upload_service.list_files()
    return FileList(data=[
        FileObject(
            id=f["id"],
            bytes=f["bytes"],
            created_at=f["created_at"],
            filename=f["filename"],
            purpose=f.get("purpose", "assistants")
        )
        for f in files
    ])


@router.get("/v1/files/{file_id}")
async def get_file(
    file_id: str,
    token: str = Depends(require_api_auth)
) -> FileObject:
    """获取文件信息"""
    mapping = file_upload_service.get_mapping(file_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileObject(
        id=mapping.openai_file_id,
        bytes=mapping.size,
        created_at=int(mapping.created_at),
        filename=mapping.filename,
        purpose="assistants"
    )


@router.delete("/v1/files/{file_id}")
async def delete_file(
    file_id: str,
    token: str = Depends(require_api_auth)
):
    """删除文件"""
    if not file_upload_service.delete_file(file_id):
        raise HTTPException(status_code=404, detail="文件不存在")

    return {"id": file_id, "object": "file", "deleted": True}


# 图片访问接口（无需认证，用于在聊天中显示图片）
@router.get("/images/{conversation_id}/{filename}")
async def get_image(conversation_id: str, filename: str):
    """
    获取会话中的图片

    无需认证，用于在聊天界面中直接显示图片
    """
    image_path = image_service.get_image_path(conversation_id, filename)

    if not image_path or not image_path.exists():
        raise HTTPException(status_code=404, detail="图片不存在")

    # 根据扩展名确定MIME类型
    ext = image_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    media_type = mime_types.get(ext, "image/png")

    return FileResponse(
        path=image_path,
        media_type=media_type
    )


@router.get("/images/{conversation_id}")
async def list_conversation_images(
    conversation_id: str,
    token: str = Depends(require_api_auth)
):
    """列出会话中的所有图片"""
    images = image_service.list_conversation_images(conversation_id)
    return {"conversation_id": conversation_id, "images": images}
