"""
灵感对话路由

处理用户与AI的灵感对话，引导蓝图筹备。
路由层仅负责HTTP协议适配，业务逻辑委托给InspirationService。
"""

import asyncio
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_conversation_service,
    get_inspiration_service,
)
from ....db.session import get_session
from ....schemas.novel import (
    ConverseRequest,
    ConverseResponse,
)
from ....schemas.user import UserInDB
from ....services.novel_service import NovelService
from ....services.conversation_service import ConversationService
from ....services.inspiration_service import InspirationService
from ....utils.sse_helpers import sse_event, sse_error_event, create_sse_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/inspiration/converse", response_model=ConverseResponse)
async def converse_with_inspiration(
    project_id: str,
    request: ConverseRequest,
    novel_service: NovelService = Depends(get_novel_service),
    inspiration_service: InspirationService = Depends(get_inspiration_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ConverseResponse:
    """
    与AI进行灵感对话，引导蓝图筹备

    通过多轮对话，引导用户梳理小说创意，为生成蓝图做准备。
    """
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 委托业务逻辑给InspirationService（小说项目始终使用"novel"类型）
    result = await inspiration_service.process_conversation(
        project_id=project_id,
        user_input=request.user_input,
        user_id=desktop_user.id,
        project_type="novel",
    )

    # 提交事务
    await session.commit()

    return ConverseResponse(**result.parsed_response)


@router.post("/{project_id}/inspiration/converse-stream")
async def converse_with_inspiration_stream(
    project_id: str,
    request: ConverseRequest,
    novel_service: NovelService = Depends(get_novel_service),
    inspiration_service: InspirationService = Depends(get_inspiration_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    与AI进行灵感对话（智能流式响应）

    使用SSE (Server-Sent Events) 实现结构化流式输出。
    - ai_message内容流式发送（用户看到的是纯文字，不是JSON）
    - 选项逐个发送（动画效果）
    - 流式进行中禁用用户交互

    事件类型：
    - streaming_start: 开始流式输出，前端应禁用交互
    - ai_message_chunk: ai_message的文字片段（多次发送）
    - option: 单个选项数据
    - complete: 完成信号，包含最终metadata
    - error: 错误信息

    Returns:
        StreamingResponse with text/event-stream
    """
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    async def event_generator():
        try:
            # 使用InspirationService处理流式对话（小说项目始终使用"novel"类型）
            async for event in inspiration_service.process_conversation_stream(
                project_id=project_id,
                user_input=request.user_input,
                user_id=desktop_user.id,
                project_type="novel",
            ):
                event_type = event["event"]
                data = event["data"]

                if event_type == "streaming_start":
                    yield sse_event("streaming_start", data)

                elif event_type == "llm_chunk":
                    # LLM chunk不直接发送给前端，只用于收集完整响应
                    # 完整响应解析后再分块发送ai_message
                    pass

                elif event_type == "parsed_result":
                    # 解析完成，开始流式发送ai_message和选项
                    parsed = data["parsed"]

                    # 流式发送ai_message内容
                    ai_message = parsed.get("ai_message", "")
                    if ai_message:
                        chunk_size = 15
                        for i in range(0, len(ai_message), chunk_size):
                            chunk_text = ai_message[i:i + chunk_size]
                            yield sse_event("ai_message_chunk", {"text": chunk_text})
                            await asyncio.sleep(0.03)

                    # 逐个发送选项
                    ui_control = parsed.get("ui_control", {})
                    if ui_control.get("type") == "inspired_options":
                        options = ui_control.get("options", [])
                        for idx, option in enumerate(options):
                            yield sse_event("option", {
                                "index": idx,
                                "total": len(options),
                                "option": option,
                            })
                            await asyncio.sleep(0.15)

                    # 注意：事务已在InspirationService中提交，此处无需再commit
                    # 这避免了SSE生成器中的事务管理风险

                    # 发送完成事件
                    yield sse_event("complete", {
                        "placeholder": ui_control.get("placeholder", "输入你的想法..."),
                        "conversation_state": parsed.get("conversation_state", {}),
                        "is_complete": data["is_complete"],
                        "ready_for_blueprint": data["ready_for_blueprint"],
                    })

        except Exception as exc:
            yield sse_error_event(exc, "灵感对话")

    return create_sse_response(event_generator())


@router.get("/{project_id}/inspiration/history", response_model=List[Dict[str, Any]])
async def get_conversation_history(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[Dict[str, Any]]:
    """
    获取项目的灵感对话历史

    返回格式化的对话历史，用于恢复未完成的灵感对话。

    Returns:
        List[Dict]: 对话历史列表，每条包含role、content、created_at等字段
    """
    # 验证项目权限
    await novel_service.ensure_project_owner(project_id, desktop_user.id)

    # 获取对话历史
    history_records = await conversation_service.list_conversations(project_id)

    # 转换为前端可用的格式
    result = [
        {
            "id": record.id,
            "role": record.role,
            "content": record.content,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }
        for record in history_records
    ]

    logger.info(
        "项目 %s 获取对话历史，用户 %s，记录数 %d",
        project_id,
        desktop_user.id,
        len(result)
    )

    return result
