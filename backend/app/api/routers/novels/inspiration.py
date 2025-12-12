"""
灵感对话路由

处理用户与AI的灵感对话，引导蓝图筹备。
"""

import json
import logging

from typing import List, Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import settings
from ....core.dependencies import (
    get_default_user,
    get_novel_service,
    get_llm_service,
    get_prompt_service,
)
from ....db.session import get_session
from ....exceptions import PromptTemplateNotFoundError
from ....schemas.novel import (
    ConverseRequest,
    ConverseResponse,
)
from ....schemas.user import UserInDB
from ....services.llm_service import LLMService
from ....services.novel_service import NovelService
from ....services.conversation_service import ConversationService
from ....services.prompt_service import PromptService
from ....utils.json_utils import (
    parse_llm_json_or_fail,
    remove_think_tags,
    unwrap_markdown_json,
)
from ....utils.prompt_helpers import ensure_prompt
from ....utils.sse_helpers import sse_event
from ....utils.exception_helpers import get_safe_error_message
from ....core.constants import NovelConstants

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{project_id}/inspiration/converse", response_model=ConverseResponse)
async def converse_with_inspiration(
    project_id: str,
    request: ConverseRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> ConverseResponse:
    """
    与AI进行灵感对话，引导蓝图筹备

    通过多轮对话，引导用户梳理小说创意，为生成蓝图做准备。
    """
    project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
    conversation_service = ConversationService(session)

    history_records = await conversation_service.list_conversations(project_id)
    logger.info(
        "项目 %s 灵感对话请求，用户 %s，历史记录 %s 条",
        project_id,
        desktop_user.id,
        len(history_records),
    )

    conversation_history = [
        {"role": record.role, "content": record.content}
        for record in history_records
    ]
    user_content = json.dumps(request.user_input, ensure_ascii=False)
    conversation_history.append({"role": "user", "content": user_content})

    # 获取灵感对话提示词（兼容旧版concept命名）
    system_prompt = await prompt_service.get_prompt("inspiration")
    if not system_prompt:
        # 向后兼容：fallback到旧名称
        system_prompt = await prompt_service.get_prompt("concept")
    system_prompt = ensure_prompt(system_prompt, "inspiration")

    llm_response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        temperature=settings.llm_temp_inspiration,
        user_id=desktop_user.id,
        timeout=240.0,
    )

    # 先标准化JSON字符串（用于存储对话历史）
    cleaned = remove_think_tags(llm_response)
    normalized = unwrap_markdown_json(cleaned)

    # 解析JSON
    parsed = parse_llm_json_or_fail(
        llm_response,
        f"项目{project_id}的灵感对话响应解析失败"
    )

    await conversation_service.append_conversation(project_id, "user", user_content)
    await conversation_service.append_conversation(project_id, "assistant", normalized)
    await session.commit()

    # 计算对话轮次（直接从已有数据计算，避免重复查询）
    # 刚添加了2条新记录（user + assistant），所以总数 = 原记录数 + 2
    total_messages = len(history_records) + 2
    conversation_turns = total_messages // 2  # 用户+助手=1轮

    # 判断对话是否完成：LLM明确标记完成 OR 对话轮次达到阈值
    llm_says_complete = parsed.get("is_complete", False)
    turns_threshold_met = conversation_turns >= NovelConstants.CONVERSATION_ROUNDS_SHORT

    if llm_says_complete or turns_threshold_met:
        parsed["is_complete"] = True
        parsed["ready_for_blueprint"] = True

        # 记录完成原因（用于调试）
        if turns_threshold_met and not llm_says_complete:
            logger.info(
                "项目 %s 对话已达到%d轮（阈值%d轮），自动标记为可生成蓝图",
                project_id, conversation_turns, NovelConstants.CONVERSATION_ROUNDS_SHORT
            )
        else:
            logger.info("项目 %s LLM标记对话完成，is_complete=true", project_id)
    else:
        logger.info(
            "项目 %s 灵感对话进行中，当前%d轮（阈值%d轮），is_complete=%s",
            project_id, conversation_turns, NovelConstants.CONVERSATION_ROUNDS_SHORT, llm_says_complete
        )

    parsed.setdefault("conversation_state", parsed.get("conversation_state", {}))
    return ConverseResponse(**parsed)


@router.post("/{project_id}/inspiration/converse-stream")
async def converse_with_inspiration_stream(
    project_id: str,
    request: ConverseRequest,
    novel_service: NovelService = Depends(get_novel_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
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
    import asyncio

    async def event_generator():
        try:
            # 1. 准备对话上下文
            project = await novel_service.ensure_project_owner(project_id, desktop_user.id)
            conversation_service = ConversationService(session)

            history_records = await conversation_service.list_conversations(project_id)
            logger.info(
                "项目 %s 灵感对话流式请求，用户 %s，历史记录 %s 条",
                project_id,
                desktop_user.id,
                len(history_records),
            )

            conversation_history = [
                {"role": record.role, "content": record.content}
                for record in history_records
            ]
            user_content = json.dumps(request.user_input, ensure_ascii=False)
            conversation_history.append({"role": "user", "content": user_content})

            # 2. 准备Prompt
            system_prompt = await prompt_service.get_prompt("inspiration")
            if not system_prompt:
                system_prompt = await prompt_service.get_prompt("concept")
            system_prompt = ensure_prompt(system_prompt, "inspiration")

            # 3. 发送streaming_start事件，通知前端禁用交互
            yield sse_event("streaming_start", {"status": "started"})

            # 4. 真流式调用LLM，收集完整响应
            full_response = []
            async for chunk in llm_service.stream_llm_response(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                temperature=settings.llm_temp_inspiration,
                user_id=desktop_user.id,
                timeout=240.0,
            ):
                content = chunk.get("content")
                if content:
                    full_response.append(content)

            # 5. 解析完整JSON响应
            llm_response = "".join(full_response)
            cleaned = remove_think_tags(llm_response)
            normalized = unwrap_markdown_json(cleaned)
            parsed = parse_llm_json_or_fail(
                llm_response,
                f"项目{project_id}的灵感对话响应解析失败"
            )

            # 6. 流式发送ai_message内容（分块发送，模拟打字效果）
            ai_message = parsed.get("ai_message", "")
            if ai_message:
                # 分块发送，每块约10-30个字符，模拟自然的打字速度
                chunk_size = 15
                for i in range(0, len(ai_message), chunk_size):
                    chunk_text = ai_message[i:i + chunk_size]
                    yield sse_event("ai_message_chunk", {"text": chunk_text})
                    await asyncio.sleep(0.03)  # 轻微延迟，让用户看到打字效果

            # 7. 逐个发送选项（如果有）
            ui_control = parsed.get("ui_control", {})
            if ui_control.get("type") == "inspired_options":
                options = ui_control.get("options", [])
                for idx, option in enumerate(options):
                    yield sse_event("option", {
                        "index": idx,
                        "total": len(options),
                        "option": option,
                    })
                    await asyncio.sleep(0.15)  # 选项间延迟，产生逐个出现的效果

            # 8. 保存对话历史
            await conversation_service.append_conversation(project_id, "user", user_content)
            await conversation_service.append_conversation(project_id, "assistant", normalized)
            await session.commit()

            # 9. 计算对话轮次和完成状态（直接从已有数据计算，避免重复查询）
            total_messages = len(history_records) + 2
            conversation_turns = total_messages // 2

            llm_says_complete = parsed.get("is_complete", False)
            turns_threshold_met = conversation_turns >= NovelConstants.CONVERSATION_ROUNDS_SHORT

            if llm_says_complete or turns_threshold_met:
                parsed["is_complete"] = True
                parsed["ready_for_blueprint"] = True

                if turns_threshold_met and not llm_says_complete:
                    logger.info(
                        "项目 %s 对话已达到%d轮（阈值%d轮），自动标记为可生成蓝图",
                        project_id, conversation_turns, NovelConstants.CONVERSATION_ROUNDS_SHORT
                    )
                else:
                    logger.info("项目 %s LLM标记对话完成，is_complete=true", project_id)
            else:
                logger.info(
                    "项目 %s 灵感对话进行中，当前%d轮（阈值%d轮），is_complete=%s",
                    project_id, conversation_turns, NovelConstants.CONVERSATION_ROUNDS_SHORT, llm_says_complete
                )

            parsed.setdefault("conversation_state", parsed.get("conversation_state", {}))

            # 10. 发送完成事件（包含placeholder等metadata，不再重复发送ui_control）
            yield sse_event("complete", {
                "placeholder": ui_control.get("placeholder", "输入你的想法..."),
                "conversation_state": parsed.get("conversation_state", {}),
                "is_complete": parsed.get("is_complete", False),
                "ready_for_blueprint": parsed.get("ready_for_blueprint"),
            })

            logger.info("项目 %s 灵感对话流式响应完成", project_id)

        except Exception as exc:
            logger.error(
                "项目 %s 灵感对话流式响应错误: %s",
                project_id,
                str(exc),
                exc_info=True
            )
            # 使用安全的错误消息过滤，避免泄露敏感信息
            safe_message = get_safe_error_message(exc, "灵感对话服务异常，请稍后重试")
            yield sse_event("error", {"message": safe_message})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        },
    )


@router.get("/{project_id}/inspiration/history", response_model=List[Dict[str, Any]])
async def get_conversation_history(
    project_id: str,
    novel_service: NovelService = Depends(get_novel_service),
    session: AsyncSession = Depends(get_session),
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
    conversation_service = ConversationService(session)
    history_records = await conversation_service.list_conversations(project_id)

    # 转换为前端可用的格式
    result = []
    for record in history_records:
        result.append({
            "id": record.id,
            "role": record.role,
            "content": record.content,  # 保持JSON字符串格式
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })

    logger.info(
        "项目 %s 获取对话历史，用户 %s，记录数 %d",
        project_id,
        desktop_user.id,
        len(result)
    )

    return result

