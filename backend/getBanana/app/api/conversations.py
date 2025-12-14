"""
会话管理API路由
- 会话创建、列表、删除
- 会话详情和消息历史
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.utils.auth import require_api_auth
from app.services.conversation_manager import conversation_manager
from app.services.image_service import image_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ConversationCreate(BaseModel):
    name: Optional[str] = ""
    model: str = "gemini-2.5-flash"
    system_prompt: Optional[str] = None


class ConversationInfo(BaseModel):
    id: str
    name: str
    model: str
    created_at: float
    message_count: int
    account_index: Optional[int] = None
    has_images: bool = False


class ConversationDetail(BaseModel):
    id: str
    name: str
    model: str
    created_at: float
    messages: List[dict]
    binding: Optional[dict] = None
    images: List[dict] = []


@router.post("")
async def create_conversation(
    request: ConversationCreate,
    token: str = Depends(require_api_auth)
) -> ConversationInfo:
    """
    创建新会话

    会自动分配一个可用账号
    """
    try:
        conv = await conversation_manager.create_conversation(
            name=request.name,
            model=request.model,
            system_prompt=request.system_prompt
        )

        return ConversationInfo(
            id=conv.id,
            name=conv.name,
            model=conv.model,
            created_at=conv.created_at,
            message_count=len(conv.messages),
            account_index=conv.binding.account_index if conv.binding else None
        )
    except Exception as e:
        logger.exception(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_conversations(
    token: str = Depends(require_api_auth)
) -> List[dict]:
    """列出所有会话"""
    return conversation_manager.list_conversations()


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    token: str = Depends(require_api_auth)
) -> ConversationDetail:
    """获取会话详情"""
    conv = await conversation_manager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取会话图片列表
    images = image_service.list_conversation_images(conversation_id)

    return ConversationDetail(
        id=conv.id,
        name=conv.name,
        model=conv.model,
        created_at=conv.created_at,
        messages=[msg.model_dump() for msg in conv.messages],
        binding=conv.binding.model_dump() if conv.binding else None,
        images=images
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    token: str = Depends(require_api_auth)
):
    """删除会话"""
    success = conversation_manager.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {"id": conversation_id, "deleted": True}


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    token: str = Depends(require_api_auth)
):
    """获取会话消息历史"""
    conv = await conversation_manager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = conv.messages[offset:offset + limit]
    return {
        "conversation_id": conversation_id,
        "messages": [msg.model_dump() for msg in messages],
        "total": len(conv.messages),
        "offset": offset,
        "limit": limit
    }


@router.get("/{conversation_id}/images")
async def get_conversation_images(
    conversation_id: str,
    token: str = Depends(require_api_auth)
):
    """获取会话的所有图片"""
    conv = await conversation_manager.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")

    images = image_service.list_conversation_images(conversation_id)
    return {
        "conversation_id": conversation_id,
        "images": images
    }
