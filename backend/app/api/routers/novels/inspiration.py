"""
灵感对话路由

处理用户与AI的灵感对话，引导蓝图筹备。
"""

import asyncio
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

logger = logging.getLogger(__name__)

router = APIRouter()

# JSON响应格式指令
JSON_RESPONSE_INSTRUCTION = """
IMPORTANT: 你的回复必须是合法的 JSON 对象，并严格包含以下字段：
{
  "ai_message": "string",
  "ui_control": {
    "type": "single_choice | text_input | info_display | inspired_options",
    "options": [
      {"id": "option_1", "label": "string", "description": "string", "key_elements": ["元素1", "元素2"]}
    ],
    "placeholder": "string"
  },
  "conversation_state": {},
  "is_complete": false
}

**UI控件类型说明：**
- `single_choice`: 简单单选（仅显示label）
- `text_input`: 文本输入框（使用placeholder）
- `info_display`: 信息展示（仅显示ai_message）
- `inspired_options`: 灵感选项卡片（显示label、description、key_elements）

**何时使用inspired_options：**
- **推荐：在整个对话过程中始终使用**，持续为用户提供灵感激发
- 每个选项必须包含：id、label（标题8-12字）、description（详细描述50-100字）、key_elements（2-3个关键要素）
- 提供3-5个差异化明显的选项
- 根据对话进展调整选项层级：
  * 早期：宏观方向（类型、基调、世界观）
  * 中期：具体细节（主角特质、冲突类型、催化事件）
  * 后期：深化选择（主题深度、风格偏好、篇幅规划）
- placeholder应提示用户可以自由输入："选择上面的选项，或输入你的新想法..."

**示例（inspired_options）：**
```json
{
  "ai_message": "我分析了你的灵感，为你准备了几个不同的发展方向：",
  "ui_control": {
    "type": "inspired_options",
    "options": [
      {
        "id": "opt_1",
        "label": "硬科幻时间旅行",
        "description": "以严谨的物理学为基础，探讨时间悖论和因果律。主角可能是科学家意外发现时间旅行技术，需要修复时间线的裂痕。",
        "key_elements": ["时间悖论", "平行宇宙", "蝴蝶效应"]
      },
      {
        "id": "opt_2",
        "label": "奇幻时间魔法",
        "description": "在魔法世界中，时间是一种稀有的魔法属性。主角可能是唯一掌握时间魔法的人，但每次使用都会付出代价。",
        "key_elements": ["时间魔法", "命运抉择", "代价机制"]
      }
    ],
    "placeholder": "或者输入你的新想法..."
  },
  "conversation_state": {"round": 1},
  "is_complete": false
}
```

**重要说明：**
- 在对话进行中，`is_complete` 必须为 `false`
- 当「内部信息清单」中的所有项目都已完成，准备结束对话时，`is_complete` 必须设置为 `true`
- 当 `is_complete` 为 `true` 时，用户将看到"生成蓝图"按钮
- **推荐始终使用 inspired_options**，在整个对话过程中持续提供灵感激发选项
- 用户可以点击选项或自由输入，两种方式并存

不要输出额外的文本或解释。
"""


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
    system_prompt = f"{system_prompt}\n{JSON_RESPONSE_INSTRUCTION}"

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

    # 获取对话轮次（包括刚添加的这轮）
    conversations = await conversation_service.list_conversations(project_id)
    conversation_turns = len(conversations) // 2  # 用户+助手=1轮

    # 判断对话是否完成：LLM明确标记完成 OR 对话轮次达到阈值
    llm_says_complete = parsed.get("is_complete", False)
    CONVERSATION_TURNS_THRESHOLD = 5  # 阈值：5轮对话后自动可生成蓝图
    turns_threshold_met = conversation_turns >= CONVERSATION_TURNS_THRESHOLD

    if llm_says_complete or turns_threshold_met:
        parsed["is_complete"] = True
        parsed["ready_for_blueprint"] = True

        # 记录完成原因（用于调试）
        if turns_threshold_met and not llm_says_complete:
            logger.info(
                "项目 %s 对话已达到%d轮（阈值%d轮），自动标记为可生成蓝图",
                project_id, conversation_turns, CONVERSATION_TURNS_THRESHOLD
            )
        else:
            logger.info("项目 %s LLM标记对话完成，is_complete=true", project_id)
    else:
        logger.info(
            "项目 %s 灵感对话进行中，当前%d轮（阈值%d轮），is_complete=%s",
            project_id, conversation_turns, CONVERSATION_TURNS_THRESHOLD, llm_says_complete
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
    与AI进行灵感对话（流式响应）

    使用SSE (Server-Sent Events) 实现真正的流式输出。
    LLM生成一个token就立即发送给前端显示。

    事件类型：
    - token: AI回复的每个字符
    - complete: 完整的metadata（ui_control、conversation_state等）
    - error: 错误信息

    Returns:
        StreamingResponse with text/event-stream
    """
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
            system_prompt = f"{system_prompt}\n{JSON_RESPONSE_INSTRUCTION}"

            # 3. 调用LLM获取完整响应
            llm_response = await llm_service.get_llm_response(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                temperature=settings.llm_temp_inspiration,
                user_id=desktop_user.id,
                timeout=240.0,
            )

            # 4. 解析JSON
            cleaned = remove_think_tags(llm_response)
            normalized = unwrap_markdown_json(cleaned)
            parsed = parse_llm_json_or_fail(
                llm_response,
                f"项目{project_id}的灵感对话响应解析失败"
            )

            # 5. 逐字符发送ai_message（流式传输）
            ai_message = parsed.get("ai_message", "")
            for char in ai_message:
                yield sse_event("token", {"token": char})
                await asyncio.sleep(0.002)  # 极小延迟确保网络稳定（可选）

            # 6. 保存对话历史
            await conversation_service.append_conversation(project_id, "user", user_content)
            await conversation_service.append_conversation(project_id, "assistant", normalized)
            await session.commit()

            # 7. 计算对话轮次和完成状态
            conversations = await conversation_service.list_conversations(project_id)
            conversation_turns = len(conversations) // 2

            llm_says_complete = parsed.get("is_complete", False)
            CONVERSATION_TURNS_THRESHOLD = 5
            turns_threshold_met = conversation_turns >= CONVERSATION_TURNS_THRESHOLD

            if llm_says_complete or turns_threshold_met:
                parsed["is_complete"] = True
                parsed["ready_for_blueprint"] = True

                if turns_threshold_met and not llm_says_complete:
                    logger.info(
                        "项目 %s 对话已达到%d轮（阈值%d轮），自动标记为可生成蓝图",
                        project_id, conversation_turns, CONVERSATION_TURNS_THRESHOLD
                    )
                else:
                    logger.info("项目 %s LLM标记对话完成，is_complete=true", project_id)
            else:
                logger.info(
                    "项目 %s 灵感对话进行中，当前%d轮（阈值%d轮），is_complete=%s",
                    project_id, conversation_turns, CONVERSATION_TURNS_THRESHOLD, llm_says_complete
                )

            parsed.setdefault("conversation_state", parsed.get("conversation_state", {}))

            # 8. 发送完成事件（包含ui_control等metadata）
            yield sse_event("complete", {
                "ui_control": parsed.get("ui_control", {}),
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
            yield sse_event("error", {"message": str(exc)})

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

