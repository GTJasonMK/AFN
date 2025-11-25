# 真正的流式输出实现方案

> 设计时间：2025-11-22
> 问题：当前是伪流式（等LLM完整响应后才打字），需要改为真流式（LLM输出一个token就立即显示）

---

## 问题分析

### 当前实现（伪流式）

```python
# 后端
llm_response = await llm_service.get_llm_response(...)  # 等待完整响应
return {"ai_message": llm_response, ...}

# 前端
def onSuccess(self, response):
    ai_message = response['ai_message']  # 拿到完整文本
    self.addMessage(ai_message, typing_effect=True)  # 打字机效果模拟
```

**问题**：
- ❌ 用户需要等待LLM完整生成后才能看到第一个字
- ❌ 打字机效果只是视觉模拟，不是真正的流式
- ❌ 长回复时等待时间过长，体验差

### 真流式实现目标

```python
# 后端
async for chunk in llm.stream():  # 立即yield每个token
    yield f"data: {chunk}\n\n"  # SSE格式

# 前端
eventSource.onmessage = (event) => {
    append_to_bubble(event.data)  # 立即显示每个token
}
```

**优势**：
- ✅ 用户立即看到第一个token开始输出
- ✅ 感知响应速度更快
- ✅ 长回复时体验流畅

---

## 技术方案：SSE (Server-Sent Events)

### 为什么选择SSE而非WebSocket？

| 特性 | SSE | WebSocket |
|------|-----|-----------|
| 通信方向 | 单向（服务器→客户端） | 双向 |
| 协议 | HTTP | 独立协议 |
| 浏览器支持 | 原生支持EventSource | 需要WebSocket API |
| 复杂度 | 简单 | 复杂 |
| 适用场景 | **LLM流式输出** | 聊天、游戏等双向交互 |

**结论**：对于LLM流式输出，SSE是最佳选择。

---

## 架构设计

### 1. 后端流式架构

```python
# backend/app/services/llm_service.py
class LLMService:
    async def get_llm_response_stream(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        *,
        temperature: float = 0.7,
        user_id: Optional[int] = None,
        timeout: float = 300.0,
    ) -> AsyncGenerator[str, None]:
        """
        流式生成LLM响应（异步生成器）

        Yields:
            str: 每个token的文本内容
        """
        # 获取配置
        config = await self._resolve_llm_config(user_id)

        # 创建客户端
        client = LLMClient.create_from_config(config)
        messages = [{"role": "system", "content": system_prompt}, *conversation_history]
        chat_messages = ChatMessage.from_list(messages)

        # 流式调用
        async for chunk in client.stream_chat(
            messages=chat_messages,
            model=config["model"],
            temperature=temperature,
            timeout=timeout,
        ):
            if chunk.get("content"):
                yield chunk["content"]  # 直接yield每个token
```

### 2. 路由层SSE端点

```python
# backend/app/api/routers/novels/inspiration.py
from fastapi.responses import StreamingResponse

@router.post("/{project_id}/inspiration/converse-stream")
async def converse_with_inspiration_stream(
    project_id: str,
    request: ConverseRequest,
    novel_service: NovelService = Depends(get_novel_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    流式灵感对话端点（SSE）

    Returns:
        StreamingResponse with text/event-stream
    """
    async def event_generator():
        # 1. 准备对话上下文
        conversation_service = ConversationService(session)
        history_records = await conversation_service.list_conversations(project_id)
        conversation_history = [
            {"role": record.role, "content": record.content}
            for record in history_records
        ]
        user_content = json.dumps(request.user_input, ensure_ascii=False)
        conversation_history.append({"role": "user", "content": user_content})

        # 2. 准备Prompt
        system_prompt = await prompt_service.get_prompt("inspiration")
        system_prompt = f"{system_prompt}\n{JSON_RESPONSE_INSTRUCTION}"

        # 3. 流式生成AI响应
        full_response = ""
        async for token in llm_service.get_llm_response_stream(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            temperature=settings.llm_temp_inspiration,
            user_id=desktop_user.id,
        ):
            full_response += token
            # 发送token事件
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        # 4. 解析完整响应并发送metadata
        cleaned = remove_think_tags(full_response)
        normalized = unwrap_markdown_json(cleaned)
        parsed = parse_llm_json_or_fail(full_response, f"项目{project_id}的灵感对话响应解析失败")

        # 5. 保存对话历史
        await conversation_service.append_conversation(project_id, "user", user_content)
        await conversation_service.append_conversation(project_id, "assistant", normalized)
        await session.commit()

        # 6. 发送完成事件（包含ui_control等metadata）
        yield f"event: complete\ndata: {json.dumps(parsed, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用Nginx缓冲
        },
    )
```

### 3. 前端SSE客户端

```python
# frontend/windows/inspiration_mode/main.py
def onMessageSent(self, message):
    """用户发送消息（流式版本）"""
    # 添加用户消息
    self.addMessage(message, is_user=True)

    # 禁用输入
    self.input_widget.setEnabled(False)

    # 创建AI消息气泡（初始为空）
    self.current_ai_bubble = ChatBubble("", is_user=False)
    self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_ai_bubble)

    # 启动SSE监听
    self._start_sse_stream(message)

def _start_sse_stream(self, message):
    """启动SSE流式监听"""
    if not self.project_id:
        # 创建新项目
        response = self.api_client.create_novel(
            title="未命名项目",
            initial_prompt=message
        )
        self.project_id = response.get('id')

    # 构造SSE URL
    url = f"{self.api_client.base_url}/api/novels/{self.project_id}/inspiration/converse-stream"

    # 启动SSE监听线程
    worker = SSEWorker(url, {
        "user_input": {"message": message},
        "conversation_state": {}
    })
    worker.token_received.connect(self.on_token_received)
    worker.complete.connect(self.on_stream_complete)
    worker.error.connect(self.on_stream_error)
    worker.start()

def on_token_received(self, token):
    """收到一个token"""
    # 立即追加到当前AI气泡
    current_text = self.current_ai_bubble.get_text()
    self.current_ai_bubble.set_text(current_text + token)

    # 滚动到底部
    QTimer.singleShot(10, lambda: self.chat_scroll.verticalScrollBar().setValue(
        self.chat_scroll.verticalScrollBar().maximum()
    ))

def on_stream_complete(self, metadata):
    """流式响应完成"""
    # 处理ui_control（显示选项卡片）
    ui_control = metadata.get('ui_control', {})
    if ui_control.get('type') == 'inspired_options':
        options_data = ui_control.get('options', [])
        if options_data:
            self._add_inspired_options(options_data)
            placeholder = ui_control.get('placeholder', '选择上面的选项，或输入你的新想法...')
            self.input_widget.setPlaceholder(placeholder)

    # 检查对话是否完成
    self.is_conversation_complete = metadata.get('is_complete', False)

    # 启用输入
    self.input_widget.setEnabled(True)
    self.input_widget.setFocus()
```

### 4. SSE Worker线程

```python
# frontend/utils/sse_worker.py
import json
import requests
from PyQt6.QtCore import QThread, pyqtSignal

class SSEWorker(QThread):
    """SSE流式监听工作线程"""

    token_received = pyqtSignal(str)  # 收到一个token
    complete = pyqtSignal(dict)  # 流式完成
    error = pyqtSignal(str)  # 错误

    def __init__(self, url, payload):
        super().__init__()
        self.url = url
        self.payload = payload
        self._stopped = False

    def run(self):
        """执行SSE监听"""
        try:
            # 使用requests的stream模式
            with requests.post(
                self.url,
                json=self.payload,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=(10, None)  # 连接10秒超时，读取无限制
            ) as response:
                response.raise_for_status()

                # 解析SSE流
                for line in response.iter_lines():
                    if self._stopped:
                        break

                    if not line:
                        continue

                    line = line.decode('utf-8')

                    # 解析SSE事件
                    if line.startswith('event: '):
                        event_type = line[7:]
                    elif line.startswith('data: '):
                        data = json.loads(line[6:])

                        if event_type == 'token':
                            # 发射token信号
                            self.token_received.emit(data['token'])
                        elif event_type == 'complete':
                            # 发射完成信号
                            self.complete.emit(data)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        """停止监听"""
        self._stopped = True
```

---

## 实现步骤

### Phase 1: 后端流式支持 ✅

1. **LLMService添加流式生成器**
   - 新增 `get_llm_response_stream()` 方法
   - 返回 `AsyncGenerator[str, None]`
   - 直接yield LLMClient.stream_chat()的每个chunk

2. **Inspiration路由添加SSE端点**
   - 新增 `/converse-stream` 端点
   - 使用 `StreamingResponse`
   - 发送两种事件：`token` 和 `complete`

### Phase 2: 前端SSE客户端 ✅

3. **创建SSEWorker线程**
   - 监听SSE流
   - 解析事件并发射PyQt信号
   - 支持停止和错误处理

4. **修改InspirationMode对话逻辑**
   - 替换原有AsyncAPIWorker为SSEWorker
   - 实现 `on_token_received()` 实时追加文本
   - 实现 `on_stream_complete()` 处理metadata

5. **ChatBubble支持动态更新**
   - 新增 `set_text()` 方法
   - 新增 `get_text()` 方法
   - 确保setText不影响样式

### Phase 3: 兼容性处理 ✅

6. **保留原有非流式端点**
   - `/converse` - 原有端点保留（用于降级）
   - `/converse-stream` - 新的流式端点
   - 前端优先使用流式，失败时fallback到非流式

7. **API客户端升级**
   - ArborisAPIClient 添加 `inspiration_converse_stream()` 方法
   - 返回SSE URL而非直接调用

---

## 收益与风险

### 预期收益 ✅

- ✅ **用户体验大幅提升**：立即看到输出，感知速度快
- ✅ **长回复友好**：避免长时间等待
- ✅ **技术先进性**：符合现代AI应用标准
- ✅ **扩展性强**：为后续功能（如打断、重新生成）铺路

### 潜在风险 ⚠️

- ⚠️ **复杂度增加**：SSE连接管理、错误处理更复杂
- ⚠️ **JSON解析挑战**：需要等待完整响应才能解析JSON（ai_message可能嵌套在JSON中）
- ⚠️ **兼容性测试**：需要测试网络不稳定场景
- ⚠️ **资源消耗**：长时间SSE连接占用资源

### 特殊挑战：JSON格式响应

当前灵感对话返回JSON：
```json
{
  "ai_message": "这是AI回复的文本...",
  "ui_control": {...},
  "conversation_state": {},
  "is_complete": false
}
```

**问题**：LLM流式输出的是JSON字符串，需要等待完整JSON才能解析。

**解决方案**：
1. **分离ai_message**：让LLM先输出ai_message，再输出其他字段
2. **改造Prompt**：要求LLM按特定格式输出（不现实，难以保证）
3. **后端解析+重组** ⭐ 推荐：
   - 后端收集完整JSON
   - 提取ai_message逐字符yield（token事件）
   - 最后发送完整metadata（complete事件）

**实现**：
```python
async def event_generator():
    # 收集完整响应
    full_response = ""
    async for token in llm_service.get_llm_response_stream(...):
        full_response += token

    # 解析JSON
    parsed = json.loads(full_response)
    ai_message = parsed["ai_message"]

    # 逐字符发送ai_message
    for char in ai_message:
        yield f"event: token\ndata: {json.dumps({'token': char})}\n\n"
        await asyncio.sleep(0.01)  # 控制发送速度

    # 发送完整metadata
    yield f"event: complete\ndata: {json.dumps(parsed)}\n\n"
```

**问题**：这样仍然需要等待LLM完整输出后才能开始显示😞

**真正的解决方案** ⭐⭐⭐：
修改Prompt，让LLM先输出ai_message（纯文本），再输出JSON：
```
请按以下格式回复：
1. 先输出对用户的回复（纯文本）
2. 然后输出 <JSON>...</JSON> 标记包裹的JSON数据

示例：
你好！我理解你的创意了。让我为你提供几个方向...

<JSON>
{
  "ui_control": {...},
  "conversation_state": {},
  "is_complete": false
}
</JSON>
```

这样后端可以：
1. 流式yield纯文本部分（实时显示）
2. 收集到<JSON>标记后解析metadata3. 发送complete事件

---

## 推荐的实现策略

由于JSON格式的复杂性，我建议：

**阶段1：保守实现**（推荐立即执行）
- 保持当前JSON响应格式
- 后端收集完整响应后逐字符发送（模拟流式）
- 虽然仍需等待LLM完整生成，但：
  - 代码架构为真流式做好准备
  - 前端体验已是真流式（逐字符显示）
  - 后续只需优化后端即可

**阶段2：Prompt改造**（后续优化）
- 修改Prompt模板，要求先输出纯文本再输出JSON
- 后端实现真正的token级流式
- 这需要大量测试确保LLM遵守格式

---

## 文件修改清单

### 后端修改（5个文件）

1. `backend/app/services/llm_service.py`
   - 新增 `get_llm_response_stream()` 方法

2. `backend/app/api/routers/novels/inspiration.py`
   - 新增 `/converse-stream` 端点
   - 导入 `StreamingResponse`

3. `backend/app/utils/sse_helpers.py` ⭐ 新建
   - SSE事件格式化工具
   - `sse_event(event_type, data)` 函数

### 前端修改（5个文件）

4. `frontend/utils/sse_worker.py` ⭐ 新建
   - SSEWorker线程类
   - 监听SSE流并发射信号

5. `frontend/windows/inspiration_mode/main.py`
   - 修改 `onMessageSent()` 使用SSEWorker
   - 新增 `on_token_received()` 处理token
   - 新增 `on_stream_complete()` 处理complete
   - 新增 `_start_sse_stream()` 启动SSE

6. `frontend/windows/inspiration_mode/chat_bubble.py`
   - 新增 `set_text()` 方法
   - 新增 `get_text()` 方法

7. `frontend/api/client.py`
   - 新增 `inspiration_converse_stream()` 方法（可选）

### 文档（1个文件）

8. `docs/STREAMING_OUTPUT_IMPLEMENTATION.md` ⭐ 本文档

---

## 测试计划

### 单元测试

- [ ] LLMService.get_llm_response_stream() 返回AsyncGenerator
- [ ] SSE事件格式正确（event: token/complete）
- [ ] JSON解析和metadata提取正确

### 集成测试

- [ ] 完整对话流程：用户输入 → SSE流 → 前端显示
- [ ] token逐个正确显示
- [ ] complete事件包含完整ui_control
- [ ] 选项卡片正确显示
- [ ] 对话历史正确保存

### 异常场景测试

- [ ] 网络中断时SSE重连
- [ ] LLM超时处理
- [ ] JSON解析失败降级
- [ ] 前端切换页面时停止SSE

---

## 兼容性说明

**向后兼容**：
- ✅ 保留原有 `/converse` 非流式端点
- ✅ 前端优先使用流式，失败时fallback
- ✅ 移动端或旧浏览器仍可使用非流式

**浏览器支持**：
- ✅ Chrome/Edge (Chromium): 完全支持
- ✅ Firefox: 完全支持
- ✅ Safari: 完全支持（iOS 13+）
- ⚠️ IE11: 不支持（但桌面应用不涉及）

---

**设计者**：Claude Code
**设计时间**：2025-11-22
**实施优先级**：高
**预估工作量**：4-6小时（阶段1），2-3小时（阶段2）
**状态**：📋 设计完成，待确认实施
