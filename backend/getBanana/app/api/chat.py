"""
聊天API路由
- OpenAI兼容的 /v1/chat/completions 接口
- 支持图片输入输出
- 支持文件引用
"""
import json
import time
import uuid
import logging
from typing import Optional, List, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.utils.auth import require_api_auth
from app.services.conversation_manager import conversation_manager
from app.services.chat_service import chat_service
from app.services.account_manager import (
    account_manager,
    NoAvailableAccountError,
    AccountAuthError,
    AccountRateLimitError,
    AccountRequestError
)
from app.services.image_service import image_service
from app.services.jwt_service import jwt_service
from app.services.file_upload_service import (
    file_upload_service,
    upload_inline_image,
    extract_images_from_openai_content,
    extract_file_ids_from_content
)
from app.services.token_manager import token_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# OpenAI兼容的请求/响应模型
class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any]]  # 支持字符串或数组格式


class ChatRequest(BaseModel):
    model: str = "gemini-2.5-flash"
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    # 扩展字段
    conversation_id: Optional[str] = Field(None, description="会话ID，用于保持会话连续性")
    file_ids: Optional[List[str]] = Field(None, description="文件ID列表")


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: ChatUsage


class ChatChunkDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class ChatChunkChoice(BaseModel):
    index: int = 0
    delta: ChatChunkDelta
    finish_reason: Optional[str] = None


class ChatChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatChunkChoice]
    usage: Optional[ChatUsage] = None


@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    http_request: Request,
    token: str = Depends(require_api_auth)
):
    """
    OpenAI兼容的聊天接口

    支持：
    - 普通请求和流式请求
    - 会话连续性（通过conversation_id）
    - 文件上传（通过file_ids）
    - 内联图片（通过image_url格式）

    Headers:
    - X-Client-Type: 客户端类型（web, cli, api），默认为 api
    """
    # 获取客户端类型
    client_type = http_request.headers.get("X-Client-Type", "api")
    if client_type not in ("web", "cli", "api"):
        client_type = "api"

    try:
        # 提取系统提示词、用户消息、内联图片和文件引用
        system_prompt = ""
        user_message = ""
        history_messages = []  # 历史消息（用于上下文）
        input_images = []
        input_file_ids = list(request.file_ids or [])

        for i, msg in enumerate(request.messages):
            if msg.role == "system":
                # 系统提示词
                if isinstance(msg.content, str):
                    system_prompt = msg.content
                else:
                    # 从数组中提取文本
                    texts = [item.get("text", "") for item in msg.content if item.get("type") == "text"]
                    system_prompt = "\n".join(texts)

            elif msg.role == "user":
                content = msg.content

                # 解析content（支持字符串或数组格式）
                if isinstance(content, str):
                    text_content = content
                else:
                    # 数组格式，提取文本、图片和文件ID
                    text_content, images = extract_images_from_openai_content(content)
                    input_images.extend(images)

                    # 提取文件ID
                    file_ids = extract_file_ids_from_content(content)
                    input_file_ids.extend(file_ids)

                # 判断是否是最后一条用户消息
                is_last_user = True
                for j in range(i + 1, len(request.messages)):
                    if request.messages[j].role == "user":
                        is_last_user = False
                        break

                if is_last_user:
                    user_message = text_content
                else:
                    # 历史用户消息
                    history_messages.append({"role": "user", "content": text_content})

            elif msg.role == "assistant":
                # 历史助手回复
                if isinstance(msg.content, str):
                    history_messages.append({"role": "assistant", "content": msg.content})
                else:
                    texts = [item.get("text", "") for item in msg.content if item.get("type") == "text"]
                    history_messages.append({"role": "assistant", "content": "\n".join(texts)})

        if not user_message and not input_images and not input_file_ids:
            raise HTTPException(status_code=400, detail="缺少用户消息")

        # 验证通过后，获取或创建会话
        conversation = await conversation_manager.get_or_create_conversation(
            conv_id=request.conversation_id,
            model=request.model,
            source=client_type
        )

        # 判断是否是新会话（没有消息记录）
        is_new_conversation = len(conversation.messages) == 0

        logger.info(f"处理聊天请求: conv_id={conversation.id}, source={client_type}, is_new={is_new_conversation}, message_len={len(user_message)}, images={len(input_images)}, files={len(input_file_ids)}")

        # 记录消息到会话
        if is_new_conversation:
            # 新会话：记录系统提示词和所有历史消息
            if system_prompt:
                conversation_manager.add_message(conversation.id, "system", system_prompt)
            for hist_msg in history_messages:
                conversation_manager.add_message(conversation.id, hist_msg["role"], hist_msg["content"])

        # 记录当前用户消息
        conversation_manager.add_message(conversation.id, "user", user_message)

        # 获取会话绑定的账号信息
        gemini_file_ids = []
        account = None
        jwt = None
        session_name = None

        if conversation.binding:
            account = account_manager.get_account(conversation.binding.account_index)
            if account and account.is_usable():
                jwt = await jwt_service.ensure_jwt(account)
                session_name = conversation.binding.session_name

                # 如果没有session，先创建一个
                if not session_name:
                    session_name = await chat_service.create_gemini_session(account, jwt)
                    conversation_manager.update_binding_session(conversation.id, session_name)

        # 转换OpenAI file_id为Gemini fileId，检查session是否匹配
        for fid in input_file_ids:
            mapping = file_upload_service.get_mapping(fid)
            if mapping:
                # 检查文件是否属于当前session
                if mapping.session_name == session_name:
                    gemini_file_ids.append(mapping.gemini_file_id)
                elif jwt and session_name and account:
                    # Session不匹配，需要重新上传文件到当前session
                    logger.info(f"文件 {fid} session不匹配，重新上传到当前session")
                    try:
                        new_gemini_fid = await file_upload_service.reupload_to_session(
                            openai_file_id=fid,
                            jwt=jwt,
                            new_session_name=session_name,
                            team_id=account.team_id
                        )
                        if new_gemini_fid:
                            gemini_file_ids.append(new_gemini_fid)
                        else:
                            logger.warning(f"文件 {fid} 重新上传失败，跳过")
                    except Exception as e:
                        logger.error(f"重新上传文件失败: {e}")

        # 如果有内联图片，上传到当前session
        if input_images and jwt and session_name and account:
            for img_data in input_images:
                try:
                    uploaded_fid = await upload_inline_image(
                        jwt, session_name, account.team_id, img_data
                    )
                    if uploaded_fid:
                        gemini_file_ids.append(uploaded_fid)
                        logger.debug(f"内联图片上传成功: {uploaded_fid}")
                except Exception as e:
                    logger.error(f"上传内联图片失败: {e}")

        if request.stream:
            return StreamingResponse(
                stream_chat_response(
                    conversation=conversation,
                    message=user_message,
                    model=request.model,
                    file_ids=gemini_file_ids,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    api_token=token
                ),
                media_type="text/event-stream"
            )
        else:
            # 非流式请求
            result = await chat_service.chat(
                conversation=conversation,
                message=user_message,
                file_ids=gemini_file_ids,
                model=request.model,
                system_prompt=system_prompt,
                history_messages=history_messages
            )

            # 先保存生成的图片
            image_urls = []
            for img in result.images:
                if img.base64_data:
                    # 如果图片已经保存过（有file_path），直接使用已有路径
                    if img.file_path:
                        image_urls.append(f"/images/{conversation.id}/{img.file_name}")
                    else:
                        # 否则保存图片
                        saved_path = image_service.save_base64_image(
                            img.base64_data,
                            img.mime_type,
                            conversation.id
                        )
                        if saved_path:
                            image_urls.append(f"/images/{conversation.id}/{saved_path.name}")

            # 构建响应内容（包含图片链接）
            response_content = result.text
            if image_urls:
                response_content += "\n\n" + "\n".join(
                    f"![image]({url})" for url in image_urls
                )

            # 记录助手回复（包含图片链接）
            conversation_manager.add_message(conversation.id, "assistant", response_content)

            # 记录 token 消耗
            total_tokens = result.prompt_tokens + result.completion_tokens
            token_manager.record_usage(token, total_tokens)

            response = ChatResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                created=int(time.time()),
                model=request.model,
                choices=[
                    ChatChoice(
                        message=ChatMessage(role="assistant", content=response_content)
                    )
                ],
                usage=ChatUsage(
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    total_tokens=total_tokens
                )
            )

            # 在响应头中返回会话ID
            return {
                **response.model_dump(),
                "conversation_id": conversation.id
            }

    except NoAvailableAccountError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except AccountAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except AccountRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except AccountRequestError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"聊天请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(
    conversation,
    message: str,
    model: str,
    file_ids: List[str],
    system_prompt: str = "",
    history_messages: List[dict] = None,
    api_token: str = ""
):
    """
    生成流式响应

    使用后台任务执行生成，确保即使客户端断开也能完成
    """
    import asyncio

    if history_messages is None:
        history_messages = []

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    logger.info(f"开始流式响应: conv_id={conversation.id}")

    # 创建一个事件来等待生成完成
    generation_done = asyncio.Event()
    generation_result = {"result": None, "error": None}

    async def do_generation():
        """在后台执行生成任务"""
        try:
            logger.info("后台生成任务开始...")
            result = await chat_service.chat(
                conversation=conversation,
                message=message,
                file_ids=file_ids,
                model=model,
                system_prompt=system_prompt,
                history_messages=history_messages
            )
            generation_result["result"] = result
            logger.info(f"后台生成完成: text_len={len(result.text)}, images={len(result.images)}")
        except Exception as e:
            generation_result["error"] = e
            logger.exception(f"后台生成失败: {e}")
        finally:
            generation_done.set()

    # 启动后台生成任务
    generation_task = asyncio.create_task(do_generation())

    try:
        # 首先发送 conversation_id（让前端尽早保存，以便后续同步）
        conv_info = {"conversation_id": conversation.id}
        yield f"data: {json.dumps(conv_info)}\n\n"

        # 发送开始标记
        start_chunk = ChatChunk(
            id=chat_id,
            created=created,
            model=model,
            choices=[
                ChatChunkChoice(
                    delta=ChatChunkDelta(role="assistant")
                )
            ]
        )
        yield f"data: {start_chunk.model_dump_json()}\n\n"
        logger.info("已发送开始标记，等待生成完成...")

        # 等待生成完成，同时保持连接活跃
        while not generation_done.is_set():
            # 每秒发送一个心跳注释，保持连接
            try:
                await asyncio.wait_for(generation_done.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                # 发送心跳（SSE 注释）
                yield ": heartbeat\n\n"

        # 检查是否有错误
        if generation_result["error"]:
            error_chunk = {
                "error": {
                    "message": str(generation_result["error"]),
                    "type": "server_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            return

        result = generation_result["result"]
        if not result:
            return

        # 先保存所有图片（在记录消息和流式输出之前）
        # 确保即使客户端断开，图片也已保存
        saved_image_urls = []
        logger.info(f"处理图片: 共 {len(result.images)} 张图片")
        for i, img in enumerate(result.images):
            logger.info(f"图片[{i}]: base64_data={bool(img.base64_data)}, file_path={img.file_path}, file_name={img.file_name}")
            if img.base64_data:
                # 如果图片已经保存过（有file_path），直接使用已有路径
                if img.file_path:
                    img_url = f"/images/{conversation.id}/{img.file_name}"
                    saved_image_urls.append(img_url)
                    logger.info(f"使用已保存图片: {img_url}")
                else:
                    # 否则保存图片
                    saved_path = image_service.save_base64_image(
                        img.base64_data,
                        img.mime_type,
                        conversation.id
                    )
                    if saved_path:
                        img_url = f"/images/{conversation.id}/{saved_path.name}"
                        saved_image_urls.append(img_url)
                        # 更新 img 对象的路径信息
                        img.file_path = str(saved_path)
                        img.file_name = saved_path.name
                        logger.info(f"保存图片成功: {img_url}")
            else:
                logger.warning(f"图片[{i}] 没有 base64_data，跳过")

        logger.info(f"收集到 {len(saved_image_urls)} 个图片URL: {saved_image_urls}")

        # 构建包含图片的响应内容
        response_content = result.text
        if saved_image_urls:
            response_content += "\n\n" + "\n".join(
                f"![image]({url})" for url in saved_image_urls
            )

        # 记录助手回复（包含图片链接）
        conversation_manager.add_message(conversation.id, "assistant", response_content)

        # 流式输出文本
        text = result.text
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size]
            chunk = ChatChunk(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    ChatChunkChoice(
                        delta=ChatChunkDelta(content=chunk_text)
                    )
                ]
            )
            yield f"data: {chunk.model_dump_json()}\n\n"

        # 输出已保存的图片URL
        for img_url in saved_image_urls:
            img_chunk = ChatChunk(
                id=chat_id,
                created=created,
                model=model,
                choices=[
                    ChatChunkChoice(
                        delta=ChatChunkDelta(content=f"\n\n![image]({img_url})")
                    )
                ]
            )
            yield f"data: {img_chunk.model_dump_json()}\n\n"

        # 发送结束标记（包含 usage 统计）
        end_chunk = ChatChunk(
            id=chat_id,
            created=created,
            model=model,
            choices=[
                ChatChunkChoice(
                    delta=ChatChunkDelta(),
                    finish_reason="stop"
                )
            ],
            usage=ChatUsage(
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                total_tokens=result.prompt_tokens + result.completion_tokens
            )
        )
        yield f"data: {end_chunk.model_dump_json()}\n\n"

        # 记录 token 消耗
        if api_token:
            total_tokens = result.prompt_tokens + result.completion_tokens
            token_manager.record_usage(api_token, total_tokens)

        yield "data: [DONE]\n\n"

    except (GeneratorExit, asyncio.CancelledError):
        # 客户端断开连接
        logger.warning(f"流式响应中断（客户端断开）: conv_id={conversation.id}")

        # 生成任务会在后台继续执行，不需要取消它
        # 但需要确保结果被保存
        if not generation_done.is_set():
            logger.info(f"生成任务仍在运行，将在后台完成: conv_id={conversation.id}")
            # 添加一个回调来保存结果
            def on_task_done(t):
                logger.info(f"后台任务完成回调触发: conv_id={conversation.id}")
                save_generation_result(conversation, generation_result)
            generation_task.add_done_callback(on_task_done)
        else:
            # 任务已完成但客户端断开，立即保存结果
            logger.info(f"生成任务已完成，立即保存结果: conv_id={conversation.id}")
            save_generation_result(conversation, generation_result)
        raise

    except Exception as e:
        logger.exception(f"流式响应失败: {e}")
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"


def save_generation_result(conversation, generation_result: dict):
    """保存后台生成的结果（同步回调）"""
    import asyncio

    result = generation_result.get("result")
    error = generation_result.get("error")

    if error:
        logger.error(f"后台生成失败，保存错误信息: conv_id={conversation.id}")
        # 使用线程安全的方式添加消息
        try:
            conversation_manager.add_message(
                conversation.id,
                "assistant",
                f"[生成过程中出错: {str(error)}]"
            )
        except Exception as e:
            logger.error(f"保存错误信息失败: {e}")
        return

    if not result:
        logger.warning(f"后台生成无结果: conv_id={conversation.id}")
        return

    try:
        logger.info(f"保存后台生成结果: conv_id={conversation.id}, text_len={len(result.text)}, images={len(result.images)}")

        # 先保存生成的图片，并收集图片URL
        saved_image_urls = []
        for i, img in enumerate(result.images):
            logger.info(f"后台图片[{i}]: base64_data={bool(img.base64_data)}, file_path={img.file_path}, file_name={img.file_name}")
            if img.base64_data:
                if img.file_path:
                    # 图片已保存，直接使用已有路径
                    img_url = f"/images/{conversation.id}/{img.file_name}"
                    saved_image_urls.append(img_url)
                    logger.info(f"后台使用已保存图片: {img_url}")
                else:
                    # 保存图片
                    saved_path = image_service.save_base64_image(
                        img.base64_data,
                        img.mime_type,
                        conversation.id
                    )
                    if saved_path:
                        img_url = f"/images/{conversation.id}/{saved_path.name}"
                        saved_image_urls.append(img_url)
                        logger.info(f"后台保存图片: {saved_path.name}")
            else:
                logger.warning(f"后台图片[{i}] 没有 base64_data，跳过")

        # 构建包含图片的响应内容
        response_content = result.text
        if saved_image_urls:
            response_content += "\n\n" + "\n".join(
                f"![image]({url})" for url in saved_image_urls
            )

        # 保存助手回复（包含图片链接）
        conversation_manager.add_message(conversation.id, "assistant", response_content)

        logger.info(f"后台生成结果已保存: conv_id={conversation.id}, images={len(saved_image_urls)}")

    except Exception as e:
        logger.exception(f"保存后台生成结果失败: {e}")
